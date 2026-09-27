#!/usr/bin/env python3
"""Erzeugt das Vorschaubild vorschau.png (1200 × 630) für Open Graph und strukturierte Daten.

Das Bild erscheint, wenn jemand eine Seite von ing-bassam.de bei LinkedIn,
WhatsApp, Xing oder in einer Suchmaschine teilt bzw. anzeigt. Google empfiehlt
für Beiträge ausdrücklich ein Bild in den strukturierten Daten. Farben und
Schriften entsprechen der Website (tools/schriften/).

Aufruf: python tools/vorschaubild.py   (schreibt vorschau.png ins Wurzelverzeichnis)
Benötigt Pillow. Nur bei Änderungen am Erscheinungsbild neu auszuführen.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WURZEL = Path(__file__).resolve().parent.parent
SCHRIFTEN = WURZEL / "tools" / "schriften"
INK, WEISS, GRAU, AKZENT = (10, 18, 29), (237, 239, 242), (174, 182, 194), (242, 107, 42)


def main() -> None:
    b, h = 1200, 630
    bild = Image.new("RGB", (b, h), INK)
    z = ImageDraw.Draw(bild)
    fira = lambda g: ImageFont.truetype(str(SCHRIFTEN / "FiraSans-300.ttf"), g)  # noqa: E731
    titel = lambda g: ImageFont.truetype(str(SCHRIFTEN / "SpaceGrotesk-600.ttf"), g)  # noqa: E731
    text = lambda g: ImageFont.truetype(str(SCHRIFTEN / "Inter-400.ttf"), g)  # noqa: E731

    # Wort-Bild-Marke wie im Kopf der Website
    x, y, s = 90, 90, 120
    z.rounded_rectangle((x, y, x + s, y + s), radius=22, outline=(40, 52, 68), width=3)
    z.text((x + s / 2, y + 52), "BIB", font=fira(46), fill=WEISS, anchor="mm")
    z.line((x + 30, y + 88, x + s - 30, y + 88), fill=AKZENT, width=5)
    z.text((x + s + 36, y + 20), "BIB", font=fira(54), fill=WEISS)
    z.text((x + s + 38, y + 86), "INGENIEURBÜRO FÜR BAUWESEN", font=text(22), fill=GRAU)

    z.text((90, 300), "Baugutachten und Fachwissen", font=titel(64), fill=WEISS)
    z.text((90, 385), "Versicherungs- und Gerichtsgutachten · Beweissicherung · Objektüberwachung",
           font=text(28), fill=GRAU)
    z.line((90, 480, 250, 480), fill=AKZENT, width=6)
    z.text((90, 510), "Berlin · ing-bassam.de", font=text(30), fill=WEISS)
    bild.save(WURZEL / "vorschau.png", optimize=True)
    print("vorschau.png geschrieben")


if __name__ == "__main__":
    main()
