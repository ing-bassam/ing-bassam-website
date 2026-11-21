"""Prüft das Änderungsdatum (lastmod) der von Hand gepflegten Seiten in der Sitemap
(tools/sitemap_stand.py).

Hintergrund (November 2026): Startseite, Leistungsseiten, englische Seiten und das
Mängelanzeige-Werkzeug standen mit dem Datum ihres ersten Eintrags in der Sitemap,
auch nachdem ihr Text geändert worden war; die Startseite trug das Datum des
neuesten Fachbeitrags. Google und Bing werten lastmod nur aus, wenn es verlässlich
zum Seiteninhalt passt. Der Seitenbau merkt sich deshalb je Seite eine Kennung des
Inhalts und setzt das Datum neu, sobald sie abweicht.

Geprüft wird die Regel, nicht der Tagesstand: Ob die Kennung in der Sitemap zum
heutigen Seiteninhalt passt, klärt der Seitenbau selbst, sobald er läuft.

Aufruf: python -m unittest discover -s tests
"""
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import sitemap_stand as s  # noqa: E402

SEITE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Schimmelgutachten in Berlin</title>
  <meta name="description" content="Ursache, Messung und Bericht.">
  <link rel="stylesheet" href="/leistungen/seiten.css">
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "Service", "name": "Schimmelgutachten"}
  </script>
</head>
<body>
  <header><nav><a href="/">Start</a> <a href="/leistungen/">Leistungen</a></nav></header>
  <main id="inhalt">
    <h1 class="titel">Schimmelgutachten</h1>
    <p>Wir messen Feuchte und Temperatur &amp; schreiben einen Bericht.</p>
    <p><a href="/fachwissen/schimmel/">Mehr zum Thema</a> <img src="/bilder/wand.jpg" alt="Wand mit Schimmel"></p>
  </main>
  <footer><p>Ingenieurbüro für Bauwesen</p></footer>
  <script src="/menue.js"></script>
</body>
</html>
"""
# Kennung der Beispielseite oben. Ändert sich dieser Wert, wurde die Berechnung geändert.
KENNUNG_DER_BEISPIELSEITE = "98c36e0910a1"

A = "https://ing-bassam.de/"
B = "https://ing-bassam.de/leistungen/schimmelgutachten/"


def sitemap(staende: dict[str, tuple[str, str | None]]) -> str:
    """Sitemap im Format des Seitenbaus aus dem Ergebnis von sitemap_stand.staende()."""
    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for ort, (datum, kennung) in staende.items():
        zeilen += ["  <url>", f"    <loc>{ort}</loc>", f"    <lastmod>{datum}</lastmod>",
                   "    <changefreq>monthly</changefreq>", "    <priority>0.8</priority>"]
        if kennung:
            zeilen.append(s.kennzeile(kennung))
        zeilen.append("  </url>")
    return "\n".join(zeilen + ["</urlset>"]) + "\n"


class Fingerabdruck(unittest.TestCase):
    def test_form(self):
        self.assertRegex(s.fingerabdruck(SEITE), r"^[0-9a-f]{12}$")

    def test_gestaltung_und_rahmen_zaehlen_nicht(self):
        gleich = {
            "Zeilenenden wie unter Windows": SEITE.replace("\n", "\r\n"),
            "andere Einrückung": SEITE.replace("\n  ", "\n\t\t\t"),
            "andere Klasse": SEITE.replace('class="titel"', 'class="titel gross"'),
            "Menü erweitert": SEITE.replace("</nav>", ' <a href="/kontakt/">Kontakt</a></nav>'),
            "Fußzeile geändert": SEITE.replace("Ingenieurbüro für Bauwesen</p>", "Ingenieurbüro für Bauwesen, Berlin</p>"),
            "anderes Stylesheet": SEITE.replace("/leistungen/seiten.css", "/leistungen/seiten.css?v=2"),
            "anderes Skript": SEITE.replace("/menue.js", "/menue-neu.js"),
            "Kommentar im Hauptteil": SEITE.replace("<h1", "<!-- Hinweis für die Pflege --><h1"),
            "Zeichen anders kodiert": SEITE.replace("&amp;", "&#38;"),
        }
        for name, variante in gleich.items():
            with self.subTest(name):
                self.assertNotEqual(variante, SEITE)
                self.assertEqual(s.fingerabdruck(variante), s.fingerabdruck(SEITE))

    def test_inhalt_zaehlt(self):
        anders = {
            "Text im Hauptteil": SEITE.replace("Feuchte und Temperatur", "Feuchte, Temperatur und Luftwechsel"),
            "Titel": SEITE.replace("<title>Schimmelgutachten in Berlin", "<title>Schimmelgutachten Berlin"),
            "Beschreibung": SEITE.replace("Ursache, Messung und Bericht.", "Ursache und Bericht."),
            "Linkziel": SEITE.replace("/fachwissen/schimmel/", "/fachwissen/schimmel-ursachen/"),
            "Bild": SEITE.replace("/bilder/wand.jpg", "/bilder/decke.jpg"),
            "Bildtext": SEITE.replace("Wand mit Schimmel", "Außenwand mit Schimmel"),
            "Strukturdaten": SEITE.replace('"name": "Schimmelgutachten"', '"name": "Schimmel- und Feuchtegutachten"'),
        }
        for name, variante in anders.items():
            with self.subTest(name):
                self.assertNotEqual(s.fingerabdruck(variante), s.fingerabdruck(SEITE))

    def test_seite_ohne_hauptteil(self):
        """Ohne <main> zählt der <body>, ohne beides der ganze Text – kein Abbruch."""
        ohne_main = SEITE.replace('<main id="inhalt">', "<div>").replace("</main>", "</div>")
        self.assertRegex(s.fingerabdruck(ohne_main), r"^[0-9a-f]{12}$")
        self.assertNotEqual(s.fingerabdruck(ohne_main.replace("Feuchte", "Nässe")), s.fingerabdruck(ohne_main))
        self.assertNotEqual(s.fingerabdruck("Nur Text"), s.fingerabdruck("Anderer Text"))

    def test_berechnung_unveraendert(self):
        self.assertEqual(
            s.fingerabdruck(SEITE), KENNUNG_DER_BEISPIELSEITE,
            "Die Berechnung der Inhaltskennung liefert einen anderen Wert als bisher. Bleibt es dabei, "
            "KENNUNG_FASSUNG in tools/sitemap_stand.py erhöhen und den Wert hier anpassen – sonst "
            "bekommen alle von Hand gepflegten Seiten in der Sitemap auf einmal das heutige Datum.")


class Datumsregel(unittest.TestCase):
    def test_einzelfaelle(self):
        self.assertEqual(s.datum(None, None, "aaa", "2026-11-19"), "2026-11-19", "neue Seite: Datum des Laufs")
        self.assertEqual(s.datum("2026-10-04", None, "aaa", "2026-11-19"), "2026-10-04", "ohne Vergleich kein neues Datum")
        self.assertEqual(s.datum("2026-10-04", "aaa", "aaa", "2026-11-19"), "2026-10-04", "unverändert")
        self.assertEqual(s.datum("2026-10-04", "aaa", "bbb", "2026-11-19"), "2026-11-19", "geändert")

    def test_erster_lauf_und_zweiter_lauf(self):
        seiten = {A: SEITE, B: SEITE.replace("Schimmelgutachten", "Feuchtegutachten")}
        erster = s.staende([A, B], "", seiten.get, "2026-11-19")
        self.assertEqual(erster[A], ("2026-11-19", s.fingerabdruck(seiten[A])))
        self.assertNotEqual(erster[A][1], erster[B][1])
        # Ein späterer Lauf ohne Änderung lässt alles stehen – sonst entstünde bei jedem Lauf ein Commit.
        zweiter = s.staende([A, B], sitemap(erster), seiten.get, "2026-12-01")
        self.assertEqual(zweiter, erster)
        self.assertEqual(sitemap(zweiter), sitemap(erster))

    def test_geaenderte_seite_bekommt_das_datum_des_laufs(self):
        seiten = {A: SEITE, B: SEITE}
        vorher = s.staende([A, B], "", seiten.get, "2026-11-19")
        seiten[B] = SEITE.replace("einen Bericht", "ein Gutachten")
        nachher = s.staende([A, B], sitemap(vorher), seiten.get, "2026-12-01")
        self.assertEqual(nachher[A], vorher[A], "unveränderte Seite behält ihr Datum")
        self.assertEqual(nachher[B][0], "2026-12-01")
        self.assertNotEqual(nachher[B][1], vorher[B][1])

    def test_nur_gestaltung_geaendert(self):
        seiten = {A: SEITE}
        vorher = s.staende([A], "", seiten.get, "2026-11-19")
        seiten[A] = SEITE.replace('class="titel"', 'class="titel gross"').replace("</nav>", ' <a href="/x/">X</a></nav>')
        self.assertEqual(s.staende([A], sitemap(vorher), seiten.get, "2026-12-01"), vorher)

    def test_altbestand_ohne_kennung(self):
        """Eine Sitemap aus der Zeit vor den Kennungen: Datum bleibt, Kennung wird nachgetragen."""
        alt = sitemap({A: ("2026-10-04", None)})
        self.assertNotIn("inhalt:", alt)
        self.assertEqual(s.staende([A], alt, {A: SEITE}.get, "2026-11-19"),
                         {A: ("2026-10-04", s.fingerabdruck(SEITE))})

    def test_kennung_anderer_fassung_gilt_als_unbekannt(self):
        alt = sitemap({A: ("2026-10-04", None)}).replace(
            "  </url>", "    <!-- inhalt:0:aaaaaaaaaaaa -->\n  </url>")
        self.assertEqual(s.kennungen_lesen(alt), {})
        self.assertEqual(s.staende([A], alt, {A: SEITE}.get, "2026-11-19")[A][0], "2026-10-04")

    def test_fehlende_seite(self):
        alt = sitemap({A: ("2026-10-04", "aaaaaaaaaaaa")})
        self.assertEqual(s.staende([A], alt, {}.get, "2026-11-19"), {A: ("2026-10-04", None)})
        self.assertEqual(s.staende([B], alt, {}.get, "2026-11-19"), {B: ("2026-11-19", None)})


class Bestand(unittest.TestCase):
    """Die sitemap.xml im Repository."""

    @classmethod
    def setUpClass(cls):
        cls.text = (WURZEL / "sitemap.xml").read_text(encoding="utf-8")

    def test_gueltiges_xml_mit_datum(self):
        raum = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        eintraege = ET.fromstring(self.text.encode("utf-8")).findall(f"{raum}url")
        self.assertGreater(len(eintraege), 50)
        for eintrag in eintraege:
            ort = eintrag.findtext(f"{raum}loc") or ""
            with self.subTest(ort):
                self.assertRegex(eintrag.findtext(f"{raum}lastmod") or "", r"^\d{4}-\d{2}-\d{2}$")

    def test_kennung_stoert_andere_werkzeuge_nicht(self):
        """tools/indexnow.py liest Adresse und lastmod mit demselben Muster wie daten_lesen():
        Die Kennung steht deshalb hinter den Angaben, nie zwischen Adresse und Datum."""
        self.assertEqual(len(s.daten_lesen(self.text)), self.text.count("<loc>"))

    def test_von_hand_gepflegte_seiten_tragen_eine_kennung(self):
        """Beiträge und englische Leitfäden haben ihr Datum im Frontmatter, die Übersicht
        /fachwissen/ folgt dem neuesten Beitrag. Jede andere Seite braucht die Kennung."""
        mit_datum = re.compile(r"^https://ing-bassam\.de/(fachwissen/((?!vorlagen/)[^/]+/)?|en/guides/.*)$")
        kennungen = s.kennungen_lesen(self.text)
        von_hand = [ort for ort in s.daten_lesen(self.text) if not mit_datum.match(ort)]
        self.assertIn("https://ing-bassam.de/", von_hand)
        self.assertIn("https://ing-bassam.de/leistungen/", von_hand)
        self.assertIn("https://ing-bassam.de/fachwissen/vorlagen/", von_hand)
        fehlend = [ort for ort in von_hand if ort not in kennungen]
        self.assertEqual(fehlend, [], "Ohne Kennung bleibt das Änderungsdatum dieser Seiten stehen – "
                                      "Seitenbau laufen lassen: python tools/artikel_generator.py")


if __name__ == "__main__":
    unittest.main()
