#!/usr/bin/env python3
"""Baut die Fachbibliothek aus einem Ordner mit PDF-Fachbüchern.

Die PDFs bleiben auf dem Rechner des Büros. In das private Repository
FachwissenAgent kommen nur:

  katalog.yml               je Werk die bibliografischen Angaben und das fertige
                            Zitat, ermittelt über die Deutsche Nationalbibliothek
  texte/<kennung>.txt       der Text, Seite für Seite, mit der gedruckten
                            Seitenzahl – nach ihr wird zitiert
  gliederung/<kennung>.md   das Inhaltsverzeichnis mit Seitenzahlen

Aufruf (auf dem Rechner mit den PDFs):
    python tools/bibliothek_auszug.py <pdf-ordner> <bibliothek-ordner> [--auslassen Ordner ...]

Läuft schrittweise: Ein Werk, dessen PDF sich nicht geändert hat (gleiche
Prüfsumme), wird nicht neu verarbeitet. Doppelte PDFs werden erkannt und nur
einmal aufgenommen; die Ordner, in denen sie liegen, gehen als Themen in den
Katalog. Benötigt pypdf und PyYAML.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pypdf
import yaml

logging.getLogger("pypdf").setLevel(logging.ERROR)

ISBN = re.compile(r"97[89][- ]?(?:\d[- ]?){9}[\dX]")
DNB = "https://services.dnb.de/sru/dnb"
MARC = {"m": "http://www.loc.gov/MARC21/slim"}
KENNUNG = "BIB-Fachbibliothek/1.0 (+https://ing-bassam.de)"
STOPPWOERTER = {"der", "die", "das", "des", "ein", "eine", "und", "in", "im", "zur",
                "zum", "fuer", "für", "von", "the", "a", "an", "of", "bei", "mit"}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def slug(text: str) -> str:
    # Die DNB liefert Umlaute zerlegt (u + Trema); ohne NFC würde aus „für“ „fur“.
    text = unicodedata.normalize("NFC", text).lower()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(alt, neu)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def pruefsumme(pfad: Path) -> str:
    h = hashlib.sha1()
    with pfad.open("rb") as datei:
        for block in iter(lambda: datei.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# Verlagsnummern der Bücher in der Bibliothek und ihre Länge – für die übliche
# Schreibweise mit Bindestrichen (978-3-658-28148-9).
VERLAGSNUMMERN = ("658", "662", "322", "540", "648", "503", "410", "8348")
# Bei diesen Verlagen (Springer) sind die Personen in den Verlagsdaten bei
# Crossref vollständiger als im Datensatz der Nationalbibliothek.
SPRINGER = ("978-3-658", "978-3-662", "978-3-8348", "978-3-322", "978-3-540")


ISBN10 = re.compile(r"ISBN(?:-10)?:?\s*(\d[\d -]{8,11}[\dX])\b")
DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+[^\s\"<>.,;])")


def isbn10_zu_13(roh: str) -> str:
    """Ältere Bücher tragen eine zehnstellige ISBN; die DNB findet sie als ISBN-13."""
    ziffern = re.sub(r"[^\dX]", "", roh.upper())
    if len(ziffern) != 10:
        return ""
    basis = "978" + ziffern[:9]
    pruef = (10 - sum(int(z) * (1 if i % 2 == 0 else 3) for i, z in enumerate(basis)) % 10) % 10
    return isbn_normal(basis + str(pruef))


def isbn_normal(roh: str) -> str:
    """ISBN-13 mit gültiger Prüfziffer, in der Schreibweise des Verlags."""
    ziffern = re.sub(r"[^\dX]", "", roh.upper())
    if len(ziffern) != 13 or not ziffern.isdigit():
        return ""
    summe = sum(int(z) * (1 if i % 2 == 0 else 3) for i, z in enumerate(ziffern))
    if summe % 10:
        return ""
    if ziffern.startswith("9783"):
        for verlag in VERLAGSNUMMERN:
            if ziffern[4:4 + len(verlag)] == verlag:
                return (f"978-3-{verlag}-{ziffern[4 + len(verlag):12]}-{ziffern[12]}")
    return ziffern


BINDEWOERTER = {"und", "oder", "bzw", "sowie", "bis", "als"}


def entbinden(text: str) -> str:
    """Trennstriche am Zeilenende entfernen: „Bau-\\nschäden“ wird „Bauschäden“.

    Nur vor einem Kleinbuchstaben – „DIN-\\nNorm“ bleibt stehen, ebenso der
    Ergänzungsstrich in „Verbund-\\nund Dichtschlämme“.
    """
    def verbinden(treffer: re.Match) -> str:
        if treffer.group(3).lower() in BINDEWOERTER:
            return f"{treffer.group(1)}- {treffer.group(3)}"
        return treffer.group(1) + treffer.group(2)

    text = re.sub(r"([a-zäöüß]) ?-\n(([a-zäöüß]+))", verbinden, text)
    return re.sub(r"[ \t]+", " ", text)


# ---------------------------------------------------------------------------
# PDF lesen (läuft parallel in eigenen Prozessen)
# ---------------------------------------------------------------------------

def pdf_lesen(pfad_text: str) -> dict:
    pfad = Path(pfad_text)
    leser = pypdf.PdfReader(str(pfad))
    if leser.is_encrypted:
        leser.decrypt("")
    anzahl = len(leser.pages)
    try:
        etiketten = list(leser.page_labels)
    except Exception:
        etiketten = []
    if len(etiketten) != anzahl:
        etiketten = [str(i + 1) for i in range(anzahl)]

    seiten = []
    for i, seite in enumerate(leser.pages):
        try:
            text = seite.extract_text() or ""
        except Exception:
            text = ""
        seiten.append(entbinden(text).strip())

    gliederung = []

    def durchlaufen(eintraege, tiefe: int) -> None:
        for eintrag in eintraege:
            if isinstance(eintrag, list):
                durchlaufen(eintrag, tiefe + 1)
                continue
            try:
                nummer = leser.get_destination_page_number(eintrag)
            except Exception:
                nummer = None
            titel = " ".join(str(getattr(eintrag, "title", "") or "").split())
            if titel and nummer is not None and 0 <= nummer < anzahl:
                gliederung.append((tiefe, titel, etiketten[nummer], nummer + 1))

    try:
        durchlaufen(leser.outline, 0)
    except Exception:
        pass

    vorne = "\n".join(seiten[:10])
    isbns = [isbn_normal(t) for t in ISBN.findall(pfad.name + "\n" + vorne)]
    isbns += [isbn10_zu_13(t) for t in ISBN10.findall(vorne)]
    return {
        "pfad": pfad_text,
        "seiten": seiten,
        "etiketten": etiketten,
        "gliederung": gliederung,
        "isbns": list(dict.fromkeys(i for i in isbns if i)),
        "dois": list(dict.fromkeys(DOI.findall(vorne))),
        "jahre": [int(j) for zeile in vorne.splitlines() if "©" in zeile
                  for j in re.findall(r"(?:19|20)\d{2}", zeile)],
        "auflage": (lambda t: t.group(1) if t else "")(
            re.search(r"(\d{1,2})\.\s*,?\s*(?:[\wäöüß-]+\s+){0,5}Auflage", vorne)),
        "titelseite": [" ".join(z.split()) for s in seiten[:4] for z in s.splitlines()
                       if len(z.strip()) > 2][:16],
    }


# ---------------------------------------------------------------------------
# Deutsche Nationalbibliothek
# ---------------------------------------------------------------------------

def dnb_abfragen(isbn: str) -> dict | None:
    """Bibliografische Angaben zu einer ISBN aus dem Katalog der DNB (kostenlos)."""
    url = (f"{DNB}?version=1.1&operation=searchRetrieve&recordSchema=MARC21-xml&query="
           + urllib.parse.quote(f"num={isbn}"))
    try:
        anfrage = urllib.request.Request(url, headers={"User-Agent": KENNUNG})
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            wurzel = ET.fromstring(antwort.read())
    except Exception:
        return None
    ziffern = isbn.replace("-", "")
    for satz in wurzel.iter("{http://www.loc.gov/MARC21/slim}record"):
        def felder(tag: str, code: str) -> list[str]:
            return [" ".join((sf.text or "").split())
                    for df in satz.findall(f"m:datafield[@tag='{tag}']", MARC)
                    for sf in df.findall(f"m:subfield[@code='{code}']", MARC) if sf.text]
        if not any(ziffern in f.replace("-", "") for f in felder("020", "a") + felder("020", "9")):
            continue
        return {"satz": satz, "felder": felder}
    return None


def aufbereiten(treffer: dict, isbn: str) -> dict:
    felder = treffer["felder"]
    satz = treffer["satz"]

    def sauber(text: str) -> str:
        text = unicodedata.normalize("NFC", re.sub("[¬]", "", text))
        return text.strip(" /:;,.")

    titel = sauber((felder("245", "a") or [""])[0])
    untertitel = sauber((felder("245", "b") or [""])[0])
    personen = []
    for tag in ("100", "700"):
        for df in satz.findall(f"m:datafield[@tag='{tag}']", MARC):
            name = df.find("m:subfield[@code='a']", MARC)
            rolle = " ".join((sf.text or "") for sf in df.findall("m:subfield[@code='4']", MARC)
                             + df.findall("m:subfield[@code='e']", MARC)).lower()
            if name is not None and name.text:
                art = "hrsg" if ("edt" in rolle or "herausgeber" in rolle) else (
                    "autor" if ("aut" in rolle or "verfasser" in rolle or tag == "100") else "")
                if art:
                    personen.append((sauber(name.text), art))
    herausgeber = [n for n, a in personen if a == "hrsg"]
    autoren = [n for n, a in personen if a == "autor"]
    namen, rolle = (herausgeber, "Hrsg.") if herausgeber else (autoren, "")
    auflage_text = (felder("250", "a") or [""])[0]
    auflage = (re.match(r"(\d+)", auflage_text) or [None, ""])[1] if auflage_text else ""
    ort = re.sub(r",\s*Germany$", "", sauber((felder("264", "a") or felder("260", "a") or [""])[0]))
    verlag = verlag_kuerzen(sauber((felder("264", "b") or felder("260", "b") or [""])[0]))
    jahr = (re.search(r"(?:19|20)\d{2}", " ".join(felder("264", "c") + felder("260", "c")))
            or [""])[0] if (felder("264", "c") or felder("260", "c")) else ""
    return {"titel": titel, "untertitel": untertitel, "personen": namen, "rolle": rolle,
            "auflage": auflage, "ort": ort, "verlag": verlag, "jahr": jahr, "isbn": isbn,
            "quelle_katalog": "Deutsche Nationalbibliothek"}


def crossref_personen(doi: str) -> tuple[list[str], str]:
    """Autoren oder Herausgeber aus den Verlagsdaten bei Crossref (kostenlos).

    Bei vielen Springer-E-Books führt die DNB keine Personen; der Verlag
    meldet sie aber mit der DOI an Crossref.
    """
    try:
        anfrage = urllib.request.Request(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
                                         headers={"User-Agent": KENNUNG})
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            daten = json.load(antwort)["message"]
    except Exception:
        return [], ""
    for feld, rolle in (("editor", "Hrsg."), ("author", "")):
        namen = [unicodedata.normalize("NFC", f"{p['family']}, {p['given']}" if p.get("given")
                                       else p["family"])
                 for p in daten.get(feld, []) if p.get("family")]
        if namen:
            return namen, rolle
    return [], ""


def zitat_bilden(angaben: dict) -> str:
    """Zitat ohne Seite und ohne ISBN; die Fußnote hängt beides an."""
    namen = angaben.get("personen") or []
    if len(namen) > 3:
        namen_text = f"{namen[0]} u. a."
    else:
        namen_text = "; ".join(namen)
    if namen_text and angaben.get("rolle"):
        namen_text += f" ({angaben['rolle']})"
    teile = [t for t in (angaben.get("titel", ""), angaben.get("untertitel", "")) if t]
    text = ""
    for teil in teile:
        text += (" " if text else "") + teil + ("" if teil[-1] in ".?!" else ".")
    if angaben.get("auflage") and angaben["auflage"] not in ("", "1"):
        text += f" {angaben['auflage']}. Aufl."
    ort_verlag = ": ".join(t for t in (angaben.get("ort"), angaben.get("verlag")) if t)
    if ort_verlag:
        text += f" {ort_verlag},"
    text += f" {angaben.get('jahr', '')}".rstrip()
    return f"{namen_text}: {text}".strip(": ").rstrip(",")


def kennung_bilden(angaben: dict, vergeben: set[str]) -> str:
    worte = [w for w in re.split(r"[\s/–-]+", angaben.get("titel", "")) if slug(w)
             and slug(w) not in STOPPWOERTER]
    if angaben.get("personen"):
        person = slug(angaben["personen"][0].split(",")[0])
        titelteil = "-".join(slug(w) for w in worte[:2])
    else:
        person, titelteil = "", "-".join(slug(w) for w in worte[:3])
    teile = [t for t in (person, titelteil or "titel", angaben.get("jahr") or "oj") if t]
    basis = "-".join(teile)
    kennung, n = basis, 2
    while kennung in vergeben:
        kennung, n = f"{basis}-{n}", n + 1
    vergeben.add(kennung)
    return kennung


def auflagen_kennzeichnen(katalog: list[dict]) -> None:
    """Ältere Auflagen und doppelte Dateien auf das aktuelle Werk verweisen.

    Liegt ein Buch in mehreren Auflagen vor (etwa „Grundlagen der Baustatik“
    in der 3. bis 6.), soll der Agent die neueste zitieren. Ältere bleiben im
    Katalog – etwa für den Stand zum Zeitpunkt einer Abnahme –, erscheinen in
    der Suche aber nur auf Wunsch.
    """
    for e in katalog:
        e.pop("ersetzt_durch", None)

    def verweisen(gruppe: list[dict]) -> None:
        gruppe = [e for e in gruppe if not e.get("ersetzt_durch")]
        if len(gruppe) < 2:
            return
        gruppe.sort(key=lambda e: (e.get("jahr") or "", int(e.get("auflage") or 0),
                                   len(e.get("personen") or []), e.get("seiten") or 0),
                    reverse=True)
        for aelter in gruppe[1:]:
            aelter["ersetzt_durch"] = gruppe[0]["kennung"]

    # Gleiche ISBN in zwei Dateien: dasselbe Buch, die vollständigere zählt.
    nach_isbn: dict[str, list[dict]] = {}
    for e in katalog:
        if e.get("isbn"):
            nach_isbn.setdefault(e["isbn"], []).append(e)
    for gruppe in nach_isbn.values():
        verweisen(gruppe)
    # Gleicher Titel und gleiche erste Person: mehrere Auflagen.
    gruppen: dict[str, list[dict]] = {}
    for e in katalog:
        if e.get("titel"):
            person = slug((e.get("personen") or [""])[0].split(",")[0])
            gruppen.setdefault(f"{slug(e['titel'])}|{person}", []).append(e)
    for gruppe in gruppen.values():
        verweisen(gruppe)


def verlag_kuerzen(verlag: str) -> str:
    """„Springer Fachmedien Wiesbaden, Imprint: Springer Vieweg“ wird „Springer Vieweg“."""
    return re.sub(r"^.*Imprint:\s*", "", verlag or "").strip()


def katalog_auffrischen(ziel: Path, katalog: list[dict], ergaenzungen: dict) -> None:
    """Zitate, Ergänzungen und Auflagenverweise neu setzen, ohne die PDFs zu lesen.

    Die Kennungen bleiben dabei unverändert, damit Texte und Gliederungen
    nicht umbenannt werden müssen.
    """
    for e in katalog:
        if e["pruefsumme"] in ergaenzungen:
            e.update({k: v for k, v in ergaenzungen[e["pruefsumme"]].items() if k != "kennung"})
        e["verlag"] = verlag_kuerzen(e.get("verlag", ""))
        e["zitat"] = zitat_bilden(e)
        isbn_teil = f" ISBN {e['isbn']}." if e.get("isbn") else ""
        for pfad, alt, neu in (
                (ziel / "texte" / f"{e['kennung']}.txt", r"^Zitat: .*$",
                 f"Zitat: {e['zitat']}, S. <Seite>.{isbn_teil}"),
                (ziel / "gliederung" / f"{e['kennung']}.md", r"^# Gliederung: .*$",
                 f"# Gliederung: {e['zitat']}")):
            if pfad.exists():
                inhalt = pfad.read_text(encoding="utf-8")
                pfad.write_text(re.sub(alt, lambda _t: neu, inhalt, count=1, flags=re.M),
                                encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pdf_ordner", type=Path)
    parser.add_argument("bibliothek", type=Path)
    parser.add_argument("--auslassen", nargs="*", default=[],
                        help="Unterordner, die nicht in die Bibliothek gehören")
    parser.add_argument("--grenze", type=int, default=0, help="nur die ersten n Werke (Test)")
    parser.add_argument("--prozesse", type=int, default=6)
    parser.add_argument("--nur-katalog", action="store_true",
                        help="nur Zitate, Ergänzungen und Auflagenverweise auffrischen; "
                             "die PDFs werden nicht gelesen")
    args = parser.parse_args()

    ziel = args.bibliothek
    (ziel / "texte").mkdir(parents=True, exist_ok=True)
    (ziel / "gliederung").mkdir(parents=True, exist_ok=True)
    katalog_pfad = ziel / "katalog.yml"
    katalog = yaml.safe_load(katalog_pfad.read_text(encoding="utf-8")) if katalog_pfad.exists() else []
    katalog = katalog or []
    bekannt = {e["pruefsumme"]: e for e in katalog}
    ergaenzungen_pfad = ziel / "katalog-ergaenzungen.yml"
    ergaenzungen = {}
    if ergaenzungen_pfad.exists():
        for eintrag in yaml.safe_load(ergaenzungen_pfad.read_text(encoding="utf-8")) or []:
            ergaenzungen[eintrag.pop("pruefsumme")] = eintrag

    if args.nur_katalog:
        katalog_auffrischen(ziel, katalog, ergaenzungen)
        auflagen_kennzeichnen(katalog)
        katalog_schreiben(katalog_pfad, katalog)
        print(f"Katalog aufgefrischt: {len(katalog)} Werke, "
              f"{sum(1 for e in katalog if e.get('ersetzt_durch'))} ältere Auflagen oder Dubletten.")
        return 0

    # PDFs sammeln, Dubletten über die Prüfsumme zusammenfassen.
    werke: dict[str, dict] = {}
    for pfad in sorted(args.pdf_ordner.rglob("*.pdf"), key=lambda p: str(p).lower()):
        teile = pfad.relative_to(args.pdf_ordner).parts
        thema = teile[0] if len(teile) > 1 else "Allgemein"
        if thema in args.auslassen:
            continue
        summe = pruefsumme(pfad)
        werk = werke.setdefault(summe, {"pfad": pfad, "themen": []})
        if thema not in werk["themen"]:
            werk["themen"].append(thema)
    print(f"{len(werke)} verschiedene Werke gefunden.")

    neu = [(summe, w) for summe, w in werke.items() if summe not in bekannt]
    if args.grenze:
        neu = neu[:args.grenze]
    for summe, w in werke.items():
        if summe in bekannt:
            bekannt[summe]["themen"] = sorted(w["themen"])
    print(f"Davon neu oder geändert: {len(neu)}")

    vergeben = {e["kennung"] for e in katalog}
    start = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.prozesse) as pool:
        ergebnisse = pool.map(pdf_lesen, [str(w["pfad"]) for _s, w in neu])
        for (summe, werk), gelesen in zip(neu, ergebnisse):
            angaben = None
            for isbn in gelesen["isbns"]:
                treffer = dnb_abfragen(isbn)
                time.sleep(0.5)
                if not treffer:
                    continue
                gefunden = aufbereiten(treffer, gelesen["isbns"][0])
                if not angaben:
                    angaben = gefunden
                elif not angaben["personen"] and gefunden["personen"]:
                    # Druckausgabe derselben Auflage nennt oft die Personen, die
                    # im E-Book-Datensatz fehlen.
                    angaben.update(personen=gefunden["personen"], rolle=gefunden["rolle"])
                if angaben["personen"]:
                    break
            springer = bool(gelesen["isbns"]) and gelesen["isbns"][0].startswith(SPRINGER)
            if angaben and (springer or not angaben["personen"]):
                # Springer meldet Autoren und Herausgeber vollständig an Crossref;
                # im DNB-Datensatz fehlen sie teils ganz oder teilweise.
                dois = [d for d in gelesen["dois"] if d.startswith("10.1007/")]
                dois += [f"10.1007/{i}" for i in gelesen["isbns"][:1] if i.startswith(SPRINGER)]
                for doi in list(dict.fromkeys(dois))[:2]:
                    namen, rolle = crossref_personen(doi)
                    time.sleep(0.5)
                    if namen:
                        angaben.update(personen=namen, rolle=rolle,
                                       quelle_katalog="Deutsche Nationalbibliothek; Personen: Crossref")
                        break
            if not angaben:
                # Nicht bei der DNB: Angaben aus dem Impressum, zur Prüfung markiert.
                angaben = {"titel": "", "untertitel": "", "personen": [], "rolle": "",
                           "auflage": gelesen["auflage"],
                           "ort": "", "verlag": "",
                           "jahr": str(max(gelesen["jahre"])) if gelesen["jahre"] else "",
                           "isbn": gelesen["isbns"][0] if gelesen["isbns"] else "",
                           "quelle_katalog": "Impressum – bitte prüfen",
                           "titelseite": gelesen["titelseite"]}
            # Von Hand ergänzte Angaben haben Vorrang (katalog-ergaenzungen.yml).
            art = "Fachbuch"
            if summe in ergaenzungen:
                angaben.update({k: v for k, v in ergaenzungen[summe].items() if k != "art"})
                art = ergaenzungen[summe].get("art", art)
                angaben.pop("titelseite", None)
            wunsch = angaben.pop("kennung", None)
            if wunsch and wunsch not in vergeben:
                kennung = wunsch
                vergeben.add(kennung)
            else:
                kennung = kennung_bilden(angaben, vergeben)
            eintrag = {"kennung": kennung, "zitat": zitat_bilden(angaben), **angaben,
                       "art": art, "themen": sorted(werk["themen"]),
                       "seiten": len(gelesen["seiten"]), "gliederung": len(gelesen["gliederung"]),
                       "datei": werk["pfad"].name, "pruefsumme": summe}

            isbn_teil = f" ISBN {eintrag['isbn']}." if eintrag["isbn"] else ""
            kopf = (f"Werk: {kennung}\nZitat: {eintrag['zitat']}, S. <Seite>.{isbn_teil}\n"
                    "Hinweis: Text aus der PDF-Ausgabe, Seitenzahlen wie gedruckt. Nur für die "
                    "interne Prüfung; wörtlich höchstens 25 Wörter zitieren.\n" + "=" * 70 + "\n")
            koerper = "\n".join(f"=== S. {etikett} | PDF {i + 1} ===\n{text}\n"
                                for i, (etikett, text) in enumerate(zip(gelesen["etiketten"],
                                                                         gelesen["seiten"])))
            (ziel / "texte" / f"{kennung}.txt").write_text(kopf + koerper, encoding="utf-8",
                                                           newline="\n")
            zeilen = [f"# Gliederung: {eintrag['zitat']}", ""]
            zeilen += [f"{'  ' * tiefe}- {titel} (S. {etikett}, PDF {pdf})"
                       for tiefe, titel, etikett, pdf in gelesen["gliederung"]]
            (ziel / "gliederung" / f"{kennung}.md").write_text("\n".join(zeilen) + "\n",
                                                               encoding="utf-8", newline="\n")
            katalog.append(eintrag)
            print(f"  {kennung:<45} {len(gelesen['seiten']):>5} S.  {angaben['quelle_katalog']}")

    auflagen_kennzeichnen(katalog)
    katalog_schreiben(katalog_pfad, katalog)
    print(f"Fertig in {time.monotonic() - start:.0f} s. Katalog: {len(katalog)} Werke.")
    return 0


def katalog_schreiben(pfad: Path, katalog: list[dict]) -> None:
    katalog.sort(key=lambda e: e["kennung"])
    pfad.write_text(
        "# Fachbibliothek des BIB Ingenieurbüros – erzeugt von tools/bibliothek_auszug.py.\n"
        "# Korrekturen gehören in katalog-ergaenzungen.yml; danach mit --nur-katalog auffrischen.\n"
        + yaml.safe_dump(katalog, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    sys.exit(main())
