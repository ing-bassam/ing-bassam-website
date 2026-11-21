"""Prüft die Strukturdaten der Übersicht /fachwissen/ am erzeugten Bestand.

Jeder Fachbeitrag nennt die Übersicht als Sammlung, zu der er gehört
(isPartOf). Bis November 2026 stand auf der Übersicht selbst kein Datensatz,
der Verweis der Beiträge lief also ins Leere. Seitdem beschreibt die Übersicht
sich als Sammlung, nennt den Herausgeber und zählt die Beiträge auf.

Verglichen wird nur Erzeugtes mit Erzeugtem: die Liste im Datensatz mit den
sichtbaren Karten, die Beiträge mit der Kennung der Übersicht. Die Prüfung
bleibt deshalb stimmig, wenn Beiträge hinzukommen oder wegfallen.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ORDNER = WURZEL / "fachwissen"
ADRESSE = "https://ing-bassam.de/fachwissen/"
FIRMA_ID = "https://ing-bassam.de/#organization"


def datensaetze(text: str) -> list[dict]:
    return [json.loads(block)
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)]


def knoten(daten: dict, typ: str) -> list[dict]:
    return [k for k in daten.get("@graph", []) if k.get("@type") == typ]


def objekte(wert):
    if isinstance(wert, dict):
        yield wert
        for teil in wert.values():
            yield from objekte(teil)
    elif isinstance(wert, list):
        for teil in wert:
            yield from objekte(teil)


class Uebersicht(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ORDNER / "index.html").read_text(encoding="utf-8")
        cls.daten = datensaetze(cls.text)
        liste = re.search(r'<ul class="karten">(.*?)</ul>', cls.text, re.S)
        cls.karten = [(kurzform, unescape(titel)) for kurzform, titel in
                      re.findall(r'<h2><a href="([^"/]+)/">(.*?)</a></h2>', liste.group(1) if liste else "")]

    def sammlung(self) -> dict:
        self.assertEqual(len(self.daten), 1, "Die Übersicht hat genau einen Datensatz")
        treffer = knoten(self.daten[0], "CollectionPage")
        self.assertEqual(len(treffer), 1)
        return treffer[0]

    def test_karten_werden_gefunden(self):
        # Sichert die Prüfungen unten ab: Ändert sich der Aufbau der Karten,
        # fällt das hier auf und nicht als stiller Vergleich zweier leerer Listen.
        self.assertEqual(len(self.karten), self.text.count('<li class="karte"'))

    def test_sammlung_traegt_die_adresse_der_seite(self):
        sammlung = self.sammlung()
        self.assertEqual(sammlung["@id"], ADRESSE)
        self.assertEqual(sammlung["url"], ADRESSE)
        self.assertIn(f'<link rel="canonical" href="{ADRESSE}">', self.text)
        self.assertTrue(sammlung.get("name"))
        self.assertTrue(sammlung.get("description"))

    def test_herausgeber_steht_auf_der_seite(self):
        self.assertEqual(self.sammlung()["publisher"], {"@id": FIRMA_ID})
        firmen = knoten(self.daten[0], "Organization")
        self.assertEqual([firma.get("@id") for firma in firmen], [FIRMA_ID])
        self.assertTrue(firmen[0].get("name"))
        self.assertEqual(firmen[0].get("url"), "https://ing-bassam.de/")

    def test_brotkrumen_entsprechen_der_sichtbaren_zeile(self):
        self.sammlung()
        pfade = knoten(self.daten[0], "BreadcrumbList")
        self.assertEqual(len(pfade), 1)
        self.assertEqual([(p["position"], p["name"], p["item"]) for p in pfade[0]["itemListElement"]],
                         [(1, "Start", "https://ing-bassam.de/"), (2, "Fachwissen", ADRESSE)])

    def test_liste_entspricht_den_karten(self):
        eintraege = self.sammlung().get("mainEntity", {}).get("itemListElement", [])
        self.assertEqual([e["position"] for e in eintraege], list(range(1, len(eintraege) + 1)))
        self.assertEqual([(e["url"], e["name"]) for e in eintraege],
                         [(f"{ADRESSE}{kurzform}/", titel) for kurzform, titel in self.karten])

    def test_beitraege_nennen_die_sammlung(self):
        ohne = []
        for kurzform, _ in self.karten:
            seite = (ORDNER / kurzform / "index.html").read_text(encoding="utf-8")
            sammlungen = {o["isPartOf"].get("@id") for daten in datensaetze(seite)
                          for o in objekte(daten) if isinstance(o.get("isPartOf"), dict)}
            if sammlungen != {ADRESSE}:
                ohne.append(kurzform)
        self.assertEqual(ohne, [])


if __name__ == "__main__":
    unittest.main()
