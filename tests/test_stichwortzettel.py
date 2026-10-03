"""Tests für die Stichwortzettel: Auftrag, Ablage in Notion (ohne Netz) und Wochenbericht-Abschnitt.

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

import stichwortzettel as sz  # noqa: E402
import trend_notion  # noqa: E402

ZETTEL = """# Stichwortzettel: Radon im Keller messen

Kernfrage: Muss ich mein Haus auf Radon messen lassen?
Zielgruppe: Privat

## Kernaussage 1
- Aussage: Eine Messung dauert mindestens drei Monate in der Heizperiode.
- Beleg: Fußnote [2] – BfS, Radon-Messung
- Nutzen: Sie vermeiden eine Messung, die nichts aussagt.

## Einstieg
Ihr Keller ist dicht – aber ist er radonfrei?

## Schluss
Lassen Sie im Winter messen, bevor Sie sanieren.
"""


class Auftrag(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.ordner.name)
        (self.wurzel / "entwuerfe" / "veroeffentlicht").mkdir(parents=True)
        (self.wurzel / "entwuerfe" / "veroeffentlicht" / "2026-10-01-radon-messen.md").write_text("# Radon", encoding="utf-8")
        self.bericht = self.wurzel / "bericht.json"
        self.bericht.write_text(json.dumps({"eintraege": [
            {"kurzform": "radon-messen", "datei": "2026-10-01-radon-messen.md", "titel": "Radon im Keller messen",
             "format": "Ratgeber", "ergebnis": "veröffentlicht"},
            {"kurzform": "fehlt", "datei": "2026-10-01-fehlt.md", "titel": "Fehlt", "format": "Ratgeber",
             "ergebnis": "veröffentlicht"},
            {"kurzform": "wartet", "datei": "x.md", "titel": "Wartet", "format": "Ratgeber", "ergebnis": "wartet"},
        ]}), encoding="utf-8")
        self.ausgabe = self.wurzel / "output.txt"
        self.patches = [mock.patch.object(sz, "WURZEL", self.wurzel),
                        mock.patch.object(sz, "VEROEFFENTLICHT", self.wurzel / "entwuerfe" / "veroeffentlicht"),
                        mock.patch.dict(sz.os.environ, {"GITHUB_OUTPUT": str(self.ausgabe)})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.ordner.cleanup()

    def test_auftrag_nur_fuer_vorhandene_beitraege(self):
        with redirect_stdout(io.StringIO()):
            sz.auftrag(self.bericht, self.wurzel / "zettel")
        text = self.ausgabe.read_text(encoding="utf-8")
        self.assertIn("anzahl=1\n", text)
        self.assertIn("Beitrag: entwuerfe/veroeffentlicht/2026-10-01-radon-messen.md", text)
        self.assertIn("Ausgabe: ", text)
        self.assertIn("radon-messen.md", text)
        self.assertNotIn("fehlt.md", text.split("auftrag<<")[1])
        self.assertTrue((self.wurzel / "zettel").is_dir())

    def test_format_fuer_notion(self):
        self.assertEqual(sz.format_fuer_notion("Rechtsprechung"), "Rechtsprechung")
        self.assertEqual(sz.format_fuer_notion("Vorlage"), "Vorlage")
        self.assertEqual(sz.format_fuer_notion("Ratgeber"), "Fachbeitrag")

    def test_ablegen_meldet_fehlende_zettel_und_legt_vorhandene_ab(self):
        (self.wurzel / "zettel").mkdir()
        (self.wurzel / "zettel" / "radon-messen.md").write_text(ZETTEL, encoding="utf-8")
        with mock.patch.object(trend_notion, "stichwortzettel_anlegen", return_value="https://www.notion.so/abc") as anlegen, \
                redirect_stdout(io.StringIO()) as ausgabe:
            sz.ablegen(self.bericht, self.wurzel / "zettel")
        self.assertEqual(anlegen.call_count, 1)
        self.assertEqual(anlegen.call_args[0][3], "radon-messen")
        self.assertEqual(anlegen.call_args[0][2], "https://ing-bassam.de/fachwissen/radon-messen/")
        self.assertIn("[Zettel in Notion](https://www.notion.so/abc)", ausgabe.getvalue())
        self.assertIn("Fehlt: kein Zettel entstanden", ausgabe.getvalue())


class Notion(unittest.TestCase):
    def test_anlegen_mit_bloecken(self):
        aufrufe = []

        def senden(methode, pfad, daten=None):
            aufrufe.append((methode, pfad, daten))
            if pfad.endswith("/query"):
                return {"results": []}
            return {"id": "neu", "url": "https://www.notion.so/neu"}

        adresse = trend_notion.stichwortzettel_anlegen(ZETTEL, "Radon im Keller messen", "https://ing-bassam.de/x/",
                                                       "radon-messen", "Fachbeitrag", "2026-10-05", senden=senden)
        self.assertEqual(adresse, "https://www.notion.so/neu")
        seite = [a for a in aufrufe if a[1] == "/pages"][0][2]
        self.assertEqual(seite["parent"]["data_source_id"], trend_notion.STICHWORTZETTEL)
        self.assertEqual(seite["properties"]["Kurzform"]["rich_text"][0]["text"]["content"], "radon-messen")
        self.assertEqual(seite["properties"]["Format"]["select"]["name"], "Fachbeitrag")
        typen = [b["type"] for b in seite["children"]]
        self.assertIn("heading_2", typen)
        self.assertIn("bulleted_list_item", typen)

    def test_anlegen_ueberspringt_vorhandene(self):
        senden = lambda methode, pfad, daten=None: {"results": [{"id": "alt"}]}  # noqa: E731
        self.assertEqual(trend_notion.stichwortzettel_anlegen(ZETTEL, "X", "https://x/", "x", senden=senden), "")


if __name__ == "__main__":
    unittest.main()
