#!/usr/bin/env python3
"""Baut aus den Markdown-Entwürfen in entwuerfe/ statische Artikelseiten.

Erzeugt wird ausschließlich in fachwissen/ und in sitemap.xml:

    fachwissen/index.html              Übersicht aller veröffentlichten Beiträge
    fachwissen/<kurzform>/index.html   eine Seite je Entwurf
    sitemap.xml                        Startseite, Übersicht, veröffentlichte Beiträge

Der ganze Artikeltext steht im ausgelieferten HTML. KI-Crawler führen kein
JavaScript aus; alles, was erst im Browser entsteht, ist für sie nicht vorhanden.
Die Artikelseiten kommen deshalb ohne JavaScript aus.

Nur `status: Veröffentlicht` im Frontmatter macht eine Seite indexierbar und
nimmt sie in Übersicht und Sitemap auf. Jeder andere Status erzeugt die Seite
ebenfalls – zum Ansehen im Pull Request – aber mit noindex, mit einem sichtbaren
Warnhinweis und ohne Eintrag in Übersicht und Sitemap.

Aufruf:  python tools/artikel_generator.py [--pruefen]
         --pruefen schreibt nichts und meldet per Exit-Code 1, ob sich etwas
         ändern würde.
"""

from __future__ import annotations

import argparse
import html
import math
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Fehlt: PyYAML. Installieren mit: python -m pip install PyYAML")

try:
    import markdown
except ImportError:  # pragma: no cover
    sys.exit("Fehlt: markdown. Installieren mit: python -m pip install markdown")

WURZEL = Path(__file__).resolve().parent.parent
ENTWUERFE = WURZEL / "entwuerfe"
ZIEL = WURZEL / "fachwissen"
SITEMAP = WURZEL / "sitemap.xml"

BASIS_URL = "https://ing-bassam.de"
FIRMA = "Bassam Ingenieurbüro für Bauwesen GmbH"
KURZNAME = "BIB Ingenieurbüro für Bauwesen"
AUTOR_VORGABE = "Abdel Karim Abu Elkheir"
TELEFON = "+49 176 23581339"
EMAIL = "info@ing-bassam.de"

# Nur dieser Status erscheint öffentlich.
STATUS_OEFFENTLICH = "veröffentlicht"

# Fachbeitrag, Rechtsprechung und Grundlagen richten sich an ein fachliches
# Publikum; schema.org kennt dafür TechArticle.
FACHLICHE_FORMATE = {"fachbeitrag", "rechtsprechung", "grundlagen", "urteilsbesprechung"}


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def kurzform_aus_dateiname(pfad: Path) -> str:
    """`2026-09-19-technische-beweissicherung.md` -> `technische-beweissicherung`."""
    name = pfad.stem
    treffer = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", name)
    return treffer.group(1) if treffer else name


def slug(text: str) -> str:
    text = text.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(alt, neu)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(z for z in text if not unicodedata.combining(z))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def als_text(wert) -> str:
    if wert is None:
        return ""
    if isinstance(wert, (date, datetime)):
        return wert.strftime("%Y-%m-%d")
    return str(wert).strip()


def als_liste(wert) -> list[str]:
    """Nimmt „a, b" genauso wie eine YAML-Liste."""
    if wert is None:
        return []
    if isinstance(wert, list):
        return [als_text(e) for e in wert if als_text(e)]
    return [t.strip() for t in als_text(wert).split(",") if t.strip()]


def ist_platzhalter(wert: str) -> bool:
    """Unausgefüllte Frontmatter-Felder der Skill-Vorlage erkennen."""
    return wert.startswith("<") and wert.endswith(">")


def datum_oder_none(wert: str) -> str | None:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", wert):
        return wert
    return None


def frontmatter_lesen(pfad: Path) -> tuple[dict, str]:
    roh = pfad.read_text(encoding="utf-8")
    treffer = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", roh, re.S)
    if not treffer:
        raise ValueError(f"{pfad.name}: kein YAML-Frontmatter gefunden")
    try:
        kopf = yaml.safe_load(treffer.group(1)) or {}
    except yaml.YAMLError as fehler:
        raise ValueError(f"{pfad.name}: Frontmatter ist kein gültiges YAML – {fehler}")
    if not isinstance(kopf, dict):
        raise ValueError(f"{pfad.name}: Frontmatter ist keine Zuordnung von Feldern")
    return kopf, treffer.group(2)


def erste_h1_entfernen(rumpf: str) -> tuple[str, str]:
    """Die H1 steht im Frontmatter; im Körper würde sie doppelt erscheinen."""
    zeilen = rumpf.splitlines()
    titel = ""
    for i, zeile in enumerate(zeilen):
        if zeile.startswith("# "):
            titel = zeile[2:].strip()
            del zeilen[i]
            break
        if zeile.strip():
            break
    return "\n".join(zeilen).strip("\n"), titel


def haupttext(rumpf: str) -> str:
    """Der Teil, den das Frontmatter-Feld ``wortzahl`` meint.

    Von der H1 bis einschließlich ``## Häufige Fragen`` – ohne Hinweis,
    Autorenkasten und Quellenverzeichnis. Fehlt die FAQ-Überschrift, wird wie
    bisher alles gezählt; lieber zu viel als eine still halbierte Zahl.
    """
    marke = re.search(r"^##\s*Häufige Fragen\b.*$", rumpf, flags=re.M | re.I)
    if not marke:
        return rumpf
    rest = rumpf[marke.end():]
    ende = re.search(r"^(##\s|---\s*$|\[\^)", rest, flags=re.M)
    return rumpf[: marke.end() + (ende.start() if ende else len(rest))]


def woerter_zaehlen(text: str) -> int:
    ohne_code = re.sub(r"```.*?```", " ", text, flags=re.S)
    return len([w for w in re.split(r"\s+", ohne_code) if w])


# --------------------------------------------------------------------------
# Markdown -> HTML
# --------------------------------------------------------------------------

def markdown_zu_html(rumpf: str) -> tuple[str, int]:
    """Wandelt den Entwurf um und hebt TODO-Blöcke sichtbar hervor.

    Rückgabe: (HTML, Anzahl der TODO-Marken)
    """
    todos = len(re.findall(r"^\s*>\s*TODO:", rumpf, flags=re.M))

    # Kein nl2br: Im Fließtext sollen einzelne Zeilenumbrüche keine harten
    # Umbrüche erzeugen, sonst zerfällt jeder Absatz optisch in Zeilen.
    umwandler = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={
            "footnotes": {"BACKLINK_TITLE": "Zurück zu Fußnote %d"},
            # Eigene Kennung statt der Standardfunktion: Die wirft Umlaute
            # ersatzlos weg, aus „Lüftungsverhalten" würde „luftungsverhalten".
            # slug() transliteriert sie wie in der Kurzform-Konvention.
            "toc": {"slugify": lambda wert, trenner: slug(wert), "toc_depth": "2-3"},
        },
        output_format="html5",
    )
    inhalt = umwandler.convert(rumpf)

    # TODO-Zitatblöcke als Warnkasten auszeichnen, damit sie beim Durchsehen
    # nicht übersehen werden.
    inhalt = re.sub(
        r"<blockquote>\s*<p>(\s*TODO:)",
        r'<blockquote class="todo"><p><strong>Offen:</strong>\1',
        inhalt,
    )
    # Aufgabenlisten des Formats Checkliste in echte Kästchen wandeln.
    inhalt = inhalt.replace("<li>[ ] ", '<li class="abhaken">')
    inhalt = inhalt.replace("<li>[x] ", '<li class="abhaken erledigt">')
    return inhalt, todos


def faq_aus_html(inhalt: str) -> list[tuple[str, str]]:
    """Liest die FAQ aus dem gerenderten HTML.

    Der Skill schreibt jede Frage als fett gesetzten Absatz, die Antwort als
    folgenden Absatz. Damit braucht das Frontmatter kein eigenes faq-Feld,
    und Markup und sichtbarer Text können nicht auseinanderlaufen.
    """
    teil = re.split(r"<h2[^>]*>\s*Häufige Fragen\s*</h2>", inhalt, maxsplit=1)
    if len(teil) < 2:
        return []
    # Der FAQ-Bereich endet an der nächsten Überschrift oder an der Trennlinie
    # vor dem Autorenkasten. Offene Prüfpunkte dürfen dazwischenstehen.
    rest = re.split(r"<h[1-6]|<hr\b", teil[1], maxsplit=1)[0]
    def blank(roh: str) -> str:
        # Fußnotenmarken zuerst ganz entfernen. Sonst bleibt die nackte Ziffer
        # stehen und eine Antwort endet im Markup auf „… begünstigen kann.4".
        ohne_marken = re.sub(r"<sup\b[^>]*>.*?</sup>", "", roh, flags=re.S)
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", ohne_marken)).strip()

    paare: list[tuple[str, str]] = []
    absaetze = re.findall(r"<p>(.*?)</p>", rest, re.S)
    offene_frage: str | None = None
    for absatz in absaetze:
        # Der Skill erlaubt beide Schreibweisen: Frage und Antwort im selben
        # Absatz (keine Leerzeile dazwischen) oder in zwei Absätzen.
        zusammen = re.match(r"\s*<strong>(.*?)</strong>(.+)$", absatz, re.S)
        nur_fett = re.fullmatch(r"\s*<strong>(.*?)</strong>\s*", absatz, re.S)
        if nur_fett:
            if offene_frage:
                paare.append((offene_frage, ""))
            offene_frage = blank(nur_fett.group(1))
        elif zusammen and blank(zusammen.group(2)):
            if offene_frage:
                paare.append((offene_frage, ""))
                offene_frage = None
            paare.append((blank(zusammen.group(1)), blank(zusammen.group(2))))
        elif offene_frage:
            # Mehrabsätzige Antwort: weitere Absätze anhängen, statt sie zu
            # verwerfen. Die Frage bleibt offen, bis die nächste fett gesetzte
            # Frage beginnt.
            if paare and paare[-1][0] == offene_frage:
                paare[-1] = (offene_frage, (paare[-1][1] + " " + blank(absatz)).strip())
            else:
                paare.append((offene_frage, blank(absatz)))
    # Nur echte Fragen mit Antwort gehören ins FAQPage-Markup. Das Fragezeichen
    # hält Fettzeilen wie „Über den Autor" zuverlässig heraus.
    return [(f, a) for f, a in paare if f.endswith("?") and a]


# --------------------------------------------------------------------------
# Strukturierte Daten
# --------------------------------------------------------------------------

def json_string(wert: str) -> str:
    """Minimaler JSON-String-Escaper – kein Modul nötig, keine Überraschungen."""
    ausgabe = []
    for zeichen in wert:
        if zeichen == '"':
            ausgabe.append('\\"')
        elif zeichen == "\\":
            ausgabe.append("\\\\")
        elif zeichen == "\n":
            ausgabe.append("\\n")
        elif zeichen == "\r":
            continue
        elif zeichen == "\t":
            ausgabe.append("\\t")
        elif ord(zeichen) < 0x20:
            ausgabe.append(f"\\u{ord(zeichen):04x}")
        elif zeichen == "<":
            # Verhindert, dass ein </script> im Text das Skript-Element beendet.
            ausgabe.append("\\u003c")
        else:
            ausgabe.append(zeichen)
    return '"' + "".join(ausgabe) + '"'


def json_wert(wert) -> str:
    if isinstance(wert, dict):
        teile = [f"{json_string(k)}:{json_wert(v)}" for k, v in wert.items() if v not in (None, "", [], {})]
        return "{" + ",".join(teile) + "}"
    if isinstance(wert, list):
        return "[" + ",".join(json_wert(e) for e in wert) + "]"
    if isinstance(wert, bool):
        return "true" if wert else "false"
    if isinstance(wert, (int, float)):
        return str(wert)
    return json_string(als_text(wert))


def strukturierte_daten(artikel: "Artikel") -> str:
    typ = "TechArticle" if artikel.format.lower() in FACHLICHE_FORMATE else "Article"

    # Ein einziger Firmenknoten mit fester Kennung. Vorher stand dieselbe GmbH
    # dreimal im Datensatz: einmal auf der Startseite, einmal als publisher und
    # einmal als Arbeitgeber des Verfassers – zweimal davon ohne Kennung und
    # unter abweichendem Namen.
    firma_id = BASIS_URL + "/#organization"
    firma = {"@type": "Organization", "@id": firma_id, "name": FIRMA,
             "url": BASIS_URL + "/"}
    autor = {
        "@type": "Person",
        "name": artikel.autor,
        "jobTitle": artikel.qualifikation or None,
        "worksFor": {"@id": firma_id},
    }
    # about darf nur behaupten, was sichtbar auf der Seite steht. Deshalb nur,
    # wenn der Definitionssatz wörtlich im gerenderten Text vorkommt.
    definition_sichtbar = bool(
        artikel.definition
        and artikel.definition.strip() in re.sub(r"<[^>]+>", "", artikel.inhalt_html)
    )
    adressat = artikel.adressat or (artikel.zielgruppe[0] if artikel.zielgruppe else "")
    knoten: list[dict] = [
        {
            "@type": typ,
            "@id": artikel.url + "#artikel",
            "headline": artikel.titel,
            "description": artikel.meta_beschreibung,
            "inLanguage": "de-DE",
            "datePublished": artikel.veroeffentlicht,
            "dateModified": artikel.geaendert,
            "author": autor,
            "publisher": {"@id": firma_id},
            "mainEntityOfPage": {"@type": "WebPage", "@id": artikel.url},
            "articleSection": artikel.kategorie or None,
            "keywords": artikel.schlagwoerter or None,
            "abstract": artikel.definition or None,
            "about": ({"@type": "DefinedTerm", "name": artikel.titel,
                       "description": artikel.definition}
                      if definition_sichtbar else None),
            "audience": ({"@type": "Audience", "audienceType": adressat}
                         if adressat else None),
            "isPartOf": {"@type": "CollectionPage", "@id": f"{BASIS_URL}/fachwissen/"},
            "wordCount": artikel.wortzahl or None,
            "isAccessibleForFree": True,
        },
        firma,
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Start", "item": BASIS_URL + "/"},
                {"@type": "ListItem", "position": 2, "name": "Fachwissen", "item": f"{BASIS_URL}/fachwissen/"},
                {"@type": "ListItem", "position": 3, "name": artikel.titel},
            ],
        },
    ]

    if artikel.faq:
        knoten.append(
            {
                "@type": "FAQPage",
                "@id": artikel.url + "#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": frage,
                        "acceptedAnswer": {"@type": "Answer", "text": antwort},
                    }
                    for frage, antwort in artikel.faq
                ],
            }
        )

    return json_wert({"@context": "https://schema.org", "@graph": knoten})


# --------------------------------------------------------------------------
# Datenmodell
# --------------------------------------------------------------------------

class Artikel:
    def __init__(self, pfad: Path):
        self.pfad = pfad
        kopf, rumpf = frontmatter_lesen(pfad)
        self.kopf = kopf

        self.kurzform = als_text(kopf.get("kurzform")) or kurzform_aus_dateiname(pfad)
        if ist_platzhalter(self.kurzform):
            self.kurzform = kurzform_aus_dateiname(pfad)
        self.kurzform = slug(self.kurzform)

        rumpf, h1 = erste_h1_entfernen(rumpf)
        self.rohtext = rumpf

        titel = als_text(kopf.get("titel"))
        self.titel = h1 if (not titel or ist_platzhalter(titel)) else titel
        if not self.titel:
            raise ValueError(f"{pfad.name}: weder titel im Frontmatter noch H1 im Text")

        self.kategorie = als_text(kopf.get("kategorie"))
        self.format = als_text(kopf.get("format"))
        self.kernfrage = als_text(kopf.get("kernfrage"))
        self.zielgruppe = als_liste(kopf.get("zielgruppe"))
        self.schlagwoerter = als_liste(kopf.get("schlagwoerter"))
        self.definition = als_text(kopf.get("definition"))
        self.adressat = als_text(kopf.get("adressat"))
        self.status = als_text(kopf.get("status")) or "Entwurf"

        self.meta_beschreibung = als_text(kopf.get("meta_beschreibung"))
        if ist_platzhalter(self.meta_beschreibung):
            self.meta_beschreibung = ""
        if not self.meta_beschreibung:
            self.meta_beschreibung = self.kernfrage or self.titel
        self.meta_beschreibung = self.meta_beschreibung[:300]

        self.autor = als_text(kopf.get("autor")) or AUTOR_VORGABE
        self.qualifikation = als_text(kopf.get("qualifikation"))
        if ist_platzhalter(self.qualifikation):
            self.qualifikation = ""

        erstellt = datum_oder_none(als_text(kopf.get("erstellt")))
        if not erstellt:
            treffer = re.match(r"^(\d{4}-\d{2}-\d{2})-", pfad.stem)
            erstellt = treffer.group(1) if treffer else als_text(date.today())
        self.veroeffentlicht = erstellt
        self.geaendert = datum_oder_none(als_text(kopf.get("fachlich_geprueft_am"))) or erstellt

        self.geprueft_von = als_text(kopf.get("fachlich_geprueft_von"))
        if ist_platzhalter(self.geprueft_von):
            self.geprueft_von = ""

        self.inhalt_html, self.todos = markdown_zu_html(self.rohtext)
        self.faq = faq_aus_html(self.inhalt_html)
        self.wortzahl = woerter_zaehlen(haupttext(self.rohtext))
        self.wortzahl_gesamt = woerter_zaehlen(self.rohtext)

    @property
    def freigegeben(self) -> bool:
        """Status im Kopf der Datei – die Absicht des Autors."""
        return self.status.strip().lower() == STATUS_OEFFENTLICH

    @property
    def oeffentlich(self) -> bool:
        """Tatsächlich veröffentlicht: freigegeben UND keine offenen Prüfpunkte.

        Ein TODO-Block steht für eine Angabe, die der Agent bewusst nicht
        behauptet hat. Solange einer im Text steht, darf die Seite weder
        indexiert noch in Übersicht und Sitemap aufgenommen werden – auch
        dann nicht, wenn der Status schon auf Veröffentlicht steht.
        """
        return self.freigegeben and not self.todos

    @property
    def pfad_relativ(self) -> str:
        return f"fachwissen/{self.kurzform}/"

    @property
    def url(self) -> str:
        return f"{BASIS_URL}/{self.pfad_relativ}"

    @property
    def lesezeit(self) -> int:
        # Der Skill verlangt Aufrunden, nicht kaufmännisches Runden.
        return max(1, math.ceil(self.wortzahl / 200))


# --------------------------------------------------------------------------
# Mechanische Prüfung des Entwurfs
# --------------------------------------------------------------------------

# Mindestzahl der FAQ-Fragen. Die SKILL.md verweist auf diese Konstante,
# damit die Zahl nicht an zwei Stellen gepflegt werden muss.
FAQ_MINDEST = 6


def _falten(text: str) -> str:
    """Vergleichsform: Kleinschreibung, Umlaute auf den Grundbuchstaben.

    Nicht die Kurzform-Umschrift (ä zu ae) verwenden: Sonst scheitert das
    Schlagwort „Bauschaden" am Plural „Bauschäden", weil aus dem einen
    „bauschad" und aus dem anderen „bauschaed" wird.
    """
    tief = text.lower()
    for zeichen, ersatz in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        tief = tief.replace(zeichen, ersatz)
    return re.sub(r"[^a-z0-9]+", " ", tief)


def _stamm(begriff: str) -> str:
    """Wortstamm für die Schlagwort-Deckung: Endungen dürfen abweichen."""
    b = _falten(begriff).strip()
    return b[:-2] if len(b) > 6 else b


def entwurf_pruefen(a: "Artikel") -> list[str]:
    """Prüft den Entwurf mechanisch gegen die Regeln des Skills.

    Diese Prüfungen ändern den Rückgabewert NICHT. Der Generator läuft über
    alle Dateien im Entwurfsordner; ein Fehler in einem fremden, älteren
    Entwurf dürfte niemals den Commit des laufenden Entwurfs blockieren oder
    den Seitenbau auf dem Hauptzweig rot färben. Die Meldungen sind Hinweise
    für Agent und Verfasser, keine Sperre.
    """
    befunde: list[str] = []

    def melden(regel: str, ist, soll):
        befunde.append(f"PRUEFUNG: {a.pfad.name}: {regel} – {ist} statt {soll}")

    rumpf = haupttext(a.rohtext)
    ohne_todo = "\n".join(z for z in rumpf.split("\n") if not z.lstrip().startswith("> TODO:"))

    listen = len([z for z in rumpf.split("\n")
                  if re.match(r"^\s*([-*+] |\d+[.)] |\|)", z) and "[ ]" not in z])
    if a.format.lower() != "checkliste" and listen:
        melden("Aufzählungen oder Tabellen im Haupttext", listen, 0)

    for regel, muster, soll in [
        ("Überschriften ab H3", r"^#{3,}", 0),
        ("Ausrufezeichen im Haupttext", r"!", 0),
        ("Restmarker FORTSETZUNG", r"FORTSETZUNG", 0),
    ]:
        n = len(re.findall(muster, ohne_todo, flags=re.M))
        if n != soll:
            melden(regel, n, soll)

    gerade = ohne_todo.count('"')
    if gerade:
        melden("gerade Anführungszeichen außerhalb des Dateikopfs", gerade, 0)

    marken = {m for m in re.findall(r"\[\^(\d+)\](?!:)", a.rohtext)}
    eintraege = {m for m in re.findall(r"^\[\^(\d+)\]:", a.rohtext, flags=re.M)}
    if marken - eintraege:
        melden("Fußnotenmarken ohne Eintrag", sorted(marken - eintraege), "keine")
    if eintraege - marken:
        melden("Fußnoteneinträge ohne Marke im Text", sorted(eintraege - marken), "keine")
    if eintraege and sorted(int(x) for x in eintraege) != list(range(1, len(eintraege) + 1)):
        melden("Fußnoten nicht lückenlos nummeriert", sorted(int(x) for x in eintraege), "1..n")
    ohne_datum = [m.group(1) for m in re.finditer(r"^\[\^(\d+)\]:(.*)$", a.rohtext, flags=re.M)
                  if "abgerufen am" not in m.group(2)]
    if ohne_datum:
        melden("Fußnoteneinträge ohne Abrufdatum", ohne_datum, "keine")

    h2 = len(re.findall(r"^## ", rumpf, flags=re.M))
    if not 6 <= h2 <= 11:
        melden("H2-Abschnitte im Haupttext", h2, "6 bis 10 zuzüglich Häufige Fragen")

    if len(a.titel) > 70:
        melden("Länge titel", len(a.titel), "höchstens 70 Zeichen")
    if len(a.meta_beschreibung) > 155:
        melden("Länge meta_beschreibung", len(a.meta_beschreibung), "höchstens 155 Zeichen")

    intern = len(re.findall(r"ing-bassam\.de/#", a.rohtext))
    if intern not in (1, 2):
        melden("interne Verweise", intern, "1 oder 2")

    if len(a.faq) < FAQ_MINDEST:
        melden("erkannte FAQ-Paare", len(a.faq), f"mindestens {FAQ_MINDEST}")

    sichtbar = re.sub(r"<[^>]+>", " ", a.inhalt_html)
    if a.definition and a.definition.strip() not in re.sub(r"\s+", " ", sichtbar):
        melden("Definitionssatz wörtlich im Text", "fehlt", "wortgleich vorhanden")

    flach = _falten(sichtbar)
    fehlend = [s for s in a.schlagwoerter
               if len(s) >= 4 and _stamm(s) and _stamm(s) not in flach]
    if fehlend:
        melden("Schlagwörter ohne Deckung im Text", fehlend, "jedes Schlagwort kommt vor")

    # Markdown-Links [Text](Adresse) und Fußnotenmarken sind keine Platzhalter.
    platzhalter = [m.group(0) for m
                   in re.finditer(r"\[[^\]\n]{12,}\](?!\()", ohne_todo)
                   if not m.group(0).startswith("[^")]
    if platzhalter:
        melden("Platzhalter in eckigen Klammern im Text", platzhalter, "keine")

    return befunde


# --------------------------------------------------------------------------
# Seiten bauen
# --------------------------------------------------------------------------

KOPF_VORLAGE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titel_tag}</title>
<meta name="description" content="{beschreibung}">
<meta name="theme-color" content="#0a121d">
{robots}<link rel="canonical" href="{canonical}">
<!--
  DATENSCHUTZ: Diese Richtlinie erlaubt nur Dateien von dieser Website selbst.
  Die Artikelseiten kommen ohne JavaScript aus; Skripte sind vollständig gesperrt.
-->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self' mailto:">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%230a121d'/%3E%3Cpath d='M16 46h32' stroke='%23f26b2a' stroke-width='3'/%3E%3Ctext x='32' y='38' text-anchor='middle' font-family='Arial,sans-serif' font-size='22' font-weight='300' fill='%23ffffff'%3EBIB%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="{css}">
{og}</head>
<body>

<a class="skip-link" href="#inhalt">Zum Inhalt springen</a>

<header class="seiten-kopf">
  <div class="wrap kopf-innen">
    <a href="{start}" class="logo" aria-label="{kurzname} – zur Startseite"><b>BIB</b><span>Ingenieurbüro für Bauwesen</span></a>
    <nav aria-label="Bereiche">
      <a href="{start}#leistungen">Leistungen</a>
      <a href="{fachwissen}">Fachwissen</a>
      <a href="{start}#kontakt">Kontakt</a>
    </nav>
  </div>
</header>
"""

FUSS_VORLAGE = """
<footer class="seiten-fuss">
  <div class="wrap">
    <p><strong>{firma}</strong><br>Straße am Flugplatz 6a, 12487 Berlin</p>
    <p><a href="tel:+4917623581339">{telefon}</a> · <a href="mailto:{email}">{email}</a></p>
    <p class="rechtliches"><a href="{start}#impressum">Impressum</a> · <a href="{start}#datenschutz">Datenschutz</a> · <a href="{fachwissen}">Alle Fachbeiträge</a></p>
    <p class="klein">© {jahr} {firma} · Keine Cookies. Kein Tracking.</p>
  </div>
</footer>

</body>
</html>
"""


def og_block(titel: str, beschreibung: str, url: str, typ: str, zeit: str = "",
             geaendert: str = "", bereich: str = "", verfasser: str = "") -> str:
    zeilen = [
        '<meta property="og:type" content="%s">' % typ,
        '<meta property="og:locale" content="de_DE">',
        '<meta property="og:site_name" content="%s">' % html.escape(KURZNAME, quote=True),
        '<meta property="og:title" content="%s">' % html.escape(titel, quote=True),
        '<meta property="og:description" content="%s">' % html.escape(beschreibung, quote=True),
        '<meta property="og:url" content="%s">' % html.escape(url, quote=True),
        '<meta name="twitter:card" content="summary">',
    ]
    if zeit:
        zeilen.append('<meta property="article:published_time" content="%s">' % zeit)
    if geaendert:
        zeilen.append('<meta property="article:modified_time" content="%s">' % geaendert)
    if bereich:
        zeilen.append('<meta property="article:section" content="%s">'
                      % html.escape(bereich, quote=True))
    if verfasser:
        zeilen.append('<meta name="author" content="%s">' % html.escape(verfasser, quote=True))
    return "\n".join(zeilen) + "\n"


def kopf_bauen(*, titel_tag: str, beschreibung: str, canonical: str, css: str,
               start: str, fachwissen: str, indexierbar: bool, og: str) -> str:
    return KOPF_VORLAGE.format(
        titel_tag=html.escape(titel_tag),
        beschreibung=html.escape(beschreibung, quote=True),
        # Freigegebene Seiten erlauben Suchmaschinen ausdrücklich Auszüge in
        # voller Länge; ohne Angabe kürzen manche Anbieter von sich aus.
        robots=('<meta name="robots" content="max-snippet:-1, max-image-preview:large">\n'
                if indexierbar else '<meta name="robots" content="noindex, follow">\n'),
        canonical=html.escape(canonical, quote=True),
        css=css,
        og=og,
        start=start,
        fachwissen=fachwissen,
        kurzname=html.escape(KURZNAME, quote=True),
    )


def fuss_bauen(*, start: str, fachwissen: str) -> str:
    return FUSS_VORLAGE.format(
        firma=html.escape(FIRMA),
        telefon=html.escape(TELEFON),
        email=html.escape(EMAIL),
        start=start,
        fachwissen=fachwissen,
        jahr=date.today().year,
    )


def artikelseite(artikel: Artikel) -> str:
    kopf = kopf_bauen(
        titel_tag=f"{artikel.titel} | {KURZNAME}",
        beschreibung=artikel.meta_beschreibung,
        canonical=artikel.url,
        css="../artikel.css",
        start="../../",
        fachwissen="../",
        indexierbar=artikel.oeffentlich,
        og=og_block(artikel.titel, artikel.meta_beschreibung, artikel.url,
                    "article", artikel.veroeffentlicht,
                    geaendert=artikel.geaendert, bereich=artikel.kategorie,
                    verfasser=artikel.autor),
    )

    warnung = ""
    if not artikel.oeffentlich:
        warnung = (
            '<div class="entwurfswarnung" role="status">'
            "<strong>Entwurf – noch nicht freigegeben.</strong> Diese Seite ist von der "
            "Indexierung ausgenommen und steht weder in der Übersicht noch in der Sitemap. "
            f"Status: <code>{html.escape(artikel.status)}</code>. "
            "Sie wird öffentlich, sobald im Entwurf <code>status: Veröffentlicht</code> steht "
            "und kein Prüfpunkt mehr offen ist."
            + (f' Offene Prüfpunkte im Text: {artikel.todos}.' if artikel.todos else "")
            + "</div>"
        )

    marken = []
    if artikel.kategorie:
        # data-kategorie steuert die Farbe des Punktes; siehe artikel.css.
        marken.append(
            f'<span class="marke marke--kategorie" data-kategorie="{slug(artikel.kategorie)}">'
            f'{html.escape(artikel.kategorie)}</span>'
        )
    if artikel.format:
        marken.append(f'<span class="marke">{html.escape(artikel.format)}</span>')
    marken_html = " ".join(marken)

    geprueft = ""
    if artikel.geaendert != artikel.veroeffentlicht:
        geprueft = (f' · Zuletzt fachlich geprüft am '
                    f'<time datetime="{artikel.geaendert}">{datum_deutsch(artikel.geaendert)}</time>')

    return (
        kopf
        + f"""
<main id="inhalt">
  <article class="artikel">
    <div class="wrap schmal">
      {warnung}
      <nav class="brotkrumen" aria-label="Sie sind hier">
        <a href="../../">Start</a> <span aria-hidden="true">›</span>
        <a href="../">Fachwissen</a> <span aria-hidden="true">›</span>
        <span>{html.escape(artikel.titel)}</span>
      </nav>

      <header class="artikel-kopf">
        {marken_html}
        <h1>{html.escape(artikel.titel)}</h1>
        <p class="artikel-meta">
          Von {html.escape(artikel.autor)}{(" , " + html.escape(artikel.qualifikation)) if artikel.qualifikation else ""} ·
          <time datetime="{artikel.veroeffentlicht}">{datum_deutsch(artikel.veroeffentlicht)}</time>{geprueft} ·
          etwa {artikel.lesezeit} Minuten Lesezeit
        </p>
      </header>

      <div class="prosa">
{artikel.inhalt_html}
      </div>
    </div>
  </article>
</main>

<script type="application/ld+json">{strukturierte_daten(artikel)}</script>
"""
        + fuss_bauen(start="../../", fachwissen="../")
    )


def datum_deutsch(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return iso


def uebersichtsseite(artikel: list[Artikel]) -> str:
    beschreibung = (
        "Fachbeiträge zu Bauschäden, Bauphysik, Baubetrieb und baurechtlichen Fragen "
        f"– vom {FIRMA} in Berlin."
    )
    url = f"{BASIS_URL}/fachwissen/"
    kopf = kopf_bauen(
        titel_tag=f"Fachwissen | {KURZNAME}",
        beschreibung=beschreibung,
        canonical=url,
        css="artikel.css",
        start="../",
        fachwissen="./",
        indexierbar=True,
        og=og_block("Fachwissen", beschreibung, url, "website"),
    )

    if artikel:
        karten = []
        for a in sorted(artikel, key=lambda x: (x.veroeffentlicht, x.titel), reverse=True):
            marken_teile = []
            if a.kategorie:
                marken_teile.append(
                    f'<span class="marke marke--kategorie" data-kategorie="{slug(a.kategorie)}">'
                    f'{html.escape(a.kategorie)}</span>'
                )
            if a.format:
                marken_teile.append(f'<span class="marke">{html.escape(a.format)}</span>')
            marken = " ".join(marken_teile)
            karten.append(f"""        <li class="karte">
          <div class="marken">{marken}</div>
          <h2><a href="{a.kurzform}/">{html.escape(a.titel)}</a></h2>
          <p>{html.escape(a.meta_beschreibung)}</p>
          <p class="karte-meta"><time datetime="{a.veroeffentlicht}">{datum_deutsch(a.veroeffentlicht)}</time> · etwa {a.lesezeit} Minuten</p>
        </li>""")
        liste = '<ul class="karten">\n' + "\n".join(karten) + "\n      </ul>"
        einleitung = (
            f"{len(artikel)} Beitrag" if len(artikel) == 1 else f"{len(artikel)} Beiträge"
        ) + " zu Bauschäden, Bauphysik, Baubetrieb und baurechtlichen Fragen."
    else:
        liste = ('<p class="leer">Die ersten Fachbeiträge sind in Vorbereitung und '
                 "erscheinen hier nach fachlicher Prüfung.</p>")
        einleitung = "Fachbeiträge aus der Gutachten- und Baupraxis."

    return (
        kopf
        + f"""
<main id="inhalt">
  <div class="wrap">
    <nav class="brotkrumen" aria-label="Sie sind hier">
      <a href="../">Start</a> <span aria-hidden="true">›</span>
      <span>Fachwissen</span>
    </nav>
    <header class="uebersicht-kopf">
      <h1>Fachwissen</h1>
      <p>{html.escape(einleitung)}</p>
    </header>
    {liste}
  </div>
</main>
"""
        + fuss_bauen(start="../", fachwissen="./")
    )


def bisherige_stande() -> dict[str, str]:
    """Liest die lastmod-Werte der vorhandenen sitemap.xml."""
    if not SITEMAP.exists():
        return {}
    roh = SITEMAP.read_text(encoding="utf-8")
    paare = re.findall(r"<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>", roh, re.S)
    return {ort.strip(): stand.strip() for ort, stand in paare}


def sitemap_bauen(artikel: list[Artikel], heute: str) -> str:
    # lastmod muss den letzten inhaltlichen Stand angeben. Würde hier immer das
    # heutige Datum stehen, änderte sich die Datei bei jedem Lauf – das erzeugt
    # unnötige Commits, und Suchmaschinen verlieren das Vertrauen in die Angabe.
    alt = bisherige_stande()
    start_url = BASIS_URL + "/"
    uebersicht_url = f"{BASIS_URL}/fachwissen/"
    neuester = max((a.geaendert for a in artikel), default="")

    def stand(url: str) -> str:
        return neuester or alt.get(url) or heute

    eintraege = [
        (start_url, stand(start_url), "monthly", "1.0"),
        (uebersicht_url, stand(uebersicht_url), "weekly", "0.8"),
    ]
    for a in sorted(artikel, key=lambda x: x.kurzform):
        eintraege.append((a.url, a.geaendert, "yearly", "0.7"))

    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for ort, stand, takt, gewicht in eintraege:
        zeilen += [
            "  <url>",
            f"    <loc>{html.escape(ort)}</loc>",
            f"    <lastmod>{stand}</lastmod>",
            f"    <changefreq>{takt}</changefreq>",
            f"    <priority>{gewicht}</priority>",
            "  </url>",
        ]
    zeilen.append("</urlset>")
    return "\n".join(zeilen) + "\n"


# --------------------------------------------------------------------------
# Ablauf
# --------------------------------------------------------------------------

def schreiben(pfad: Path, inhalt: str, geaendert: list[str], nur_pruefen: bool) -> None:
    alt = pfad.read_text(encoding="utf-8") if pfad.exists() else None
    if alt == inhalt:
        return
    geaendert.append(str(pfad.relative_to(WURZEL)).replace(os.sep, "/"))
    if nur_pruefen:
        return
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8", newline="\n")


def main() -> int:
    zerleger = argparse.ArgumentParser(description="Baut die Fachwissen-Seiten.")
    zerleger.add_argument("--pruefen", action="store_true",
                          help="nichts schreiben, nur melden, ob sich etwas ändern würde")
    argumente = zerleger.parse_args()

    heute = als_text(date.today())
    artikel: list[Artikel] = []
    fehler: list[str] = []

    if ENTWUERFE.is_dir():
        for pfad in sorted(ENTWUERFE.glob("*.md")):
            try:
                artikel.append(Artikel(pfad))
            except Exception as ausnahme:  # eine kaputte Datei stoppt nicht alles
                fehler.append(f"{pfad.name}: {ausnahme}")

    bekannt: dict[str, Path] = {}
    for a in artikel:
        if a.kurzform in bekannt:
            fehler.append(
                f"{a.pfad.name}: Kurzform „{a.kurzform}\" wird schon von "
                f"{bekannt[a.kurzform].name} belegt"
            )
        bekannt[a.kurzform] = a.pfad

    # Freigabe trotz offener Prüfpunkte ist ein Fehler, kein stiller Sonderfall:
    # Der Lauf endet mit Rückgabewert 2, der Workflow schlägt sichtbar fehl.
    for a in artikel:
        if a.freigegeben and a.todos:
            fehler.append(
                f"{a.pfad.name}: Status „Veröffentlicht“, aber {a.todos} offene "
                f"Prüfpunkte im Text. Erst die TODO-Blöcke auflösen, dann freigeben. "
                f"Die Seite bleibt bis dahin auf noindex."
            )

    oeffentlich = [a for a in artikel if a.oeffentlich]

    geaendert: list[str] = []
    for a in artikel:
        schreiben(ZIEL / a.kurzform / "index.html", artikelseite(a), geaendert, argumente.pruefen)
    schreiben(ZIEL / "index.html", uebersichtsseite(oeffentlich), geaendert, argumente.pruefen)
    schreiben(SITEMAP, sitemap_bauen(oeffentlich, heute), geaendert, argumente.pruefen)

    # Seiten entfernen, zu denen es keinen Entwurf mehr gibt.
    verwaist: list[str] = []
    if ZIEL.is_dir():
        for ordner in sorted(p for p in ZIEL.iterdir() if p.is_dir()):
            if ordner.name not in bekannt:
                verwaist.append(f"fachwissen/{ordner.name}/")
                if not argumente.pruefen:
                    for datei in sorted(ordner.rglob("*"), reverse=True):
                        datei.unlink() if datei.is_file() else datei.rmdir()
                    ordner.rmdir()

    print(f"Entwürfe gefunden: {len(artikel)}")
    print(f"Davon veröffentlicht: {len(oeffentlich)}")
    for a in sorted(artikel, key=lambda x: x.kurzform):
        kennzeichen = "öffentlich" if a.oeffentlich else f"noindex ({a.status})"
        hinweis = f", {a.todos} offene Prüfpunkte" if a.todos else ""
        print(f"  - {a.kurzform}: {a.wortzahl} Wörter, {len(a.faq)} FAQ, {kennzeichen}{hinweis}")
        print(f"      Haupttext: {a.wortzahl} Wörter (Vorschlag für das Frontmatter-Feld wortzahl), "
              f"Datei gesamt: {a.wortzahl_gesamt}")
        for zeile in entwurf_pruefen(a):
            print(f"      {zeile}")
    if verwaist:
        print("Entfernt (kein Entwurf mehr vorhanden): " + ", ".join(verwaist))
    if geaendert:
        print("Geändert: " + ", ".join(geaendert))
    else:
        print("Keine Änderungen.")
    for eintrag in fehler:
        print(f"FEHLER: {eintrag}", file=sys.stderr)

    if fehler:
        return 2
    if argumente.pruefen and (geaendert or verwaist):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
