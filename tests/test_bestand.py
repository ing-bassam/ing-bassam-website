"""Tests für tools/bestand.py und den ERGEBNIS-Block in tools/agent_bericht.py.

Aufruf: python -m unittest discover -s tests
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import agent_bericht  # noqa: E402
import bestand  # noqa: E402

ENTWURF = """---
titel: "Pauschalpreis im Bauvertrag: Was ist wirklich enthalten?"
format: Rechtsprechung
fassung: verständlich
kernfrage: Was ist in einem Pauschalpreis enthalten?
aktenzeichen: 10 U 308/20
ecli: ECLI:DE:OLGSTUT:2021:0309.10U308.20.00
kurzform: pauschalpreis-bauvertrag-leistungsbeschreibung
status: Entwurf
notion_id: 3e5d96ad-00b4-8112-bea6-eb068b017c48
---

# Pauschalpreis
"""


class Eintrag(unittest.TestCase):
    def test_entwurf(self):
        e = bestand.eintrag_aus_entwurf(ENTWURF, "entwuerfe/entwurf/2026-10-02-x.md", "hauptzweig")
        self.assertEqual(e["art"], "urteil")
        self.assertEqual(e["status"], "entwurf")
        self.assertEqual(e["link"], "")
        self.assertEqual(e["notion_id"], "3e5d96ad00b48112bea6eb068b017c48")
        self.assertEqual(e["aktenzeichen"], "10 U 308/20")

    def test_veroeffentlicht(self):
        text = ENTWURF.replace("status: Entwurf", "status: Veröffentlicht")
        e = bestand.eintrag_aus_entwurf(text, "entwuerfe/veroeffentlicht/2026-10-02-x.md", "hauptzweig")
        self.assertEqual(e["status"], "veröffentlicht")
        self.assertEqual(e["link"], "https://ing-bassam.de/fachwissen/pauschalpreis-bauvertrag-leistungsbeschreibung/")

    def test_ohne_titel_kein_eintrag(self):
        self.assertIsNone(bestand.eintrag_aus_entwurf("---\nformat: Ratgeber\n---\n", "entwuerfe/x.md", "hauptzweig"))

    def test_arten(self):
        self.assertEqual(bestand.art_von("Vorlage"), "vorlage")
        self.assertEqual(bestand.art_von("Urteil verständlich"), "urteil")
        self.assertEqual(bestand.art_von("Checkliste"), "beitrag")


class PullRequests(unittest.TestCase):
    def test_zusammengefuehrte_zaehlen_nur_ohne_datei_auf_main(self):
        prs = [
            {"number": 1, "state": "OPEN", "url": "u1", "files": [{"path": "entwuerfe/entwurf/2026-10-03-neu.md"}]},
            {"number": 2, "state": "MERGED", "url": "u2",
             "files": [{"path": "entwuerfe/entwurf/2026-10-01-online.md"}]},          # liegt heute unter veroeffentlicht/
            {"number": 3, "state": "MERGED", "url": "u3",
             "files": [{"path": "entwuerfe/entwurf/2026-10-02-entfernt.md"}]},        # auf main wieder gelöscht
        ]
        with mock.patch.object(bestand.shutil, "which", return_value="gh"), \
                mock.patch.object(bestand, "repo_name", return_value="a/b"), \
                mock.patch.object(bestand, "pull_requests", return_value=prs), \
                mock.patch.object(bestand, "pr_datei", side_effect=lambda r, n, p: f"Text {n}"):
            texte = bestand.pr_texte({"entwuerfe/veroeffentlicht/2026-10-01-online.md"}, [])
        self.assertEqual(sorted(t["pr"]["number"] for t in texte), [1, 3])

    def test_github_nicht_erreichbar_gibt_warnung(self):
        warnungen = []
        with mock.patch.object(bestand.shutil, "which", return_value="gh"), \
                mock.patch.object(bestand, "repo_name", side_effect=RuntimeError("offline")):
            self.assertEqual(bestand.pr_texte(set(), warnungen), [])
        self.assertTrue(warnungen)

    def test_laden_zaehlt_beitrag_auf_main_nur_einmal(self):
        texte = [{"pfad": "entwuerfe/entwurf/2026-10-02-x.md", "text": ENTWURF, "quelle": "hauptzweig", "pr": None},
                 {"pfad": "entwuerfe/2026-10-02-x.md", "text": ENTWURF, "quelle": "pull_request",
                  "pr": {"number": 70, "state": "MERGED", "url": "u"}}]
        with mock.patch.object(bestand, "texte", return_value=texte):
            eintraege = bestand.laden(notion=False)["eintraege"]
        self.assertEqual([e["quelle"] for e in eintraege], ["hauptzweig"])


@unittest.skipUnless(shutil.which("git"), "git fehlt")
class Hauptzweig(unittest.TestCase):
    def test_texte_am_stand(self):
        with tempfile.TemporaryDirectory() as ordner:
            wurzel = Path(ordner)
            (wurzel / "entwuerfe" / "entwurf").mkdir(parents=True)
            (wurzel / "entwuerfe" / "entwurf" / "2026-10-02-x.md").write_text(ENTWURF, encoding="utf-8")
            (wurzel / "entwuerfe" / "README.md").write_text("Übersicht", encoding="utf-8")
            for befehl in (["init", "-q"], ["add", "-A"],
                           ["-c", "user.name=Test", "-c", "user.email=t@example.org", "commit", "-q", "-m", "x"]):
                subprocess.run(["git", *befehl], cwd=wurzel, check=True, capture_output=True)
            with mock.patch.object(bestand, "WURZEL", wurzel):
                texte = bestand.texte_am_stand("HEAD")
        self.assertEqual([p for p, _ in texte], ["entwuerfe/entwurf/2026-10-02-x.md"])
        self.assertEqual(texte[0][1], ENTWURF)

    def test_ohne_netz_der_ausgecheckte_stand(self):
        warnungen = []
        with mock.patch.object(bestand, "_git", side_effect=RuntimeError("kein Netz")):
            texte = bestand.hauptzweig_texte(warnungen)
        self.assertTrue(warnungen)
        self.assertTrue(any(p.startswith("entwuerfe/") for p, _ in texte))


class ErgebnisBlock(unittest.TestCase):
    def test_duplikat_mit_grund(self):
        meldung = "Fertig.\n\nERGEBNIS: DUPLIKAT\nGrund: Kernfrage wie entwuerfe/entwurf/x.md\nPR: -"
        self.assertEqual(agent_bericht.ergebnis_block(meldung), ("DUPLIKAT", "Kernfrage wie entwuerfe/entwurf/x.md"))

    def test_fettdruck_und_mehrere_woerter(self):
        self.assertEqual(agent_bericht.ergebnis_block("**ERGEBNIS: KEIN AUFTRAG**\n**Grund:** fehlt"),
                         ("KEIN AUFTRAG", "fehlt"))

    def test_der_letzte_block_gilt(self):
        meldung = "ERGEBNIS: OK | DUPLIKAT | ABBRUCH\n\nERGEBNIS: ABBRUCH\nGrund: zu kurz"
        self.assertEqual(agent_bericht.ergebnis_block(meldung), ("ABBRUCH", "zu kurz"))

    def test_ohne_block(self):
        self.assertEqual(agent_bericht.ergebnis_block("nichts"), ("", ""))

    def test_abschlussmeldung_aus_dem_verlauf(self):
        verlauf = [{"type": "system", "message": "Claude Code initialized"},
                   {"type": "assistant", "message": {"content": [{"type": "text", "text": "ERGEBNIS: OK"}]}}]
        self.assertEqual(agent_bericht.abschlussmeldung(verlauf), "ERGEBNIS: OK")


if __name__ == "__main__":
    unittest.main()
