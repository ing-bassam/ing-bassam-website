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
    python tools/indexnow.py --vergleichen _site --merken <datei>
                                     vor der Auslieferung: Seiten der gebauten Website mit
                                     der Live-Website vergleichen, neue und geänderte merken
    python tools/indexnow.py --liste <datei>                gemerkte Seiten melden (nach der Auslieferung)
    python tools/indexnow.py --vorher <alte-sitemap.xml>   neue und geänderte Seiten laut Sitemap
    python tools/indexnow.py --seit 8                       Seiten mit Stand der letzten 8 Tage
    python tools/indexnow.py --alle                         alle Seiten der Sitemap
                                                            und die Weiterleitungen alter Adressen

Der Workflow „Website ausliefern“ ruft --vergleichen vor und --liste nach der
Veröffentlichung auf. Der Vergleich mit dem, was tatsächlich online ist, findet
auch Seiten, deren Inhalt sich ohne neues Datum geändert hat (Gestaltung,
Verlinkung), und braucht keinen gespeicherten Vorzustand.

Zusätzlich:
    --warten <Sekunden>  so lange warten, bis die Website Schlüsseldatei und
                         neue Sitemap ausliefert (Standard 600, 0 = nicht warten)
    --probe              nur anzeigen, was gemeldet würde

Rückgabewert 0 bei Erfolg oder wenn nichts zu melden ist, 1 bei einem Fehler.
Die Auslieferung ruft das Skript mit continue-on-error auf: Eine gescheiterte
Meldung darf nie die Veröffentlichung der Seiten aufhalten.
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


def datei_zur_adresse(url: str) -> str:
    """https://ing-bassam.de/a/b/ -> a/b/index.html; die Startseite -> index.html."""
    pfad = urllib.parse.urlsplit(url).path.lstrip("/")
    return pfad + "index.html" if pfad == "" or pfad.endswith("/") else pfad


def vergleichen(verzeichnis: Path) -> dict[str, str]:
    """Adressen der gebauten Website, deren Seite live fehlt oder anders aussieht.

    Verglichen wird jede Adresse der neuen Sitemap mit dem, was die Website
    gerade ausliefert – also vor der Veröffentlichung des neuen Stands.
    """
    from concurrent.futures import ThreadPoolExecutor

    neu = eintraege((verzeichnis / "sitemap.xml").read_text(encoding="utf-8"))
    marke = int(time.time())

    def pruefen(url: str) -> str | None:
        datei = verzeichnis / datei_zur_adresse(url)
        if not datei.is_file():
            return None
        status, inhalt = abrufen(f"{url}?v={marke}")
        # Zeilenenden angleichen: read_text liefert immer \n.
        if status != 200 or inhalt.replace("\r\n", "\n") != datei.read_text(encoding="utf-8"):
            return url
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        geaendert = {url for url in pool.map(pruefen, neu) if url}
    return {url: neu[url] for url in neu if url in geaendert}


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


def weiterleitungen() -> list[str]:
    """Adressen der Weiterleitungsseiten im Wurzelverzeichnis (frühere Seiten wie
    impressum.html). Gemeldet, damit Suchmaschinen die Weiterleitung sehen und die
    tote Adresse durch das Ziel ersetzen."""
    adressen = []
    for datei in sorted(WURZEL.glob("*.html")):
        if datei.name in ("index.html", "404.html"):
            continue
        kopf = datei.read_text(encoding="utf-8", errors="replace")[:1500].lower()
        if 'http-equiv="refresh"' in kopf:
            adressen.append(f"https://{HOST}/{datei.name}")
    return adressen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    auswahl = parser.add_mutually_exclusive_group(required=True)
    auswahl.add_argument("--vorher", type=Path, help="Sitemap vor der Änderung")
    auswahl.add_argument("--seit", type=int, help="Seiten mit Stand der letzten n Tage")
    auswahl.add_argument("--alle", action="store_true", help="alle Seiten der Sitemap")
    auswahl.add_argument("--vergleichen", type=Path,
                         help="gebaute Website (z. B. _site) mit der Live-Website vergleichen; mit --merken")
    auswahl.add_argument("--liste", type=Path, help="Datei mit gemerkten Adressen (eine je Zeile) melden")
    parser.add_argument("--merken", type=Path, help="Ziel für die Adressen aus --vergleichen")
    parser.add_argument("--dateien", nargs="*", default=[],
                        help="zusätzlich diese geänderten Seiten melden (Pfade wie index.html oder "
                             "fachwissen/<kurz>/index.html)")
    parser.add_argument("--warten", type=int, default=600)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()

    if args.vergleichen:
        if not args.merken:
            parser.error("--vergleichen braucht --merken <datei>")
        geaendert = vergleichen(args.vergleichen)
        args.merken.write_text("".join(f"{url}\n" for url in geaendert), encoding="utf-8")
        print(f"Neu oder geändert gegenüber der Live-Website: {len(geaendert)} Seiten.")
        for url in geaendert:
            print(f"  {url}")
        return 0

    aktuell = eintraege(SITEMAP.read_text(encoding="utf-8"))
    if args.liste:
        gemerkt = [z.strip() for z in args.liste.read_text(encoding="utf-8").splitlines() if z.strip()] \
            if args.liste.exists() else []
        ziel = {url: aktuell[url] for url in gemerkt if url in aktuell}
    elif args.alle:
        ziel = dict(aktuell)
    elif args.seit is not None:
        grenze = (date.today() - timedelta(days=args.seit)).isoformat()
        ziel = {url: stand for url, stand in aktuell.items() if stand >= grenze}
    else:
        vorher = (eintraege(args.vorher.read_text(encoding="utf-8"))
                  if args.vorher.exists() else {})
        ziel = {url: stand for url, stand in aktuell.items() if vorher.get(url) != stand}
    # Seiten, deren HTML sich geändert hat, ohne dass ihr Stand in der Sitemap
    # neu ist (etwa nach einer Gestaltungsänderung). Gemeldet wird nur, was in
    # der Sitemap steht – Entwürfe mit noindex also nie. Anlass: Ahrefs meldete
    # am 28.09.2026 „Changed pages not submitted to IndexNow“ (30 Seiten).
    for pfad in args.dateien:
        pfad = pfad.replace("\\", "/")
        if pfad.endswith("index.html"):
            url = f"https://{HOST}/" + pfad[: -len("index.html")]
        else:
            continue
        if url in aktuell and url not in ziel:
            ziel[url] = aktuell[url]
    ziel = {url: stand for url, stand in ziel.items()
            if urllib.parse.urlsplit(url).hostname == HOST}

    if not ziel:
        print("Keine neuen oder geänderten Seiten – nichts zu melden.")
        return 0
    print("Zu melden:")
    for url, stand in ziel.items():
        print(f"  {url} (Stand {stand})")

    zusatz = weiterleitungen() if args.alle else []
    for url in zusatz:
        print(f"  {url} (Weiterleitung einer früheren Adresse)")
    if args.probe:
        return 0

    key = schluessel()
    if args.warten > 0:
        warten_bis_online(ziel, key, args.warten)
    return melden(list(ziel) + zusatz, key)


if __name__ == "__main__":
    sys.exit(main())
