#!/usr/bin/env python3
"""Kontingent-Bremse: geplante Agentenläufe pausieren, solange das Claude-Abo erschöpft ist.

Die Agenten arbeiten über das Claude-Abo (Secret CLAUDE_CODE_OAUTH_TOKEN) –
dasselbe Wochenkontingent, mit dem der Auftraggeber selbst arbeitet. Am
27.09.2026 war es aufgebraucht, und alle Agenten brachen mitten im Lauf ab
(„You've hit your weekly limit · resets Sep 30, 2am (UTC)“). Damit geplante
Läufe danach nicht Nacht für Nacht vergeblich starten, gibt es zwei Bremsen:

    Pause         Meldet ein Claude-Schritt das Wochenlimit, öffnet dieses
                  Werkzeug das Issue „Agenten pausieren bis …“ (Label
                  kontingent-pause, Zeile „pause_bis:“). Bis dahin setzen die
                  geplanten Läufe aus. Wer das Issue schließt, hebt die Pause auf.
    Wochengrenze  Höchstens WOCHENGRENZE Entwürfe je Kontingentwoche; danach
                  setzen die geplanten Läufe bis zum Neustart aus.

Von Hand gestartete Läufe sind nie gesperrt.

Befehle (Ausgabe jeweils als Zeilen name=wert für $GITHUB_OUTPUT):
    erkennen [DATEI]   liest den Verlauf eines Claude-Schritts (Standard:
                       $RUNNER_TEMP/claude-execution-output.json) → limit=woche|sitzung|nein,
                       bis=<Zeit UTC>; beim Wochenlimit wird die Pause gesetzt
    pruefen            vor einem geplanten Lauf → laufen=ja|nein, frei=<Zahl>, grund=<Text>;
                       abgelaufene Pausen werden geschlossen
    zaehlen            Entwürfe seit dem letzten Neustart → anzahl=<Zahl>, seit=<Zeit UTC>

Die Kontingentwoche beginnt mittwochs um 02:00 UTC – 04:00 Uhr deutscher
Sommerzeit, 03:00 Uhr Winterzeit. Benötigt nur die Standardbibliothek und die
GitHub-CLI (GH_TOKEN mit issues: write und pull-requests: read).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

WOCHENGRENZE = 10                 # Entwürfe je Kontingentwoche (alle Agenten zusammen)
NEUSTART_WOCHENTAG = 2            # Mittwoch (Montag = 0)
NEUSTART_STUNDE_UTC = 2
PUFFER = timedelta(minutes=15)    # nach dem Neustart etwas warten
LABEL = "kontingent-pause"
AGENTEN_ZWEIGE = re.compile(r"^(entwurf|vorlage)/")
MONATE = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun",
                                      "jul", "aug", "sep", "oct", "nov", "dec"), start=1)}
MELDUNG = re.compile(
    r"hit your (?P<art>weekly|session|daily|usage) limit\s*[·•|\-–]?\s*resets\s+(?P<wann>[^()\n\"\\]+?)"
    r"\s*\((?P<zone>[A-Za-z_/+\-0-9]+)\)", re.I)
MELDUNG_ALT = re.compile(r"Claude AI usage limit reached\|(?P<epoch>\d{9,11})")


# --------------------------------------------------------------------------
# Zeit
# --------------------------------------------------------------------------

def letzter_sonntag(jahr: int, monat: int) -> int:
    tag = 31
    while datetime(jahr, monat, tag).weekday() != 6:
        tag -= 1
    return tag


def berlin_versatz(utc: datetime) -> timedelta:
    """Abstand der deutschen Zeit zu UTC: Sommerzeit vom letzten Sonntag im März bis zum
    letzten Sonntag im Oktober, jeweils 01:00 UTC (ohne Zeitzonendaten, auch unter Windows)."""
    beginn = datetime(utc.year, 3, letzter_sonntag(utc.year, 3), 1, tzinfo=timezone.utc)
    ende = datetime(utc.year, 10, letzter_sonntag(utc.year, 10), 1, tzinfo=timezone.utc)
    return timedelta(hours=2 if beginn <= utc < ende else 1)


def berlin(utc: datetime) -> datetime:
    return (utc + berlin_versatz(utc)).replace(tzinfo=None)


def berlin_nach_utc(ortszeit: datetime) -> datetime:
    """Deutsche Ortszeit (ohne Zeitzone) → UTC. Bei der doppelten Stunde im Oktober die erste."""
    for stunden in (2, 1):
        kandidat = ortszeit.replace(tzinfo=timezone.utc) - timedelta(hours=stunden)
        if berlin_versatz(kandidat) == timedelta(hours=stunden):
            return kandidat
    return ortszeit.replace(tzinfo=timezone.utc) - timedelta(hours=1)


def berlin_text(utc: datetime) -> str:
    tage = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
    b = berlin(utc)
    return f"{tage[b.weekday()]}, {b:%d.%m.%Y}, {b:%H:%M} Uhr"


def iso(utc: datetime) -> str:
    return utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_lesen(text: str) -> datetime | None:
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def wochenbeginn(jetzt: datetime) -> datetime:
    """Letzter Neustart des Kontingents (Mittwoch 02:00 UTC) bis einschließlich jetzt."""
    tag = jetzt.astimezone(timezone.utc).replace(hour=NEUSTART_STUNDE_UTC, minute=0, second=0, microsecond=0)
    tag -= timedelta(days=(tag.weekday() - NEUSTART_WOCHENTAG) % 7)
    return tag if tag <= jetzt else tag - timedelta(days=7)


def naechster_neustart(jetzt: datetime) -> datetime:
    return wochenbeginn(jetzt) + timedelta(days=7)


# --------------------------------------------------------------------------
# Limit-Meldung lesen
# --------------------------------------------------------------------------

def reset_lesen(text: str, jetzt: datetime) -> tuple[str, datetime] | None:
    """Art des Limits (woche|sitzung) und Zeitpunkt des Neustarts (UTC) aus der Meldung.

    Bekannte Formen: „You've hit your weekly limit · resets Sep 30, 2am (UTC)“,
    „You've hit your session limit · resets 12:20pm (Europe/Berlin)“ und die ältere
    „Claude AI usage limit reached|1759197600“. Ohne lesbare Zeit: nächster Mittwoch.
    """
    m = MELDUNG.search(text)
    if m:
        art = "woche" if m.group("art").lower() == "weekly" else "sitzung"
        zeit = zeit_lesen(m.group("wann"), m.group("zone"), jetzt)
        if zeit is None:
            zeit = naechster_neustart(jetzt) if art == "woche" else jetzt + timedelta(hours=5)
        return art, zeit
    m = MELDUNG_ALT.search(text)
    if m:
        zeit = datetime.fromtimestamp(int(m.group("epoch")), tz=timezone.utc)
        return ("woche" if zeit - jetzt > timedelta(hours=6) else "sitzung"), zeit
    return None


def zeit_lesen(wann: str, zone: str, jetzt: datetime) -> datetime | None:
    """„Sep 30, 2am“ oder „12:20pm“ in der genannten Zeitzone (UTC oder Europe/Berlin) → UTC."""
    if zone.upper() not in ("UTC", "GMT", "EUROPE/BERLIN"):
        return None
    t = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)", wann, re.I)
    if not t:
        return None
    stunde = int(t.group(1)) % 12 + (12 if t.group(3).lower() == "pm" else 0)
    minute = int(t.group(2) or 0)
    d = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})\b", wann)
    ortsjetzt = berlin(jetzt) if zone.upper() == "EUROPE/BERLIN" else jetzt.replace(tzinfo=None)

    def nach_utc(ortszeit: datetime) -> datetime:
        return berlin_nach_utc(ortszeit) if zone.upper() == "EUROPE/BERLIN" else ortszeit.replace(tzinfo=timezone.utc)

    if d and d.group(1).lower() in MONATE:
        monat, tag = MONATE[d.group(1).lower()], int(d.group(2))
        for jahr in (ortsjetzt.year, ortsjetzt.year + 1):
            try:
                kandidat = nach_utc(datetime(jahr, monat, tag, stunde, minute))
            except ValueError:
                return None
            if kandidat > jetzt - timedelta(days=2):
                return kandidat
        return None
    kandidat = nach_utc(ortsjetzt.replace(hour=stunde, minute=minute, second=0, microsecond=0))
    return kandidat if kandidat > jetzt else kandidat + timedelta(days=1)


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------

def gh(*args: str) -> str:
    fehler = ""
    for versuch in range(3):
        r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120)
        if r.returncode == 0:
            return r.stdout
        fehler = r.stderr.strip()
        time.sleep(2 * (versuch + 1))
    raise RuntimeError(fehler[:300])


def repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or gh("repo", "view", "--json", "nameWithOwner",
                                                     "--jq", ".nameWithOwner").strip()


def pausen() -> list[dict]:
    """Offene Pause-Issues mit ihrem Ende (UTC)."""
    issues = json.loads(gh("issue", "list", "--repo", repo(), "--label", LABEL, "--state", "open",
                           "--limit", "20", "--json", "number,title,body"))
    for issue in issues:
        m = re.search(r"(?m)^pause_bis:\s*(\S+)", issue.get("body") or "")
        issue["bis"] = iso_lesen(m.group(1)) if m else None
    return issues


def pause_text(bis: datetime, lauf: str) -> tuple[str, str]:
    titel = f"Agenten pausieren bis {berlin_text(bis)}"
    koerper = "\n".join([
        "Die Agenten haben das Wochenkontingent des Claude-Abos erreicht. Geplante Läufe setzen aus, "
        "bis es wieder zur Verfügung steht.",
        "",
        f"pause_bis: {iso(bis)}",
        "",
        f"- **Weiter geht es:** {berlin_text(bis)} (deutsche Zeit), beim nächsten geplanten Lauf.",
        f"- **Erkannt im Lauf:** {lauf}" if lauf else "- **Erkannt** in einem Agentenlauf.",
        "- **Früher weitermachen:** dieses Issue schließen. Dann laufen die geplanten Agenten beim nächsten "
        "Termin wieder.",
        "",
        "Von Hand gestartete Läufe sind nicht gesperrt, scheitern bis dahin aber voraussichtlich am Limit. "
        "Dieses Issue schließt sich nach Ablauf der Pause von selbst.",
    ])
    return titel, koerper


def pause_setzen(bis: datetime, lauf: str = "") -> str:
    """Öffnet das Pause-Issue oder verlängert ein offenes. Ergebnis: Issue-Nummer."""
    gh("label", "create", LABEL, "--repo", repo(), "--color", "FBCA04", "--force",
       "--description", "Agenten pausieren: Wochenkontingent des Claude-Abos erschöpft")
    titel, koerper = pause_text(bis, lauf)
    offen = pausen()
    if offen:
        nummer = str(offen[0]["number"])
        if offen[0]["bis"] is None or offen[0]["bis"] < bis:
            gh("issue", "edit", nummer, "--repo", repo(), "--title", titel, "--body", koerper)
        return nummer
    adresse = gh("issue", "create", "--repo", repo(), "--title", titel, "--body", koerper, "--label", LABEL).strip()
    return adresse.rsplit("/", 1)[-1]


def entwuerfe_seit(seit: datetime) -> int:
    """Pull Requests der Agenten (Zweige entwurf/… und vorlage/…), angelegt seit `seit`."""
    prs = json.loads(gh("pr", "list", "--repo", repo(), "--state", "all", "--limit", "100",
                        "--search", f"created:>={iso(seit)}", "--json", "number,headRefName,createdAt"))
    return sum(1 for pr in prs if AGENTEN_ZWEIGE.match(pr.get("headRefName", ""))
               and (iso_lesen(pr.get("createdAt", "")) or seit) >= seit)


# --------------------------------------------------------------------------

def ausgabe(**werte) -> None:
    for name, wert in werte.items():
        print(f"{name}={wert}")


def erkennen(datei: Path, jetzt: datetime, lauf: str) -> int:
    if not datei.is_file():
        ausgabe(limit="nein", bis="")
        return 0
    roh = datei.read_text(encoding="utf-8", errors="replace")
    try:                    # · und ’ aus der JSON-Datei als Zeichen lesen
        roh = json.dumps(json.loads(roh), ensure_ascii=False)
    except ValueError:
        pass
    gelesen = reset_lesen(roh, jetzt)
    if not gelesen:
        ausgabe(limit="nein", bis="")
        return 0
    art, bis = gelesen
    bis += PUFFER
    if art == "woche":
        try:
            nummer = pause_setzen(bis, lauf)
            print(f"::warning title=Kontingent::Wochenlimit des Claude-Abos erreicht. Geplante Läufe pausieren bis "
                  f"{berlin_text(bis)} (Issue #{nummer}).", file=sys.stderr)
        except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
            print(f"::warning title=Kontingent::Wochenlimit erreicht, Pause-Issue nicht anlegbar ({fehler}).",
                  file=sys.stderr)
    else:
        print(f"::warning title=Kontingent::Sitzungslimit des Claude-Abos erreicht – wieder frei ab "
              f"{berlin_text(bis)}. Keine Pause nötig.", file=sys.stderr)
    ausgabe(limit=art, bis=iso(bis))
    return 0


def pruefen(jetzt: datetime) -> int:
    try:
        for issue in pausen():
            if issue["bis"] and issue["bis"] > jetzt:
                ausgabe(laufen="nein", frei=0,
                        grund=f"Kontingent-Pause bis {berlin_text(issue['bis'])} (Issue #{issue['number']})")
                return 0
            gh("issue", "close", str(issue["number"]), "--repo", repo(), "--comment",
               "Die Pause ist abgelaufen – die geplanten Agenten laufen wieder.")
        anzahl = entwuerfe_seit(wochenbeginn(jetzt))
    except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
        print(f"::warning title=Kontingent::Prüfung nicht möglich ({str(fehler)[:200]}) – der Lauf startet trotzdem.",
              file=sys.stderr)
        ausgabe(laufen="ja", frei=WOCHENGRENZE, grund="Prüfung nicht möglich")
        return 0
    frei = max(0, WOCHENGRENZE - anzahl)
    if not frei:
        ausgabe(laufen="nein", frei=0, grund=f"Wochengrenze erreicht: {anzahl} Entwürfe seit "
                                             f"{berlin_text(wochenbeginn(jetzt))}, höchstens {WOCHENGRENZE}")
        return 0
    ausgabe(laufen="ja", frei=frei, grund=f"{anzahl} von {WOCHENGRENZE} Entwürfen dieser Woche")
    return 0


def main(argumente: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    unter = p.add_subparsers(dest="befehl", required=True)
    e = unter.add_parser("erkennen")
    e.add_argument("datei", nargs="?", default="")
    unter.add_parser("pruefen")
    unter.add_parser("zaehlen")
    a = p.parse_args(argumente)
    jetzt = datetime.now(timezone.utc)
    if a.befehl == "erkennen":
        datei = Path(a.datei or Path(os.environ.get("RUNNER_TEMP", ".")) / "claude-execution-output.json")
        lauf = ""
        if os.environ.get("GITHUB_RUN_ID"):
            lauf = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                    f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
        return erkennen(datei, jetzt, lauf)
    if a.befehl == "pruefen":
        return pruefen(jetzt)
    seit = wochenbeginn(jetzt)
    try:
        ausgabe(anzahl=entwuerfe_seit(seit), seit=iso(seit))
    except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
        print(f"::warning title=Kontingent::Zählung nicht möglich ({str(fehler)[:200]}).", file=sys.stderr)
        ausgabe(anzahl="", seit=iso(seit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
