#!/usr/bin/env python3
"""Doppelungsprüfung ohne KI: Gibt es zu einem Thema schon einen Beitrag?

Ein Thema (Titel und Kernfrage, bei Urteilen Aktenzeichen und ECLI) wird mit
dem Bestand verglichen – Website, Entwürfe in Pull Requests (tools/bestand.py).
Ergebnis je vorhandenem Beitrag:

    doppelung  dasselbe Thema gibt es schon – nicht schreiben
    verwandt   ein ähnlicher Beitrag existiert – schreiben, aber klar abgrenzen
    neu        nichts Vergleichbares

Regeln:
    - Urteile: dasselbe Urteil (gleiche ECLI oder gleiches Aktenzeichen) ist
      eine Doppelung, gleich in welcher Fassung. Zwei verschiedene Urteile zum
      selben Thema sind höchstens verwandt.
    - Eine Vorlage vertritt einen Beitrag: Eine Checkliste zum Ortstermin samt
      Begleitseite deckt auch den Ratgeber „So läuft ein Ortstermin ab“ ab.
      Umgekehrt nicht – eine Vorlage ergänzt einen Fachbeitrag zum selben Thema.
    - Doppelung, wenn die Titel fast gleich sind oder wenn beide Titel einander
      weitgehend abdecken und auch die Kernfragen übereinstimmen (Schwellen
      unten, kalibriert am 03.10.2026: neun bekannte Doppelungen, 71 offene
      Themen, alle Paare veröffentlichter Beiträge).
    - Begriffe zählen nach Seltenheit: „Ortstermin“ wiegt mehr als „prüfen“.
      Gleichbedeutende Wörter werden vorher vereinheitlicht (Mängelrüge =
      Mängelanzeige, Gutachter = Sachverständiger, …).
    - Verglichen wird nur innerhalb einer Sprache (Dateikopf `sprache:`, Notion
      „Sprache“; leer = Deutsch): Ein englischer Beitrag zum Thema eines
      deutschen ist eine Übersetzung, keine Doppelung.

Die Prüfung ist bewusst vorsichtig: Im Zweifel heißt das Ergebnis „verwandt“.
Dann prüft der Agent selbst mit vollem Textverständnis (Skill-Regel DUPLIKAT)
und grenzt sein Thema ab.

Befehle:
    auswahl --kandidaten DATEI --liste themenspeicher|vorlagen|trendthemen --seite DATEI
            [--verwandt DATEI] [--bestand-datei DATEI] [--probelauf]
        Geht offene Notion-Themen in der gegebenen Reihenfolge durch (eine Seite
        je Zeile, JSON). Doppelungen bekommen in Notion den Status „Doppelung“
        und einen Hinweis; das erste Thema ohne Doppelung wird nach --seite
        geschrieben. Rückgabewert 3, wenn keins übrig bleibt.
    verwandt --titel T [--kernfrage K] [--format F] [--notion-id ID] --verwandt DATEI
        schreibt den Abschnitt „Verwandte Beiträge“ für die Auftragsdatei
    pruefen --titel T [--kernfrage K] [--format F]
        zeigt das Ergebnis für ein Thema (zum Ausprobieren)
    bestand-pruefen
        prüft alle Entwürfe gegeneinander und gegen die Website
    markieren --seite ID [--grund TEXT]
        setzt eine Notion-Seite auf „Doppelung“, wenn der Agent selbst DUPLIKAT gemeldet hat

Im öffentlichen Protokoll stehen nie Titel aus Notion – nur Seiten-IDs und die
Kurzformen der vorhandenen Beiträge. Benötigt nur die Standardbibliothek.
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bestand as bestand_modul  # noqa: E402

# Schwellen (siehe Kopf). tc: Anteil der Titelbegriffe des Themas, die der
# vorhandene Beitrag im Titel hat (Schlagwörter zählen halb); te: umgekehrt;
# ac: dasselbe für Titel und Kernfrage zusammen.
DOPPELUNG_TC, DOPPELUNG_TE, DOPPELUNG_AC = 0.6, 0.5, 0.5
VERWANDT_TC, VERWANDT_AC = 0.4, 0.3
TITEL_FAST_GLEICH = 0.82          # wie trend_notion.aehnlich
HOECHSTENS_MARKIEREN = 5          # Notion-Markierungen je Lauf – Schutz vor einem Fehler in der Prüfung
VERWANDTE_ANZAHL = 5

STOPPWOERTER = set("""
a ab aber alle allem allen aller alles als also am an andere anderen auch auf aus bei beim bevor bin bis bitte
bleibt bleiben brauche brauchen bzw dabei dafur damit dann darf darin darauf daran das dass davon davor dazu dem
den denn der des die dies diese diesem diesen dieser doch dort durch durfen ein eine einem einen einer eines
einmal er es etwa etwas fur gegen geht gehen gibt geben gilt habe haben hat hatte heute hier hilft ich ihm ihn
ihr ihre im immer in ist ja jede jedem jeden jeder jetzt kann kein keine konnen konnte lasst lassen man mehr mein
meine meinem meinen meiner mich mir mit muss mussen musst nach nicht noch nun nur ob oder oft ohne sehr sein seine
sich sie sind so soll sollen sollte sollten sowie statt uber um und uns unser unsere unter vom von vor vorher war
warum was weil welch welche welcher welches wem wen wenn wer werden wie wieder will wird wo woher wofur womit
wovon worauf woran wollen wurde zu zum zur zwischen
richtig richtige richtigen richtiges typisch typische typischen haufig haufige haufigsten wichtig wichtige
wichtigste genau wirklich eigentlich gut besser beste neu neue neuen neuer alt klar klaren sauber saubere
einfach schnell sicher jahr jahre jahren lang lange spat spater zuerst sofort
tun tut machen macht gemacht passiert passieren lauft laufen ablauft achten beachten kommt kommen stehen steht
stand lohnt lohnen kostet erkenne erkennen erkennt zahlt bedeutet gehort gehoren stell stelle stellen setze
setzen setzt bleibt liegt nimmt hangt fuhren fuhrt erhalten entdeckt formulieren formuliert schreibe schreiben
schreibt wirksam inhalt zustellung zustellen zugestellt unterscheiden unterscheidet gefunden scheitert
checkliste vorlage musterschreiben muster leitfaden formular tabelle protokoll ratgeber grundlagen anleitung
prufliste prufhilfe haus abs
""".split())

# Gleichbedeutende Begriffe → ein Schlüssel. Muster auf dem gefalteten Text (ä→a, ß→ss).
SYNONYME = [
    (r"\bmangel ?rug\w*|\bmangel ?anzeig\w*", "mangelanzeige"),
    (r"\bbedenken ?anzeig\w*|\bbedenken ?anmeld\w*|\bbedenkenhinweis\w*|\bbedenken anmelden", "bedenkenanzeige"),
    (r"\bbehinderungs ?anzeig\w*", "behinderungsanzeige"),
    (r"\b(?:bau)?sachverstandig\w*|\b(?:bau)?gutachter\w*", "sachverstaendiger"),
    (r"\b\w*begehung\w*", "begehung"),
    (r"\bverkehrssicher\w*", "verkehrssicherung"),
    (r"\banerkannten? regeln der technik|\bregeln der technik", "regeln-der-technik"),
    (r"\bgewahrleist\w*|\bmangelanspruch\w*|\bmangelhaftung", "gewaehrleistung"),
    (r"\bbautagebuch\w*|\bbautagesbericht\w*", "bautagebuch"),
    (r"\bpfusch\w*|\bbaumangel\w*|\bmangel\b|\bmangeln\b|\bmangelhaft\w*", "mangel"),
    (r"\bimmobilienkauf\w*|\bhauskauf\w*|\bkauf (?:eines|einer) (?:gebrauchten )?(?:hauses|immobilie)\b"
     r"|\bimmobilien? (?:zu )?kaufen\b|\bhaus (?:zu )?kaufen\b", "hauskauf"),
    (r"\b(?:bau|end)?abnahm\w*", "abnahme"),
    (r"\bschlussrechnung\w*", "schlussrechnung"),
    (r"\baufmass\w*", "aufmass"),
    (r"\bwasserschad\w*|\bleitungswasser\w*", "wasserschaden"),
    (r"\bortstermin\w*", "ortstermin"),
    (r"\bdin[ -]?norm\w*|\bdin\b", "din"),
    (r"\bschimmel\w*", "schimmel"),
    (r"\bverjahr\w*", "verjaehrung"),
    (r"\bnachtrag\w*", "nachtrag"),
    (r"\b(?:verbraucher)?bauvertrag\w*|\bbauvertrage\b", "bauvertrag"),
    (r"\bhausverwaltung\w*|\bverwalter\w*", "hausverwaltung"),
    (r"\bweg\b|\beigentumergemeinschaft\w*|\bwohnungseigentum\w*", "weg"),
    (r"\briss\w*", "riss"),
    (r"\bfeucht\w*|\bdurchfeucht\w*|\bnass\w*", "feuchte"),
    (r"\bbautrager\w*", "bautraeger"),
    (r"\bgemeinschaftseigentum\w*", "gemeinschaftseigentum"),
    (r"\bbeweissicherung\w*|\bzustandsfeststellung\w*", "beweissicherung"),
    (r"\bbeweisverfahren\w*", "beweisverfahren"),
    (r"\bfrist\w*", "frist"),
    (r"\bdokumentier\w*|\bdokumentation\w*", "dokumentation"),
    (r"\bhoai\b|\bleistungsphase 8\b|\blp ?8\b|\bobjektuberwach\w*|\bbauuberwach\w*", "objektueberwachung"),
    (r"\bbaufirm\w*|\bbauunternehm\w*", "bauunternehmen"),
    (r"\bvorbereit\w*", "vorbereitung"),
    (r"\babschlags\w*|\braten?\b", "abschlag"),
]
# Grundwörter für „Behinderungs- und Bedenkenanzeige“ → „behinderungsanzeige und bedenkenanzeige“
GRUNDWOERTER = ("anzeige", "sanierung", "schaden", "protokoll", "vertrag", "planung", "plan", "kosten",
                "rechnung", "prufung", "messung", "gutachten", "verfahren", "abnahme", "eigentum", "sicherung")


def falten(text: str) -> str:
    """Kleinschreibung, Umlaute auf den Grundbuchstaben (wie artikel_generator._falten),
    verkürzte Zusammensetzungen ergänzt, alles außer Buchstaben und Ziffern als Leerzeichen."""
    t = (text or "").lower()
    for zeichen, ersatz in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        t = t.replace(zeichen, ersatz)

    def ergaenzen(m: re.Match) -> str:
        for grundwort in GRUNDWOERTER:
            if m.group(3).endswith(grundwort) and len(m.group(3)) > len(grundwort):
                return f"{m.group(1)}{grundwort} {m.group(2)} {m.group(3)}"
        return m.group(0)

    t = re.sub(r"(\w+)-\s+(und|oder)\s+(\w+)", ergaenzen, t)
    return re.sub(r"[^a-z0-9]+", " ", t)


def stamm(wort: str) -> str:
    """Grobe Grundform: häufige Endungen ab, damit „Fristen“ und „Frist“ zusammenfallen."""
    if len(wort) <= 4:
        return wort
    for endung, ersatz in (("ungen", "ung"), ("heiten", "heit"), ("keiten", "keit"), ("ionen", "ion"),
                           ("erinnen", ""), ("innen", "")):
        if wort.endswith(endung):
            return wort[: -len(endung)] + ersatz
    for endung in ("ern", "en", "em", "er", "es", "e"):
        if len(wort) - len(endung) >= 4 and wort.endswith(endung):
            return wort[: -len(endung)]
    if len(wort) > 5 and wort.endswith("n") and wort[-2] in "lr":
        return wort[:-1]
    if len(wort) > 5 and wort.endswith("s") and wort[-2] not in "aeiouys":
        return wort[:-1]
    return wort


def begriffe(text: str) -> frozenset[str]:
    t = f" {falten(text)} "
    gefunden = set()
    for muster, schluessel in SYNONYME:
        if re.search(muster, t):
            gefunden.add(schluessel)
            t = re.sub(muster, " ", t)
    for wort in t.split():
        if wort not in STOPPWOERTER and len(wort) >= 3 and not wort.isdigit():
            gefunden.add(stamm(wort))
    return frozenset(gefunden)


def normal_az(wert: str) -> str:
    """Aktenzeichen vergleichbar machen (wie urteile_finden.normal_az)."""
    return re.sub(r"\s+", " ", (wert or "").strip().strip("\"'")).upper()


def normal_ecli(wert: str) -> str:
    return re.sub(r"\s+", "", (wert or "").strip().strip("\"'")).upper()


def gleiches_urteil(a: dict, b: dict) -> bool:
    ea, eb = normal_ecli(a.get("ecli", "")), normal_ecli(b.get("ecli", ""))
    if ea and eb and ea == eb:
        return True
    za, zb = normal_az(a.get("aktenzeichen", "")), normal_az(b.get("aktenzeichen", ""))
    return bool(za) and za == zb


def gleicher_eintrag(a: dict, b: dict) -> bool:
    """Dieselbe Sache in zwei Quellen (etwa Notion-Seite und ihr Entwurf)."""
    if a is b:
        return True
    if a.get("notion_id") and a.get("notion_id") == b.get("notion_id"):
        return True
    return bool(a.get("kurzform")) and a.get("kurzform") == b.get("kurzform")


class Vergleich:
    """Vergleicht Themen mit dem Bestand; die Seltenheit der Begriffe kommt aus allen Einträgen."""

    def __init__(self, eintraege: list[dict]):
        self.eintraege = eintraege
        for e in eintraege:
            self.vorbereiten(e)
        self.df: dict[str, int] = {}
        for e in eintraege:
            for w in e["_T"] | e["_K"]:
                self.df[w] = self.df.get(w, 0) + 1
        self.n = len(eintraege)

    @staticmethod
    def vorbereiten(e: dict) -> dict:
        if "_T" not in e:
            e["_T"] = begriffe(e.get("titel", ""))
            e["_K"] = begriffe(e.get("kernfrage", ""))
            e["_S"] = begriffe((e.get("schlagwoerter") or "").replace(",", " , "))
        return e

    def gewicht(self, menge) -> float:
        return sum(math.log((self.n + 1) / (self.df.get(w, 0) + 1)) + 1 for w in menge)

    def anteil(self, a, b, halb=frozenset()) -> float:
        """Gewichteter Anteil der Begriffe von a, die b enthält; Begriffe aus `halb` zählen halb."""
        if not a:
            return 0.0
        return (self.gewicht(a & b) + 0.5 * self.gewicht((a - b) & halb)) / self.gewicht(a)

    def merkmale(self, c: dict, e: dict) -> dict:
        self.vorbereiten(c)
        self.vorbereiten(e)
        tc, te = c["_T"], e["_T"]
        alle_c, alle_e = c["_T"] | c["_K"], e["_T"] | e["_K"]
        return {"tc": self.anteil(tc, te, e["_S"]), "te": self.anteil(te, tc),
                "ac": self.anteil(alle_c, alle_e, e["_S"]), "ae": self.anteil(alle_e, alle_c)}

    def urteil(self, c: dict, e: dict) -> tuple[str, str, dict]:
        """(doppelung|verwandt|neu, Grund, Merkmale) für das Thema c gegenüber dem Eintrag e."""
        if c.get("art") == "urteil" and e.get("art") == "urteil" and gleiches_urteil(c, e):
            return "doppelung", "dasselbe Urteil", {}
        # Ein englischer Beitrag zum Thema eines deutschen ist eine Übersetzung, keine Doppelung.
        if c.get("sprache", "de") != e.get("sprache", "de"):
            return "neu", "", {}
        m = self.merkmale(c, e)
        # Urteile vertreten keine Beiträge und umgekehrt; eine Vorlage ergänzt einen Fachbeitrag
        # zum selben Thema (die Begleitseite verlinkt ihn), ersetzt wird sie nur durch eine Vorlage.
        texte = c.get("art") != "urteil" and e.get("art") != "urteil" and \
            not (c.get("art") == "vorlage" and e.get("art") == "beitrag")
        if texte:
            na, nb = " ".join(sorted(c["_T"])), " ".join(sorted(e["_T"]))
            if na and difflib.SequenceMatcher(None, na, nb).ratio() >= TITEL_FAST_GLEICH:
                return "doppelung", "fast gleicher Titel", m
            if m["tc"] >= DOPPELUNG_TC and m["te"] >= DOPPELUNG_TE and m["ac"] >= DOPPELUNG_AC:
                return "doppelung", "gleiches Thema und gleiche Kernfrage", m
        if m["tc"] >= VERWANDT_TC or m["ac"] >= VERWANDT_AC:
            return "verwandt", "ähnliches Thema", m
        return "neu", "", m

    def pruefen(self, c: dict, kandidaten: list[dict] | None = None) -> dict:
        """Vergleicht c mit allen Einträgen (außer sich selbst).

        Ergebnis: {"urteil": doppelung|verwandt|neu|vorhanden, "doppelungen": [...],
        "verwandte": [...]} – Listen von (Eintrag, Grund, Merkmale), die stärksten zuerst.
        „vorhanden“: Zu dieser Notion-Seite gibt es schon einen Entwurf.
        """
        doppelungen, verwandte = [], []
        for e in kandidaten if kandidaten is not None else self.eintraege:
            if e is c:
                continue
            if c.get("notion_id") and c.get("notion_id") == e.get("notion_id"):
                if e.get("quelle") != "notion":
                    return {"urteil": "vorhanden", "doppelungen": [(e, "eigener Entwurf", {})], "verwandte": []}
                continue
            if c.get("kurzform") and c.get("kurzform") == e.get("kurzform"):
                continue
            u, grund, m = self.urteil(c, e)
            if u == "doppelung":
                doppelungen.append((e, grund, m))
            elif u == "verwandt":
                verwandte.append((e, grund, m))
        staerke = lambda t: -(t[2].get("ac", 1) + t[2].get("tc", 1))  # noqa: E731
        doppelungen.sort(key=staerke)
        verwandte.sort(key=staerke)
        urteil = "doppelung" if doppelungen else "verwandt" if verwandte else "neu"
        return {"urteil": urteil, "doppelungen": doppelungen, "verwandte": verwandte}


# --------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------

def beschreibung(e: dict) -> str:
    """Wie ein vorhandener Beitrag im Protokoll heißt: Kurzform und Stand – nie ein Notion-Titel."""
    if e.get("quelle") == "notion":
        return f"Notion-Thema {e.get('notion_id', '')[:8]}… ({e.get('liste', '')}, {e.get('status', '')})"
    kurz = e.get("kurzform") or "Thema ohne Kurzform"
    if e.get("status") == "veröffentlicht":
        return f"{kurz} (veröffentlicht)"
    if e.get("pr_offen"):
        return f"{kurz} (Entwurf, Pull Request #{e.get('pr')})"
    return f"{kurz} (Entwurf, wartet auf Veröffentlichung)"


def verweis(e: dict) -> str:
    """Wie ein vorhandener Beitrag in Notion und in der Auftragsdatei genannt wird."""
    if e.get("status") == "veröffentlicht" and e.get("link"):
        return f"„{e['titel']}“ – veröffentlicht: {e['link']}"
    if e.get("pr_offen") and e.get("pr_url"):
        return f"„{e['titel']}“ – Entwurf, wartet auf Freigabe: {e['pr_url']} (nicht verlinken)"
    return f"„{e['titel']}“ – Entwurf, wartet auf Veröffentlichung (nicht verlinken)"


def abschnitt_verwandte(ergebnis: dict, freigegeben: bool = False, gezielt: bool = False) -> str:
    """Abschnitt „Verwandte Beiträge“ für die Auftragsdatei (liegt außerhalb des Repositorys)."""
    eintraege = [t for t in ergebnis["doppelungen"] + ergebnis["verwandte"] if t[0].get("quelle") != "notion"]
    zeilen = ["", "## Verwandte Beiträge (vom Workflow ermittelt)", ""]
    if not eintraege:
        zeilen.append("Keine – zu diesem Thema gibt es noch nichts Vergleichbares.")
        return "\n".join(zeilen) + "\n"
    zeilen += ["Diese Beiträge gibt es schon, oder sie warten auf die Freigabe. Dein Beitrag grenzt sich klar "
               "davon ab: eigene Kernfrage, eigener Schwerpunkt, keine Wiederholung ihrer Inhalte. Verlinke im "
               "Text nur veröffentlichte Beiträge, mit der angegebenen Adresse.", ""]
    if freigegeben:
        zeilen += ["Der Auftraggeber hat dieses Thema trotz Ähnlichkeit ausdrücklich freigegeben (Notion: "
                   "Status von „Doppelung“ zurück auf „Idee“). Wegen der hier genannten Beiträge ist es kein "
                   "DUPLIKAT; die gewünschte Abgrenzung steht in den Notizen aus Notion.", ""]
    elif gezielt:
        zeilen += ["Der Auftraggeber hat dieses Thema gezielt gestartet. Beantwortet einer der Beiträge "
                   "dieselbe Kernfrage, schreibst du trotzdem – mit klarer Abgrenzung – und nennst die Nähe im "
                   "Pull Request.", ""]
    for e, _, _ in eintraege[:VERWANDTE_ANZAHL]:
        zeile = f"- {verweis(e)}"
        if e.get("kernfrage"):
            zeile += f" – Kernfrage: {e['kernfrage']}"
        zeilen.append(zeile)
    return "\n".join(zeilen) + "\n"


def protokoll(text: str) -> None:
    """Ins öffentliche Protokoll – Zeilen beginnen nie mit „::“, außer echten Meldungen."""
    print(text)


# --------------------------------------------------------------------------
# Notion
# --------------------------------------------------------------------------

def notion_text(inhalt: str, link: str | None = None) -> dict:
    from trend_notion import text
    return text(inhalt, link)


def doppelung_hinweis_vorhanden(seite_id: str, senden=None) -> bool:
    """Hat die Seite schon einen Doppelungs-Hinweis? Dann hat der Auftraggeber den Status
    bewusst zurückgesetzt – das Thema ist freigegeben."""
    from trend_notion import anfrage
    senden = senden or anfrage
    antwort = senden("GET", f"/blocks/{seite_id}/children?page_size=100")
    for block in antwort.get("results") or []:
        if block.get("type") == "callout":
            text = "".join(t.get("plain_text", "") for t in block["callout"].get("rich_text") or [])
            if text.strip().startswith("Doppelung"):
                return True
    return False


def als_doppelung_markieren(seite_id: str, abdeckend: list[dict], senden=None, grund: str = "") -> None:
    """Status „Doppelung“ und ein Hinweis auf die Beiträge, die das Thema schon abdecken –
    oder, wenn der Agent die Doppelung gemeldet hat, auf seinen Grund."""
    from trend_notion import anfrage
    senden = senden or anfrage
    stuecke = [notion_text("Doppelung: ", None)]
    stuecke[0]["annotations"] = {"bold": True}
    if grund:
        stuecke.append(notion_text(f"Der Agent hat beim Abgleich mit dem Bestand festgestellt: {grund.rstrip('.')}."))
        stuecke.append(notion_text(" Die Agenten überspringen das Thema."))
    else:
        stuecke.append(notion_text("Dieses Thema deckt bereits "))
        for i, e in enumerate(abdeckend[:2]):
            if i:
                stuecke.append(notion_text(" und "))
            ziel = e.get("link") or e.get("pr_url") or None
            stuecke.append(notion_text(e.get("titel", e.get("kurzform", "")), ziel))
            stand = "online" if e.get("status") == "veröffentlicht" else "wartet auf Veröffentlichung"
            stuecke.append(notion_text(f" ({stand})"))
        stuecke.append(notion_text(" ab. Die Agenten überspringen es."))
    stuecke.append(notion_text(" Soll es trotzdem einen eigenen Beitrag geben, Status zurück auf „Idee“ setzen "
                               "und hier die Abgrenzung notieren."))
    senden("PATCH", f"/pages/{seite_id}", {"properties": {"Status": {"select": {"name": "Doppelung"}}}})
    senden("PATCH", f"/blocks/{seite_id}/children", {"children": [{
        "object": "block", "type": "callout",
        "callout": {"rich_text": stuecke, "icon": {"type": "emoji", "emoji": "⚠️"}, "color": "red_background"}}]})


# --------------------------------------------------------------------------
# Auswahl
# --------------------------------------------------------------------------

def bestand_holen(datei: Path | None) -> list[dict]:
    """Website und Pull Requests (ohne Notion: Die offenen Themen sind die Kandidaten selbst).
    Mit --bestand-datei wird ein schon gelesener Bestand wiederverwendet."""
    if datei and datei.is_file():
        b = bestand_modul.lesen(datei)
    else:
        b = bestand_modul.laden(notion=False)
        if datei:
            bestand_modul.speichern(b, datei)
        for w in b["warnungen"]:
            print(f"::warning title=Doppelungsprüfung::{w}")
    return [e for e in b["eintraege"] if e.get("quelle") != "notion"]


def auswaehlen(kandidaten: list[dict], liste: str, vorhanden: list[dict], *, markieren: bool = True,
               senden=None, hinweis_pruefen=None) -> tuple[dict | None, dict, list[str]]:
    """Das erste Notion-Thema ohne Doppelung.

    kandidaten: Notion-Seiten in Auswahlreihenfolge. Ergebnis: (Seite oder None,
    Prüfergebnis der gewählten Seite, Protokollzeilen ohne Notion-Titel).
    """
    from trend_notion import NotionFehler

    def freigegeben(seite_id: str) -> bool:
        try:
            return (hinweis_pruefen or (lambda sid: doppelung_hinweis_vorhanden(sid, senden)))(seite_id)
        except NotionFehler:
            return False

    themen = [t for t in (bestand_modul.notion_eintrag(s, liste) for s in kandidaten)]
    vergleich = Vergleich(vorhanden + [t for t in themen if t])
    zeilen, markiert = [], 0
    for seite, thema in zip(kandidaten, themen):
        kurz = (seite.get("id") or "")[:8]
        if thema is None:
            zeilen.append(f"Thema {kurz}…: ohne Titel – übersprungen")
            continue
        ergebnis = vergleich.pruefen(thema, vorhanden)
        if ergebnis["urteil"] == "vorhanden":
            zeilen.append(f"Thema {kurz}…: Entwurf gibt es schon ({beschreibung(ergebnis['doppelungen'][0][0])}) "
                          "– übersprungen")
            continue
        if ergebnis["urteil"] == "doppelung":
            treffer = [t[0] for t in ergebnis["doppelungen"]]
            if freigegeben(seite["id"]):
                zeilen.append(f"Thema {kurz}…: Doppelung zu {beschreibung(treffer[0])}, aber vom Auftraggeber "
                              "freigegeben – wird geschrieben, mit Abgrenzung")
                ergebnis["freigegeben"] = True
                ergebnis["verwandte"] = ergebnis["doppelungen"] + ergebnis["verwandte"]
                ergebnis["doppelungen"] = []
                return seite, ergebnis, zeilen
            if markieren and markiert < HOECHSTENS_MARKIEREN:
                try:
                    als_doppelung_markieren(seite["id"], treffer, senden)
                    markiert += 1
                    vermerk = "in Notion als „Doppelung“ markiert"
                except NotionFehler as fehler:
                    vermerk = f"übersprungen, Markierung in Notion fehlgeschlagen ({str(fehler)[:120]})"
                zeilen.append(f"Thema {kurz}…: Doppelung zu {beschreibung(treffer[0])} "
                              f"({ergebnis['doppelungen'][0][1]}) – {vermerk}")
            else:
                zeilen.append(f"Thema {kurz}…: Doppelung zu {beschreibung(treffer[0])} "
                              f"({ergebnis['doppelungen'][0][1]}) – übersprungen"
                              + ("" if not markieren else ", nicht markiert (Höchstzahl je Lauf erreicht)"))
            continue
        zeilen.append(f"Gewählt: Thema {kurz}… ({'verwandt mit ' + beschreibung(ergebnis['verwandte'][0][0]) if ergebnis['verwandte'] else 'neu'})")
        return seite, ergebnis, zeilen
    return None, {"urteil": "neu", "doppelungen": [], "verwandte": []}, zeilen


# --------------------------------------------------------------------------

def thema_aus_argumenten(a) -> dict:
    return {"quelle": "auftrag", "art": bestand_modul.art_von(a.format), "format": a.format,
            "titel": a.titel, "kernfrage": a.kernfrage, "aktenzeichen": a.aktenzeichen, "ecli": a.ecli,
            "notion_id": bestand_modul.normiere_id(a.notion_id)}


def bestand_pruefen(eintraege: list[dict]) -> list[tuple[dict, dict, str]]:
    """Paare (Entwurf, anderer Beitrag, Grund), bei denen ein Entwurf eine Doppelung ist.

    Zwei Entwürfe zum selben Thema werden einmal gemeldet – beim jüngeren."""
    vergleich = Vergleich(eintraege)
    reihenfolge = sorted(eintraege, key=lambda e: (e.get("erstellt", ""), e.get("pfad", ""), e.get("pr") or 0))
    funde, gesehen = [], []
    for e in reihenfolge:
        if e.get("status") == "entwurf":
            for frueher in gesehen:
                if gleicher_eintrag(e, frueher):
                    continue
                u, grund, _ = vergleich.urteil(e, frueher)
                if u == "doppelung":
                    funde.append((e, frueher, grund))
                    break
        gesehen.append(e)
    # Entwürfe gegen später veröffentlichte Beiträge (Reihenfolge der Erstellung zählt nicht,
    # wenn der andere schon online ist)
    for e in eintraege:
        if e.get("status") != "entwurf" or any(f[0] is e for f in funde):
            continue
        for anderer in eintraege:
            if anderer is e or anderer.get("status") != "veröffentlicht" or gleicher_eintrag(e, anderer):
                continue
            u, grund, _ = vergleich.urteil(e, anderer)
            if u == "doppelung":
                funde.append((e, anderer, grund))
                break
    return funde


def main(argumente: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    unter = p.add_subparsers(dest="befehl", required=True)
    q = unter.add_parser("auswahl")
    q.add_argument("--kandidaten", type=Path, required=True, help="Notion-Seiten, eine JSON-Zeile je Seite")
    q.add_argument("--liste", choices=sorted(bestand_modul.NOTION_LISTEN), required=True)
    q.add_argument("--seite", type=Path, required=True, help="hierhin die gewählte Seite (JSON)")
    q.add_argument("--verwandt", type=Path, help="hierhin der Abschnitt „Verwandte Beiträge“")
    q.add_argument("--bestand-datei", type=Path)
    q.add_argument("--probelauf", action="store_true", help="nichts in Notion ändern")
    for name in ("verwandt", "pruefen"):
        q2 = unter.add_parser(name)
        q2.add_argument("--titel", required=True)
        q2.add_argument("--kernfrage", default="")
        q2.add_argument("--format", default="")
        q2.add_argument("--notion-id", default="")
        q2.add_argument("--aktenzeichen", default="")
        q2.add_argument("--ecli", default="")
        q2.add_argument("--bestand-datei", type=Path)
        if name == "verwandt":
            q2.add_argument("--verwandt", type=Path, required=True)
            q2.add_argument("--gezielt", action="store_true")
    q3 = unter.add_parser("bestand-pruefen")
    q3.add_argument("--bestand-datei", type=Path)
    q4 = unter.add_parser("markieren", help="eine Notion-Seite als Doppelung markieren (Meldung des Agenten)")
    q4.add_argument("--seite", required=True, help="Notion-Seiten-ID")
    q4.add_argument("--grund", default="", help="Grund aus dem ERGEBNIS-Block des Agenten")
    a = p.parse_args(argumente)

    from trend_notion import NotionFehler
    try:
        if a.befehl == "markieren":
            als_doppelung_markieren(a.seite, [], grund=" ".join(a.grund.split()) or "Doppelung erkannt")
            print(f"Notion-Seite {a.seite[:8]}… als „Doppelung“ markiert.")
            return 0
        if a.befehl == "auswahl":
            kandidaten = [json.loads(z) for z in a.kandidaten.read_text(encoding="utf-8").splitlines() if z.strip()]
            vorhanden = bestand_holen(a.bestand_datei)
            seite, ergebnis, zeilen = auswaehlen(kandidaten, a.liste, vorhanden, markieren=not a.probelauf)
            for z in zeilen:
                protokoll(z)
            if seite is None:
                print(f"::warning title=Doppelungsprüfung::Kein offenes Thema ohne Doppelung "
                      f"({len(kandidaten)} geprüft).")
                return 3
            a.seite.write_text(json.dumps(seite, ensure_ascii=False), encoding="utf-8")
            if a.verwandt:
                a.verwandt.write_text(abschnitt_verwandte(ergebnis, freigegeben=ergebnis.get("freigegeben", False)),
                                      encoding="utf-8")
            return 0
        if a.befehl in ("verwandt", "pruefen"):
            vorhanden = bestand_holen(a.bestand_datei)
            thema = thema_aus_argumenten(a)
            ergebnis = Vergleich(vorhanden + [thema]).pruefen(thema, vorhanden)
            if a.befehl == "verwandt":
                a.verwandt.write_text(abschnitt_verwandte(ergebnis, gezielt=a.gezielt), encoding="utf-8")
            print(f"Ergebnis: {ergebnis['urteil']}")
            for e, grund, m in ergebnis["doppelungen"]:
                print(f"  Doppelung: {beschreibung(e)} – {grund}")
            for e, grund, m in ergebnis["verwandte"][:VERWANDTE_ANZAHL]:
                print(f"  verwandt: {beschreibung(e)}")
            return 0
        vorhanden = bestand_holen(a.bestand_datei)
        funde = bestand_pruefen(vorhanden)
        for e, anderer, grund in funde:
            print(f"Doppelung: {beschreibung(e)} ↔ {beschreibung(anderer)} – {grund}")
        print(f"{len(funde)} Doppelung(en) unter {sum(1 for e in vorhanden if e.get('status') == 'entwurf')} Entwürfen")
        return 0
    except NotionFehler as fehler:
        print(f"::error title=Doppelungsprüfung::{fehler}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
