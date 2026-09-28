#!/usr/bin/env python3
"""Erzeugt die Website-Icons (Favicon) als Dateien im Wurzelverzeichnis.

Warum Dateien: Bis zum 28.09.2026 stand das Icon nur als data-URL im
Seitencode. Browser zeigen das an, Google aber nicht – Google holt das Symbol
neben dem Suchergebnis als eigene Datei ab (Standard: /favicon.ico), und die
gab es nicht. Deshalb erschien dort ein grauer Globus.

Googles Vorgaben: quadratisch, Kantenlänge ein Vielfaches von 48 Pixeln,
unter einer festen, abrufbaren Adresse. Erzeugt werden:

    favicon.ico           16, 32 und 48 Pixel in einer Datei (Standardadresse)
    favicon.svg           Vektor, gestochen scharf in jedem Browser
    favicon-192.png       192 × 192 (4 × 48) – für Google und Android
    apple-touch-icon.png  180 × 180 – Symbol auf dem iPhone-Startbildschirm

Aufruf: python tools/icons_bauen.py   (nur bei Änderungen am Logo neu auszuführen)
Benötigt Pillow und die Schrift aus tools/schriften/.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WURZEL = Path(__file__).resolve().parent.parent
SCHRIFT = WURZEL / "tools" / "schriften" / "FiraSans-300.ttf"
INK, WEISS, AKZENT = (10, 18, 29), (255, 255, 255), (242, 107, 42)

# Dasselbe Zeichen wie bisher im Seitencode (dunkles Quadrat, „BIB“, orangefarbene Linie)
SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0a121d"/><path d="M16 46h32" stroke="#f26b2a" stroke-width="3"/><text x="32" y="38" text-anchor="middle" font-family="'Fira Sans',Arial,sans-serif" font-size="22" font-weight="300" fill="#ffffff">BIB</text></svg>
"""


def zeichnen(kante: int, abgerundet: bool = True) -> Image.Image:
    """Das Zeichen in hoher Auflösung zeichnen und auf die Zielgröße verkleinern (scharfe Kanten)."""
    g = 512
    f = g / 64
    bild = Image.new("RGBA", (g, g), (0, 0, 0, 0))
    z = ImageDraw.Draw(bild)
    if abgerundet:
        z.rounded_rectangle((0, 0, g - 1, g - 1), radius=int(12 * f), fill=INK)
    else:
        z.rectangle((0, 0, g, g), fill=INK)       # iOS rundet selbst ab
    z.line((16 * f, 46 * f, 48 * f, 46 * f), fill=AKZENT, width=int(3 * f))
    z.text((32 * f, 38 * f), "BIB", font=ImageFont.truetype(str(SCHRIFT), int(22 * f)),
           fill=WEISS, anchor="ms")
    return bild.resize((kante, kante), Image.LANCZOS)


def main() -> None:
    (WURZEL / "favicon.svg").write_text(SVG, encoding="utf-8")
    zeichnen(48).save(WURZEL / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    zeichnen(192).save(WURZEL / "favicon-192.png", optimize=True)
    zeichnen(180, abgerundet=False).convert("RGB").save(WURZEL / "apple-touch-icon.png", optimize=True)
    print("favicon.ico, favicon.svg, favicon-192.png, apple-touch-icon.png geschrieben")


if __name__ == "__main__":
    main()
