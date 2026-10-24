"""Tests für tools/normstand_pruefen.py mit einem erfundenen Normindex.

Normnummern und Themen sind erfunden; der Index enthält wie das Original nur
Metadaten, keinen Normtext.

Aufruf: python -m unittest discover -s tests
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import normstand_pruefen as n  # noqa: E402

INDEX = """# Nur Metadaten (Norm, Thema, Ausgabe) – kein Normtext.
stand_index: '2026-10-16'
quelle: test
normen:
  - norm: DIN 4711-1
    schluessel: DIN 4711-1
    thema: Erfundene Prüfnorm
    sachgebiet: 99 Test
    neueste: '2024-05'
    aeltere: ['2013-04', '2018-01']
    aenderungen: []
    berichtigungen: []
    sprache: DE
    pruefen: false
  - norm: DIN EN 9999-1-1-NA
    schluessel: DIN EN 9999-1-1-NA
    neueste: '2013-04'
    aenderungen: []
    berichtigungen: ['Berichtigung 1:2015-02']
    pruefen: false
  - norm: VDI 9876 Blatt 1
    schluessel: VDI 9876 BLATT 1
    neueste: '2018-01'
    pruefen: false
  - norm: DIN-TS 4711-8
    schluessel: DIN-TS 4711-8
    neueste: '2022-09'
    pruefen: false
  - norm: DIN 4712
    schluessel: DIN 4712
    neueste: '2025-10'
    aenderungen: ['A1:2026-09']
    pruefen: false
  - norm: DIN 4713
    schluessel: DIN 4713
    neueste: '2019-07'
    pruefen: true
    pruefgrund: ['Thema im Index leer']
"""


class Grundlage(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.ordner.name)
        self.index = self.wurzel / "normen" / "ausgaben.yml"
        self.index.parent.mkdir()
        self.index.write_text(INDEX, encoding="utf-8", newline="\n")

    def tearDown(self):
        self.ordner.cleanup()

    def entwurf(self, rumpf: str, name: str = "entwurf.md", kopf: str = "") -> Path:
        pfad = self.wurzel / name
        pfad.write_text(f"---\ntitel: \"Test\"\n{kopf}status: Entwurf\n---\n\n# Test\n\n{rumpf}",
                        encoding="utf-8", newline="\n")
        return pfad

    def starten(self, *dateien: Path, index: Path | None = None) -> tuple[int, str, str, dict]:
        bericht, daten = self.wurzel / "aus" / "bericht.md", self.wurzel / "aus" / "bericht.json"
        ausgabe = io.StringIO()
        with mock.patch.object(sys, "argv", ["normstand_pruefen.py", *map(str, dateien),
                                             "--ausgaben", str(index or self.index),
                                             "--bericht", str(bericht), "--json", str(daten)]), \
                redirect_stdout(ausgabe):
            code = n.main()
        return (code, ausgabe.getvalue(), bericht.read_text(encoding="utf-8"),
                json.loads(daten.read_text(encoding="utf-8")))

    def stufen(self, daten: dict) -> list[tuple]:
        return [(z["regelwerk"], z["genannt"], z["stufe"]) for z in daten["zeilen"]]


class Ausgaben(Grundlage):
    def test_aeltere_ausgabe_ist_fehler(self):
        code, ausgabe, bericht, daten = self.starten(self.entwurf("Nach DIN 4711-1:2018-01 wird die Fuge geprüft.\n"))
        self.assertEqual(code, 1)
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "2018-01", "FEHLER")])
        self.assertEqual(daten["zeilen"][0]["zeile"], 8)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "fehler=1 hinweise=0")
        self.assertIn("## Stand der Technik – Normausgaben", bericht)
        self.assertIn("| Datei | Zeile | Regelwerk | genannte Ausgabe | neueste in der Fachbibliothek | Ergebnis |",
                      bericht)
        self.assertIn("| 8 | DIN 4711-1 | 2018-01 | 2024-05 | FEHLER:", bericht)

    def test_damals_geltende_ausgabe_ist_hinweis(self):
        code, ausgabe, _, daten = self.starten(self.entwurf(
            "Bei der Abnahme 2016 war die Lage anders. Damals galt DIN 4711-1:2013-04 für die Fugen.\n"))
        self.assertEqual(code, 0)
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "2013-04", "HINWEIS")])
        self.assertIn("frühere oder stichtagsbezogene Fassung", daten["zeilen"][0]["ergebnis"])
        self.assertEqual(ausgabe.strip().splitlines()[-1], "fehler=0 hinweise=1")

    def test_kennzeichnung_gilt_nur_im_selben_satz(self):
        code, _, _, daten = self.starten(self.entwurf(
            "Damals war vieles anders. Heute gilt DIN 4711-1:2018-01 für die Fugen.\n"))
        self.assertEqual(code, 1)

    def test_ersetzt_kennzeichnet_nur_die_aeltere_von_zwei_ausgaben(self):
        rumpf = ("Text.[^1]\n\n## Quellen und Fußnoten\n\n[^1]: DIN Media: DIN 4711-1:2018-01 „Erfundener Titel“, "
                 "ersetzt DIN 4711-1:2013-04. https://example.org/din-4711-1:2013-04 (abgerufen am 2026-10-20).\n")
        code, _, _, daten = self.starten(self.entwurf(rumpf))
        self.assertEqual(code, 1)
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "2018-01", "FEHLER"),
                                              ("DIN 4711-1", "2013-04", "HINWEIS")])

    def test_englischer_leitfaden_replaces(self):
        rumpf = ("[^din]: DIN Media: DIN 4711-1:2024-05 (invented title). Edition 2024-05, "
                 "replaces DIN 4711-1:2018-01.\n")
        code, _, _, daten = self.starten(self.entwurf(rumpf))
        self.assertEqual(code, 0)
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "2024-05", "OK"), ("DIN 4711-1", "2018-01", "HINWEIS")])

    def test_neueste_ausgabe_in_verschiedenen_schreibweisen(self):
        rumpf = ("DIN 4711-1:2024-05 regelt es. Ebenso DIN 4711-1 (2024-05) und DIN 4711-1, Ausgabe Mai 2024.\n\n"
                 "VDI 9876 Blatt 1:2018-01 und DIN/TS 4711-8:2022-09 sowie DIN EN 9999-1-1/NA:2013-04 "
                 "mit DIN EN 9999-1-1/NA Berichtigung 1:2015-02.\n\n"
                 "[^1]: DIN Media: DIN 4711-1 – 2024-05. Dazu DIN\N{NO-BREAK SPACE}4711-8 nicht, "
                 "aber DIN-TS 4711-8.\n")
        code, ausgabe, _, daten = self.starten(self.entwurf(rumpf))
        self.assertEqual(code, 0, ausgabe)
        self.assertEqual(daten["fehler"] + daten["hinweise"], 1, daten["zeilen"])   # nur DIN 4711-8 unbekannt
        ok = {(z["regelwerk"], z["genannt"]) for z in daten["zeilen"] if z["stufe"] == "OK"}
        self.assertEqual(ok, {("DIN 4711-1", "2024-05"), ("VDI 9876 Blatt 1", "2018-01"),
                              ("DIN/TS 4711-8", "2022-09"), ("DIN EN 9999-1-1/NA", "2013-04"),
                              ("DIN EN 9999-1-1/NA Berichtigung 1", "2015-02")})

    def test_weitere_schreibweisen_der_ausgabe(self):
        for rumpf in ("Maßgeblich ist DIN 4711-1 (Ausgabe 2018-01) für die Fuge.",
                      "Maßgeblich ist DIN 4711-1 in der Fassung 2018-01 für die Fuge.",
                      "Maßgeblich ist DIN 4711-1 vom Januar 2018 für die Fuge.",
                      "Maßgeblich ist DIN 4711-1, Ausgabe 01/2018, für die Fuge.",
                      "Maßgeblich ist DIN 4711-1 in der Fassung von 2018 für die Fuge.",
                      "Maßgeblich ist DIN 4711-1 aus dem Jahr 2018 für die Fuge."):
            with self.subTest(rumpf=rumpf):
                code, _, _, daten = self.starten(self.entwurf(rumpf + "\n"))
                self.assertEqual(code, 1, daten["zeilen"])
                self.assertEqual([z["stufe"] for z in daten["zeilen"]], ["FEHLER"])
                self.assertTrue(daten["zeilen"][0]["genannt"].startswith("2018"))

    def test_kennzeichnung_nur_fuer_die_gemeinte_nennung(self):
        faelle = {
            # „Status aktuell“ stellt die genannte Ausgabe als geltend dar – „ersetzt die Ausgabe …“ ändert das nicht
            "[^1]: DIN 4711-1:2018-01 „Erfundener Titel“, Status aktuell, ersetzt die Ausgabe 2016-07.": "FEHLER",
            # Ein anderes „ersetzt“ nach dem Semikolon kennzeichnet nichts
            "Es gilt DIN 4711-1:2013-04; sie ersetzt keine vertragliche Vereinbarung.": "FEHLER",
            # „im Jahr“ nur mit dem Jahr der Ausgabe
            "Es gilt DIN 4711-1:2013-04, wie schon im Jahr 2020 empfohlen.": "FEHLER",
            "Im Jahr 2013 erschien DIN 4711-1:2013-04 und war für die Fuge maßgeblich.": "HINWEIS",
            # „ersetzt“ hinter der Nennung kennzeichnet nur, wenn sie ersetzt wurde
            "DIN 4711-1:2013-04 regelt die Fuge und ersetzt keine Prüfung vor Ort.": "FEHLER",
            "DIN 4711-1:2013-04 wurde durch die Ausgabe 2024-05 ersetzt.": "HINWEIS",
            "DIN 4711-1:2013-04, ersetzt durch die Ausgabe 2024-05, regelte die Fuge.": "HINWEIS",
            "Die inzwischen ersetzte DIN 4711-1:2013-04 regelte die Fuge.": "HINWEIS",
        }
        for rumpf, stufe in faelle.items():
            with self.subTest(rumpf=rumpf):
                _, _, _, daten = self.starten(self.entwurf(rumpf + "\n"))
                self.assertEqual([z["stufe"] for z in daten["zeilen"]], [stufe], daten["zeilen"])

    def test_ersetzt_kennzeichnet_eine_aufzaehlung(self):
        rumpf = ("[^1]: DIN Media: DIN 4711-1:2024-05 „Erfundener Titel“, Status aktuell, ersetzt DIN 4711-1:2013-04 "
                 "und DIN 4711-1:2018-01.\n")
        code, _, _, daten = self.starten(self.entwurf(rumpf))
        self.assertEqual(code, 0, daten["zeilen"])
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "2024-05", "OK"), ("DIN 4711-1", "2013-04", "HINWEIS"),
                                              ("DIN 4711-1", "2018-01", "HINWEIS")])

    def test_neuer_als_bibliothek_ist_hinweis(self):
        code, _, _, daten = self.starten(self.entwurf("DIN 4711-1:2026-01 ist erschienen.\n"))
        self.assertEqual(code, 0)
        self.assertIn("neuer als die Fachbibliothek", daten["zeilen"][0]["ergebnis"])


class Hinweise(Grundlage):
    def test_ohne_ausgabe_ist_hinweis(self):
        code, _, _, daten = self.starten(self.entwurf("DIN 4711-1 regelt die Fuge. Auch DIN 4711-1 hilft.\n"))
        self.assertEqual(code, 0)
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "", "HINWEIS")])
        self.assertIn("ohne Ausgabe genannt – neueste Ausgabe 2024-05 angeben", daten["zeilen"][0]["ergebnis"])

    def test_ohne_ausgabe_genuegt_wenn_fussnote_die_ausgabe_nennt(self):
        code, _, _, daten = self.starten(self.entwurf(
            "DIN 4711-1 regelt die Fuge.[^1]\n\n[^1]: DIN Media: DIN 4711-1:2024-05.\n"))
        self.assertEqual(code, 0)
        self.assertEqual(self.stufen(daten), [("DIN 4711-1", "2024-05", "OK")])

    def test_unbekannte_norm_ist_hinweis(self):
        code, ausgabe, _, daten = self.starten(self.entwurf("Nach DIN EN ISO 12345-6:2020-01 und VDE 0815.\n"))
        self.assertEqual(code, 0)
        self.assertEqual([z["regelwerk"] for z in daten["zeilen"]], ["DIN EN ISO 12345-6", "VDE 0815"])
        self.assertTrue(all("Status bei DIN Media prüfen" in z["ergebnis"] for z in daten["zeilen"]))
        self.assertEqual(ausgabe.strip().splitlines()[-1], "fehler=0 hinweise=2")

    def test_aenderung_nicht_genannt(self):
        code, _, _, daten = self.starten(self.entwurf("Es gilt DIN 4712:2025-10.\n"))
        self.assertEqual(code, 0)
        self.assertIn("A1:2026-09", " ".join(z["ergebnis"] for z in daten["zeilen"]))
        code, _, _, daten = self.starten(self.entwurf("Es gilt DIN 4712:2025-10 mit DIN 4712/A1:2026-09.\n"))
        self.assertEqual(daten["hinweise"], 0, daten["zeilen"])

    def test_auffaelliger_indexeintrag(self):
        _, _, _, daten = self.starten(self.entwurf("DIN 4713:2019-07 gilt.\n"))
        self.assertEqual([z["stufe"] for z in daten["zeilen"]], ["HINWEIS", "OK"])
        self.assertIn("Thema im Index leer", daten["zeilen"][0]["ergebnis"])

    def test_dateikopf_nur_regelwerke_bestaetigt(self):
        datei = self.entwurf("Text ohne Norm.\n",
                             kopf="schlagwoerter: DIN 4711-1:2013-04, Fuge\n"
                                  "regelwerke_bestaetigt: BGH VII ZR 1/26, DIN 4711-1:2018-01\n")
        code, _, _, daten = self.starten(datei)
        self.assertEqual(code, 1)
        self.assertEqual([(z["zeile"], z["genannt"], z["stufe"]) for z in daten["zeilen"]], [(4, "2018-01", "FEHLER")])

    def test_keine_normzitate(self):
        code, ausgabe, bericht, _ = self.starten(self.entwurf("Die DIN-Norm und DIN Media ohne Nummer.\n"))
        self.assertEqual(code, 0)
        self.assertIn("Keine Normzitate gefunden.", bericht)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "fehler=0 hinweise=0")

    def test_mehrere_entwuerfe(self):
        a = self.entwurf("DIN 4711-1:2018-01.\n", name="a.md")
        b = self.entwurf("DIN 4711-1:2024-05.\n", name="b.md")
        code, _, _, daten = self.starten(a, b)
        self.assertEqual(code, 1)
        self.assertEqual([(z["datei"].rsplit("/", 1)[-1], z["stufe"]) for z in daten["zeilen"]],
                         [("a.md", "FEHLER"), ("b.md", "OK")])


class OhneIndex(Grundlage):
    def test_index_fehlt_exit_2(self):
        code, ausgabe, bericht, daten = self.starten(self.entwurf("DIN 4711-1:2018-01.\n"),
                                                     index=self.wurzel / "fehlt.yml")
        self.assertEqual(code, 2)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "fehler=nicht-geprueft")
        self.assertIn("Nicht geprüft", bericht)
        self.assertFalse(daten["geprueft"])

    def test_index_unlesbar_exit_2(self):
        self.index.write_text("normen: [kein: gueltiges: yaml\n", encoding="utf-8")
        code, ausgabe, _, _ = self.starten(self.entwurf("DIN 4711-1:2018-01.\n"))
        self.assertEqual(code, 2)
        self.assertTrue(ausgabe.strip().endswith("fehler=nicht-geprueft"))


class Schluessel(unittest.TestCase):
    def test_schreibweisen_ergeben_denselben_schluessel(self):
        self.assertEqual(n.schluessel("DIN/TS 4108-8"), n.schluessel("DIN-TS 4108-8"))
        self.assertEqual(n.schluessel("DIN EN 1996-2/NA"), n.schluessel("DIN EN 1996-2-NA"))
        self.assertEqual(n.schluessel("vdi 6022  Blatt 1"), "VDI 6022 BLATT 1")
        self.assertEqual(n.schluessel("DIN 4109-1/A1:2026-09"), "DIN 4109-1")
        self.assertEqual(n.schluessel("DIN 4108 Teil 2"), "DIN 4108-2")


if __name__ == "__main__":
    unittest.main()
