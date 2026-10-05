"""Prüft alle Seiten der Website auf zwei Punkte, die Ahrefs im Site Audit
bemängelt hat (Oktober 2026):

- Meta-Beschreibung länger als 160 Zeichen („Meta description too long“). Die
  Fachbeiträge begrenzt schon der Seitenbau auf 155 Zeichen; hier geht es vor
  allem um die von Hand gepflegten Seiten: Startseite, Leistungsseiten,
  Wertrechner.
- Strukturdaten mit einer Eigenschaft an einem Typ, der sie laut schema.org
  nicht kennt („Structured data has schema.org validation error“).
"""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
HOECHSTENS = 160

# Eigenschaften, die schema.org nur bestimmten Typen erlaubt, samt den
# Unterklassen, die auf der Website vorkommen (Stand schema.org, Oktober 2026).
NUR_BEI = {
    "areaServed": {"ContactPoint", "DeliveryChargeSpecification", "Demand", "FinancialIncentive", "Offer",
                   "Organization", "LocalBusiness", "ProfessionalService", "Service"},
    "availableLanguage": {"ContactPoint", "Course", "LodgingBusiness", "ServiceChannel", "TouristAttraction"},
}


def seiten() -> list[Path]:
    return sorted(p for p in WURZEL.rglob("index.html") if ".git" not in p.parts)


def objekte(knoten):
    if isinstance(knoten, dict):
        yield knoten
        for wert in knoten.values():
            yield from objekte(wert)
    elif isinstance(knoten, list):
        for wert in knoten:
            yield from objekte(wert)


class SeitenTest(unittest.TestCase):
    def test_meta_beschreibung_hoechstens_160_zeichen(self):
        zu_lang = []
        for seite in seiten():
            treffer = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', seite.read_text(encoding="utf-8"))
            if treffer and len(unescape(treffer.group(1))) > HOECHSTENS:
                zu_lang.append(f"{seite.parent.relative_to(WURZEL)}: {len(unescape(treffer.group(1)))} Zeichen")
        self.assertEqual(zu_lang, [])

    def test_strukturdaten_eigenschaften_am_richtigen_typ(self):
        fehler = []
        for seite in seiten():
            text = seite.read_text(encoding="utf-8")
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
                for obj in objekte(json.loads(block)):
                    typ = obj.get("@type")
                    typen = set(typ) if isinstance(typ, list) else ({typ} if typ else set())
                    for eigenschaft, erlaubt in NUR_BEI.items():
                        if eigenschaft in obj and typen and not typen & erlaubt:
                            fehler.append(f"{seite.parent.relative_to(WURZEL)}: {eigenschaft} an {', '.join(sorted(typen))}")
        self.assertEqual(fehler, [])


if __name__ == "__main__":
    unittest.main()
