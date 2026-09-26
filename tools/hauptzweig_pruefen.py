#!/usr/bin/env python3
"""Prüft, ob während eines Agentenlaufs etwas DIREKT auf den Hauptzweig geschrieben wurde.

Ein Agent darf nur auf seinem eigenen Zweig arbeiten und einen Pull Request
öffnen – nie selbst auf den Hauptzweig schieben. Dieses Werkzeug geht die
direkte Commit-Kette des Hauptzweigs (jeweils erster Elternteil) vom neuen
Stand zurück bis zum Stand bei Laufbeginn und bewertet jeden Commit:

    unbedenklich   Merge über GitHub (Committer „GitHub“) – die Commits eines
                   gemergten Pull Requests hängen am zweiten Elternteil und
                   werden deshalb gar nicht betrachtet
                   Seitenbau des Workflows „Fachwissen-Seiten bauen“
                   (github-actions[bot], „Fachwissen-Seiten neu gebaut“)
                   Commits eines Menschen (z. B. Bearbeitung im Browser)
    verdächtig     jeder andere Bot-Commit, insbesondere claude[bot]

Anlass: Die frühere Prüfung sah nur den letzten Commit an und wertete jeden
Bot als Verstoß. Merged der Auftraggeber während eines Laufs einen Pull
Request, schreibt der Seitenbau danach als Bot – das brach am 26.09.2026 einen
Lauf mit drei Runden nach Runde 1 ab.

Aufruf: python tools/hauptzweig_pruefen.py <sha_vorher> <sha_nachher> [--titel Vorlagen]
Rückgabewert 1 bei einem verdächtigen Commit, sonst 0. Ist GitHub nicht
erreichbar, gibt es nur einen Hinweis (0) – die Prüfung ist eine Absicherung,
kein Grund, einen sonst gelungenen Lauf scheitern zu lassen.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ERLAUBTE_BOT_COMMITS = {"Fachwissen-Seiten neu gebaut"}
HOECHSTENS = 60


def commit_lesen(repo: str, sha: str) -> dict:
    r = subprocess.run(["gh", "api", f"repos/{repo}/commits/{sha}"], capture_output=True,
                       text=True, encoding="utf-8", timeout=60)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:200])
    return json.loads(r.stdout)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("vorher")
    p.add_argument("nachher")
    p.add_argument("--titel", default="Hauptzweig")
    a = p.parse_args()
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not a.nachher or a.nachher == a.vorher:
        print("Hauptzweig unverändert.")
        return 0

    verdacht, geprueft, sha = [], [], a.nachher
    try:
        while sha and sha != a.vorher and len(geprueft) < HOECHSTENS:
            c = commit_lesen(repo, sha)
            autor = (c.get("commit", {}).get("author") or {}).get("name", "")
            committer = (c.get("commit", {}).get("committer") or {}).get("name", "")
            nachricht = (c.get("commit", {}).get("message") or "").splitlines()[0] if c.get("commit") else ""
            wer = f"{autor} {committer}".lower()
            eintrag = f"{sha[:7]} {autor}/{committer}: {nachricht[:70]}"
            geprueft.append(eintrag)
            if "claude" in wer or ("[bot]" in wer and nachricht not in ERLAUBTE_BOT_COMMITS):
                verdacht.append(eintrag)
            eltern = c.get("parents") or []
            sha = eltern[0]["sha"] if eltern else ""
    except (RuntimeError, subprocess.SubprocessError, OSError, json.JSONDecodeError) as fehler:
        print(f"::notice title={a.titel}::Hauptzweig hat sich geändert; die Prüfung der Commits war nicht möglich ({fehler}).")
        return 0

    if verdacht:
        print(f"::error title={a.titel}::Während des Laufs wurde direkt auf den Hauptzweig geschrieben: "
              + "; ".join(verdacht)
              + ". Ein Agent darf nur über einen Pull Request arbeiten – bitte die Commits prüfen und ggf. zurücknehmen.")
        return 1
    print(f"::notice title={a.titel}::Der Hauptzweig hat sich während des Laufs geändert – nur durch Merges, "
          f"Seitenbau oder eigene Änderungen ({len(geprueft)} Commit(s)), unbedenklich.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
