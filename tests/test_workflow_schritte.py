"""Führt die Prüfschritte der Workflows wirklich aus – mit nachgebildetem gh und python.

GitHub startet run-Schritte mit „bash -e“ (ohne shell:) bzw. „bash --noprofile --norc
-eo pipefail“ (defaults.run.shell: bash). „set -uo pipefail“ im Schritt schaltet -e
nicht ab. Liefert ein Prüfwerkzeug 1 (Treffer) oder 2 (nicht geprüft), darf der
Schritt trotzdem nicht abbrechen: Bericht, Kommentar und Ausgaben müssen kommen, und
freigegeben wird nur bei 0/0 (fail-closed). Die Tests ziehen die run-Blöcke aus den
Workflow-Dateien und führen sie unter beiden Aufrufarten aus.

Aufruf: python -m unittest discover -s tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
WORKFLOWS = WURZEL / ".github" / "workflows"
AGENTEN = ("fachartikel.yml", "vorlagen.yml", "urteil.yml", "urteil-verstaendlich.yml", "trendscout.yml")
BASH = shutil.which("bash")
GIT = shutil.which("git")
# Auf Windows kann „bash“ der WSL-Starter sein – der kennt die Pfade nicht.
GEEIGNET = bool(BASH) and "system32" not in BASH.lower()
AUFRUFE = (("bash", "-e"), ("bash", "--noprofile", "--norc", "-eo", "pipefail"))

GH = r"""#!/bin/sh
# Nachbildung von gh: Dateien des Pull Requests lesen, Kommentare mitschreiben
case "$1 $2" in
  "pr view") [ -n "$STUB_DATEIEN" ] && cat "$STUB_DATEIEN"; exit "${STUB_GH_VIEW:-0}" ;;
  "pr comment")
    shift 2
    while [ $# -gt 0 ]; do
      case "$1" in
        --body-file) cat "$2" >> "$STUB_KOMMENTARE"; echo "-----" >> "$STUB_KOMMENTARE"; shift 2 ;;
        --body) printf '%s\n-----\n' "$2" >> "$STUB_KOMMENTARE"; shift 2 ;;
        *) shift ;;
      esac
    done
    exit 0 ;;
esac
exit 0
"""

PYTHON = r"""#!/bin/sh
# Nachbildung der Prüfwerkzeuge: Rückgabewert und letzte Zeile wie das echte Werkzeug
werkzeug="$1"
shift
case "$werkzeug" in
  *wortgleich_pruefen.py) rc="${STUB_WORT:-0}"; zeile="treffer=$rc" ;;
  *normstand_pruefen.py) rc="${STUB_NORM:-0}"; zeile="fehler=$rc hinweise=0" ;;
  -c) exec "$STUB_ECHTES_PYTHON" -c "$@" ;;
  *) exit 0 ;;
esac
echo "$werkzeug $*" >> "$STUB_AUFRUFE"
while [ $# -gt 0 ]; do
  case "$1" in
    --bericht) echo "## Bericht ($zeile)" > "$2"; shift 2 ;;
    --json)
      if [ "$rc" = 2 ]; then echo '{"geprueft": false}' > "$2"; else echo "{\"geprueft\": true, \"anzahl_treffer\": $rc}" > "$2"; fi
      shift 2 ;;
    *) shift ;;
  esac
done
echo "$zeile"
exit "$rc"
"""


def run_block(workflow: str, schritt_id: str) -> tuple[str, dict]:
    import yaml
    daten = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    for job in daten["jobs"].values():
        for schritt in job.get("steps") or []:
            if schritt.get("id") == schritt_id:
                return schritt["run"], schritt.get("env") or {}
    raise AssertionError(f"{workflow}: kein Schritt {schritt_id}")


@unittest.skipUnless(GEEIGNET, "bash fehlt")
class Grundlage(unittest.TestCase):
    def setUp(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML fehlt")
        self.ordner = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.ordner.name)
        self.stubs = self.wurzel / "stubs"
        self.stubs.mkdir()
        for name, inhalt in (("gh", GH), ("python", PYTHON), ("python3", PYTHON)):
            pfad = self.stubs / name
            pfad.write_text(inhalt, encoding="utf-8", newline="\n")
            pfad.chmod(0o755)
        self.repo = self.wurzel / "repo"
        (self.repo / "entwuerfe" / "entwurf").mkdir(parents=True)
        (self.repo / "entwuerfe" / "entwurf" / "2026-10-20-test.md").write_text("---\ntitel: Test\n---\n\nText.\n",
                                                                                  encoding="utf-8", newline="\n")
        self.temp = self.wurzel / "runner-temp"
        self.temp.mkdir()
        self.werkzeug = self.wurzel / "pruefwerkzeug"
        self.werkzeug.mkdir()
        for name in ("wortgleich_pruefen.py", "normstand_pruefen.py"):
            (self.werkzeug / name).write_text("# Platzhalter\n", encoding="utf-8", newline="\n")
        self.dateien = self.wurzel / "dateien.txt"
        self.dateien.write_text("entwuerfe/entwurf/2026-10-20-test.md\nsitemap.xml\n", encoding="utf-8", newline="\n")
        self.kommentare = self.wurzel / "kommentare.txt"
        self.aufrufe = self.wurzel / "aufrufe.txt"

    def tearDown(self):
        self.ordner.cleanup()

    def starten(self, workflow: str, schritt_id: str, aufruf=AUFRUFE[0], schritt: dict | None = None,
                **umgebung) -> tuple[int, dict, str, str]:
        """Führt den run-Block aus (Schritt mit `schritt_id` oder der übergebene `schritt`)."""
        skript, env = (schritt["run"], schritt.get("env") or {}) if schritt else run_block(workflow, schritt_id)
        datei = self.wurzel / "schritt.sh"
        datei.write_text(skript, encoding="utf-8", newline="\n")
        ausgabe = self.wurzel / "github_output"
        zusammenfassung = self.wurzel / "summary"
        for pfad in (ausgabe, zusammenfassung, self.kommentare):
            pfad.write_text("", encoding="utf-8", newline="\n")
        werte = {k: str(v) for k, v in env.items() if "${{" not in str(v)}   # feste Werte wie TITEL
        werte.update({
            "PATH": str(self.stubs) + os.pathsep + os.environ.get("PATH", ""),
            "RUNNER_TEMP": str(self.temp), "GITHUB_OUTPUT": str(ausgabe), "GITHUB_STEP_SUMMARY": str(zusammenfassung),
            "NR": "42", "GH_TOKEN": "x", "WERKZEUG": str(self.werkzeug), "STUB_DATEIEN": str(self.dateien),
            "STUB_KOMMENTARE": str(self.kommentare), "STUB_AUFRUFE": str(self.aufrufe),
            "STUB_ECHTES_PYTHON": sys.executable.replace("\\", "/"),
        })
        werte.update({k: str(v) for k, v in umgebung.items()})
        for schluessel in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE"):
            if schluessel in os.environ and schluessel not in werte:
                werte[schluessel] = os.environ[schluessel]
        lauf = subprocess.run([BASH, *aufruf[1:], str(datei)], cwd=self.repo, env=werte, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)
        ausgaben = dict(z.split("=", 1) for z in ausgabe.read_text(encoding="utf-8").splitlines() if "=" in z)
        return lauf.returncode, ausgaben, self.kommentare.read_text(encoding="utf-8"), lauf.stdout + lauf.stderr


class Freigabeschritt(Grundlage):
    """Schritt „Wörtliche Übernahmen und Normstand prüfen (ohne KI)“ der fünf Agenten."""

    def test_rueckgabewerte_unter_bash_e(self):
        for workflow in AGENTEN:
            for aufruf in AUFRUFE:
                for wort, norm in ((0, 0), (1, 0), (0, 1), (2, 0), (0, 2), (1, 1)):
                    with self.subTest(workflow=workflow, aufruf=" ".join(aufruf), wort=wort, norm=norm):
                        code, ausgaben, kommentare, protokoll = self.starten(
                            workflow, "wortlaut", aufruf, STUB_WORT=wort, STUB_NORM=norm)
                        self.assertEqual(code, 0, protokoll)
                        sauber = (wort, norm) == (0, 0)
                        self.assertEqual(ausgaben.get("freigabe"), "true" if sauber else "false", protokoll)
                        self.assertIn("## Wörtliche Übernahmen und Normstand (automatische Prüfung)", kommentare)
                        self.assertIn("✅" if sauber else "⛔", kommentare)
                        if not sauber:
                            self.assertIn("::error", protokoll)
                            self.assertIn("nie Werk, Seite oder Text aus der Bibliothek", kommentare)
        # Werk und Seite (--intern) gehören nie in den öffentlichen Kommentar
        self.assertNotIn("--intern", self.aufrufe.read_text(encoding="utf-8"))

    def test_ohne_werkzeug_bibliothek_oder_entwurf_keine_freigabe(self):
        faelle = {"ohne Werkzeug": {"WERKZEUG": ""},
                  "ohne Entwurfsdatei": {"STUB_DATEIEN": ""},
                  "Pull Request nicht lesbar": {"STUB_GH_VIEW": "1"}}
        for fall, umgebung in faelle.items():
            with self.subTest(fall=fall):
                code, ausgaben, kommentare, protokoll = self.starten("fachartikel.yml", "wortlaut", **umgebung)
                self.assertEqual(code, 0, protokoll)
                self.assertEqual(ausgaben.get("freigabe"), "false", protokoll)
                self.assertIn("⛔", kommentare)

    def test_aenderung_an_werkzeugen_sperrt(self):
        self.dateien.write_text("entwuerfe/entwurf/2026-10-20-test.md\ntools/wortgleich_erlaubt.txt\n", encoding="utf-8", newline="\n")
        code, ausgaben, kommentare, protokoll = self.starten("fachartikel.yml", "wortlaut")
        self.assertEqual(code, 0, protokoll)
        self.assertEqual(ausgaben.get("freigabe"), "false")
        self.assertIn("tools/wortgleich_erlaubt.txt", kommentare)

    def test_vorlage_wird_mitgeprueft_werkzeug_vom_hauptzweig(self):
        (self.repo / "vorlagen").mkdir()
        (self.repo / "vorlagen" / "fugen.yml").write_text("titel: Fugen\n", encoding="utf-8", newline="\n")
        self.dateien.write_text("entwuerfe/entwurf/2026-10-20-test.md\nvorlagen/fugen.yml\n"
                                "vorlagen/fugen/fugen.pdf\nentwuerfe/README.md\n", encoding="utf-8", newline="\n")
        (self.temp / "schlusspruefung" / "quellen").mkdir(parents=True)
        code, ausgaben, _, protokoll = self.starten("vorlagen.yml", "wortlaut")
        self.assertEqual((code, ausgaben.get("freigabe")), (0, "true"), protokoll)
        aufrufe = self.aufrufe.read_text(encoding="utf-8")
        wortgleich = next(z for z in aufrufe.splitlines() if "wortgleich_pruefen.py" in z)
        self.assertIn(self.werkzeug.name, wortgleich)          # Werkzeug vom Hauptzweig, nicht tools/
        self.assertIn("vorlagen/fugen.yml", wortgleich)
        self.assertIn("--zusatz", wortgleich)
        self.assertNotIn("README", wortgleich)
        self.assertNotIn("fugen.pdf", wortgleich)


class Entwurfspruefung(Grundlage):
    def test_rueckgabewerte(self):
        arbeit = self.wurzel / "arbeit"
        arbeit.mkdir()
        for aufruf in AUFRUFE:
            for wort, norm in ((0, 0), (1, 0), (0, 1), (2, 2)):
                with self.subTest(aufruf=" ".join(aufruf), wort=wort, norm=norm):
                    code, ausgaben, _, protokoll = self.starten(
                        "entwurf-pruefen.yml", "wortlaut", aufruf, STUB_WORT=wort, STUB_NORM=norm,
                        ENTWURF="entwuerfe/entwurf/2026-10-20-test.md", ARBEIT=arbeit)
                    self.assertEqual(code, 0, protokoll)
                    self.assertEqual(ausgaben.get("sauber"), "true" if (wort, norm) == (0, 0) else "false")
                    self.assertEqual(ausgaben.get("wortgleich"), str(wort))
                    self.assertIn("## Wörtliche Übernahmen und Normstand", (arbeit / "wortlaut.md").read_text(
                        encoding="utf-8"))
        self.assertNotIn("--intern", self.aufrufe.read_text(encoding="utf-8"))


class Veroeffentlichen(Grundlage):
    def test_rueckgabewerte(self):
        for aufruf in AUFRUFE:
            for wort in (0, 1, 2):
                with self.subTest(aufruf=" ".join(aufruf), wort=wort):
                    code, ausgaben, _, protokoll = self.starten("veroeffentlichen.yml", "wortgleich", aufruf,
                                                                STUB_WORT=wort)
                    self.assertEqual(code, 0, protokoll)
                    self.assertEqual(ausgaben.get("rueckgabe"), str(wort))
                    daten = json.loads((self.temp / "wortgleich.json").read_text(encoding="utf-8"))
                    self.assertEqual(daten.get("geprueft"), wort != 2)
                    # Das JSON (mit Werk und Seite) bleibt im Runner-Temp; ins Protokoll kommt nur treffer=…
                    self.assertNotIn('"geprueft"', protokoll)
        self.assertNotIn("--intern", self.aufrufe.read_text(encoding="utf-8"))


@unittest.skipUnless(GEEIGNET and GIT, "bash oder git fehlt")
class Korrekturen(Grundlage):
    """Fakten- und Schlussprüfung: erst prüfen, dann pushen und kommentieren."""

    def git(self, *argumente: str, cwd: Path | None = None) -> str:
        return subprocess.run([GIT, *argumente], cwd=cwd or self.repo, check=True, capture_output=True,
                              text=True).stdout.strip()

    def setUp(self):
        super().setUp()
        self.origin = self.wurzel / "origin.git"
        self.git("init", "-q", "--bare", str(self.origin), cwd=self.wurzel)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        (self.repo / "sitemap.xml").write_text("<urlset/>\n", encoding="utf-8", newline="\n")
        (self.repo / "fachwissen").mkdir()
        (self.repo / "fachwissen" / "index.html").write_text("<p>x</p>\n", encoding="utf-8", newline="\n")
        (self.repo / "vorlagen").mkdir()
        (self.repo / "vorlagen" / "fugen.yml").write_text("titel: Fugen\n", encoding="utf-8", newline="\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "Start")
        self.git("remote", "add", "origin", str(self.origin))
        self.git("push", "-q", "origin", "HEAD:refs/heads/entwurf/test")
        self.start = self.git("rev-parse", "HEAD")
        self.bericht = self.wurzel / "bericht.md"

    def schritt_starten(self, workflow: str, nummer: int, wort: int) -> tuple[int, str, str]:
        """nummer: welche Push-Stelle des Workflows (0 = erste)."""
        import yaml
        daten = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
        schritte = [s for job in daten["jobs"].values() for s in job.get("steps") or []
                    if "geaenderte_texte_frei" in (s.get("run") or "")]
        schritt = schritte[nummer]
        (self.repo / "entwuerfe" / "entwurf" / "2026-10-20-test.md").write_text(
            "---\ntitel: Test\n---\n\nKorrigierter Text.\n", encoding="utf-8", newline="\n")
        self.bericht.write_text("## Bericht\n\nAlles geprüft.\n", encoding="utf-8", newline="\n")
        code, _, kommentare, protokoll = self.starten(
            workflow, "", AUFRUFE[0], schritt=schritt, STUB_WORT=wort, ZWEIG="entwurf/test", BERICHT=self.bericht,
            PRUEFUNG="success", ENTWURF="entwuerfe/entwurf/2026-10-20-test.md", DIFF=self.wurzel / "diff.txt")
        gepusht = self.git("log", "--format=%s", "-1", "entwurf/test", cwd=self.origin)
        return code, kommentare, gepusht + "\n" + protokoll

    def test_push_und_bericht_nur_ohne_treffer(self):
        for workflow in AGENTEN:
            daten = (WORKFLOWS / workflow).read_text(encoding="utf-8")
            for nummer in range(daten.count("if geaenderte_texte_frei; then")):
                for wort in (0, 1, 2):
                    with self.subTest(workflow=workflow, stelle=nummer, wort=wort):
                        self.git("reset", "-q", "--hard", self.start)
                        self.git("push", "-q", "-f", "origin", "HEAD:refs/heads/entwurf/test")
                        code, kommentare, protokoll = self.schritt_starten(workflow, nummer, wort)
                        self.assertEqual(code, 0, protokoll)
                        if wort == 0:
                            self.assertTrue(protokoll.startswith(("Schlusspruefung", "Faktenpruefung")), protokoll)
                            self.assertIn("Alles geprüft.", kommentare)
                        else:
                            self.assertTrue(protokoll.startswith("Start"), protokoll)   # nichts gepusht
                            self.assertIn("nicht übernommen", kommentare)
                            self.assertNotIn("Alles geprüft.", kommentare)
                            self.assertEqual(self.git("status", "--porcelain", "--", "entwuerfe"), "")


if __name__ == "__main__":
    unittest.main()
