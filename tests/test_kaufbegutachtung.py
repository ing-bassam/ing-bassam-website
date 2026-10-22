"""Prüft die Seiten zur Kaufbegutachtung gegen ihre einzige Datenquelle.

werkzeuge/kaufbegutachtung/daten.js enthält Preise, Regeln, Unterlagen und
Texte. Der Rechner liest sie im Browser; die festen Abschnitte der Seiten (für
Besucher ohne JavaScript, Suchmaschinen und KI-Crawler) erzeugt
tools/kaufbegutachtung_bauen.py daraus. Dieser Test stellt sicher:

- Die Daten sind in sich stimmig (Verweise auf Optionen, Eingaben, Kategorien).
- Jede Regel-ID und jeder Bruttopreis steht im HTML beider Sprachfassungen.
- Die festen Abschnitte entsprechen den Daten (sonst Skript ausführen).
- Jeder Betrag mit Cent auf den betroffenen Seiten ist ein Preis aus den Daten –
  ein veralteter Preis fällt so auf, auch auf der Due-Diligence-Seite.
- „x € (y € netto)“ in den Texten passt zu y × 1,19.
- Die Anker der QR-Codes (#wohnung, #haus, #flat, #house) bleiben erhalten.

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
BETRAG = {"de": re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2}) €"), "en": re.compile(r"€(\d{1,3}(?:,\d{3})*\.\d{2})")}
BRUTTO_NETTO = {"de": re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2}) €(?: je Stunde)? \((\d+(?:,\d{2})?) € netto\)"),
                "en": re.compile(r"€(\d{1,3}(?:,\d{3})*\.\d{2})(?: per hour)? \(€(\d+(?:\.\d{2})?) net\)")}


def text(pfad: Path) -> str:
    return unescape(pfad.read_text(encoding="utf-8"))


def cent(betrag: str, sprache: str) -> int:
    if sprache == "de":
        betrag = betrag.replace(".", "").replace(",", ".")
    else:
        betrag = betrag.replace(",", "")
    return round(float(betrag) * 100)


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
                self.assertLessEqual(set(r.get("empfiehlt", [])), set(d["optionen"]))
                if "von" in r and "bis" in r:
                    self.assertLessEqual(r["von"], r["bis"])
                for sprache in ("de", "en"):
                    self.assertTrue(r[sprache]["titel"] and r[sprache]["text"])
                self.assertTrue(r["quelle"]["titel"])
                self.assertTrue(r["quelle"]["url"] == "" or r["quelle"]["url"].startswith("https://"))
        for objekt in kb.OBJEKTE:
            paket = d["pakete"][objekt]
            self.assertLessEqual(set(paket["optionen"]), set(d["optionen"]), objekt)
            for z in paket["zuschlaege"]:
                schalter_id = z.get("auto", {}).get("schalter")
                if schalter_id:
                    self.assertEqual(d["eingaben"]["preis_schalter"][schalter_id]["objekt"], objekt, z["id"])
            unterlagen = [u["id"] for u in d["unterlagen"][objekt]]
            self.assertEqual(len(unterlagen), len(set(unterlagen)), objekt)
            for u in d["unterlagen"][objekt]:
                self.assertIn(u["prio"], (1, 2, 3))
                self.assertLessEqual(set(u.get("heizung", [])), heizung)
                self.assertLessEqual(set(u.get("nutzung", [])), nutzung)
        self.assertEqual(set(d["seite"]["de"]["kategorien"]), set(kb.KATEGORIEN))
        self.assertEqual(set(d["seite"]["de"]["ui"]), set(d["seite"]["en"]["ui"]))

    def test_brutto_und_netto_in_texten_passen(self):
        # „71,40 € (60 € netto)“: der Bruttobetrag muss netto × 1,19 sein.
        gefunden = 0
        quellen = [text(kb.DATEN_JS), *(text(p) for p in DUE_DILIGENCE.values()), *(text(p) for p in UEBERSICHTEN.values())]
        for sprache in ("de", "en"):
            for brutto, netto in (paar for q in quellen for paar in BRUTTO_NETTO[sprache].findall(q)):
                gefunden += 1
                with self.subTest(sprache=sprache, brutto=brutto, netto=netto):
                    netto_wert = netto.replace(",", ".") if sprache == "de" else netto
                    self.assertEqual(cent(brutto, sprache), kb.brutto_cent(netto_wert, self.d["mwst"]))
        self.assertGreater(gefunden, 3)


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

    def test_jeder_bruttopreis_in_beiden_sprachen(self):
        for sprache, inhalt in self.html.items():
            for p in kb.posten(self.d):
                with self.subTest(sprache=sprache, posten=p["id"]):
                    self.assertIn(kb.euro_spanne(p["brutto_von"], p["brutto_bis"], sprache), inhalt)
                    self.assertIn(kb.euro_spanne(p["netto_von"], p["netto_bis"], sprache), inhalt)

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


class Preisangaben(unittest.TestCase):
    """Beträge mit Cent auf den betroffenen Seiten stammen aus den Daten."""

    @classmethod
    def setUpClass(cls):
        d = kb.daten_laden()
        bekannt = set()
        for p in kb.posten(d):
            bekannt |= {p["brutto_von"], p["brutto_bis"], p["netto_von"], p["netto_bis"]}
        # Preise, die in den Texten als „brutto (netto)“ stehen, z. B. jede weitere Schadstoffprobe.
        for brutto, _ in BRUTTO_NETTO["de"].findall(text(kb.DATEN_JS)):
            bekannt.add(cent(brutto, "de"))
        cls.bekannt = bekannt
        cls.d = d

    def test_nur_bekannte_betraege(self):
        seiten = {**{("neu", s): p for s, p in SEITEN.items()},
                  **{("dd", s): p for s, p in DUE_DILIGENCE.items()},
                  **{("uebersicht", s): p for s, p in UEBERSICHTEN.items()}}
        for (art, sprache), pfad in seiten.items():
            inhalt = text(pfad)
            for betrag in BETRAG[sprache].findall(inhalt):
                with self.subTest(seite=pfad.relative_to(WURZEL).as_posix(), betrag=betrag):
                    self.assertIn(cent(betrag, sprache), self.bekannt)

    def test_due_diligence_verweist_auf_kaufbegutachtung(self):
        for sprache, pfad in DUE_DILIGENCE.items():
            inhalt = text(pfad)
            ziel = "/leistungen/kaufbegutachtung/" if sprache == "de" else "/en/pre-purchase-inspection-berlin/"
            self.assertIn(f'href="{ziel}"', inhalt)
            for objekt in kb.OBJEKTE:
                grund = kb.preis_von(self.d, self.d["pakete"][objekt]["grund"]["id"])
                self.assertIn(kb.euro(grund["brutto_von"], sprache), inhalt)
            # Der frühere „Technische Kurzbericht ab 1.290 €“ ist ersetzt.
            self.assertNotIn("Technischer Kurzbericht", inhalt)
            self.assertNotIn("Building survey report", inhalt)
            self.assertNotIn('"price": "1290"', inhalt)

    def test_uebersichten_verlinken_die_seite(self):
        self.assertIn('href="/leistungen/kaufbegutachtung/"', text(UEBERSICHTEN["de"]))
        self.assertIn('href="/en/pre-purchase-inspection-berlin/"', text(UEBERSICHTEN["en"]))


if __name__ == "__main__":
    unittest.main()
