#!/usr/bin/env python3
"""Prüft die in Entwürfen genannten Normausgaben gegen den Normindex der Fachbibliothek.

Stand der Technik heißt: Ein Beitrag nennt die neueste Ausgabe einer Norm – oder
sagt im selben Satz ausdrücklich, dass er eine frühere Fassung meint, etwa die
zum Abnahmezeitpunkt geltende. Das Werkzeug sucht alle Normzitate (DIN, DIN EN,
DIN EN ISO, DIN ISO, DIN IEC, DIN EN IEC, DIN SPEC, DIN-TS, DIN V, DIN VDE, VDI,
VDE) im Text, in den Fußnoten und im Dateikopf-Feld regelwerke_bestaetigt und
vergleicht sie mit normen/ausgaben.yml aus dem privaten Repository
FachwissenAgent (im Workflow .bibliothek/normen/ausgaben.yml). Der Index enthält
nur Metadaten – Norm, Thema, Ausgaben –, keine Normtexte.

    FEHLER   genannte Ausgabe älter als die neueste im Index, ohne dass der Satz
             sie als frühere oder stichtagsbezogene Fassung kennzeichnet
             (damals, seinerzeit, zum Zeitpunkt, galt bis, frühere Ausgabe,
             zurückgezogen, zum Abnahmezeitpunkt, „im Jahr 2013“ mit dem Jahr
             der Ausgabe …). „ersetzt“ kennzeichnet nur die Ausgabe, die ersetzt
             wird („X ersetzt DIN …:2013-04“, „DIN …:2013-04 wurde durch …
             ersetzt“), nie die ersetzende. „Status aktuell“ bei der Nennung
             heißt: als geltend dargestellt. Gewertet wird je Satzteil bis zum
             nächsten Semikolon.
    HINWEIS  ältere Ausgabe, im Satz als frühere Fassung gekennzeichnet; Norm
             ohne Ausgabe genannt; Norm nicht im Index; genannte Ausgabe neuer
             als der Index; Änderung oder Berichtigung im Index, im Beitrag
             nicht genannt; Indexeintrag mit „pruefen: true“

Maßgeblich bleibt der Status bei DIN Media – der Index kann veraltet sein.

Aufruf:
    python tools/normstand_pruefen.py <entwurf.md> [<weitere.md> ...] --ausgaben <ausgaben.yml>
        [--bericht <datei.md>] [--json <datei.json>]

Rückgabewert 0 = kein FEHLER, 1 = mindestens ein FEHLER, 2 = Normindex fehlt oder
ist unlesbar (dann ist nichts geprüft). Letzte Zeile der Ausgabe:
„fehler=<n> hinweise=<m>“ bzw. „fehler=nicht-geprueft“.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

UEBERSCHRIFT = "## Stand der Technik – Normausgaben"
NICHT_GEPRUEFT = "Nicht geprüft: Normindex der Fachbibliothek nicht geladen – Stand der Technik ungeprüft."
DIN_MEDIA = "Status bei DIN Media bestätigen"

MONATE = {"Januar": "01", "Februar": "02", "März": "03", "April": "04", "Mai": "05", "Juni": "06",
          "Juli": "07", "August": "08", "September": "09", "Oktober": "10", "November": "11",
          "Dezember": "12"}
JAHR = r"(?:19|20)\d{2}"
MONAT = r"[01]\d"
# Reihe: DIN, DIN EN, DIN EN ISO, DIN ISO, DIN IEC, DIN EN IEC, DIN SPEC, DIN-TS
# (auch DIN/TS, DIN TS), DIN V, DIN VDE, DIN-Fachbericht, VDI (auch VDI/VDE,
# VDI/GVSS …), VDE
REIHE = (r"DIN(?: EN ISO(?:/IEC)?| EN IEC| EN| ISO(?:/IEC)?| IEC| SPEC| VDE| CEN(?:/TS| ISO/TS)?"
         r"|[ /-]TS|-SPEC|-Fachbericht| V(?= \d))?"
         r"|VDI(?:/[A-Z]{2,6})?|VDE(?:-AR-[A-Z])?")
NORM = re.compile(
    r"(?<![\w/-])(?P<reihe>" + REIHE + r") (?P<nummer>\d{1,5}(?:-\d{1,4})*)"
    r"(?P<zusatz>(?: (?:Blatt|Beiblatt|Teil) \d+(?:\.\d+)?)*)"
    r"(?P<na>[/-]NA)?"
    r"(?:[/-](?P<aenderung>A\d{1,2}))?"
    r"(?:(?: Berichtigung ?| ?/Ber\.? ?)(?P<berichtigung>\d{1,2}))?"
    r"(?: \((?:DIN|VDE|VDI)[^)\n]{1,40}\))?"           # Doppelbezeichnung „DIN VDE … (VDE …)“
    r"(?::\s?(?P<j1>" + JAHR + r")(?:-(?P<m1>" + MONAT + r"))?(?!\d)"
    r"| \((?P<j2>" + JAHR + r")-(?P<m2>" + MONAT + r")\)"
    r"| [–-] (?P<j3>" + JAHR + r")-(?P<m3>" + MONAT + r")(?!\d)"
    # „, Ausgabe Mai 2024“, „(Ausgabe 2013-04)“, „in der Fassung 07/2013“, „Fassung von 2013“
    r"|,? \(?(?:in der |in ihrer )?(?:Ausgabe|Fassung)(?: vom| von| aus(?: dem Jahre?)?)? "
    r"(?:(?P<j4>" + JAHR + r")-(?P<m4>" + MONAT + r")|(?P<m6>" + MONAT + r")/(?P<j6>" + JAHR + r")"
    r"|(?P<monat>" + "|".join(MONATE) + r") (?P<j5>" + JAHR + r")|(?P<j7>" + JAHR + r")(?![-/\d]))\)?"
    # „vom April 2013“, „von 2013“, „aus dem Jahr 2013“
    r"|,? (?:vom|von|aus(?: dem Jahre?)?) (?:(?P<monat2>" + "|".join(MONATE) + r") (?P<j8>" + JAHR + r")"
    r"|(?P<j9>" + JAHR + r")(?![-/\d])))?")
JAHRGRUPPEN = ("j1", "j2", "j3", "j4", "j5", "j6", "j7", "j8", "j9")
MONATSGRUPPEN = ("m1", "m2", "m3", "m4", "m6")

# Der Satzteil kennzeichnet eine ältere Ausgabe als frühere oder stichtagsbezogene Fassung.
# Die englischen Wendungen gelten für die Leitfäden in entwuerfe-en/.
HISTORISCH = re.compile(
    r"\b(?:damal\w*|seinerzeit\w*|zum Zeitpunkt|zu diesem Zeitpunkt|galt|galten|gültig bis|"
    r"bis zur Ausgabe|zum Abnahmezeitpunkt|zur Bauzeit|bei Errichtung|"
    r"(?:frühere|früheren|früherer|ältere|älteren|älterer|alte|alten|bisherige|bisherigen|vorige|vorigen)"
    r" (?:Ausgabe|Fassung|Norm)\w*|"
    r"Vorausgabe\w*|Vorgängerausgabe\w*|Vorgängerfassung\w*|Vorgängernorm\w*|zurückgezogen\w*|"
    r"at the time|then applicable|in force until|withdrawn|"
    r"(?:former|previous|earlier|older|old) (?:edition|version|standard)s?)\b"
    r"|\ba\. ?F\.", re.I)
# „im Jahr 2013“ kennzeichnet nur die Ausgabe dieses Jahres als stichtagsbezogen.
JAHRMARKE = re.compile(r"\b(?:im Jahre?|in) (" + JAHR + r")(?![-/\d])", re.I)
# „X ersetzt DIN …“, „die ersetzte DIN …“: kennzeichnet die Ausgabe(n) DANACH.
ERSETZT_VOR = re.compile(r"\b(?:ersetzt(?!\s+(?:durch|worden)\b)|ersetzte\w*|replaces|supersedes"
                         r"|replaced(?!\s+by\b)|superseded(?!\s+by\b))\b", re.I)
# „DIN … wurde (durch …) ersetzt“, „…, ersetzt durch …“: kennzeichnet die Ausgabe DAVOR.
ERSETZT_NACH = re.compile(r"\b(?:ersetzt\s+(?:durch|worden)|inzwischen\s+ersetzt"
                          r"|(?:wurde|wurden|ist|sind)\s+(?:(?!und\b|oder\b|aber\b)[^\s,;.]+\s+){0,6}?ersetzt"
                          r"|(?:replaced|superseded)\s+by"
                          r"|(?:was|were|is|are|has\s+been|have\s+been)\s+(?:replaced|superseded))\b", re.I)
# Zwischen Kennwort und Nennung nur eine Aufzählung (weitere Nennungen, „und“, „die Ausgabe“ …)
AUFZAEHLUNG = re.compile(r"(?:[\s,/&\x01]|\b(?:und|sowie|bzw|oder|and|or|die|den|das|der|the|frühere\w*|"
                         r"alte\w*|Ausgabe\w*|Fassung\w*|Norm\w*|editions?|versions?)\b|\.)*", re.I)
# Als geltend dargestellt: „Status aktuell“ hinter der Nennung, „aktuelle Ausgabe“ direkt davor
STATUS_NACH = re.compile(r"\bStatus:?\s*(?:aktuell|gültig|current|valid)\b|\b(?:derzeit|aktuell|heute)\s+gültig",
                         re.I)
STATUS_VOR = re.compile(r"\b(?:aktuelle|gültige|geltende|current)\s+(?:Ausgabe|Fassung|edition|version)"
                        r"(?:\s+ist)?\s*[:,]?\s*$", re.I)

LINK = re.compile(r"\[([^\]]*)\]\([^)\s]*\)")
ADRESSE = re.compile(r"<?https?://[^\s<>)\]]+>?")
ZEICHEN = str.maketrans({"\u00a0": " ", "\u202f": " ", "\u2009": " ", "\u2010": "-", "\u2011": "-"})
SATZGRENZE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„\"(])")
ABKUERZUNGEN = {"abs", "art", "bzw", "ca", "d", "dr", "evtl", "f", "ff", "ggf", "h", "i", "inkl", "nr",
                "rn", "s", "u", "v", "vgl", "z", "b", "a", "bspw", "sog", "tab", "abschn", "kap", "aufl"}


class IndexFehlt(Exception):
    """Der Normindex fehlt oder ist unlesbar – nichts geprüft."""


def schluessel(text: str) -> str:
    """Normalisierter Schlüssel wie im Index: Großbuchstaben, einfache Leerzeichen, Grundnorm ohne Ausgabe."""
    s = re.sub(r"\s+", " ", str(text).translate(ZEICHEN).replace("–", "-")).strip().upper()
    s = re.sub(r":.*$", "", s)                                  # Ausgabe
    s = re.sub(r" ?(?:BERICHTIGUNG|/BER\.?) ?\d+.*$", "", s)    # Berichtigung
    s = re.sub(r"[/-]A\d+\b.*$", "", s)                         # Änderung
    s = re.sub(r"\s*/\s*", "/", s)
    s = re.sub(r"^DIN[ /-](TS|SPEC)\b", r"DIN \1", s)           # DIN-TS, DIN/TS, DIN TS
    s = re.sub(r"[/-]NA\b", "/NA", s)                           # Nationaler Anhang: /NA oder -NA
    s = re.sub(r"(\d) TEIL (\d+)", r"\1-\2", s)                 # alte Schreibweise „DIN 4108 Teil 2“
    return s.strip()


def ausgabe_text(wert) -> str:
    return "" if wert in (None, "") else str(wert).strip()


def nachtraege(liste, art: str) -> list[tuple[str, str, str]]:
    """[(Anzeige, Kennzeichen, Ausgabe)] aus Einträgen wie „A1:2026-09“ oder „Berichtigung 1:2023-04“."""
    ergebnis = []
    for eintrag in liste or []:
        text = str(eintrag).strip()
        teil, _, datum = text.partition(":")
        if art == "aenderung":
            kennz = (re.search(r"A\d+", teil.upper()) or re.search(r"\d+", teil))
            kennz = kennz.group(0) if kennz else teil.upper()
            kennz = kennz if kennz.startswith("A") else f"A{kennz}"
        else:
            nummer = re.search(r"\d+", teil)
            kennz = nummer.group(0) if nummer else teil
        ergebnis.append((text, kennz, datum.strip()))
    return ergebnis


def vergleichen(genannt: str, neueste: str) -> int:
    """-1 genannte Ausgabe älter, 0 gleich, 1 neuer. Nur ein Jahr genannt: Vergleich nach Jahren."""
    if len(genannt) == 4 or len(neueste) == 4:
        genannt, neueste = genannt[:4], neueste[:4]
    return (genannt > neueste) - (genannt < neueste)


def index_laden(pfad: Path | None) -> dict:
    if pfad is None or not pfad.is_file():
        raise IndexFehlt("Datei fehlt")
    try:
        import yaml  # im Workflow installiert
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except Exception as fehler:  # noqa: BLE001 – jede Störung heißt: nicht geprüft
        raise IndexFehlt(f"unlesbar ({type(fehler).__name__})") from fehler
    if not isinstance(daten, dict) or not isinstance(daten.get("normen"), list):
        raise IndexFehlt("ohne Liste „normen“")
    normen = {}
    for eintrag in daten["normen"]:
        if isinstance(eintrag, dict) and (eintrag.get("schluessel") or eintrag.get("norm")):
            normen[schluessel(eintrag.get("schluessel") or eintrag["norm"])] = eintrag
    return {"stand": ausgabe_text(daten.get("stand_index")) or "unbekannt", "normen": normen}


def satz_um(zeile: str, stelle: int) -> tuple[int, int]:
    """Anfang und Ende des Satzes, in dem die Stelle steht (Abkürzungen wie „z. B.“ oder „Rn. 12“
    beenden keinen Satz)."""
    anfang, ende = 0, len(zeile)
    for grenze in SATZGRENZE.finditer(zeile):
        wort = re.search(r"(\w+)\.$", zeile[:grenze.start()])
        if wort and (wort.group(1).lower() in ABKUERZUNGEN or wort.group(1).isdigit()):
            continue
        if grenze.end() <= stelle:
            anfang = grenze.end()
        elif grenze.start() >= stelle:
            ende = grenze.start()
            break
    return anfang, ende


def historisch(maskiert: str, start: int, ende: int, teil_anfang: int, teil_ende: int,
               voriges_ende: int, naechster_anfang: int, jahr: str) -> bool:
    """Kennzeichnet der Satzteil die Nennung [start, ende) als frühere oder stichtagsbezogene Fassung?

    maskiert: Text mit allen Nennungen durch \\x01 ersetzt; voriges_ende / naechster_anfang:
    Grenzen der benachbarten Nennungen im selben Satzteil.
    """
    if STATUS_NACH.search(maskiert, ende, naechster_anfang) or STATUS_VOR.search(maskiert[voriges_ende:start]):
        return False                      # ausdrücklich als geltend dargestellt
    teil = maskiert[teil_anfang:teil_ende]
    if HISTORISCH.search(teil):
        return True
    if jahr and any(j == jahr[:4] for j in JAHRMARKE.findall(teil)):
        return True
    davor = list(ERSETZT_VOR.finditer(maskiert, teil_anfang, start))
    if davor and AUFZAEHLUNG.fullmatch(maskiert[davor[-1].end():start]):
        return True                       # „… ersetzt DIN …:2013-04 und DIN …“
    danach = ERSETZT_NACH.search(maskiert, ende, teil_ende)
    return bool(danach and AUFZAEHLUNG.fullmatch(maskiert[ende:danach.start()]))


def zitate_finden(text: str) -> list[dict]:
    """Alle Normzitate eines Entwurfs mit Zeile, Schlüssel, Ausgabe und Satzumfeld."""
    zeilen = text.replace("\r\n", "\n").split("\n")
    ende_kopf = 0
    if zeilen and zeilen[0].strip() == "---":
        ende_kopf = next((i + 1 for i in range(1, len(zeilen)) if zeilen[i].strip() == "---"), 0)
    zitate, im_feld = [], False
    for nr, roh in enumerate(zeilen, 1):
        zeile = ADRESSE.sub(" ", LINK.sub(r"\1", roh)).translate(ZEICHEN)
        if nr <= ende_kopf:
            # Im Dateikopf zählt nur das Feld regelwerke_bestaetigt (auch als Liste darunter).
            if re.match(r"^\S[^:]*:", zeile):
                im_feld = zeile.startswith("regelwerke_bestaetigt:")
            if not im_feld:
                continue
            teile = [(m.start(), m.end()) for m in re.finditer(r"[^,]+", zeile)]
        else:
            teile = [(0, len(zeile))]
        for von, bis in teile:
            abschnitt = zeile[von:bis]
            treffer = list(NORM.finditer(abschnitt))
            # Nennungen maskiert: Kennwörter werden nur außerhalb der Nennungen gesucht, und
            # weitere Nennungen zählen zwischen Kennwort und Nennung als Aufzählung.
            maskiert = abschnitt
            for m in treffer:
                maskiert = maskiert[:m.start()] + "\x01" * (m.end() - m.start()) + maskiert[m.end():]
            for k, m in enumerate(treffer):
                jahr = next((m.group(g) for g in JAHRGRUPPEN if m.group(g)), "")
                monat = next((m.group(g) for g in MONATSGRUPPEN if m.group(g)), "")
                if m.group("monat") or m.group("monat2"):
                    monat = MONATE[m.group("monat") or m.group("monat2")]
                ausgabe = f"{jahr}-{monat}" if jahr and monat else jahr
                grund = f"{m.group('reihe')} {m.group('nummer')}{m.group('zusatz')}{m.group('na') or ''}"
                anzeige = grund + (f"/{m.group('aenderung')}" if m.group("aenderung") else "") + (
                    f" Berichtigung {m.group('berichtigung')}" if m.group("berichtigung") else "")
                anfang, ende = (0, len(abschnitt)) if nr <= ende_kopf else satz_um(abschnitt, m.start())
                # Satzteil: bis zum Semikolon („DIN …:2013-04; sie ersetzt keine Vereinbarung“)
                teil_anfang = max(anfang, maskiert.rfind(";", anfang, m.start()) + 1)
                teil_ende = maskiert.find(";", m.end(), ende)
                teil_ende = ende if teil_ende < 0 else teil_ende
                vorige = [t.end() for t in treffer[:k] if t.end() > teil_anfang]
                naechste = [t.start() for t in treffer[k + 1:] if t.start() < teil_ende]
                zitate.append({"zeile": nr, "regelwerk": anzeige, "schluessel": schluessel(grund),
                               "reihe": m.group("reihe"), "ausgabe": ausgabe,
                               "aenderung": m.group("aenderung") or "",
                               "berichtigung": m.group("berichtigung") or "",
                               "historisch": historisch(maskiert, m.start(), m.end(), teil_anfang, teil_ende,
                                                        vorige[-1] if vorige else teil_anfang,
                                                        naechste[0] if naechste else teil_ende, jahr),
                               "satz": (nr, von + anfang), "zeilentext": abschnitt})
    # Nennt ein Satz mehrere Ausgaben derselben Norm („DIN 18202:2019-07 „…“, ersetzt
    # DIN 18202:2013-04“), stellt er die neueste davon als geltend dar: Wörter wie
    # „ersetzt“ kennzeichnen dann nur die älteren als frühere Fassung.
    saetze: dict[tuple, list[dict]] = {}
    for z in zitate:
        if z["ausgabe"] and not z["aenderung"] and not z["berichtigung"]:
            saetze.setdefault((z["satz"], z["schluessel"]), []).append(z)
    for gruppe in saetze.values():
        ausgaben = {z["ausgabe"] for z in gruppe}
        if len(ausgaben) > 1:
            neueste = max(ausgaben)
            for z in gruppe:
                if z["ausgabe"] == neueste:
                    z["historisch"] = False
    return zitate


def eintrag_suchen(index: dict, zitat: dict) -> dict | None:
    eintrag = index["normen"].get(zitat["schluessel"])
    if eintrag is None and re.match(r"VDI/[A-Z]+ ", zitat["schluessel"]):
        # VDI/GVSS 6202 Blatt 1 steht im Index womöglich als VDI 6202 Blatt 1
        eintrag = index["normen"].get(re.sub(r"^VDI/[A-Z]+ ", "VDI ", zitat["schluessel"]))
    return eintrag


def befund(datei: str, z: dict, neueste: str, stufe: str, ergebnis: str, genannt: str | None = None) -> dict:
    return {"datei": datei, "zeile": z["zeile"], "regelwerk": z["regelwerk"],
            "genannt": z["ausgabe"] if genannt is None else genannt, "neueste": neueste,
            "stufe": stufe, "ergebnis": ergebnis}


def entwurf_pruefen(datei: str, text: str, index: dict) -> list[dict]:
    """Ergebniszeilen eines Entwurfs: FEHLER, HINWEIS und OK (aktuelle Ausgabe)."""
    zitate = zitate_finden(text)
    zeilen: list[dict] = []
    gruppen: dict[str, list[dict]] = {}
    for z in zitate:
        gruppen.setdefault(z["schluessel"], []).append(z)

    for gruppe in gruppen.values():
        erstes = gruppe[0]
        eintrag = eintrag_suchen(index, erstes)
        if eintrag is None:
            genannt = ", ".join(dict.fromkeys(z["ausgabe"] for z in gruppe if z["ausgabe"]))
            zeilen.append(befund(datei, erstes, "–", "HINWEIS",
                                 "nicht im Normindex der Fachbibliothek – Status bei DIN Media prüfen", genannt))
            continue
        neueste = ausgabe_text(eintrag.get("neueste"))
        if eintrag.get("pruefen"):
            grund = "; ".join(str(g) for g in (eintrag.get("pruefgrund") or []))
            zeilen.append(befund(datei, erstes, neueste, "HINWEIS",
                                 "Indexeintrag auffällig (pruefen)" + (f": {grund}" if grund else "")
                                 + f" – {DIN_MEDIA}", ""))
        if not neueste:
            zeilen.append(befund(datei, erstes, "–", "HINWEIS", f"Index ohne neueste Ausgabe – {DIN_MEDIA}", ""))
            continue

        # Ohne Ausgabe genannt: nur ein Hinweis je Norm, und nur, wenn der Beitrag die
        # geltende Ausgabe nirgends nennt (Fußnote oder Dateikopf genügt).
        grundzitate = [z for z in gruppe if not z["aenderung"] and not z["berichtigung"]]
        ohne = [z for z in grundzitate if not z["ausgabe"]]
        if ohne and not any(z["ausgabe"] and not z["historisch"] for z in grundzitate):
            zeilen.append(befund(datei, ohne[0], neueste, "HINWEIS",
                                 f"ohne Ausgabe genannt – neueste Ausgabe {neueste} angeben"))
        gesehen = set()
        nachtrag_listen = {"aenderung": nachtraege(eintrag.get("aenderungen"), "aenderung"),
                           "berichtigung": nachtraege(eintrag.get("berichtigungen"), "berichtigung")}
        for z in gruppe:
            if not z["ausgabe"]:
                continue
            art = "aenderung" if z["aenderung"] else "berichtigung" if z["berichtigung"] else ""
            vergleich = vergleichen(z["ausgabe"], neueste)
            if vergleich < 0:
                if z["historisch"]:
                    merkmal = ("historisch", z["regelwerk"], z["ausgabe"])
                    if merkmal not in gesehen:
                        gesehen.add(merkmal)
                        zeilen.append(befund(datei, z, neueste, "HINWEIS",
                                             "ältere Ausgabe, im Satz als frühere oder stichtagsbezogene "
                                             "Fassung gekennzeichnet"))
                else:
                    zeilen.append(befund(datei, z, neueste, "FEHLER",
                                         f"ältere Ausgabe – neueste in der Fachbibliothek ist {neueste}; "
                                         "aktualisieren oder im Satz als frühere Fassung kennzeichnen"))
                continue
            merkmal = ("aktuell", z["regelwerk"], z["ausgabe"])
            if merkmal in gesehen:
                continue
            gesehen.add(merkmal)
            if art:
                kennz = z["aenderung"] or z["berichtigung"]
                passend = [a for a, k, d in nachtrag_listen[art]
                           if k == kennz and (not d or not vergleichen(z["ausgabe"], d))]
                if passend:
                    zeilen.append(befund(datei, z, neueste, "OK", f"{passend[0]} laut Fachbibliothek aktuell"))
                else:
                    liste = ", ".join(a for a, _, _ in nachtrag_listen[art]) or "keine"
                    zeilen.append(befund(datei, z, neueste, "HINWEIS",
                                         f"{'Änderung' if art == 'aenderung' else 'Berichtigung'} nicht im Normindex "
                                         f"(dort: {liste}) – Status bei DIN Media prüfen"))
            elif vergleich == 0:
                zeilen.append(befund(datei, z, neueste, "OK", "aktuell laut Fachbibliothek"))
            else:
                zeilen.append(befund(datei, z, neueste, "HINWEIS",
                                     "genannte Ausgabe neuer als die Fachbibliothek – Bibliothek ggf. veraltet, "
                                     + DIN_MEDIA))

        # Änderungen und Berichtigungen zur neuesten Ausgabe, die der Beitrag nicht nennt
        if any(not z["historisch"] for z in gruppe):
            text_der_zeilen = " ".join(z["zeilentext"] for z in gruppe)
            fehlend = []
            for a, kennz, datum in nachtrag_listen["aenderung"]:
                genannt = any(z["aenderung"] == kennz for z in gruppe) or re.search(
                    rf"\b{re.escape(kennz)}\b", text_der_zeilen)
                if not genannt and (not datum or vergleichen(datum, neueste) >= 0):
                    fehlend.append(a)
            for a, kennz, datum in nachtrag_listen["berichtigung"]:
                genannt = any(z["berichtigung"] == kennz for z in gruppe) or re.search(
                    rf"(?:Berichtigung|Ber\.?)\s?{re.escape(kennz)}\b", text_der_zeilen)
                if not genannt and (not datum or vergleichen(datum, neueste) >= 0):
                    fehlend.append(a)
            if fehlend:
                zeilen.append(befund(datei, erstes, neueste, "HINWEIS",
                                     f"Änderung/Berichtigung vorhanden, aber nicht genannt: {', '.join(fehlend)}",
                                     ", ".join(dict.fromkeys(z["ausgabe"] for z in gruppe if z["ausgabe"]))))
    zeilen.sort(key=lambda e: e["zeile"])
    return zeilen


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def zelle(wert) -> str:
    return "–" if wert in (None, "") else str(wert).replace("|", "\\|")


def bericht_bilden(ergebnis: dict) -> str:
    zeilen = [UEBERSCHRIFT, ""]
    if not ergebnis["geprueft"]:
        return "\n".join(zeilen + [ergebnis["meldung"], "", f"Grund: {ergebnis['grund']}.", ""])
    zeilen += [f"Abgleich mit dem Normindex der Fachbibliothek (Stand {ergebnis['stand_index']}, "
               f"{ergebnis['normen_im_index']} Normen) – nur Metadaten, keine Normtexte. "
               f"Maßgeblich bleibt der Status bei DIN Media.", ""]
    if not ergebnis["zeilen"]:
        return "\n".join(zeilen + ["Keine Normzitate gefunden.", ""])
    zeilen += ["| Datei | Zeile | Regelwerk | genannte Ausgabe | neueste in der Fachbibliothek | Ergebnis |",
               "|---|---|---|---|---|---|"]
    for e in ergebnis["zeilen"]:
        text = e["ergebnis"] if e["stufe"] == "OK" else f"{e['stufe']}: {e['ergebnis']}"
        werte = (e["datei"], e["zeile"], e["regelwerk"], e["genannt"], e["neueste"], text)
        zeilen.append("| " + " | ".join(zelle(w) for w in werte) + " |")
    zeilen += ["", f"{ergebnis['fehler']} Fehler, {ergebnis['hinweise']} Hinweise. Ein FEHLER sperrt den Entwurf: "
               "neueste Ausgabe nennen oder im Satz ausdrücklich als frühere Fassung kennzeichnen "
               "(etwa „zum Abnahmezeitpunkt galt …“)."]
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
    parser.add_argument("--ausgaben", type=Path, help="normen/ausgaben.yml der Fachbibliothek")
    parser.add_argument("--bericht", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    try:
        index = index_laden(args.ausgaben)
        texte = [(p.as_posix(), p.read_text(encoding="utf-8")) for p in args.entwuerfe]
    except IndexFehlt as fehler:
        ergebnis = {"geprueft": False, "meldung": NICHT_GEPRUEFT, "grund": f"Normindex: {fehler}"}
    except (OSError, UnicodeDecodeError) as fehler:
        ergebnis = {"geprueft": False, "meldung": "Nicht geprüft: Entwurf nicht lesbar.",
                    "grund": type(fehler).__name__}
    else:
        alle = [e for datei, text in texte for e in entwurf_pruefen(datei, text, index)]
        ergebnis = {"geprueft": True, "stand_index": index["stand"], "normen_im_index": len(index["normen"]),
                    "entwuerfe": [d for d, _ in texte],
                    "fehler": sum(e["stufe"] == "FEHLER" for e in alle),
                    "hinweise": sum(e["stufe"] == "HINWEIS" for e in alle), "zeilen": alle}

    schreiben(args.bericht, bericht_bilden(ergebnis))
    schreiben(args.json, json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n")
    if not ergebnis["geprueft"]:
        print(f"{ergebnis['meldung']} ({ergebnis['grund']})")
        print("fehler=nicht-geprueft")
        return 2

    anzahl = len(ergebnis["entwuerfe"])
    print(f"Normstand-Prüfung: {anzahl} {'Entwurf' if anzahl == 1 else 'Entwürfe'} gegen den Normindex "
          f"(Stand {ergebnis['stand_index']}, {ergebnis['normen_im_index']} Normen). {DIN_MEDIA}.")
    for e in ergebnis["zeilen"]:
        if e["stufe"] != "OK":
            print(f"{e['stufe']} {e['datei']}:{e['zeile']} {e['regelwerk']} · genannt {e['genannt'] or '–'} · "
                  f"neueste {e['neueste'] or '–'} · {e['ergebnis']}")
    print(f"fehler={ergebnis['fehler']} hinweise={ergebnis['hinweise']}")
    return 1 if ergebnis["fehler"] else 0


if __name__ == "__main__":
    sys.exit(main())
