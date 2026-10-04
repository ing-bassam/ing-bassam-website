"""Leistungsseiten des Büros und ihre Zuordnung zu den Fachbeiträgen.

Eine Stelle für alles, was mehrere Werkzeuge wissen müssen: die Adressen der
Leistungsseiten unter /leistungen/, ihre Kurztexte für Übersichten (llms.txt,
Sitemap) und die Regel, welche Seite der Kasten „Passende Leistung“ unter einem
Fachbeitrag zeigt. Nur Standardbibliothek, damit die Tests ohne Zusatzpakete laufen.

Zuordnung: Das Frontmatter-Feld ``leistung`` eines Beitrags nennt eine oder
mehrere Leistungen („Beweissicherung, Objektüberwachung LP 8“). Der erste Wert,
zu dem es eine Seite gibt, gewinnt. „Gutachten“ ist zu allgemein; dort entscheidet
das Thema des Beitrags (Schlagwörter, Titel, Kategorie) über die Seite. Passt
nichts, zeigt der Kasten die Übersicht aller Leistungen.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Leistungsseite:
    schluessel: str
    pfad: str       # relativ zur Wurzel der Website, mit Schrägstrich am Ende
    name: str       # kurzer Name für Listen
    titel: str      # Überschrift im Kasten unter dem Beitrag
    kurztext: str   # ein bis zwei Sätze für Kasten und llms.txt


SEITEN: dict[str, Leistungsseite] = {s.schluessel: s for s in (
    Leistungsseite(
        "uebersicht", "leistungen/", "Alle Leistungen",
        "Gutachten, Beweissicherung, Baubegleitung – unsere Leistungen in Berlin",
        "Umfang, Ablauf und Richtpreise aller Leistungen des Büros auf einen Blick – vom "
        "Schimmelgutachten bis zur technischen Due Diligence."),
    Leistungsseite(
        "schimmel", "leistungen/schimmelgutachten/", "Schimmelgutachten",
        "Schimmelgutachten in Berlin: erst die Ursache, dann die Sanierung",
        "Wir klären mit Messung und Berechnung, ob Wärmebrücke, Feuchte aus dem Bauteil oder "
        "Nutzung hinter dem Befall steckt – mit Sanierungsempfehlung und Kostenbandbreite."),
    Leistungsseite(
        "wasserschaden", "leistungen/wasserschaden-gutachten/", "Wasserschaden-Gutachten",
        "Wasserschaden-Gutachten in Berlin: Ursache, Umfang, Sanierung",
        "Zustand sichern, bevor saniert wird; Ursache und betroffene Bauteile feststellen; "
        "Trocknungskonzept und Kosten prüfen – für Eigentümer, Verwaltungen und Versicherer."),
    Leistungsseite(
        "beweissicherung", "leistungen/technische-beweissicherung/", "Technische Beweissicherung",
        "Technische Beweissicherung in Berlin: der Zustand, bevor er sich verändert",
        "Dokumentation von Rissen, Verformungen und Feuchte vor Bauarbeiten am Nachbargrundstück, "
        "vor Sanierungen und vor dem Verdecken von Bauteilen – nachvollziehbar auch Jahre später."),
    Leistungsseite(
        "baubegleitung", "leistungen/baubegleitung-bauabnahme/", "Baubegleitung und Bauabnahme",
        "Baubegleitung und Bauabnahme in Berlin: ein Bauingenieur auf Ihrer Seite",
        "Prüfung der Ausführung, wenn Bauteile fertig, aber noch offen sind, und ein Mängelprotokoll "
        "zur Abnahme, das hält – als Einzeltermin oder Paket."),
    Leistungsseite(
        "due-diligence", "leistungen/technische-due-diligence/", "Technische Due Diligence",
        "Technische Due Diligence und Kaufberatung in Berlin",
        "Begehung und Unterlagenprüfung vor dem Kauf: Zustand, Risiken, Instandhaltungsstau und "
        "Kosten – als Kaufberatung vor Ort, Kurzbericht oder vollständige Due Diligence."),
    Leistungsseite(
        "privatgutachten", "leistungen/privatgutachten-bauprozess/", "Privatgutachten für Bauprozesse",
        "Privatgutachten und Parteiberatung im Bauprozess",
        "Gutachterliche Stellungnahmen zu Mängeln, Schäden, Nachträgen und Bauzeit, Prüfung "
        "gegnerischer Gutachten und Begleitung im Beweisverfahren – für Kanzleien und Parteien."),
    Leistungsseite(
        "gerichte-versicherer", "leistungen/gerichte-versicherer/", "Für Gerichte und Versicherer",
        "Gerichts- und Versicherungsgutachten: Bauschäden, Baumängel, Bauphysik",
        "Gutachten nach Beweisbeschluss oder Rahmenvereinbarung mit verbindlichen Bearbeitungszeiten "
        "– Sachgebiete, Ablauf und Vergütung."),
)}

# Anzeige-Reihenfolge in Übersichten (ohne die Übersichtsseite selbst).
REIHENFOLGE = ["schimmel", "wasserschaden", "beweissicherung", "baubegleitung",
               "due-diligence", "privatgutachten", "gerichte-versicherer"]

# Wert des Frontmatter-Felds „leistung“ (klein geschrieben) → Schlüssel der Seite.
# „Gutachten“ fehlt absichtlich, siehe STICHWORTE.
ZUORDNUNG = {
    "beweissicherung": "beweissicherung",
    "baubegleitung": "baubegleitung",
    "bauherrenvertretung": "baubegleitung",
    "objektüberwachung lp 8": "baubegleitung",
    "objektueberwachung lp 8": "baubegleitung",
    "objektüberwachung": "baubegleitung",
    "kaufberatung": "due-diligence",
    "due diligence": "due-diligence",
    "claim management": "privatgutachten",
    "kalkulation": "privatgutachten",
}

# Thema des Beitrags → Seite; die erste Zeile mit einem Treffer gewinnt. Die
# Reihenfolge geht vom Besonderen zum Allgemeinen: „Beweissicherung“ im Titel
# schlägt „Versicherung“ in den Schlagwörtern.
STICHWORTE: list[tuple[tuple[str, ...], str]] = [
    (("beweissicherung", "zustandsfeststellung", "rissprotokoll", "rissbeobachtung", "risse",
      "übergabeprotokoll", "uebergabeprotokoll"), "beweissicherung"),
    (("wasserschaden", "leitungswasser", "leckage", "rohrbruch", "durchfeucht", "trocknung"),
     "wasserschaden"),
    (("schimmel", "taupunkt", "raumklima", "wärmebrücke", "waermebruecke", "kondensat", "tauwasser"),
     "schimmel"),
    (("hauskauf", "wohnungskauf", "kaufberatung", "altbaukauf", "immobilienkauf", "due diligence",
      "kaufentscheidung"), "due-diligence"),
    (("abnahme", "bauträger", "bautraeger", "baubegleit", "bautagebuch", "gewährleistung",
      "gewaehrleistung", "qualitätskontrolle", "qualitaetskontrolle"), "baubegleitung"),
    (("beweisverfahren", "privatgutachten", "gerichtsgutachten", "prozess", "klage", "verjährung",
      "verjaehrung", "beweislast", "nachtrag", "bauzeit", "jveg"), "privatgutachten"),
    (("versicherungsfall", "versicherer", "versicherung"), "gerichte-versicherer"),
]


def alle() -> list[Leistungsseite]:
    """Alle Seiten in Anzeige-Reihenfolge, die Übersicht zuerst."""
    return [SEITEN["uebersicht"]] + [SEITEN[s] for s in REIHENFOLGE]


def _nach_thema(quellen: list[str]) -> str | None:
    text = " ".join(q.lower() for q in quellen if q)
    for woerter, schluessel in STICHWORTE:
        if any(w in text for w in woerter):
            return schluessel
    return None


def passende_seite(leistungen: list[str], titelquellen: list[str],
                   schlagwortquellen: list[str] = ()) -> Leistungsseite:
    """Die Leistungsseite zu einem Beitrag.

    ``leistungen`` sind die Werte des Frontmatter-Felds in Reihenfolge,
    ``titelquellen`` Titel und Kurzform, ``schlagwortquellen`` Schlagwörter und
    Kategorie. Titel und Kurzform wiegen schwerer: Ein Schimmel-Beitrag, der die
    Beweissicherung nur in den Schlagwörtern erwähnt, führt zum Schimmelgutachten.
    """
    thema = _nach_thema(list(titelquellen)) or _nach_thema(list(schlagwortquellen))
    for wert in leistungen:
        schluessel = wert.strip().lower()
        if schluessel == "gutachten":
            if thema:
                return SEITEN[thema]
            continue
        if schluessel in ZUORDNUNG:
            return SEITEN[ZUORDNUNG[schluessel]]
    return SEITEN[thema] if thema else SEITEN["uebersicht"]
