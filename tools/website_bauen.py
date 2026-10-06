#!/usr/bin/env python3
"""Stellt die Website zusammen – nur die Dateien, die ein Besucher abrufen kann.

Warum: GitHub Pages lieferte bis Oktober 2026 das ganze Repository aus. Unter
ing-bassam.de waren damit auch Agenten (.claude/), Workflows, Werkzeuge (tools/),
Tests, Entwürfe, Marketing-Unterlagen, Fachliteratur und Rohdaten abrufbar.
Seitdem baut der Workflow „Website ausliefern“ mit diesem Skript ein Verzeichnis
nur aus freigegebenen Dateien und veröffentlicht ausschließlich dieses.

Regel: Positivliste. Ausgeliefert wird nur, was unten ausdrücklich freigegeben
ist. Ein neuer Ordner oder eine neue Datei auf oberster Ebene bleibt intern, bis
sie hier eingetragen ist. tests/test_website_bauen.py verlangt, dass jeder
Eintrag der obersten Ebene einer der beiden Listen zugeordnet ist, und prüft,
dass jede ausgelieferte Seite nur auf ausgelieferte Dateien verweist.

Aufruf:
    python tools/website_bauen.py --ziel _site    Verzeichnis bauen (darf nicht existieren oder muss leer sein)
    python tools/website_bauen.py --liste         ausgelieferte Dateien auflisten
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

WURZEL = Path(__file__).resolve().parent.parent

# Dateien auf oberster Ebene, die zur Website gehören.
DATEIEN = {
    "index.html", "404.html", "robots.txt", "sitemap.xml", "llms.txt",
    "favicon.ico", "favicon.svg", "favicon-192.png", "apple-touch-icon.png", "vorschau.png",
    # Weiterleitungen früherer Adressen (meta refresh): Alte Links und
    # Suchmaschineneinträge sollen weiter ankommen.
    "danke.html", "datenschutz.html", "fachartikel.html", "impressum.html", "kontakt.html",
    "leistungen.html", "projekte.html", "referenzen.html",
    # Für GitHub Pages: eigene Domain, kein Jekyll. Schaden nicht und werden
    # gebraucht, falls die Website später aus einem eigenen Repository kommt.
    "CNAME", ".nojekyll",
}

# Prüf- und Schlüsseldateien von Suchmaschinen und Diensten (Muster für den Namen).
MUSTER = (
    re.compile(r"^google[0-9a-f]+\.html$"),     # Google Search Console
    re.compile(r"^BingSiteAuth\.xml$"),         # Bing Webmaster Tools
    re.compile(r"^ahrefs_[0-9a-f]+$"),          # Ahrefs
    re.compile(r"^[0-9a-f]{32}\.txt$"),         # IndexNow-Schlüssel (tools/indexnow.py)
)

# Ordner der Website und die Dateiarten, die daraus ausgeliefert werden.
ORDNER = {
    "fachwissen": {".html", ".css"},
    "leistungen": {".html"},
    "en": {".html"},
    "werkzeuge": {".html", ".js"},
    "wertrechner": {".html", ".css", ".js", ".json"},
    "fonts": {".woff2"},
    # Nur die Downloads; die .yml-Quellen der Vorlagen bleiben intern.
    "vorlagen": {".pdf", ".docx", ".xlsx"},
}

# Bewusst intern: gehört nicht zur Website und wird nie ausgeliefert.
INTERN = {
    ".claude", ".github", ".gitignore",      # Agenten und Workflows
    "tools", "tests",                        # Werkzeuge und Tests
    "entwuerfe", "entwuerfe-en",             # Quelltexte der Beiträge (gebaut nach fachwissen/ und en/guides/)
    "marketing", "fachliteratur", "daten",   # Unterlagen, Literatur, Rohdaten
}


def _git() -> str | None:
    gefunden = shutil.which("git")
    if gefunden:
        return gefunden
    for kandidat in (r"C:\Program Files\Git\cmd\git.exe", "/usr/bin/git"):
        if Path(kandidat).is_file():
            return kandidat
    return None


def _ignoriert(pfad: str, regeln: list[str]) -> bool:
    """Einfache Auswertung der .gitignore für den Fall ohne git."""
    teile = pfad.split("/")
    for regel in regeln:
        if regel.endswith("/") and regel.rstrip("/") in teile[:-1]:
            return True
        if "/" in regel.rstrip("/") and pfad == regel:
            return True
        if fnmatch.fnmatch(teile[-1], regel):
            return True
    return False


def repo_dateien() -> list[str]:
    """Alle versionierten Dateien. Nicht versionierte (lokale Zwischenstände,
    Caches, Rohdaten) kommen so nie auf die Website."""
    git = _git()
    if git:
        try:
            aus = subprocess.run([git, "ls-files", "-z"], cwd=WURZEL, capture_output=True, check=True)
            return sorted(p for p in aus.stdout.decode("utf-8").split("\0") if p)
        except (OSError, subprocess.CalledProcessError):
            pass
    datei = WURZEL / ".gitignore"
    regeln = [z.strip() for z in datei.read_text(encoding="utf-8").splitlines()
              if z.strip() and not z.startswith("#")] if datei.is_file() else []
    return sorted(p for p in (q.relative_to(WURZEL).as_posix() for q in WURZEL.rglob("*") if q.is_file())
                  if not p.startswith(".git/") and not _ignoriert(p, regeln))


def zur_website(pfad: str) -> bool:
    teile = pfad.split("/")
    if len(teile) == 1:
        return pfad in DATEIEN or any(m.match(pfad) for m in MUSTER)
    endungen = ORDNER.get(teile[0])
    return bool(endungen) and PurePosixPath(pfad).suffix.lower() in endungen


def nicht_zugeordnet(dateien: list[str]) -> list[str]:
    """Einträge der obersten Ebene, die weder freigegeben noch als intern geführt sind."""
    offen = set()
    for pfad in dateien:
        oben = pfad.split("/", 1)[0]
        if "/" in pfad:
            if oben not in ORDNER and oben not in INTERN:
                offen.add(oben + "/")
        elif not zur_website(pfad) and pfad not in INTERN:
            offen.add(pfad)
    return sorted(offen)


def auswahl(dateien: list[str] | None = None) -> list[str]:
    return [p for p in (repo_dateien() if dateien is None else dateien) if zur_website(p)]


def bauen(ziel: Path) -> list[str]:
    """Kopiert die freigegebenen Dateien nach ziel und gibt ihre Pfade zurück."""
    if ziel.exists() and any(ziel.iterdir()):
        raise SystemExit(f"FEHLER: {ziel} ist nicht leer – bitte ein neues Verzeichnis angeben.")
    dateien = auswahl()
    for pfad in dateien:
        quelle = WURZEL / pfad
        ausgabe = ziel / pfad
        ausgabe.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ausgabe)
    return dateien


def main() -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    modus = zerleger.add_mutually_exclusive_group(required=True)
    modus.add_argument("--ziel", type=Path, help="Verzeichnis, in das die Website gebaut wird")
    modus.add_argument("--liste", action="store_true", help="ausgelieferte Dateien auflisten")
    argumente = zerleger.parse_args()

    offen = nicht_zugeordnet(repo_dateien())
    for eintrag in offen:
        # Nicht freigegeben heißt: nicht ausgeliefert. Der Hinweis erinnert daran,
        # den Eintrag einer der Listen zuzuordnen (der Test schlägt sonst fehl).
        print(f"HINWEIS: {eintrag} ist keiner Liste zugeordnet und wird nicht ausgeliefert.")

    if argumente.liste:
        for pfad in auswahl():
            print(pfad)
        return 0

    dateien = bauen(argumente.ziel)
    groesse = sum((argumente.ziel / p).stat().st_size for p in dateien)
    print(f"Website gebaut: {len(dateien)} Dateien, {groesse / 1_000_000:.1f} MB in {argumente.ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
