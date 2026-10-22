"""Prüft die Seiten zur Kaufbegutachtung gegen ihre einzige Datenquelle.

werkzeuge/kaufbegutachtung/daten.js enthält Leistungsumfang, Regeln, Unterlagen
und Texte. Der Hinweis-Assistent liest sie im Browser; die festen Abschnitte der
Seiten (für Besucher ohne JavaScript, Suchmaschinen und KI-Crawler) erzeugt
tools/kaufbegutachtung_bauen.py daraus. Dieser Test stellt sicher:

- Die Daten sind in sich stimmig (Verweise auf Eingaben, Merkmale, Kategorien).
- In den Daten stehen keine Preisfelder mehr (die Datei ist öffentlich abrufbar):
  Preise und Leistungsübersicht verschickt das Büro nur auf Anfrage per E-Mail.
- Jede Regel-ID, jede Unterlage und der Leistungsumfang stehen im HTML beider
  Sprachfassungen; die Seiten nennen „Preise auf Anfrage per E-Mail“.
- Die festen Abschnitte entsprechen den Daten (sonst Skript ausführen).
- Die Anker der QR-Codes (#wohnung, #haus, #flat, #house) bleiben erhalten.

Dass auf den Seiten und in den Skripten keine Eurobeträge des Büros stehen, prüft
tests/test_leistungen.py für alle Leistungsseiten gemeinsam.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import re
import sys
import unittest
from html import unescape
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import kaufbegutachtung_bauen as kb  # noqa: E402
import website_bauen  # noqa: E402

SEITEN = kb.SEITEN
DUE_DILIGENCE = {"de": WURZEL / "leistungen" / "technische-due-diligence" / "index.html",
                 "en": WURZEL / "en" / "technical-due-diligence-berlin" / "index.html"}
UEBERSICHTEN = {"de": WURZEL / "leistungen" / "index.html", "en": WURZEL / "en" / "index.html"}
PREISFELDER = {"mwst", "netto", "netto_von", "netto_bis", "brutto", "stundensatz_netto", "zuschlaege",
               "preis_schalter", "optionen", "pakete", "empfiehlt", "pauschal", "stundensatz"}
PREISE_AUF_ANFRAGE = {"de": "Preise und die Übersicht aller Leistungen und Optionen senden wir Ihnen auf Anfrage per E-Mail",
                      "en": "We send prices and a full list of services and options on request by email"}


def text(pfad: Path) -> str:
    return unescape(pfad.read_text(encoding="utf-8"))


def schluessel(knoten, pfad="") -> list[tuple[str, str]]:
    """Alle Schlüssel eines JSON-Baums mit ihrem Pfad."""
    gefunden = []
    if isinstance(knoten, dict):
        for k, v in knoten.items():
            gefunden.append((k, f"{pfad}.{k}"))
            gefunden += schluessel(v, f"{pfad}.{k}")
    elif isinstance(knoten, list):
        for i, v in enumerate(knoten):
            gefunden += schluessel(v, f"{pfad}[{i}]")
    return gefunden


class Daten(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = kb.daten_laden()

    def test_verweise_stimmen(self):
        d = self.d
        heizung = {x["id"] for x in d["eingaben"]["heizung"]}
        nutzung = {x["id"] for x in d["eingaben"]["nutzung"]}
        region = {x["id"] for x in d["eingaben"]["region"]}
        schalter = set(d["eingaben"]["schalter"])
        ids = [r["id"] for r in d["regeln"]]
        self.assertEqual(len(ids), len(set(ids)), "Regel-IDs doppelt")
        for r in d["regeln"]:
            with self.subTest(regel=r["id"]):
                self.assertIn(r["kategorie"], kb.KATEGORIEN)
                self.assertIn(r["objekt"], {"etw", "efh", "beide"})
                self.assertLessEqual(set(r.get("heizung", [])), heizung)
                self.assertLessEqual(set(r.get("nutzung", [])), nutzung)
                self.assertLessEqual(set(r.get("region", [])), region)
                self.assertLessEqual(set(r) & {"fertighaus", "mfh6", "milieuschutz"}, schalter)
                if "von" in r and "bis" in r:
                    self.assertLessEqual(r["von"], r["bis"])
                for sprache in ("de", "en"):
                    self.assertTrue(r[sprache]["titel"] and r[sprache]["text"])
                self.assertTrue(r["quelle"]["titel"])
                self.assertTrue(r["quelle"]["url"] == "" or r["quelle"]["url"].startswith("https://"))
        for name, s in d["eingaben"]["schalter"].items():
            self.assertIn(s["objekt"], kb.OBJEKTE, name)
            self.assertTrue(s["de"] and s["en"], name)
        for objekt in kb.OBJEKTE:
            for sprache in ("de", "en"):
                self.assertGreaterEqual(len(d["leistungen"][objekt][sprache]), 5, (objekt, sprache))
            self.assertEqual(len(d["leistungen"][objekt]["de"]), len(d["leistungen"][objekt]["en"]), objekt)
            unterlagen = [u["id"] for u in d["unterlagen"][objekt]]
            self.assertEqual(len(unterlagen), len(set(unterlagen)), objekt)
            for u in d["unterlagen"][objekt]:
                self.assertIn(u["prio"], (1, 2, 3))
                self.assertLessEqual(set(u.get("heizung", [])), heizung)
                self.assertLessEqual(set(u.get("nutzung", [])), nutzung)
        self.assertEqual(set(d["seite"]["de"]["kategorien"]), set(kb.KATEGORIEN))
        self.assertEqual(set(d["seite"]["de"]["ui"]), set(d["seite"]["en"]["ui"]))
        self.assertEqual(set(d["text"]["de"]), set(d["text"]["en"]))

    def test_keine_preisfelder(self):
        # daten.js ist öffentlich abrufbar: keine Preise, Zuschläge, Optionen oder Stundensätze.
        gefunden = [pfad for name, pfad in schluessel(self.d) if name in PREISFELDER]
        self.assertEqual(gefunden, [])
        roh = kb.DATEN_JS.read_text(encoding="utf-8")
        self.assertNotRegex(roh, r"\{(?:brutto|netto):")

    def test_anfrage_bittet_um_angebot_mit_preisen(self):
        self.assertEqual(self.d["seite"]["de"]["ui"]["angebot_bitte"],
                         "Bitte senden Sie mir Ihr Angebot mit Preisen und der Leistungsübersicht.")
        self.assertIn("quote with prices", self.d["seite"]["en"]["ui"]["angebot_bitte"])
        for sprache, satz in PREISE_AUF_ANFRAGE.items():
            self.assertTrue(self.d["text"][sprache]["preise"].startswith(satz), sprache)


class Seiten(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = kb.daten_laden()
        cls.html = {sprache: text(pfad) for sprache, pfad in SEITEN.items()}
        cls.roh = {sprache: pfad.read_text(encoding="utf-8") for sprache, pfad in SEITEN.items()}

    def test_feste_abschnitte_entsprechen_den_daten(self):
        self.assertEqual(kb.pruefen(self.d), [], "python tools/kaufbegutachtung_bauen.py ausführen")

    def test_jede_regel_in_beiden_sprachen(self):
        for sprache, roh in self.roh.items():
            for r in self.d["regeln"]:
                with self.subTest(sprache=sprache, regel=r["id"]):
                    self.assertIn(f'data-regel="{r["id"]}"', roh)
                    self.assertIn(r[sprache]["titel"], self.html[sprache])
                    self.assertIn(r[sprache]["text"], self.html[sprache])

    def test_leistungsumfang_in_beiden_sprachen(self):
        for sprache, inhalt in self.html.items():
            for objekt in kb.OBJEKTE:
                for punkt in self.d["leistungen"][objekt][sprache]:
                    with self.subTest(sprache=sprache, punkt=punkt):
                        self.assertIn(punkt, inhalt)

    def test_preise_auf_anfrage(self):
        # Statt Preisen: der Hinweis auf die E-Mail, ein Kontaktweg und „Angebot anfordern“.
        for sprache, inhalt in self.html.items():
            with self.subTest(sprache=sprache):
                self.assertIn(PREISE_AUF_ANFRAGE[sprache], inhalt)
                self.assertIn('href="mailto:info@ing-bassam.de', inhalt)
                self.assertIn('href="tel:+4917623581339"', inhalt)
                self.assertIn('id="anfrage-link"', inhalt)
                self.assertIn("Angebot anfordern" if sprache == "de" else "Request a quote", inhalt)
                for wort in ("Preis berechnen", "Calculate your price", "Preisrechner", "price calculator",
                             'id="summe"', 'id="optionen"', "preistabelle", "data-preis="):
                    self.assertNotIn(wort, inhalt)
                kopf = re.search(r"<head>.*?</head>", inhalt, re.S).group(0)
                self.assertNotRegex(kopf, r'"(?:price|minPrice|maxPrice|priceRange|priceSpecification)"|"Offer"')

    def test_unterlagen_in_beiden_sprachen(self):
        for sprache, inhalt in self.html.items():
            for objekt in kb.OBJEKTE:
                for u in self.d["unterlagen"][objekt]:
                    with self.subTest(sprache=sprache, unterlage=u["id"]):
                        self.assertIn(u[sprache], inhalt)

    def test_anker_der_qr_codes(self):
        # Ziele der QR-Codes in den Broschüren – diese Adressen müssen stabil bleiben.
        for sprache, anker in (("de", ("wohnung", "haus")), ("en", ("flat", "house"))):
            for name in anker:
                self.assertIn(f'id="{name}"', self.roh[sprache], name)
            self.assertEqual(set(self.d["anker"][sprache].values()), set(anker))

    def test_titel_und_skripte(self):
        for sprache, roh in self.roh.items():
            titel = re.search(r"<title>(.*?)</title>", roh).group(1)
            self.assertLessEqual(len(unescape(titel)), 60, titel)
            self.assertNotRegex(titel, r"[Pp]reis|[Pp]rice")
            self.assertIn('<script type="module" src="/werkzeuge/kaufbegutachtung/app.js"></script>', roh)
            self.assertIn("script-src 'self'", roh)
            self.assertNotIn("http://", roh.replace("http://www.w3.org", ""))

    def test_skripte_werden_ausgeliefert(self):
        # Positivliste in tools/website_bauen.py: unter werkzeuge/ dürfen .js-Dateien online gehen.
        for datei in ("app.js", "kaufbegutachtung.js", "daten.js"):
            pfad = f"werkzeuge/kaufbegutachtung/{datei}"
            self.assertTrue((WURZEL / pfad).is_file(), pfad)
            self.assertTrue(website_bauen.zur_website(pfad), pfad)
        for pfad in SEITEN.values():
            self.assertTrue(website_bauen.zur_website(pfad.relative_to(WURZEL).as_posix()), pfad)


class AndereSeiten(unittest.TestCase):
    def test_due_diligence_verweist_auf_kaufbegutachtung(self):
        for sprache, pfad in DUE_DILIGENCE.items():
            inhalt = text(pfad)
            ziel = "/leistungen/kaufbegutachtung/" if sprache == "de" else "/en/pre-purchase-inspection-berlin/"
            self.assertIn(f'href="{ziel}"', inhalt)
            # Der frühere „Technische Kurzbericht“ ist ersetzt.
            self.assertNotIn("Technischer Kurzbericht", inhalt)
            self.assertNotIn("Building survey report", inhalt)

    def test_uebersichten_verlinken_die_seite(self):
        self.assertIn('href="/leistungen/kaufbegutachtung/"', text(UEBERSICHTEN["de"]))
        self.assertIn('href="/en/pre-purchase-inspection-berlin/"', text(UEBERSICHTEN["en"]))


if __name__ == "__main__":
    unittest.main()
