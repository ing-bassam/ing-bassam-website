#!/usr/bin/env python3
"""Findet den Pull Request, den DIESER Agentenlauf angelegt hat.

Mehrere Agenten dürfen gleichzeitig laufen (Fachartikel, Urteilsbesprechung,
Urteil verständlich, Vorlagen). Zweigname und Anlagezeit allein reichen dann
nicht, um den eigenen Entwurf zu erkennen: Ein gleichzeitig laufender Agent
legt ebenfalls einen Zweig entwurf/… an. Dieses Werkzeug liest deshalb die
Entwurfsdatei jedes in Frage kommenden Pull Requests und prüft ihren Kopf:

    format      gehört zum Agenten (z. B. „Rechtsprechung“, „Urteil verständlich“,
                „Vorlage“) bzw. gehört NICHT zu einem anderen
    notion_id   stimmt mit der Notion-Seite des Laufs überein (falls bekannt);
                ein Entwurf mit einer ANDEREN Notion-Seite gehört nie dazu

Aufruf:
    python tools/eigener_entwurf.py --seit 2026-09-25T17:23:00Z --format "Rechtsprechung"
    python tools/eigener_entwurf.py --seit … --ohne-format "Rechtsprechung,Urteil verständlich,Vorlage" --notion-id <id>

Ausgabe (--ausgabe):
    kurz    „<Nummer> <Zweig>“ des neuesten passenden Pull Requests (Standard)
    tab     „<Nummer>\\t<Zweig>\\t<URL>\\t<Entwurfsdatei>“
    url     nur die Adresse
    json    {"number", "url", "title", "headRefName", "entwurf"}
    anzahl  Zahl der passenden Pull Requests
Kein Treffer: leere Ausgabe (bei „anzahl“: 0). Rückgabewert 2, wenn GitHub
nicht erreichbar ist – das ist etwas anderes als „kein Entwurf“.
Benötigt nur die Standardbibliothek und die GitHub-CLI (GH_TOKEN).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse


def gh(*args: str) -> str:
    fehler = ""
    for versuch in range(3):
        r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            return r.stdout
        fehler = r.stderr.strip()
        time.sleep(3 * (versuch + 1))
    raise RuntimeError(fehler[:300])


def liste(wert: str) -> set[str]:
    return {w.strip().lower() for w in (wert or "").split(",") if w.strip()}


def kopf(text: str) -> dict[str, str]:
    """Die einfachen Felder des YAML-Kopfs – ohne Abhängigkeit von PyYAML."""
    m = re.match(r"﻿?---\s*\n(.*?)\n---\s*(\n|$)", text, flags=re.S)
    felder: dict[str, str] = {}
    for zeile in (m.group(1) if m else "").splitlines():
        t = re.match(r"([A-Za-z_]+):\s*(.*)$", zeile)
        if t:
            felder[t.group(1).lower()] = t.group(2).strip().strip('"').strip("'").strip()
    return felder


def normiere_id(wert: str) -> str:
    return re.sub(r"[^0-9a-f]", "", (wert or "").lower())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--seit", required=True, help="Startzeit des Laufs (ISO 8601, UTC)")
    p.add_argument("--format", default="", help="erlaubte Formate, kommagetrennt")
    p.add_argument("--ohne-format", default="", help="ausgeschlossene Formate, kommagetrennt")
    p.add_argument("--notion-id", default="", help="Notion-Seite dieses Laufs")
    p.add_argument("--ausgabe", default="kurz", choices=["kurz", "tab", "url", "json", "anzahl"])
    a = p.parse_args()

    if not a.seit.strip():
        print("FEHLER: --seit ist leer", file=sys.stderr)
        return 2
    erlaubt, verboten, eigene_id = liste(a.format), liste(a.ohne_format), normiere_id(a.notion_id)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    try:
        if not repo:
            repo = gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()
        prs = json.loads(gh("pr", "list", "--repo", repo, "--state", "all", "--limit", "100",
                            "--json", "number,url,title,headRefName,createdAt,files"))
    except (RuntimeError, json.JSONDecodeError) as e:
        print(f"FEHLER: Pull Requests nicht abrufbar – {e}", file=sys.stderr)
        return 2

    treffer = []
    for pr in prs:
        if pr.get("createdAt", "") < a.seit:
            continue
        entwuerfe = [f["path"] for f in pr.get("files") or []
                     if f["path"].startswith("entwuerfe/") and f["path"].endswith(".md")]
        if not entwuerfe:
            continue
        pfad = entwuerfe[0]
        try:
            text = gh("api", "-H", "Accept: application/vnd.github.raw+json",
                      f"repos/{repo}/contents/{urllib.parse.quote(pfad)}?ref=refs/pull/{pr['number']}/head")
        except RuntimeError as e:
            print(f"WARNUNG: #{pr['number']}: Entwurf nicht lesbar – {e}", file=sys.stderr)
            continue
        f = kopf(text)
        fmt = f.get("format", "").lower()
        if erlaubt and fmt not in erlaubt:
            continue
        if verboten and fmt in verboten:
            continue
        fremde_id = normiere_id(f.get("notion_id", ""))
        if eigene_id and fremde_id and fremde_id != eigene_id:
            continue
        pr["entwurf"] = pfad
        pr["_passt_id"] = bool(eigene_id and fremde_id == eigene_id)
        treffer.append(pr)

    if a.ausgabe == "anzahl":
        print(len(treffer))
        return 0
    if not treffer:
        return 0
    # Genaue Notion-Übereinstimmung zuerst, sonst der neueste.
    treffer.sort(key=lambda t: (t["_passt_id"], t["createdAt"]))
    t = treffer[-1]
    if a.ausgabe == "kurz":
        print(f"{t['number']} {t['headRefName']}")
    elif a.ausgabe == "tab":
        print(f"{t['number']}\t{t['headRefName']}\t{t['url']}\t{t['entwurf']}")
    elif a.ausgabe == "url":
        print(t["url"])
    else:
        print(json.dumps({k: t[k] for k in ("number", "url", "title", "headRefName", "entwurf")},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
