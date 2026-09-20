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

  Nordrhein-    nrwesuche.justiz.nrw.de (Justiz Nordrhein-Westfalen)
  Westfalen     Die größte Entscheidungsdatenbank des Landes. Nimmt die Suche
                nur per POST entgegen, liefert die Treffer aber serverseitig
                mit Gericht, Aktenzeichen, ECLI und Datum. Enthält als einziges
                Land ein Berufsgericht für Beratende Ingenieure im Bauwesen.

  Berlin        Nicht abrufbar. Die Datenbank gesetze.berlin.de lädt ihre
                Treffer erst im Browser über eine Schnittstelle, die Abrufe von
                außerhalb mit „security_wrongDomain" ablehnt. Dieselbe Technik
                setzen neun weitere Länder ein (Baden-Württemberg, Hamburg,
                Hessen, Mecklenburg-Vorpommern, Rheinland-Pfalz, Saarland,
                Sachsen-Anhalt, Schleswig-Holstein, Thüringen). Das Skript
                weist auf die Lücke hin, statt sie zu verschweigen.

Aufruf:  python tools/urteile_finden.py --ziel <datei> [--monate 18] [--max 12]
"""

from __future__ import annotations

import argparse
import html
import io
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ENTWUERFE = WURZEL / "entwuerfe"

BUND_INDEX = "https://www.rechtsprechung-im-internet.de/rii-toc.xml"
BB_BASIS = "https://gerichtsentscheidungen.brandenburg.de"
BB_SUCHE = BB_BASIS + "/suche"
NRW_SUCHE = "https://nrwesuche.justiz.nrw.de/index.php"

# Gerichtsarten in NRW, bei denen Bausachen zu erwarten sind. Das Berufsgericht
# für Beratende Ingenieure ist für ein Sachverständigenbüro unmittelbar
# einschlägig und gibt es in dieser Form nur in Nordrhein-Westfalen.
NRW_GERICHTE = [
    "Oberlandesgericht",
    "Landgericht",
    "Berufsgericht für Beratende Ingenieure und Ingenieurinnen sowie "
    "Ingenieure und Ingenieurinnen im Bauwesen",
]

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


def rohabruf(url: str, versuche: int = 3) -> bytes:
    """Holt eine Adresse als Bytes. Bei Fehlern wird begrenzt erneut versucht."""
    letzte: Exception | None = None
    for versuch in range(versuche):
        try:
            anfrage = urllib.request.Request(
                url, headers={"User-Agent": KENNUNG, "Accept-Language": "de"}
            )
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                return antwort.read()
        except (urllib.error.URLError, TimeoutError, OSError) as fehler:
            letzte = fehler
            if versuch < versuche - 1:
                time.sleep(2 * (versuch + 1))
    raise RuntimeError(f"Abruf fehlgeschlagen: {url} – {letzte}")


def abrufen(url: str, versuche: int = 3) -> str:
    return rohabruf(url, versuche).decode("utf-8", errors="replace")


def nur_text(auszeichnung: str) -> str:
    """Entfernt Auszeichnung und fasst Leerraum zusammen."""
    ohne = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", auszeichnung, flags=re.S | re.I)
    ohne = re.sub(r"<[^>]+>", " ", ohne)
    return re.sub(r"[ \t]+", " ", html.unescape(ohne)).strip()


def dateiname(wert: str) -> str:
    wert = wert.lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        wert = wert.replace(alt, neu)
    wert = unicodedata.normalize("NFKD", wert)
    wert = "".join(z for z in wert if not unicodedata.combining(z))
    return re.sub(r"[^a-z0-9]+", "-", wert).strip("-")[:60]


def volltext_holen(fund: "Fund") -> tuple[str, str]:
    """Lädt den Volltext einer Entscheidung.

    Rückgabe: (Klartext, ECLI). Für den Bund liegt der Volltext als ZIP mit
    einer XML-Datei bereit – ein Agent kann ein ZIP nicht lesen, das Skript
    entpackt es deshalb hier. Brandenburg liefert HTML.
    """
    if fund.link.endswith(".zip"):
        rohdaten = rohabruf(fund.link)
        with zipfile.ZipFile(io.BytesIO(rohdaten)) as archiv:
            namen = [n for n in archiv.namelist() if n.lower().endswith(".xml")]
            if not namen:
                raise RuntimeError("ZIP enthält keine XML-Datei")
            xml = archiv.read(namen[0]).decode("utf-8", errors="replace")
        ecli = ""
        treffer = re.search(r"\bECLI:[A-Z0-9.:]+", xml)
        if treffer:
            ecli = treffer.group(0)
        return nur_text(xml), ecli

    seite = abrufen(fund.link)
    text = nur_text(seite)
    treffer = re.search(r"\bECLI:[A-Z0-9.:]+", text)
    return text, treffer.group(0) if treffer else ""


def themenbezug(text: str) -> tuple[int, list[str]]:
    """Zählt, wie viele Begriffe des Themenfelds im Volltext vorkommen.

    Das ist ein Hinweis für den Agenten, keine Entscheidung. Ein hoher Wert
    bedeutet nicht, dass die Entscheidung taugt; ein niedriger nicht, dass sie
    untauglich ist.
    """
    klein = text.lower()
    getroffen = [b for b in THEMENFELD if b.lower() in klein]
    return len(getroffen), getroffen


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
        # wird erst beim Laden des Volltextes gefüllt
        self.volltext: Path | None = None
        self.ecli = ""
        self.woerter = 0
        self.treffer = 0
        self.begriffe: list[str] = []
        self.hinweis = ""

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
# Nordrhein-Westfalen
# --------------------------------------------------------------------------

def nrw_suchen(stichtag: date, bekannt: set[str], pause: float) -> list[Fund]:
    """Durchsucht die NRW-Entscheidungsdatenbank.

    Anders als Brandenburg nimmt NRW die Suche nur per POST entgegen; eine
    Adresse allein genügt nicht. Die Trefferliste kommt serverseitig gerendert
    zurück und nennt je Treffer Gericht, Aktenzeichen, ECLI und Datum.
    """
    gefunden: dict[str, Fund] = {}
    for gericht in NRW_GERICHTE:
        for begriff in BB_BEGRIFFE:
            daten = urllib.parse.urlencode({
                "q": begriff,
                "method": "search",
                "absenden": "Suchen",
                "qSize": "20",
                "gerichtstyp": gericht,
            }).encode()
            try:
                anfrage = urllib.request.Request(
                    NRW_SUCHE, data=daten,
                    headers={"User-Agent": KENNUNG, "Accept-Language": "de"},
                )
                with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                    seite = antwort.read().decode("utf-8", errors="replace")
            except Exception as fehler:
                print(f"  NRW: „{begriff}\" bei {gericht[:28]} übersprungen – {fehler}")
                time.sleep(pause)
                continue

            neu = 0
            for fund in nrw_treffer_lesen(seite, begriff):
                if fund.datum < stichtag.isoformat():
                    continue
                if fund.schluessel in bekannt or fund.schluessel in gefunden:
                    continue
                gefunden[fund.schluessel] = fund
                neu += 1
            if neu:
                print(f"  NRW: {gericht[:28]} / „{begriff}\" – {neu} neu")
            time.sleep(pause)
    print(f"Nordrhein-Westfalen: {len(gefunden)} Entscheidungen seit {stichtag.isoformat()}")
    return list(gefunden.values())


def nrw_treffer_lesen(seite: str, begriff: str) -> list[Fund]:
    funde: list[Fund] = []
    for block in re.findall(r"<div class='einErgebnis'>(.*?)</div>", seite, re.S):
        link = re.search(r"href='([^']+)'", block)
        gericht = re.search(r"Gericht:\s*([^<]+)", block)
        az = re.search(r"Aktenzeichen:\s*([^<]+)", block)
        datum = re.search(r"Entscheidungsdatum:\s*(\d{2})\.(\d{2})\.(\d{4})", block)
        if not (link and az and datum):
            continue
        ecli = re.search(r"(ECLI:[A-Z0-9.:]+)", block)
        art = re.search(r"Entscheidungsart:\s*([^<]+)", block)
        tag, monat, jahr = datum.groups()
        fund = Fund(
            gericht=(gericht.group(1).strip() if gericht else "Gericht in Nordrhein-Westfalen"),
            datum=f"{jahr}-{monat}-{tag}",
            aktenzeichen=az.group(1).strip(),
            link=html.unescape(link.group(1).strip()),
            quelle="nrwesuche.justiz.nrw.de (Justiz Nordrhein-Westfalen)",
            grund=f"Volltexttreffer für „{begriff}\""
                  + (f", {art.group(1).strip()}" if art else ""),
            region="Weitere Länder",
        )
        if ecli:
            fund.ecli = ecli.group(1)
        funde.append(fund)
    return funde


# --------------------------------------------------------------------------
# Bericht
# --------------------------------------------------------------------------

def volltexte_ablegen(auswahl: list["Fund"], ordner: Path, pause: float) -> None:
    """Holt die Volltexte der Kandidaten und legt sie als Textdatei ab.

    Der Agent liest danach nur noch lokale Dateien. Das ist zuverlässiger als
    ein Abruf im Agentenlauf – beim Bund sogar zwingend, weil dort nur ein ZIP
    bereitsteht – und spart Web-Aufrufe für die eigentliche Prüfung.
    """
    ordner.mkdir(parents=True, exist_ok=True)
    for fund in auswahl:
        ziel = ordner / f"{dateiname(fund.aktenzeichen)}.txt"
        try:
            text, ecli = volltext_holen(fund)
        except Exception as ausnahme:
            fund.hinweis = f"Volltext nicht abrufbar ({ausnahme}). Bitte selbst öffnen."
            print(f"  Volltext fehlgeschlagen: {fund.aktenzeichen} – {ausnahme}")
            time.sleep(pause)
            continue
        fund.ecli = ecli
        fund.woerter = len(text.split())
        fund.treffer, begriffe = themenbezug(text)
        fund.begriffe = begriffe
        kopf = (
            "Volltext einer Gerichtsentscheidung, unverändert aus der amtlichen Quelle.\n"
            f"Gericht: {fund.gericht}\n"
            f"Entscheidungsdatum: {fund.datum}\n"
            f"Aktenzeichen: {fund.aktenzeichen}\n"
            f"ECLI: {ecli or 'nicht vergeben'}\n"
            f"Amtliche Quelle: {fund.link}\n"
            f"Herausgeber: {fund.quelle}\n"
            f"Abgerufen am: {date.today().isoformat()}\n"
            + "-" * 72 + "\n\n"
        )
        ziel.write_text(kopf + text, encoding="utf-8", newline="\n")
        fund.volltext = ziel
        print(f"  Volltext: {fund.aktenzeichen} – {fund.woerter} Wörter, "
              f"{fund.treffer} Themenbegriffe")
        time.sleep(pause)


REGIONEN = ("Berlin/Brandenburg", "Bund", "Weitere Länder")


def auswaehlen(funde: list[Fund], grenze: int) -> dict[str, list[Fund]]:
    """Verteilt die Plätze auf die Regionen, je das Jüngste zuerst.

    Berlin und Brandenburg bekommen die Hälfte, weil das Büro dort arbeitet.
    Der Bund folgt, weil der BGH bundesweit die Linie vorgibt. Die übrigen
    Länder füllen auf, was übrig bleibt.
    """
    nach_region = {
        r: sorted([f for f in funde if f.region == r], key=lambda f: f.datum, reverse=True)
        for r in REGIONEN
    }
    anteile = {
        "Berlin/Brandenburg": max(grenze // 2, 1),
        "Bund": max(grenze // 3, 1),
    }
    ausgewaehlt: dict[str, list[Fund]] = {}
    rest = grenze
    for region in REGIONEN:
        platz = anteile.get(region, rest)
        ausgewaehlt[region] = nach_region[region][: max(min(platz, rest), 0)]
        rest -= len(ausgewaehlt[region])
    # Freie Plätze an die Regionen zurückgeben, die noch Kandidaten haben.
    for region in REGIONEN:
        if rest <= 0:
            break
        offen = [f for f in nach_region[region] if f not in ausgewaehlt[region]]
        nachschlag = offen[:rest]
        ausgewaehlt[region] += nachschlag
        rest -= len(nachschlag)
    return ausgewaehlt


def bericht(gruppen: dict[str, list[Fund]], stichtag: date) -> str:
    auswahl = [f for r in REGIONEN for f in gruppen.get(r, [])]

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
        "Die Volltexte liegen bereits als Textdatei neben dieser Liste – öffne sie",
        "mit Read, nicht mit WebFetch. Sie stammen unverändert aus der amtlichen",
        "Quelle; der Kopf jeder Datei nennt Gericht, Datum, Aktenzeichen, ECLI und",
        "die Fundstelle. Übernimm die Angaben zur Zitierung aus diesem Kopf.",
        "",
        "Die Zahl der Begriffe aus dem Themenfeld ist ein grober Hinweis, keine",
        "Aussage über die Eignung. Ein hoher Wert kann auch eine Kostenentscheidung",
        "in einer Bausache treffen, ein niedriger eine grundlegende Entscheidung.",
        "",
        "## Hinweis zur Abdeckung",
        "",
        "Durchsucht werden: der Bund (rechtsprechung-im-internet.de), Brandenburg",
        "samt der gemeinsamen Gerichte von Berlin und Brandenburg (OVG, LSG,",
        "LArbG, FG) und Nordrhein-Westfalen.",
        "",
        "Nicht durchsucht wird Berlin selbst: Die Datenbank gesetze.berlin.de",
        "liefert ihre Treffer erst im Browser und sperrt Abrufe von außerhalb ab",
        "(Fehler „security_wrongDomain\"). Entscheidungen des Kammergerichts und",
        "der Berliner Landgerichte fehlen deshalb. Ebenso fehlen neun weitere",
        "Länder, die dieselbe Technik einsetzen.",
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

    titel_je_region = {
        "Berlin/Brandenburg": "Berlin und Brandenburg",
        "Bund": "Bund",
        "Weitere Länder": "Weitere Länder",
    }
    for region in REGIONEN:
        gruppe, titel = gruppen.get(region, []), titel_je_region[region]
        if not gruppe:
            continue
        zeilen += [f"## {titel} ({len(gruppe)})", ""]
        for nummer, f in enumerate(gruppe, start=1):
            zeilen += [
                f"### {nummer}. {f.gericht}, {datum_deutsch(f.datum)} – {f.aktenzeichen}",
                "",
            ]
            if f.volltext:
                zeilen.append(f"- Volltext (lokal, mit Read öffnen): `{f.volltext}`")
                zeilen.append(f"- Umfang: {f.woerter} Wörter")
                zeilen.append(
                    f"- Begriffe aus dem Themenfeld: {f.treffer}"
                    + (f" ({', '.join(f.begriffe[:8])})" if f.begriffe else "")
                )
            else:
                zeilen.append(f"- Volltext: {f.link}")
            if f.ecli:
                zeilen.append(f"- ECLI: {f.ecli}")
            zeilen.append(f"- Amtliche Fundstelle: {f.link}")
            zeilen.append(f"- Herausgeber: {f.quelle}")
            zeilen.append(f"- In die Liste gekommen über: {f.grund}")
            if f.hinweis:
                zeilen.append(f"- Achtung: {f.hinweis}")
            zeilen.append("")
    return "\n".join(zeilen)


def datum_deutsch(iso: str) -> str:
    jahr, monat, tag = iso.split("-")
    return f"{tag}.{monat}.{jahr}"


def main() -> int:
    zerleger = argparse.ArgumentParser(description="Sucht Bau-Entscheidungen.")
    zerleger.add_argument("--ziel", required=True, help="Datei für die Kandidatenliste")
    zerleger.add_argument("--monate", type=int, default=18,
                          help="Wie weit zurück gesucht wird (Vorgabe: 18)")
    zerleger.add_argument("--max", type=int, default=12,
                          help="Höchstzahl der Kandidaten in der Liste")
    zerleger.add_argument("--pause", type=float, default=1.0,
                          help="Sekunden zwischen zwei Abfragen der Landesdatenbank")
    zerleger.add_argument("--nur", choices=["bund", "brandenburg", "nrw"],
                          help="nur eine Quelle abfragen (für Tests)")
    argumente = zerleger.parse_args()

    stichtag = date.today() - timedelta(days=int(argumente.monate * 30.4))
    bekannt = bekannte_aktenzeichen()
    if bekannt:
        print(f"Bereits besprochen: {len(bekannt)} Aktenzeichen")

    funde: list[Fund] = []
    fehler = False

    if argumente.nur in (None, "brandenburg"):
        try:
            funde += bb_suchen(stichtag, bekannt, argumente.pause)
        except Exception as ausnahme:
            fehler = True
            print(f"FEHLER Brandenburg: {ausnahme}", file=sys.stderr)

    if argumente.nur in (None, "nrw"):
        try:
            funde += nrw_suchen(stichtag, bekannt, argumente.pause)
        except Exception as ausnahme:
            fehler = True
            print(f"FEHLER Nordrhein-Westfalen: {ausnahme}", file=sys.stderr)

    if argumente.nur not in ("brandenburg", "nrw"):
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

    gruppen = auswaehlen(funde, argumente.max)
    auswahl = [f for r in REGIONEN for f in gruppen[r]]
    if auswahl:
        print(f"\nVolltexte werden geladen ({len(auswahl)} Entscheidungen) …")
        volltexte_ablegen(auswahl, ziel.parent / "volltexte", argumente.pause)

    ziel.write_text(bericht(gruppen, stichtag), encoding="utf-8", newline="\n")
    print(f"\nGefunden: {len(funde)} · in der Liste: {len(auswahl)}")
    print(f"Liste geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
