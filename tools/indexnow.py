#!/usr/bin/env python3
"""Meldet neue und geänderte Seiten per IndexNow an Suchmaschinen.

IndexNow ist ein offenes Protokoll: Die Website teilt Bing und den übrigen
teilnehmenden Suchmaschinen mit, welche Adressen neu sind oder sich geändert
haben, statt zu warten, bis deren Crawler von selbst vorbeikommen. Microsoft
Copilot baut auf dem Bing-Index auf. Google nimmt nicht teil; dort wirken
Sitemap und Search Console.

Übertragen werden nur öffentliche Adressen aus der Sitemap – Entwürfe mit
noindex stehen dort nie –, keine Besucherdaten. Dass die Meldung von der
Website stammt, weist die Schlüsseldatei <schlüssel>.txt im Wurzelverzeichnis
nach. Der Schlüssel ist kein Geheimnis; er muss öffentlich abrufbar sein.

Aufruf:
    python tools/indexnow.py --vorher <alte-sitemap.xml>   neue und geänderte Seiten
    python tools/indexnow.py --seit 8                       Seiten mit Stand der letzten 8 Tage
    python tools/indexnow.py --alle                         alle Seiten der Sitemap

Zusätzlich:
    --warten <Sekunden>  so lange warten, bis die Website Schlüsseldatei und
                         neue Sitemap ausliefert (Standard 600, 0 = nicht warten)
    --probe              nur anzeigen, was gemeldet würde

Rückgabewert 0 bei Erfolg oder wenn nichts zu melden ist, 1 bei einem Fehler.
Der Seitenbau ruft das Skript mit continue-on-error auf: Eine gescheiterte
Meldung darf nie den Bau der Seiten aufhalten.
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

WURZEL = Path(__file__).resolve().parent.parent
SITEMAP = WURZEL / "sitemap.xml"
BASIS_URL = "https://ing-bassam.de"
HOST = "ing-bassam.de"
# Gemeinsamer Endpunkt; er gibt die Meldung an alle teilnehmenden
# Suchmaschinen weiter.
ENDPUNKT = "https://api.indexnow.org/indexnow"
KENNUNG = "BIB-Seitenbau/1.0 (+https://ing-bassam.de)"

BEDEUTUNG = {
    200: "angenommen",
    202: "angenommen, der Schlüssel wird noch geprüft",
    400: "ungültiges Format",
    403: "Schlüssel ungültig oder Schlüsseldatei nicht gefunden",
    422: "Adressen gehören nicht zur Website oder der Schlüssel passt nicht",
    429: "zu viele Meldungen – die Suchmaschine vermutet Spam",
}


def schluessel() -> str:
    """Der Schlüssel steht als Name und Inhalt der Datei <schlüssel>.txt."""
    for datei in sorted(WURZEL.glob("*.txt")):
        if re.fullmatch(r"[0-9a-f]{32}", datei.stem) and \
                datei.read_text(encoding="utf-8").strip() == datei.stem:
            return datei.stem
    raise SystemExit("FEHLER: Keine IndexNow-Schlüsseldatei im Wurzelverzeichnis gefunden.")


def eintraege(text: str) -> dict[str, str]:
    """Adresse und lastmod aus einer Sitemap."""
    paare = re.findall(r"<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>", text, re.S)
    return {ort.strip(): stand.strip() for ort, stand in paare}


def abrufen(url: str) -> tuple[int, str]:
    anfrage = urllib.request.Request(url, headers={"User-Agent": KENNUNG,
                                                   "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            return antwort.status, antwort.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as fehler:
        return fehler.code, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, ""


def warten_bis_online(ziel: dict[str, str], key: str, frist: int) -> bool:
    """Wartet, bis die Website Schlüsseldatei und neue Sitemap ausliefert.

    GitHub Pages veröffentlicht erst einige Minuten nach dem Push. Wer vorher
    meldet, schickt die Suchmaschine auf die alte Fassung oder auf einen 404.
    Der Zusatz ?v=… umgeht den Zwischenspeicher der Auslieferung.
    """
    ende = time.monotonic() + frist
    while True:
        marke = int(time.time())
        status_k, inhalt_k = abrufen(f"{BASIS_URL}/{key}.txt?v={marke}")
        status_s, inhalt_s = abrufen(f"{BASIS_URL}/sitemap.xml?v={marke}")
        live = eintraege(inhalt_s) if status_s == 200 else {}
        schluessel_da = status_k == 200 and inhalt_k.strip() == key
        sitemap_neu = all(live.get(url) == stand for url, stand in ziel.items())
        if schluessel_da and sitemap_neu:
            print("Website liefert den neuen Stand aus.")
            return True
        if time.monotonic() >= ende:
            print(f"Hinweis: nach {frist} Sekunden noch nicht vollständig online "
                  f"(Schlüsseldatei {'ok' if schluessel_da else 'fehlt'}, "
                  f"Sitemap {'neu' if sitemap_neu else 'alt'}). Es wird trotzdem gemeldet.")
            return False
        time.sleep(20)


def melden(adressen: list[str], key: str) -> int:
    koerper = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASIS_URL}/{key}.txt",
        "urlList": adressen,
    }).encode("utf-8")
    anfrage = urllib.request.Request(
        ENDPUNKT, data=koerper, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": KENNUNG})
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            status = antwort.status
    except urllib.error.HTTPError as fehler:
        status = fehler.code
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        print(f"FEHLER: IndexNow nicht erreichbar ({fehler})")
        return 1
    if status in (200, 202):
        print(f"IndexNow: {len(adressen)} Adressen gemeldet – {BEDEUTUNG[status]} (HTTP {status}).")
        return 0
    print(f"FEHLER: IndexNow antwortete mit HTTP {status}: "
          f"{BEDEUTUNG.get(status, 'unerwartete Antwort')}.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    auswahl = parser.add_mutually_exclusive_group(required=True)
    auswahl.add_argument("--vorher", type=Path, help="Sitemap vor der Änderung")
    auswahl.add_argument("--seit", type=int, help="Seiten mit Stand der letzten n Tage")
    auswahl.add_argument("--alle", action="store_true", help="alle Seiten der Sitemap")
    parser.add_argument("--warten", type=int, default=600)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()

    aktuell = eintraege(SITEMAP.read_text(encoding="utf-8"))
    if args.alle:
        ziel = dict(aktuell)
    elif args.seit is not None:
        grenze = (date.today() - timedelta(days=args.seit)).isoformat()
        ziel = {url: stand for url, stand in aktuell.items() if stand >= grenze}
    else:
        vorher = (eintraege(args.vorher.read_text(encoding="utf-8"))
                  if args.vorher.exists() else {})
        ziel = {url: stand for url, stand in aktuell.items() if vorher.get(url) != stand}
    ziel = {url: stand for url, stand in ziel.items()
            if urllib.parse.urlsplit(url).hostname == HOST}

    if not ziel:
        print("Keine neuen oder geänderten Seiten – nichts zu melden.")
        return 0
    print("Zu melden:")
    for url, stand in ziel.items():
        print(f"  {url} (Stand {stand})")
    if args.probe:
        return 0

    key = schluessel()
    if args.warten > 0:
        warten_bis_online(ziel, key, args.warten)
    return melden(list(ziel), key)


if __name__ == "__main__":
    sys.exit(main())
