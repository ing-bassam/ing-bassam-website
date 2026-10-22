"""Prüft, dass die private Angebotsseite Kaufbegutachtung privat bleibt.

angebot/kaufbegutachtung/ zeigt Preise, Optionen, Hinweise nach Baujahr, Pflichten
nach dem Kauf und die Unterlagenliste – aber nur mit dem Schlüssel aus dem
persönlichen Link, den das Büro nach einer Anfrage verschickt. Die Inhalte liegen
ausschließlich verschlüsselt in paket.js (tools/angebot_verschluesseln.mjs).
Dieser Test stellt sicher:

- Die Seite soll nicht in Suchmaschinen: noindex, nofollow, kein Referrer, nicht
  in Sitemap, llms.txt oder robots.txt, von keiner anderen Seite verlinkt.
- Sicherheitsregeln der Website gelten: script-src 'self', connect-src 'none'.
- Ohne Schlüssel steht nur der Hinweis „Dieser Link ist nicht vollständig“ da.
- Im Klartext der Seite (HTML, Skripte, Stile) stehen keine Eurobeträge und keine
  Regeltexte; paket.js enthält nur das Chiffrat.
- werkzeuge/kaufbegutachtung/ (früher öffentlich mit allen Regeln) gibt es nicht mehr.
- Die Dateien werden ausgeliefert (Positivliste in tools/website_bauen.py).

Ver- und Entschlüsselung, Preislogik und E-Mail prüft tests/angebot.test.mjs.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import base64
import json
import re
import sys
import unittest
from html import unescape
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import website_bauen  # noqa: E402

ORDNER = WURZEL / "angebot" / "kaufbegutachtung"
SEITE = ORDNER / "index.html"
PAKET = ORDNER / "paket.js"
DATEIEN = ("index.html", "app.js", "angebot.js", "oberflaeche.js", "angebot.css", "paket.js")

# Eurobetrag: „1.234,50 €“, „100 €“, „€1,234.50“, „EUR 100“, „100 Euro“.
EUROBETRAG = re.compile(r"\d[\d.,]*(?:\s| )?(?:Mio\.\s?)?(?:€|EUR\b|Euro\b)|(?:€|\bEUR\b)(?:\s| )?\d")
# Kennzeichnende Stellen aus Hinweisregeln, Pflichten und Unterlagen. Sie dürfen weder
# auf der privaten Seite im Klartext noch öffentlich bei der Kaufbegutachtung stehen.
REGELTEXTE = (
    "Bleileitungen", "Blei verlegt", "lead pipes", "GModG", "§ 35", "TrinkwV", "Dämmpflicht", "Insulation duty",
    "Mietpreisbremse", "Mietspiegel", "Eigenbedarf", "Heizkostenverteiler", "BImSchV", "AwSV", "Hausschwamm",
    "Biomethan", "Nachtspeicher", "Teilungserklärung mit Gemeinschaftsordnung", "Verwalterbestätigung",
    "Wohngebäudeversicherung mit Schadenhistorie", "KfW", "Milieuschutzgebiet", "Thermografie nach",
)
OEFFENTLICH = (WURZEL / "leistungen" / "kaufbegutachtung" / "index.html",
               WURZEL / "en" / "pre-purchase-inspection-berlin" / "index.html")
LINK_FEHLT = {
    "de": "Dieser Link ist nicht vollständig. Bitte verwenden Sie den Link aus unserer E-Mail oder schreiben Sie an info@ing-bassam.de.",
    "en": "This link is incomplete. Please use the link from our email or write to info@ing-bassam.de.",
}


def nur_text(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", html)))


class Privat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = SEITE.read_text(encoding="utf-8")

    def test_kein_suchmaschinenindex(self):
        self.assertIn('<meta name="robots" content="noindex, nofollow">', self.html)
        self.assertIn('<meta name="referrer" content="no-referrer">', self.html)
        self.assertNotIn('rel="canonical"', self.html)
        self.assertNotIn("hreflang", self.html)
        self.assertNotIn("application/ld+json", self.html)
        self.assertNotIn('property="og:', self.html)

    def test_nicht_in_sitemap_llms_robots(self):
        for datei in ("sitemap.xml", "llms.txt", "robots.txt"):
            text = (WURZEL / datei).read_text(encoding="utf-8").lower()
            with self.subTest(datei=datei):
                self.assertNotIn("/angebot", text)
                self.assertNotIn("angebot/", text)

    def test_von_keiner_seite_verlinkt(self):
        funde = []
        for pfad in website_bauen.auswahl():
            if pfad.startswith("angebot/") or not pfad.endswith((".html", ".js", ".txt", ".xml", ".css")):
                continue
            if "/angebot/" in (WURZEL / pfad).read_text(encoding="utf-8", errors="replace"):
                funde.append(pfad)
        self.assertEqual(funde, [])

    def test_sicherheitsregeln(self):
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.html).group(1)
        for regel in ("default-src 'self'", "script-src 'self'", "connect-src 'none'", "object-src 'none'", "base-uri 'self'"):
            self.assertIn(regel, csp)
        self.assertNotIn("unsafe", csp)
        self.assertNotRegex(self.html, r"<script(?![^>]*\bsrc=\"/angebot/kaufbegutachtung/app\.js\")[^>]*>",
                            "nur das eigene Modul, kein eingebettetes Skript")
        # Externe Links ohne Referrer – in der Seite und in den Quellenangaben der Hinweise.
        for treffer in re.finditer(r'<a [^>]*href="https?://[^"]*"[^>]*>', self.html):
            self.assertIn("noreferrer", treffer.group(0))
        self.assertIn('rel: "noreferrer noopener"', (ORDNER / "app.js").read_text(encoding="utf-8"))

    def test_ohne_schluessel_nur_hinweis(self):
        text = nur_text(self.html)
        for satz in LINK_FEHLT.values():
            self.assertIn(satz, text)
        # Der eigentliche Inhalt entsteht erst im Browser, nach dem Entschlüsseln.
        self.assertRegex(self.html, r'<div id="angebot" hidden></div>')
        self.assertNotIn("<form", self.html)

    def test_keine_klartext_inhalte(self):
        funde = []
        for name in DATEIEN:
            roh = (ORDNER / name).read_text(encoding="utf-8")
            if name == "paket.js":
                roh = re.sub(r'"daten": "[^"]*"', '"daten": ""', roh)
            text = unescape(roh) if name.endswith(".html") else roh
            for treffer in EUROBETRAG.finditer(text):
                funde.append(f"{name}: Betrag …{text[max(0, treffer.start() - 40):treffer.end() + 10]}…")
            for wort in REGELTEXTE:
                if wort in text:
                    funde.append(f"{name}: {wort}")
        self.assertEqual(funde, [])

    def test_paket_nur_chiffrat(self):
        roh = PAKET.read_text(encoding="utf-8")
        self.assertNotIn("\r", roh)
        treffer = re.fullmatch(r"(?:// [^\n]*\n)+export const PAKET = (\{.*\});\n", roh, re.S)
        self.assertIsNotNone(treffer, "paket.js: nur Kopfkommentar und export const PAKET = {…}")
        paket = json.loads(treffer.group(1))
        self.assertEqual(set(paket), {"v", "iv", "daten"})
        self.assertEqual(paket["v"], 1)
        self.assertEqual(len(base64.b64decode(paket["iv"], validate=True)), 12)
        chiffrat = base64.b64decode(paket["daten"], validate=True)
        self.assertGreater(len(chiffrat), 1000)
        # Verschlüsselte Bytes sehen zufällig aus: kein JSON, kein lesbarer Text.
        self.assertFalse(chiffrat.lstrip().startswith(b"{"))
        lesbar = sum(32 <= b < 127 for b in chiffrat) / len(chiffrat)
        self.assertLess(lesbar, 0.5)
        self.assertNotIn(b"pflicht", chiffrat)

    def test_auslieferung(self):
        for name in DATEIEN:
            self.assertTrue(website_bauen.zur_website(f"angebot/kaufbegutachtung/{name}"), name)
        self.assertFalse(website_bauen.zur_website("angebot/kaufbegutachtung/inhalte.json"))
        self.assertFalse(website_bauen.zur_website("angebot/kaufbegutachtung/schluessel.txt"))
        # Klartext-Quelle und Schlüssel liegen nie im Repository.
        for muster in ("*.json", "*.txt", "*.md", "*.key"):
            self.assertEqual(sorted(p.name for p in (WURZEL / "angebot").rglob(muster)), [], muster)


class OeffentlicheSeiten(unittest.TestCase):
    def test_keine_regeltexte_mehr_oeffentlich(self):
        for pfad in OEFFENTLICH:
            text = unescape(pfad.read_text(encoding="utf-8"))
            for wort in REGELTEXTE:
                with self.subTest(seite=pfad.parent.name, wort=wort):
                    self.assertNotIn(wort, text)

    def test_werkzeuge_ohne_regeln(self):
        ordner = WURZEL / "werkzeuge" / "kaufbegutachtung"
        self.assertFalse(ordner.exists() and any(ordner.iterdir()), "werkzeuge/kaufbegutachtung/ muss leer sein oder fehlen")
        for pfad in (WURZEL / "werkzeuge").rglob("*"):
            if pfad.is_file() and pfad.suffix in (".js", ".html"):
                text = pfad.read_text(encoding="utf-8")
                for wort in ("Bleileitungen", "GModG", "Mietpreisbremse", "Eigenbedarf"):
                    with self.subTest(datei=pfad.relative_to(WURZEL).as_posix(), wort=wort):
                        self.assertNotIn(wort, text)


if __name__ == "__main__":
    unittest.main()
