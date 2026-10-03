#!/usr/bin/env python3
"""Notion-Anbindung für die Trendthemen (Workflow „Trend-Agent“: Themensuche und Entwurf).

Befehle:
    offene                       Zahl der freigegebenen Trendthemen ohne Entwurf
    staerkstes                   das stärkste offene Thema ohne Doppelung („seite=<id>“,
                                 „titel=<Titel>“) – oder nichts; Doppelungen bekommen in
                                 Notion den Status „Doppelung“ (tools/doppelungen.py)
    bestand                      Titel aller Trendthemen und aller Themen des Themenspeichers
    vorschlaege DATEI [--max N]  legt die Vorschläge des Trend-Scouts (JSON) als Seiten mit
                                 Status „Vorschlag“ an – geprüft und ohne Dubletten, auch
                                 nicht zu vorhandenen Beiträgen und Entwürfen
    shorts --seite ID --datei MD [--pr URL] [--warnung TEXT]
                                 hängt das Shorts-Paket (Markdown) an die Seite des Themas an
                                 und setzt das Häkchen „Shorts-Paket“

Protokoll und Zusammenfassung des Laufs sind öffentlich: Titel neuer oder
übersprungener Vorschläge stehen dort nicht (Redaktionsplan), nur Nummern,
Gründe und Notion-Adressen ohne Titel.

Das Secret NOTION_TOKEN kommt aus der Umgebung und wird nie ausgegeben. Die
Integration braucht die Fähigkeiten „Inhalte lesen“, „Inhalte aktualisieren“
und „Inhalte einfügen“ und muss mit beiden Datenbanken verbunden sein.
Benötigt nur die Standardbibliothek.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

NOTION_VERSION = "2025-09-03"
TRENDTHEMEN = "a744bdd5-1831-423c-8bb4-3c354fdaf149"        # Data Source „Trendthemen Bauwesen“
THEMENSPEICHER = "532c3c18-5d73-4312-89f6-a2a4035b981d"     # Data Source „Themenspeicher Fachartikel“

# Erlaubte Werte – wie in den Notion-Datenbanken
KATEGORIEN = ("Bauphysik", "Bauschäden", "Gutachten & Recht", "Baubetrieb", "Bauherrenwissen",
              "Hausverwaltung & Bestand", "Energie & Förderung")
FORMATE = ("Ratgeber", "Fachbeitrag", "Grundlagen", "Praxisfall", "Checkliste", "Rechtsprechung")
ZIELGRUPPEN = ("Privat", "Gewerblich", "Hausverwaltung", "Wohnungsbaugesellschaft", "Mieter")
LEISTUNGEN = ("Gutachten", "Bauherrenvertretung", "Baubegleitung", "Claim Management",
              "Objektüberwachung LP 8", "Kalkulation", "Energieberatung")
PRIORITAETEN = ("Hoch", "Mittel", "Später")

TEXT_MAX = 1900          # Notion erlaubt 2.000 Zeichen je Textstück


class NotionFehler(RuntimeError):
    pass


def heute_berlin() -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Berlin")).date()
    except Exception:                      # ohne Zeitzonendaten (etwa unter Windows): Sommerzeit annehmen
        return (datetime.now(timezone.utc) + timedelta(hours=2)).date()


def zusammenfassung(zeilen: str) -> None:
    """Text ins Protokoll und – im Workflow – in die Zusammenfassung des Laufs."""
    print(zeilen)
    ziel = os.environ.get("GITHUB_STEP_SUMMARY")
    if ziel:
        with open(ziel, "a", encoding="utf-8") as datei:
            datei.write(zeilen + "\n")


# --------------------------------------------------------------------------
# Notion-API
# --------------------------------------------------------------------------

HINWEISE = {
    400: "Anfrage abgelehnt – meist heißt eine Eigenschaft in Notion anders als erwartet",
    401: "NOTION_TOKEN ungültig, widerrufen oder unvollständig eingefügt",
    403: ("Zugriff verweigert – die Integration ist nicht mit der Datenbank verbunden (Notion: "
          "Datenbank → ··· → Verbindungen) oder ihr fehlt eine Fähigkeit (lesen, aktualisieren, einfügen)"),
    404: "nicht gefunden – Seite/Datenbank gelöscht oder für die Integration nicht freigegeben",
    409: "Konflikt – die Seite wurde gleichzeitig bearbeitet",
    429: "Rate-Limit, auch nach Wiederholungen",
}


def token() -> str:
    wert = "".join(os.environ.get("NOTION_TOKEN", "").split())   # Leerzeichen/Zeilenumbrüche aus dem Secret
    if not wert:
        raise NotionFehler("Secret NOTION_TOKEN fehlt.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", wert):
        raise NotionFehler("Secret NOTION_TOKEN enthält unerwartete Zeichen – bitte neu kopieren und ersetzen.")
    return wert


def anfrage(methode: str, pfad: str, daten: dict | None = None) -> dict:
    kopf = {"Authorization": f"Bearer {token()}", "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"}
    rumpf = json.dumps(daten).encode("utf-8") if daten is not None else None
    for versuch in range(4):
        req = urllib.request.Request(f"https://api.notion.com/v1{pfad}", data=rumpf, headers=kopf, method=methode)
        try:
            with urllib.request.urlopen(req, timeout=60) as antwort:
                return json.load(antwort)
        except urllib.error.HTTPError as fehler:
            if fehler.code in (409, 429, 500, 502, 503, 504) and versuch < 3:
                time.sleep(3 + 4 * versuch)
                continue
            try:
                meldung = json.load(fehler).get("message", "")
            except (ValueError, AttributeError):
                meldung = ""
            raise NotionFehler(f"Notion HTTP {fehler.code} bei {methode} {pfad.split('?')[0]}: "
                               f"{HINWEISE.get(fehler.code, 'unerwarteter Fehler')}"
                               + (f" ({meldung[:200]})" if meldung else "")) from None
        except (urllib.error.URLError, TimeoutError) as fehler:
            if versuch < 3:
                time.sleep(3 + 4 * versuch)
                continue
            raise NotionFehler(f"Keine Verbindung zu Notion ({fehler}).") from None
    raise NotionFehler("Notion nicht erreichbar.")


def abfragen(datenquelle: str, filter_: dict | None = None) -> list[dict]:
    """Alle Seiten einer Datenquelle (mit Blättern), höchstens 2.000."""
    seiten, cursor = [], None
    for _ in range(20):
        rumpf: dict = {"page_size": 100}
        if filter_:
            rumpf["filter"] = filter_
        if cursor:
            rumpf["start_cursor"] = cursor
        antwort = anfrage("POST", f"/data_sources/{datenquelle}/query", rumpf)
        seiten += antwort.get("results") or []
        if not antwort.get("has_more"):
            break
        cursor = antwort.get("next_cursor")
    return seiten


def klartext(eigenschaft: dict | None) -> str:
    if not eigenschaft:
        return ""
    teile = eigenschaft.get("title") or eigenschaft.get("rich_text") or []
    return "".join(t.get("plain_text", "") for t in teile).strip()


# --------------------------------------------------------------------------
# offene, bestand
# --------------------------------------------------------------------------

def offene() -> int:
    filter_ = {"and": [{"property": "Status", "select": {"equals": "Freigegeben"}},
                       {"property": "Entwurf (PR)", "url": {"is_empty": True}}]}
    return len(abfragen(TRENDTHEMEN, filter_))


RANG = {"Hoch": 0, "Mittel": 1, "Später": 2}


def reihenfolge(seiten: list[dict], heute: date) -> list[dict]:
    """Die offenen Themen vom stärksten zum schwächsten: von Hand freigegebene zuerst, dann nach
    Priorität (Hoch → Mittel → Später), dann das, dessen Aktualität am frühesten endet („Gültig
    bis“), dann das älteste. Themen, deren „Gültig bis“ vorbei ist, zählen nicht mehr."""
    kandidaten = []
    for seite in seiten:
        eigenschaften = seite.get("properties") or {}
        gueltig = ((((eigenschaften.get("Gültig bis") or {}).get("date") or {}).get("start")) or "9999-12-31")[:10]
        if gueltig < heute.isoformat():
            continue
        status = ((eigenschaften.get("Status") or {}).get("select") or {}).get("name", "")
        prioritaet = ((eigenschaften.get("Priorität") or {}).get("select") or {}).get("name", "")
        rang = (status != "Freigegeben", RANG.get(prioritaet, 3), gueltig, seite.get("created_time", ""))
        kandidaten.append((rang, seite))
    return [seite for _, seite in sorted(kandidaten, key=lambda k: k[0])]


def auswaehlen(seiten: list[dict], heute: date) -> dict | None:
    """Das stärkste Thema (siehe reihenfolge)."""
    geordnet = reihenfolge(seiten, heute)
    return geordnet[0] if geordnet else None


def staerkstes(heute: date | None = None, zeilen: list[str] | None = None) -> dict | None:
    """Das stärkste offene Trendthema (Status „Vorschlag“ oder „Freigegeben“, noch ohne Entwurf),
    das kein vorhandener Beitrag und kein Entwurf schon abdeckt. Doppelungen bekommen in Notion
    den Status „Doppelung“ (tools/doppelungen.py). Ist der Bestand nicht lesbar, gilt die
    Reihenfolge allein – der Agent prüft dann selbst."""
    filter_ = {"and": [{"or": [{"property": "Status", "select": {"equals": "Freigegeben"}},
                               {"property": "Status", "select": {"equals": "Vorschlag"}}]},
                       {"property": "Entwurf (PR)", "url": {"is_empty": True}}]}
    geordnet = reihenfolge(abfragen(TRENDTHEMEN, filter_), heute or heute_berlin())
    zeilen = zeilen if zeilen is not None else []
    try:
        import doppelungen
        seite, _, protokoll = doppelungen.auswaehlen(geordnet, "trendthemen", doppelungen.bestand_holen(None))
        zeilen += protokoll
        return seite
    except (RuntimeError, OSError, ValueError) as fehler:
        zeilen.append(f"::warning title=Trend-Agent::Doppelungsprüfung nicht möglich ({str(fehler)[:160]}) – "
                      "gewählt wird nach Reihenfolge, der Agent prüft selbst.")
        return geordnet[0] if geordnet else None


def bestand() -> list[dict]:
    """Titel und Status aus Trendthemen und Themenspeicher."""
    zeilen = []
    for name, quelle in (("Trendthemen", TRENDTHEMEN), ("Themenspeicher", THEMENSPEICHER)):
        for seite in abfragen(quelle):
            eigenschaften = seite.get("properties") or {}
            titel = klartext(eigenschaften.get("Thema"))
            if titel:
                zeilen.append({"titel": titel, "quelle": name,
                               "status": ((eigenschaften.get("Status") or {}).get("select") or {}).get("name", "")})
    return zeilen


# --------------------------------------------------------------------------
# Vorschläge des Trend-Scouts
# --------------------------------------------------------------------------

def normiert(text_: str) -> str:
    text_ = text_.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text_ = text_.replace(alt, neu)
    return " ".join(re.findall(r"[a-z0-9]+", text_))


def aehnlich(a: str, b: str) -> bool:
    """Grobe Dublettenprüfung: fast gleicher Titel oder weitgehend dieselben Wörter."""
    na, nb = normiert(a), normiert(b)
    if not na or not nb:
        return False
    if difflib.SequenceMatcher(None, na, nb).ratio() >= 0.82:
        return True
    wa = {w for w in na.split() if len(w) > 3}
    wb = {w for w in nb.split() if len(w) > 3}
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.6


def pruefen(vorschlag: dict) -> tuple[dict | None, str]:
    """Prüft einen Vorschlag gegen die erlaubten Werte. Ergebnis: bereinigter Vorschlag oder Grund."""
    if not isinstance(vorschlag, dict):
        return None, "kein Objekt"
    v = {k: vorschlag.get(k) for k in ("thema", "kernfrage", "format", "kategorie", "leistung", "zielgruppe",
                                       "prioritaet", "anlass", "trendsignal", "hook", "quellen", "gueltig_bis")}
    thema = " ".join(str(v["thema"] or "").split())
    if not thema:
        return None, "Thema fehlt"
    v["thema"] = thema[:120]
    for feld in ("kernfrage", "anlass", "trendsignal", "hook"):
        v[feld] = " ".join(str(v[feld] or "").split())
    if not v["anlass"]:
        return None, f"„{thema}“: Anlass fehlt"
    if v["kategorie"] not in KATEGORIEN:
        return None, f"„{thema}“: unbekannte Kategorie {v['kategorie']!r}"
    if v["format"] not in FORMATE:
        return None, f"„{thema}“: unbekanntes Format {v['format']!r}"
    v["prioritaet"] = v["prioritaet"] if v["prioritaet"] in PRIORITAETEN else "Mittel"
    v["zielgruppe"] = [z for z in (v["zielgruppe"] or []) if z in ZIELGRUPPEN] or ["Privat"]
    v["leistung"] = [l for l in (v["leistung"] or []) if l in LEISTUNGEN]
    v["quellen"] = [q.strip() for q in (v["quellen"] or []) if isinstance(q, str)
                    and re.fullmatch(r"https?://\S+", q.strip())][:6]
    if not v["quellen"]:
        return None, f"„{thema}“: keine gültige Quelle"
    try:
        v["gueltig_bis"] = date.fromisoformat(str(v["gueltig_bis"])[:10]).isoformat()
    except ValueError:
        v["gueltig_bis"] = (heute_berlin() + timedelta(days=60)).isoformat()
    return v, ""


def text(inhalt: str, link: str | None = None) -> dict:
    stueck: dict = {"type": "text", "text": {"content": inhalt[:TEXT_MAX]}}
    if link:
        stueck["text"]["link"] = {"url": link}
    return stueck


def eigenschaften_fuer(v: dict, heute: date) -> dict:
    quellen = []
    for i, url in enumerate(v["quellen"]):
        if i:
            quellen.append(text("\n"))
        quellen.append(text(url, url))
    return {
        "Thema": {"title": [text(v["thema"])]},
        "Status": {"select": {"name": "Vorschlag"}},
        "Herkunft": {"select": {"name": "Trend-Scout"}},
        "Priorität": {"select": {"name": v["prioritaet"]}},
        "Kernfrage": {"rich_text": [text(v["kernfrage"])] if v["kernfrage"] else []},
        "Anlass": {"rich_text": [text(v["anlass"])]},
        "Trendsignal": {"rich_text": [text(v["trendsignal"])] if v["trendsignal"] else []},
        "Hook": {"rich_text": [text(v["hook"])] if v["hook"] else []},
        "Quellen": {"rich_text": quellen},
        "Kategorie": {"select": {"name": v["kategorie"]}},
        "Format": {"select": {"name": v["format"]}},
        "Zielgruppe": {"multi_select": [{"name": z} for z in v["zielgruppe"]]},
        "Leistung": {"multi_select": [{"name": l} for l in v["leistung"]]},
        "Gefunden am": {"date": {"start": heute.isoformat()}},
        "Gültig bis": {"date": {"start": v["gueltig_bis"]}},
    }


def vorschlaege_anlegen(vorschlaege, vorhanden: list[str], maximal: int,
                        anlegen=None, doppelt_zu=None) -> tuple[list[str], list[str]]:
    """Legt bis zu `maximal` neue Vorschläge an. Ergebnis: (angelegt, übersprungen mit Grund) –
    ohne Titel, weil die Zeilen in die öffentliche Zusammenfassung des Laufs gehen.

    vorhanden: Titel der Notion-Themen (grober Titelvergleich, aehnlich).
    doppelt_zu: Prüfung gegen Website und Entwürfe (tools/doppelungen.py) – Funktion, die
    für einen Vorschlag (thema, kernfrage, format) den abdeckenden Beitrag nennt oder "".
    """
    anlegen = anlegen or (lambda props: anfrage("POST", "/pages", {
        "parent": {"type": "data_source_id", "data_source_id": TRENDTHEMEN}, "properties": props}))
    angelegt, uebersprungen = [], []
    titel = list(vorhanden)
    heute = heute_berlin()
    for nummer, roh in enumerate(vorschlaege if isinstance(vorschlaege, list) else [], start=1):
        v, grund = pruefen(roh)
        if v is None:
            uebersprungen.append(f"Vorschlag {nummer}: {re.sub(r'^„[^“]*“: ', '', grund)}")
            continue
        if any(aehnlich(v["thema"], t) for t in titel):
            uebersprungen.append(f"Vorschlag {nummer}: ähnelt einem vorhandenen Notion-Thema")
            continue
        abgedeckt = doppelt_zu(v) if doppelt_zu else ""
        if abgedeckt:
            uebersprungen.append(f"Vorschlag {nummer}: Doppelung zu {abgedeckt}")
            continue
        if len(angelegt) >= maximal:
            uebersprungen.append(f"Vorschlag {nummer}: mehr als {maximal} Vorschläge")
            continue
        seite = anlegen(eigenschaften_fuer(v, heute)) or {}
        adresse = ("https://www.notion.so/" + re.sub(r"[^0-9a-f]", "", seite["id"])) if seite.get("id") else "angelegt"
        angelegt.append(f"[{v['prioritaet']}] {adresse}")
        titel.append(v["thema"])
    return angelegt, uebersprungen


def doppelung_zum_bestand():
    """Prüffunktion für vorschlaege_anlegen: Website und Entwürfe (tools/doppelungen.py).
    Ohne lesbaren Bestand: keine Prüfung (Rückgabe None) – der Titelvergleich bleibt."""
    try:
        import doppelungen
        vorhanden = doppelungen.bestand_holen(None)
    except (RuntimeError, OSError, ValueError) as fehler:
        print(f"::warning title=Trend-Agent::Doppelungsprüfung der Vorschläge nicht möglich ({str(fehler)[:160]}).")
        return None

    def pruefen_(v: dict) -> str:
        thema = {"quelle": "vorschlag", "art": "urteil" if v.get("format") == "Rechtsprechung" else "beitrag",
                 "titel": v["thema"], "kernfrage": v.get("kernfrage", "")}
        ergebnis = doppelungen.Vergleich(vorhanden + [thema]).pruefen(thema, vorhanden)
        return doppelungen.beschreibung(ergebnis["doppelungen"][0][0]) if ergebnis["urteil"] == "doppelung" else ""
    return pruefen_


# --------------------------------------------------------------------------
# Shorts-Paket: Markdown → Notion-Blöcke
# --------------------------------------------------------------------------

def inline(zeile: str) -> list[dict]:
    """**fett** und [Text](https://…) als Notion-Textstücke, alles andere als Klartext.
    Lange Texte werden in Stücke unter 2.000 Zeichen geteilt."""
    stuecke = []
    for teil in re.split(r"(\*\*[^*]+\*\*|\[[^\]]+\]\(https?://[^)\s]+\))", zeile):
        if not teil:
            continue
        fett = re.fullmatch(r"\*\*([^*]+)\*\*", teil)
        link = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", teil)
        if fett:
            inhalt, ziel = fett.group(1), None
        elif link:
            inhalt, ziel = link.group(1), link.group(2)
        else:
            inhalt, ziel = teil, None
        for anfang in range(0, len(inhalt), TEXT_MAX):
            stueck = text(inhalt[anfang:anfang + TEXT_MAX], ziel)
            if fett:
                stueck["annotations"] = {"bold": True}
            stuecke.append(stueck)
    return stuecke or [text("")]


def block(typ: str, zeile: str) -> dict:
    return {"object": "block", "type": typ, typ: {"rich_text": inline(zeile)}}


def bloecke_aus_markdown(markdown: str) -> list[dict]:
    bloecke, absatz = [], []

    def absatz_schliessen():
        if absatz:
            bloecke.append(block("paragraph", " ".join(absatz)))
            absatz.clear()

    for roh in markdown.splitlines():
        zeile = roh.rstrip()
        if not zeile.strip():
            absatz_schliessen()
            continue
        if re.fullmatch(r"\s*(-{3,}|\*{3,})\s*", zeile):
            absatz_schliessen()
            bloecke.append({"object": "block", "type": "divider", "divider": {}})
            continue
        treffer = re.match(r"(#{1,6})\s+(.*)", zeile)
        if treffer:
            absatz_schliessen()
            bloecke.append(block("heading_2" if len(treffer.group(1)) <= 2 else "heading_3", treffer.group(2)))
            continue
        treffer = re.match(r"\s*[-*]\s+(.*)", zeile)
        if treffer:
            absatz_schliessen()
            bloecke.append(block("bulleted_list_item", treffer.group(1)))
            continue
        treffer = re.match(r"\s*\d+[.)]\s+(.*)", zeile)
        if treffer:
            absatz_schliessen()
            bloecke.append(block("numbered_list_item", treffer.group(1)))
            continue
        treffer = re.match(r"\s*>\s?(.*)", zeile)
        if treffer:
            absatz_schliessen()
            bloecke.append(block("quote", treffer.group(1)))
            continue
        absatz.append(zeile.strip())
    absatz_schliessen()
    return bloecke


def shorts_anhaengen(seite: str, markdown: str, pr: str = "", warnung: str = "", senden=None) -> int:
    senden = senden or anfrage
    hinweis = (f"Erstellt am {heute_berlin().strftime('%d.%m.%Y')} aus dem geprüften Artikelentwurf. "
               "Jede Aussage verweist auf eine Fußnote des Artikels – vor dem Dreh bitte gegenlesen.")
    kopf = [block("heading_1", "Shorts-Paket"),
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": [text(hinweis)] + ([text(" Artikelentwurf: "), text(pr, pr)] if pr else [])}}]
    if warnung:
        kopf.append({"object": "block", "type": "callout",
                     "callout": {"rich_text": [text(warnung)], "icon": {"type": "emoji", "emoji": "⚠️"}}})
    alle = kopf + bloecke_aus_markdown(markdown)
    for anfang in range(0, len(alle), 100):
        senden("PATCH", f"/blocks/{seite}/children", {"children": alle[anfang:anfang + 100]})
    senden("PATCH", f"/pages/{seite}", {"properties": {"Shorts-Paket": {"checkbox": True}}})
    return len(alle)


# --------------------------------------------------------------------------

def main(argumente: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    unter = zerleger.add_subparsers(dest="befehl", required=True)
    unter.add_parser("offene")
    unter.add_parser("staerkstes")
    unter.add_parser("bestand")
    p = unter.add_parser("vorschlaege")
    p.add_argument("datei", type=Path)
    p.add_argument("--max", type=int, default=5)
    p = unter.add_parser("shorts")
    p.add_argument("--seite", required=True)
    p.add_argument("--datei", type=Path, required=True)
    p.add_argument("--pr", default="")
    p.add_argument("--warnung", default="")
    a = zerleger.parse_args(argumente)

    try:
        if a.befehl == "offene":
            print(offene())
        elif a.befehl == "staerkstes":
            # Ausgabe für $GITHUB_OUTPUT; ohne offenes Thema bleibt sie leer. Die Protokollzeilen
            # der Doppelungsprüfung nennen nur Seiten-IDs.
            zeilen: list[str] = []
            seite = staerkstes(zeilen=zeilen)
            for zeile in zeilen:
                print(zeile)
            if seite:
                titel = " ".join(klartext((seite.get("properties") or {}).get("Thema")).split())
                print(f"seite={seite['id']}")
                print(f"titel={titel}")
        elif a.befehl == "bestand":
            for zeile in bestand():
                print(f"{zeile['quelle']}\t{zeile['status']}\t{zeile['titel']}")
        elif a.befehl == "vorschlaege":
            try:
                daten = json.loads(a.datei.read_text(encoding="utf-8"))
            except (OSError, ValueError) as fehler:
                print(f"::error title=Trend-Agent::Keine lesbare Vorschlagsdatei ({fehler}).")
                return 1
            vorhanden = [z["titel"] for z in bestand()]
            angelegt, uebersprungen = vorschlaege_anlegen(daten, vorhanden, max(a.max, 1),
                                                          doppelt_zu=doppelung_zum_bestand())
            bericht = f"## Trend-Agent: {len(angelegt)} neue Vorschläge in Notion\n\n"
            bericht += "\n".join(f"- {z}" for z in angelegt) or "_Keine neuen Vorschläge._"
            if uebersprungen:
                bericht += "\n\n**Nicht übernommen:**\n\n" + "\n".join(f"- {z}" for z in uebersprungen)
            zusammenfassung(bericht + "\n")
            if not angelegt:
                print("::warning title=Trend-Agent::Kein neuer Vorschlag angelegt – Einzelheiten in der Zusammenfassung.")
        else:
            anzahl = shorts_anhaengen(a.seite, a.datei.read_text(encoding="utf-8"), a.pr, a.warnung)
            print(f"Shorts-Paket mit {anzahl} Blöcken an die Notion-Seite angehängt.")
    except NotionFehler as fehler:
        print(f"::error title=Notion::{fehler}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
