"""Prüft, dass die FAQPage-Strukturdaten der von Hand gepflegten Seiten wörtlich
dem sichtbaren FAQ entsprechen.

Google verlangt, dass Fragen und Antworten im JSON-LD auch sichtbar auf der Seite
stehen. Auf mehreren englischen Seiten war die Antwort im JSON-LD kürzer oder
anders formuliert als im aufklappbaren FAQ (fehlende Sätze, „60 per cent“ statt
„60 %“). Verglichen wird der Text ohne Tags mit vereinheitlichten Leerzeichen,
Frage für Frage in derselben Reihenfolge.

Die Fachbeiträge und englischen Leitfäden erzeugen beide Fassungen aus derselben
Quelle (tools/artikel_generator.py, tools/beitraege_en.py); sie prüft dieser Test
nicht.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

# Tags, an deren Grenze im Fließtext ein Leerzeichen steht.
BLOCK = {"p", "li", "ul", "ol", "div", "br", "h3", "h4", "table", "tr", "td", "th", "dl", "dt", "dd"}


def seiten() -> list[Path]:
    liste = [WURZEL / "index.html", WURZEL / "wertrechner" / "index.html", WURZEL / "en" / "index.html"]
    liste += sorted((WURZEL / "leistungen").rglob("index.html"))
    liste += sorted(p for p in (WURZEL / "en").glob("*/index.html") if p.parent.name != "guides")
    liste += sorted((WURZEL / "werkzeuge").rglob("index.html"))
    return [p for p in liste if p.is_file()]


def normalisiert(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class FaqLeser(HTMLParser):
    """Sammelt Frage und Antwort jedes <details> im Block <div class="faq">."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paare: list[tuple[str, str]] = []
        self._div_tiefe = 0      # > 0: innerhalb von <div class="faq">
        self._frage: list[str] | None = None
        self._antwort: list[str] | None = None
        self._in_summary = False

    def handle_starttag(self, tag, attrs):
        klassen = (dict(attrs).get("class") or "").split()
        if tag == "div":
            if self._div_tiefe:
                self._div_tiefe += 1
            elif "faq" in klassen:
                self._div_tiefe = 1
        if not self._div_tiefe:
            return
        if tag == "details":
            self._frage, self._antwort = [], []
        elif tag == "summary":
            self._in_summary = True
        elif tag in BLOCK and self._antwort is not None:
            self._antwort.append(" ")

    def handle_endtag(self, tag):
        if not self._div_tiefe:
            return
        if tag == "summary":
            self._in_summary = False
        elif tag == "details" and self._frage is not None:
            self.paare.append((normalisiert("".join(self._frage)), normalisiert("".join(self._antwort))))
            self._frage = self._antwort = None
        elif tag in BLOCK and self._antwort is not None:
            self._antwort.append(" ")
        if tag == "div":
            self._div_tiefe -= 1

    def handle_data(self, data):
        if self._frage is None:
            return
        (self._frage if self._in_summary else self._antwort).append(data)


def sichtbares_faq(roh: str) -> list[tuple[str, str]]:
    leser = FaqLeser()
    leser.feed(roh)
    return leser.paare


def objekte(knoten):
    if isinstance(knoten, dict):
        yield knoten
        for wert in knoten.values():
            yield from objekte(wert)
    elif isinstance(knoten, list):
        for wert in knoten:
            yield from objekte(wert)


def strukturdaten_faq(roh: str) -> list[tuple[str, str]]:
    paare = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', roh, re.S):
        for obj in objekte(json.loads(block)):
            if obj.get("@type") == "FAQPage":
                for frage in obj.get("mainEntity", []):
                    paare.append((normalisiert(frage["name"]), normalisiert(frage["acceptedAnswer"]["text"])))
    return paare


class FaqStrukturdaten(unittest.TestCase):
    def test_strukturdaten_gleich_sichtbarem_faq(self):
        geprueft = 0
        for seite in seiten():
            roh = seite.read_text(encoding="utf-8")
            sichtbar, daten = sichtbares_faq(roh), strukturdaten_faq(roh)
            if not sichtbar and not daten:
                continue
            geprueft += 1
            with self.subTest(seite=seite.relative_to(WURZEL).as_posix()):
                self.assertEqual(daten, sichtbar)
        self.assertGreater(geprueft, 0)


if __name__ == "__main__":
    unittest.main()
