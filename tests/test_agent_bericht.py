"""Tests für tools/agent_bericht.py: kein Text aus Edit-Fehlern, Befehlsargumenten oder Suchen im Protokoll.

Protokoll und Job-Zusammenfassung sind öffentlich. Scheitert ein Edit, meldet das Werkzeug den
gesuchten Text mit – das kann eine Buchpassage sein, die der Agent umformulieren wollte.
Das Kunstwort „Quarzbläulingsfuge“ steht hier für solchen Text und darf nie ausgegeben werden.

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

import agent_bericht  # noqa: E402

KUNSTWORT = "Quarzbläulingsfuge"
SATZ = f"Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen"


def verlauf() -> list[dict]:
    werkzeug = lambda kennung, name, eingabe: {"type": "tool_use", "id": kennung, "name": name, "input": eingabe}  # noqa: E731
    fehler = lambda kennung, text: {"type": "tool_result", "tool_use_id": kennung, "is_error": True,  # noqa: E731
                                    "content": [{"type": "text", "text": text}]}
    return [
        {"type": "system", "message": "Claude Code initialized"},
        {"type": "assistant", "message": {"content": [
            werkzeug("e1", "Edit", {"file_path": "entwuerfe/entwurf/x.md", "old_string": SATZ, "new_string": "neu"}),
            werkzeug("e2", "Edit", {"file_path": "entwuerfe/entwurf/x.md", "old_string": SATZ, "new_string": "neu"}),
            werkzeug("b1", "Bash", {"command": f'python tools/bibliothek_suchen.py "{SATZ}"'}),
            werkzeug("g1", "Grep", {"pattern": SATZ, "path": "entwuerfe"}),
            werkzeug("w1", "WebSearch", {"query": SATZ})]}},
        {"type": "user", "message": {"content": [
            fehler("e1", f"String to replace not found in file.\nString: {SATZ}"),
            fehler("e2", f"Found 2 matches of the string to replace, but replace_all is false.\nString: {SATZ}"),
            fehler("b1", "Exit code 1"),
            fehler("g1", "Grep fehlgeschlagen"),
            fehler("w1", "Suche fehlgeschlagen")]}},
        {"type": "result", "num_turns": 7, "subtype": "success", "result": "ERGEBNIS: OK",
         "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": f'grep -rn "{SATZ}" .bibliothek'}},
                                {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.md", "content": SATZ}}]},
    ]


class Protokoll(unittest.TestCase):
    def test_kein_text_aus_fehlern_befehlen_und_suchen(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "claude-execution-output.json"
            pfad.write_text(json.dumps(verlauf(), ensure_ascii=False), encoding="utf-8")
            zusammenfassung = Path(ordner) / "summary.md"
            ausgabe = io.StringIO()
            with mock.patch.object(sys, "argv", ["agent_bericht.py", str(pfad)]), \
                    mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(zusammenfassung)}), \
                    redirect_stdout(ausgabe):
                self.assertEqual(agent_bericht.main(), 0)
            alles = (ausgabe.getvalue() + zusammenfassung.read_text(encoding="utf-8")).casefold()
        for teil in (KUNSTWORT, "lindenhonig", "bei frost"):
            self.assertNotIn(teil.casefold(), alles)
        # Was zur Fehlersuche bleibt: Werkzeug, Datei, Fehlerart, Programm
        self.assertIn("string to replace not found in file.", alles)
        self.assertIn("found 2 matches", alles)
        self.assertIn("command: python tools/bibliothek_suchen.py …", alles)
        self.assertIn("command: grep …", alles)
        self.assertIn("file_path: entwuerfe/entwurf/x.md", alles)
        self.assertIn("werkzeugfehler: 5", alles)
        self.assertIn("abgelehnte berechtigungen: 2", alles)

    def test_befehl_kurz(self):
        self.assertEqual(agent_bericht.befehl_kurz("git push -u origin entwurf/x"), "git push …")
        self.assertEqual(agent_bericht.befehl_kurz("gh pr create --draft --title X"), "gh pr create …")
        self.assertEqual(agent_bericht.befehl_kurz("wc -w datei.md"), "wc …")
        self.assertEqual(agent_bericht.befehl_kurz("ls"), "ls")

    def test_wortgleich_intern_ohne_werk_und_seite(self):
        """Mit Treffern endet die Prüfung mit Rückgabewert 1 – für den Agenten ein Werkzeugfehler. Mit
        --intern nennt ihre Ausgabe Werk und Seite; ins öffentliche Protokoll kommt davon nichts."""
        kennung = "zz-geheimwerk-kennung-4711"
        ausgabe_werkzeug = ("Exit code 1\nWortgleich-Prüfung: 1 Entwurf gegen 92 Werke und 3 amtliche Texte, "
                            "Grenze 8 Wörter, 0 Wortfolgen freigegeben, 1.2 s.\nInterne Ausgabe mit Werk und Seite\n"
                            "entwuerfe/entwurf/x.md: 1 Treffer, 0 Hinweise\n"
                            f"  Zeile 14 · Messen · 9 Wörter · {kennung} S. 987 · kommt in 2 Werken vor\ntreffer=1")
        daten = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "p1", "name": "Bash",
                 "input": {"command": "python tools/wortgleich_pruefen.py entwuerfe/entwurf/x.md "
                                      "--bibliothek .bibliothek --intern"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "p1", "is_error": True,
                 "content": [{"type": "text", "text": ausgabe_werkzeug}]}]}},
            {"type": "result", "num_turns": 2, "subtype": "success", "result": "ERGEBNIS: OK"},
        ]
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "claude-execution-output.json"
            pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
            zusammenfassung = Path(ordner) / "summary.md"
            ausgabe = io.StringIO()
            with mock.patch.object(sys, "argv", ["agent_bericht.py", str(pfad)]), \
                    mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(zusammenfassung)}), \
                    redirect_stdout(ausgabe):
                self.assertEqual(agent_bericht.main(), 0)
            alles = ausgabe.getvalue() + zusammenfassung.read_text(encoding="utf-8")
        for teil in (kennung, "S. 987", "Werken", "Messen", "--intern"):
            self.assertNotIn(teil, alles)
        self.assertIn("Bash (command: python tools/wortgleich_pruefen.py …) → Exit code 1 · treffer=1 · "
                      "Ausgabe nicht gezeigt", alles)


if __name__ == "__main__":
    unittest.main()
