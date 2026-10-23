"""Prüft die Workflows auf die Regeln des Wochenplans – ohne sie auszuführen.

    - Jeder Zeitplan hat die Zeitzone Europe/Berlin und keine volle oder halbe
      Stunde (zu diesen Zeiten lässt GitHub geplante Läufe öfter ausfallen).
    - Die Schreib-Agenten laufen an verschiedenen Tagen.
    - Jeder geplante Agent prüft die Kontingent-Bremse, erkennt das Wochenlimit
      und gibt seinen Pull Request erst nach den Prüfungen frei.
    - Geplante Läufe haben keine Eingaben: Jede, die das Verhalten bestimmt,
      braucht einen Standardwert.
    - Der Commit der Veröffentlichung gilt der Hauptzweig-Kontrolle als erlaubt.
    - Urheberrecht (Regel des Inhabers): Jeder Agent prüft vor der Freigabe ohne
      KI auf wörtliche Übernahmen aus der Fachbibliothek und auf den Normstand,
      fail-closed; die Skills erlauben keine wörtlichen Buchzitate mehr.

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

    def test_agenten_nur_montag_bis_donnerstag(self):
        """Freitag bis Sonntag entstehen keine Entwürfe: Der Wochenbericht kommt freitags,
        das Wochenende gehört den Videos des Auftraggebers."""
        tage: dict[int, list[str]] = {}
        for name in AGENTEN:
            for cron, _ in zeitplaene(text(name)):
                for tag in wochentage(cron):
                    tage.setdefault(tag, []).append(name)
        self.assertTrue(set(tage) <= {1, 2, 3, 4}, tage)
        self.assertEqual(set(tage), {1, 2, 3, 4})
        # Die beiden Urteils-Agenten teilen sich eine Warteschlange – nie am selben Tag.
        for tag, namen in tage.items():
            self.assertFalse({"urteil.yml", "urteil-verstaendlich.yml"} <= set(namen), tage)

    def test_trend_agent_nach_dem_neustart(self):
        self.assertEqual(zeitplaene(text("trendscout.yml")), [("17 4 * * 3", "Europe/Berlin")])

    def test_wochenbericht_freitags(self):
        self.assertEqual(zeitplaene(text("wochenpruefung.yml")), [("7 8 * * 5", "Europe/Berlin")])


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

    def test_stichwortzettel_nach_der_veroeffentlichung(self):
        inhalt = text("veroeffentlichen.yml")
        self.assertIn("/stichwortzettel", inhalt)
        self.assertIn("stichwortzettel.py auftrag", inhalt)
        self.assertIn("stichwortzettel.py ablegen", inhalt)
        self.assertIn("id-token: write", inhalt)
        self.assertTrue((WURZEL / ".claude" / "skills" / "stichwortzettel" / "SKILL.md").is_file())

    def test_commit_ist_fuer_die_hauptzweig_kontrolle_erlaubt(self):
        erste_zeile = re.search(r'git commit -q -m "([^"]+)"', text("veroeffentlichen.yml")).group(1)
        self.assertIn(erste_zeile, hauptzweig_pruefen.ERLAUBTE_BOT_COMMITS)


INHABERREGEL = (
    "Aus Fachbüchern, Fachaufsätzen, Normen, Regelwerken und Leistungsverzeichnissen wird nichts wörtlich übernommen: "
    "kein Satz, kein Satzteil, keine Tabelle, keine Abbildung, kein Rechenbeispiel – auch nicht in Anführungszeichen. "
    "Diese Quellen dienen nur dazu, Fakten zu prüfen; die Aussage steht in eigenen Worten mit Fundstelle (Werk, Ausgabe, "
    "Seite oder Abschnitt). Kurze wörtliche Zitate sind nur aus amtlichen Werken (Gesetze, Verordnungen, "
    "Gerichtsentscheidungen, § 5 UrhG) erlaubt, mit Fundstelle. Wörtliche Belegstücke aus Büchern oder Normen stehen nie "
    "an öffentlichen Stellen (Repository-Dateien, PR-Texte, PR-Kommentare, Issues, Logs, Job-Zusammenfassungen), sondern "
    "nur in Arbeitsdateien im Runner-Temp.")


def skill(name: str) -> str:
    return (WURZEL / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def schritte(name: str) -> list[dict]:
    import yaml
    daten = yaml.safe_load(text(name))
    return [s for job in (daten.get("jobs") or {}).values() for s in job.get("steps") or []]


class Urheberrecht(unittest.TestCase):
    def test_pruefwerkzeuge_in_agenten_und_entwurfspruefung(self):
        for name in (*AGENTEN, "entwurf-pruefen.yml"):
            inhalt = text(name)
            with self.subTest(workflow=name):
                self.assertIn("wortgleich_pruefen.py", inhalt)
                self.assertIn("normstand_pruefen.py", inhalt)
                self.assertIn("Bash(python tools/wortgleich_pruefen.py:*)", inhalt)
                self.assertIn("Bash(python tools/normstand_pruefen.py:*)", inhalt)

    def test_veroeffentlichen_prueft_wortgleich(self):
        inhalt = text("veroeffentlichen.yml")
        self.assertIn("wortgleich_pruefen.py", inhalt)
        self.assertIn("--wortgleich", inhalt)
        self.assertIn("path: .bibliothek", inhalt)
        self.assertIn("persist-credentials: false", inhalt)

    def test_freigabe_nur_nach_der_pruefung_fail_closed(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML fehlt")
        for name in AGENTEN:
            liste = schritte(name)
            namen = [s.get("name") for s in liste]
            with self.subTest(workflow=name):
                pruefung = namen.index("Wörtliche Übernahmen und Normstand prüfen (ohne KI)")
                freigabe = namen.index("Zum Mergen freigeben")
                self.assertLess(pruefung, freigabe)
                self.assertEqual(liste[pruefung].get("id"), "wortlaut")
                self.assertIn("steps.wortlaut.outputs.freigabe == 'true'", liste[freigabe]["if"])
                skript = liste[pruefung]["run"]
                self.assertNotIn("${{", skript)
                self.assertIn("--bibliothek .bibliothek", skript)
                self.assertIn("--ausgaben .bibliothek/normen/ausgaben.yml", skript)
                self.assertIn("gh pr comment", skript)
                self.assertIn("::error", skript)
                # Freigegeben wird nur, wenn kein Grund vorliegt; Exit 1 und 2 sind Gründe.
                self.assertEqual(skript.count("freigabe=true"), 1)

    def test_entwurfspruefung_meldet_befund_als_fehler(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML fehlt")
        liste = schritte("entwurf-pruefen.yml")
        namen = [s.get("name") for s in liste]
        pruefung = namen.index("Wörtliche Übernahmen und Normstand prüfen (ohne KI)")
        vorlegen = namen.index("Korrekturen als Pull Request vorlegen")
        self.assertLess(namen.index("Schlussprüfung gegen die Quellen"), pruefung)
        self.assertLess(pruefung, vorlegen)
        skript = liste[vorlegen]["run"]
        self.assertIn("WORTLAUTBERICHT", skript)
        self.assertIn("--draft", skript)
        self.assertIn("exit 1", skript)

    def test_wochenpruefung_meldet_normenindex(self):
        inhalt = text("wochenpruefung.yml")
        self.assertIn("normen/ausgaben.yml", inhalt)
        self.assertIn("stand_index", inhalt)
        self.assertIn("HOECHSTALTER=45", inhalt)

    def test_pruefwerkzeuge_vom_hauptzweig(self):
        """Werkzeug und Freigabeliste kommen nie aus dem Zweig des Agenten (er könnte sie ändern)."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML fehlt")
        for name in (*AGENTEN, "entwurf-pruefen.yml"):
            liste = schritte(name)
            ids = [s.get("id") for s in liste]
            with self.subTest(workflow=name):
                werkzeug = liste[ids.index("werkzeug")]
                self.assertIn('git show "FETCH_HEAD:tools/$datei"', werkzeug["run"])
                self.assertIn("wortgleich_erlaubt.txt", werkzeug["run"])
                self.assertLess(ids.index("werkzeug"), ids.index("wortlaut"))
                pruefung = liste[ids.index("wortlaut")]
                self.assertEqual(pruefung["env"]["WERKZEUG"], "${{ steps.werkzeug.outputs.ordner }}")
                self.assertIn('"$WERKZEUG/wortgleich_pruefen.py"', pruefung["run"])
                aufrufe = re.findall(r"(?m)^\s*python (\S*wortgleich_pruefen\.py\"?)", pruefung["run"])
                self.assertEqual(aufrufe, ['"$WERKZEUG/wortgleich_pruefen.py"'])
                self.assertIn("set +e", pruefung["run"])        # bash -e bricht sonst bei Rückgabewert 1/2 ab
                # Jeder Push und jeder Bericht der Prüf-Agenten kommt erst nach der Prüfung
                for schritt in liste:
                    skript = schritt.get("run") or ""
                    if 'git push -q origin "HEAD:$ZWEIG"' in skript:
                        self.assertIn("if geaenderte_texte_frei; then", skript)
                        self.assertIn('wortgleich_frei "$BERICHT"', skript)
                        self.assertLess(liste.index(werkzeug), liste.index(schritt))

    def test_seitenbau_prueft_von_hand_veroeffentlichte(self):
        inhalt = text("seiten-bauen.yml")
        self.assertIn("Von Hand veröffentlichte Beiträge prüfen (ohne KI)", inhalt)
        self.assertIn("python tools/wortgleich_pruefen.py \"$datei\" --bibliothek .bibliothek", inhalt)
        self.assertIn("status: Entwurf", inhalt)

    def test_wochenpruefung_ohne_oeffentliches_bestandsissue(self):
        """Ein öffentliches Issue mit den wörtlichen Übereinstimmungen veröffentlichter Beiträge wäre
        selbst ein Risiko: Den Bestand prüft nur der Inhaber lokal (tools/bestandspruefung.py)."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML fehlt")
        inhalt = text("wochenpruefung.yml")
        self.assertNotIn("bestand", yaml.safe_load(inhalt)["jobs"])
        for verboten in ("bestandspruefung.py", "wortgleich_pruefen.py", "Veröffentlichte Beiträge: wörtliche"):
            self.assertNotIn(verboten, inhalt)
        for datei in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(workflow=datei.name):
                self.assertNotIn("bestandspruefung.py", datei.read_text(encoding="utf-8"))

    def test_kein_workflow_nutzt_intern(self):
        """--intern nennt Werk und Seite – das gehört nie in Logs, Zusammenfassungen oder Kommentare."""
        for datei in sorted(WORKFLOWS.glob("*.yml")):
            inhalt = datei.read_text(encoding="utf-8")
            with self.subTest(workflow=datei.name):
                self.assertFalse("--intern" in inhalt, "--intern im Workflow")
                # Berichte und Ausgabe nennen öffentlich weder Werk noch Seite.
                self.assertIsNone(re.search(r"(?:nennen|nennt) nur Datei, Abschnitt, Zeile,\s+(?:#\s*)?Werk", inhalt))

    def test_wortgleich_json_nie_ins_protokoll(self):
        """Das JSON der Prüfung nennt Werk und Seite: Es bleibt im Runner-Temp – kein Befehl gibt es aus,
        keine Zusammenfassung, kein Kommentar und kein Artefakt enthält es."""
        ausgeben = re.compile(r"\b(?:cat|head|tail|less|more|jq|tee)\b[^|;]*(?:wortgleich\.json|\"\$JSON\")"
                              r"|(?:wortgleich\.json|\"\$JSON\")[^|;]*(?:GITHUB_STEP_SUMMARY|--body-file)")
        for datei in sorted(WORKFLOWS.glob("*.yml")):
            inhalt = datei.read_text(encoding="utf-8")
            with self.subTest(workflow=datei.name):
                self.assertNotIn("upload-artifact", inhalt)
                for zeile in inhalt.splitlines():
                    if not zeile.lstrip().startswith("#"):
                        self.assertNotRegex(zeile, ausgeben)

    def test_skills_werk_und_seite_nur_intern(self):
        for name in ("fachartikel", "schlusspruefung", "urteilsbesprechung", "urteil-verstaendlich", "vorlage"):
            inhalt = skill(name)
            with self.subTest(skill=name):
                self.assertIn("--intern", inhalt)
                self.assertIn("nur zur eigenen Überarbeitung", inhalt)
                self.assertIn("pr-body.md", inhalt)
        claude = (WURZEL / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("--intern", claude)
        self.assertIn("nur zur eigenen Überarbeitung", claude)

    def test_skills_ohne_woertliche_buchzitate(self):
        for name in ("fachartikel", "schlusspruefung"):
            inhalt = skill(name)
            with self.subTest(skill=name):
                for verboten in ("höchstens 25 Wörter", "Belegstück (wörtlich)", "Belegstück Stufe 3 (wörtlich)",
                                 "nur mit dem Wortlaut einer Quelle"):
                    self.assertNotIn(verboten, inhalt)
        self.assertNotIn("höchstens 25 Wörter", (WURZEL / "tools" / "bibliothek_auszug.py").read_text(encoding="utf-8"))

    def test_regel_des_inhabers_wortgleich(self):
        self.assertIn(INHABERREGEL, (WURZEL / "CLAUDE.md").read_text(encoding="utf-8"))
        for name in ("fachartikel", "schlusspruefung"):
            with self.subTest(skill=name):
                self.assertIn(INHABERREGEL, skill(name))

    def test_stand_der_technik_in_den_schreib_skills(self):
        for name in ("fachartikel", "vorlage", "urteilsbesprechung"):
            inhalt = skill(name)
            with self.subTest(skill=name):
                self.assertIn("bibliothek_suchen.py --norm", inhalt)
                self.assertIn("normstand_pruefen.py", inhalt)
                self.assertIn("wortgleich_pruefen.py", inhalt)
                self.assertIn("Stand der Technik – Normausgaben", inhalt)
        pr_vorlage = skill("fachartikel")
        self.assertIn("### Wörtliche Übernahmen (automatische Prüfung)", pr_vorlage)
        self.assertIn("Fundstelle Stufe 3 (Abschnitt/Seite/Rn., kein Wortlaut)", pr_vorlage)
        self.assertIn("Geprüfte Aussage (eigene Worte)", pr_vorlage)
        self.assertIn("VOB-Gesamtausgabe 2019", pr_vorlage)


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
