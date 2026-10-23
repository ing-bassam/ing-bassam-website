#!/usr/bin/env python3
"""Zeigt nach einem Agentenlauf, was der Agent gemeldet hat und woran er hing.

Die Claude-Aktion schreibt den vollständigen Verlauf nach
$RUNNER_TEMP/claude-execution-output.json, zeigt im Protokoll aber nur
Kennzahlen (Züge, Kosten, Zahl der abgelehnten Berechtigungen). Scheitert ein
Lauf still – der Agent meldet Erfolg, es entsteht aber kein Pull Request –,
fehlt damit jeder Hinweis auf den Grund. Dieses Werkzeug liest die Datei und
gibt drei Dinge aus:

    1. die Abschlussmeldung des Agenten (ERGEBNIS-Block), gekürzt
    2. abgelehnte Berechtigungen: welches Werkzeug, welcher Befehl
    3. die letzten Werkzeugfehler (Fehlermeldungen, gekürzt – ohne den Text,
       den Edit oder Write mitmelden, ohne Befehlsargumente oder
       Suchbegriffe und von tools/wortgleich_pruefen.py nur Rückgabewert und
       „treffer=…“, nie Werk oder Seite: Das Protokoll ist öffentlich)

Jede Zeile beginnt mit „| “, damit der Runner nichts davon als
Workflow-Befehl auswertet. Die Ausgabe geht ins Protokoll und – falls
gesetzt – in die Job-Zusammenfassung ($GITHUB_STEP_SUMMARY). Inhalte aus der
Auftragsdatei (Notion-Notizen) werden nicht ausgegeben.

Aufruf: python tools/agent_bericht.py [<pfad zur execution-output.json>] [--titel „…“]
        python tools/agent_bericht.py [<pfad>] --nur-ergebnis >> "$GITHUB_OUTPUT"
Mit --nur-ergebnis gibt es nur zwei Zeilen für die folgenden Schritte aus:
„ergebnis=<Wert aus dem ERGEBNIS-Block>“ (z. B. OK, DUPLIKAT, ABBRUCH; leer, wenn
keiner da ist) und „grund=<Grund-Zeile, einzeilig>“. Der Grund kann Titel
nennen und gehört deshalb nicht ins öffentliche Protokoll.
Rückgabewert immer 0 – das Werkzeug erklärt, es entscheidet nichts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# Protokoll und Job-Zusammenfassung sind öffentlich. Werkzeuge, die Text schreiben oder
# ersetzen, melden bei einem Fehler den gesuchten Text mit („String: …“) – er kann eine
# Buchpassage sein, die der Agent gerade umformulieren wollte. Deshalb erscheinen von
# Fehlern nur Werkzeug und Fehlerart, von Befehlen nur das Programm und von Suchen nie der
# Suchbegriff.
TEXTWERKZEUGE = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
TEXT_IM_FEHLER = re.compile(r"\b(?:String|old_string|new_string|content)\s*:", re.I)
# Befehle, deren Ausgabe nie ins Protokoll kommt: Mit Treffern endet die Prüfung auf wörtliche
# Übernahmen mit Rückgabewert 1 (für den Agenten ein Werkzeugfehler), und mit --intern nennt sie
# Werk und Seite – das dient nur seiner eigenen Überarbeitung. Gezeigt werden nur Rückgabewert
# und letzte Zeile (treffer=…).
STILLE_BEFEHLE = ("wortgleich_pruefen.py",)


def kurz(text: str, laenge: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def befehl_kurz(befehl: str) -> str:
    """Nur das Programm (bei python, node, git, gh auch Skript bzw. Unterbefehl), ohne Argumente."""
    teile = str(befehl).split()
    if not teile:
        return ""
    zahl = 2 if teile[0] in ("python", "python3", "node", "bash", "sh", "git", "gh") else 1
    if teile[0] == "gh":
        zahl = 3
    return " ".join(teile[:zahl]) + (" …" if len(teile) > zahl else "")


def eingabe_beschreiben(eingabe) -> str:
    if isinstance(eingabe, dict):
        if eingabe.get("command"):
            return f"command: {befehl_kurz(eingabe['command'])}"
        for schluessel in ("file_path", "path", "url"):
            if eingabe.get(schluessel):
                return f"{schluessel}: {eingabe[schluessel]}"
        if eingabe.get("pattern") or eingabe.get("query"):
            return "Suche (Suchbegriff nicht ausgegeben)"
        return "Eingabe mit " + ", ".join(sorted(map(str, eingabe))) if eingabe else "ohne Eingabe"
    return "Eingabe nicht ausgegeben"


def fehler_beschreiben(werkzeug: str, text: str, befehl: str = "") -> str:
    """Fehlermeldung ohne mitgelieferten Text: bis „String:“, bei Schreibwerkzeugen nur die erste Zeile,
    bei der Prüfung auf wörtliche Übernahmen nur Rückgabewert und „treffer=…“."""
    if any(teil in str(befehl) for teil in STILLE_BEFEHLE):
        zeilen = str(text).splitlines()
        code = next((z.strip() for z in zeilen if re.fullmatch(r"\s*Exit code \d+\s*", z)), "")
        schluss = next((z.strip() for z in reversed(zeilen) if re.fullmatch(r"\s*treffer=[\w-]+\s*", z)), "")
        return " · ".join(filter(None, [code, schluss, "Ausgabe nicht gezeigt"]))
    text = TEXT_IM_FEHLER.split(str(text), maxsplit=1)[0].strip()
    if werkzeug in TEXTWERKZEUGE:
        text = text.splitlines()[0] if text else ""
    return kurz(text, 240)


def nachrichten(daten) -> list[dict]:
    if isinstance(daten, list):
        return [d for d in daten if isinstance(d, dict)]
    if isinstance(daten, dict):
        for schluessel in ("messages", "log", "entries"):
            if isinstance(daten.get(schluessel), list):
                return daten[schluessel]
        return [daten]
    return []


def abschlussmeldung(liste: list[dict]) -> str:
    """Die Abschlussmeldung: das Ergebnis des Laufs oder die letzte Textnachricht des Agenten."""
    ergebnis = next((m for m in reversed(liste) if m.get("type") == "result"), {})
    letzter_text = ""
    for m in liste:
        nachricht = m.get("message")
        inhalt = nachricht.get("content") if isinstance(nachricht, dict) else None
        for teil in inhalt if isinstance(inhalt, list) else []:
            if (isinstance(teil, dict) and m.get("type") == "assistant" and teil.get("type") == "text"
                    and teil.get("text", "").strip()):
                letzter_text = teil["text"]
    return ergebnis.get("result") or letzter_text or ""


def ergebnis_block(meldung: str) -> tuple[str, str]:
    """(Wert, Grund) aus dem ERGEBNIS-Block der Abschlussmeldung, etwa („DUPLIKAT“,
    „gleiche Kernfrage wie …“). Ohne Block: („“, „“). Es gilt der letzte Block."""
    werte = re.findall(r"(?m)^\W{0,4}ERGEBNIS:\s*\**\s*([A-ZÄÖÜ][A-ZÄÖÜ ]*[A-ZÄÖÜ])", meldung)
    if not werte:
        return "", ""
    rest = meldung[meldung.rfind("ERGEBNIS:"):]
    grund = re.search(r"(?m)^\W{0,4}Grund:\s*\**\s*(.+)$", rest)
    return werte[-1].strip(), " ".join((grund.group(1) if grund else "").replace("*", "").split())[:400]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("datei", nargs="?", default="")
    p.add_argument("--titel", default="Abschlussmeldung des Agenten")
    p.add_argument("--nur-ergebnis", action="store_true",
                   help="nur ergebnis=… und grund=… ausgeben (für $GITHUB_OUTPUT)")
    a = p.parse_args()

    pfad = Path(a.datei or Path(os.environ.get("RUNNER_TEMP", ".")) / "claude-execution-output.json")
    if a.nur_ergebnis:
        try:
            meldung = abschlussmeldung(nachrichten(json.loads(pfad.read_text(encoding="utf-8", errors="replace"))))
        except (OSError, json.JSONDecodeError):
            meldung = ""
        wert, grund = ergebnis_block(meldung)
        print(f"ergebnis={wert}")
        print(f"grund={grund}")
        return 0
    zeilen: list[str] = [f"## {a.titel}", ""]
    if not pfad.is_file():
        zeilen.append(f"Kein Verlauf gefunden ({pfad.name}) – der Agent ist vermutlich nicht gestartet.")
        ausgeben(zeilen)
        return 0
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError as fehler:
        zeilen.append(f"Verlauf nicht lesbar: {fehler}")
        ausgeben(zeilen)
        return 0

    liste = nachrichten(daten)
    ergebnis = next((m for m in reversed(liste) if m.get("type") == "result"), {})
    letzter_text = ""
    werkzeuge: dict[str, str] = {}
    namen: dict[str, str] = {}
    befehle: dict[str, str] = {}
    fehler: list[str] = []
    for m in liste:
        # Nicht jeder Eintrag trägt ein Nachrichtenobjekt: Die Startmeldung hat
        # „message“: „Claude Code initialized“ als Text. Daran stürzte dieses
        # Werkzeug am 02.10.2026 ab (Urteil verständlich, Runde 1).
        nachricht = m.get("message")
        inhalt = nachricht.get("content") if isinstance(nachricht, dict) else None
        if not isinstance(inhalt, list):
            continue
        for teil in inhalt:
            if not isinstance(teil, dict):
                continue
            if m.get("type") == "assistant" and teil.get("type") == "text" and teil.get("text", "").strip():
                letzter_text = teil["text"]
            if teil.get("type") == "tool_use":
                namen[teil.get("id", "")] = str(teil.get("name", "?"))
                eingabe = teil.get("input")
                befehle[teil.get("id", "")] = str(eingabe.get("command") or "") if isinstance(eingabe, dict) else ""
                werkzeuge[teil.get("id", "")] = f"{teil.get('name', '?')} ({kurz(eingabe_beschreiben(eingabe), 160)})"
            if teil.get("type") == "tool_result" and teil.get("is_error"):
                text = teil.get("content")
                if isinstance(text, list):
                    text = "\n".join(t.get("text", "") for t in text if isinstance(t, dict))
                kennung = teil.get("tool_use_id", "")
                fehler.append(f"{werkzeuge.get(kennung, '?')} → "
                              f"{fehler_beschreiben(namen.get(kennung, '?'), text or '', befehle.get(kennung, ''))}")

    meldung = ergebnis.get("result") or letzter_text or "(keine Abschlussmeldung im Verlauf)"
    zeilen += [f"Züge: {ergebnis.get('num_turns', '?')} · Ende: {ergebnis.get('subtype', '?')}"
               f"{' · mit Fehler' if ergebnis.get('is_error') else ''}", "",
               "**Abschlussmeldung (gekürzt):**", ""]
    zeilen += [kurz(z, 300) for z in meldung.strip().splitlines()[-40:] if z.strip()]

    abgelehnt = ergebnis.get("permission_denials") or []
    zeilen += ["", f"**Abgelehnte Berechtigungen: {len(abgelehnt)}**"]
    for d in abgelehnt[:10]:
        zeilen.append(f"- {d.get('tool_name', '?')}: {kurz(eingabe_beschreiben(d.get('tool_input')), 240)}")

    zeilen += ["", f"**Werkzeugfehler: {len(fehler)}** (die letzten fünf)"]
    zeilen += [f"- {f}" for f in fehler[-5:]]
    ausgeben(zeilen)
    return 0


def ausgeben(zeilen: list[str]) -> None:
    for z in zeilen:
        print("| " + z)
    zusammenfassung = os.environ.get("GITHUB_STEP_SUMMARY")
    if zusammenfassung:
        with open(zusammenfassung, "a", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n\n")


if __name__ == "__main__":
    sys.exit(main())
