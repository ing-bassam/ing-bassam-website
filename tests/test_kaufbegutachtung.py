"""Prüft die öffentlichen Seiten zur Kaufbegutachtung (Deutsch und Englisch).

Seit Oktober 2026 stehen dort nur noch Nutzen, Leistungsumfang, Ablauf, Grenzen,
Qualifikation und FAQ. Preise, Optionen, Hinweise nach Baujahr, Pflichten nach
dem Kauf und Unterlagenlisten verschickt das Büro erst nach einer Anfrage – über
die private, verschlüsselte Angebotsseite (angebot/kaufbegutachtung/, geprüft in
tests/test_angebot.py). Dieser Test stellt sicher:

- Kein interaktiver Teil mehr: kein Formular, kein Skript, keine Regeltexte,
  keine Unterlagenliste, kein Anteilsrechner.
- Der Knopf „Angebot anfordern“ öffnet eine E-Mail mit der vorgegebenen Vorlage.
- „Preise und Leistungsübersicht senden wir Ihnen nach Ihrer Anfrage“ steht da.
- Die Anker der QR-Codes (#wohnung, #haus, #flat, #house) bleiben erhalten.
- Andere Seiten verweisen weiter auf die Kaufbegutachtung.

Dass auf den Seiten keine Eurobeträge des Büros stehen, prüft
tests/test_leistungen.py für alle Leistungsseiten gemeinsam.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import re
import unittest
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

WURZEL = Path(__file__).resolve().parent.parent

SEITEN = {"de": WURZEL / "leistungen" / "kaufbegutachtung" / "index.html",
          "en": WURZEL / "en" / "pre-purchase-inspection-berlin" / "index.html"}
DUE_DILIGENCE = {"de": WURZEL / "leistungen" / "technische-due-diligence" / "index.html",
                 "en": WURZEL / "en" / "technical-due-diligence-berlin" / "index.html"}
UEBERSICHTEN = {"de": WURZEL / "leistungen" / "index.html", "en": WURZEL / "en" / "index.html"}

PREISE_NACH_ANFRAGE = {"de": "Preise und Leistungsübersicht senden wir Ihnen nach Ihrer Anfrage",
                       "en": "We send you prices and the list of services after your enquiry"}
MAIL = {
    "de": ("Anfrage: Kaufbegutachtung",
           "Guten Tag,\r\n\r\nich interessiere mich für eine Kaufbegutachtung.\r\n\r\n"
           "Objekt (Haus oder Wohnung), Ort/Bezirk, geplanter Notartermin: …\r\n\r\n"
           "Bitte senden Sie mir Ihr Angebot."),
    "en": ("Enquiry: pre-purchase inspection",
           "Hello,\r\n\r\nI am interested in a pre-purchase inspection.\r\n\r\n"
           "Property (house or flat), location/district, planned notary date: …\r\n\r\n"
           "Please send me your quote."),
}
KNOPF = {"de": "Angebot anfordern", "en": "Request a quote"}
ANKER = {"de": ("wohnung", "haus"), "en": ("flat", "house")}
# Was es öffentlich nicht mehr gibt: Hinweis-Assistent, Regeln, Unterlagen, Anteilsrechner.
VERBOTEN = (
    "<form", "<script type=\"module\"", "<script src", "werkzeuge/kaufbegutachtung", "data-regel", "data-unterlage",
    "Hinweise nach Baujahr", "Notes by year of construction", "Diese Unterlagen helfen uns", "Documents that help us",
    "Liste kopieren", "Copy list", "Miteigentumsanteil", "co-ownership share", "Anteil an Gemeinschaftskosten",
    "share of common costs", "Bleileitungen", "lead pipes", "GModG", "TrinkwV", "Mietspiegel", "rent index",
    "Rechtsstand", "Legal position", "/angebot/",
)


def roh(sprache: str) -> str:
    return SEITEN[sprache].read_text(encoding="utf-8")


def mail_links(text: str) -> list[str]:
    return [unescape(h) for h in re.findall(r'href="(mailto:[^"]*)"', text)]


class OeffentlicheSeiten(unittest.TestCase):
    def test_kein_interaktiver_teil(self):
        for sprache in SEITEN:
            text = unescape(roh(sprache))
            for wort in VERBOTEN:
                with self.subTest(sprache=sprache, wort=wort):
                    self.assertNotIn(wort, text)

    def test_angebot_anfordern_mit_vorlage(self):
        for sprache, (betreff, text) in MAIL.items():
            seite = roh(sprache)
            self.assertIn(f">{KNOPF[sprache]}</a>", seite)
            mit_text = [h for h in mail_links(seite) if "body=" in h]
            self.assertGreaterEqual(len(mit_text), 2, sprache)
            for link in mit_text:
                teile = urlsplit(link)
                self.assertEqual(teile.path, "info@ing-bassam.de")
                werte = parse_qs(teile.query)
                self.assertEqual(werte["subject"], [betreff])
                self.assertEqual(werte["body"], [text])

    def test_preise_nach_anfrage(self):
        for sprache, satz in PREISE_NACH_ANFRAGE.items():
            seite = unescape(roh(sprache))
            self.assertIn(satz, seite)
            self.assertIn('href="tel:+4917623581339"', seite)
            for wort in ("Preis berechnen", "Calculate your price", "Preisrechner", "price calculator", "data-preis="):
                self.assertNotIn(wort, seite)
            kopf = re.search(r"<head>.*?</head>", seite, re.S).group(0)
            self.assertNotRegex(kopf, r'"(?:price|minPrice|maxPrice|priceRange|priceSpecification)"|"Offer"')

    def test_abschnitte_vorhanden(self):
        erwartet = {
            "de": ("Leistungsumfang", "Eigentumswohnung", "Einfamilienhaus", "So läuft es ab", "Was nicht enthalten ist",
                   "Qualifikation", "Mitglied der Baukammer Berlin", "Häufige Fragen"),
            "en": ("Scope of services", "Flat (condominium)", "House", "How it works", "What is not included",
                   "Qualifications", "Member of the Berlin Chamber of Engineers", "Frequently asked questions"),
        }
        for sprache, teile in erwartet.items():
            seite = unescape(roh(sprache))
            for teil in teile:
                with self.subTest(sprache=sprache, teil=teil):
                    self.assertIn(teil, seite)

    def test_anker_der_qr_codes(self):
        # Ziele der QR-Codes in den Broschüren – diese Adressen bleiben stabil.
        for sprache, namen in ANKER.items():
            for name in namen:
                self.assertIn(f'id="{name}"', roh(sprache), name)

    def test_titel_und_sicherheit(self):
        for sprache in SEITEN:
            seite = roh(sprache)
            titel = re.search(r"<title>(.*?)</title>", seite).group(1)
            self.assertLessEqual(len(unescape(titel)), 60, titel)
            self.assertNotRegex(titel, r"[Pp]reis|[Pp]rice")
            self.assertIn("script-src 'self'", seite)
            self.assertNotIn("http://", seite.replace("http://www.w3.org", ""))

    def test_alte_skripte_entfernt(self):
        # Regeln und Unterlagen lagen bis Oktober 2026 öffentlich in werkzeuge/kaufbegutachtung/daten.js.
        ordner = WURZEL / "werkzeuge" / "kaufbegutachtung"
        self.assertEqual(sorted(p.name for p in ordner.rglob("*")) if ordner.exists() else [], [])
        self.assertFalse((WURZEL / "tools" / "kaufbegutachtung_bauen.py").exists())


class AndereSeiten(unittest.TestCase):
    def test_due_diligence_verweist_auf_kaufbegutachtung(self):
        for sprache, pfad in DUE_DILIGENCE.items():
            inhalt = unescape(pfad.read_text(encoding="utf-8"))
            ziel = "/leistungen/kaufbegutachtung/" if sprache == "de" else "/en/pre-purchase-inspection-berlin/"
            self.assertIn(f'href="{ziel}"', inhalt)
            # Der frühere „Technische Kurzbericht“ ist ersetzt.
            self.assertNotIn("Technischer Kurzbericht", inhalt)
            self.assertNotIn("Building survey report", inhalt)

    def test_uebersichten_verlinken_die_seite(self):
        self.assertIn('href="/leistungen/kaufbegutachtung/"', UEBERSICHTEN["de"].read_text(encoding="utf-8"))
        self.assertIn('href="/en/pre-purchase-inspection-berlin/"', UEBERSICHTEN["en"].read_text(encoding="utf-8"))

    def test_startseite_fuehrt_zur_kaufbegutachtung(self):
        # Der Leistungseintrag „Objektüberwachung (LP 8)“ ist durch die Kaufbegutachtung ersetzt;
        # der Anker #leistung-objektueberwachung bleibt für ältere Links aus Fachbeiträgen erhalten.
        start = (WURZEL / "index.html").read_text(encoding="utf-8")
        karte = re.search(r'<article class="service-card[^"]*"[^>]*id="leistung-kaufbegutachtung">(.*?)</article>', start, re.S)
        self.assertIsNotNone(karte)
        self.assertIn("Kaufbegutachtung", karte.group(1))
        self.assertIn('href="/leistungen/kaufbegutachtung/"', karte.group(1))
        self.assertIn('id="leistung-objektueberwachung"', start)
        self.assertNotRegex(start, r'<h3>Objektüberwachung')
        self.assertIn('"url": "https://ing-bassam.de/leistungen/kaufbegutachtung/"', start)


if __name__ == "__main__":
    unittest.main()
