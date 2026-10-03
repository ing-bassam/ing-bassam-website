"""Prüft die Workflows auf die Regeln des Wochenplans – ohne sie auszuführen.

    - Jeder Zeitplan hat die Zeitzone Europe/Berlin und keine volle oder halbe
      Stunde (zu diesen Zeiten lässt GitHub geplante Läufe öfter ausfallen).
    - Die Schreib-Agenten laufen an verschiedenen Tagen.
    - Jeder geplante Agent prüft die Kontingent-Bremse, erkennt das Wochenlimit
      und gibt seinen Pull Request erst nach den Prüfungen frei.
    - Geplante Läufe haben keine Eingaben: Jede, die das Verhalten bestimmt,
      braucht einen Standardwert.
    - Der Commit der Veröffentlichung gilt der Hauptzweig-Kontrolle als erlaubt.

Aufruf: python -m unittest discover -s tests
"""
import re
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
WORKFLOWS = WURZEL / ".github" / "workflows"
sys.path.insert(0, str(WURZEL / "tools"))

import hauptzweig_pruefen  # noqa: E402

AGENTEN = ("fachartikel.yml", "vorlagen.yml", "urteil.yml", "urteil-verstaendlich.yml", "trendscout.yml")


def text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def zeitplaene(inhalt: str) -> list[tuple[str, str]]:
    """(cron, Zeitzone) je Eintrag unter schedule:."""
    ergebnis = []
    for m in re.finditer(r'(?m)^\s*- cron:\s*"([^"]+)"[^\n]*\n(?:\s*#[^\n]*\n)*(\s*timezone:\s*"([^"]+)")?', inhalt):
        ergebnis.append((m.group(1), m.group(3) or ""))
    return ergebnis


def wochentage(cron: str) -> set[int]:
    feld = cron.split()[4]
    tage = set()
    for teil in feld.split(","):
        if "-" in teil:
            von, bis = (int(x) for x in teil.split("-"))
            tage |= set(range(von, bis + 1))
        elif teil != "*":
            tage.add(int(teil) % 7)
    return tage


class Zeitplaene(unittest.TestCase):
    def test_zeitzone_und_krumme_minute(self):
        for datei in sorted(WORKFLOWS.glob("*.yml")):
            for cron, zone in zeitplaene(datei.read_text(encoding="utf-8")):
                with self.subTest(workflow=datei.name, cron=cron):
                    self.assertEqual(zone, "Europe/Berlin")
                    minute = cron.split()[0]
                    self.assertTrue(minute.isdigit(), "feste Minute erwartet")
                    self.assertNotIn(int(minute), (0, 30))

    def test_agenten_an_verschiedenen_tagen(self):
        belegt: dict[int, str] = {}
        for name in AGENTEN:
            for cron, _ in zeitplaene(text(name)):
                for tag in wochentage(cron):
                    with self.subTest(workflow=name, tag=tag):
                        self.assertNotIn(tag, belegt, f"Tag {tag} schon belegt von {belegt.get(tag)}")
                    belegt[tag] = name
        self.assertEqual(set(belegt), {0, 1, 3, 4, 5, 6})   # dienstags Pause vor dem Neustart des Kontingents

    def test_trend_agent_nach_dem_neustart(self):
        self.assertEqual(zeitplaene(text("trendscout.yml")), [("17 4 * * 3", "Europe/Berlin")])


class Agenten(unittest.TestCase):
    def test_bremse_limit_und_freigabe(self):
        for name in AGENTEN:
            inhalt = text(name)
            with self.subTest(workflow=name):
                self.assertIn("kontingent.py pruefen", inhalt)
                self.assertIn("kontingent.py erkennen", inhalt)
                self.assertIn("gh pr ready \"$NR\" --undo", inhalt)
                self.assertIn("name: Zum Mergen freigeben", inhalt)
                self.assertIn("github.event_name == 'schedule'", inhalt)

    def test_runden_fuer_geplante_laeufe(self):
        for name, runden in (("fachartikel.yml", "2"), ("vorlagen.yml", "2"), ("urteil.yml", "1"),
                             ("urteil-verstaendlich.yml", "1")):
            with self.subTest(workflow=name):
                self.assertRegex(text(name), rf'RUNDEN_GEPLANT: "{runden}"')
                self.assertIn("needs.planen.outputs.anzahl != '0'", text(name))

    def test_nur_deutsche_themen_bis_die_englische_ausgabe_steht(self):
        abfrage = re.search(r"abfrage='(\{.*?\})'\n", text("fachartikel.yml")).group(1)
        self.assertIn('"property":"Sprache","select":{"is_empty":true}', abfrage)
        self.assertIn('"property":"Sprache","select":{"equals":"Deutsch"}', abfrage)

    def test_doppelungspruefung_vor_der_themenwahl(self):
        self.assertIn("doppelungen.py auswahl --kandidaten", text("fachartikel.yml"))
        self.assertIn("--liste vorlagen", text("vorlagen.yml"))
        self.assertIn("cat \"$VERWANDT\"", text("fachartikel.yml"))
        self.assertIn("doppelungen.py markieren", text("fachartikel.yml"))

    def test_skills_legen_entwuerfe_an(self):
        for skill in ("fachartikel", "vorlage"):
            inhalt = (WURZEL / ".claude" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            befehle = re.findall(r"gh pr create --[^`\n]*", inhalt)      # Befehle mit Argumenten
            with self.subTest(skill=skill):
                self.assertTrue(befehle)
                self.assertTrue(all("--draft" in b for b in befehle), befehle)


class Veroeffentlichen(unittest.TestCase):
    def test_automatik_ohne_eingaben(self):
        inhalt = text("veroeffentlichen.yml")
        self.assertIn("inputs.auswahl || 'automatisch'", inhalt)
        self.assertIn("--automatisch --max 2", inhalt)
        self.assertEqual(zeitplaene(inhalt), [("43 7 * * 1-5", "Europe/Berlin")])

    def test_commit_ist_fuer_die_hauptzweig_kontrolle_erlaubt(self):
        erste_zeile = re.search(r'git commit -q -m "([^"]+)"', text("veroeffentlichen.yml")).group(1)
        self.assertIn(erste_zeile, hauptzweig_pruefen.ERLAUBTE_BOT_COMMITS)


class Ausdruecke(unittest.TestCase):
    """GitHub begrenzt run-Blöcke mit Ausdrücken in doppelten geschweiften Klammern auf 21.000 Zeichen."""

    def test_lange_skripte_ohne_ausdruecke(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML fehlt")
        for datei in sorted(WORKFLOWS.glob("*.yml")):
            daten = yaml.safe_load(datei.read_text(encoding="utf-8"))
            for job in (daten.get("jobs") or {}).values():
                for schritt in job.get("steps") or []:
                    skript = schritt.get("run") or ""
                    if "${{" in skript:
                        with self.subTest(workflow=datei.name, schritt=schritt.get("name")):
                            self.assertLess(len(skript), 21000)


if __name__ == "__main__":
    unittest.main()
