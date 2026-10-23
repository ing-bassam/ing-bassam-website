#!/usr/bin/env python3
"""Sucht in der Fachbibliothek des Büros (privates Repository FachwissenAgent).

Die Bibliothek enthält den Text der Fachbücher Seite für Seite mit der
gedruckten Seitenzahl, das Inhaltsverzeichnis je Werk und einen Katalog mit
dem fertigen Zitat. Gesucht wird mit der Volltextsuche, die in Python
eingebaut ist (SQLite FTS5) – ohne weiteren Dienst.

Dazu kommt, was der Workflow „Wissen sammeln“ im Bibliotheks-Repository jede
Nacht ergänzt; die Suche umfasst alles:

    forschung/   frei zugängliche Forschungsarbeiten (Kennung fo-…) – Text mit
                 Seitenzahlen wie bei den Büchern, Fußnote mit Seite und Adresse
    quellen/     Steckbriefe geprüfter Webquellen aus freigegebenen Beiträgen
                 (Kennung wq-…) – Adresse, belegte Aussagen, Belegstück; kein Volltext
    erfahrungen.md  das Erfahrungsbuch (wird gelesen, nicht durchsucht)
    normen/ausgaben.yml  Normenindex: je Norm neueste und ältere Ausgaben,
                 Änderungen, Berichtigungen – nur Metadaten, kein Normtext

Die Texte dienen nur dazu, Fakten zu prüfen. Übernommen wird nichts wörtlich
(kein Satz, kein Satzteil, keine Tabelle, keine Abbildung, kein
Rechenbeispiel); die Aussage steht in eigenen Worten mit Fundstelle.

Aufrufe:
    python tools/bibliothek_suchen.py <bibliothek> --index
        baut den Suchindex (einmal je Lauf, rund eine Minute)
    python tools/bibliothek_suchen.py <bibliothek> --katalog [--thema <Thema>]
        alle Fachbücher mit Kennung, Jahr, Themen und Titel; dazu die Zahl der
        Forschungsarbeiten und Webquellen
    python tools/bibliothek_suchen.py <bibliothek> --forschung [--thema <Thema>]
        alle Forschungsarbeiten
    python tools/bibliothek_suchen.py <bibliothek> --webquellen [--thema <Thema>]
        alle Steckbriefe geprüfter Webquellen
    python tools/bibliothek_suchen.py <bibliothek> "<Suchwörter>" [--werk <kennung>] [--anzahl 8] [--alle-auflagen]
        die passendsten Seiten. Jedes Wort wird als Wortanfang gesucht: „abdicht“
        findet „Abdichtung“ und „Abdichtungsbahn“; Umlaute sind gleichgültig.
        Wörter in Anführungszeichen gelten als Wortgruppe.
    python tools/bibliothek_suchen.py <bibliothek> --gliederung <kennung> [--tiefe 2]
        Inhaltsverzeichnis eines Werkes mit Seitenzahlen
    python tools/bibliothek_suchen.py <bibliothek> --werk <kennung> --seite <S> [--bis <S>]
        Text der gedruckten Seite(n) – zum Prüfen, nicht zum Übernehmen
    python tools/bibliothek_suchen.py --norm "DIN 4109-1" [--bibliothek <bibliothek>]
        neueste Ausgabe einer Norm laut Normenindex, dazu Änderungen,
        Berichtigungen und ältere Ausgaben (Standard-Ordner: .bibliothek).
        Rückgabewert 0 = gefunden, 1 = nicht im Index, 2 = Index fehlt.
        Den Status bestätigt danach die Primärquelle (DIN Media).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path

KOPF = re.compile(r"^=== S\. (.+?) \| PDF (\d+) ===$", re.M)
GLIEDERUNG = re.compile(r"^( *)- (.+) \(S\. ([^,]+), PDF (\d+)\)$")
JE_WERK = 3   # höchstens so viele Treffer aus demselben Werk
# Teile der Bibliothek: Fachbücher (oberste Ebene), Forschungsarbeiten, Steckbriefe von Webquellen
BEREICHE = ("", "forschung", "quellen")
# Normenindex (nur Metadaten) und sein Höchstalter – dieselbe Grenze meldet die Wöchentliche Prüfung.
NORMENINDEX = Path("normen") / "ausgaben.yml"
INDEX_HOECHSTALTER = 45   # Tage
# Steht nach jeder gelesenen Seite: Die Bibliothek dient der Prüfung, nicht als Textvorlage.
NICHT_UEBERNEHMEN = ("Nur zum Prüfen: nichts wörtlich übernehmen (kein Satz, kein Satzteil, keine Tabelle, "
                     "keine Abbildung, kein Rechenbeispiel) – die Aussage in eigenen Worten mit dieser Fundstelle.")


def katalog_laden(bibliothek: Path) -> list[dict]:
    """Alle Einträge aller Teile; `_bereich` sagt, in welchem Ordner Text und Gliederung liegen."""
    import yaml  # nur hier nötig; im Workflow installiert
    alle = []
    for bereich in BEREICHE:
        datei = bibliothek / bereich / "katalog.yml"
        if datei.exists():
            for eintrag in yaml.safe_load(datei.read_text(encoding="utf-8")) or []:
                alle.append({**eintrag, "_bereich": bereich})
    return alle


def ist_webquelle(eintrag: dict) -> bool:
    return eintrag.get("art") == "Webquelle"


def satzende(text: str) -> str:
    return text if text[-1:] in ".?!" else text + "."


def fussnote(eintrag: dict, seite: str = "<Seite>") -> str:
    if ist_webquelle(eintrag):
        return f"{satzende(eintrag['zitat'])} {eintrag['url']} (abgerufen am <Laufdatum>)."
    if eintrag.get("url"):        # Forschungsarbeit im Netz: Seite und Adresse
        return f"{eintrag['zitat']}, S. {seite}. {eintrag['url']} (abgerufen am <Laufdatum>)."
    isbn = f" ISBN {eintrag['isbn']}." if eintrag.get("isbn") else ""
    return f"{eintrag['zitat']}, S. {seite}.{isbn}"


def ordner(bibliothek: Path, eintrag: dict | None) -> Path:
    return bibliothek / ((eintrag or {}).get("_bereich") or "")


def index_pfad(bibliothek: Path) -> Path:
    return bibliothek / ".suchindex.sqlite"


def index_bauen(bibliothek: Path) -> None:
    pfad = index_pfad(bibliothek)
    if pfad.exists():
        pfad.unlink()
    db = sqlite3.connect(pfad)
    db.execute("CREATE VIRTUAL TABLE seiten USING fts5(kennung UNINDEXED, seite UNINDEXED, "
               "pdf UNINDEXED, text, tokenize='unicode61 remove_diacritics 2')")
    db.execute("CREATE TABLE gliederung (kennung TEXT, tiefe INT, titel TEXT, seite TEXT, pdf INT)")
    db.execute("CREATE TABLE werke (kennung TEXT PRIMARY KEY, ersetzt TEXT)")
    db.executemany("INSERT INTO werke VALUES (?, ?)",
                   [(e["kennung"], e.get("ersetzt_durch") or "") for e in katalog_laden(bibliothek)])
    werke = seiten_gesamt = 0
    dateien = [d for bereich in BEREICHE for d in sorted((bibliothek / bereich / "texte").glob("*.txt"))]
    for datei in dateien:
        kennung = datei.stem
        inhalt = datei.read_text(encoding="utf-8")
        treffer = list(KOPF.finditer(inhalt))
        zeilen = []
        for i, kopf in enumerate(treffer):
            ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(inhalt)
            text = inhalt[kopf.end():ende].strip()
            if text:
                zeilen.append((kennung, kopf.group(1), int(kopf.group(2)), text))
        db.executemany("INSERT INTO seiten VALUES (?, ?, ?, ?)", zeilen)
        werke += 1
        seiten_gesamt += len(zeilen)
        gl = datei.parent.parent / "gliederung" / f"{kennung}.md"
        if gl.exists():
            eintraege = []
            for zeile in gl.read_text(encoding="utf-8").splitlines():
                t = GLIEDERUNG.match(zeile)
                if t:
                    eintraege.append((kennung, len(t.group(1)) // 2, t.group(2), t.group(3),
                                      int(t.group(4))))
            db.executemany("INSERT INTO gliederung VALUES (?, ?, ?, ?, ?)", eintraege)
    db.execute("CREATE INDEX gl_werk ON gliederung (kennung, pdf)")
    db.commit()
    db.close()
    print(f"Suchindex gebaut: {werke} Werke, {seiten_gesamt} Seiten.")


def verbinden(bibliothek: Path) -> sqlite3.Connection:
    if not index_pfad(bibliothek).exists():
        print("(Suchindex fehlt – wird jetzt gebaut.)")
        index_bauen(bibliothek)
    return sqlite3.connect(index_pfad(bibliothek))


# Zulässige Doppelschreibungen: Die Bücher schreiben teils „selbständig“, teils
# „selbstständig“ – gesucht wird nach beiden.
SCHREIBWEISEN = [("selbstständ", "selbständ"), ("selbständ", "selbstständ")]


def anfrage_bilden(suchtext: str, verknuepfung: str) -> str:
    teile = []
    for gruppe, wort in re.findall(r'"([^"]+)"|(\S+)', suchtext):
        if gruppe:
            woerter = re.findall(r"\w+", gruppe)
            if woerter:
                teile.append('"' + " ".join(woerter) + '"')
        else:
            wort = re.sub(r"[^\w]", "", wort)
            if not wort:
                continue
            formen = [wort]
            for alt, neu in SCHREIBWEISEN:
                if alt in wort.lower():
                    formen.append(wort.lower().replace(alt, neu))
                    break
            teile.append("(" + " OR ".join(f'"{f}"*' for f in formen) + ")"
                         if len(formen) > 1 else f'"{wort}"*')
    return f" {verknuepfung} ".join(teile)


def kapitel(db: sqlite3.Connection, kennung: str, pdf: int) -> str:
    zeile = db.execute("SELECT titel, seite FROM gliederung WHERE kennung = ? AND pdf <= ? "
                       "ORDER BY pdf DESC, tiefe DESC LIMIT 1", (kennung, pdf)).fetchone()
    return zeile[0] if zeile else ""


def suchen(bibliothek: Path, suchtext: str, werk: str, anzahl: int, alle: bool = False) -> None:
    katalog = {e["kennung"]: e for e in katalog_laden(bibliothek)}
    db = verbinden(bibliothek)
    zeilen, hinweis = [], ""
    for verknuepfung in ("AND", "OR"):
        anfrage = anfrage_bilden(suchtext, verknuepfung)
        if not anfrage:
            print("Keine Suchwörter.")
            return
        sql = ("SELECT kennung, seite, pdf, snippet(seiten, 3, '»', '«', ' … ', 28) "
               "FROM seiten WHERE seiten MATCH ?" + (" AND kennung = ?" if werk else "")
               + ("" if (werk or alle) else
                  " AND kennung NOT IN (SELECT kennung FROM werke WHERE ersetzt != '')")
               + " ORDER BY bm25(seiten) LIMIT 200")
        try:
            neue = db.execute(sql, (anfrage, werk) if werk else (anfrage,)).fetchall()
        except sqlite3.OperationalError as fehler:
            print(f"Suchanfrage nicht verstanden ({fehler}).")
            return
        bekannt = {(z[0], z[1]) for z in zeilen}
        zeilen += [z for z in neue if (z[0], z[1]) not in bekannt]
        # Wenige Seiten enthalten alle Wörter: breiter suchen und anhängen.
        if len(zeilen) >= max(3, anzahl // 2) or " " not in suchtext.strip():
            break
        if verknuepfung == "AND":
            hinweis = ("(Wenige Seiten enthalten alle Wörter – dahinter folgen Seiten mit "
                       "einem Teil der Wörter.)" if zeilen else
                       "(Keine Seite enthält alle Wörter – Ergebnis der ODER-Suche.)")
    if not zeilen:
        print("Keine Treffer. Andere Wörter oder Wortanfänge versuchen, etwa Fachbegriff "
              "statt Umschreibung.")
        return
    if hinweis:
        print(hinweis)
    if not (werk or alle):
        print("(Ältere Auflagen sind ausgeblendet; mit --alle-auflagen einbeziehen.)")

    # Treffer in Verzeichnissen (Stichwort-, Literatur-, Inhaltsverzeichnis)
    # belegen nichts; sie rücken ans Ende.
    verzeichnis = re.compile(r"(Stichwort|Sach|Literatur|Abkürzungs|Inhalts)verzeichnis|"
                             r"^(Literatur|Index|Register)$", re.I)
    zeilen.sort(key=lambda z: bool(verzeichnis.search(kapitel(db, z[0], z[2]))))
    auswahl, je_werk = [], {}
    for zeile in zeilen:
        if werk or je_werk.get(zeile[0], 0) < JE_WERK:
            auswahl.append(zeile)
            je_werk[zeile[0]] = je_werk.get(zeile[0], 0) + 1
        if len(auswahl) >= anzahl:
            break

    for nummer, (kennung, seite, pdf, auszug) in enumerate(auswahl, 1):
        eintrag = katalog.get(kennung, {})
        if ist_webquelle(eintrag):
            print(f"[{nummer}] {kennung} · Steckbrief einer geprüften Webquelle ({eintrag.get('quelltyp')}, "
                  f"{eintrag.get('domain')}; zuletzt belegt {eintrag.get('zuletzt_belegt')})")
        else:
            titel = kapitel(db, kennung, pdf)
            art = f" · {eintrag.get('art')}" if eintrag.get("_bereich") == "forschung" else ""
            print(f"[{nummer}] {kennung}{art} · S. {seite}" + (f" · Kap.: {titel}" if titel else ""))
        print("    " + " ".join(auszug.split()))
    print("\nFundstelle für die Fußnote (Seite einsetzen, Abrufdatum = Laufdatum; "
          "die Aussage selbst in eigenen Worten):")
    for kennung in dict.fromkeys(z[0] for z in auswahl):
        if kennung in katalog:
            print(f"  {kennung}: {fussnote(katalog[kennung])}")
    print(f"\nGanze Seite lesen: python tools/bibliothek_suchen.py {bibliothek.as_posix()} "
          "--werk <kennung> --seite <S>")
    if any(ist_webquelle(katalog.get(z[0], {})) for z in auswahl):
        print("Steckbrief einer Webquelle lesen: --werk <wq-…> --seite 1")


def seiten_zeigen(bibliothek: Path, werk: str, von: str, bis: str | None) -> None:
    katalog = {e["kennung"]: e for e in katalog_laden(bibliothek)}
    if werk not in katalog:
        print(f"Unbekannte Kennung „{werk}“. Alle Werke: --katalog")
        return
    db = verbinden(bibliothek)
    start = db.execute("SELECT pdf FROM seiten WHERE kennung = ? AND seite = ?", (werk, von)).fetchone()
    if not start:
        print(f"Seite {von} gibt es in {werk} nicht (Seitenzahlen wie gedruckt, z. B. 214 oder XII).")
        return
    ende = start
    if bis:
        ende = db.execute("SELECT pdf FROM seiten WHERE kennung = ? AND seite = ?", (werk, bis)).fetchone()
        if not ende or ende[0] < start[0]:
            print(f"Seite {bis} gibt es nicht oder sie liegt vor {von}.")
            return
    if ende[0] - start[0] > 5:
        print("Höchstens sechs Seiten auf einmal.")
        return
    eintrag = katalog[werk]
    for seite, pdf, text in db.execute(
            "SELECT seite, pdf, text FROM seiten WHERE kennung = ? AND pdf BETWEEN ? AND ? ORDER BY pdf",
            (werk, start[0], ende[0])):
        titel = kapitel(db, werk, pdf)
        kopf = "Steckbrief" if ist_webquelle(eintrag) else f"S. {seite}" + (f" · Kap.: {titel}" if titel else "")
        print(f"=== {werk} · {kopf} ===")
        print(text)
        print()
    if eintrag.get("ersetzt_durch"):
        print(f"Achtung: ältere Auflage. Aktuell ist {eintrag['ersetzt_durch']} – "
              "für geltende Aussagen dort nachsehen.")
    seite_text = von if not bis or bis == von else f"{von}–{bis}"
    print(f"Fußnote: {fussnote(eintrag, seite_text)}")
    print(NICHT_UEBERNEHMEN)
    # Bücher und Arbeiten zitieren oft ältere Normausgaben; die neueste nennt der Normenindex.
    neueste = 'Neueste Ausgabe einer Norm: python tools/bibliothek_suchen.py --norm "<Norm>".'
    if ist_webquelle(eintrag):
        print(f"Zuletzt in einem freigegebenen Beitrag belegt: {eintrag.get('zuletzt_belegt') or 'unbekannt'}. "
              "Den aktuellen Stand – Normstatus, Gesetzesfassung, geänderte Seite – zeigt nur die Adresse.")
    elif eintrag.get("_bereich") == "forschung":
        print(f"Stand der Arbeit: {eintrag.get('jahr') or 'unbekannt'} ({eintrag.get('art')}, frei zugänglich, "
              f"Lizenz {eintrag.get('lizenz') or 'unbekannt'}) – bei Normaussagen prüfen, ob die Fassung noch gilt. "
              + neueste)
    else:
        print(f"Stand des Werkes: {eintrag.get('jahr') or 'unbekannt'} – bei Normaussagen prüfen, "
              "ob die zitierte Fassung noch gilt; eine Buchaussage zu einer Norm nur übernehmen, wenn die "
              "neueste Ausgabe sie trägt. " + neueste)


def katalog_zeigen(bibliothek: Path, thema: str | None, teil: str = "") -> None:
    """`teil`: „“ für die Fachbücher, „forschung“ oder „quellen“."""
    katalog = katalog_laden(bibliothek)
    for e in katalog:
        themen = ", ".join(e.get("themen") or [])
        if e["_bereich"] != teil or (thema and thema.lower() not in themen.lower()):
            continue
        titel = e.get("titel") or "(Titel fehlt)"
        if ist_webquelle(e):
            print(f"{e['kennung']:<36} {e.get('zuletzt_belegt') or '?'}  [{e.get('quelltyp')}]  {titel[:80]}")
            continue
        art = f"{e.get('art')}: " if teil == "forschung" else ""
        hinweis = f"  → ältere Auflage, aktuell: {e['ersetzt_durch']}" if e.get("ersetzt_durch") else ""
        print(f"{e['kennung']:<48} {e.get('jahr') or '?':>4}  [{themen}]  {art}{titel[:70]}{hinweis}")
    if not teil:
        forschung = sum(1 for e in katalog if e["_bereich"] == "forschung")
        quellen = sum(1 for e in katalog if e["_bereich"] == "quellen")
        if forschung or quellen:
            print(f"\nDazu {forschung} Forschungsarbeiten (Liste: --forschung) und {quellen} Steckbriefe "
                  "geprüfter Webquellen (Liste: --webquellen) – beide erscheinen in der Suche.")


def gliederung_zeigen(bibliothek: Path, werk: str, tiefe: int) -> None:
    eintrag = next((e for e in katalog_laden(bibliothek) if e["kennung"] == werk), None)
    pfad = ordner(bibliothek, eintrag) / "gliederung" / f"{werk}.md"
    if not pfad.exists():
        print(f"Keine Gliederung zu „{werk}“.")
        return
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        t = GLIEDERUNG.match(zeile)
        if not t or len(t.group(1)) // 2 < tiefe:
            print(zeile)


def norm_schluessel(bezeichnung: str) -> str:
    """Normbezeichnung in der Form des Feldes `schluessel` im Normenindex: Großbuchstaben,
    einfache Leerzeichen, ohne Ausgabe, Änderung und Berichtigung.

    „din 4109-1:2018-01“ → „DIN 4109-1“, „DIN 4109-1/A1:2026-09“ → „DIN 4109-1“, „VDI4100“ → „VDI 4100“.
    Dieselben Regeln wie normstand_pruefen.schluessel und normen_index.py (FachwissenAgent): Änderung
    als „/A1“ oder „-A1“, „DIN-TS“, „DIN/TS“ und „DIN TS“ → „DIN TS“ (ebenso SPEC), „-NA“ → „/NA“.
    """
    s = " ".join(bezeichnung.replace(" ", " ").upper().split())
    s = re.sub(r"\b([A-ZÄÖÜ]{2,})(?=\d)", r"\1 ", s)                 # „DIN4109“ → „DIN 4109“
    s = re.sub(r"\s*:\s*\d{4}(-\d{1,2})?\b.*$", "", s)                # Ausgabe
    s = re.sub(r"\s*[/-]\s*A\d+\b.*$", "", s)                         # Änderung A1, A2 … („/A1“, „-A1“)
    s = re.sub(r"\s+(BERICHTIGUNG|BER\.)\s*\d*.*$", "", s)             # Berichtigung
    s = re.sub(r"^DIN\s*[/-]?\s*(TS|SPEC)\b", r"DIN \1", s)          # DIN-TS, DIN/TS, DIN TS
    s = re.sub(r"\s*[/-]\s*NA\b", "/NA", s)                           # Nationaler Anhang: /NA oder -NA
    return s.strip()


def als_liste(wert) -> list[str]:
    if not wert:
        return []
    if isinstance(wert, (list, tuple)):
        return [str(w).strip() for w in wert if str(w).strip()]
    return [str(wert).strip()]


def index_alter(stand, heute: dt.date | None = None) -> int | None:
    """Alter des Normenindex in Tagen; None, wenn `stand_index` fehlt oder kein Datum ist."""
    try:
        datum = stand if isinstance(stand, dt.date) else dt.date.fromisoformat(str(stand).strip())
    except ValueError:
        return None
    return ((heute or dt.date.today()) - datum).days


def norm_zeigen(bibliothek: Path, bezeichnung: str, heute: dt.date | None = None) -> int:
    """Zeigt Ausgaben einer Norm aus normen/ausgaben.yml – nur Metadaten, nie Normtext.

    Rückgabewert: 0 gefunden, 1 nicht im Index, 2 Index fehlt oder ist unlesbar.
    """
    pfad = bibliothek / NORMENINDEX
    if not pfad.is_file():
        print(f"Kein Normenindex unter {pfad.as_posix()} – Fachbibliothek nicht geladen oder ohne "
              "normen/ausgaben.yml. Ausgabe und Status dann nur über Stufe 2 bestimmen "
              "(Status bei DIN Media bestätigen).")
        return 2
    try:
        import yaml  # nur hier nötig; im Workflow installiert
        index = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    except Exception as fehler:  # noqa: BLE001 – jede Störung heißt: Index nicht nutzbar
        print(f"Normenindex {pfad.as_posix()} nicht lesbar ({type(fehler).__name__}). Ausgabe und Status "
              "dann nur über Stufe 2 bestimmen (Status bei DIN Media bestätigen).")
        return 2
    if not isinstance(index, dict):
        print(f"Normenindex {pfad.as_posix()} hat nicht den erwarteten Aufbau (Schlüssel „normen“ fehlt).")
        return 2

    gesucht = norm_schluessel(bezeichnung)
    normen = [n for n in index.get("normen") or [] if isinstance(n, dict)]

    def schluessel(n: dict) -> str:
        return norm_schluessel(str(n.get("schluessel") or n.get("norm") or ""))

    treffer = [n for n in normen if schluessel(n) == gesucht]
    if not treffer:
        print(f"„{gesucht}“ steht nicht im Normenindex der Fachbibliothek.")
        # Eine Reihe („DIN 4109“) steht dort nur mit ihren Teilen („DIN 4109-1“ …).
        teile = sorted({str(n.get("norm") or schluessel(n)) for n in normen
                        if schluessel(n).startswith(gesucht + "-")})
        if teile:
            print("Teile dieser Reihe im Index: " + ", ".join(teile[:20]) + (" …" if len(teile) > 20 else ""))
            print(f'Einzeln abfragen, etwa: python tools/bibliothek_suchen.py --norm "{teile[0]}"')
        print("Ausgabe und Status nur über Stufe 2 bestimmen – Status bei DIN Media bestätigen.")
        index_stand_zeigen(index, heute)
        return 1

    for n in treffer:
        print(str(n.get("norm") or gesucht))
        thema = str(n.get("thema") or "").strip()
        sachgebiet = str(n.get("sachgebiet") or "").strip()
        if thema or sachgebiet:
            print(f"  Thema laut Index: {thema or '–'}" + (f" (Sachgebiet {sachgebiet})" if sachgebiet else "")
                  + " – Gruppenbezeichnung, kein amtlicher Titel")
        print(f"  Neueste Ausgabe in der Fachbibliothek: {str(n.get('neueste') or '').strip() or 'unbekannt'}")
        print(f"  Änderungen: {', '.join(als_liste(n.get('aenderungen'))) or 'keine'}")
        print(f"  Berichtigungen: {', '.join(als_liste(n.get('berichtigungen'))) or 'keine'}")
        print(f"  Ältere Ausgaben: {', '.join(als_liste(n.get('aeltere'))) or 'keine'}")
        if n.get("sprache"):
            print(f"  Sprache: {n['sprache']}")
        if n.get("pruefen") is True:
            print("  Im Index auffällig (pruefen: true) – Ausgabe besonders sorgfältig an der Primärquelle prüfen.")
    index_stand_zeigen(index, heute)
    print("Status bei DIN Media bestätigen (Stufe 2): Ob die neueste Ausgabe gilt oder inzwischen ersetzt ist, "
          "zeigt nur der Herausgeber.")
    print("Bücher zitieren oft ältere Ausgaben: Eine Buchaussage zu dieser Norm nur übernehmen, wenn die "
          "neueste Ausgabe sie trägt.")
    return 0


def index_stand_zeigen(index: dict, heute: dt.date | None = None) -> None:
    stand = index.get("stand_index")
    quelle = f" (aus {index['quelle']})" if index.get("quelle") else ""
    print(f"Stand des Normenindex: {stand or 'unbekannt'}{quelle}. Nur Metadaten – kein Normtext.")
    alter = index_alter(stand, heute)
    if alter is None or alter > INDEX_HOECHSTALTER:
        print(f"Achtung: Der Normenindex ist {'unbekannten Alters' if alter is None else f'{alter} Tage alt'} – "
              "neuere Ausgaben sind möglich.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bibliothek", type=Path, nargs="?",
                        help="Ordner der Fachbibliothek (Standard: .bibliothek)")
    parser.add_argument("suchtext", nargs="?")
    parser.add_argument("--norm", metavar="NORM",
                        help="Ausgaben einer Norm aus dem Normenindex, etwa „DIN 4109-1“")
    parser.add_argument("--bibliothek", dest="bibliothek_ordner", type=Path, metavar="ORDNER",
                        help="Ordner der Fachbibliothek (statt des ersten Arguments)")
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--katalog", action="store_true")
    parser.add_argument("--forschung", action="store_true", help="alle Forschungsarbeiten")
    parser.add_argument("--webquellen", action="store_true", help="alle Steckbriefe geprüfter Webquellen")
    parser.add_argument("--thema")
    parser.add_argument("--gliederung", metavar="KENNUNG")
    parser.add_argument("--tiefe", type=int, default=2)
    parser.add_argument("--werk", metavar="KENNUNG")
    parser.add_argument("--seite")
    parser.add_argument("--bis")
    parser.add_argument("--anzahl", type=int, default=8)
    parser.add_argument("--alle-auflagen", action="store_true",
                        help="auch ältere Auflagen durchsuchen")
    args = parser.parse_args()
    bibliothek = args.bibliothek_ordner or args.bibliothek or Path(".bibliothek")

    # Der Normenindex braucht nur normen/ausgaben.yml, nicht den Katalog der Bücher.
    if args.norm:
        return norm_zeigen(bibliothek, args.norm)
    if not (bibliothek / "katalog.yml").exists():
        print(f"Keine Fachbibliothek unter {bibliothek} (katalog.yml fehlt).")
        return 2
    if args.index:
        index_bauen(bibliothek)
    elif args.katalog:
        katalog_zeigen(bibliothek, args.thema)
    elif args.forschung:
        katalog_zeigen(bibliothek, args.thema, "forschung")
    elif args.webquellen:
        katalog_zeigen(bibliothek, args.thema, "quellen")
    elif args.gliederung:
        gliederung_zeigen(bibliothek, args.gliederung, args.tiefe)
    elif args.seite:
        if not args.werk:
            print("--seite braucht --werk <kennung>.")
            return 2
        seiten_zeigen(bibliothek, args.werk, args.seite, args.bis)
    elif args.suchtext:
        suchen(bibliothek, args.suchtext, args.werk, args.anzahl, args.alle_auflagen)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
