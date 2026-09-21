#!/usr/bin/env python3
"""Sucht in der Fachbibliothek des Büros (privates Repository FachwissenAgent).

Die Bibliothek enthält den Text der Fachbücher Seite für Seite mit der
gedruckten Seitenzahl, das Inhaltsverzeichnis je Werk und einen Katalog mit
dem fertigen Zitat. Gesucht wird mit der Volltextsuche, die in Python
eingebaut ist (SQLite FTS5) – ohne weiteren Dienst.

Aufrufe:
    python tools/bibliothek_suchen.py <bibliothek> --index
        baut den Suchindex (einmal je Lauf, rund eine Minute)
    python tools/bibliothek_suchen.py <bibliothek> --katalog [--thema <Thema>]
        alle Werke mit Kennung, Jahr, Themen und Titel
    python tools/bibliothek_suchen.py <bibliothek> "<Suchwörter>" [--werk <kennung>] [--anzahl 8] [--alle-auflagen]
        die passendsten Seiten. Jedes Wort wird als Wortanfang gesucht: „abdicht“
        findet „Abdichtung“ und „Abdichtungsbahn“; Umlaute sind gleichgültig.
        Wörter in Anführungszeichen gelten als Wortgruppe.
    python tools/bibliothek_suchen.py <bibliothek> --gliederung <kennung> [--tiefe 2]
        Inhaltsverzeichnis eines Werkes mit Seitenzahlen
    python tools/bibliothek_suchen.py <bibliothek> --werk <kennung> --seite <S> [--bis <S>]
        Text der gedruckten Seite(n) – zum Lesen und Zitieren
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

KOPF = re.compile(r"^=== S\. (.+?) \| PDF (\d+) ===$", re.M)
GLIEDERUNG = re.compile(r"^( *)- (.+) \(S\. ([^,]+), PDF (\d+)\)$")
JE_WERK = 3   # höchstens so viele Treffer aus demselben Werk


def katalog_laden(bibliothek: Path) -> list[dict]:
    import yaml  # nur hier nötig; im Workflow installiert
    return yaml.safe_load((bibliothek / "katalog.yml").read_text(encoding="utf-8")) or []


def fussnote(eintrag: dict, seite: str = "<Seite>") -> str:
    isbn = f" ISBN {eintrag['isbn']}." if eintrag.get("isbn") else ""
    return f"{eintrag['zitat']}, S. {seite}.{isbn}"


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
    for datei in sorted((bibliothek / "texte").glob("*.txt")):
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
        gl = bibliothek / "gliederung" / f"{kennung}.md"
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
        titel = kapitel(db, kennung, pdf)
        print(f"[{nummer}] {kennung} · S. {seite}" + (f" · Kap.: {titel}" if titel else ""))
        print("    " + " ".join(auszug.split()))
    print("\nZitierweise in der Fußnote (Seite einsetzen):")
    for kennung in dict.fromkeys(z[0] for z in auswahl):
        if kennung in katalog:
            print(f"  {kennung}: {fussnote(katalog[kennung])}")
    print(f"\nGanze Seite lesen: python tools/bibliothek_suchen.py {bibliothek.as_posix()} "
          "--werk <kennung> --seite <S>")


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
    for seite, pdf, text in db.execute(
            "SELECT seite, pdf, text FROM seiten WHERE kennung = ? AND pdf BETWEEN ? AND ? ORDER BY pdf",
            (werk, start[0], ende[0])):
        titel = kapitel(db, werk, pdf)
        print(f"=== {werk} · S. {seite}" + (f" · Kap.: {titel}" if titel else "") + " ===")
        print(text)
        print()
    if katalog[werk].get("ersetzt_durch"):
        print(f"Achtung: ältere Auflage. Aktuell ist {katalog[werk]['ersetzt_durch']} – "
              "für geltende Aussagen dort nachsehen.")
    seite_text = von if not bis or bis == von else f"{von}–{bis}"
    print(f"Fußnote: {fussnote(katalog[werk], seite_text)}")
    print(f"Stand des Werkes: {katalog[werk].get('jahr') or 'unbekannt'} – bei Normaussagen prüfen, "
          "ob die zitierte Fassung noch gilt.")


def katalog_zeigen(bibliothek: Path, thema: str | None) -> None:
    for e in katalog_laden(bibliothek):
        themen = ", ".join(e.get("themen") or [])
        if thema and thema.lower() not in themen.lower():
            continue
        titel = e.get("titel") or "(Titel fehlt)"
        hinweis = f"  → ältere Auflage, aktuell: {e['ersetzt_durch']}" if e.get("ersetzt_durch") else ""
        print(f"{e['kennung']:<48} {e.get('jahr') or '?':>4}  [{themen}]  {titel[:70]}{hinweis}")


def gliederung_zeigen(bibliothek: Path, werk: str, tiefe: int) -> None:
    pfad = bibliothek / "gliederung" / f"{werk}.md"
    if not pfad.exists():
        print(f"Keine Gliederung zu „{werk}“.")
        return
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        t = GLIEDERUNG.match(zeile)
        if not t or len(t.group(1)) // 2 < tiefe:
            print(zeile)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bibliothek", type=Path)
    parser.add_argument("suchtext", nargs="?")
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--katalog", action="store_true")
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

    if not (args.bibliothek / "katalog.yml").exists():
        print(f"Keine Fachbibliothek unter {args.bibliothek} (katalog.yml fehlt).")
        return 2
    if args.index:
        index_bauen(args.bibliothek)
    elif args.katalog:
        katalog_zeigen(args.bibliothek, args.thema)
    elif args.gliederung:
        gliederung_zeigen(args.bibliothek, args.gliederung, args.tiefe)
    elif args.seite:
        if not args.werk:
            print("--seite braucht --werk <kennung>.")
            return 2
        seiten_zeigen(args.bibliothek, args.werk, args.seite, args.bis)
    elif args.suchtext:
        suchen(args.bibliothek, args.suchtext, args.werk, args.anzahl, args.alle_auflagen)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
