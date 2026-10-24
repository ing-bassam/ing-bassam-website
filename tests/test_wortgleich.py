"""Tests für tools/wortgleich_pruefen.py mit einer erfundenen Mini-Bibliothek.

Alle Bibliotheks- und Entwurfstexte hier sind erfunden – kein Buch-, Norm- oder
Gesetzestext. Das Kunstwort „Quarzbläulingsfuge“ steht nur im Bibliothekstext
(und in kopierten Entwurfssätzen); es darf nie in Ausgabe, Bericht oder JSON
auftauchen. Die Werk-Kennung „zz-geheimwerk-kennung-4711“ und ihre Seite stehen
nur im JSON und – mit --intern – in Ausgabe und Bericht.

Aufruf: python -m unittest discover -s tests
"""
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import wortgleich_pruefen as w  # noqa: E402

KUNSTWORT = "Quarzbläulingsfuge"
TRENNLINIE = "=" * 70

BUCH = f"""Werk: muster-fugenlehre-2020
Zitat: Mustermann, Max: Fugenlehre für Prüfstände. Ein erfundenes Lehrbuch für Tests. Teststadt: Probeverlag, 2020
Hinweis: Diese Kopfzeile ist nur für die interne Prüfung bestimmt und wird niemals mitgeprüft.
{TRENNLINIE}
=== S. III | PDF 3 ===
Fugenlehre für Prüfstände. Ein erfundenes Lehrbuch für Tests
=== S. 12 | PDF 14 ===
Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen, danach trocknet sie
sieben Tage im Schatten. Ein zweiter Absatz erklärt, warum der Prüfstand niemals am Dienstag
gegossen werden darf, weil die Kelle dann ermüdet. Zum Schluss steht ein langer Satz, der über
die Grenze hinaus läuft und auf der
=== S. 13 | PDF 15 ===
nächsten Seite mit einem Hinweis endet. Holzwurm-
dämmungsplatten sind laut erfundener Lehre stets dreifach zu verschrauben, sonst wackelt die Kiste.
Nach § 99 Testgesetz gilt: Der Prüfer hat die Fuge vor der Abnahme gründlich mit einem Pinsel
aus Dachshaar zu reinigen. Die Norm nennt dazu den Titel Prüfstände aus Holz – Teil 7: Fugen,
Kisten und andere wackelige Dinge im Testbetrieb. Am Ende der Seite steht ein getrenntes Kalk-
=== S. 14 | PDF 16 ===
mörtelbett, das nur in erfundenen Büchern aus geriebenem Bernstein gemischt wird.
"""

# Ein Satz, der in drei Werken steht (wie ein Gesetzeswortlaut, den mehrere Bücher abdrucken)
VIELFACH = "Die Kiste ist nach dem Gießen sieben Tage lang feucht zu halten und vor Zugluft zu schützen."

GESETZ = f"""Werk: Testgesetz (TestG)
Hinweis: Erfundener amtlicher Text für Tests
{TRENNLINIE}
§ 99 Reinigung
Der Prüfer hat die Fuge vor der Abnahme gründlich mit einem Pinsel aus Dachshaar zu reinigen.
"""

KATALOG = """- kennung: muster-fugenlehre-2020
  zitat: 'Mustermann, Max: Fugenlehre für Prüfstände. Ein erfundenes Lehrbuch für Tests. Teststadt: Probeverlag, 2020'
  titel: Fugenlehre für Prüfstände
  untertitel: Ein erfundenes Lehrbuch für Tests
- kennung: kiste-alt-2018
  zitat: 'Kistner, Kai: Kistenbau. Teststadt, 2018'
  ersetzt_durch: kiste-neu-2022
- kennung: kiste-neu-2022
  zitat: 'Kistner, Kai: Kistenbau. 2. Aufl. Teststadt, 2022'
- kennung: wackel-2021
  zitat: 'Wackler, Wanda: Wackelkunde. Teststadt, 2021'
"""


def schreiben(pfad: Path, text: str) -> Path:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8", newline="\n")
    return pfad


def einfaches_werk(kennung: str, text: str) -> str:
    return f"Werk: {kennung}\n{TRENNLINIE}\n=== S. 5 | PDF 7 ===\nVorher etwas anderes. {text} Danach etwas anderes.\n"


class Grundlage(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.ordner.name)
        self.bib = self.wurzel / "bibliothek"
        schreiben(self.bib / "katalog.yml", KATALOG)
        schreiben(self.bib / "texte" / "muster-fugenlehre-2020.txt", BUCH)
        schreiben(self.bib / "texte" / "kiste-alt-2018.txt", einfaches_werk("kiste-alt-2018", VIELFACH))
        schreiben(self.bib / "texte" / "kiste-neu-2022.txt", einfaches_werk("kiste-neu-2022", VIELFACH))
        schreiben(self.bib / "forschung" / "katalog.yml", "- kennung: fo-wackel-2021\n  zitat: 'Wackler: Studie'\n")
        schreiben(self.bib / "forschung" / "texte" / "fo-wackel-2021.txt", einfaches_werk("fo-wackel-2021", VIELFACH))
        schreiben(self.bib / "texte" / "wackel-2021.txt", einfaches_werk("wackel-2021", VIELFACH))
        schreiben(self.bib / "gemeinfrei" / "katalog.yml", "- kennung: testg\n  titel: Testgesetz\n")
        schreiben(self.bib / "gemeinfrei" / "texte" / "testg.txt", GESETZ)
        # quellen/ enthält eigene Beitragssätze und wird nie durchsucht
        schreiben(self.bib / "quellen" / "texte" / "wq-eigen.txt",
                  einfaches_werk("wq-eigen", "Unser eigener Satz über die runde Prüfkiste aus Ahornholz im Garten."))
        self.erlaubt = schreiben(self.wurzel / "erlaubt.txt", "# leer\n")
        self.patch = mock.patch.object(w, "ERLAUBT", self.erlaubt)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.ordner.cleanup()

    def entwurf(self, name: str, rumpf: str, kopf: str = "") -> Path:
        text = f"---\ntitel: \"Test\"\n{kopf}status: Entwurf\n---\n\n# Test\n\n{rumpf}"
        return schreiben(self.wurzel / "entwuerfe" / name, text)

    def starten(self, *argumente: str, bibliothek: Path | None = None) -> tuple[int, str, str, dict]:
        bericht = self.wurzel / "aus" / "bericht.md"
        daten = self.wurzel / "aus" / "bericht.json"
        bib = ["--bibliothek", str(bibliothek or self.bib)] if bibliothek is not False else []
        ausgabe = io.StringIO()
        with mock.patch.object(sys, "argv", ["wortgleich_pruefen.py", *argumente, *bib,
                                             "--bericht", str(bericht), "--json", str(daten)]), \
                redirect_stdout(ausgabe):
            code = w.main()
        return (code, ausgabe.getvalue(), bericht.read_text(encoding="utf-8"),
                json.loads(daten.read_text(encoding="utf-8")))


class Treffer(Grundlage):
    def test_achtwortkopie_mit_kennung_und_seite(self):
        datei = self.entwurf("kopie.md", "## Erster Abschnitt\n\nEinleitung in eigenen Worten.\n\n"
                                         f"## Zweiter Abschnitt\n\nWir wissen: die {KUNSTWORT} wird bei Frost "
                                         "zuerst mit Lindenhonig bestrichen, so die Lehre.\n")
        code, ausgabe, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=1")
        treffer = daten["treffer"][0]
        self.assertEqual((treffer["werk"], treffer["seite"]), ("muster-fugenlehre-2020", "12"))
        self.assertEqual(treffer["zeile"], 14)
        self.assertEqual(treffer["abschnitt"], "Zweiter Abschnitt")
        self.assertEqual(treffer["laenge"], 9)   # die … bestrichen
        self.assertEqual(treffer["werke"], 1)

    def test_ueber_seitengrenze(self):
        datei = self.entwurf("grenze.md", "Ein langer Satz, der über die Grenze hinaus läuft und auf der "
                                          "nächsten Seite mit einem Hinweis endet.\n")
        code, _, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual(daten["treffer"][0]["werk"], "muster-fugenlehre-2020")
        self.assertEqual(daten["treffer"][0]["seite"], "12–13")

    def test_silbentrennung_im_buch_und_an_der_seitengrenze(self):
        datei = self.entwurf("trennung.md", "Holzwurmdämmungsplatten sind laut erfundener Lehre stets dreifach "
                                            "zu verschrauben.\n\nAm Ende der Seite steht ein getrenntes "
                                            "Kalkmörtelbett, das nur in erfundenen Büchern vorkommt.\n")
        code, _, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual([t["seite"] for t in daten["treffer"]], ["13", "13–14"])

    def test_schreibweise_spielt_keine_rolle(self):
        # Großschreibung, Umlaut ausgeschrieben, weiches Trennzeichen, Fettdruck, Fußnotenmarke
        datei = self.entwurf("schreibweise.md",
                             "**ZWEITER ABSATZ** erklaert, warum der Pruef\N{SOFT HYPHEN}stand niemals "
                             "am Dienstag[^1] gegossen werden darf.\n")
        code, _, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual(daten["treffer"][0]["seite"], "12")

    def test_umschreibung_kein_treffer(self):
        datei = self.entwurf("eigen.md", "Bei Frost bestreicht man die Fuge zuerst mit Honig von der Linde; "
                                         "danach muss sie eine Woche lang im Schatten trocknen.\n")
        code, ausgabe, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=0")
        self.assertIn("Keine wörtlichen Übernahmen gefunden.", bericht)
        self.assertEqual(daten["treffer"], [])

    def test_kopfzeilen_der_bibliothek_zaehlen_nicht(self):
        datei = self.entwurf("kopf.md", "Diese Kopfzeile ist nur für die interne Prüfung bestimmt und wird "
                                        "niemals mitgeprüft.\n")
        code, _, _, _ = self.starten(str(datei))
        self.assertEqual(code, 0)

    def test_veroeffentlichte_felder_des_dateikopfs_werden_geprueft(self):
        # titel, meta_beschreibung, definition, kernfrage und schlagwoerter erscheinen auf der
        # Website (Seitentitel, Meta-Description, JSON-LD); andere Felder nicht.
        kopf = (f"kernfrage: Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen?\n"
                "meta_beschreibung: \"Ein zweiter Absatz erklärt, warum der Prüfstand niemals am Dienstag "
                "gegossen werden darf.\"\n"
                "fundstelle: Holzwurmdämmungsplatten sind laut erfundener Lehre stets dreifach zu verschrauben\n"
                "definition: >-\n"
                "  Eigene Worte vorweg: Holzwurmdämmungsplatten sind laut erfundener Lehre\n"
                "  stets dreifach zu verschrauben, sagt das Buch.\n"
                "schlagwoerter: Die Kiste ist nach dem Gießen, sieben Tage lang feucht, zu halten und vor Zugluft\n")
        datei = self.entwurf("kopf2.md", "Eigener Text ohne jede Übernahme.\n", kopf=kopf)
        code, ausgabe, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        # Zeile 1 „---“, 2 titel, 3 kernfrage, 4 meta_beschreibung, 5 fundstelle, 6 definition, 7–8 Blocktext
        self.assertEqual([(t["zeile"], t["abschnitt"]) for t in daten["treffer"]],
                         [(3, "(Dateikopf: kernfrage)"), (4, "(Dateikopf: meta_beschreibung)"),
                          (7, "(Dateikopf: definition)")])
        self.assertNotIn("lindenhonig", ausgabe.casefold())

    def test_kopf_mit_bom_und_crlf(self):
        datei = self.wurzel / "entwuerfe" / "bom.md"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_bytes(("﻿---\r\ntitel: Test\r\nautor: Die " + KUNSTWORT + " wird bei Frost zuerst mit "
                           "Lindenhonig bestrichen\r\n---\r\n\r\nEigener Text.\r\n").encode("utf-8"))
        self.assertEqual(self.starten(str(datei))[0], 0)

    def test_ziffern_und_zitierkuerzel_zaehlen_nicht_als_woerter(self):
        kette = ("gemäß § 2 Abs. 5 oder Abs. 6 VOB/B sowie § 4 Abs. 7 Satz 1 VOB/B und § 13 Abs. 5 Nr. 1 VOB/B, "
                 "DIN 276:2018-12, DIN 276-1:2008-12 und DIN 276-4:2009-08")
        schreiben(self.bib / "texte" / "kette-2020.txt", einfaches_werk("kette-2020", kette + "."))
        datei = self.entwurf("kette.md", f"Die Ansprüche ergeben sich {kette}.\n")
        self.assertEqual(self.starten(str(datei))[0], 0)
        # Ein Satz mit Zahlen bleibt ein Treffer: Gezählt werden nur seine Wörter.
        satz = "Bei 5 °C und 80 % Luftfeuchte trocknet die Kiste erst nach 14 Tagen vollständig im Schatten aus"
        schreiben(self.bib / "texte" / "zahl-2020.txt", einfaches_werk("zahl-2020", satz + "."))
        datei = self.entwurf("zahl.md", satz.replace("14", "vierzehn") + ".\n")
        code, _, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual(daten["treffer"][0]["werk"], "zahl-2020")

    def test_seitenzahl_und_fusszeile_an_der_seitengrenze(self):
        fuss = "Fugenkunde für Fortgeschrittene · Testverlag"
        werk = (f"Werk: rand-2019\n{TRENNLINIE}\n"
                f"=== S. 84 | PDF 90 ===\n84\nKapitel 3 | Fugen und Kisten\nErster Text dieser Seite.\n"
                f"Der lange Satz über die besonders ausgefallene Fugenmasse läuft über die\n{fuss}\n"
                f"=== S. 85 | PDF 91 ===\n85\nKapitel 3 | Fugen und Kisten\n"
                f"Seitengrenze hinweg und endet erst auf der folgenden Seite.\n{fuss}\n"
                f"=== S. 86 | PDF 92 ===\n86\nKapitel 3 | Fugen und Kisten\nNoch eine Seite.\n{fuss}\n")
        schreiben(self.bib / "texte" / "rand-2019.txt", werk)
        datei = self.entwurf("rand.md", "Er schreibt, der lange Satz über die besonders ausgefallene Fugenmasse "
                                        "läuft über die Seitengrenze hinweg.\n")
        code, _, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual((daten["treffer"][0]["werk"], daten["treffer"][0]["seite"]), ("rand-2019", "84–85"))

    def test_absatzgrenzen_bilden_keine_wortfolge(self):
        # Ende eines Listenpunkts + Anfang des nächsten ergäben eine Folge aus dem Buch
        datei = self.entwurf("liste.md", f"- Erstens: die {KUNSTWORT} wird bei Frost\n"
                                         "- zuerst mit Lindenhonig bestrichen, sagt die Liste.\n")
        self.assertEqual(self.starten(str(datei))[0], 0)

    def test_quellen_ordner_wird_nicht_durchsucht(self):
        datei = self.entwurf("eigen2.md", "Unser eigener Satz über die runde Prüfkiste aus Ahornholz im Garten.\n")
        self.assertEqual(self.starten(str(datei))[0], 0)

    def test_viele_werke_vermerk_und_auflagen_zaehlen_einmal(self):
        datei = self.entwurf("vielfach.md", f"Merke: {VIELFACH}\n")
        code, ausgabe, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        treffer = daten["treffer"][0]
        # vier Dateien, aber zwei Auflagen desselben Buches: drei Werke
        self.assertEqual(treffer["werke"], 3)
        self.assertIn("kommt in 3 Werken vor – vermutlich Gesetzes-, VOB- oder Normwortlaut", treffer["vermerk"])
        # gemeldet wird die neueste Auflage, nicht die ersetzte
        self.assertNotEqual(treffer["werk"], "kiste-alt-2018")
        # Öffentlich nur der neutrale Vermerk – die Zahl der Werke verriete die Art der Quelle.
        for text in (ausgabe, bericht):
            self.assertNotIn("Werken vor", text)
            self.assertNotIn("Normwortlaut", text)
        _, ausgabe, bericht, _ = self.starten(str(datei), "--intern")
        self.assertIn("kommt in 3 Werken vor", ausgabe)
        self.assertIn("Freigabe nur durch den Inhaber", bericht)

    def test_bilder_sind_treffer_tabellen_nur_hinweis(self):
        datei = self.entwurf("bild.md", "## Abbildungen\n\n![Skizze](bild.png)\n\n<figure>x</figure>\n\n"
                                        "| Spalte | Wert |\n|---|---|\n| a | 1 |\n")
        code, ausgabe, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual([t["art"] for t in daten["treffer"]], ["Abbildung", "Abbildung"])
        self.assertEqual([t["zeile"] for t in daten["treffer"]], [10, 12])
        self.assertEqual(len(daten["hinweise"]), 1)
        self.assertEqual((daten["hinweise"][0]["zeile"], daten["hinweise"][0]["zeilen"]), (14, 3))
        self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=2")

    def test_nur_tabelle_sperrt_nicht(self):
        datei = self.entwurf("tabelle.md", "| Spalte | Wert |\n|---|---|\n| a | 1 |\n")
        code, _, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 0)
        self.assertIn("Hinweise (keine Sperre)", bericht)
        self.assertEqual(daten["anzahl_hinweise"], 1)


class Freigaben(Grundlage):
    def test_amtlicher_wortlaut_wird_freigegeben(self):
        # Der Buchsatz leitet mit eigenen Worten ein („Nach § 99 Testgesetz gilt:“); übernommen
        # wird hier nur der amtliche Wortlaut selbst.
        datei = self.entwurf("gesetz.md", "Das Testgesetz bestimmt in § 99 wörtlich: Der Prüfer hat die Fuge vor "
                                          "der Abnahme gründlich mit einem Pinsel aus Dachshaar zu reinigen.[^1]\n")
        code, _, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 0, daten["treffer"])
        self.assertIn("1 amtliche Texte", bericht)

    def test_katalogtitel_in_fussnote_wird_freigegeben(self):
        rumpf = ("Text.[^1]\n\n## Quellen und Fußnoten\n\n[^1]: Mustermann, Max: Fugenlehre für Prüfstände. "
                 "Ein erfundenes Lehrbuch für Tests. Teststadt: Probeverlag, 2020, S. 12.\n")
        datei = self.entwurf("fussnote.md", rumpf)
        self.assertEqual(self.starten(str(datei))[0], 0)
        # Gegenprobe: ohne Katalogangaben wäre die Titelzeile von S. III ein Treffer
        schreiben(self.bib / "katalog.yml", "- kennung: muster-fugenlehre-2020\n")
        code, _, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual((daten["treffer"][0]["seite"], daten["treffer"][0]["abschnitt"]),
                         ("III", "Quellen und Fußnoten"))

    def test_normtitel_hinter_nummer_und_ausgabe_wird_ausgeblendet(self):
        titel = "Prüfstände aus Holz – Teil 7: Fugen, Kisten und andere wackelige Dinge im Testbetrieb"
        datei = self.entwurf("norm.md", f"[^1]: DIN Media: DIN 99999-7:2024-05 „{titel}“. Status aktuell.\n")
        self.assertEqual(self.starten(str(datei))[0], 0)
        ohne_ausgabe = self.entwurf("norm2.md", f"Die Norm heißt „{titel}“.\n")
        self.assertEqual(self.starten(str(ohne_ausgabe))[0], 1)

    def test_normtitel_in_fussnote_ohne_anfuehrungszeichen(self):
        titel = "Prüfstände aus Holz – Teil 7: Fugen, Kisten und andere wackelige Dinge im Testbetrieb"
        for trenner in (",", ":", " –"):
            with self.subTest(trenner=trenner):
                datei = self.entwurf("norm3.md", f"Text.[^1]\n\n[^1]: DIN Media: DIN 99999-7:2024-05{trenner} {titel}. "
                                                 "https://example.org/norm (abgerufen am 2026-10-01).\n")
                self.assertEqual(self.starten(str(datei))[0], 0)
        # Nur in Fußnoten und nur bis zum Satzende: Im Fließtext und nach dem Punkt wird geprüft.
        fliesstext = self.entwurf("norm4.md", f"Sie gilt als DIN 99999-7:2024-05, {titel}.\n")
        self.assertEqual(self.starten(str(fliesstext))[0], 1)
        danach = self.entwurf("norm5.md", f"[^1]: DIN 99999-7:2024-05, Kurztitel. Die {KUNSTWORT} wird bei Frost "
                                          "zuerst mit Lindenhonig bestrichen.\n")
        self.assertEqual(self.starten(str(danach))[0], 1)

    def test_satz_aus_der_norm_in_anfuehrungszeichen_bleibt_treffer(self):
        satz = "Holzwurmdämmungsplatten sind laut erfundener Lehre stets dreifach zu verschrauben, sonst wackelt die Kiste"
        for rumpf in (f"Nach DIN 99999-7:2024-05 „{satz}“.\n",
                      f"[^1]: DIN 99999-7:2024-05, „{satz}.“\n",
                      f"Siehe VDI 9999 Blatt 1:2013-10 „{satz}“.\n"):
            with self.subTest(rumpf=rumpf[:30]):
                code, _, _, daten = self.starten(str(self.entwurf("normsatz.md", rumpf)))
                self.assertEqual(code, 1)
                self.assertEqual(daten["treffer"][0]["werk"], "muster-fugenlehre-2020")

    def test_titel_plausibel(self):
        self.assertTrue(w.titel_plausibel("„Toleranzen im Hochbau – Bauwerke“"))
        self.assertFalse(w.titel_plausibel("„Die Fuge muss trocken sein“"))
        self.assertFalse(w.titel_plausibel("„Zwei Wörter. Und noch ein Satz“"))
        self.assertFalse(w.titel_plausibel("„" + " ".join(["Wort"] * (w.TITEL_HOECHSTENS + 1)) + "“"))

    def test_amtlicher_wortlaut_mit_randwoertern(self):
        # „Testgesetz gilt:“ steht nur im Buch; zwei ungedeckte Randwörter am amtlichen Wortlaut sind frei.
        datei = self.entwurf("rand.md", "Testgesetz gilt: Der Prüfer hat die Fuge vor der Abnahme gründlich mit "
                                        "einem Pinsel aus Dachshaar zu reinigen.\n")
        self.assertEqual(self.starten(str(datei))[0], 0)
        # Drei Wörter aus dem Buch davor sind kein Randwort mehr.
        datei = self.entwurf("rand2.md", "Nach § 99 Testgesetz gilt: Der Prüfer hat die Fuge vor der Abnahme "
                                         "gründlich mit einem Pinsel aus Dachshaar zu reinigen.\n")
        self.assertEqual(self.starten(str(datei))[0], 1)

    def test_wendungsliste_des_inhabers(self):
        satz = "Ein zweiter Absatz erklärt, warum der Prüfstand niemals am Dienstag gegossen werden darf."
        datei = self.entwurf("wendung.md", satz + "\n")
        self.assertEqual(self.starten(str(datei))[0], 1)
        schreiben(self.erlaubt, "# vom Inhaber freigegeben\n" + satz + "\n")
        self.assertEqual(self.starten(str(datei))[0], 0)

    def test_hinweis_baustein_steht_in_der_echten_wendungsliste(self):
        wendungen = w.erlaubte_wendungen(Path(w.__file__).resolve().parent / "wortgleich_erlaubt.txt")
        self.assertTrue(any(z.startswith("Dieser Beitrag gibt den fachlichen Kenntnisstand") for z in wendungen))


class Ausgabe(Grundlage):
    def test_kein_bibliothekstext_in_ausgabe_bericht_und_json(self):
        datei = self.entwurf("kopie.md", "## Eigener Abschnitt\n\n"
                                         f"Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen, "
                                         "danach trocknet sie sieben Tage im Schatten.\n\n"
                                         "![Bild](x.png)\n\n| a | b |\n")
        code, ausgabe, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        alles = (ausgabe + bericht + json.dumps(daten, ensure_ascii=False)).casefold()
        for wort in (KUNSTWORT, "quarzblaeulingsfuge", "Lindenhonig", "lindenhonig bestrichen",
                     "bei Frost zuerst", "trocknet sie"):
            self.assertNotIn(wort.casefold(), alles)
        self.assertIn("## Wörtliche Übernahmen aus der Fachbibliothek", bericht)
        self.assertIn("| Datei | Abschnitt | Zeile | Länge (Wörter) | Vermerk |", bericht)
        self.assertNotIn("| Werk |", bericht)
        self.assertRegex(bericht, r"Geprüft gegen: 5 Werke, 1 amtliche Texte, Grenze 8 Wörter")
        _, _, bericht, _ = self.starten(str(datei), "--intern")
        self.assertIn("| Datei | Abschnitt | Zeile | Länge (Wörter) | Werk | Seite | Vermerk |", bericht)

    def test_treffer_in_zwischenueberschrift_ohne_wortlaut(self):
        datei = self.entwurf("h2.md", f"## Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen\n\n"
                                      "Eigener Text ohne Übernahme.\n\n![Bild](x.png)\n\n## Danach\n\nMehr Text.\n")
        code, ausgabe, bericht, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        self.assertEqual([t["abschnitt"] for t in daten["treffer"]],
                         ["(Abschnitt ab Zeile 8 – Überschrift selbst betroffen)"] * 2)
        alles = (ausgabe + bericht + json.dumps(daten, ensure_ascii=False)).casefold()
        self.assertNotIn("lindenhonig", alles)
        self.assertNotIn("quarzbl", alles)

    def test_ohne_bibliothek_exit_2(self):
        datei = self.entwurf("x.md", "Text.\n")
        for bib in (self.wurzel / "fehlt", False):
            code, ausgabe, bericht, daten = self.starten(str(datei), bibliothek=bib)
            self.assertEqual(code, 2)
            self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=nicht-geprueft")
            self.assertIn("Nicht geprüft: Fachbibliothek nicht geladen – Entwurf bleibt gesperrt.", bericht)
            self.assertFalse(daten["geprueft"])

    def test_leere_bibliothek_exit_2(self):
        leer = self.wurzel / "leer"
        schreiben(leer / "katalog.yml", "[]\n")
        code, ausgabe, _, _ = self.starten(str(self.entwurf("x.md", "Text.\n")), bibliothek=leer)
        self.assertEqual(code, 2)
        self.assertTrue(ausgabe.strip().endswith("treffer=nicht-geprueft"))

    def test_fehlender_entwurf_exit_2(self):
        code, ausgabe, _, _ = self.starten(str(self.wurzel / "gibt-es-nicht.md"))
        self.assertEqual(code, 2)
        self.assertTrue(ausgabe.strip().endswith("treffer=nicht-geprueft"))

    def test_mehrere_entwuerfe_bibliothek_nur_einmal_gelesen(self):
        a = self.entwurf("a.md", f"Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen.\n")
        b = self.entwurf("b.md", "Ganz eigene Worte ohne jede Übernahme aus irgendeinem Buch.\n")
        c = self.entwurf("c.md", f"Merke: {VIELFACH}\n")
        gelesen = []
        echt = w.seiten

        def zaehlen(inhalt):
            gelesen.append(inhalt[:30])
            return echt(inhalt)

        with mock.patch.object(w, "seiten", zaehlen):
            code, ausgabe, _, daten = self.starten(str(a), str(b), str(c))
        self.assertEqual(code, 1)
        # 5 Werktexte + 1 amtlicher Text, je einmal – unabhängig von der Zahl der Entwürfe
        self.assertEqual(len(gelesen), 6)
        self.assertEqual(sorted({t["datei"].rsplit("/", 1)[-1] for t in daten["treffer"]}), ["a.md", "c.md"])
        self.assertIn("b.md: 0 Treffer", ausgabe)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=2")


class OeffentlicheAusgabe(Grundlage):
    """Ausgabe und Bericht landen in PR-Kommentaren, Logs und Zusammenfassungen: Ohne --intern
    nennen sie nie Werk-Kennung, Seite oder Zahl der Werke – das verriete, aus welchem Buch eine
    Stelle stammt. Das JSON (nur Runner-Temp) bleibt vollständig."""

    KENNUNG = "zz-geheimwerk-kennung-4711"
    SATZ = "Der Kistenleim wird nur bei Vollmond mit einer silbernen Kelle auf die Fuge gestrichen"
    SEITE = re.compile(r"S\.\s*987")

    def setUp(self):
        super().setUp()
        schreiben(self.bib / "texte" / f"{self.KENNUNG}.txt",
                  f"Werk: {self.KENNUNG}\n{TRENNLINIE}\n=== S. 987 | PDF 990 ===\nVorher. {self.SATZ}. Danach.\n")
        with (self.bib / "katalog.yml").open("a", encoding="utf-8", newline="\n") as katalog:
            katalog.write(f"- kennung: {self.KENNUNG}\n  zitat: 'Geheim, Gerd: Kistenleimkunde. Teststadt, 2019'\n")

    def kopie(self) -> Path:
        return self.entwurf("geheim.md", f"## Leim\n\nMerke: {self.SATZ}.\n\n![Skizze](leim.png)\n\n| a | b |\n")

    def test_ohne_intern_weder_werk_noch_seite(self):
        code, ausgabe, bericht, daten = self.starten(str(self.kopie()))
        self.assertEqual(code, 1)
        treffer = next(t for t in daten["treffer"] if t["art"] == "Wortfolge")
        self.assertEqual((treffer["werk"], treffer["seite"], treffer["werke"]), (self.KENNUNG, "987", 1))
        for name, text in (("Ausgabe", ausgabe), ("Bericht", bericht)):
            with self.subTest(name=name):
                self.assertNotIn(self.KENNUNG, text)
                self.assertNotIn("geheimwerk", text)
                self.assertNotIn("Kistenleimkunde", text)
                self.assertNotRegex(text, self.SEITE)
                self.assertNotIn("Werken", text)
                self.assertNotIn("Fundstelle angeben", text)
                self.assertIn(w.NEUTRAL, text)
                # Hinweise auf Abbildung und Tabelle bleiben – sie nennen keine Quelle
                self.assertIn("Markdown-Bild im Entwurf", text)
                self.assertIn("Hinweis: Tabelle mit 1 Zeilen", text)
        self.assertIn(f"Zeile {treffer['zeile']} · Leim · {treffer['laenge']} Wörter · {w.NEUTRAL}", ausgabe)
        self.assertIn(f"| Leim | {treffer['zeile']} | {treffer['laenge']} | {w.NEUTRAL} |", bericht)
        self.assertIn(w.SCHLUSS_OEFFENTLICH, bericht)
        self.assertNotIn("mit Werk und Seite belegen", bericht)
        self.assertNotIn(w.INTERN_WARNUNG, ausgabe + bericht)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=2")

    def test_mit_intern_werk_und_seite(self):
        code, ausgabe, bericht, daten = self.starten(str(self.kopie()), "--intern")
        self.assertEqual(code, 1)
        self.assertIn(f"{self.KENNUNG} S. 987", ausgabe)
        self.assertIn(f"| {self.KENNUNG} | 987 |", bericht)
        self.assertIn(w.INTERN_WARNUNG, ausgabe)
        self.assertIn(w.INTERN_WARNUNG, bericht)
        self.assertIn("mit Werk und Seite belegen", bericht)
        self.assertEqual(ausgabe.strip().splitlines()[-1], "treffer=2")
        # Auch intern nie Text aus der Bibliothek
        self.assertNotIn("vollmond", (ausgabe + bericht).casefold())
        self.assertEqual(daten["treffer"][0]["werk"], self.KENNUNG)

    def test_json_gleich_mit_und_ohne_intern(self):
        datei = str(self.kopie())
        _, _, _, ohne = self.starten(datei)
        _, _, _, mit = self.starten(datei, "--intern")
        self.assertEqual(ohne["treffer"], mit["treffer"])
        self.assertEqual(ohne["hinweise"], mit["hinweise"])


class Vorlage(Grundlage):
    """Vorlagen-Beschreibung vorlagen/<kurzform>.yml: ohne Dateikopf, alle Textfelder."""

    YML = (f"titel: Prüfliste für Fugen\n"
           "kurzform: fugen\n"
           "dateien: [pdf, docx]\n"
           "einleitung: >\n"
           "  Mit dieser Liste prüfen Sie Ihre Fugen: Schritt für Schritt\n"
           "  und in eigenen Worten.\n"
           "abschnitte:\n"
           "  - titel: Vor dem Termin\n"
           "    punkte:\n"
           f"      - text: Die {KUNSTWORT} wird bei Frost zuerst mit Lindenhonig bestrichen\n"
           "        hinweis: Ein eigener Hinweis ohne Übernahme.\n"
           f"      - text: Die {KUNSTWORT} wird bei Frost\n"
           "      - text: zuerst mit Lindenhonig bestrichen, sagt die Liste\n"
           "      - text: |\n"
           "          Ein zweiter Absatz erklärt: warum der Prüfstand niemals am Dienstag\n"
           "          gegossen werden darf.\n")

    def test_textfelder_der_vorlage_werden_geprueft(self):
        datei = schreiben(self.wurzel / "vorlagen" / "fugen.yml", self.YML)
        code, ausgabe, _, daten = self.starten(str(datei))
        self.assertEqual(code, 1)
        # Zeile 10: Punkt aus dem Buch; Zeile 15: Blocktext (auch mit Doppelpunkt darin).
        # Zeilen 12/13 sind zwei Punkte – zusammen ergäben sie eine Buchfolge, getrennt nicht.
        self.assertEqual([(t["zeile"], t["abschnitt"]) for t in daten["treffer"]],
                         [(10, "(Vorlage: text)"), (15, "(Vorlage: text)")])
        self.assertNotIn("lindenhonig", ausgabe.casefold())

    def test_vorlage_ohne_uebernahme(self):
        datei = schreiben(self.wurzel / "vorlagen" / "eigen.yml",
                          "titel: Eigene Liste\neinleitung: Nur eigene Worte stehen hier.\n"
                          "abschnitte:\n  - titel: Prüfen\n    punkte:\n      - text: Die Fuge ist trocken\n")
        self.assertEqual(self.starten(str(datei))[0], 0)


class Webquellen(Grundlage):
    """--zusatz: heruntergeladene Quelltexte der Schlussprüfung (Fachaufsätze), amtliche ausgenommen."""

    AUFSATZ = "Der Verband empfiehlt ausdrücklich, jede Kiste nach dem Gießen mit Lindenblüten zu bedecken"
    GESETZ = "Der Unternehmer ist verpflichtet, dem Besteller das Werk frei von Sach- und Rechtsmängeln zu verschaffen"

    def quellen(self) -> Path:
        ordner = self.wurzel / "schlusspruefung" / "quellen"
        linie = "-" * 64
        schreiben(ordner / "q1.txt", f"Quelle Q1 – abgerufen am 2026-10-20\nAdresse: https://www.verband.example/aufsatz\n"
                                     f"Art: html · Status: ok\nHinweis: Prüfmaterial.\n{linie}\n{self.AUFSATZ}.\n")
        schreiben(ordner / "q2.txt", f"Quelle Q2 – abgerufen am 2026-10-20\n"
                                     f"Adresse: https://www.gesetze-im-internet.de/bgb/__633.html\n"
                                     f"Art: html · Status: ok\nHinweis: Prüfmaterial.\n{linie}\n{self.GESETZ}.\n")
        schreiben(ordner / "q3.txt", f"Quelle Q3 – Buch\nHinweis: Text der zitierten Buchseiten aus der "
                                     f"Fachbibliothek.\n{linie}\nUnser eigener Satz über die runde Prüfkiste aus "
                                     "Ahornholz im Garten.\n")
        return ordner

    def test_fachaufsatz_ist_treffer_amtliche_seite_nicht(self):
        ordner = self.quellen()
        datei = self.entwurf("web.md", f"Kurz gesagt: {self.AUFSATZ}.\n\nDas Gesetz sagt: {self.GESETZ}.\n\n"
                                       "Unser eigener Satz über die runde Prüfkiste aus Ahornholz im Garten.\n")
        code, ausgabe, bericht, daten = self.starten(str(datei), "--zusatz", str(ordner))
        self.assertEqual(code, 1)
        self.assertEqual([(t["zeile"], t["werk"]) for t in daten["treffer"]],
                         [(8, "Webquelle Q1 (www.verband.example)")])
        self.assertEqual(daten["webquellen"], 3)
        self.assertIn("3 heruntergeladene Quelltexte", bericht)
        self.assertNotIn("lindenbl", (ausgabe + bericht).casefold())
        # Öffentlich weder Name noch Adresse der Webquelle – nur mit --intern
        for teil in ("Webquelle", "Q1", "verband.example"):
            self.assertNotIn(teil, ausgabe + bericht)
        _, ausgabe, bericht, _ = self.starten(str(datei), "--zusatz", str(ordner), "--intern")
        self.assertIn("Webquelle Q1 (www.verband.example)", ausgabe)
        self.assertIn("Webquelle Q1 (www.verband.example)", bericht)
        # Ohne --zusatz wie bisher nur die Bibliothek
        self.assertEqual(self.starten(str(datei))[0], 0)


if __name__ == "__main__":
    unittest.main()
