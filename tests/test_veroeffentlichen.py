"""Tests für tools/veroeffentlichen.py auf einer Kopie (ohne GitHub).

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

import veroeffentlichen as v  # noqa: E402


def kopf(kurzform: str, titel: str, *, erstellt: str, status: str = "Entwurf", weitere: str = "") -> str:
    return (f"---\ntitel: \"{titel}\"\nformat: Ratgeber\nkernfrage: Frage zu {titel}?\nkurzform: {kurzform}\n"
            f"erstellt: {erstellt}\nstatus: {status}\n{weitere}---\n\n# {titel}\n\nText.\n")


class Automatik(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        wurzel = Path(self.ordner.name)
        self.entwurf = wurzel / "entwuerfe" / "entwurf"
        self.entwurf.mkdir(parents=True)
        (wurzel / "entwuerfe" / "veroeffentlicht").mkdir()
        dateien = {
            "2026-09-01-radon-messen.md": kopf("radon-messen", "Radon im Keller messen", erstellt="2026-09-01"),
            "2026-09-02-estrich-belegreife.md": kopf("estrich-belegreife", "Estrich und Belegreife", erstellt="2026-09-02"),
            "2026-09-03-fenster-lueften.md": kopf("fenster-lueften", "Lüften nach dem Fenstertausch", erstellt="2026-09-03"),
            "2026-09-04-mit-todo.md": kopf("mit-todo", "Mit offenem Punkt", erstellt="2026-09-04") + "> TODO: prüfen\n",
            "2026-09-05-angehalten.md": kopf("angehalten", "Angehalten", erstellt="2026-09-05",
                                             weitere="zurueckhalten: ja\n"),
            "2026-09-06-urteil-zweitfassung.md": kopf("urteil-zweitfassung", "Zweite Besprechung", erstellt="2026-09-06",
                                                       weitere="aktenzeichen: 10 U 308/20\n").replace(
                "format: Ratgeber", "format: Rechtsprechung"),
        }
        for name, text in dateien.items():
            (self.entwurf / name).write_text(text, encoding="utf-8")
        (wurzel / "entwuerfe" / "veroeffentlicht" / "2026-08-01-urteil-erstfassung.md").write_text(
            kopf("urteil-erstfassung", "Erste Besprechung", erstellt="2026-08-01", status="Veröffentlicht",
                 weitere="aktenzeichen: 10 U 308/20\n").replace("format: Ratgeber", "format: Rechtsprechung"),
            encoding="utf-8")
        self.patches = [mock.patch.object(v, "WURZEL", wurzel), mock.patch.object(v, "ORDNER", self.entwurf)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.ordner.cleanup()

    def starten(self, *argumente: str) -> tuple[str, dict]:
        bericht = Path(self.ordner.name) / "bericht.json"
        ausgabe = io.StringIO()
        with mock.patch.object(sys, "argv", ["veroeffentlichen.py", "--ohne-github", "--bericht", str(bericht),
                                             *argumente]), redirect_stdout(ausgabe):
            v.main()
        return ausgabe.getvalue(), json.loads(bericht.read_text(encoding="utf-8"))

    def status(self, name: str) -> str:
        return v.feld(v.KOPF.match((self.entwurf / name).read_text(encoding="utf-8")).group(1), "status")

    def test_automatisch_hoechstens_zwei_die_aeltesten_zuerst(self):
        ausgabe, bericht = self.starten("--automatisch", "--max", "2")
        self.assertEqual(ausgabe.strip().splitlines()[-1], "2")
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Veröffentlicht")
        self.assertEqual(self.status("2026-09-02-estrich-belegreife.md"), "Veröffentlicht")
        self.assertEqual(self.status("2026-09-03-fenster-lueften.md"), "Entwurf")
        ergebnisse = {e["kurzform"]: e["ergebnis"] for e in bericht["eintraege"]}
        self.assertEqual(ergebnisse["fenster-lueften"], "wartet")

    def test_zurueckgehalten_mit_grund(self):
        _, bericht = self.starten("--automatisch", "--max", "5")
        zurueck = {e["kurzform"]: " ".join(e["gruende"]) for e in bericht["eintraege"]
                   if e["ergebnis"] == "zurückgehalten"}
        self.assertIn("Prüfpunkt", zurueck["mit-todo"])
        self.assertIn("zurueckhalten", zurueck["angehalten"])
        self.assertIn("dasselbe Urteil", zurueck["urteil-zweitfassung"])
        self.assertEqual(self.status("2026-09-06-urteil-zweitfassung.md"), "Entwurf")

    def test_probelauf_aendert_nichts(self):
        ausgabe, _ = self.starten("--automatisch", "--probelauf")
        self.assertIn("Würde veröffentlichen", ausgabe)
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Entwurf")

    def test_auswahl_von_hand(self):
        ausgabe, _ = self.starten("--auswahl", "fenster-lueften")
        self.assertEqual(ausgabe.strip().splitlines()[-1], "1")
        self.assertEqual(self.status("2026-09-03-fenster-lueften.md"), "Veröffentlicht")
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Entwurf")


if __name__ == "__main__":
    unittest.main()
