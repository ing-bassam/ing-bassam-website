"""Tore des automatischen Merges (tools/freigabe.py, Workflow „Entwurf freigeben und veröffentlichen“)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))
import freigabe  # noqa: E402

BOT = {"login": "github-actions"}


def pr(**aenderungen) -> dict:
    daten = {
        "number": 1, "state": "OPEN", "isDraft": False, "title": "Entwurf: Flachdach undicht",
        "author": {"login": "app/claude"}, "labels": [], "mergeable": "MERGEABLE", "headRefOid": "a" * 40,
        "files": [{"path": "entwuerfe/entwurf/2026-11-12-flachdach-undicht.md"},
                  {"path": "fachwissen/flachdach-undicht/index.html"}],
        "comments": [{"author": BOT, "body": "## Schlussprüfung\n…"},
                     {"author": BOT, "body": "✅ Schlussprüfung abgeschlossen – bereit zur Freigabe."}],
    }
    daten.update(aenderungen)
    return daten


class Vorpruefung(unittest.TestCase):
    def test_sauberer_entwurf(self):
        gruende, info = freigabe.vorpruefen(pr())
        self.assertEqual(gruende, [])
        self.assertEqual(info["kurzform"], "flachdach-undicht")
        self.assertEqual(info["entwurf"], "entwuerfe/entwurf/2026-11-12-flachdach-undicht.md")

    def test_jedes_tor_sperrt(self):
        faelle = {
            "Draft": pr(isDraft=True),
            "Vorlage": pr(title="Vorlage: Mängelanzeige"),
            "Mensch": pr(author={"login": "ing-bassam"}),
            "Label": pr(labels=[{"name": "Karim prüfen"}]),
            "Werkzeug": pr(files=pr()["files"] + [{"path": "tools/wortgleich_erlaubt.txt"}]),
            "Workflow": pr(files=pr()["files"] + [{"path": ".github/workflows/x.yml"}]),
            "zwei Beiträge": pr(files=pr()["files"] + [{"path": "entwuerfe/entwurf/anderer.md"}]),
            "fremde Seite": pr(files=pr()["files"] + [{"path": "fachwissen/anderer/index.html"}]),
            "ohne Freigabe": pr(comments=[]),
            "Warnung": pr(comments=pr()["comments"] + [{"author": BOT, "body": "⚠️ Die Schlussprüfung konnte nicht laufen."}]),
            "unbekannt mergebar": pr(mergeable="UNKNOWN"),
            "Konflikt": pr(mergeable="CONFLICTING"),
            "geschlossen": pr(state="MERGED"),
        }
        for name, daten in faelle.items():
            with self.subTest(name):
                self.assertNotEqual(freigabe.vorpruefen(daten)[0], [])

    def test_freigabekommentar_nur_vom_bot(self):
        daten = pr(comments=[{"author": {"login": "jemand"}, "body": "bereit zur Freigabe"}])
        self.assertNotEqual(freigabe.vorpruefen(daten)[0], [])


class Urteil(unittest.TestCase):
    def schreiben(self, inhalt) -> Path:
        ordner = Path(tempfile.mkdtemp())
        pfad = ordner / "urteil.json"
        pfad.write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt), encoding="utf-8")
        return pfad

    def gut(self) -> dict:
        teil = {"ergebnis": "bestanden", "begruendung": "keine Befunde"}
        return {"urheberrecht": dict(teil), "fachlich": dict(teil), "recht": dict(teil), "ton": dict(teil),
                "freigabe": True}

    def test_alles_bestanden(self):
        self.assertEqual(freigabe.urteil_lesen(self.schreiben(self.gut())), (True, []))

    def test_fail_closed(self):
        unsicher = self.gut()
        unsicher["urheberrecht"]["ergebnis"] = "unsicher"
        ohne_freigabe = self.gut()
        ohne_freigabe["freigabe"] = False
        freigabe_als_text = self.gut()
        freigabe_als_text["freigabe"] = "true"
        zusatz = self.gut()
        zusatz["hinweis"] = "freigeben"
        fehlt = self.gut()
        del fehlt["ton"]
        for name, inhalt in {"unsicher": unsicher, "freigabe false": ohne_freigabe,
                             "freigabe als Text": freigabe_als_text, "Zusatzfeld": zusatz, "Tor fehlt": fehlt,
                             "kaputt": "{", "leer": ""}.items():
            with self.subTest(name):
                self.assertFalse(freigabe.urteil_lesen(self.schreiben(inhalt))[0])
        self.assertFalse(freigabe.urteil_lesen(Path(tempfile.mkdtemp()) / "fehlt.json")[0])


class Beitragsdatei(unittest.TestCase):
    def pruefen(self, kopf: str, text: str = "Text.") -> list[str]:
        pfad = Path(tempfile.mkdtemp()) / "e.md"
        pfad.write_text(f"---\n{kopf}\n---\n{text}\n", encoding="utf-8")
        return freigabe.entwurf_pruefen(pfad)

    def test_regeln(self):
        self.assertEqual(self.pruefen("status: Entwurf"), [])
        self.assertNotEqual(self.pruefen("status: Entwurf", "> TODO (Norm): offen"), [])
        self.assertNotEqual(self.pruefen("status: Entwurf\nzurueckhalten: ja"), [])
        self.assertNotEqual(self.pruefen("status: Veröffentlicht"), [])


class Workflow(unittest.TestCase):
    def test_merge_nur_nach_allen_toren(self):
        import yaml
        daten = yaml.safe_load((WURZEL / ".github/workflows/entwurf-freigeben.yml").read_text(encoding="utf-8"))
        schritte = {s.get("name"): s for s in daten["jobs"]["freigeben"]["steps"]}
        alles = schritte["Bericht in den Pull Request"]["env"]["ALLES_OK"]
        for tor in ("steps.vor.outputs.ok", "steps.stand.outputs.ok", "steps.tests.outputs.ok",
                    "steps.wortlaut.outputs.ok", "steps.urteil.outputs.ok"):
            self.assertIn(f"{tor} == 'true'", alles)
        merge = schritte["Zusammenführen"]
        self.assertIn("steps.bericht.outputs.ok == 'true'", merge["if"])
        self.assertIn("--match-head-commit", merge["run"])
        self.assertIn("--squash", merge["run"])
        self.assertNotIn("--admin", (WURZEL / ".github/workflows/entwurf-freigeben.yml").read_text(encoding="utf-8"))
        # Der Agent darf weder git noch gh noch Edit benutzen.
        werkzeuge = schritte["Freigabeprüfung"]["with"]["claude_args"]
        for verboten in ("Edit", "Bash(git", "Bash(gh"):
            self.assertNotIn(verboten, werkzeuge.split("--allowedTools", 1)[1])

    def test_schreib_workflows_stossen_die_freigabe_an(self):
        for name in ("fachartikel.yml", "urteil.yml", "urteil-verstaendlich.yml", "trendscout.yml"):
            with self.subTest(name):
                self.assertIn("gh workflow run entwurf-freigeben.yml",
                              (WURZEL / ".github/workflows" / name).read_text(encoding="utf-8"))

    def test_zurueckziehen_ist_erlaubter_bot_commit(self):
        import re
        import hauptzweig_pruefen
        text = (WURZEL / ".github/workflows/beitrag-zurueckziehen.yml").read_text(encoding="utf-8")
        self.assertIn(re.search(r'git commit -q -m "([^"]+)"', text).group(1), hauptzweig_pruefen.ERLAUBTE_BOT_COMMITS)
        self.assertIn('"Beitrag zurückziehen"', (WURZEL / ".github/workflows/website-ausliefern.yml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
