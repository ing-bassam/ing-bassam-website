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


class Kopie(unittest.TestCase):
    """Entwürfe in einem Ordner auf Zeit; die Tests stehen in den Unterklassen."""

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


class Automatik(Kopie):
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
        ausgabe, bericht = self.starten("--automatisch", "--probelauf")
        self.assertIn("Würde veröffentlichen", ausgabe)
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Entwurf")
        # Wochenbericht: Die Prüfung auf wörtliche Übernahmen kommt erst am Veröffentlichungstag.
        self.assertIn("erst am Veröffentlichungstag", bericht["hinweis"])
        self.assertIn("erst am Veröffentlichungstag", ausgabe)

    def test_auswahl_von_hand(self):
        ausgabe, _ = self.starten("--auswahl", "fenster-lueften")
        self.assertEqual(ausgabe.strip().splitlines()[-1], "1")
        self.assertEqual(self.status("2026-09-03-fenster-lueften.md"), "Veröffentlicht")
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Entwurf")


class Wortgleich(Kopie):
    """Zurückhalten nach der Prüfung auf wörtliche Übernahmen (tools/wortgleich_pruefen.py --json)."""

    def ergebnis(self, inhalt) -> str:
        pfad = Path(self.ordner.name) / "wortgleich.json"
        pfad.write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")
        return str(pfad)

    def zurueck(self, bericht: dict) -> dict[str, str]:
        return {e["kurzform"]: " ".join(e["gruende"]) for e in bericht["eintraege"]
                if e["ergebnis"] == "zurückgehalten"}

    def test_treffer_halten_den_entwurf_zurueck(self):
        json_pfad = self.ergebnis({"treffer": [
            {"entwurf": "entwuerfe/entwurf/2026-09-01-radon-messen.md", "abschnitt": "Messen", "zeile": 14,
             "woerter": 11, "werk": "beispielwerk-2020", "seite": "214", "werke": 1}]})
        ausgabe, bericht = self.starten("--automatisch", "--max", "2", "--wortgleich", json_pfad)
        self.assertIn("wörtliche Übereinstimmung mit der Fachbibliothek", self.zurueck(bericht)["radon-messen"])
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Entwurf")
        # Die übrigen rücken nach.
        self.assertEqual(self.status("2026-09-02-estrich-belegreife.md"), "Veröffentlicht")
        self.assertEqual(self.status("2026-09-03-fenster-lueften.md"), "Veröffentlicht")
        self.assertEqual(ausgabe.strip().splitlines()[-1], "2")

    def test_ergebnis_im_format_des_werkzeugs(self):
        """Aufbau wie tools/wortgleich_pruefen.py --json: Hinweise (eigene Tabellen) sperren nicht."""
        pfad = "entwuerfe/entwurf/"
        json_pfad = self.ergebnis({
            "geprueft": True, "grenze": 8, "werke": 92, "amtliche_texte": 3, "freigegeben": 0,
            "entwuerfe": [pfad + d.name for d in sorted(self.entwurf.glob("*.md"))],
            "anzahl_treffer": 1, "anzahl_hinweise": 1,
            "treffer": [{"datei": pfad + "2026-09-02-estrich-belegreife.md", "abschnitt": "Belegreife", "zeile": 9,
                         "laenge": 15, "werk": "beispielwerk-2019", "seite": "12", "werke": 1, "art": "Wortfolge",
                         "vermerk": "in eigenen Worten fassen, Fundstelle angeben"}],
            "hinweise": [{"datei": pfad + "2026-09-01-radon-messen.md", "abschnitt": "Messen", "zeile": 20,
                          "art": "Tabelle", "zeilen": 4, "vermerk": "Hinweis: Tabelle"}]})
        ausgabe, bericht = self.starten("--automatisch", "--max", "5", "--wortgleich", json_pfad)
        zurueck = self.zurueck(bericht)
        self.assertIn("wörtliche Übereinstimmung", zurueck["estrich-belegreife"])
        self.assertIn("(1 Stelle(n))", zurueck["estrich-belegreife"])
        self.assertNotIn("radon-messen", zurueck)
        self.assertNotIn("Wortgleich", zurueck.get("fenster-lueften", ""))
        self.assertEqual(self.status("2026-09-03-fenster-lueften.md"), "Veröffentlicht")
        # Protokoll, Zusammenfassung und Wochenbericht: nur Zahl der Stellen, nie Werk oder Seite
        oeffentlich = ausgabe + json.dumps(bericht, ensure_ascii=False)
        for teil in ("beispielwerk", "S. 12", "Fundstelle angeben"):
            self.assertNotIn(teil, oeffentlich)

    def test_treffer_je_datei(self):
        json_pfad = self.ergebnis({"dateien": [
            {"datei": "entwuerfe/entwurf/2026-09-02-estrich-belegreife.md", "treffer": [{"werk": "x", "seite": "3"}]},
            {"datei": "entwuerfe/entwurf/2026-09-01-radon-messen.md", "treffer": []},
            {"datei": "entwuerfe/entwurf/2026-09-03-fenster-lueften.md", "treffer": 0}]})
        _, bericht = self.starten("--automatisch", "--max", "5", "--wortgleich", json_pfad)
        zurueck = self.zurueck(bericht)
        self.assertIn("wörtliche Übereinstimmung", zurueck["estrich-belegreife"])
        self.assertNotIn("radon-messen", zurueck)
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Veröffentlicht")
        # Nicht in der Liste der geprüften Dateien: nicht geprüft, also zurück.
        self.assertIn("Wortgleich-Prüfung nicht möglich", zurueck["urteil-zweitfassung"])

    def test_nicht_geprueft_haelt_alle_zurueck(self):
        json_pfad = self.ergebnis({"treffer": "nicht-geprueft"})
        ausgabe, bericht = self.starten("--automatisch", "--max", "5", "--wortgleich", json_pfad)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "0")
        zurueck = self.zurueck(bericht)
        self.assertIn("Wortgleich-Prüfung nicht möglich", zurueck["radon-messen"])
        self.assertIn("Wortgleich-Prüfung nicht möglich", zurueck["fenster-lueften"])

    def test_ergebnis_fehlt_oder_unlesbar(self):
        for inhalt in (None, "kein JSON"):
            with self.subTest(inhalt=inhalt):
                pfad = Path(self.ordner.name) / "wortgleich-kaputt.json"
                if inhalt is None:
                    pfad.unlink(missing_ok=True)
                else:
                    pfad.write_text(inhalt, encoding="utf-8")
                ausgabe, bericht = self.starten("--automatisch", "--probelauf", "--wortgleich", str(pfad))
                self.assertEqual(ausgabe.strip().splitlines()[-1], "0")
                self.assertIn("Wortgleich-Prüfung nicht möglich", self.zurueck(bericht)["estrich-belegreife"])

    def test_treffer_ohne_zuordnung_halten_alle_zurueck(self):
        json_pfad = self.ergebnis({"anzahl_treffer": 2, "treffer": []})
        ausgabe, bericht = self.starten("--automatisch", "--probelauf", "--wortgleich", json_pfad)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "0")
        self.assertIn("keinem Entwurf", self.zurueck(bericht)["radon-messen"])

    def test_auswahl_trotz_treffer_in_anderem_entwurf(self):
        """Handauswahl: Ein Treffer in einem nicht gewählten Entwurf hält die Auswahl nicht auf."""
        json_pfad = self.ergebnis({"geprueft": True, "anzahl_treffer": 1, "treffer": [
            {"datei": "entwuerfe/entwurf/2026-09-02-estrich-belegreife.md", "zeile": 9, "laenge": 15,
             "werk": "beispielwerk-2019", "seite": "12", "art": "Wortfolge"}]})
        ausgabe, bericht = self.starten("--auswahl", "fenster-lueften", "--wortgleich", json_pfad)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "1")
        self.assertEqual(self.status("2026-09-03-fenster-lueften.md"), "Veröffentlicht")
        self.assertNotIn("Wortgleich", json.dumps(bericht, ensure_ascii=False))

    def test_treffer_in_unbekannter_datei_halten_alle_zurueck(self):
        json_pfad = self.ergebnis({"geprueft": True, "anzahl_treffer": 1, "treffer": [
            {"datei": "anderswo/2026-09-09-gibt-es-nicht.md", "zeile": 3, "werk": "beispielwerk-2019", "seite": "1"}]})
        ausgabe, bericht = self.starten("--auswahl", "fenster-lueften", "--wortgleich", json_pfad)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "0")
        self.assertIn("keinem Entwurf", self.zurueck(bericht)["fenster-lueften"])

    def test_mit_wortgleich_kein_hinweis_auf_spaetere_pruefung(self):
        json_pfad = self.ergebnis({"treffer": [], "anzahl_treffer": 0})
        _, bericht = self.starten("--automatisch", "--probelauf", "--wortgleich", json_pfad)
        self.assertNotIn("Veröffentlichungstag", bericht["hinweis"])

    def test_ohne_treffer_wie_bisher(self):
        json_pfad = self.ergebnis({"treffer": [], "anzahl_treffer": 0, "werke": 92})
        ausgabe, bericht = self.starten("--automatisch", "--max", "2", "--wortgleich", json_pfad)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "2")
        self.assertEqual(self.status("2026-09-01-radon-messen.md"), "Veröffentlicht")
        self.assertNotIn("Wortgleich", json.dumps(bericht, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
