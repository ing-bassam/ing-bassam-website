#!/usr/bin/env python3
"""Setzt Entwürfe in entwuerfe/entwurf/ auf „Veröffentlicht“ – alle, eine Auswahl oder automatisch.

Wird vom Workflow „Entwürfe veröffentlichen“ aufgerufen: von Hand (ein Klick
unter Actions) oder nach Zeitplan montags bis freitags (--automatisch).
Geändert wird nur die Zeile `status:` im Dateikopf; alles andere
(Einsortieren nach veroeffentlicht/, Seiten, Sitemap, llms.txt) erledigt
danach der Seitenbauer.

Zurückgehalten werden – mit Grund in der Ausgabe – Entwürfe
    - mit offenen Prüfpunkten (`> TODO`): Der Seitenbauer würde sie ohnehin
      gesperrt lassen;
    - mit `zurueckhalten: ja` im Dateikopf (von Hand gesetzt);
    - die eine Doppelung sind: dasselbe Urteil oder dasselbe Thema wie ein
      veröffentlichter oder ein älterer Entwurf (tools/doppelungen.py);
    - deren Pull-Request-Zweig nach dem Zusammenführen noch Korrekturen bekommen
      hat, die auf main fehlen (verglichen wird der Inhalt) – typischerweise aus der Fakten-
      oder Schlussprüfung, die zu spät kamen (Anlass: Am 02.10.2026 waren fünf
      Entwürfe zusammengeführt worden, bevor die Prüfungen fertig waren; einer
      ging so ohne Korrekturen online);
    - die ein offener Pull Request noch ändert.
Die beiden letzten Prüfungen brauchen die GitHub-CLI; ohne sie entfallen sie
mit einem Hinweis.

Aufruf:
    python tools/veroeffentlichen.py                       alle Entwürfe
    python tools/veroeffentlichen.py --auswahl kurz1,kurz2 nur diese (Kurzform oder Dateiname)
    python tools/veroeffentlichen.py --automatisch --max 2 die ältesten freigegebenen, höchstens 2
    python tools/veroeffentlichen.py --probelauf           nur anzeigen, nichts ändern
    … --bericht DATEI                                      Ergebnis zusätzlich als JSON

Letzte Ausgabezeile: Zahl der veröffentlichten Entwürfe (für den Workflow).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bestand  # noqa: E402
import doppelungen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
ORDNER = WURZEL / "entwuerfe" / "entwurf"
KOPF = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)


def feld(kopf: str, name: str) -> str:
    m = re.search(rf"(?m)^{name}:\s*(.*?)\s*$", kopf)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def lokaler_bestand() -> list[dict]:
    """Alle Beiträge und Entwürfe im ausgecheckten Stand (der Workflow checkt main frisch aus)."""
    eintraege = []
    for pfad in sorted((WURZEL / "entwuerfe").rglob("*.md")):
        if pfad.name.lower() == "readme.md":
            continue
        e = bestand.eintrag_aus_entwurf(pfad.read_text(encoding="utf-8"), pfad.relative_to(WURZEL).as_posix(),
                                        "hauptzweig")
        if e:
            eintraege.append(e)
    return eintraege


def gh(*args: str) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:300])
    return r.stdout


def offene_korrekturen(dateinamen: set[str]) -> tuple[dict[str, str], str]:
    """Dateiname → Grund zum Zurückhalten, aus den Pull Requests.

    Zweiter Rückgabewert: Hinweis, wenn die Prüfung nicht möglich war.
    """
    if not shutil.which("gh"):
        return {}, "GitHub-CLI fehlt – nicht geprüft, ob Prüfkorrekturen fehlen."
    gruende: dict[str, str] = {}
    try:
        repo = bestand.repo_name()
        felder = "number,headRefName,headRefOid,files,state"
        offen = json.loads(gh("pr", "list", "--repo", repo, "--state", "open", "--limit", "100", "--json", felder))
        for pr in offen:
            for f in pr.get("files") or []:
                name = Path(f["path"]).name
                if name in dateinamen:
                    gruende.setdefault(name, f"Pull Request #{pr['number']} ändert diesen Entwurf noch – erst "
                                             "zusammenführen oder schließen")
        zusammen = json.loads(gh("pr", "list", "--repo", repo, "--state", "merged", "--limit", "200",
                                 "--json", felder))
        for pr in zusammen:
            namen = {Path(f["path"]).name for f in pr.get("files") or []} & dateinamen
            if not namen or not pr.get("headRefOid") or not pr.get("headRefName"):
                continue
            zweig = urllib.parse.quote(pr["headRefName"], safe="")
            try:
                # Was kam auf dem Zweig nach dem Zusammenführen dazu?
                spaeter = json.loads(gh("api", f"repos/{repo}/compare/{pr['headRefOid']}...{zweig}",
                                        "--jq", "[.ahead_by, [.files[]?.filename]]"))
            except (RuntimeError, ValueError):
                continue                  # Zweig gelöscht: nichts nachgekommen
            if not spaeter[0]:
                continue
            # Quelldateien vergleichen (Seiten und PDFs entstehen daraus): Wurden die
            # Korrekturen auf anderem Weg übernommen – etwa per Cherry-Pick –, ist der
            # Inhalt auf main gleich, und es gibt nichts zurückzuhalten.
            fehlend = []
            for pfad in spaeter[1]:
                if not ((pfad.startswith("entwuerfe/") and pfad.endswith(".md")) or
                        (pfad.startswith("vorlagen/") and pfad.endswith(".yml"))):
                    continue
                lokal = WURZEL / pfad
                try:
                    auf_zweig = gh("api", "-H", "Accept: application/vnd.github.raw+json",
                                   f"repos/{repo}/contents/{urllib.parse.quote(pfad)}?ref={zweig}")
                except RuntimeError:
                    continue
                if not lokal.is_file() or lokal.read_text(encoding="utf-8").strip() != auf_zweig.strip():
                    fehlend.append(pfad)
            if fehlend:
                for name in namen:
                    gruende.setdefault(name, f"Zweig von Pull Request #{pr['number']} hat nach dem Zusammenführen "
                                             f"Korrekturen bekommen, die auf main fehlen ({len(fehlend)} Datei(en)) – "
                                             "erst übernehmen oder, falls schon eingearbeitet, den Zweig löschen")
    except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
        return gruende, f"Pull Requests nicht lesbar ({str(fehler)[:160]}) – nicht geprüft, ob Prüfkorrekturen fehlen."
    return gruende, ""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--auswahl", default="alle",
                   help="„alle“ oder Kurzformen bzw. Dateinamen, durch Komma getrennt")
    p.add_argument("--automatisch", action="store_true",
                   help="die ältesten freigegebenen Entwürfe, höchstens --max")
    p.add_argument("--max", type=int, default=2, help="Höchstzahl bei --automatisch")
    p.add_argument("--probelauf", action="store_true")
    p.add_argument("--ohne-github", action="store_true", help="Pull Requests nicht abfragen (Tests)")
    p.add_argument("--bericht", type=Path, help="Ergebnis zusätzlich als JSON in diese Datei")
    a = p.parse_args()

    wunsch = set() if a.automatisch else {w.strip().removesuffix(".md") for w in a.auswahl.split(",") if w.strip()}
    alle = not wunsch or wunsch == {"alle"}
    eintraege = lokaler_bestand()
    doppelt = {e["pfad"]: (anderer, grund) for e, anderer, grund in doppelungen.bestand_pruefen(eintraege)}
    dateien = sorted(ORDNER.glob("*.md")) if ORDNER.is_dir() else []
    hinweis = ""
    korrekturen: dict[str, str] = {}
    if not a.ohne_github:
        korrekturen, hinweis = offene_korrekturen({d.name for d in dateien})

    veroeffentlicht, uebersprungen, gefunden, bericht = [], [], set(), []
    texte = {datei: datei.read_text(encoding="utf-8") for datei in dateien}

    def erstellt(datei: Path) -> str:
        m = KOPF.match(texte[datei])
        return feld(m.group(1), "erstellt") if m else ""

    # Die ältesten zuerst: Wer am längsten wartet, geht zuerst online.
    for datei in sorted(dateien, key=lambda d: (erstellt(d), d.name)):
        text = texte[datei]
        m = KOPF.match(text)
        if not m:
            uebersprungen.append(f"{datei.name}: kein Dateikopf")
            continue
        kopf = m.group(1)
        kurz, titel, status = feld(kopf, "kurzform"), feld(kopf, "titel"), feld(kopf, "status")
        if not alle and not ({kurz, datei.stem} & wunsch):
            continue
        gefunden |= {kurz, datei.stem}
        if status == "Veröffentlicht":
            continue
        name = f"{titel or datei.name} ({kurz})"
        gruende = []
        todos = len(re.findall(r"(?m)^> TODO", text))
        if todos:
            gruende.append(f"{todos} offene(r) Prüfpunkt(e) – erst auflösen")
        if feld(kopf, "zurueckhalten").lower() in ("ja", "true", "yes"):
            gruende.append("im Dateikopf zurückgehalten (zurueckhalten: ja)")
        pfad = datei.relative_to(WURZEL).as_posix()
        if pfad in doppelt:
            anderer, grund = doppelt[pfad]
            gruende.append(f"Doppelung ({grund}) zu {doppelungen.beschreibung(anderer)}")
        if datei.name in korrekturen:
            gruende.append(korrekturen[datei.name])
        if gruende:
            uebersprungen.append(f"{name}: " + "; ".join(gruende))
            bericht.append({"kurzform": kurz, "datei": datei.name, "ergebnis": "zurückgehalten", "gruende": gruende})
            continue
        if a.automatisch and len(veroeffentlicht) >= a.max:
            bericht.append({"kurzform": kurz, "datei": datei.name, "ergebnis": "wartet"})
            continue
        neuer_kopf = re.sub(r"(?m)^status:.*$", "status: Veröffentlicht", kopf, count=1) \
            if re.search(r"(?m)^status:", kopf) else kopf + "\nstatus: Veröffentlicht"
        if not a.probelauf:
            datei.write_bytes((text[:m.start(1)] + neuer_kopf + text[m.end(1):]).encode("utf-8"))
        veroeffentlicht.append(name)
        bericht.append({"kurzform": kurz, "datei": datei.name, "ergebnis": "veröffentlicht"})

    if not alle:
        for w in sorted(wunsch - gefunden):
            uebersprungen.append(f"{w}: nicht unter den Entwürfen gefunden")

    wartend = sum(1 for b in bericht if b["ergebnis"] == "wartet")
    print(("Würde veröffentlichen" if a.probelauf else "Veröffentlicht") + f" ({len(veroeffentlicht)}):")
    for z in veroeffentlicht:
        print(f"  - {z}")
    if wartend:
        print(f"Warten auf die nächsten Tage (höchstens {a.max} je Lauf): {wartend}")
    if uebersprungen:
        print(f"Zurückgehalten ({len(uebersprungen)}):")
        for z in uebersprungen:
            print(f"  - {z}")
    if hinweis:
        print(f"Hinweis: {hinweis}")
    if a.bericht:
        a.bericht.write_text(json.dumps({"eintraege": bericht, "hinweis": hinweis}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    print(len(veroeffentlicht))
    return 0


if __name__ == "__main__":
    sys.exit(main())
