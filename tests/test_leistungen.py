"""Tests für tools/leistungen.py – Zuordnung der Fachbeiträge zu den Leistungsseiten.

Aufruf: python -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import leistungen as l  # noqa: E402


class Zuordnung(unittest.TestCase):
    def test_ausdrueckliche_leistung(self):
        seite = l.passende_seite(["Beweissicherung"], ["Nachbesserung", "Werklohn"])
        self.assertEqual(seite.schluessel, "beweissicherung")

    def test_erster_wert_gewinnt(self):
        seite = l.passende_seite(["Beweissicherung", "Objektüberwachung LP 8"], ["Aufmaß"])
        self.assertEqual(seite.schluessel, "beweissicherung")

    def test_gutachten_nach_thema(self):
        seite = l.passende_seite(["Gutachten"], ["Schimmel", "Schimmel in der Wohnung: Baumangel oder Lüftung?"])
        self.assertEqual(seite.schluessel, "schimmel")
        seite = l.passende_seite(["Gutachten"], ["Wasserschaden im Mehrfamilienhaus"])
        self.assertEqual(seite.schluessel, "wasserschaden")

    def test_gutachten_ohne_thema_nimmt_naechsten_wert(self):
        seite = l.passende_seite(["Gutachten", "Bauherrenvertretung"], ["Mängelanzeige mit Fristsetzung"])
        self.assertEqual(seite.schluessel, "baubegleitung")

    def test_besonderes_schlaegt_allgemeines(self):
        # „Beweissicherung“ im Titel gewinnt gegen „Versicherung“ in den Schlagwörtern.
        seite = l.passende_seite(["Gutachten"], ["Versicherung", "Technische Beweissicherung: Nutzen"])
        self.assertEqual(seite.schluessel, "beweissicherung")

    def test_kaufberatung(self):
        seite = l.passende_seite(["Kaufberatung", "Gutachten"], ["Checkliste Hauskauf"])
        self.assertEqual(seite.schluessel, "due-diligence")

    def test_unbekannt_und_leer_fuehren_zur_uebersicht(self):
        self.assertEqual(l.passende_seite([], ["Werklohn", "Widerruf"]).schluessel, "uebersicht")
        self.assertEqual(l.passende_seite(["Energieberatung"], ["Dämmung"]).schluessel, "uebersicht")
        self.assertEqual(l.passende_seite(["Gutachten"], ["Wartungskalender"]).schluessel, "uebersicht")


class Seiten(unittest.TestCase):
    def test_reihenfolge_vollstaendig(self):
        self.assertEqual(set(l.REIHENFOLGE) | {"uebersicht"}, set(l.SEITEN))
        self.assertEqual(len(l.REIHENFOLGE), len(set(l.REIHENFOLGE)))

    def test_zuordnung_zeigt_auf_vorhandene_seiten(self):
        for schluessel in list(l.ZUORDNUNG.values()) + [s for _, s in l.STICHWORTE]:
            self.assertIn(schluessel, l.SEITEN)

    def test_jede_seite_liegt_im_repository(self):
        for seite in l.alle():
            self.assertTrue(seite.pfad.endswith("/"), seite.pfad)
            self.assertTrue((WURZEL / seite.pfad / "index.html").is_file(), seite.pfad)


if __name__ == "__main__":
    unittest.main()
