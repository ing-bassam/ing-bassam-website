"""Tests für tools/bibliothek_auszug.py: Sperre gegen den Ordner „DIN Normen“ und Hinweiszeile der Texte.

Die PDFs sind leere Dateien – die Sperre prüft nur Ordner und Pfade und öffnet keine PDF.

Aufruf: python -m unittest discover -s tests
"""
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


def auszug_laden():
    """bibliothek_auszug laden. Die Sperre braucht pypdf nicht; der Test-Workflow installiert es nicht."""
    try:
        import pypdf  # noqa: F401
    except ImportError:
        with mock.patch.dict(sys.modules, {"pypdf": types.ModuleType("pypdf")}):
            import bibliothek_auszug
            return bibliothek_auszug
    import bibliothek_auszug
    return bibliothek_auszug


try:
    a = auszug_laden()
except ImportError:          # PyYAML fehlt
    a = None


class Normordner(unittest.TestCase):
    def setUp(self):
        if a is None:
            self.skipTest("PyYAML fehlt")
        self.ordner = tempfile.TemporaryDirectory()
        self.wissen = Path(self.ordner.name) / "04_Wissen"
        for teil in ("DIN Normen/04 Wärmeschutz", "Literatur/08 Bauphysik"):
            (self.wissen / teil).mkdir(parents=True)
        (self.wissen / "00_inhalt.md").write_text("Stand: 16.10.2026\n", encoding="utf-8")
        (self.wissen / "DIN Normen" / "04 Wärmeschutz" / "DIN 9999-1_2025-11-00_DE.pdf").write_bytes(b"")
        (self.wissen / "Literatur" / "08 Bauphysik" / "musterbuch.pdf").write_bytes(b"")

    def tearDown(self):
        self.ordner.cleanup()

    def grund(self, ordner: Path) -> str:
        return a.normordner_grund(ordner, sorted(ordner.rglob("*.pdf")))

    def test_literatur_wird_eingelesen(self):
        self.assertEqual(self.grund(self.wissen / "Literatur"), "")

    def test_ordner_din_normen_gesperrt(self):
        self.assertIn("DIN Normen", self.grund(self.wissen / "DIN Normen"))
        self.assertIn("DIN Normen", self.grund(self.wissen / "DIN Normen" / "04 Wärmeschutz"))

    def test_wurzel_von_04_wissen_gesperrt(self):
        self.assertIn("Wurzel", self.grund(self.wissen))
        (self.wissen / "00_inhalt.md").unlink()                  # auch ohne Inhaltsverzeichnis
        self.assertIn("Wurzel", self.grund(self.wissen))

    def test_pdf_in_einem_ordner_din_normen_gesperrt(self):
        versteckt = self.wissen / "Literatur" / "08 Bauphysik" / "DIN Normen"
        versteckt.mkdir()
        (versteckt / "DIN 9999-2_2025-11-00_DE.pdf").write_bytes(b"")
        self.assertIn("DIN 9999-2", self.grund(self.wissen / "Literatur"))

    def test_aufruf_bricht_ab_und_schreibt_nichts(self):
        bibliothek = Path(self.ordner.name) / "FachwissenAgent"
        fehler = io.StringIO()
        with mock.patch.object(sys, "argv", ["bibliothek_auszug.py", str(self.wissen), str(bibliothek)]), \
                redirect_stderr(fehler):
            self.assertEqual(a.main(), 2)
        self.assertIn("Abbruch", fehler.getvalue())
        self.assertIn("Normenindex", fehler.getvalue())
        self.assertFalse(bibliothek.exists())


class Hinweiszeile(unittest.TestCase):
    # Wortlaut vom Inhaber vorgegeben; steht so auch in Zeile 3 der Texte in FachwissenAgent.
    VORGABE = ("Hinweis: Nur für die interne Prüfung von Fakten. Nichts wörtlich übernehmen – kein Satz, keine "
               "Tabelle, keine Abbildung; Aussagen nur in eigenen Worten mit Fundstelle.")

    def test_hinweis_wortgleich_mit_der_vorgabe(self):
        if a is None:
            self.skipTest("PyYAML fehlt")
        self.assertEqual(a.HINWEIS, self.VORGABE)

    def test_hinweis_steht_in_zeile_3(self):
        if a is None:
            self.skipTest("PyYAML fehlt")
        quelltext = (Path(__file__).resolve().parent.parent / "tools" / "bibliothek_auszug.py").read_text(
            encoding="utf-8")
        self.assertIn('kopf = (f"Werk: {kennung}\\nZitat: {eintrag[\'zitat\']}, S. <Seite>.{isbn_teil}\\n"\n'
                      '                    f"{HINWEIS}\\n" + "=" * 70 + "\\n")', quelltext)


if __name__ == "__main__":
    unittest.main()
