"""Tests für den Aufruf --norm von tools/bibliothek_suchen.py mit einem kleinen Normenindex.

Der Index (normen/ausgaben.yml im Repository FachwissenAgent) enthält nur
Metadaten – Norm, Thema, Ausgaben –, keinen Normtext.

Aufruf: python -m unittest discover -s tests
"""
import datetime as dt
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import bibliothek_suchen as b  # noqa: E402

INDEX = """# Nur Metadaten (Norm, Thema, Ausgabe) – kein Normtext.
stand_index: '{stand}'
quelle: 04_Wissen/00_inhalt.md
normen:
  - norm: DIN 4109-1
    schluessel: DIN 4109-1
    thema: Schallschutz im Hochbau
    sachgebiet: 05 Schallschutz
    neueste: '2026-09'
    aeltere: ['2018-01']
    aenderungen: ['A1:2026-09']
    berichtigungen: []
    sprache: DE
    pruefen: false
  - norm: DIN 4109-2
    schluessel: DIN 4109-2
    thema: Schallschutz im Hochbau
    sachgebiet: 05 Schallschutz
    neueste: '2018-01'
    aeltere: []
    aenderungen: []
    berichtigungen: ['Berichtigung 1:2019-03']
    sprache: DE
    pruefen: true
"""


class Normenindex(unittest.TestCase):
    def setUp(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML fehlt")
        self.ordner = tempfile.TemporaryDirectory()
        self.bibliothek = Path(self.ordner.name)
        (self.bibliothek / "normen").mkdir()
        self.heute = dt.date(2026, 10, 23)
        self.index_schreiben("2026-10-16")

    def tearDown(self):
        self.ordner.cleanup()

    def index_schreiben(self, stand: str) -> None:
        (self.bibliothek / "normen" / "ausgaben.yml").write_text(INDEX.format(stand=stand), encoding="utf-8")

    def zeigen(self, norm: str) -> tuple[int, str]:
        ausgabe = io.StringIO()
        with redirect_stdout(ausgabe):
            rueckgabe = b.norm_zeigen(self.bibliothek, norm, heute=self.heute)
        return rueckgabe, ausgabe.getvalue()

    def test_schluessel_ohne_ausgabe_und_aenderung(self):
        self.assertEqual(b.norm_schluessel("din  4109-1:2018-01"), "DIN 4109-1")
        self.assertEqual(b.norm_schluessel("DIN 4109-1/A1:2026-09"), "DIN 4109-1")
        self.assertEqual(b.norm_schluessel("DIN 4109-2 Berichtigung 1:2019-03"), "DIN 4109-2")
        self.assertEqual(b.norm_schluessel("VDI4100"), "VDI 4100")
        self.assertEqual(b.norm_schluessel("DIN EN 1992-1-1/NA"), "DIN EN 1992-1-1/NA")

    def test_schluessel_ts_nationaler_anhang_und_aenderung_mit_bindestrich(self):
        # gleiche Regeln wie normstand_pruefen.schluessel und normen_index.py (FachwissenAgent)
        for schreibweise in ("DIN-TS 4108-8", "DIN/TS 4108-8", "DIN TS 4108-8:2022-09"):
            self.assertEqual(b.norm_schluessel(schreibweise), "DIN TS 4108-8")
        for schreibweise in ("DIN EN 1996-2-NA", "DIN EN 1996-2/NA:2012-01"):
            self.assertEqual(b.norm_schluessel(schreibweise), "DIN EN 1996-2/NA")
        self.assertEqual(b.norm_schluessel("DIN 18534-1-A1"), "DIN 18534-1")
        self.assertEqual(b.norm_schluessel("DIN EN 13791-A20:2021-07"), "DIN EN 13791")
        self.assertEqual(b.norm_schluessel("DIN SPEC 4102-23"), "DIN SPEC 4102-23")

    def test_ts_und_nationaler_anhang_in_jeder_schreibweise_gefunden(self):
        # Einträge mit neuem Schlüssel („DIN TS …“) und mit altem („…-NA“) – beide werden gefunden.
        zusatz = "".join(
            f"  - norm: {norm}\n    schluessel: {schluessel}\n    thema: Muster\n    sachgebiet: 04 Muster\n"
            f"    neueste: '2022-09'\n    aeltere: []\n    aenderungen: {aenderungen}\n    berichtigungen: []\n"
            "    sprache: DE\n    pruefen: false\n"
            for norm, schluessel, aenderungen in (("DIN-TS 4108-8", "DIN TS 4108-8", "[]"),
                                                  ("DIN EN 1996-2-NA", "DIN EN 1996-2-NA", "[]"),
                                                  ("DIN 18534-1", "DIN 18534-1", "['A1:2022-11']")))
        (self.bibliothek / "normen" / "ausgaben.yml").write_text(INDEX.format(stand="2026-10-16") + zusatz,
                                                                 encoding="utf-8")
        for anfrage in ("DIN-TS 4108-8", "DIN/TS 4108-8", "DIN TS 4108-8", "DIN EN 1996-2-NA", "DIN EN 1996-2/NA",
                        "DIN 18534-1-A1", "DIN 18534-1/A1"):
            with self.subTest(anfrage=anfrage):
                rueckgabe, text = self.zeigen(anfrage)
                self.assertEqual(rueckgabe, 0, text)

    def test_neueste_ausgabe_aenderungen_und_hinweis(self):
        rueckgabe, text = self.zeigen("DIN 4109-1:2018-01")
        self.assertEqual(rueckgabe, 0)
        self.assertIn("Neueste Ausgabe in der Fachbibliothek: 2026-09", text)
        self.assertIn("Änderungen: A1:2026-09", text)
        self.assertIn("Ältere Ausgaben: 2018-01", text)
        self.assertIn("Status bei DIN Media bestätigen", text)
        self.assertIn("kein amtlicher Titel", text)
        self.assertNotIn("Achtung", text)

    def test_auffaellige_norm_und_berichtigung(self):
        rueckgabe, text = self.zeigen("din 4109-2")
        self.assertEqual(rueckgabe, 0)
        self.assertIn("Berichtigungen: Berichtigung 1:2019-03", text)
        self.assertIn("pruefen: true", text)

    def test_reihe_nennt_ihre_teile(self):
        rueckgabe, text = self.zeigen("DIN 4109")
        self.assertEqual(rueckgabe, 1)
        self.assertIn("DIN 4109-1, DIN 4109-2", text)
        self.assertIn("Status bei DIN Media bestätigen", text)

    def test_unbekannte_norm(self):
        rueckgabe, text = self.zeigen("DIN 18533-1")
        self.assertEqual(rueckgabe, 1)
        self.assertIn("nicht im Normenindex", text)

    def test_veralteter_index(self):
        self.index_schreiben("2026-08-01")
        _, text = self.zeigen("DIN 4109-1")
        self.assertIn("83 Tage alt", text)

    def test_ohne_index_klare_meldung_und_rueckgabewert_2(self):
        (self.bibliothek / "normen" / "ausgaben.yml").unlink()
        rueckgabe, text = self.zeigen("DIN 4109-1")
        self.assertEqual(rueckgabe, 2)
        self.assertIn("Kein Normenindex", text)

    def test_aufruf_von_der_kommandozeile(self):
        r = subprocess.run([sys.executable, str(WURZEL / "tools" / "bibliothek_suchen.py"),
                            "--norm", "DIN 4109-1", "--bibliothek", str(self.bibliothek)],
                           capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2026-09", r.stdout)
        r = subprocess.run([sys.executable, str(WURZEL / "tools" / "bibliothek_suchen.py"),
                            "--norm", "DIN 4109-1", "--bibliothek", str(self.bibliothek / "fehlt")],
                           capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
