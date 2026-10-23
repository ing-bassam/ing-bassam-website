"""Tests für tools/bestandspruefung.py (lokaler Bericht des Inhabers zum veröffentlichten Bestand).

Der Bericht nennt Werk und Seite und wird nie veröffentlicht; in GitHub Actions bricht das
Werkzeug ab, ohne etwas zu schreiben.

Aufruf: python -m unittest discover -s tests
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import bestandspruefung as b  # noqa: E402

WORTGLEICH = {"geprueft": True, "grenze": 8, "werke": 5, "treffer": [
    {"datei": "entwuerfe/veroeffentlicht/2026-09-01-a.md", "zeile": 12, "werk": "muster-2020", "seite": "14",
     "art": "Wortfolge"},
    {"datei": "entwuerfe/veroeffentlicht/2026-09-01-a.md", "zeile": 30, "werk": None, "seite": None,
     "art": "Abbildung"}]}
NORMSTAND = {"geprueft": True, "stand_index": "2026-10-16", "zeilen": [
    {"datei": "entwuerfe/veroeffentlicht/2026-09-02-b.md", "zeile": 7, "regelwerk": "DIN 4711-1",
     "genannt": "2018-01", "neueste": "2024-05", "stufe": "FEHLER", "ergebnis": "ältere Ausgabe"},
    {"datei": "entwuerfe/veroeffentlicht/2026-09-02-b.md", "zeile": 9, "regelwerk": "DIN 4712",
     "genannt": "", "neueste": "2025-10", "stufe": "HINWEIS", "ergebnis": "ohne Ausgabe"}]}


class Bericht(unittest.TestCase):
    def test_nur_fundstellen(self):
        text, befund = b.bericht(WORTGLEICH, NORMSTAND)
        self.assertEqual(befund, "befund=3")
        self.assertIn("| 2026-09-01-a.md | 2 | 12 (muster-2020 S. 14), 30 (Abbildung) |", text)
        self.assertIn("| 2026-09-02-b.md | 7 | DIN 4711-1 | 2018-01 | 2024-05 |", text)
        self.assertNotIn("DIN 4712", text)          # Hinweise sperren nicht und stehen nicht im Issue

    def test_ohne_befund(self):
        _, befund = b.bericht({"geprueft": True, "treffer": []}, {"geprueft": True, "zeilen": []})
        self.assertEqual(befund, "befund=0")

    def test_nicht_geprueft(self):
        for wortgleich, normstand in ((None, NORMSTAND), (WORTGLEICH, None)):
            with self.subTest(wortgleich=bool(wortgleich), normstand=bool(normstand)):
                text, befund = b.bericht(wortgleich, normstand)
                self.assertEqual(befund, "befund=nicht-geprueft")
                self.assertIn("Nicht geprüft", text)
        # „geprueft: false“ (Bibliothek fehlt), fehlende oder unlesbare Datei gelten als nicht geprüft
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "x.json"
            self.assertIsNone(b.lesen(pfad))
            pfad.write_text('{"geprueft": false, "treffer": "nicht-geprueft"}', encoding="utf-8")
            self.assertIsNone(b.lesen(pfad))
            pfad.write_text("kein JSON", encoding="utf-8")
            self.assertIsNone(b.lesen(pfad))

    def test_laenge_begrenzt(self):
        viele = {"geprueft": True, "treffer": [{"datei": f"entwuerfe/veroeffentlicht/{i:04d}-x.md", "zeile": 1,
                                                 "werk": "w" * 40, "seite": "1"} for i in range(3000)]}
        text, _ = b.bericht(viele, {"geprueft": True, "zeilen": []})
        self.assertLessEqual(len(text), b.HOECHSTLAENGE + 100)
        self.assertIn("gekürzt", text)

    def test_bericht_ist_nur_fuer_den_inhaber(self):
        text, _ = b.bericht(WORTGLEICH, NORMSTAND)
        self.assertIn("nie veröffentlicht", text)
        self.assertNotIn("Issue wird", text)


class Aufruf(unittest.TestCase):
    """Nur lokal: In GitHub Actions entsteht kein Bericht."""

    def starten(self, ordner: Path, umgebung: dict) -> tuple[int, str, Path]:
        wortgleich, normstand = ordner / "wortgleich.json", ordner / "normstand.json"
        wortgleich.write_text(json.dumps(WORTGLEICH), encoding="utf-8")
        normstand.write_text(json.dumps(NORMSTAND), encoding="utf-8")
        ziel = ordner / "bestand.md"
        ausgabe = io.StringIO()
        with mock.patch.object(sys, "argv", ["bestandspruefung.py", "--wortgleich", str(wortgleich),
                                             "--normstand", str(normstand), "--bericht", str(ziel)]), \
                mock.patch.dict(os.environ, umgebung), redirect_stdout(ausgabe):
            code = b.main()
        return code, ausgabe.getvalue(), ziel

    def test_lokal_mit_werk_und_seite(self):
        with tempfile.TemporaryDirectory() as ordner, mock.patch.dict(os.environ):
            os.environ.pop("GITHUB_ACTIONS", None)
            code, ausgabe, ziel = self.starten(Path(ordner), {})
            self.assertEqual(code, 0)
            self.assertEqual(ausgabe.strip().splitlines()[-1], "befund=3")
            self.assertIn("muster-2020 S. 14", ziel.read_text(encoding="utf-8"))
            self.assertNotIn("muster-2020", ausgabe)

    def test_in_github_actions_kein_bericht(self):
        with tempfile.TemporaryDirectory() as ordner:
            code, ausgabe, ziel = self.starten(Path(ordner), {"GITHUB_ACTIONS": "true"})
            self.assertEqual(code, 2)
            self.assertFalse(ziel.exists())
            self.assertEqual(ausgabe.strip().splitlines()[-1], "befund=nicht-geprueft")
            self.assertNotIn("muster-2020", ausgabe)


if __name__ == "__main__":
    unittest.main()
