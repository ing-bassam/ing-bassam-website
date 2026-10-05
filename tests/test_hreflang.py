"""Prüft die Sprachverknüpfungen (hreflang) zwischen deutschen und englischen Seiten.

Google wertet hreflang nur aus, wenn beide Seiten aufeinander zeigen. Ein
einseitiger Verweis wird stillschweigend ignoriert – die englische Seite
erscheint dann womöglich nicht für englische Suchanfragen. Geprüft wird:

- Jede Seite, die eine andere Sprachfassung nennt, nennt sich auch selbst.
- Das Ziel jedes Verweises existiert im Repository.
- Das Ziel zeigt mit der Sprache der Ausgangsseite zurück.
- Die Liste der englischen Seiten in tools/leistungen.py stimmt mit den Dateien überein.
  Ausgenommen sind die Leitfäden unter en/guides/; die erzeugt der Seitenbauer aus
  entwuerfe-en/, geprüft in tests/test_leitfaeden_en.py.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
BASIS = "https://ing-bassam.de/"
sys.path.insert(0, str(WURZEL / "tools"))

import leistungen  # noqa: E402

LINK = re.compile(r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"\s*/?>')
SPRACHE = re.compile(r'<html\s+lang="([^"]+)"')


def url_von(seite: Path) -> str:
    teil = seite.parent.relative_to(WURZEL).as_posix()
    return BASIS if teil == "." else f"{BASIS}{teil}/"


def datei_von(url: str) -> Path:
    teil = url[len(BASIS):].strip("/")
    return WURZEL / teil / "index.html" if teil else WURZEL / "index.html"


def seiten() -> list[Path]:
    return sorted(p for p in WURZEL.rglob("index.html")
                  if ".git" not in p.parts and ".wertrechner-cache" not in p.parts)


def alternativen(seite: Path) -> dict[str, str]:
    return {sprache: ziel for sprache, ziel in LINK.findall(seite.read_text(encoding="utf-8"))}


class Hreflang(unittest.TestCase):
    def test_verweise_sind_gegenseitig(self):
        fehler = []
        for seite in seiten():
            alt = alternativen(seite)
            if not alt:
                continue
            eigene_url = url_von(seite)
            treffer = SPRACHE.search(seite.read_text(encoding="utf-8"))
            eigene_sprache = treffer.group(1) if treffer else ""
            ort = seite.parent.relative_to(WURZEL).as_posix()
            if alt.get(eigene_sprache) != eigene_url:
                fehler.append(f"{ort}: nennt sich nicht selbst unter hreflang={eigene_sprache}")
            for sprache, ziel in alt.items():
                if sprache == "x-default" or ziel == eigene_url:
                    continue
                if not ziel.startswith(BASIS):
                    fehler.append(f"{ort}: {ziel} liegt nicht auf ing-bassam.de")
                    continue
                ziel_datei = datei_von(ziel)
                if not ziel_datei.is_file():
                    fehler.append(f"{ort}: Ziel {ziel} fehlt im Repository")
                    continue
                if alternativen(ziel_datei).get(eigene_sprache) != eigene_url:
                    fehler.append(f"{ort}: {ziel} zeigt nicht mit hreflang={eigene_sprache} zurück")
        self.assertEqual(fehler, [])

    def test_englische_seiten_vollstaendig(self):
        for seite in leistungen.ENGLISCH:
            datei = WURZEL / seite.pfad / "index.html"
            self.assertTrue(datei.is_file(), seite.pfad)
            text = datei.read_text(encoding="utf-8")
            self.assertRegex(text, r'<html\s+lang="en"', seite.pfad)
            if seite.deutsch is not None:
                self.assertEqual(alternativen(datei).get("de"), BASIS + seite.deutsch, seite.pfad)

    def test_jede_englische_seite_steht_in_der_liste(self):
        bekannt = {s.pfad for s in leistungen.ENGLISCH}
        vorhanden = {p.parent.relative_to(WURZEL).as_posix() + "/" for p in (WURZEL / "en").rglob("index.html")}
        vorhanden = {pfad for pfad in vorhanden if not pfad.startswith("en/guides/")}
        self.assertEqual(sorted(vorhanden - bekannt), [])


if __name__ == "__main__":
    unittest.main()
