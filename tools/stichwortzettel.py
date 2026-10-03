#!/usr/bin/env python3
"""Stichwortzettel für die Videos: Auftrag für den Agenten und Ablage in Notion.

Der Auftraggeber dreht seine Kurzvideos selbst. Zu jedem Beitrag, der gerade
online gegangen ist, schreibt der Agent (Skill /stichwortzettel) die drei
stärksten Kernaussagen mit Fußnote auf einen Zettel; der landet in der
Notion-Liste „Stichwortzettel Videos“, und der Wochenbericht am Freitag listet
die Zettel der Woche – der Drehplan fürs Wochenende.

Befehle (Workflow „Entwürfe veröffentlichen“):
    auftrag --bericht JSON --ordner ORDNER
        liest das Ergebnis von tools/veroeffentlichen.py --bericht, sucht die
        veröffentlichten Beiträge unter entwuerfe/veroeffentlicht/ und schreibt
        den Auftrag für den Agenten (Zeilen „Beitrag:“ und „Ausgabe:“) nach
        $GITHUB_OUTPUT: anzahl, auftrag (mehrzeilig), ordner
    ablegen --bericht JSON --ordner ORDNER
        legt jeden vom Agenten geschriebenen Zettel als Seite in Notion ab
        (tools/trend_notion.py stichwortzettel); Zettel, die es schon gibt,
        bleiben unverändert

Benötigt nur die Standardbibliothek; „ablegen“ braucht NOTION_TOKEN.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

WURZEL = Path(__file__).resolve().parent.parent
VEROEFFENTLICHT = WURZEL / "entwuerfe" / "veroeffentlicht"
BASIS_URL = "https://ing-bassam.de"
HOECHSTENS = 2          # Zettel je Lauf – wie die Veröffentlichung selbst


def format_fuer_notion(format_: str) -> str:
    f = (format_ or "").strip().lower()
    if f in ("rechtsprechung", "urteil verständlich", "urteilsbesprechung"):
        return "Rechtsprechung"
    if f == "vorlage":
        return "Vorlage"
    return "Fachbeitrag"


def veroeffentlichte(bericht: Path) -> list[dict]:
    try:
        daten = json.loads(bericht.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in daten.get("eintraege", []) if e.get("ergebnis") == "veröffentlicht"][:HOECHSTENS]


def beitragsdatei(eintrag: dict) -> Path | None:
    """Die Datei liegt nach dem Seitenbau unter veroeffentlicht/ – mit demselben Namen."""
    direkt = VEROEFFENTLICHT / eintrag.get("datei", "")
    if eintrag.get("datei") and direkt.is_file():
        return direkt
    treffer = sorted(VEROEFFENTLICHT.glob(f"*-{eintrag.get('kurzform', '')}.md")) if eintrag.get("kurzform") else []
    return treffer[0] if treffer else None


def ausgabe(name: str, wert: str) -> None:
    ziel = os.environ.get("GITHUB_OUTPUT")
    if not ziel:
        print(f"{name}={wert}")
        return
    with open(ziel, "a", encoding="utf-8") as f:
        if "\n" in wert:
            f.write(f"{name}<<ENDE_{name}\n{wert}\n" + f"ENDE_{name}\n")
        else:
            f.write(f"{name}={wert}\n")


def auftrag(bericht: Path, ordner: Path) -> int:
    ordner.mkdir(parents=True, exist_ok=True)
    zeilen, anzahl = [], 0
    for e in veroeffentlichte(bericht):
        datei = beitragsdatei(e)
        if not datei:
            print(f"::warning title=Stichwortzettel::Beitrag {e.get('kurzform')} nicht unter veroeffentlicht/ gefunden.")
            continue
        ziel = ordner / f"{e['kurzform']}.md"
        zeilen += [f"Beitrag: {datei.relative_to(WURZEL).as_posix()}", f"Ausgabe: {ziel.as_posix()}", ""]
        anzahl += 1
    ausgabe("anzahl", str(anzahl))
    ausgabe("auftrag", "\n".join(zeilen).strip())
    ausgabe("ordner", ordner.as_posix())
    print(f"Stichwortzettel: {anzahl} Beitrag/Beiträge im Auftrag.")
    return 0


def ablegen(bericht: Path, ordner: Path) -> int:
    from trend_notion import NotionFehler, heute_berlin, stichwortzettel_anlegen
    zeilen = []
    for e in veroeffentlichte(bericht):
        datei = ordner / f"{e['kurzform']}.md"
        if not datei.is_file() or not datei.read_text(encoding="utf-8").strip():
            zeilen.append(f"- {e.get('titel') or e['kurzform']}: kein Zettel entstanden")
            continue
        try:
            adresse = stichwortzettel_anlegen(datei.read_text(encoding="utf-8"), e.get("titel") or e["kurzform"],
                                              f"{BASIS_URL}/fachwissen/{e['kurzform']}/", e["kurzform"],
                                              format_fuer_notion(e.get("format", "")), heute_berlin().isoformat())
        except NotionFehler as fehler:
            zeilen.append(f"- {e.get('titel') or e['kurzform']}: Notion-Fehler – {fehler}")
            continue
        zeilen.append(f"- {e.get('titel') or e['kurzform']}: " + (f"[Zettel in Notion]({adresse})" if adresse
                                                                    else "Zettel gab es schon"))
    text = "## Stichwortzettel für die Videos\n\n" + ("\n".join(zeilen) if zeilen else "_Keine._") + "\n"
    print(text)
    ziel = os.environ.get("GITHUB_STEP_SUMMARY")
    if ziel:
        with open(ziel, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    unter = p.add_subparsers(dest="befehl", required=True)
    for name in ("auftrag", "ablegen"):
        q = unter.add_parser(name)
        q.add_argument("--bericht", type=Path, required=True)
        q.add_argument("--ordner", type=Path, required=True)
    a = p.parse_args()
    return auftrag(a.bericht, a.ordner) if a.befehl == "auftrag" else ablegen(a.bericht, a.ordner)


if __name__ == "__main__":
    sys.exit(main())
