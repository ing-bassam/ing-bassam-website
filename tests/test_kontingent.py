"""Tests für tools/kontingent.py: Limit-Meldung lesen, Kontingentwoche, deutsche Zeit.

Aufruf: python -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import kontingent as k  # noqa: E402

UTC = timezone.utc


def zeit(*teile) -> datetime:
    return datetime(*teile, tzinfo=UTC)


class Meldung(unittest.TestCase):
    JETZT = zeit(2026, 9, 27, 14, 0)          # Sonntag, als das Limit am 27.09.2026 griff

    def test_wochenlimit_wie_am_27_09_2026(self):
        self.assertEqual(k.reset_lesen("You've hit your weekly limit · resets Sep 30, 2am (UTC)", self.JETZT),
                         ("woche", zeit(2026, 9, 30, 2, 0)))

    def test_sitzungslimit_deutsche_zeit(self):
        art, bis = k.reset_lesen("You've hit your session limit · resets 12:20pm (Europe/Berlin)", self.JETZT)
        self.assertEqual(art, "sitzung")
        self.assertEqual(bis, zeit(2026, 9, 28, 10, 20))   # heute schon vorbei → morgen, Sommerzeit

    def test_aeltere_form_mit_zeitstempel(self):
        art, bis = k.reset_lesen("Claude AI usage limit reached|1791338400", self.JETZT)
        self.assertEqual(bis, datetime.fromtimestamp(1791338400, tz=UTC))
        self.assertEqual(art, "woche")

    def test_keine_meldung(self):
        self.assertIsNone(k.reset_lesen("ERGEBNIS: OK", self.JETZT))

    def test_jahreswechsel(self):
        art, bis = k.reset_lesen("You've hit your weekly limit · resets Jan 6, 2am (UTC)", zeit(2026, 12, 31, 12))
        self.assertEqual(bis, zeit(2027, 1, 6, 2))

    def test_unlesbare_zeit_ergibt_naechsten_mittwoch(self):
        art, bis = k.reset_lesen("You've hit your weekly limit · resets soon (Mars/Olympus)", self.JETZT)
        self.assertEqual((art, bis), ("woche", zeit(2026, 9, 30, 2)))

    def test_erkennen_liest_json_mit_escapes(self):
        verlauf = [{"type": "result", "is_error": True,
                    "result": "You’ve hit your weekly limit · resets Oct 7, 4am (Europe/Berlin)"}]
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "verlauf.json"
            datei.write_text(json.dumps(verlauf), encoding="utf-8")          # ensure_ascii: · im Text
            with mock.patch.object(k, "pause_setzen", return_value="7") as pause, \
                    mock.patch("builtins.print") as ausgabe:
                k.erkennen(datei, zeit(2026, 10, 3, 12), "")
        pause.assert_called_once()
        self.assertEqual(pause.call_args[0][0], zeit(2026, 10, 7, 2, 15))   # 04:00 Sommerzeit + 15 Minuten
        zeilen = [c.args[0] for c in ausgabe.call_args_list if not c.kwargs.get("file")]
        self.assertIn("limit=woche", zeilen)


class DeutscheZeit(unittest.TestCase):
    def test_umstellung_herbst_2026(self):
        self.assertEqual(k.berlin(zeit(2026, 10, 25, 0, 59)), datetime(2026, 10, 25, 2, 59))
        self.assertEqual(k.berlin(zeit(2026, 10, 25, 1, 0)), datetime(2026, 10, 25, 2, 0))

    def test_umstellung_fruehjahr_2027(self):
        self.assertEqual(k.berlin(zeit(2027, 3, 28, 0, 59)), datetime(2027, 3, 28, 1, 59))
        self.assertEqual(k.berlin(zeit(2027, 3, 28, 1, 0)), datetime(2027, 3, 28, 3, 0))

    def test_rueckweg(self):
        self.assertEqual(k.berlin_nach_utc(datetime(2026, 10, 7, 4, 0)), zeit(2026, 10, 7, 2, 0))
        self.assertEqual(k.berlin_nach_utc(datetime(2026, 12, 2, 3, 0)), zeit(2026, 12, 2, 2, 0))

    def test_neustart_im_sommer_und_im_winter(self):
        self.assertEqual(k.berlin_text(zeit(2026, 9, 30, 2)), "Mittwoch, 30.09.2026, 04:00 Uhr")
        self.assertEqual(k.berlin_text(zeit(2026, 10, 28, 2)), "Mittwoch, 28.10.2026, 03:00 Uhr")


class Woche(unittest.TestCase):
    def test_wochenbeginn(self):
        self.assertEqual(k.wochenbeginn(zeit(2026, 9, 30, 1, 59)), zeit(2026, 9, 23, 2))
        self.assertEqual(k.wochenbeginn(zeit(2026, 9, 30, 2, 0)), zeit(2026, 9, 30, 2))
        self.assertEqual(k.wochenbeginn(zeit(2026, 10, 6, 23, 0)), zeit(2026, 9, 30, 2))

    def test_pruefen_mit_offener_pause(self):
        pause = [{"number": 9, "bis": zeit(2026, 10, 7, 2, 15)}]
        with mock.patch.object(k, "pausen", return_value=pause), mock.patch("builtins.print") as ausgabe:
            k.pruefen(zeit(2026, 10, 3, 22))
        zeilen = [c.args[0] for c in ausgabe.call_args_list]
        self.assertIn("laufen=nein", zeilen)

    def test_pruefen_wochengrenze(self):
        with mock.patch.object(k, "pausen", return_value=[]), \
                mock.patch.object(k, "entwuerfe_seit", return_value=k.WOCHENGRENZE), \
                mock.patch("builtins.print") as ausgabe:
            k.pruefen(zeit(2026, 10, 3, 22))
        zeilen = [c.args[0] for c in ausgabe.call_args_list]
        self.assertIn("laufen=nein", zeilen)
        self.assertIn("frei=0", zeilen)

    def test_pruefen_frei(self):
        with mock.patch.object(k, "pausen", return_value=[]), \
                mock.patch.object(k, "entwuerfe_seit", return_value=3), mock.patch("builtins.print") as ausgabe:
            k.pruefen(zeit(2026, 10, 3, 22))
        zeilen = [c.args[0] for c in ausgabe.call_args_list]
        self.assertIn("laufen=ja", zeilen)
        self.assertIn(f"frei={k.WOCHENGRENZE - 3}", zeilen)

    def test_abgelaufene_pause_wird_geschlossen(self):
        pause = [{"number": 9, "bis": zeit(2026, 9, 30, 2, 15)}]
        with mock.patch.object(k, "pausen", return_value=pause), \
                mock.patch.object(k, "entwuerfe_seit", return_value=0), \
                mock.patch.object(k, "gh") as gh, mock.patch.object(k, "repo", return_value="a/b"), \
                mock.patch("builtins.print"):
            k.pruefen(zeit(2026, 10, 3, 22))
        self.assertEqual(gh.call_args[0][:3], ("issue", "close", "9"))


class PauseText(unittest.TestCase):
    def test_issue_text(self):
        titel, koerper = k.pause_text(zeit(2026, 10, 7, 2, 15), "https://github.com/x/y/actions/runs/1")
        self.assertEqual(titel, "Agenten pausieren bis Mittwoch, 07.10.2026, 04:15 Uhr")
        self.assertIn("pause_bis: 2026-10-07T02:15:00Z", koerper)
        self.assertNotIn("@claude", koerper.lower())      # würde den Workflow „Claude Code“ auslösen


if __name__ == "__main__":
    unittest.main()
