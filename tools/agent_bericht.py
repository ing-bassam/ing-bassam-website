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
    3. die letzten Werkzeugfehler (Fehlermeldungen, gekürzt)

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


def kurz(text: str, laenge: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def eingabe_beschreiben(eingabe) -> str:
    if isinstance(eingabe, dict):
        for schluessel in ("command", "file_path", "path", "pattern", "url", "query"):
            if eingabe.get(schluessel):
                return f"{schluessel}: {eingabe[schluessel]}"
        return json.dumps(eingabe, ensure_ascii=False)
    return str(eingabe)


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
                werkzeuge[teil.get("id", "")] = f"{teil.get('name', '?')} ({kurz(eingabe_beschreiben(teil.get('input')), 160)})"
            if teil.get("type") == "tool_result" and teil.get("is_error"):
                text = teil.get("content")
                if isinstance(text, list):
                    text = " ".join(t.get("text", "") for t in text if isinstance(t, dict))
                fehler.append(f"{werkzeuge.get(teil.get('tool_use_id', ''), '?')} → {kurz(text or '', 240)}")

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
