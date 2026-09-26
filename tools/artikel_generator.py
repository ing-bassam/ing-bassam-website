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
# Autorenname, wie ihn der Auftraggeber festgelegt hat (21.09.2026): überall
# „M. Sc. Karim Abu Elkheir“. Steht im Entwurf eine andere Schreibweise
# desselben Namens („Karim Abu Elkheir“, „M.Sc. …“), gilt trotzdem diese –
# Suchmaschinen und KI-Systeme ordnen Urheberschaft über den Namen zu, und
# dafür muss er auf jeder Seite gleich lauten.
AUTOR_NAME = "Karim Abu Elkheir"
AUTOR_GRAD = "M. Sc."
AUTOR_VORGABE = f"{AUTOR_GRAD} {AUTOR_NAME}"
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

GRAD_VORN = re.compile(
    r"^\s*((?:(?:M|B)\.?\s?(?:Sc|Eng|A)\.?|Dipl\.-Ing\.(?:\s?\(FH\))?|Dr\.-Ing\.|Dr\.)\s+)+")


def autor_aufteilen(roh: str) -> tuple[str, str, str]:
    """Liefert Anzeigeform, Name ohne Grad und Grad.

    In den strukturierten Daten steht der Grad getrennt (honorificPrefix),
    damit die Person unter ihrem Namen erkannt wird; sichtbar bleibt die volle
    Form.
    """
    treffer = GRAD_VORN.match(roh)
    grad = " ".join(treffer.group(0).split()) if treffer else ""
    name = " ".join((roh[treffer.end():] if treffer else roh).split())
    if name == AUTOR_NAME:
        return AUTOR_VORGABE, AUTOR_NAME, AUTOR_GRAD
    return " ".join(f"{grad} {name}".split()), name, grad


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
        "name": artikel.autor_name,
        "honorificPrefix": artikel.autor_grad or None,
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

        self.autor, self.autor_name, self.autor_grad = autor_aufteilen(
            als_text(kopf.get("autor")) or AUTOR_VORGABE)
        self.qualifikation = als_text(kopf.get("qualifikation"))
        if ist_platzhalter(self.qualifikation):
            self.qualifikation = ""

        erstellt = datum_oder_none(als_text(kopf.get("erstellt")))
        if not erstellt:
            treffer = re.match(r"^(\d{4}-\d{2}-\d{2})-", pfad.stem)
            erstellt = treffer.group(1) if treffer else als_text(date.today())
        self.veroeffentlicht = erstellt
        # Letzter inhaltlicher Stand. „aktualisiert“ setzt der Autor, wenn er
        # den Beitrag überarbeitet; bisher änderte sich das Datum nur mit
        # „fachlich_geprueft_am“, und eine Überarbeitung blieb für Leser und
        # Suchmaschinen unsichtbar. Es gilt das jüngste der drei Daten.
        # Vorlagen: Liste der Download-Dateien (Pfad relativ zur Repository-Wurzel).
        # Der Vorlagen-Agent trägt sie ein; die Seite zeigt daraus den Download-Kasten.
        self.dateien = [als_text(d) for d in als_liste(kopf.get("dateien"))]
        self.aktualisiert = datum_oder_none(als_text(kopf.get("aktualisiert")))
        geprueft_am = datum_oder_none(als_text(kopf.get("fachlich_geprueft_am")))
        self.geaendert = max(d for d in (erstellt, self.aktualisiert, geprueft_am) if d)

        self.geprueft_von = als_text(kopf.get("fachlich_geprueft_von"))
        if ist_platzhalter(self.geprueft_von):
            self.geprueft_von = ""

        # Verwandte Beiträge setzt main(), sobald alle Entwürfe gelesen sind.
        self.passende: list[Artikel] = []
        self.passend_thematisch = False

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

# Lesezeit, die der Auftraggeber für angenehm hält. Bei 200 Wörtern je Minute
# entspricht das 3.000 bis 5.000 Wörtern Haupttext.
LESEZEIT_MIN = 15
LESEZEIT_MAX = 25

# Kurze Formate: leicht verständliche Urteilsbesprechung und die Seite zu einer
# Vorlage. Der Auftraggeber will dort höchstens 10 Minuten Lesezeit, wenige
# Abschnitte und weniger FAQ. Schlüssel: Format in Kleinschreibung.
KURZE_FORMATE = {
    "urteil verständlich": {"lesezeit": (4, 10), "h2": (3, 7), "faq": 3},
    "vorlage": {"lesezeit": (5, 10), "h2": (3, 7), "faq": 3},
}

# Formate, die eine Gerichtsentscheidung wiedergeben: Jeder Absatz über das
# Gericht braucht eine Randnummer.
URTEILS_FORMATE = {"rechtsprechung", "urteil verständlich"}


def grenzen(a: "Artikel") -> dict:
    """Lesezeit-, Abschnitts- und FAQ-Grenzen für das Format des Beitrags."""
    kurz = KURZE_FORMATE.get(a.format.lower())
    if kurz:
        return kurz
    return {"lesezeit": (LESEZEIT_MIN, LESEZEIT_MAX), "h2": (6, 8), "faq": FAQ_MINDEST}


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
    # Webquellen tragen ein Abrufdatum, Buch- und Normquellen aus der
    # Fachbibliothek stattdessen eine Seitenangabe (Bücher zusätzlich die ISBN).
    ohne_datum = [m.group(1) for m in re.finditer(r"^\[\^(\d+)\]:(.*)$", a.rohtext, flags=re.M)
                  if "abgerufen am" not in m.group(2)
                  and not (re.search(r"\bS\.\s*\S+", m.group(2)) and "http" not in m.group(2))]
    if ohne_datum:
        melden("Fußnoteneinträge ohne Abrufdatum (Web) oder Seitenangabe (Buch)",
               ohne_datum, "keine")

    g = grenzen(a)
    h2 = len(re.findall(r"^## ", rumpf, flags=re.M))
    h2_min, h2_max = g["h2"]
    # Die FAQ zählen als eigene H2 mit; bei den langen Formaten gilt weiter 7..10.
    if not h2_min + 1 <= h2 <= h2_max + 2:
        melden("H2-Abschnitte im Haupttext", h2, f"{h2_min} bis {h2_max} zuzüglich Häufige Fragen")

    lz_min, lz_max = g["lesezeit"]
    if not lz_min <= a.lesezeit <= lz_max:
        melden("Lesezeit", f"{a.lesezeit} Minuten ({a.wortzahl} Wörter)",
               f"{lz_min} bis {lz_max} Minuten")

    if len(a.titel) > 70:
        melden("Länge titel", len(a.titel), "höchstens 70 Zeichen")
    if len(a.meta_beschreibung) > 155:
        melden("Länge meta_beschreibung", len(a.meta_beschreibung), "höchstens 155 Zeichen")

    intern = len(re.findall(r"ing-bassam\.de/#", a.rohtext))
    if intern not in (1, 2):
        melden("interne Verweise", intern, "1 oder 2")

    if len(a.faq) < g["faq"]:
        melden("erkannte FAQ-Paare", len(a.faq), f"mindestens {g['faq']}")

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

    # Doppelte Wörter. „und und“ ist ein Tippfehler; „Den den Eigentümern
    # übersandten …“ ist grammatisch möglich, liest sich aber wie einer und wird
    # umgestellt. Relativsätze wie „…, die die Eigentümer …“ und „soweit sie sie
    # anerkannte“ bleiben unbeanstandet.
    doppelt = []
    for m in re.finditer(r"\b([^\W\d_]+)\s+(\1)\b", ohne_todo, flags=re.I):
        wort = m.group(1)
        if wort in {"Sie", "sie", "die", "der", "das", "den", "dem", "des"}:
            continue
        doppelt.append(m.group(0))
    if doppelt:
        melden("doppelte Wörter", doppelt, "keine (Tippfehler beheben oder Satz umstellen)")

    # Urteilsbesprechung: Jeder Absatz, der das Gericht nennt, trägt die
    # Randnummer, auf der er beruht. Beim Beitrag zu OVG 6 A 1/25 standen
    # Zuschreibungen an den Senat ohne Randnummer und wurden nie geprüft.
    if a.format.lower() in URTEILS_FORMATE:
        ohne_rn = []
        for absatz in re.split(r"\n\s*\n", ohne_todo):
            absatz = absatz.strip()
            if not absatz or absatz.startswith(("#", "**", ">")):
                continue
            if re.search(r"\b(Senat|Senats|Kammer)\b", absatz) and "(Rn." not in absatz:
                ohne_rn.append(" ".join(absatz.split()[:8]) + " …")
        if ohne_rn:
            melden("Absätze über die Entscheidung ohne Randnummer", ohne_rn,
                   "je Absatz mindestens eine „(Rn. n)“")

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

    stand = ""
    if artikel.geaendert != artikel.veroeffentlicht:
        wort = ("Aktualisiert am" if artikel.aktualisiert == artikel.geaendert
                else "Zuletzt fachlich geprüft am")
        stand = (f' · {wort} '
                 f'<time datetime="{artikel.geaendert}">{datum_deutsch(artikel.geaendert)}</time>')

    qualifikation = f", {html.escape(artikel.qualifikation)}" if artikel.qualifikation else ""

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
          Von {html.escape(artikel.autor)}{qualifikation} ·
          <time datetime="{artikel.veroeffentlicht}">{datum_deutsch(artikel.veroeffentlicht)}</time>{stand} ·
          etwa {artikel.lesezeit} Minuten Lesezeit
        </p>
      </header>

{download_html(artikel)}      <div class="prosa">
{autorenkasten_angleichen(artikel.inhalt_html, artikel.geaendert)}
      </div>
{weiterlesen_html(artikel)}
    </div>
  </article>
</main>

<script type="application/ld+json">{strukturierte_daten(artikel)}</script>
"""
        + fuss_bauen(start="../../", fachwissen="../")
    )


DATEI_ARTEN = {
    ".pdf": ("PDF", "zum Ausdrucken oder am Bildschirm ausfüllen"),
    ".docx": ("Word", "zum Anpassen"),
    ".xlsx": ("Excel", "zum Weiterrechnen"),
}


def download_html(artikel: "Artikel") -> str:
    """Kasten mit den Download-Dateien einer Vorlage, oben auf der Seite."""
    if not artikel.dateien:
        return ""
    eintraege = []
    for pfad in artikel.dateien:
        datei = WURZEL / pfad
        if not datei.is_file():
            print(f"PRUEFUNG: {artikel.pfad.name}: Download-Datei fehlt – {pfad}")
            continue
        art, zweck = DATEI_ARTEN.get(datei.suffix.lower(), (datei.suffix.lstrip(".").upper(), ""))
        if "ausfuellbar" in datei.stem:
            art, zweck = "PDF ausfüllbar", "am Bildschirm ausfüllen und speichern"
        elif datei.suffix.lower() == ".pdf":
            zweck = "zum Ausdrucken"
        groesse = datei.stat().st_size
        groesse_text = f"{groesse / 1024:.0f} KB" if groesse < 1_000_000 else f"{groesse / 1_048_576:.1f} MB"
        eintraege.append(
            f'        <li><a class="download" href="{html.escape(BASIS_URL + "/" + pfad)}" download>'
            f'<b>{html.escape(art)}</b> <span>{html.escape(zweck)} · {groesse_text}</span></a></li>')
    if not eintraege:
        return ""
    return ('      <aside class="downloads" aria-labelledby="downloads-titel">\n'
            '        <h2 id="downloads-titel">Vorlage herunterladen</h2>\n'
            '        <p>Kostenlos, ohne Anmeldung. Mit Logo und Stand des Büros; '
            'bitte unverändert weitergeben.</p>\n'
            '        <ul>\n' + "\n".join(eintraege) + "\n        </ul>\n      </aside>\n")


def autorenkasten_angleichen(inhalt: str, geaendert: str) -> str:
    """Autorenname und „Stand“ im Autorenkasten auf den gültigen Stand bringen.

    Der Kasten steht als Text im Entwurf. Ohne diese Angleichung zeigte der
    Kopf „Aktualisiert am 15.10.“, der Kasten darunter aber weiter den Stand
    vom Erstelldatum – und ältere Entwürfe schrieben den Grad „M.Sc.“ ohne
    Leerzeichen.
    """
    inhalt = inhalt.replace(f"M.Sc. {AUTOR_NAME}", AUTOR_VORGABE)

    def ersetzen(treffer: re.Match) -> str:
        return treffer.group(1) + max(treffer.group(2), geaendert)

    return re.sub(r"(Kontakt:[^<]*?Stand:\s*)(\d{4}-\d{2}-\d{2})", ersetzen, inhalt)


def passende_beitraege(artikel: "Artikel", kandidaten: list["Artikel"],
                       anzahl: int = 3) -> tuple[list["Artikel"], bool]:
    """Die veröffentlichten Beiträge, die thematisch am nächsten liegen.

    Punkte: je gemeinsames Schlagwort 3, gleiche Kategorie 2, je gemeinsame
    Zielgruppe 1. Bei Gleichstand der neuere Beitrag, dann der Titel – so
    liefern zwei Läufe dasselbe Ergebnis. Reichen die thematischen Treffer
    nicht, füllen die neuesten Beiträge auf; der zweite Rückgabewert sagt,
    ob alle gezeigten Beiträge thematisch passen.

    Weil die Liste bei jedem Neubau neu berechnet wird, verlinken ältere
    Artikel automatisch auf neu veröffentlichte.
    """
    eigene = {_falten(s) for s in artikel.schlagwoerter}

    def punkte(b: "Artikel") -> int:
        wert = 3 * len(eigene & {_falten(s) for s in b.schlagwoerter})
        if artikel.kategorie and b.kategorie == artikel.kategorie:
            wert += 2
        return wert + len(set(artikel.zielgruppe) & set(b.zielgruppe))

    andere = [b for b in kandidaten if b.kurzform != artikel.kurzform]
    andere.sort(key=lambda b: b.titel)
    andere.sort(key=lambda b: b.veroeffentlicht, reverse=True)
    andere.sort(key=punkte, reverse=True)
    thematisch = [b for b in andere if punkte(b) > 0][:anzahl]
    if len(thematisch) >= min(2, len(andere)):
        return thematisch, True
    auffuellen = [b for b in andere if b not in thematisch][:anzahl - len(thematisch)]
    return thematisch + auffuellen, False


def weiterlesen_html(artikel: "Artikel") -> str:
    """Block unter dem Artikel: Links auf verwandte, veröffentlichte Beiträge."""
    if not artikel.passende:
        return ""
    karten = []
    for b in artikel.passende:
        marke = (f'<span class="marke marke--kategorie" data-kategorie="{slug(b.kategorie)}">'
                 f'{html.escape(b.kategorie)}</span>' if b.kategorie else "")
        karten.append(f"""          <li class="karte">
            <div class="marken">{marke}</div>
            <h3><a href="../{b.kurzform}/">{html.escape(b.titel)}</a></h3>
            <p>{html.escape(b.meta_beschreibung)}</p>
            <p class="karte-meta"><time datetime="{b.veroeffentlicht}">{datum_deutsch(b.veroeffentlicht)}</time> · etwa {b.lesezeit} Minuten</p>
          </li>""")
    ueberschrift = "Passende Fachbeiträge" if artikel.passend_thematisch else "Weitere Fachbeiträge"
    return (f"""      <nav class="weiterlesen" aria-labelledby="weiterlesen-titel">
        <h2 id="weiterlesen-titel">{ueberschrift}</h2>
        <ul class="karten">
""" + "\n".join(karten) + """
        </ul>
      </nav>""")


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
            karten.append(f"""        <li class="karte" data-kategorie="{slug(a.kategorie)}" data-format="{slug(a.format)}">
          <div class="marken">{marken}</div>
          <h2><a href="{a.kurzform}/">{html.escape(a.titel)}</a></h2>
          <p>{html.escape(a.meta_beschreibung)}</p>
          <p class="karte-meta"><time datetime="{a.veroeffentlicht}">{datum_deutsch(a.veroeffentlicht)}</time> · etwa {a.lesezeit} Minuten</p>
        </li>""")
        liste = filter_html(artikel) + '<ul class="karten">\n' + "\n".join(karten) + "\n      </ul>"
        einleitung = (
            f"{len(artikel)} Beitrag" if len(artikel) == 1 else f"{len(artikel)} Beiträge"
        ) + " zu Bauschäden, Bauphysik, Baubetrieb und baurechtlichen Fragen – zum Eingrenzen ein Thema oder Format antippen."
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


def filter_html(artikel: list[Artikel]) -> str:
    """Hashtag-Chips über der Übersicht: ein Klick zeigt nur Beiträge dieser
    Kategorie oder dieses Formats.

    Ohne JavaScript – die Seiten liefern keins aus (Content-Security-Policy,
    KI-Crawler). Die Chips sind Radio-Knöpfe; die Regel ``:has(#…:checked)``
    blendet die übrigen Karten aus. Browser ohne ``:has`` (vor 2023) zeigen
    einfach alle Beiträge. Die Regeln entstehen hier je vorhandenem Wert.
    """
    kategorien: dict[str, tuple[str, int]] = {}
    formate: dict[str, tuple[str, int]] = {}
    for a in artikel:
        if a.kategorie:
            k = slug(a.kategorie)
            kategorien[k] = (a.kategorie, kategorien.get(k, ("", 0))[1] + 1)
        if a.format:
            f = slug(a.format)
            formate[f] = (a.format, formate.get(f, ("", 0))[1] + 1)
    if len(kategorien) + len(formate) < 2:
        return ""

    def chip(kennung: str, name: str, anzahl: int, zusatz: str = "") -> str:
        return (f'          <input type="radio" name="filter" id="filter-{kennung}"{zusatz}>'
                f'<label for="filter-{kennung}">#{html.escape(name)} <span>{anzahl}</span></label>')

    zeilen = ['      <form class="filter" aria-label="Beiträge eingrenzen">',
              '        <p class="filter-titel">Thema</p>',
              '        <div class="chips">',
              chip("alle", "Alle", len(artikel), " checked")]
    zeilen += [chip(f"k-{k}", name, n) for k, (name, n) in sorted(kategorien.items(),
                                                                key=lambda e: e[1][0])]
    zeilen += ['        </div>', '        <p class="filter-titel">Format</p>', '        <div class="chips">']
    zeilen += [chip(f"f-{f}", name, n) for f, (name, n) in sorted(formate.items(),
                                                                key=lambda e: e[1][0])]
    zeilen += ['        </div>', '      </form>']

    regeln = []
    for k in kategorien:
        regeln.append(f'main:has(#filter-k-{k}:checked) .karte:not([data-kategorie="{k}"])'
                      '{display:none}')
        regeln.append(f'#filter-k-{k}:checked+label{{--chip:var(--kat,var(--accent))}}')
    for f in formate:
        regeln.append(f'main:has(#filter-f-{f}:checked) .karte:not([data-format="{f}"])'
                      '{display:none}')
    # Die Kategoriefarbe des Chips kommt aus derselben Zuordnung wie der Punkt auf den Karten.
    for k, (name, _n) in kategorien.items():
        regeln.append(f'label[for="filter-k-{k}"]{{--kat:var(--kat-{k})}}')
    stil = "      <style>" + "".join(regeln) + "</style>"
    return "\n".join(zeilen) + "\n" + stil + "\n      "


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
    # Verlinkt wird nur auf Veröffentlichtes – nie auf einen Entwurf mit noindex.
    for a in artikel:
        a.passende, a.passend_thematisch = passende_beitraege(a, oeffentlich)

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
