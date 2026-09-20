#!/usr/bin/env python3
"""Sucht in amtlichen Rechtsprechungsdatenbanken nach Bau-Entscheidungen.

Das Skript trifft keine fachliche Entscheidung. Es stellt nur die Kandidaten
zusammen, damit der Agent nicht blind durch Suchmasken klicken muss. Ob eine
Entscheidung wirklich das Bauwesen betrifft und ob sie einen Beitrag trägt,
entscheidet danach der Agent am Volltext.

Quellen – ausschließlich amtlich:

  Bund          www.rechtsprechung-im-internet.de (BMJV / Bundesamt für Justiz)
                Liefert ein maschinenlesbares Verzeichnis aller Entscheidungen
                mit Gericht, Datum und Aktenzeichen. Das Aktenzeichen verrät den
                Senat: „VII ZR" ist der Bausenat des BGH (Werkvertrags- und
                Architektenrecht). Damit lässt sich ohne Volltext vorfiltern.

  Brandenburg   gerichtsentscheidungen.brandenburg.de (Landesrechtsportal)
                Echte Volltextsuche über die Adresszeile, serverseitig
                gerendert, nach Datum absteigend. Enthält neben den
                Brandenburger Gerichten auch die gemeinsamen Gerichte von
                Berlin und Brandenburg (OVG, LSG, LArbG, FG).

  Berlin        Die Berliner Datenbank (gesetze.berlin.de) ist eine reine
                JavaScript-Anwendung und ohne Browser nicht abrufbar. Das
                Kammergericht fehlt deshalb. Das Skript weist darauf hin,
                statt die Lücke zu verschweigen.

Aufruf:  python tools/urteile_finden.py --ziel <datei> [--monate 18] [--max 40]
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ENTWUERFE = WURZEL / "entwuerfe"

BUND_INDEX = "https://www.rechtsprechung-im-internet.de/rii-toc.xml"
BB_BASIS = "https://gerichtsentscheidungen.brandenburg.de"
BB_SUCHE = BB_BASIS + "/suche"

KENNUNG = "BIB-Fachartikel/1.0 (+https://ing-bassam.de; Recherche für Fachbeiträge)"

# Senate des Bundes, die für privates Baurecht zuständig sind. Der Schlüssel ist
# das Muster im Aktenzeichen, der Wert die Begründung für den Kandidatenbericht.
BUND_SENATE = {
    "VII ZR": "BGH, Bausenat – Werkvertrag, Bauvertrag, Architekten- und Ingenieurvertrag",
    "VII ZB": "BGH, Bausenat – Nebenverfahren",
}

# Gerichte in Brandenburg, bei denen Bausachen zu erwarten sind. Die Reihenfolge
# bestimmt die Reihenfolge der Abfragen.
BB_GERICHTE = [
    "OLG Brandenburg",
    "LG Potsdam",
    "LG Cottbus",
    "LG Frankfurt (Oder)",
    "LG Neuruppin",
    "Vergabekammer Potsdam",
    "OVG Berlin-Brandenburg",
]

# Suchbegriffe. Bewusst knapp gehalten: Jeder Begriff ist eine eigene Abfrage,
# und die Treffer werden ohnehin über die Entscheidungs-ID zusammengeführt.
BB_BEGRIFFE = [
    "Bauvertrag",
    "Werkvertrag",
    "Nachtrag",
    "Bauablauf",
    "Architektenvertrag",
    "Baumangel",
    "Sachverständiger Baumangel",
    "VOB/B",
]

# Begriffe, an denen der Agent später erkennt, ob ein Volltext zum Themenfeld
# gehört. Hier nur zur Vorsortierung der Bundes-Entscheidungen verwendet.
THEMENFELD = [
    "Bauvertrag", "Werkvertrag", "Bauleistung", "Bauunternehmer", "Bauherr",
    "Architekt", "Ingenieur", "HOAI", "VOB", "Nachtrag", "Bauablauf",
    "Behinderung", "Bauzeit", "Mangel", "Abnahme", "Werklohn", "Aufmaß",
    "Kalkulation", "Baugrund", "Planungsfehler", "Sachverständige",
]


def abrufen(url: str, versuche: int = 3) -> str:
    """Holt eine Seite. Bei Fehlern wird begrenzt erneut versucht."""
    letzte: Exception | None = None
    for versuch in range(versuche):
        try:
            anfrage = urllib.request.Request(
                url, headers={"User-Agent": KENNUNG, "Accept-Language": "de"}
            )
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                rohdaten = antwort.read()
            return rohdaten.decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as fehler:
            letzte = fehler
            if versuch < versuche - 1:
                time.sleep(2 * (versuch + 1))
    raise RuntimeError(f"Abruf fehlgeschlagen: {url} – {letzte}")


def bekannte_aktenzeichen() -> set[str]:
    """Aktenzeichen, zu denen es schon einen Entwurf gibt."""
    bekannt: set[str] = set()
    if not ENTWUERFE.is_dir():
        return bekannt
    for pfad in ENTWUERFE.glob("*.md"):
        text = pfad.read_text(encoding="utf-8", errors="replace")
        for treffer in re.findall(r"^aktenzeichen:\s*(.+)$", text, re.M):
            bekannt.add(normal_az(treffer))
        # Auch im Fließtext genannte Aktenzeichen zählen als abgedeckt.
        for treffer in re.findall(r"\b[IVX]+ Z[RB] \d+/\d{2}\b", text):
            bekannt.add(normal_az(treffer))
    return {a for a in bekannt if a}


def normal_az(wert: str) -> str:
    return re.sub(r"\s+", " ", wert.strip().strip("\"'")).upper()


class Fund:
    def __init__(self, *, gericht: str, datum: str, aktenzeichen: str,
                 link: str, quelle: str, grund: str, region: str):
        self.gericht = gericht
        self.datum = datum              # JJJJ-MM-TT
        self.aktenzeichen = aktenzeichen
        self.link = link
        self.quelle = quelle
        self.grund = grund
        self.region = region            # "Berlin/Brandenburg" oder "Bund"

    @property
    def schluessel(self) -> str:
        return normal_az(self.aktenzeichen)

    @property
    def vorrang(self) -> tuple:
        # Berlin/Brandenburg zuerst, danach das jüngere Datum.
        return (0 if self.region == "Berlin/Brandenburg" else 1,
                # negatives Datum als String lässt sich nicht bilden – daher
                # invertiert über die Sortierrichtung im Aufrufer
                self.datum)


# --------------------------------------------------------------------------
# Bund
# --------------------------------------------------------------------------

def bund_suchen(stichtag: date, bekannt: set[str]) -> list[Fund]:
    print(f"Bund: Verzeichnis wird geladen ({BUND_INDEX}) …")
    roh = abrufen(BUND_INDEX)
    eintraege = re.findall(r"<item>(.*?)</item>", roh, re.S)
    print(f"Bund: {len(eintraege)} Entscheidungen im Verzeichnis")

    def feld(block: str, name: str) -> str:
        treffer = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
        return html.unescape(treffer.group(1).strip()) if treffer else ""

    funde: list[Fund] = []
    for block in eintraege:
        az = feld(block, "aktenzeichen")
        grund = next((g for muster, g in BUND_SENATE.items() if muster in az), "")
        if not grund:
            continue
        roh_datum = feld(block, "entsch-datum")
        if not re.fullmatch(r"\d{8}", roh_datum):
            continue
        datum = f"{roh_datum[:4]}-{roh_datum[4:6]}-{roh_datum[6:]}"
        if datum < stichtag.isoformat():
            continue
        if normal_az(az) in bekannt:
            continue
        funde.append(Fund(
            gericht=feld(block, "gericht"),
            datum=datum,
            aktenzeichen=az,
            link=feld(block, "link").replace("http://", "https://"),
            quelle="rechtsprechung-im-internet.de (Bundesamt für Justiz)",
            grund=grund,
            region="Bund",
        ))
    print(f"Bund: {len(funde)} Entscheidungen der Bausenate seit {stichtag.isoformat()}")
    return funde


# --------------------------------------------------------------------------
# Brandenburg
# --------------------------------------------------------------------------

def bb_suchen(stichtag: date, bekannt: set[str], pause: float) -> list[Fund]:
    gefunden: dict[str, Fund] = {}
    for gericht in BB_GERICHTE:
        for begriff in BB_BEGRIFFE:
            adresse = BB_SUCHE + "?" + urllib.parse.urlencode({
                "input_fulltext": begriff,
                "select_source": gericht,
                "input_date_promulgation_from": stichtag.strftime("%Y-%m-%d"),
            })
            try:
                seite = abrufen(adresse)
            except RuntimeError as fehler:
                print(f"  Brandenburg: „{begriff}\" bei {gericht} übersprungen – {fehler}")
                continue
            neu = 0
            for fund in bb_treffer_lesen(seite, gericht, begriff):
                if fund.datum < stichtag.isoformat():
                    continue
                if fund.schluessel in bekannt or fund.schluessel in gefunden:
                    continue
                gefunden[fund.schluessel] = fund
                neu += 1
            if neu:
                print(f"  Brandenburg: {gericht} / „{begriff}\" – {neu} neu")
            time.sleep(pause)
    print(f"Brandenburg: {len(gefunden)} Entscheidungen seit {stichtag.isoformat()}")
    return list(gefunden.values())


def bb_treffer_lesen(seite: str, gericht: str, begriff: str) -> list[Fund]:
    """Liest die Trefferliste einer Suchseite.

    Die Treffer stehen serverseitig im HTML; jeder Treffer ist ein Link auf
    /gerichtsentscheidung/<id>, gefolgt von Aktenzeichen und Datum.
    """
    funde: list[Fund] = []
    bloecke = re.split(r'(?=<a[^>]+href="/gerichtsentscheidung/)', seite)
    for block in bloecke[1:]:
        kennung = re.search(r'href="(/gerichtsentscheidung/(\d+))"', block)
        if not kennung:
            continue
        az = re.search(r"\b(\d+\s+[A-Za-zÄÖÜ]{1,4}\s+\d+/\d{2})\b", block)
        datum = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", block)
        if not az or not datum:
            continue
        tag, monat, jahr = datum.groups()
        funde.append(Fund(
            gericht=gericht,
            datum=f"{jahr}-{monat}-{tag}",
            aktenzeichen=az.group(1),
            link=BB_BASIS + kennung.group(1),
            quelle="gerichtsentscheidungen.brandenburg.de (Landesrechtsportal)",
            grund=f"Volltexttreffer für „{begriff}\"",
            region="Berlin/Brandenburg",
        ))
    return funde


# --------------------------------------------------------------------------
# Bericht
# --------------------------------------------------------------------------

def bericht(funde: list[Fund], stichtag: date, grenze: int) -> str:
    sortiert = sorted(
        funde,
        key=lambda f: (0 if f.region == "Berlin/Brandenburg" else 1, f.datum),
    )
    # innerhalb jeder Region das jüngste Datum zuerst
    bb = sorted([f for f in sortiert if f.region == "Berlin/Brandenburg"],
                key=lambda f: f.datum, reverse=True)
    bund = sorted([f for f in sortiert if f.region == "Bund"],
                  key=lambda f: f.datum, reverse=True)
    auswahl = bb[: max(grenze // 2, 1)] + bund[: grenze - len(bb[: max(grenze // 2, 1)])]

    zeilen = [
        "# Kandidaten für eine Urteilsbesprechung",
        "",
        f"Stand der Recherche: {date.today().isoformat()}",
        f"Berücksichtigt werden Entscheidungen ab {stichtag.isoformat()}.",
        "",
        "Die Liste ist vorsortiert, nicht geprüft. Ob eine Entscheidung das",
        "Bauwesen betrifft und einen Beitrag trägt, entscheidest du am Volltext.",
        "Berlin und Brandenburg stehen zuerst, danach der Bund; innerhalb der",
        "Gruppen die jüngste Entscheidung zuerst.",
        "",
        "## Hinweis zur Abdeckung",
        "",
        "Die Berliner Rechtsprechungsdatenbank (gesetze.berlin.de) ist eine reine",
        "JavaScript-Anwendung und ohne Browser nicht abrufbar. Entscheidungen des",
        "Kammergerichts und der Berliner Landgerichte fehlen deshalb in dieser",
        "Liste. Enthalten sind die gemeinsamen Gerichte von Berlin und Brandenburg",
        "(OVG, LSG, LArbG, FG) über das Brandenburger Portal.",
        "",
    ]

    if not auswahl:
        zeilen += [
            "## Keine Kandidaten",
            "",
            "Im gewählten Zeitraum wurde nichts gefunden, zu dem noch kein Entwurf",
            "vorliegt. Beende den Lauf mit `ERGEBNIS: KEINE KANDIDATEN`.",
            "",
        ]
        return "\n".join(zeilen)

    for gruppe, titel in ((bb[: max(grenze // 2, 1)], "Berlin und Brandenburg"),
                          (bund[: grenze - len(bb[: max(grenze // 2, 1)])], "Bund")):
        if not gruppe:
            continue
        zeilen += [f"## {titel} ({len(gruppe)})", ""]
        for nummer, f in enumerate(gruppe, start=1):
            zeilen += [
                f"### {nummer}. {f.gericht}, {datum_deutsch(f.datum)} – {f.aktenzeichen}",
                "",
                f"- Volltext: {f.link}",
                f"- Quelle: {f.quelle}",
                f"- Aufgenommen, weil: {f.grund}",
                "",
            ]
    return "\n".join(zeilen)


def datum_deutsch(iso: str) -> str:
    jahr, monat, tag = iso.split("-")
    return f"{tag}.{monat}.{jahr}"


def main() -> int:
    zerleger = argparse.ArgumentParser(description="Sucht Bau-Entscheidungen.")
    zerleger.add_argument("--ziel", required=True, help="Datei für die Kandidatenliste")
    zerleger.add_argument("--monate", type=int, default=18,
                          help="Wie weit zurück gesucht wird (Vorgabe: 18)")
    zerleger.add_argument("--max", type=int, default=40,
                          help="Höchstzahl der Kandidaten in der Liste")
    zerleger.add_argument("--pause", type=float, default=1.0,
                          help="Sekunden zwischen zwei Abfragen der Landesdatenbank")
    zerleger.add_argument("--nur", choices=["bund", "brandenburg"],
                          help="nur eine Quelle abfragen (für Tests)")
    argumente = zerleger.parse_args()

    stichtag = date.today() - timedelta(days=int(argumente.monate * 30.4))
    bekannt = bekannte_aktenzeichen()
    if bekannt:
        print(f"Bereits besprochen: {len(bekannt)} Aktenzeichen")

    funde: list[Fund] = []
    fehler = False

    if argumente.nur != "bund":
        try:
            funde += bb_suchen(stichtag, bekannt, argumente.pause)
        except Exception as ausnahme:
            fehler = True
            print(f"FEHLER Brandenburg: {ausnahme}", file=sys.stderr)

    if argumente.nur != "brandenburg":
        try:
            funde += bund_suchen(stichtag, bekannt)
        except Exception as ausnahme:
            fehler = True
            print(f"FEHLER Bund: {ausnahme}", file=sys.stderr)

    if fehler and not funde:
        print("FEHLER: Keine Quelle erreichbar.", file=sys.stderr)
        return 2

    ziel = Path(argumente.ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(bericht(funde, stichtag, argumente.max), encoding="utf-8", newline="\n")
    print(f"\nKandidaten gesamt: {len(funde)}")
    print(f"Liste geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
