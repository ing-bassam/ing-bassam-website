#!/usr/bin/env python3
"""Entscheidet nach einem gescheiterten Agentenlauf, ob ein zweiter Versuch sinnvoll ist.

Anlass (02.10.2026): Im Fachartikel-Lauf brach Runde 3 („Mängelrüge richtig
formulieren“) nach zehn Zügen ab mit

    API Error: Opus 5's safeguards flagged this message … This sometimes
    happens with safe, normal conversations … Try rephrasing the request in a
    new session or change your model.

Weil die Runden mit fail-fast laufen, fielen die Runden 4 und 5 mit aus. Ein
zweiter Versuch mit einem anderen Modell hätte das Thema sehr wahrscheinlich
geschafft – so wie es die Fehlermeldung selbst empfiehlt.

Ein zweiter Versuch kommt nur in Frage, wenn

  1. der Lauf an genau diesem Fehlalarm des Sicherheitsfilters gescheitert ist.
     Bei anderen Fehlern (Zeitüberschreitung, abgelaufener Zugangsschlüssel,
     Zugriffsfehler) hilft ein zweiter Versuch nicht und kostet nur Kontingent;
  2. der erste Versuch noch nichts veröffentlicht hat – kein erfolgreiches
     „git push“, kein „gh pr create“. Sonst entstünde ein doppelter Zweig oder
     Pull Request.

Ausgabe: zwei Zeilen „zweiter_versuch=true|false“ und „grund=…“, zusätzlich
in $GITHUB_OUTPUT, falls gesetzt. Rückgabewert immer 0.

Aufruf: python tools/zweiter_versuch.py [<pfad zur claude-execution-output.json>]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_bericht import nachrichten  # noqa: E402

FEHLALARM = "safeguards flagged"
VEROEFFENTLICHEN = ("git push", "gh pr create")


def entscheiden(daten) -> tuple[bool, str]:
    liste = nachrichten(daten)
    ergebnis = next((m for m in reversed(liste) if m.get("type") == "result"), {})

    texte = [str(ergebnis.get("result") or "")]
    befehle: dict[str, str] = {}
    gescheitert: set[str] = set()
    for m in liste:
        nachricht = m.get("message")
        if isinstance(nachricht, str):          # z. B. „Claude Code initialized“
            texte.append(nachricht)
            continue
        inhalt = nachricht.get("content") if isinstance(nachricht, dict) else None
        if isinstance(inhalt, str):
            texte.append(inhalt)
            continue
        if not isinstance(inhalt, list):
            continue
        for teil in inhalt:
            if not isinstance(teil, dict):
                continue
            if teil.get("type") == "text":
                texte.append(str(teil.get("text") or ""))
            elif teil.get("type") == "tool_use" and teil.get("name") == "Bash":
                befehle[teil.get("id", "")] = str((teil.get("input") or {}).get("command") or "")
            elif teil.get("type") == "tool_result" and teil.get("is_error"):
                gescheitert.add(teil.get("tool_use_id", ""))

    if not any(FEHLALARM in t for t in texte):
        return False, "kein Fehlalarm des Sicherheitsfilters – ein zweiter Versuch hilft hier nicht"
    veroeffentlicht = [b for i, b in befehle.items()
                       if i not in gescheitert and any(v in b for v in VEROEFFENTLICHEN)]
    if veroeffentlicht:
        return False, ("Fehlalarm des Sicherheitsfilters, aber der erste Versuch hat schon "
                       "veröffentlicht (git push oder Pull Request) – kein zweiter Versuch, "
                       "damit nichts doppelt entsteht")
    zuege = ergebnis.get("num_turns", "?")
    return True, f"Fehlalarm des Sicherheitsfilters nach {zuege} Zügen, noch nichts veröffentlicht"


def main() -> int:
    pfad = Path(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1]
                else Path(os.environ.get("RUNNER_TEMP", ".")) / "claude-execution-output.json")
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8", errors="replace"))
        zweiter, grund = entscheiden(daten)
    except (OSError, json.JSONDecodeError) as fehler:
        zweiter, grund = False, f"Verlauf nicht lesbar ({fehler})"
    zeilen = [f"zweiter_versuch={'true' if zweiter else 'false'}", f"grund={grund}"]
    print("\n".join(zeilen))
    ausgabe = os.environ.get("GITHUB_OUTPUT")
    if ausgabe:
        with open(ausgabe, "a", encoding="utf-8") as f:
            f.write("\n".join(zeilen) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
