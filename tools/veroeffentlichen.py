#!/usr/bin/env python3
"""Setzt Entwürfe in entwuerfe/entwurf/ auf „Veröffentlicht“ – alle oder eine Auswahl.

Wird vom Workflow „Entwürfe veröffentlichen“ aufgerufen (ein Klick unter
Actions). Geändert wird nur die Zeile `status:` im Dateikopf; alles andere
(Einsortieren nach veroeffentlicht/, Seiten, Sitemap, llms.txt) erledigt
danach der Seitenbauer.

Nicht veröffentlicht werden – mit Meldung – Entwürfe mit offenen Prüfpunkten
(`> TODO`): Der Seitenbauer würde sie ohnehin gesperrt lassen und den Lauf als
Fehler melden.

Aufruf:
    python tools/veroeffentlichen.py                       alle Entwürfe
    python tools/veroeffentlichen.py --auswahl kurz1,kurz2 nur diese (Kurzform oder Dateiname)
    python tools/veroeffentlichen.py --probelauf           nur anzeigen, nichts ändern

Letzte Ausgabezeile: Zahl der veröffentlichten Entwürfe (für den Workflow).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ORDNER = WURZEL / "entwuerfe" / "entwurf"
KOPF = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)


def feld(kopf: str, name: str) -> str:
    m = re.search(rf"(?m)^{name}:\s*(.*?)\s*$", kopf)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--auswahl", default="alle",
                   help="„alle“ oder Kurzformen bzw. Dateinamen, durch Komma getrennt")
    p.add_argument("--probelauf", action="store_true")
    a = p.parse_args()

    wunsch = {w.strip().removesuffix(".md") for w in a.auswahl.split(",") if w.strip()}
    alle = not wunsch or wunsch == {"alle"}
    veroeffentlicht, uebersprungen, gefunden = [], [], set()

    for datei in sorted(ORDNER.glob("*.md")) if ORDNER.is_dir() else []:
        text = datei.read_text(encoding="utf-8")
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
        todos = len(re.findall(r"(?m)^> TODO", text))
        if todos:
            uebersprungen.append(f"{titel or datei.name}: {todos} offene(r) Prüfpunkt(e) – erst auflösen")
            continue
        neuer_kopf = re.sub(r"(?m)^status:.*$", "status: Veröffentlicht", kopf, count=1) \
            if re.search(r"(?m)^status:", kopf) else kopf + "\nstatus: Veröffentlicht"
        if not a.probelauf:
            datei.write_bytes((text[:m.start(1)] + neuer_kopf + text[m.end(1):]).encode("utf-8"))
        veroeffentlicht.append(f"{titel or datei.name} ({kurz})")

    if not alle:
        for w in sorted(wunsch - gefunden):
            uebersprungen.append(f"{w}: nicht unter den Entwürfen gefunden")

    print(("Würde veröffentlichen" if a.probelauf else "Veröffentlicht") + f" ({len(veroeffentlicht)}):")
    for z in veroeffentlicht:
        print(f"  - {z}")
    if uebersprungen:
        print(f"Nicht veröffentlicht ({len(uebersprungen)}):")
        for z in uebersprungen:
            print(f"  - {z}")
    print(len(veroeffentlicht))
    return 0


if __name__ == "__main__":
    sys.exit(main())
