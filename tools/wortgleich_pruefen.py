#!/usr/bin/env python3
"""Sperre gegen wörtliche Übernahmen aus der Fachbibliothek.

Regel des Inhabers:

    „Aus Fachbüchern, Fachaufsätzen, Normen, Regelwerken und Leistungsverzeichnissen
    wird nichts wörtlich übernommen: kein Satz, kein Satzteil, keine Tabelle, keine
    Abbildung, kein Rechenbeispiel – auch nicht in Anführungszeichen. Diese Quellen
    dienen nur dazu, Fakten zu prüfen; die Aussage steht in eigenen Worten mit
    Fundstelle (Werk, Ausgabe, Seite oder Abschnitt). Kurze wörtliche Zitate sind nur
    aus amtlichen Werken (Gesetze, Verordnungen, Gerichtsentscheidungen, § 5 UrhG)
    erlaubt, mit Fundstelle. Wörtliche Belegstücke aus Büchern oder Normen stehen nie
    an öffentlichen Stellen (Repository-Dateien, PR-Texte, PR-Kommentare, Issues,
    Logs, Job-Zusammenfassungen), sondern nur in Arbeitsdateien im Runner-Temp.“

Das Werkzeug vergleicht jeden Entwurf Wortfolge für Wortfolge mit dem Text aller
Fachbücher und Forschungsarbeiten der Fachbibliothek (privates Repository
FachwissenAgent, im Workflow unter .bibliothek) und, mit --zusatz, mit den für
die Schlussprüfung heruntergeladenen Quelltexten (Fachaufsätze, Verbandsschriften;
amtliche Seiten wie gesetze-im-internet.de ausgenommen). Stimmen mindestens so
viele Wörter hintereinander überein wie die Grenze (Standard 8), ist das ein
Treffer – im Fließtext, in Tabellen, in den Fußnoten und in den veröffentlichten
Feldern des Dateikopfs (titel, meta_beschreibung, definition, kernfrage,
schlagwoerter), denn all das wird veröffentlicht. Eine Vorlagen-Beschreibung
(vorlagen/<kurzform>.yml, ohne Dateikopf) wird mit allen Textfeldern geprüft.
Groß- und Kleinschreibung, Umlaute, Satzzeichen, Silbentrennung und Markdown
spielen keine Rolle; nur eine echte Umschreibung hilft. Als Wörter zählen nur
Wörter aus Buchstaben: Ziffern, einzelne Buchstaben und Zitierkürzel (Abs., Nr.,
Satz, DIN, EN, ISO, VOB …) zählen nicht mit – eine Kette aus Paragrafen oder
Normnummern ist eine Fundstelle, kein übernommener Text.

Nicht gemeldet werden Wortfolgen, die auch stehen
- in den amtlichen Werken der Bibliothek (gemeinfrei/texte, § 5 UrhG),
- im Zitat, Titel oder Untertitel eines Katalogeintrags (Werktitel in Fußnoten),
- in tools/wortgleich_erlaubt.txt (vom Inhaber freigegebene feste Wendungen);
ebenso eine Strecke, von der höchstens zwei Randwörter nicht durch solche
Freigaben gedeckt sind (ein amtliches Zitat mit „BGB“ dahinter oder einem
Artikel davor). In Fußnoten ausgeblendet wird der Titel einer Norm direkt hinter
Nummer und Ausgabe – in „…“ (DIN 4109-1:2018-01 „Titel“) und ohne
Anführungszeichen hinter Komma, Doppelpunkt oder Gedankenstrich bis zum
Satzende oder zur Adresse –, aber nur, wenn er wie ein Titel aussieht: höchstens
25 Wörter, kein Satzende und kein Satzwort (ist, muss, handelt, es, sich, dass …)
darin. Im Fließtext wird nichts ausgeblendet; ein Satz aus der Norm in
Anführungszeichen ist dort wie überall ein Treffer.

Ebenfalls Treffer: Bilder und Grafiken im Entwurf (Markdown-Bild, <img>, <svg>,
<figure>). Tabellen sind nur ein Hinweis – eigene Tabellen sind erlaubt.

Aufruf:
    python tools/wortgleich_pruefen.py <entwurf.md|vorlage.yml> [<weitere> ...] --bibliothek <ordner>
        [--zusatz <ordner mit Quelltexten>] [--grenze 8] [--bericht <datei.md>] [--json <datei.json>]
        [--intern]

Mehrere Entwürfe in einem Aufruf: Die Bibliothek wird nur einmal gelesen.

Rückgabewert 0 = keine Treffer, 1 = Treffer, 2 = Fachbibliothek fehlt oder ist
unlesbar – dann ist NICHTS geprüft und der Entwurf bleibt gesperrt. Letzte Zeile
der Ausgabe: „treffer=<n>“ bzw. „treffer=nicht-geprueft“.

Ausgabe und Bericht (--bericht) landen in öffentlichen Logs,
Job-Zusammenfassungen, PR-Texten und PR-Kommentaren. Sie nennen je Treffer nur
Datei, Abschnitt (Zwischenüberschrift oder Feld des Dateikopfs), Zeile, Länge in
Wörtern und einen neutralen Vermerk („in eigenen Worten neu fassen“) – keine
Werk-Kennung, keine Seite, keine Zahl der Werke und keinen Namen einer Quelle
oder Webquelle, denn das dokumentierte öffentlich, aus welchem Werk eine Stelle
stammt. Nie erscheint Text aus der Bibliothek oder eine Wortfolge aus dem
Entwurf; liegt ein Treffer in einer Zwischenüberschrift selbst, erscheint statt
ihres Wortlauts nur ihre Zeilennummer. Hinweise auf Tabellen und Abbildungen
bleiben, denn sie nennen keine Quelle.

Mit --intern nennen Ausgabe und Bericht zusätzlich Werk-Kennung, gedruckte
Seite und die Zahl der Werke – nur zur eigenen Überarbeitung (am PC des
Inhabers oder im Arbeitsschritt eines Agenten). Diese Angaben gehören nie in
pr-body.md, PR-Kommentare, Issues, Logs, Job-Zusammenfassungen oder
Abschlussmeldungen; kein Workflow ruft --intern auf.

Die JSON-Datei (--json) ist immer vollständig, mit Werk-Kennung und Seite, aber
ohne Text. Sie liegt nur im Runner-Temp, wird von tools/veroeffentlichen.py
gelesen und nie ins Protokoll, in eine Zusammenfassung oder einen Kommentar
ausgegeben.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bibliothek_suchen import KOPF  # noqa: E402  (Seitenkopf „=== S. <Seite> | PDF <n> ===“)

ERLAUBT = Path(__file__).resolve().parent / "wortgleich_erlaubt.txt"
GRENZE = 8
# Durchsucht werden Fachbücher (oberste Ebene) und Forschungsarbeiten – nicht
# quellen/: Die Steckbriefe dort enthalten Sätze aus unseren eigenen Beiträgen.
KORPUS = ("", "forschung")
AMTLICH = "gemeinfrei"
VIELE_WERKE = 3          # ab so vielen Werken vermutlich Gesetzes-, VOB- oder Normwortlaut
RANDWOERTER = 2          # so viele ungedeckte Randwörter an amtlichem Wortlaut oder Werktitel sind frei
TITEL_HOECHSTENS = 25    # längere Anführungen hinter einer Normnummer sind kein Titel
UEBERSCHRIFT = "## Wörtliche Übernahmen aus der Fachbibliothek"
NICHT_GEPRUEFT = "Nicht geprüft: Fachbibliothek nicht geladen – Entwurf bleibt gesperrt."
# Öffentliche Ausgabe (ohne --intern): je Wortfolge nur dieser Vermerk – nichts, was auf das Werk schließen lässt
NEUTRAL = "in eigenen Worten neu fassen"
SCHLUSS_OEFFENTLICH = ("Jede Stelle in eigenen Worten neu fassen. Werk und Seite zeigt nur der interne Aufruf mit "
                       "--intern (nie in öffentliche Kommentare übernehmen). Freigaben fester Wendungen nur durch "
                       "den Inhaber (tools/wortgleich_erlaubt.txt).")
SCHLUSS_INTERN = ("Jede Fundstelle in eigenen Worten neu fassen und mit Werk und Seite belegen. "
                  "Freigaben fester Wendungen nur durch den Inhaber (tools/wortgleich_erlaubt.txt).")
INTERN_WARNUNG = ("Interne Ausgabe mit Werk und Seite – nur zur eigenen Überarbeitung; nie in pr-body.md, "
                  "Kommentare, Issues oder Abschlussmeldungen übernehmen.")
# Veröffentlichte Felder des Dateikopfs (Seitentitel, Meta-Description, JSON-LD, Übersicht)
KOPFFELDER = ("titel", "meta_beschreibung", "definition", "kernfrage", "schlagwoerter")

# ---------------------------------------------------------------------------
# Normalisierung – für Entwurf und Bibliothek dieselbe
# ---------------------------------------------------------------------------

# Silbentrennung am Zeilenende: „Abdich-⏎tung“ wird „Abdichtung⏎“. Der
# Zeilenumbruch wandert hinter das Wort, damit die Zeilenzählung des Entwurfs
# stimmt. Nicht bei „Wärme-⏎und Feuchteschutz“ (Ergänzungsstrich).
TRENNSTRICHE = "-­‐‑¬"   # Bindestrich, weiches Trennzeichen, Trennstriche, Negationszeichen
TRENNUNG = re.compile(r"[" + TRENNSTRICHE + r"](?<=[^\W\d_][" + TRENNSTRICHE + r"])[ \t]*\r?\n[ \t]*"
                      r"(?!(?:und|oder|bzw|sowie|bis)\b)([a-zäöüß]\S*)")
UNSICHTBAR = "­​‌‍⁠﻿"   # weiches Trennzeichen, Nullbreiten
UMLAUTE = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"))
SCHRANKE = "\x00"        # trennt Wortfolgen, die im Entwurf nicht zusammenhängen
# Zitierkürzel aus Paragrafen- und Normketten (nach der Normalisierung). Sie zählen wie
# Ziffern und einzelne Buchstaben nicht als Wörter – im Entwurf wie in der Bibliothek.
KUERZEL = ("abb", "abs", "abschn", "aufl", "ber", "bgb", "bl", "din", "en", "ff", "hoai", "hrsg", "hs",
           "iec", "iso", "kap", "lit", "nr", "nrn", "rdn", "rn", "rz", "satz", "spec", "tab", "ts", "vde",
           "vdi", "vgl", "vob", "ziff", "zpo")
# Ein Wort: mindestens zwei Buchstaben, keine Ziffer daran, kein Zitierkürzel.
WORT = re.compile(r"(?<![0-9a-z])(?!(?:" + "|".join(KUERZEL) + r")(?![0-9a-z]))[a-z]{2,}(?![0-9a-z])|\x00")


def normalisieren(text: str) -> str:
    """NFKC, Silbentrennung zusammenführen, weiches Trennzeichen weg, casefold, ä → ae usw."""
    text = TRENNUNG.sub(r"\1\n", unicodedata.normalize("NFKC", text))
    # str.replace statt str.translate: bei 90 MB Buchtext um ein Vielfaches schneller
    for zeichen in UNSICHTBAR:
        if zeichen in text:
            text = text.replace(zeichen, "")
    text = text.casefold()
    for alt, neu in UMLAUTE:
        if alt in text:
            text = text.replace(alt, neu)
    return text


def seitenende_getrennt(text: str) -> bool:
    """Endet die Seite mit einem getrennten Wort („Abdich-“)?"""
    ende = text.rstrip()
    return len(ende) >= 2 and ende[-1] in TRENNSTRICHE and ende[-2].isalpha()


def woerter(text: str) -> list[str]:
    return WORT.findall(normalisieren(text))


def ngramme(folge: list[str], n: int) -> list[tuple | None]:
    """Alle Wortfolgen der Länge n; None, wo eine Folge über eine Schranke reichen würde."""
    return [None if SCHRANKE in ng else ng for ng in zip(*(folge[k:] for k in range(n)))]


# ---------------------------------------------------------------------------
# Entwurf lesen
# ---------------------------------------------------------------------------

FUSSNOTENMARKE = re.compile(r"\[\^[^\]\s]+\]:?")
FUSSNOTENZEILE = re.compile(r"^\s*\[\^[^\]\s]+\]:")
BILD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]*)\]\([^)\s]*(?:\s+\"[^\"]*\")?\)")
ADRESSE = re.compile(r"<?https?://[^\s<>)\]]+>?|\bwww\.[^\s<>)\]]+")
HTML_TAG = re.compile(r"</?[A-Za-z][^<>\n]*>")
HTML_GRAFIK = re.compile(r"<\s*(img|svg|figure)\b", re.I)
TABELLENZEILE = re.compile(r"^\s*\|")
BLOCKANFANG = re.compile(r"^\s*(?:#|[-*+]\s|>|\||\[\^|\d+[.)]\s)")
# Normnummer mit Ausgabe: DIN 4109-1:2018-01, DIN EN 1992-1-1:2011-01, VDI 6202 Blatt 1:2013-10
NORMNUMMER = (r"(?:DIN|VDI|VDE)(?:[ /-][A-Z]{1,8})*[ ]?\d[\w./-]*"
              r"(?:[ ](?:Blatt|Beiblatt|Teil|Berichtigung)[ ]?\d+)*"
              r"(?::[ ]?\d{4}(?:-\d{2})?|[ ]\(\d{4}-\d{2}\)|[ ][–-][ ]\d{4}-\d{2})")
# Titel in „…“ direkt hinter Nummer und Ausgabe: DIN 4109-1:2018-01 „Titel“
NORMTITEL = re.compile("(" + NORMNUMMER + r")[ \t]*,?[ \t]*"
                       r"(„[^“”\n]*[“”]|“[^”\n]*”|»[^«\n]*«|\"[^\"\n]*\")")
# In Fußnoten auch ohne Anführungszeichen: DIN 4109-1:2018-01, Titel. – bis zum Satzende oder zur Adresse
NORMTITEL_FUSSNOTE = re.compile("(" + NORMNUMMER + r")[ \t]*[,:–—-][ \t]*(?![„“»\"\s])"
                                r"([^\n]*?)(?=\.(?:\s|$)|<?https?://|\bwww\.|$)")
SATZENDE = re.compile(r"[.!?](?=\s|[“”\"«]|$)")
# Satzwörter (normalisiert): Verben, Pronomen und Konjunktionen eines Satzes. Ein Normtitel
# enthält sie nicht, eine Anforderung oder ein Buchsatz in Anführungszeichen schon.
SATZWOERTER = frozenset((
    "ist", "sind", "war", "waren", "wird", "werden", "wurde", "wurden", "worden", "sei", "seien",
    "muss", "muessen", "musste", "mussten", "darf", "duerfen", "durfte", "durften", "kann", "koennen",
    "konnte", "konnten", "soll", "sollen", "sollte", "sollten", "hat", "haben", "hatte", "hatten",
    "gilt", "gelten", "galt", "betraegt", "betragen", "liegt", "liegen", "erfolgt", "erfolgen",
    "ergibt", "bedarf", "genuegt", "reicht", "bleibt", "bleiben", "entspricht", "entsprechen",
    "erfordert", "handelt", "gibt", "geht", "steht", "stehen", "kommt", "zeigt", "zeigen", "bedeutet",
    "heisst", "beschreibt", "regelt", "verlangt", "fordert", "empfiehlt", "es", "sich", "man", "er",
    "sie", "wir", "ihr", "dass", "weil", "wenn", "ob", "damit", "jedoch", "nicht", "kein", "keine",
    "is", "are", "was", "were", "shall", "must", "should", "may", "will", "has", "have", "be", "it",
    "they", "we", "not"))
ERSTE_ZWISCHENUEBERSCHRIFT = "(vor der ersten Zwischenüberschrift)"
YAML_SCHLUESSEL = re.compile(r"^(\s*)(?:-\s+)?([A-Za-z_][\w-]*):(?:[ \t]+|$)(.*)$")
YAML_BLOCKTEXT = re.compile(r"[|>][+-]?\d*")


def titel_plausibel(text: str) -> bool:
    """Sieht der Text hinter einer Normnummer wie ein Normtitel aus – oder wie ein Satz aus der Norm?"""
    if SATZENDE.search(text):
        return False
    gezaehlt = [w for w in woerter(text) if w != SCHRANKE]
    return len(gezaehlt) <= TITEL_HOECHSTENS and not SATZWOERTER.intersection(gezaehlt)


def normtitel_ausblenden(zeile: str) -> str:
    """Normtitel nur in Fußnoten ausblenden – im Fließtext wird alles geprüft, auch Titel in „…“."""
    if not FUSSNOTENZEILE.match(zeile):
        return zeile

    def ersetzen(m: re.Match) -> str:
        return f"{m.group(1)} {SCHRANKE} " if titel_plausibel(m.group(2)) else m.group(0)

    return NORMTITEL_FUSSNOTE.sub(ersetzen, NORMTITEL.sub(ersetzen, zeile))


def zeile_bereinigen(zeile: str) -> str:
    """Entfernt Auszeichnung, die nicht veröffentlichter Fließtext ist."""
    zeile = normtitel_ausblenden(zeile)
    zeile = BILD.sub(f" {SCHRANKE} ", zeile)
    zeile = LINK.sub(r"\1", zeile)
    zeile = ADRESSE.sub(f" {SCHRANKE} ", zeile)
    zeile = FUSSNOTENMARKE.sub(" ", zeile)
    zeile = HTML_TAG.sub(" ", zeile)
    return html.unescape(zeile)


def yaml_wert(wert: str, liste: bool = False) -> str:
    """Wert einer YAML-Zeile ohne Anführungszeichen; Listenelemente durch Schranken getrennt."""
    wert = wert.strip()
    if wert.startswith("[") and wert.endswith("]"):
        wert, liste = wert[1:-1], True
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "'\"":
        wert = wert[1:-1]
    if liste:
        wert = f" {SCHRANKE} ".join(teil.strip().strip("'\"") for teil in wert.split(","))
    return wert


def yaml_lesen(zeilen: list[str], felder: set[str] | None) -> list[tuple[str, bool, str]]:
    """Je Zeile: zu prüfender Text, ob dort ein neuer Block beginnt, und das Feld.

    felder=None: alle Felder (Vorlagen-Beschreibung); sonst nur die genannten (Dateikopf).
    Jedes Feld und jedes Listenelement ist ein eigener Block; Blocktexte (| oder >) und
    mehrzeilige Werte bleiben zusammenhängend.
    """
    ergebnis: list[tuple[str, bool, str]] = []
    feld, aktiv, block_einzug = "", False, None
    for zeile in zeilen:
        einzug = len(zeile) - len(zeile.lstrip())
        inhalt = zeile.strip()
        if block_einzug is not None and (not inhalt or einzug > block_einzug):
            # Zeile eines Blocktexts – Inhalt, auch wenn ein Doppelpunkt darin steht
            ergebnis.append((inhalt if aktiv else "", False, feld))
            continue
        block_einzug = None
        if not inhalt or inhalt.startswith("#") or inhalt in ("---", "..."):
            ergebnis.append(("", True, feld))
            continue
        m = YAML_SCHLUESSEL.match(zeile)
        if m:
            feld = m.group(2)
            aktiv = felder is None or feld in felder
            wert = m.group(3).strip()
            if YAML_BLOCKTEXT.fullmatch(wert):
                block_einzug, wert = einzug, ""
            ergebnis.append((yaml_wert(wert, feld == "schlagwoerter") if aktiv else "", True, feld))
        elif inhalt == "-" or inhalt.startswith("- "):
            ergebnis.append((yaml_wert(inhalt[1:]) if aktiv else "", True, feld))
        else:                            # Fortsetzung eines mehrzeiligen Werts
            ergebnis.append((yaml_wert(inhalt, feld == "schlagwoerter") if aktiv else "", False, feld))
    return ergebnis


def entwurf_lesen(pfad: Path, n: int) -> dict:
    """Wörter mit Zeilennummer, Abschnitt je Zeile, Bilder und Tabellen eines Entwurfs."""
    zeilen = pfad.read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
    yml = pfad.suffix.lower() in (".yml", ".yaml")
    ende_kopf = 0
    if not yml and zeilen and zeilen[0].strip() == "---":
        ende_kopf = next((i + 1 for i in range(1, len(zeilen)) if zeilen[i].strip() == "---"), 0)
    # Dateikopf: nur die veröffentlichten Felder; Vorlagen-Beschreibung: alle Textfelder
    yaml_teil = yaml_lesen(zeilen, None) if yml else yaml_lesen(zeilen[:ende_kopf], set(KOPFFELDER))
    abschnitte, h2_zeile, bereinigt, neuer_block, bilder, tabellen = [], [], [], [], [], []
    ueberschriften: set[int] = set()
    abschnitt, abschnitt_nr = ERSTE_ZWISCHENUEBERSCHRIFT, 0
    for nr, zeile in enumerate(zeilen, 1):
        if yml or nr <= ende_kopf:
            text, anfang, feld = yaml_teil[nr - 1]
            ort = "Vorlage" if yml else "Dateikopf"
            abschnitte.append(f"({ort}: {feld})" if feld else f"({ort})")
            h2_zeile.append(0)
            bereinigt.append(zeile_bereinigen(text) if text else "")
            neuer_block.append(anfang)
            continue
        if zeile.startswith("## "):
            abschnitt, abschnitt_nr = zeile[3:].strip(), nr
            ueberschriften.add(nr)
        abschnitte.append(abschnitt)
        h2_zeile.append(abschnitt_nr)
        bilder += [(nr, "Markdown-Bild") for _ in BILD.finditer(zeile)]
        bilder += [(nr, f"HTML-Grafik <{m.group(1).lower()}>") for m in HTML_GRAFIK.finditer(zeile)]
        if TABELLENZEILE.match(zeile):
            tabellen.append(nr)
        bereinigt.append(zeile_bereinigen(zeile))
        neuer_block.append(bool(BLOCKANFANG.match(zeile)))

    normal = normalisieren("\n".join(bereinigt)).split("\n")
    if len(normal) != len(bereinigt):    # Sicherheitsnetz, falls ein Zeichen Zeilen verschiebt
        normal = [normalisieren(z) for z in bereinigt]
    # Zwischen Absätzen, Überschriften, Listenpunkten, Fußnoten und Feldern eine Schranke: Sonst
    # entstünden Wortfolgen, die so nirgends stehen (Ende einer Fußnote + Anfang der nächsten).
    folge, zeile_je_wort = [], []
    vorher_leer = vorher_ueberschrift = True
    for nr, zeile in enumerate(normal, 1):
        roh = zeilen[nr - 1]
        if (vorher_leer or vorher_ueberschrift or neuer_block[nr - 1]) and folge and folge[-1] != SCHRANKE:
            folge.append(SCHRANKE)
            zeile_je_wort.append(nr)
        for wort in WORT.findall(zeile):
            folge.append(wort)
            zeile_je_wort.append(nr)
        vorher_leer = not bereinigt[nr - 1].strip()
        vorher_ueberschrift = not yml and nr > ende_kopf and roh.lstrip().startswith("#")
    return {"pfad": pfad, "name": pfad.as_posix(), "woerter": folge, "zeilen": zeile_je_wort,
            "abschnitte": abschnitte, "h2_zeile": h2_zeile, "ueberschriften": ueberschriften,
            "bilder": bilder, "tabellen": tabellen, "ngramme": ngramme(folge, n)}


# ---------------------------------------------------------------------------
# Bibliothek lesen
# ---------------------------------------------------------------------------

TRENNLINIE = re.compile(r"^={10,}[ \t]*$", re.M)
ZUSATZ_TRENNLINIE = re.compile(r"^-{10,}[ \t]*$", re.M)
SEITENZAHL = re.compile(r"(?:\d{1,4}|[ivxlcdm]{1,7})", re.I)
# Amtliche Seiten (§ 5 UrhG): Gesetze und Entscheidungen dürfen kurz wörtlich zitiert werden.
AMTLICHE_ADRESSEN = ("gesetze", "landesrecht", "rechtsprechung", "justiz", "gerichtsentscheidungen",
                     "bundesgerichtshof", "bundesverfassungsgericht", "bverwg", "bundesverwaltungsgericht",
                     "bundesfinanzhof", "bundessozialgericht", "bsg.bund", "bundesarbeitsgericht",
                     "recht.bund.de", "bgbl", "eur-lex.europa.eu", "curia.europa.eu", "openjur", "dejure",
                     "buzer", "hessenrecht", "bravors", "revosax", "voris", "recht.nrw")


class NichtGeprueft(Exception):
    """Die Prüfung war nicht möglich – der Entwurf gilt als nicht geprüft."""


def seiten(inhalt: str):
    """(gedruckte Seite, PDF-Seite, Text) je Seite – ohne die Kopfzeilen bis zur Trennlinie."""
    koepfe = list(KOPF.finditer(inhalt))
    erster = koepfe[0].start() if koepfe else len(inhalt)
    linie = TRENNLINIE.search(inhalt, 0, erster)
    start = linie.end() if linie else 0
    if inhalt[start:erster].strip():
        yield "", 0, inhalt[start:erster]
    for i, kopf in enumerate(koepfe):
        ende = koepfe[i + 1].start() if i + 1 < len(koepfe) else len(inhalt)
        yield kopf.group(1), int(kopf.group(2)), inhalt[kopf.end():ende]


def raender_entfernen(seitenliste: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    """Entfernt am Seitenrand gedruckte Seitenzahlen und wiederkehrende Kopf- und Fußzeilen.

    Sonst stünden sie zwischen dem Ende einer Seite und dem Anfang der nächsten, und eine
    Wortfolge über die Seitengrenze würde nicht gefunden. Als Rand gelten die ersten und
    letzten zwei Zeilen mit Text; wiederkehrend ist eine Randzeile, die (Ziffern gleichgesetzt)
    am Rand von mindestens drei Seiten steht.
    """
    def schluessel(zeile: str) -> str:
        return re.sub(r"\d+", "#", " ".join(zeile.split())).casefold()

    raender, zaehler = [], Counter()
    for _, _, text in seitenliste:
        zeilen = text.split("\n")
        mit_text = [i for i, z in enumerate(zeilen) if z.strip()]
        rand = set(mit_text[:2] + mit_text[-2:])
        raender.append((zeilen, rand))
        zaehler.update({schluessel(zeilen[i]) for i in rand})
    haeufig = {k for k, v in zaehler.items() if v >= 3}
    ergebnis = []
    for (seite, pdf, text), (zeilen, rand) in zip(seitenliste, raender):
        weg = {i for i in rand if SEITENZAHL.fullmatch(zeilen[i].strip()) or schluessel(zeilen[i]) in haeufig}
        if weg:
            text = "\n".join(z for i, z in enumerate(zeilen) if i not in weg)
        ergebnis.append((seite, pdf, text))
    return ergebnis


def zusatz_lesen(datei: Path) -> tuple[str, str] | None:
    """(Werk-Kennung, Text) eines heruntergeladenen Quelltexts von tools/quellen_laden.py –
    None für amtliche Seiten und für Buchseiten aus der Fachbibliothek (die prüft der Korpus)."""
    inhalt = datei.read_text(encoding="utf-8", errors="replace")
    linie = ZUSATZ_TRENNLINIE.search(inhalt)
    kopf, text = (inhalt[:linie.start()], inhalt[linie.end():]) if linie else ("", inhalt)
    if "Fachbibliothek" in kopf:
        return None
    adresse = re.search(r"(?m)^Adresse:\s*(\S+)", kopf)
    host = urllib.parse.urlsplit(adresse.group(1)).hostname or "" if adresse else ""
    if any(teil in host for teil in AMTLICHE_ADRESSEN):
        return None
    return f"Webquelle {datei.stem.upper()}" + (f" ({host})" if host else ""), text


RAND_ENDE = 6            # so viele Zeilen am Seitenende dürfen Fußnoten oder Fußzeilen sein
RAND_ANFANG = 2          # so viele Zeilen am Seitenanfang dürfen Kopfzeilen sein


def woerter_je_zeile(zeilen: list[str]) -> list[list[str]]:
    """Wörter je Zeile, mit einer Normalisierung für alle Zeilen (die Zeilenzahl bleibt gleich)."""
    normal = normalisieren("\n".join(zeilen)).split("\n")
    if len(normal) != len(zeilen):
        normal = [normalisieren(z) for z in zeilen]
    return [WORT.findall(z) for z in normal]


def seitenenden(zeilen: list[str], n: int) -> list[tuple[list[str], bool]]:
    """Mögliche Enden einer Seite für die Folge über die Seitengrenze: die letzten n-1 Wörter,
    ohne 0 bis RAND_ENDE Schlusszeilen (Fußnoten, Fußzeile), und ob dort ein Wort getrennt ist."""
    bereich = zeilen[-(RAND_ENDE + 8):]
    je_zeile = woerter_je_zeile(bereich)
    enden = []
    for weg in range(min(RAND_ENDE, len(bereich) - 1) + 1):
        bis = len(bereich) - weg
        folge = [w for liste in je_zeile[max(0, bis - 8):bis] for w in liste]
        enden.append((folge[-(n - 1):], seitenende_getrennt(bereich[bis - 1])))
    return enden


def seitenanfaenge(zeilen: list[str], n: int) -> list[tuple[list[str], bool]]:
    """Mögliche Anfänge der Folgeseite: die ersten n-1 Wörter ohne 0 bis RAND_ANFANG Kopfzeilen,
    und ob der Text klein beginnt (Fortsetzung eines getrennten Wortes)."""
    bereich = zeilen[:RAND_ANFANG + 8]
    je_zeile = woerter_je_zeile(bereich)
    anfaenge = []
    for weg in range(min(RAND_ANFANG, len(bereich) - 1) + 1):
        folge = [w for liste in je_zeile[weg:weg + 8] for w in liste]
        anfaenge.append((folge[:n - 1], bereich[weg].lstrip()[:1].islower()))
    return anfaenge


def durchsuchen(dateien: list[Path], gesucht: set, n: int, zusatz: bool = False) -> dict:
    """Liest jede Datei einmal und merkt, wo Wortfolgen aus `gesucht` vorkommen.

    Ergebnis: {Wortfolge: {Werk: (Seite, PDF, Seite am Folgenende, PDF am Folgenende)}},
    je Werk die erste Fundstelle. Folgen über eine Seitengrenze werden ebenfalls gefunden:
    Ende der einen und Anfang der nächsten Seite werden aneinandergehängt – auch ohne die
    letzten Zeilen (Fußnoten, Fußzeile) und ohne die ersten (Kopfzeile), die
    raender_entfernen nicht als wiederkehrend erkannt hat.
    zusatz=True: heruntergeladene Quelltexte (ohne Seiten) statt Werktexten der Bibliothek.
    """
    fund: dict = {}
    if not gesucht:
        return fund

    def merken(ng: tuple, werk: str, anfang: tuple, ende: tuple) -> None:
        stellen = fund.setdefault(ng, {})
        if werk not in stellen:
            stellen[werk] = (*anfang, *ende)

    for datei in dateien:
        if zusatz:
            gelesen = zusatz_lesen(datei)
            if gelesen is None:
                continue
            werk, text = gelesen
            seitenliste = [("", 0, text)]
        else:
            werk = datei.stem
            seitenliste = raender_entfernen(list(seiten(datei.read_text(encoding="utf-8", errors="replace"))))
        vorige: tuple | None = None              # (Seite, PDF, mögliche Seitenenden) der vorigen Seite
        for seite, pdf, text in seitenliste:
            neu = woerter(text)
            if len(neu) >= n and not gesucht.isdisjoint(zip(*(neu[k:] for k in range(n)))):
                for ng in zip(*(neu[k:] for k in range(n))):
                    if ng in gesucht:
                        merken(ng, werk, (seite, pdf), (seite, pdf))
            zeilen = [z for z in text.split("\n") if z.strip()]
            if not zeilen:
                continue
            if vorige is not None:
                v_seite, v_pdf, enden = vorige
                anfaenge = seitenanfaenge(zeilen, n)
                for ende, getrennt in enden:
                    for anfang, klein in anfaenge:
                        if not ende or not anfang:
                            continue
                        if getrennt and klein:   # „Abdich-“ | „tung“ über die Seitengrenze
                            folge = ende[:-1] + [ende[-1] + anfang[0]] + anfang[1:]
                            grenze = len(ende) - 1       # das zusammengesetzte Wort gehört zu beiden Seiten
                            letzter_anfang = grenze
                        else:
                            folge, grenze = ende + anfang, len(ende)
                            letzter_anfang = grenze - 1
                        # nur Folgen, die vor der Grenze beginnen und dahinter enden
                        for i in range(max(0, grenze - n + 1), letzter_anfang + 1):
                            ng = tuple(folge[i:i + n])
                            if len(ng) == n and ng in gesucht:
                                merken(ng, werk, (v_seite, v_pdf),
                                       (seite, pdf) if i + n > grenze else (v_seite, v_pdf))
            vorige = (seite, pdf, seitenenden(zeilen, n))
    return fund


def katalog_eintraege(bibliothek: Path) -> list[dict]:
    """Einträge aller katalog.yml der Bibliothek (Bücher, Forschung, Webquellen, amtliche Werke)."""
    try:
        import yaml  # im Workflow installiert
        eintraege = []
        for datei in [bibliothek / "katalog.yml", *sorted(bibliothek.glob("*/katalog.yml"))]:
            if datei.exists():
                inhalt = yaml.safe_load(datei.read_text(encoding="utf-8")) or []
                if isinstance(inhalt, list):
                    eintraege += [e for e in inhalt if isinstance(e, dict)]
        return eintraege
    except Exception as fehler:  # noqa: BLE001 – jede Störung heißt: nicht geprüft
        raise NichtGeprueft(f"Katalog unlesbar ({type(fehler).__name__})") from fehler


def erlaubte_wendungen(pfad: Path) -> list[str]:
    if not pfad.exists():
        return []
    return [z.strip() for z in pfad.read_text(encoding="utf-8").splitlines()
            if z.strip() and not z.lstrip().startswith("#")]


def familien(eintraege: list[dict]) -> tuple[dict[str, str], set[str]]:
    """Ordnet jede Auflage ihrer neuesten zu (ersetzt_durch), damit Auflagen eines Buches
    beim Zählen der Werke nur einmal zählen. Dazu die Menge der ersetzten Auflagen."""
    nachfolger = {str(e["kennung"]): str(e.get("ersetzt_durch") or "") for e in eintraege
                  if e.get("kennung")}

    def neueste(kennung: str) -> str:
        gesehen = set()
        while nachfolger.get(kennung) and kennung not in gesehen:
            gesehen.add(kennung)
            kennung = nachfolger[kennung]
        return kennung

    return {k: neueste(k) for k in nachfolger}, {k for k, v in nachfolger.items() if v}


# ---------------------------------------------------------------------------
# Prüfen und auswerten
# ---------------------------------------------------------------------------

def strecken(positionen: list[int], n: int) -> list[list[int]]:
    """Fasst Fundstellen, deren Wortfolgen sich überlappen, zu maximalen Strecken zusammen."""
    ergebnis: list[list[int]] = []
    for p in positionen:
        if ergebnis and p <= ergebnis[-1][1] + n - 1:
            ergebnis[-1][1] = p
        else:
            ergebnis.append([p, p])
    return ergebnis


def vermerk(werke: int) -> str:
    if werke >= VIELE_WERKE:
        return (f"kommt in {werke} Werken vor – vermutlich Gesetzes-, VOB- oder Normwortlaut; "
                "Freigabe nur durch den Inhaber")
    if werke == 2:
        return "kommt in 2 Werken vor – in eigenen Worten fassen"
    return "in eigenen Worten fassen, Fundstelle angeben"


def auswerten(entwurf: dict, fund: dict, n: int, familie: dict, ersetzt: set,
              reihenfolge: dict, frei: set | None = None) -> tuple[list[dict], list[dict]]:
    """Treffer und Hinweise eines Entwurfs – nur Ortsangaben, kein Text."""
    treffer, hinweise = [], []
    ngr = entwurf["ngramme"]
    # Von Freigaben (amtlicher Wortlaut, Werktitel, Wendungsliste) gedeckte Wörter des Entwurfs
    gedeckt = [False] * len(entwurf["woerter"])
    for i, ng in enumerate(ngr):
        if ng is not None and frei and ng in frei:
            gedeckt[i:i + n] = [True] * n
    positionen = [i for i, ng in enumerate(ngr) if ng is not None and ng in fund]
    for anfang, ende in strecken(positionen, n):
        if sum(not gedeckt[p] for p in range(anfang, ende + n)) <= RANDWOERTER:
            continue                     # freigegebener Wortlaut mit einem oder zwei Randwörtern
        folgen = [ngr[p] for p in positionen if anfang <= p <= ende]
        abdeckung: dict[str, int] = {}
        for ng in folgen:
            for werk in fund[ng]:
                abdeckung[werk] = abdeckung.get(werk, 0) + 1
        # Zahl der Werke, in denen die ganze Folge vorkommen kann: das seltenste Stück zählt
        werke = min(len({familie.get(w, w) for w in fund[ng]}) for ng in folgen)
        werk = max(abdeckung, key=lambda w: (abdeckung[w], w not in ersetzt, -reihenfolge.get(w, 0)))
        im_werk = [ng for ng in folgen if werk in fund[ng]]
        seite, pdf, _, _ = fund[im_werk[0]][werk]
        _, _, seite_ende, pdf_ende = fund[im_werk[-1]][werk]
        if seite_ende and seite_ende != seite and 0 < pdf_ende - pdf <= 3:
            seite = f"{seite}–{seite_ende}"
        zeile = entwurf["zeilen"][anfang]
        treffer.append({"datei": entwurf["name"], "abschnitt": entwurf["abschnitte"][zeile - 1],
                        "zeile": zeile, "laenge": ende - anfang + n, "werk": werk,
                        "seite": seite or "?", "werke": werke, "art": "Wortfolge",
                        "vermerk": vermerk(werke)})
    for zeile, art in entwurf["bilder"]:
        treffer.append({"datei": entwurf["name"], "abschnitt": entwurf["abschnitte"][zeile - 1],
                        "zeile": zeile, "laenge": None, "werk": None, "seite": None, "werke": None,
                        "art": "Abbildung",
                        "vermerk": f"{art} im Entwurf – Abbildungen nicht übernehmen, nur eigene Grafiken "
                                   "nach Freigabe des Inhabers"})
    treffer.sort(key=lambda t: t["zeile"])
    # Tabellen: zusammenhängende Tabellenzeilen als ein Hinweis
    gruppen: list[list[int]] = []
    for nr in entwurf["tabellen"]:
        if gruppen and nr == gruppen[-1][-1] + 1:
            gruppen[-1].append(nr)
        else:
            gruppen.append([nr])
    for gruppe in gruppen:
        hinweise.append({"datei": entwurf["name"], "abschnitt": entwurf["abschnitte"][gruppe[0] - 1],
                         "zeile": gruppe[0], "art": "Tabelle", "zeilen": len(gruppe),
                         "vermerk": f"Hinweis: Tabelle mit {len(gruppe)} Zeilen – eigene Tabellen sind erlaubt, "
                                    "übernommene nicht"})
    # Steht ein Treffer in einer Zwischenüberschrift selbst, darf ihr Wortlaut nirgends erscheinen.
    betroffen = {t["zeile"] for t in treffer if t["zeile"] in entwurf["ueberschriften"]}
    for eintrag in treffer + hinweise:
        h2 = entwurf["h2_zeile"][eintrag["zeile"] - 1]
        if h2 in betroffen:
            eintrag["abschnitt"] = f"(Abschnitt ab Zeile {h2} – Überschrift selbst betroffen)"
    return treffer, hinweise


def pruefen(dateien: list[Path], bibliothek: Path | None, n: int, zusatz: list[Path] | None = None) -> dict:
    """Prüft alle Entwürfe gegen die Bibliothek; die Bibliothek wird nur einmal gelesen."""
    if bibliothek is None or not bibliothek.is_dir():
        raise NichtGeprueft("Ordner der Fachbibliothek fehlt")
    korpus = [d for teil in KORPUS for d in sorted((bibliothek / teil / "texte").glob("*.txt"))]
    if not korpus:
        raise NichtGeprueft("keine Werktexte (texte/*.txt) in der Fachbibliothek")
    webtexte = [d for ordner in (zusatz or []) if ordner.is_dir() for d in sorted(ordner.glob("*.txt"))]
    entwuerfe = [entwurf_lesen(p, n) for p in dateien]
    gesucht = {ng for e in entwuerfe for ng in e["ngramme"] if ng is not None}

    eintraege = katalog_eintraege(bibliothek)
    amtlich = sorted((bibliothek / AMTLICH / "texte").glob("*.txt"))
    try:
        # Freigaben: amtliche Werke, Werktitel aus den Katalogen, Wendungsliste des Inhabers
        frei = set(durchsuchen(amtlich, gesucht, n))
        for eintrag in eintraege:
            for feld in ("zitat", "titel", "untertitel"):
                if isinstance(eintrag.get(feld), str):
                    frei.update(ng for ng in ngramme(woerter(eintrag[feld]), n) if ng in gesucht)
        for wendung in erlaubte_wendungen(ERLAUBT):
            frei.update(ng for ng in ngramme(woerter(wendung), n) if ng in gesucht)
        gesucht -= frei
        fund = durchsuchen(korpus, gesucht, n)
        for ng, stellen in durchsuchen(webtexte, gesucht, n, zusatz=True).items():
            fund.setdefault(ng, {}).update(stellen)
    except (OSError, UnicodeDecodeError) as fehler:
        raise NichtGeprueft(f"Datei der Fachbibliothek unlesbar ({type(fehler).__name__})") from fehler

    familie, ersetzt = familien(eintraege)
    reihenfolge = {d.stem: i for i, d in enumerate(korpus)}
    treffer, hinweise = [], []
    for entwurf in entwuerfe:
        t, h = auswerten(entwurf, fund, n, familie, ersetzt, reihenfolge, frei)
        treffer += t
        hinweise += h
    return {"geprueft": True, "grenze": n, "werke": len(korpus), "amtliche_texte": len(amtlich),
            "webquellen": len(webtexte), "entwuerfe": [e["name"] for e in entwuerfe], "freigegeben": len(frei),
            "anzahl_treffer": len(treffer), "anzahl_hinweise": len(hinweise),
            "treffer": treffer, "hinweise": hinweise}


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def zelle(wert) -> str:
    return "–" if wert in (None, "") else str(wert).replace("|", "\\|")


def oeffentlich(eintrag: dict) -> dict:
    """Ein Treffer oder Hinweis ohne alles, was auf die Quelle schließen lässt (Werk, Seite, Zahl der Werke).

    Wortfolgen bekommen den neutralen Vermerk; Abbildungen und Tabellen behalten ihren, er nennt keine Quelle.
    """
    sicher = {s: eintrag.get(s) for s in ("datei", "abschnitt", "zeile", "laenge", "art")}
    sicher["vermerk"] = NEUTRAL if eintrag.get("art") == "Wortfolge" else eintrag.get("vermerk")
    return sicher


def bericht_bilden(ergebnis: dict, intern: bool = False) -> str:
    """Markdown-Bericht. Ohne `intern` ohne Werk, Seite und Zahl der Werke (öffentliche Stellen)."""
    zeilen = [UEBERSCHRIFT, ""]
    if not ergebnis["geprueft"]:
        zeilen += [ergebnis["meldung"], ""]
        if ergebnis.get("grund"):
            zeilen += [f"Grund: {ergebnis['grund']}.", ""]
        return "\n".join(zeilen)
    if intern:
        zeilen += [f"> {INTERN_WARNUNG}", ""]
    web = f", {ergebnis['webquellen']} heruntergeladene Quelltexte" if ergebnis.get("webquellen") else ""
    zeilen += [f"Geprüft gegen: {ergebnis['werke']} Werke, {ergebnis['amtliche_texte']} amtliche Texte{web}, "
               f"Grenze {ergebnis['grenze']} Wörter", ""]
    if intern:
        spalten = ("datei", "abschnitt", "zeile", "laenge", "werk", "seite", "vermerk")
        kopf = ["| Datei | Abschnitt | Zeile | Länge (Wörter) | Werk | Seite | Vermerk |",
                "|---|---|---|---|---|---|---|"]
    else:
        spalten = ("datei", "abschnitt", "zeile", "laenge", "vermerk")
        kopf = ["| Datei | Abschnitt | Zeile | Länge (Wörter) | Vermerk |",
                "|---|---|---|---|---|"]

    def tabellenzeile(e: dict) -> str:
        e = e if intern else oeffentlich(e)
        return "| " + " | ".join(zelle(e.get(s)) for s in spalten) + " |"

    if ergebnis["treffer"]:
        zeilen += kopf + [tabellenzeile(t) for t in ergebnis["treffer"] + ergebnis["hinweise"]]
        zeilen += ["", SCHLUSS_INTERN if intern else SCHLUSS_OEFFENTLICH]
    else:
        zeilen.append("Keine wörtlichen Übernahmen gefunden.")
        if ergebnis["hinweise"]:
            zeilen += ["", "Hinweise (keine Sperre):", ""] + kopf + [tabellenzeile(h) for h in ergebnis["hinweise"]]
    return "\n".join(zeilen) + "\n"


def schreiben(pfad: Path | None, inhalt: str) -> None:
    if pfad:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(inhalt, encoding="utf-8", newline="\n")


def main() -> int:
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, "reconfigure"):
            strom.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("entwuerfe", nargs="+", type=Path)
    parser.add_argument("--bibliothek", type=Path)
    parser.add_argument("--zusatz", type=Path, action="append", default=[],
                        help="Ordner mit Quelltexten von tools/quellen_laden.py (amtliche Seiten ausgenommen)")
    parser.add_argument("--grenze", type=int, default=GRENZE)
    parser.add_argument("--bericht", type=Path)
    parser.add_argument("--json", type=Path, help="vollständiges Ergebnis mit Werk und Seite (nur Runner-Temp)")
    parser.add_argument("--intern", action="store_true",
                        help="Ausgabe und Bericht mit Werk, Seite und Zahl der Werke – nur zur eigenen "
                             "Überarbeitung, nie in öffentliche Kommentare, PR-Texte oder Logs")
    args = parser.parse_args()

    beginn = time.monotonic()
    entwurf_fehler = "Nicht geprüft: Entwurf nicht lesbar – Entwurf bleibt gesperrt."
    fehlt = [p.as_posix() for p in args.entwuerfe if not p.is_file()]
    if fehlt:
        ergebnis = {"geprueft": False, "meldung": entwurf_fehler, "grund": "fehlt: " + ", ".join(fehlt)}
    else:
        try:
            if args.grenze < 3:
                raise NichtGeprueft("Grenze unter 3 Wörtern ist nicht sinnvoll")
            ergebnis = pruefen(args.entwuerfe, args.bibliothek, args.grenze, args.zusatz)
        except NichtGeprueft as fehler:
            ergebnis = {"geprueft": False, "meldung": NICHT_GEPRUEFT, "grund": str(fehler)}
        except (OSError, UnicodeDecodeError) as fehler:
            ergebnis = {"geprueft": False, "meldung": entwurf_fehler, "grund": type(fehler).__name__}

    schreiben(args.bericht, bericht_bilden(ergebnis, args.intern))
    schreiben(args.json, json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n")
    if not ergebnis["geprueft"]:
        print(f"{ergebnis['meldung']} ({ergebnis['grund']})")
        print("treffer=nicht-geprueft")
        return 2

    anzahl = len(ergebnis["entwuerfe"])
    web = f", {ergebnis['webquellen']} Quelltexte" if ergebnis.get("webquellen") else ""
    print(f"Wortgleich-Prüfung: {anzahl} {'Entwurf' if anzahl == 1 else 'Entwürfe'} gegen "
          f"{ergebnis['werke']} Werke und {ergebnis['amtliche_texte']} amtliche Texte{web}, "
          f"Grenze {ergebnis['grenze']} Wörter, {ergebnis['freigegeben']} Wortfolgen freigegeben, "
          f"{time.monotonic() - beginn:.1f} s.")
    if args.intern:
        print(INTERN_WARNUNG)
    for name in ergebnis["entwuerfe"]:
        eigene = [t for t in ergebnis["treffer"] if t["datei"] == name]
        hinweise = [h for h in ergebnis["hinweise"] if h["datei"] == name]
        print(f"{name}: {len(eigene)} Treffer, {len(hinweise)} Hinweise")
        for t in eigene + hinweise:
            ort = f"  Zeile {t['zeile']} · {t['abschnitt']}"
            if t.get("art") == "Wortfolge" and args.intern:
                print(f"{ort} · {t['laenge']} Wörter · {t['werk']} S. {t['seite']} · {t['vermerk']}")
            elif t.get("art") == "Wortfolge":
                print(f"{ort} · {t['laenge']} Wörter · {NEUTRAL}")
            else:
                print(f"{ort} · {t['vermerk']}")
    print(f"treffer={ergebnis['anzahl_treffer']}")
    return 1 if ergebnis["anzahl_treffer"] else 0


if __name__ == "__main__":
    sys.exit(main())
