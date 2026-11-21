"""Prüft alle Seiten der Website auf drei Punkte, die Ahrefs im Site Audit
bemängelt hat (Oktober und November 2026):

- Meta-Beschreibung länger als 160 Zeichen („Meta description too long“). Die
  Fachbeiträge begrenzt schon der Seitenbau auf 155 Zeichen; hier geht es vor
  allem um die von Hand gepflegten Seiten: Startseite, Leistungsseiten,
  englische Seiten.
- Strukturdaten mit einer Eigenschaft an einem Typ, der sie laut schema.org
  nicht kennt („Structured data has schema.org validation error“).
- Seitentitel länger als 60 Zeichen („Title too long“, November 2026 bei acht
  Leistungsseiten). Suchmaschinen schneiden längere Titel in der Trefferliste
  ab. Geprüft werden die von Hand gepflegten Seiten; die Titel der
  Fachbeiträge begrenzt der Seitenbau selbst (titel_tag).
"""
from __future__ import annotations

import json
import re
import unittest
from html import unescape
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
HOECHSTENS = 160
TITEL_HOECHSTENS = 60

# Eigenschaften, die schema.org nur bestimmten Typen erlaubt, samt den
# Unterklassen, die auf der Website vorkommen (Stand schema.org, Oktober 2026).
NUR_BEI = {
    "areaServed": {"ContactPoint", "DeliveryChargeSpecification", "Demand", "FinancialIncentive", "Offer",
                   "Organization", "LocalBusiness", "ProfessionalService", "Service"},
    "availableLanguage": {"ContactPoint", "Course", "LodgingBusiness", "ServiceChannel", "TouristAttraction"},
    # Ahrefs, 12.10.2026: „unitText“ direkt am Offer ist ein schema.org-Fehler.
    "unitText": {"PriceSpecification", "UnitPriceSpecification", "CompoundPriceSpecification",
                 "QuantitativeValue", "TypeAndQuantityNode"},
}


def seiten() -> list[Path]:
    return sorted(p for p in WURZEL.rglob("index.html") if ".git" not in p.parts)


def von_hand(seite: Path) -> bool:
    """Seiten, die nicht der Seitenbau erzeugt (tools/artikel_generator.py baut
    fachwissen/, tools/beitraege_en.py baut en/guides/)."""
    teile = seite.relative_to(WURZEL).parts
    return teile[0] != "fachwissen" and teile[:2] != ("en", "guides")


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

    def test_titel_hoechstens_60_zeichen(self):
        zu_lang = []
        for seite in filter(von_hand, seiten()):
            treffer = re.search(r"<title>(.*?)</title>", seite.read_text(encoding="utf-8"), re.S)
            if treffer and len(unescape(treffer.group(1).strip())) > TITEL_HOECHSTENS:
                zu_lang.append(f"{seite.parent.relative_to(WURZEL)}: {len(unescape(treffer.group(1).strip()))} Zeichen")
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
