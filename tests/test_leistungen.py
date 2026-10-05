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
        seite = l.passende_seite(["Gutachten"], ["Schimmel in der Wohnung: Baumangel oder Lüftung?"], ["Schimmel"])
        self.assertEqual(seite.schluessel, "schimmel")
        seite = l.passende_seite(["Gutachten"], ["Wasserschaden im Mehrfamilienhaus"])
        self.assertEqual(seite.schluessel, "wasserschaden")

    def test_gutachten_ohne_thema_nimmt_naechsten_wert(self):
        seite = l.passende_seite(["Gutachten", "Bauherrenvertretung"], ["Mängelanzeige mit Fristsetzung"])
        self.assertEqual(seite.schluessel, "baubegleitung")

    def test_titel_wiegt_schwerer_als_schlagwoerter(self):
        # Der Schimmel-Beitrag erwähnt die Beweissicherung nur in den Schlagwörtern.
        seite = l.passende_seite(["Gutachten"], ["Schimmel in der Wohnung: Baumangel oder Lüftungsverhalten?"],
                                 ["Schimmel", "Beweissicherung", "Lüftung"])
        self.assertEqual(seite.schluessel, "schimmel")
        # Steht das Thema nur in den Schlagwörtern, zählen diese.
        seite = l.passende_seite(["Gutachten"], ["Was die Verwaltung zuerst tun muss"], ["Leitungswasser"])
        self.assertEqual(seite.schluessel, "wasserschaden")

    def test_besonderes_schlaegt_allgemeines(self):
        # „Beweissicherung“ im Titel gewinnt gegen „Versicherung“ in den Schlagwörtern.
        seite = l.passende_seite(["Gutachten"], ["Technische Beweissicherung: Nutzen"], ["Versicherung"])
        self.assertEqual(seite.schluessel, "beweissicherung")

    def test_kaufberatung(self):
        seite = l.passende_seite(["Kaufberatung", "Gutachten"], ["Checkliste Hauskauf"])
        self.assertEqual(seite.schluessel, "due-diligence")

    def test_unbekannt_und_leer_fuehren_zur_uebersicht(self):
        self.assertEqual(l.passende_seite([], ["Werklohn", "Widerruf"]).schluessel, "uebersicht")
        self.assertEqual(l.passende_seite(["Energieberatung"], ["Dämmung"]).schluessel, "uebersicht")
        self.assertEqual(l.passende_seite(["Gutachten"], ["Lichtplanung"]).schluessel, "uebersicht")

    def test_zielgruppenseiten(self):
        # Verwaltungsthemen ohne eigene Leistung führen zur Seite für Hausverwaltungen …
        seite = l.passende_seite(["Gutachten"], ["Wartungs- und Instandhaltungskalender für Wohngebäude",
                                                 "wartungskalender-instandhaltung-wohngebaeude"])
        self.assertEqual(seite.schluessel, "hausverwaltungen")
        # … der Versicherungsfall zur Seite für Versicherer.
        seite = l.passende_seite(["Gutachten"], ["Was gilt im Versicherungsfall?"])
        self.assertEqual(seite.schluessel, "versicherer")
        # Ein konkretes Thema schlägt die Zielgruppe in den Schlagwörtern.
        seite = l.passende_seite(["Gutachten"], ["Was die Verwaltung zuerst tun muss"],
                                 ["Hausverwaltung", "Leitungswasser"])
        self.assertEqual(seite.schluessel, "wasserschaden")


class Zielgruppen(unittest.TestCase):
    def test_hinweis_fuer_hausverwaltungen(self):
        seite = l.zielgruppen_seite(["Privat", "Hausverwaltung"], "schimmel")
        self.assertEqual(seite.schluessel, "hausverwaltungen")
        seite = l.zielgruppen_seite(["Gewerblich", "Wohnungsbaugesellschaft"], "uebersicht")
        self.assertEqual(seite.schluessel, "hausverwaltungen")

    def test_kein_doppelter_hinweis(self):
        self.assertIsNone(l.zielgruppen_seite(["Hausverwaltung"], "hausverwaltungen"))
        self.assertIsNone(l.zielgruppen_seite(["Privat", "Mieter"], "schimmel"))
        self.assertIsNone(l.zielgruppen_seite([], "schimmel"))


class Seiten(unittest.TestCase):
    def test_jede_seite_in_der_uebersicht_verlinkt(self):
        uebersicht = (WURZEL / "leistungen" / "index.html").read_text(encoding="utf-8")
        for seite in l.alle()[1:]:
            self.assertIn(f'href="/{seite.pfad}"', uebersicht, seite.pfad)

    def test_jede_seite_in_sitemap_und_llms(self):
        sitemap = (WURZEL / "sitemap.xml").read_text(encoding="utf-8")
        llms = (WURZEL / "llms.txt").read_text(encoding="utf-8")
        for seite in l.alle():
            url = f"https://ing-bassam.de/{seite.pfad}"
            self.assertIn(f"<loc>{url}</loc>", sitemap, seite.pfad)
            self.assertIn(f"({url})", llms, seite.pfad)

    def test_zielgruppenseiten_nennen_nur_bekannte_preise(self):
        # Die Seiten für Geschäftskunden wiederholen die Beträge der Leistungsseiten
        # (dort brutto für Privatkunden, hier netto) und erfinden keine neuen.
        import json
        import re

        def preise(datei: Path) -> set[str]:
            gefunden = set()
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                    datei.read_text(encoding="utf-8"), re.S):
                gefunden |= set(re.findall(r'"price":\s*"(\d+)"', json.dumps(json.loads(block))))
            return gefunden

        zielgruppen = {"hausverwaltungen", "rechtsanwaelte", "versicherer"}
        bekannt = set()
        for seite in l.alle()[1:]:
            if seite.schluessel not in zielgruppen:
                bekannt |= preise(WURZEL / seite.pfad / "index.html")
        for schluessel in sorted(zielgruppen):
            neu = preise(WURZEL / l.SEITEN[schluessel].pfad / "index.html")
            self.assertTrue(neu, schluessel)
            self.assertEqual(sorted(neu - bekannt), [], schluessel)

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
