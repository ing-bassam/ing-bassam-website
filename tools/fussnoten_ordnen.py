#!/usr/bin/env python3
"""Nummeriert die Fußnoten eines Entwurfs neu und entfernt unbenutzte Einträge.

Streicht die Schlussprüfung einen unbelegten Satz, verliert dessen Fußnote oft
ihre letzte Marke im Text. Der Seitenbauer meldet dann „Fußnoteneinträge ohne
Marke“ und nach dem Entfernen „nicht lückenlos nummeriert“. Das Umnummerieren
von Hand ist fehleranfällig; dieses Skript macht es mechanisch:

- Reihenfolge nach dem ersten Auftreten im Text (1, 2, 3 …),
- Einträge ohne Marke im Text werden entfernt,
- das Feld ``fussnoten`` im Dateikopf wird angepasst.

Aufruf:
    python tools/fussnoten_ordnen.py <entwurf.md>

Rückgabewert 0 bei Erfolg (auch wenn nichts zu tun war), 2, wenn eine Marke im
Text keinen Eintrag hat – das kann das Skript nicht beheben.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ABSCHNITT = re.compile(r"^## Quellen und Fußnoten[ \t]*$", re.M)
MARKE = re.compile(r"\[\^(\d+)\](?!:)")
EINTRAG = re.compile(r"^\[\^(\d+)\]:[ \t]?(.*)$")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pfad = Path(sys.argv[1])
    text = pfad.read_text(encoding="utf-8")
    teilung = ABSCHNITT.search(text)
    if not teilung:
        print(f"FEHLER: {pfad.name} hat keinen Abschnitt „Quellen und Fußnoten“.")
        return 2

    vorne, hinten = text[:teilung.end()], text[teilung.end():]

    # Einträge einlesen; eingerückte Folgezeilen gehören zum Eintrag davor.
    eintraege: dict[str, list[str]] = {}
    reihenfolge_alt: list[str] = []
    rest: list[str] = []
    letzte = None
    for zeile in hinten.split("\n"):
        treffer = EINTRAG.match(zeile)
        if treffer:
            letzte = treffer.group(1)
            eintraege[letzte] = [treffer.group(2)]
            reihenfolge_alt.append(letzte)
        elif letzte is not None and zeile.startswith("    "):
            eintraege[letzte].append(zeile)
        elif zeile.strip() or (letzte is None and not reihenfolge_alt):
            rest.append(zeile)
            letzte = None

    kopf_ende = 0
    if text.startswith("---"):
        kopf_ende = text.index("---", 3) + 3
    neu_nummer: dict[str, str] = {}
    for treffer in MARKE.finditer(vorne, kopf_ende):
        alt = treffer.group(1)
        if alt not in neu_nummer:
            neu_nummer[alt] = str(len(neu_nummer) + 1)

    fehlend = [alt for alt in neu_nummer if alt not in eintraege]
    if fehlend:
        print("FEHLER: Marken ohne Eintrag: " + ", ".join(f"[^{n}]" for n in fehlend))
        return 2

    entfernt = [alt for alt in reihenfolge_alt if alt not in neu_nummer]
    geaendert = {alt: neu for alt, neu in neu_nummer.items() if alt != neu}
    if not entfernt and not geaendert and reihenfolge_alt == list(neu_nummer):
        print(f"{pfad.name}: Fußnoten sind bereits lückenlos und in Reihenfolge ({len(neu_nummer)}).")
        return 0

    vorne = vorne[:kopf_ende] + MARKE.sub(
        lambda t: f"[^{neu_nummer[t.group(1)]}]", vorne[kopf_ende:])
    liste = []
    for alt, neu in sorted(neu_nummer.items(), key=lambda paar: int(paar[1])):
        erste, *folgende = eintraege[alt]
        liste.append(f"[^{neu}]: {erste}")
        liste.extend(folgende)
    davor = "\n".join(z for z in rest if z.strip())
    neu_hinten = "\n\n" + (davor + "\n\n" if davor else "") + "\n".join(liste) + "\n"
    ergebnis = vorne + neu_hinten

    if kopf_ende:
        ergebnis = re.sub(r"^fussnoten:.*$", f"fussnoten: {len(neu_nummer)}",
                          ergebnis[:kopf_ende], count=1, flags=re.M) + ergebnis[kopf_ende:]

    pfad.write_bytes(ergebnis.encode("utf-8"))
    print(f"{pfad.name}: {len(reihenfolge_alt)} → {len(neu_nummer)} Fußnoten.")
    if entfernt:
        print("Entfernt (keine Marke mehr im Text): " + ", ".join(f"[^{n}]" for n in entfernt))
    if geaendert:
        print("Umnummeriert: " + ", ".join(f"[^{a}] → [^{n}]" for a, n in geaendert.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
