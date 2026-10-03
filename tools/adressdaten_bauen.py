#!/usr/bin/env python3
"""Baut die Adress- und Bodenrichtwertdaten für den Wertrechner (wertrechner/data/).

Einmal im Jahr (nach Veröffentlichung der neuen Bodenrichtwerte) ausführen.
Der Browser des Besuchers liest später nur die kleinen JSON-Dateien je
Postleitzahl – er ruft nie einen fremden Dienst auf.

Was das Skript tut:
  1. lädt vier offene Datensätze des Landes Berlin (Lizenz dl-de/zero-2.0):
       - Bodenrichtwerte zum Modellstichtag (01.01.2024, Modellkonformität)
       - Bodenrichtwerte zum aktuellen Stichtag (zur Information)
       - Adressen Berlin (amtliche Adresspunkte mit Koordinaten)
       - Wohnlagen nach Adressen zum Berliner Mietspiegel
  2. ordnet jeden Adresspunkt seiner Bodenrichtwertzone zu (Punkt in Polygon,
     ohne Zusatzbibliothek) und übernimmt die Wohnlage der Adresse
  3. schreibt je Postleitzahl eine kompakte JSON-Datei nach wertrechner/data/adressen/

Aufruf:
    python tools/adressdaten_bauen.py                 kompletter Lauf
    python tools/adressdaten_bauen.py --plz 12487     nur eine PLZ (Test)
    python tools/adressdaten_bauen.py --nur-laden     nur herunterladen

Die Rohdaten (ca. 300 MB) landen im Ordner .wertrechner-cache/ und werden
nicht ins Repository übernommen (.gitignore). Ein zweiter Lauf lädt nichts
neu, solange die Dateien dort liegen; zum Erneuern Ordner löschen.

Aufbau einer PLZ-Datei (alles 0-basiert indiziert, damit sie klein bleibt):
    {
      "plz": "12487",
      "stichtage": {"modell": "2024-01-01", "aktuell": "2026-01-01"},
      "strassen":  ["Straße am Flugplatz", ...],
      "ortsteile": ["Johannisthal", ...],
      "zonen": {"1234": {"modell": {brw, nutzung, gfz}, "aktuell": {...}}, ...},
      "adressen": [[strassenIndex, "6a", "zoneModell", "zoneAktuell", wohnlage, ortsteilIndex], ...]
    }
    wohnlage: 0 = unbekannt, 1 = einfach, 2 = mittel, 3 = gut
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
CACHE = WURZEL / ".wertrechner-cache"
ZIEL = WURZEL / "wertrechner" / "data" / "adressen"

WFS = "https://gdi.berlin.de/services/wfs/"
CRS = "EPSG:25833"            # UTM 33N, Meter – passt zu allen vier Diensten

# Welcher Bodenrichtwert-Stichtag für die Berechnung gilt, legen die Berliner
# Modellbeschreibungen fest (Sachwertfaktoren 2025 und Liegenschaftszinssätze
# 2025: „Bodenrichtwert zum 01.01.2024“). Siehe fachliteratur/MODELL-BERLIN.md.
BRW_MODELL = ("brw2024", "brw2024:brw_2024_vector")
BRW_AKTUELL = ("brw2026", "brw2026:brw2026_vector")
ADRESSEN = ("adressen_berlin", "adressen_berlin:adressen_berlin")
WOHNLAGEN = ("wohnlagenadr2024", "wohnlagenadr2024:wohnlagenadr2024")
WOHNLAGEN_STAND = "Berliner Mietspiegel 2024"

SEITE = 50000                 # Adresspunkte je Anfrage (Paging)
WOHNLAGE_CODE = {"einfach": 1, "mittel": 2, "gut": 3}


# --------------------------------------------------------------------------
# Herunterladen
# --------------------------------------------------------------------------

def laden(url: str, ziel: Path, versuche: int = 3) -> None:
    if ziel.exists() and ziel.stat().st_size > 0:
        return
    ziel.parent.mkdir(parents=True, exist_ok=True)
    for versuch in range(1, versuche + 1):
        try:
            print(f"  lade {ziel.name} …", flush=True)
            anfrage = urllib.request.Request(url, headers={"User-Agent": "ing-bassam-wertrechner/1.0"})
            with urllib.request.urlopen(anfrage, timeout=900) as antwort, open(ziel, "wb") as f:
                while True:
                    teil = antwort.read(1 << 20)
                    if not teil:
                        break
                    f.write(teil)
            return
        except Exception as fehler:  # noqa: BLE001 – Netzfehler sollen wiederholt werden
            if ziel.exists():
                ziel.unlink()
            if versuch == versuche:
                raise
            print(f"  Fehler ({fehler}), neuer Versuch in 10 s", flush=True)
            time.sleep(10)


def wfs_url(dienst: str, typ: str, **extra: str) -> str:
    params = {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": typ, "OUTPUTFORMAT": "application/json", "SRSNAME": CRS,
    }
    params.update(extra)
    return WFS + dienst + "?" + urllib.parse.urlencode(params)


def anzahl(dienst: str, typ: str) -> int:
    url = WFS + dienst + "?" + urllib.parse.urlencode({
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": typ, "RESULTTYPE": "hits"})
    with urllib.request.urlopen(url, timeout=120) as antwort:
        text = antwort.read().decode("utf-8")
    m = re.search(r'numberMatched="(\d+)"', text)
    if not m:
        raise RuntimeError(f"numberMatched nicht gefunden für {typ}")
    return int(m.group(1))


def seitenweise_laden(dienst: str, typ: str, felder: str, name: str) -> list[Path]:
    """Lädt einen großen Punktdatensatz in Seiten zu SEITE Features."""
    gesamt = anzahl(dienst, typ)
    seiten = []
    for start in range(0, gesamt, SEITE):
        ziel = CACHE / f"{name}_{start // SEITE:03d}.json"
        laden(wfs_url(dienst, typ, PROPERTYNAME=felder, COUNT=str(SEITE), STARTINDEX=str(start)), ziel)
        seiten.append(ziel)
    print(f"  {name}: {gesamt} Features laut Dienst, {len(seiten)} Seiten")
    return seiten


def alles_laden() -> dict:
    CACHE.mkdir(exist_ok=True)
    dateien = {}
    for schluessel, (dienst, typ) in (("modell", BRW_MODELL), ("aktuell", BRW_AKTUELL)):
        ziel = CACHE / f"{dienst}.geojson"
        laden(wfs_url(dienst, typ), ziel)
        dateien[schluessel] = ziel
    dateien["adressen"] = seitenweise_laden(*ADRESSEN, "str_name,hnr,hnr_zusatz,plz,ort_name,typ,geom", "adressen")
    dateien["wohnlagen"] = seitenweise_laden(*WOHNLAGEN, "plz,strasse,hnr,wol,geom", "wohnlagen")
    return dateien


# --------------------------------------------------------------------------
# Geometrie: Punkt in Polygon mit Rasterindex (reines Python)
# --------------------------------------------------------------------------

RASTER = 250.0  # Meter je Rasterzelle


def zelle(x: float, y: float) -> tuple[int, int]:
    return (int(x // RASTER), int(y // RASTER))


def punkt_in_ring(x: float, y: float, ring: list) -> bool:
    innen = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            innen = not innen
        j = i
    return innen


class Zonen:
    """Bodenrichtwertzonen eines Stichtags mit Rasterindex für schnelle Suche."""

    def __init__(self, geojson: Path):
        daten = json.loads(geojson.read_text(encoding="utf-8"))
        self.stichtag = None
        self.attribute: dict[str, dict] = {}
        self.polygone: list[tuple[str, list]] = []     # (brwid, [ringe...]) je Einzelpolygon
        self.bbox: list[tuple[float, float, float, float]] = []
        self.index: dict[tuple[int, int], list[int]] = defaultdict(list)

        for f in daten["features"]:
            p = f["properties"]
            brwid = str(p["brwid"])
            self.stichtag = self.stichtag or p.get("stichtag")
            self.attribute[brwid] = {
                "brw": p.get("brw"),
                "nutzung": p.get("nutzung"),
                "gfz": p.get("gfz"),
                "bezirk": p.get("bezirk"),
                "beitrag": p.get("beitragszustand"),
                "entwicklung": p.get("verfahrensart"),
            }
            g = f["geometry"]
            teile = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for ringe in teile:
                nr = len(self.polygone)
                self.polygone.append((brwid, ringe))
                xs = [pt[0] for pt in ringe[0]]
                ys = [pt[1] for pt in ringe[0]]
                box = (min(xs), min(ys), max(xs), max(ys))
                self.bbox.append(box)
                z0, z1 = zelle(box[0], box[1]), zelle(box[2], box[3])
                for cx in range(z0[0], z1[0] + 1):
                    for cy in range(z0[1], z1[1] + 1):
                        self.index[(cx, cy)].append(nr)

    def suche(self, x: float, y: float) -> str | None:
        for nr in self.index.get(zelle(x, y), ()):
            x0, y0, x1, y1 = self.bbox[nr]
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            brwid, ringe = self.polygone[nr]
            if punkt_in_ring(x, y, ringe[0]) and not any(punkt_in_ring(x, y, loch) for loch in ringe[1:]):
                return brwid
        return None


# --------------------------------------------------------------------------
# Adressen und Wohnlagen
# --------------------------------------------------------------------------

def norm_strasse(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def norm_hausnummer(hnr, zusatz: str | None = None) -> str:
    """'012' + 'A' -> '12A'; Wohnlagen liefern '001', Adressen 1 + 'a'."""
    text = str(hnr if hnr is not None else "").strip() + (zusatz or "").strip()
    text = text.replace(" ", "").upper().lstrip("0")
    return text or "0"


def hausnummer_sortierung(hnr: str) -> tuple[int, str]:
    m = re.match(r"(\d+)(.*)", hnr)
    return (int(m.group(1)), m.group(2)) if m else (10**9, hnr)


def seiten_lesen(seiten: list[Path]):
    for pfad in seiten:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        for f in daten["features"]:
            if f.get("geometry"):
                yield f["properties"], f["geometry"]["coordinates"]


class Wohnlagen:
    """Wohnlage je Adresse: erst über PLZ/Straße/Hausnummer, sonst nächster Punkt (≤ 30 m)."""

    def __init__(self, seiten: list[Path]):
        self.nach_adresse: dict[tuple[str, str, str], int] = {}
        self.raster: dict[tuple[int, int], list[tuple[float, float, int]]] = defaultdict(list)
        for p, (x, y) in seiten_lesen(seiten):
            code = WOHNLAGE_CODE.get((p.get("wol") or "").strip().lower(), 0)
            if not code:
                continue
            self.nach_adresse[(p.get("plz") or "", norm_strasse(p.get("strasse")), norm_hausnummer(p.get("hnr")))] = code
            self.raster[(int(x // 50), int(y // 50))].append((x, y, code))

    def suche(self, plz: str, strasse: str, hnr: str, x: float, y: float) -> int:
        code = self.nach_adresse.get((plz, norm_strasse(strasse), hnr))
        if code:
            return code
        cx, cy = int(x // 50), int(y // 50)
        bester, abstand = 0, 30.0 ** 2
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for px, py, c in self.raster.get((cx + dx, cy + dy), ()):
                    d = (px - x) ** 2 + (py - y) ** 2
                    if d < abstand:
                        bester, abstand = c, d
        return bester


# --------------------------------------------------------------------------
# Zusammenführen und schreiben
# --------------------------------------------------------------------------

def bauen(dateien: dict, nur_plz: str | None) -> None:
    print("Bodenrichtwertzonen einlesen …", flush=True)
    modell = Zonen(dateien["modell"])
    aktuell = Zonen(dateien["aktuell"])
    print(f"  Modellstichtag {modell.stichtag}: {len(modell.attribute)} Zonen; "
          f"aktuell {aktuell.stichtag}: {len(aktuell.attribute)} Zonen")

    print("Wohnlagen einlesen …", flush=True)
    wohnlagen = Wohnlagen(dateien["wohnlagen"])
    print(f"  {len(wohnlagen.nach_adresse)} Adressen mit Wohnlage")

    print("Adressen zuordnen …", flush=True)
    je_plz: dict[str, list] = defaultdict(list)
    statistik = {"gesamt": 0, "ohne_plz": 0, "ohne_zone": 0, "ohne_wohnlage": 0, "typen": defaultdict(int)}
    for p, (x, y) in seiten_lesen(dateien["adressen"]):
        statistik["gesamt"] += 1
        statistik["typen"][p.get("typ")] += 1
        plz = (p.get("plz") or "").strip()
        # Einträge vom Typ „Platz/Straße ohne HNR“ haben keine Hausnummer und
        # bezeichnen kein Grundstück – sie fallen heraus.
        if not plz or p.get("hnr") is None:
            statistik["ohne_plz"] += 1
            continue
        if nur_plz and plz != nur_plz:
            continue
        hnr = norm_hausnummer(p.get("hnr"), p.get("hnr_zusatz"))
        z_modell = modell.suche(x, y)
        z_aktuell = aktuell.suche(x, y)
        if not z_modell:
            statistik["ohne_zone"] += 1
        wohnlage = wohnlagen.suche(plz, p.get("str_name"), hnr, x, y)
        if not wohnlage:
            statistik["ohne_wohnlage"] += 1
        je_plz[plz].append((p.get("str_name") or "", hnr, z_modell, z_aktuell, wohnlage, p.get("ort_name") or ""))
        if statistik["gesamt"] % 50000 == 0:
            print(f"  {statistik['gesamt']} Adressen …", flush=True)

    print("PLZ-Dateien schreiben …", flush=True)
    ZIEL.mkdir(parents=True, exist_ok=True)
    if not nur_plz:
        for alt in ZIEL.glob("*.json"):
            alt.unlink()
    uebersicht = []
    for plz in sorted(je_plz):
        eintraege = sorted(je_plz[plz], key=lambda e: (e[0].casefold(), hausnummer_sortierung(e[1]), e[1]))
        strassen = sorted({e[0] for e in eintraege}, key=str.casefold)
        ortsteile = sorted({e[5] for e in eintraege})
        s_idx = {s: i for i, s in enumerate(strassen)}
        o_idx = {o: i for i, o in enumerate(ortsteile)}
        zonen = {}
        for e in eintraege:
            for schluessel, z, quelle in (("modell", e[2], modell), ("aktuell", e[3], aktuell)):
                if z:
                    zonen.setdefault(z, {})[schluessel] = zone_kompakt(quelle.attribute[z])
        datei = {
            "plz": plz,
            "stichtage": {"modell": modell.stichtag, "aktuell": aktuell.stichtag},
            "wohnlagen_stand": WOHNLAGEN_STAND,
            "strassen": strassen,
            "ortsteile": ortsteile,
            "zonen": {k: zonen[k] for k in sorted(zonen, key=lambda k: (len(k), k))},
            "adressen": [[s_idx[e[0]], e[1], e[2], e[3], e[4], o_idx[e[5]]] for e in eintraege],
        }
        pfad = ZIEL / f"{plz}.json"
        pfad.write_text(json.dumps(datei, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        uebersicht.append({"plz": plz, "adressen": len(eintraege), "bytes": pfad.stat().st_size})

    if not nur_plz:
        index = {
            "stichtage": {"modell": modell.stichtag, "aktuell": aktuell.stichtag},
            "wohnlagen_stand": WOHNLAGEN_STAND,
            "quellen": [
                "Bodenrichtwerte: Gutachterausschuss für Grundstückswerte in Berlin, Geoportal Berlin (WFS brw2024, brw2026), dl-de/zero-2.0",
                "Adressen: Geoportal Berlin / Adressen Berlin (WFS adressen_berlin), dl-de/zero-2.0",
                "Wohnlagen: Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen, Wohnlagen nach Adressen zum Berliner Mietspiegel 2024 (WFS wohnlagenadr2024), dl-de/zero-2.0",
            ],
            "plz": {u["plz"]: u["adressen"] for u in uebersicht},
        }
        (ZIEL / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    groessen = [u["bytes"] for u in uebersicht]
    print()
    print(f"Adressen gesamt: {statistik['gesamt']}, ohne PLZ: {statistik['ohne_plz']}, "
          f"ohne Modellzone: {statistik['ohne_zone']}, ohne Wohnlage: {statistik['ohne_wohnlage']}")
    print("Adresstypen:", dict(statistik["typen"]))
    if groessen:
        print(f"PLZ-Dateien: {len(groessen)}, gesamt {sum(groessen) / 1e6:.1f} MB, "
              f"Mittel {sum(groessen) / len(groessen) / 1e3:.0f} kB, größte {max(groessen) / 1e3:.0f} kB "
              f"({max(uebersicht, key=lambda u: u['bytes'])['plz']})")


def zone_kompakt(a: dict) -> dict:
    """Nur was der Rechner braucht; Nutzungskürzel vor dem Gedankenstrich (z. B. 'W', 'M1')."""
    nutzung = (a.get("nutzung") or "").split(" - ")[0].strip()
    k = {"brw": a.get("brw"), "nutzung": nutzung, "gfz": a.get("gfz")}
    if a.get("beitrag") and not str(a["beitrag"]).startswith("Beitragsfrei"):
        k["beitrag"] = a["beitrag"]
    if a.get("entwicklung"):
        k["entwicklung"] = a["entwicklung"]
    return k


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--plz", help="nur diese Postleitzahl verarbeiten (Test)")
    p.add_argument("--nur-laden", action="store_true", help="nur herunterladen, nichts bauen")
    a = p.parse_args()

    print("Rohdaten laden (Cache: .wertrechner-cache/) …", flush=True)
    dateien = alles_laden()
    if a.nur_laden:
        return 0
    bauen(dateien, a.plz)
    return 0


if __name__ == "__main__":
    sys.exit(main())
