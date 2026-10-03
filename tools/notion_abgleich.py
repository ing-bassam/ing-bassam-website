#!/usr/bin/env python3
"""Hält die drei Notion-Listen auf dem Stand der Website.

Jeder Entwurf trägt im Dateikopf die `notion_id` seines Themas. Daran
erkennt dieses Werkzeug, welche Notion-Seite zu welchem Beitrag gehört, und
setzt dort:

    veröffentlicht   Themenspeicher und Trendthemen: Status „Veröffentlicht“,
                     „Online“ angehakt, „Website-Link“; Vorlagen: Status
                     „Online“ und „Download-Link“ (Adresse der Seite)
    Entwurf          Status „Entwurf“ (Vorlagen: „In Arbeit“), sofern das Thema
                     noch als Idee, Gliederung, Vorschlag oder freigegeben geführt
                     wird; „Entwurf (PR)“, falls leer

Ein Status wird nie zurückgestuft („Fachlich geprüft“ bleibt bis zur
Veröffentlichung), Doppelungen bleiben unberührt. Das Werkzeug darf beliebig
oft laufen: Was schon stimmt, wird nicht angefasst.

Anlass: Notion war am 03.10.2026 veraltet – veröffentlichte Beiträge standen
dort noch als Idee oder Entwurf.

Aufruf:
    python tools/notion_abgleich.py              abgleichen
    python tools/notion_abgleich.py --probelauf  nur anzeigen
Im Protokoll stehen nur die Kurzformen der Beiträge (die sind öffentlich),
keine Notion-Titel. Benötigt NOTION_TOKEN, git und die GitHub-CLI.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bestand  # noqa: E402

OFFEN = {"Idee", "Gliederung", "Vorschlag", "Freigegeben"}


def eigenschaft(seite: dict, name: str) -> dict:
    return (seite.get("properties") or {}).get(name) or {}


def aenderungen(seite: dict, liste: str, eintrag: dict) -> dict:
    """Die nötigen Änderungen an einer Notion-Seite für ihren Beitrag – leer, wenn alles stimmt."""
    status = (eigenschaft(seite, "Status").get("select") or {}).get("name", "")
    if status == "Doppelung":
        return {}
    neu: dict = {}
    if eintrag["status"] == "veröffentlicht":
        if liste == "vorlagen":
            if status != "Online":
                neu["Status"] = {"select": {"name": "Online"}}
            if eintrag["link"] and eigenschaft(seite, "Download-Link").get("url") != eintrag["link"]:
                neu["Download-Link"] = {"url": eintrag["link"]}
        else:
            if status != "Veröffentlicht":
                neu["Status"] = {"select": {"name": "Veröffentlicht"}}
            if not eigenschaft(seite, "Online").get("checkbox"):
                neu["Online"] = {"checkbox": True}
            if eintrag["link"] and eigenschaft(seite, "Website-Link").get("url") != eintrag["link"]:
                neu["Website-Link"] = {"url": eintrag["link"]}
        return neu
    if status in OFFEN:
        neu["Status"] = {"select": {"name": "In Arbeit" if liste == "vorlagen" else "Entwurf"}}
    if liste != "vorlagen" and eintrag.get("pr_url") and not eigenschaft(seite, "Entwurf (PR)").get("url"):
        neu["Entwurf (PR)"] = {"url": eintrag["pr_url"]}
    return neu


def abgleichen(eintraege: list[dict], seiten: dict[str, tuple[str, dict]], senden=None) -> list[str]:
    """Gleicht ab; Ergebnis: Protokollzeilen (Kurzform und Änderung). `seiten`: notion_id → (Liste, Seite)."""
    zeilen = []
    # Veröffentlicht vor Entwurf, falls es zu einer Seite beides gibt (etwa eine Überarbeitung im Pull Request).
    for e in sorted(eintraege, key=lambda e: e["status"] != "veröffentlicht"):
        if not e.get("notion_id") or e["notion_id"] not in seiten:
            continue
        liste, seite = seiten.pop(e["notion_id"])
        neu = aenderungen(seite, liste, e)
        if not neu:
            continue
        if senden:
            senden("PATCH", f"/pages/{seite['id']}", {"properties": neu})
        felder = ", ".join(f"{k} → {v.get('select', {}).get('name') if 'select' in v else 'gesetzt'}"
                           for k, v in neu.items())
        zeilen.append(f"{e['kurzform']} ({liste}): {felder}")
    return zeilen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--probelauf", action="store_true", help="nichts ändern, nur anzeigen")
    a = p.parse_args()
    from trend_notion import NotionFehler, abfragen, anfrage
    b = bestand.laden(notion=False)
    for w in b["warnungen"]:
        print(f"::warning title=Notion-Abgleich::{w}")
    try:
        seiten = {}
        for liste, (quelle, _, _) in bestand.NOTION_LISTEN.items():
            for seite in abfragen(quelle):
                seiten[bestand.normiere_id(seite.get("id", ""))] = (liste, seite)
        zeilen = abgleichen(b["eintraege"], seiten, None if a.probelauf else anfrage)
    except NotionFehler as fehler:
        print(f"::error title=Notion-Abgleich::{fehler}")
        return 1
    print(("Würde ändern" if a.probelauf else "Geändert") + f": {len(zeilen)} Notion-Seite(n)")
    for z in zeilen:
        print(f"  - {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
