"""Prüft den Quelltext auf Fehler, die man beim Durchlesen nicht sieht.

Anlass (10. November 2026): Nach einem Suchen-und-Ersetzen stand im Kopf der
Startseite ein unsichtbares Steuerzeichen an der Stelle, an der der Anfang des
Kontakt-Knopfs hätte stehen sollen. Dem Link fehlte dadurch die schließende
spitze Klammer. Der Browser ließ ihn offen und begann ihn in jedem folgenden
Abschnitt neu: Das Menü rutschte in die Mitte, die Gebäudeskizze unter den
Text, Überschrift und Einleitung wurden anklickbar. Die übrigen Tests und die
Layoutprüfung haben das nicht bemerkt.

- Steuerzeichen: In Textdateien stehen außer Tabulator und Zeilenende keine
  Steuerzeichen.
- Links: Jeder Link ist geschlossen, bevor der nächste beginnt, und keiner
  HTML-Marke fehlt die schließende spitze Klammer.
"""
from __future__ import annotations

import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import website_bauen  # noqa: E402

TEXTDATEIEN = {".html", ".css", ".js", ".mjs", ".py", ".md", ".yml", ".yaml", ".json", ".txt", ".xml", ".svg"}
# Erlaubt bleiben Tabulator (0x09), Zeilenvorschub (0x0a) und Wagenrücklauf (0x0d).
STEUERZEICHEN = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def dateien(endungen: set[str]) -> list[Path]:
    """Alle versionierten Dateien mit einer der Endungen."""
    pfade = (WURZEL / p for p in website_bauen.repo_dateien() if Path(p).suffix.lower() in endungen)
    return [p for p in pfade if p.is_file()]


class LinkPruefer(HTMLParser):
    """Liest eine Seite wie ein Browser und merkt sich, ob gerade ein Link offen ist."""

    def __init__(self) -> None:
        super().__init__()
        self.offen: int | None = None  # Zeile, in der der offene Link beginnt
        self.befunde: list[str] = []

    def handle_starttag(self, tag, attrs):
        zeile = self.getpos()[0]
        # Fehlt die schließende Klammer, liest der Browser den folgenden Text
        # samt der nächsten öffnenden Klammer als Angabe der Marke.
        if any("<" in name for name, _ in attrs):
            self.befunde.append(f"Zeile {zeile}: <{tag}> ohne schließende spitze Klammer")
        if tag == "a":
            if self.offen is not None:
                self.befunde.append(f"Zeile {self.offen}: Link nicht geschlossen")
            self.offen = zeile

    def handle_endtag(self, tag):
        if tag == "a":
            if self.offen is None:
                self.befunde.append(f"Zeile {self.getpos()[0]}: </a> ohne geöffneten Link")
            self.offen = None

    def pruefe(self, text: str) -> list[str]:
        self.feed(text)
        self.close()
        if self.offen is not None:
            self.befunde.append(f"Zeile {self.offen}: Link nicht geschlossen")
        return self.befunde


class QuelltextTest(unittest.TestCase):
    def test_keine_steuerzeichen_in_textdateien(self):
        fehler = []
        for datei in dateien(TEXTDATEIEN):
            inhalt = datei.read_bytes()
            for treffer in STEUERZEICHEN.finditer(inhalt):
                zeile = inhalt.count(b"\n", 0, treffer.start()) + 1
                fehler.append(f"{datei.relative_to(WURZEL).as_posix()}:{zeile}: Zeichen 0x{treffer.group()[0]:02x}")
        self.assertEqual(fehler, [])

    def test_links_sind_geschlossen(self):
        fehler = []
        for datei in dateien({".html"}):
            for befund in LinkPruefer().pruefe(datei.read_text(encoding="utf-8")):
                fehler.append(f"{datei.relative_to(WURZEL).as_posix()}: {befund}")
        self.assertEqual(fehler, [])

    def test_pruefer_erkennt_den_fehler_vom_november_2026(self):
        kaputt = '<nav><a href="#kontakt" \x01Kontakt</a></nav><main><a href="#leistungen">Leistungen</a></main>'
        befunde = LinkPruefer().pruefe(kaputt)
        self.assertIn("Zeile 1: <a> ohne schließende spitze Klammer", befunde)
        self.assertIn("Zeile 1: Link nicht geschlossen", befunde)
        heil = kaputt.replace("\x01", 'class="btn">')
        self.assertEqual(LinkPruefer().pruefe(heil), [])


if __name__ == "__main__":
    unittest.main()
