#!/usr/bin/env python3
"""Sammelt Signale für den Trend-Scout – ohne KI, ohne Kosten – und schreibt sie als Markdown.

1. Saison: was in diesem Monat erfahrungsgemäß gefragt ist.
2. Wikipedia-Seitenaufrufe (offizielle Wikimedia-Schnittstelle, ohne Schlüssel) zu
   den Begriffen in tools/trend_begriffe.yml: die letzten 14 Tage gegenüber den
   28 Tagen davor und gegenüber demselben Zeitraum im Vorjahr. Ein Anstieg zeigt
   saisonales oder aktuelles Interesse – keine Klickzahlen aus Suchmaschinen oder
   sozialen Netzen, die sind nicht frei zugänglich.
3. Was es schon gibt: Titel aller Entwürfe und Beiträge (entwuerfe/) und – mit
   NOTION_TOKEN – aller Themen in „Trendthemen Bauwesen“ und im Themenspeicher.

Aufruf: python tools/trend_signale.py --ausgabe <datei.md>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trend_notion  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
BEGRIFFE = Path(__file__).resolve().parent / "trend_begriffe.yml"
KOPF = {"User-Agent": "BIB-Trendscout/1.0 (https://ing-bassam.de/#kontakt; einmal pro Woche)"}
MINDESTENS = 100            # Aufrufe in 14 Tagen, darunter ist ein Anstieg Zufall

SAISON = {
    1: "Frost und Rohrbruch, Heizkostenabrechnungen, Änderungen zum Jahresbeginn (CO2-Preis, Förderung, Gesetze)",
    2: "Frostschäden, Schimmel durch Heizen und Lüften, Heizkosten, Planung der Bausaison",
    3: "Beginn der Bausaison, Hauskauf und Besichtigung, Schäden nach Winterstürmen",
    4: "Bausaison, Abnahme und Mängel, Dach und Fassade nach dem Winter",
    5: "Bausaison, feuchte Keller, Starkregenvorsorge, Förderanträge vor Baubeginn",
    6: "Sommerlicher Wärmeschutz und Hitze, Starkregen und Überflutung",
    7: "Hitze im Gebäude, Starkregen, Rückstau, Urlaubszeit auf Baustellen",
    8: "Starkregen und Wasserschäden, Vorbereitung der Heizperiode",
    9: "Beginn der Heizperiode, Heizungscheck, Schimmel und Lüften, Fristen zum Jahresende",
    10: "Heizperiode, Schimmel und Kondensat, Wärmebrücken, Fristen zum Jahresende (Förderung, Steuer)",
    11: "Schimmel und Lüften, Heizkosten, Jahresend-Fristen, Änderungen zum Jahreswechsel",
    12: "Änderungen zum Jahreswechsel (CO2-Preis, Förderung, Gesetze), Frost und Rohrbruch",
}


def aufrufe(titel: str, von: date, bis: date) -> dict[str, int] | None:
    """Tägliche Aufrufe eines Artikels der deutschen Wikipedia, oder None ohne Artikel."""
    adresse = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/de.wikipedia.org/all-access/user/"
               f"{urllib.parse.quote(titel.replace(' ', '_'), safe='')}/daily/{von:%Y%m%d}/{bis:%Y%m%d}")
    for versuch in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(adresse, headers=KOPF), timeout=30) as antwort:
                return {e["timestamp"][:8]: int(e["views"]) for e in json.load(antwort).get("items", [])}
        except urllib.error.HTTPError as fehler:
            if fehler.code == 404:
                return None
            if versuch == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if versuch == 2:
                raise
        time.sleep(2 + 3 * versuch)
    return None


def summe(werte: dict[str, int], von: date, bis: date) -> int:
    return sum(v for k, v in werte.items() if f"{von:%Y%m%d}" <= k <= f"{bis:%Y%m%d}")


def wikipedia(heute: date) -> tuple[list[dict], list[str]]:
    gestern = heute - timedelta(days=1)
    jetzt = (gestern - timedelta(days=13), gestern)
    davor = (jetzt[0] - timedelta(days=28), jetzt[0] - timedelta(days=1))
    vorjahr = (jetzt[0] - timedelta(days=364), jetzt[1] - timedelta(days=364))
    zeilen, fehlend = [], []
    begriffe = yaml.safe_load(BEGRIFFE.read_text(encoding="utf-8")) or {}
    for kategorie, titel_liste in begriffe.items():
        for titel in titel_liste or []:
            try:
                werte = aufrufe(str(titel), vorjahr[0], gestern)
            except (urllib.error.URLError, TimeoutError, OSError) as fehler:
                fehlend.append(f"{titel} (nicht abrufbar: {fehler})")
                continue
            if werte is None:
                fehlend.append(f"{titel} (kein Artikel unter diesem Titel)")
                continue
            a, b, c = summe(werte, *jetzt), summe(werte, *davor), summe(werte, *vorjahr)
            zeilen.append({"begriff": str(titel), "kategorie": str(kategorie), "aufrufe": a,
                           "monat": a / (b / 2) if b else None, "jahr": a / c if c else None})
    zeilen.sort(key=lambda z: -(z["monat"] or 0))
    return zeilen, fehlend


def entwuerfe() -> list[str]:
    """Titel und Status aller Entwürfe und Beiträge aus entwuerfe/ (Kopf der Datei)."""
    titel = []
    for datei in sorted((WURZEL / "entwuerfe").glob("**/*.md")):
        if datei.name.lower() == "readme.md":
            continue
        kopf = datei.read_text(encoding="utf-8", errors="replace").split("\n---", 1)[0]
        t = re.search(r"(?m)^titel:\s*\"?(.*?)\"?\s*$", kopf)
        s = re.search(r"(?m)^status:\s*(.*?)\s*$", kopf)
        if t and t.group(1):
            titel.append(f"{t.group(1)} ({s.group(1) if s else 'ohne Status'})")
    return titel


def faktor(wert: float | None) -> str:
    return "–" if wert is None else f"{wert:.2f}×" + (" ↑" if wert >= 1.15 else "")


def markdown(heute: date) -> str:
    zeilen = [f"# Signale für den Trend-Scout – Stand {heute:%d.%m.%Y}", "",
              "## Saison", "", f"{SAISON[heute.month]}.", "",
              "## Wikipedia-Seitenaufrufe der letzten 14 Tage", "",
              "Anstieg gegenüber den 28 Tagen davor (auf 14 Tage umgerechnet) und gegenüber demselben "
              "Zeitraum im Vorjahr. Wikipedia verliert insgesamt Leser; ein Vorjahreswert unter 1 ist "
              f"deshalb normal. Nur Begriffe mit mindestens {MINDESTENS} Aufrufen.", "",
              "| Begriff | Kategorie | Aufrufe | ggü. Vormonat | ggü. Vorjahr |", "|---|---|---:|---:|---:|"]
    daten, fehlend = wikipedia(heute)
    for z in daten:
        if z["aufrufe"] >= MINDESTENS:
            zeilen.append(f"| {z['begriff']} | {z['kategorie']} | {z['aufrufe']} | {faktor(z['monat'])} | "
                          f"{faktor(z['jahr'])} |")
    if fehlend:
        zeilen += ["", "Nicht ausgewertet: " + "; ".join(fehlend)]

    zeilen += ["", "## Schon vorhanden – nicht noch einmal vorschlagen", "",
               "### Beiträge und Entwürfe auf ing-bassam.de", ""]
    zeilen += [f"- {t}" for t in entwuerfe()] or ["- (keine gefunden)"]
    zeilen += ["", "### Themen in Notion", ""]
    try:
        notion = trend_notion.bestand()
        zeilen += [f"- [{z['quelle']} · {z['status'] or 'ohne Status'}] {z['titel']}" for z in notion] or ["- (keine)"]
    except trend_notion.NotionFehler as fehler:
        zeilen.append(f"- Notion nicht abgefragt: {fehler}")
        print(f"::warning title=Trend-Agent::Notion nicht abgefragt – Dubletten prüft erst der letzte Schritt ({fehler})")
    return "\n".join(zeilen) + "\n"


def main(argumente: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    zerleger.add_argument("--ausgabe", type=Path, required=True)
    zerleger.add_argument("--heute", type=date.fromisoformat, default=None)
    a = zerleger.parse_args(argumente)
    heute = a.heute or trend_notion.heute_berlin()
    text = markdown(heute)
    a.ausgabe.parent.mkdir(parents=True, exist_ok=True)
    a.ausgabe.write_text(text, encoding="utf-8")
    print(f"Signale geschrieben: {a.ausgabe} ({len(text.splitlines())} Zeilen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
