"""Tests für tools/leistungen.py – Zuordnung der Fachbeiträge zu den Leistungsseiten.

Dazu der Schutz „keine eigenen Preise auf der Website“ (Klasse KeineEigenenPreise):
Preise und Leistungsübersicht verschickt das Büro nur auf Anfrage per E-Mail.

Aufruf: python -m unittest discover -s tests
"""
import json
import re
import sys
import unittest
from html import unescape
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
        # Private Käufer von Haus oder Wohnung landen bei der Kaufbegutachtung.
        seite = l.passende_seite(["Kaufberatung", "Gutachten"], ["Checkliste Hauskauf"])
        self.assertEqual(seite.schluessel, "kaufbegutachtung")
        seite = l.passende_seite(["Kaufberatung"], ["Checkliste Altbaukauf: Schwachstellen nach Baujahr"])
        self.assertEqual(seite.schluessel, "kaufbegutachtung")

    def test_kaufthemen_nach_stichwort(self):
        for titel in ("Checkliste Wohnungskauf: Sonder- und Gemeinschaftseigentum", "Altbaukauf in Berlin",
                      "Immobilienkauf ohne Reue", "Die Kaufentscheidung absichern", "Hauskauf: Unterlagen"):
            with self.subTest(titel=titel):
                self.assertEqual(l.passende_seite(["Gutachten"], [titel]).schluessel, "kaufbegutachtung")

    def test_due_diligence_bleibt(self):
        # „Due Diligence“ (Mietwohnhäuser, Investoren) bleibt bei der Due Diligence –
        # auch wenn im Titel zugleich vom Immobilienkauf die Rede ist.
        self.assertEqual(l.passende_seite(["Due Diligence"], ["Ankauf eines Mietshauses"]).schluessel,
                         "due-diligence")
        self.assertEqual(l.passende_seite(["Gutachten"], ["Technische Due Diligence beim Immobilienkauf"]).schluessel,
                         "due-diligence")

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


# ---------------------------------------------------------------------------
# Keine eigenen Preise auf der Website
#
# Der Inhaber verschickt Preise und die Übersicht der Leistungen nur auf Anfrage
# per E-Mail (Oktober 2026). Auf den ausgelieferten Leistungsseiten, den englischen
# Seiten, der Startseite, den Werkzeugen und in llms.txt dürfen deshalb keine
# Eurobeträge und keine Preisangaben in den Strukturdaten stehen.

# Eurobetrag: „1.059,10 €“, „150 €/h“, „3 Mio. €“, „150 Euro“, „€1,059.10“, „€3m“, „EUR 150“.
EUROBETRAG = re.compile(r"\d[\d.,]*(?:\s| )?(?:Mio\.\s?)?(?:€|EUR\b|Euro\b)|(?:€|\bEUR\b)(?:\s| )?\d")
# Strukturdaten-Felder für Preise (schema.org). "price": "0" ist erlaubt: kostenlose Werkzeuge.
PREISFELDER = {"price", "lowPrice", "highPrice", "minPrice", "maxPrice", "priceRange", "priceSpecification"}

# Beträge, die keine Preise des Büros sind – mit Grund. Sie werden vor der Suche
# aus dem Text entfernt; jede Ausnahme muss noch vorkommen, sonst ist sie überflüssig.
AUSNAHMEN = {
    # Rechenbeispiel im Mini-Rechner „Ihr Anteil an Gemeinschaftskosten“ (Kosten der Eigentümergemeinschaft).
    "Beispiel: 100.000 € × 45/1.000 = 4.500 €": ["leistungen/kaufbegutachtung/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    "Example: €100,000 × 45/1,000 = €4,500": ["en/pre-purchase-inspection-berlin/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    # Hinweis zum Berliner Mietspiegel: mögliche Mehrmiete (Marktangabe).
    "rund 40–47 € mehr im Monat": ["leistungen/kaufbegutachtung/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    "about €40–47 more per month": ["en/pre-purchase-inspection-berlin/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    # Förderbedingung des KfW-Programms 308 (Einkommensgrenze).
    "Einkommen bis 90.000 € (plus 10.000 € je weiteres Kind)": ["leistungen/kaufbegutachtung/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    "income up to €90,000 (plus €10,000 per further child)": ["en/pre-purchase-inspection-berlin/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    # Deckungssummen der Berufshaftpflicht (Qualifikation, kein Preis).
    "Berufshaftpflicht: 3 Mio. € Personen-, 300.000 € Vermögensschäden": ["leistungen/kaufbegutachtung/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
    "Professional indemnity: €3m personal injury, €300,000 financial loss": ["en/pre-purchase-inspection-berlin/index.html", "werkzeuge/kaufbegutachtung/daten.js"],
}


def ausgelieferte_dateien() -> list[Path]:
    """Leistungsseiten, englische Seiten (ohne die erzeugten Leitfäden), Startseite und Werkzeuge."""
    liste = [WURZEL / "index.html", WURZEL / "404.html"]
    liste += sorted((WURZEL / "leistungen").rglob("*.html"))
    liste += sorted(p for p in (WURZEL / "en").rglob("*.html") if "guides" not in p.relative_to(WURZEL / "en").parts)
    liste += sorted(p for p in (WURZEL / "werkzeuge").rglob("*") if p.suffix in (".html", ".js"))
    return [p for p in liste if p.is_file()]


def lesbarer_text(pfad: Path) -> str:
    roh = pfad.read_text(encoding="utf-8")
    if pfad.suffix == ".html":
        roh = re.sub(r'href="[^"]*"', " ", roh)      # URL-kodierte mailto-Texte
        roh = unescape(roh)
    return roh


def objekte(knoten):
    if isinstance(knoten, dict):
        yield knoten
        for wert in knoten.values():
            yield from objekte(wert)
    elif isinstance(knoten, list):
        for wert in knoten:
            yield from objekte(wert)


class KeineEigenenPreise(unittest.TestCase):
    def test_keine_eurobetraege(self):
        funde, benutzt = [], set()
        for pfad in ausgelieferte_dateien():
            ort = pfad.relative_to(WURZEL).as_posix()
            text = lesbarer_text(pfad)
            for ausnahme, orte in AUSNAHMEN.items():
                if ort in orte and ausnahme in text:
                    benutzt.add((ausnahme, ort))
                    text = text.replace(ausnahme, " ")
            for treffer in EUROBETRAG.finditer(text):
                funde.append(f"{ort}: …{text[max(0, treffer.start() - 50):treffer.end() + 20]}…")
        self.assertEqual(funde, [])
        fehlend = [(a, o) for a, orte in AUSNAHMEN.items() for o in orte if (a, o) not in benutzt]
        self.assertEqual(fehlend, [], "Ausnahme kommt nicht mehr vor – aus AUSNAHMEN streichen")

    def test_keine_preise_in_strukturdaten(self):
        funde = []
        for pfad in ausgelieferte_dateien():
            ort = pfad.relative_to(WURZEL).as_posix()
            roh = pfad.read_text(encoding="utf-8")
            if pfad.suffix == ".js":
                if re.search(r'"(?:%s)"\s*:' % "|".join(sorted(PREISFELDER)), roh):
                    funde.append(f"{ort}: Preisfeld im Skript")
                continue
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', roh, re.S):
                for obj in objekte(json.loads(block)):
                    for feld in PREISFELDER & set(obj):
                        if feld == "price" and str(obj[feld]) in ("0", "0.00"):
                            continue          # kostenloses Werkzeug, z. B. Wertrechner
                        funde.append(f"{ort}: {feld} = {obj[feld]}")
        self.assertEqual(funde, [])

    def test_keine_preisregeln_und_preisabschnitte(self):
        # Prozent- und Stundenregeln und frühere Überschriften dürfen nicht zurückkommen.
        verboten = re.compile(r"Erstpreis|initial (?:fee|price)|Stundensatz|hourly rate|€\s?/\s?h\b|\d\s?€\s?/\s?Stunde|"
                              r"Pakete und Preise|Packages and prices|Preise netto|Preis berechnen|Calculate your price|"
                              r"zzgl\.\s*USt|inkl\.\s*19\s*%|incl\.\s*19\s*% VAT|plus VAT")
        funde = []
        for pfad in ausgelieferte_dateien():
            for treffer in verboten.finditer(lesbarer_text(pfad)):
                funde.append(f"{pfad.relative_to(WURZEL).as_posix()}: {treffer.group(0)}")
        self.assertEqual(funde, [])

    def test_llms_txt_ohne_eigene_preise(self):
        # Die Abschnitte zu Leistungen und englischen Seiten in llms.txt (aus tools/leistungen.py).
        # Fachbeiträge dürfen Beträge aus Urteilen oder Kostenbeispielen nennen.
        llms = (WURZEL / "llms.txt").read_text(encoding="utf-8")
        zeilen = [z for z in llms.splitlines()
                  if "](https://ing-bassam.de/leistungen/" in z
                  or ("](https://ing-bassam.de/en/" in z and "/en/guides/" not in z)]
        self.assertTrue(zeilen)
        for zeile in zeilen:
            self.assertNotRegex(zeile, EUROBETRAG)
            self.assertNotRegex(zeile, r"Festpreis|fixed price|Richtpreis|Preise netto|incl\. VAT|price calculator|Preisrechner")
        for seite in l.alle():
            self.assertNotRegex(seite.kurztext, EUROBETRAG)
            self.assertNotRegex(seite.kurztext, r"Festpreis|Richtpreis|Preise netto|Preisrechner")
        for seite in l.ENGLISCH:
            self.assertNotRegex(seite.kurztext, EUROBETRAG)
            self.assertNotRegex(seite.kurztext, r"fixed price|incl\. VAT|price calculator|\bfees\b")


if __name__ == "__main__":
    unittest.main()
