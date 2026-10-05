"""Wortregeln des Inhabers auf den von Hand gepflegten Seiten und in den LinkedIn-Entwürfen.

Die Fachbeiträge prüfen die Skills der Agenten; diese Prüfung deckt den Rest ab:
Startseite, Leistungs- und Zielgruppenseiten, Wertrechner, englische Seiten und
die LinkedIn-Entwürfe in marketing/linkedin/. Verboten sind Selbstzuschreibungen
(„unabhängig“, „neutral“, Titel), Erfahrungsaussagen ohne Beleg („gehören zu
unserem Alltag“ – es gibt noch keine Referenzen) und Ergebnisversprechen („hält
vor Gericht“). Erlaubt bleiben Fachbegriffe wie „independent evidence proceedings“
(selbständiges Beweisverfahren) und „unabhängig davon, ob …“.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import re
import unittest
from html import unescape
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent

DEUTSCH = [
    # „unabhängig davon, ob …“ und „voneinander unabhängig“ sind keine Selbstzuschreibung.
    (re.compile(r"(?<!voneinander )\b[Uu]nabhängig(?:e|en|er|es)?\b(?!\s+davon)"), "Selbstzuschreibung „unabhängig“"),
    (re.compile(r"(?<![-\w])[Nn]eutral(?:e|en|er|es)?\b"), "Selbstzuschreibung „neutral“"),
    (re.compile(r"gehören zu unserem Alltag|[Uu]nser Alltag"), "Erfahrungsaussage ohne Beleg"),
    (re.compile(r"vor Gericht Bestand|standhält|hält vor Gericht|halten den Termin|rechtssicher"),
     "Ergebnisversprechen"),
    (re.compile(r"Beratende[rn]? Ingenieur|[Pp]rüfsachverständige|[Pp]rüfingenieur"), "Titel ohne Grundlage"),
    (re.compile(r"\berfahrene[nr]?\b"), "Erfahrungsaussage ohne Beleg"),
]
ENGLISCH = [
    (re.compile(r"\b[Ii]ndependent\b(?!\s+evidence)"), "self-description „independent“"),
    (re.compile(r"day-to-day|used to being|stand up to|same diligence|same rigour|hold up in court"),
     "experience claim or promise"),
]


def sichtbarer_text(roh: str) -> str:
    """Text, den Besucher und Suchmaschinen lesen: ohne Skripte (außer JSON-LD),
    Stile, Kommentare und die Datenschutzerklärung (dort beschreibt
    „zertifiziert“ Dritte, nicht das Büro)."""
    roh = re.sub(r'<details id="datenschutz".*?</details>', " ", roh, flags=re.S)
    roh = re.sub(r'<script(?![^>]*application/ld\+json)[^>]*>.*?</script>', " ", roh, flags=re.S)
    roh = re.sub(r"<style.*?</style>", " ", roh, flags=re.S)
    roh = re.sub(r"<!--.*?-->", " ", roh, flags=re.S)
    roh = re.sub(r'content="([^"]*)"', r" \1 ", roh)           # Meta- und OG-Beschreibungen
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", roh)))


def seiten() -> list[Path]:
    liste = [WURZEL / "index.html", WURZEL / "wertrechner" / "index.html", WURZEL / "en" / "index.html"]
    liste += sorted((WURZEL / "leistungen").rglob("index.html"))
    liste += sorted(p for p in (WURZEL / "en").glob("*/index.html") if p.parent.name != "guides")
    liste += sorted((WURZEL / "werkzeuge").rglob("index.html"))
    return [p for p in liste if p.is_file()]


def entwuerfe() -> list[Path]:
    return sorted((WURZEL / "marketing" / "linkedin").glob("0*.md"))


def verstoesse(text: str, regeln) -> list[str]:
    funde = []
    for muster, grund in regeln:
        for treffer in muster.finditer(text):
            stelle = text[max(0, treffer.start() - 50):treffer.end() + 30]
            funde.append(f"{grund}: …{stelle}…")
    return funde


class Wortregeln(unittest.TestCase):
    def test_seiten(self):
        fehler = []
        for seite in seiten():
            roh = seite.read_text(encoding="utf-8")
            englisch = re.search(r'<html\s+lang="en"', roh) is not None
            for fund in verstoesse(sichtbarer_text(roh), ENGLISCH if englisch else DEUTSCH):
                fehler.append(f"{seite.relative_to(WURZEL).as_posix()}: {fund}")
        self.assertEqual(fehler, [])

    def test_linkedin_entwuerfe(self):
        fehler = []
        for datei in entwuerfe():
            text = datei.read_text(encoding="utf-8")
            beitrag = text.split("## Beitragstext", 1)[-1].split("## Belege", 1)[0]
            for fund in verstoesse(beitrag, DEUTSCH):
                fehler.append(f"{datei.name}: {fund}")
            if "!" in beitrag:
                fehler.append(f"{datei.name}: Ausrufezeichen im Beitragstext")
        self.assertEqual(fehler, [])

    def test_keine_internen_listen_im_repository(self):
        # Die Verzeichnisliste enthält interne Einschätzungen und gehört nicht in das
        # öffentliche Repository (es wird zugleich als Website ausgeliefert).
        self.assertFalse((WURZEL / "marketing" / "verzeichnisse.md").exists())


if __name__ == "__main__":
    unittest.main()
