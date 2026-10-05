"""Prüft die englischen Leitfäden (entwuerfe-en/ -> en/guides/, tools/beitraege_en.py).

- Jeder Entwurf lässt sich lesen und besteht die mechanische Prüfung
  (Titellänge, Meta-Beschreibung, Leistungsseite, FAQ, Autorenkasten, Fußnoten).
- Jeder Leitfaden ist die Fassung eines veröffentlichten deutschen Beitrags.
- Jede veröffentlichte Fassung ist gebaut und mit dem Original verknüpft
  (hreflang in beide Richtungen), steht in Übersicht, Sitemap und llms.txt.
- Unter en/guides/ liegt keine Seite ohne Entwurf.

Braucht nur PyYAML; markdown lädt beitraege_en erst beim Bauen.
Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

WURZEL = Path(__file__).resolve().parent.parent
BASIS = "https://ing-bassam.de/"
sys.path.insert(0, str(WURZEL / "tools"))

import beitraege_en  # noqa: E402

LINK = re.compile(r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"\s*/?>')


def deutsche_beitraege() -> dict[str, str]:
    """Kurzform -> Status aller deutschen Entwürfe unter entwuerfe/."""
    ergebnis: dict[str, str] = {}
    for pfad in sorted((WURZEL / "entwuerfe").rglob("*.md")):
        if pfad.name.lower() == "readme.md":
            continue
        roh = pfad.read_text(encoding="utf-8")
        treffer = re.match(r"^---\r?\n(.*?)\r?\n---", roh, re.S)
        kopf = (yaml.safe_load(treffer.group(1)) or {}) if treffer else {}
        kurzform = str(kopf.get("kurzform") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", pfad.stem)).strip()
        ergebnis[kurzform] = str(kopf.get("status") or "").strip()
    return ergebnis


def alternativen(datei: Path) -> dict[str, str]:
    return dict(LINK.findall(datei.read_text(encoding="utf-8")))


class Leitfaeden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.leitfaeden, cls.fehler = beitraege_en.laden()
        cls.oeffentlich = [l for l in cls.leitfaeden if l.oeffentlich]

    def test_entwuerfe_lesbar(self):
        self.assertEqual(self.fehler, [])
        self.assertTrue(self.leitfaeden, "entwuerfe-en/ enthält keinen Leitfaden")

    def test_mechanische_pruefung(self):
        befunde = {l.kurzform: beitraege_en.pruefen(l) for l in self.leitfaeden}
        self.assertEqual({k: v for k, v in befunde.items() if v}, {})

    def test_original_ist_veroeffentlicht(self):
        deutsch = deutsche_beitraege()
        for l in self.leitfaeden:
            with self.subTest(l.kurzform):
                self.assertIn(l.original, deutsch, "deutsches Original fehlt")
                self.assertEqual(deutsch[l.original].lower(), "veröffentlicht")

    def test_seiten_gebaut_und_verknuepft(self):
        sitemap = (WURZEL / "sitemap.xml").read_text(encoding="utf-8")
        llms = (WURZEL / "llms.txt").read_text(encoding="utf-8")
        uebersicht = (WURZEL / "en" / "guides" / "index.html").read_text(encoding="utf-8")
        for l in self.oeffentlich:
            with self.subTest(l.kurzform):
                seite = WURZEL / "en" / "guides" / l.kurzform / "index.html"
                original = WURZEL / "fachwissen" / l.original / "index.html"
                self.assertTrue(seite.is_file(), "Seite nicht gebaut – tools/artikel_generator.py laufen lassen")
                self.assertRegex(seite.read_text(encoding="utf-8"), r'<html\s+lang="en"')
                self.assertEqual(alternativen(seite).get("de"), f"{BASIS}fachwissen/{l.original}/")
                self.assertEqual(alternativen(original).get("en"), l.url)
                self.assertIn(f'href="{l.adresse}"', uebersicht)
                self.assertIn(f"<loc>{l.url}</loc>", sitemap)
                self.assertIn(f"({l.url})", llms)

    def test_keine_verwaisten_seiten(self):
        ordner = WURZEL / "en" / "guides"
        vorhanden = {p.name for p in ordner.iterdir() if p.is_dir()} if ordner.is_dir() else set()
        self.assertEqual(sorted(vorhanden - {l.kurzform for l in self.leitfaeden}), [])


ENTWURF = """---
titel: "Test guide"
kurzform: {kurzform}
original: schimmel-wohnung-baumangel-lueftung
meta_beschreibung: "A test description that is long enough to pass the lower limit of seventy characters."
leistung: en/mould-survey-berlin/
erstellt: 2026-10-05
status: Veröffentlicht
---

# Test guide

Text with a source.[^a]{zusatz}

## Frequently asked questions

**First question?**

Answer.

**Second question?**

Answer.

**Third question?**

Answer.

---

**About the author**

Author.

[^a]: Source.
"""


class Regeln(unittest.TestCase):
    """Die Prüfregeln selbst, an Entwürfen in einem leeren Ordner."""

    def laden(self, *dateien: tuple[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            for name, inhalt in dateien:
                Path(tmp, name).write_text(inhalt, encoding="utf-8")
            with mock.patch.object(beitraege_en, "ORDNER", Path(tmp)):
                return beitraege_en.laden()

    def test_gueltiger_entwurf_ohne_befund(self):
        leitfaeden, fehler = self.laden(("a.md", ENTWURF.format(kurzform="test-a", zusatz="")))
        self.assertEqual(fehler, [])
        self.assertEqual(beitraege_en.pruefen(leitfaeden[0]), [])
        self.assertTrue(leitfaeden[0].oeffentlich)

    def test_doppelte_kurzform_und_doppeltes_original(self):
        _, fehler = self.laden(("a.md", ENTWURF.format(kurzform="test-a", zusatz="")),
                               ("b.md", ENTWURF.format(kurzform="test-a", zusatz="")))
        self.assertTrue(any("belegt schon" in f for f in fehler))
        self.assertTrue(any("schon eine englische Fassung" in f for f in fehler))

    def test_fussnote_ohne_quelle(self):
        leitfaeden, _ = self.laden(("a.md", ENTWURF.format(kurzform="test-a", zusatz=" More.[^b]")))
        self.assertIn("Fußnoten ohne Quelle: b", beitraege_en.pruefen(leitfaeden[0]))

    def test_offener_pruefpunkt_sperrt_veroeffentlichung(self):
        leitfaeden, fehler = self.laden(("a.md", ENTWURF.format(kurzform="test-a", zusatz="\n\n> TODO: check")))
        self.assertFalse(leitfaeden[0].oeffentlich)
        self.assertTrue(any("offene Prüfpunkte" in f for f in fehler))


if __name__ == "__main__":
    unittest.main()
