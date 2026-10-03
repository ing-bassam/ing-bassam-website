#!/usr/bin/env python3
"""Was es schon gibt: der aktuelle Bestand für die Doppelungsprüfung.

Gelesen wird zum Zeitpunkt des Aufrufs – nicht der Stand, den der Workflow
bei Laufbeginn ausgecheckt hat:

    hauptzweig     origin/main nach einem neuen „git fetch“: alle Beiträge und
                   Entwürfe unter entwuerfe/ (Fachartikel, Urteile, Begleitseiten
                   der Vorlagen)
    pull_requests  Entwürfe aus offenen und aus in den letzten 14 Tagen
                   zusammengeführten Pull Requests (GitHub-CLI, GH_TOKEN)
    notion         die drei Notion-Listen Themenspeicher, Vorlagen und
                   Trendthemen (NOTION_TOKEN)

Anlass: Am 02.10.2026 entstanden zwei Besprechungen desselben Urteils (OLG
Stuttgart 10 U 308/20). Der zweite Lauf kannte nur den Stand bei seinem
Beginn und die offenen Pull Requests; der erste Entwurf war in der
Zwischenzeit zusammengeführt worden und damit für ihn unsichtbar.

Fällt eine Quelle aus, gibt es eine Warnung, und die übrigen zählen. Die
Agenten prüfen zusätzlich selbst (Skill-Regel „DUPLIKAT“).

Aufruf zur Kontrolle:
    python tools/bestand.py                  Zahl der Einträge je Quelle
    python tools/bestand.py --json DATEI     Bestand als JSON speichern
    python tools/bestand.py --ohne-notion    nur Repository und Pull Requests

Titel aus Notion erscheinen nie in der Ausgabe: Das Protokoll ist öffentlich,
die Themenliste ist der Redaktionsplan. Benötigt nur die Standardbibliothek,
git und die GitHub-CLI.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eigener_entwurf import kopf  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
BASIS_URL = "https://ing-bassam.de"
REF = "refs/bestand/main"           # eigener Verweis, damit origin/main unberührt bleibt
TAGE_ZUSAMMENGEFUEHRT = 14

# Notion-Listen: Datenquelle, Titel-Eigenschaft, Eigenschaft mit der Leserfrage
NOTION_LISTEN = {
    "themenspeicher": ("532c3c18-5d73-4312-89f6-a2a4035b981d", "Thema", "Kernfrage"),
    "vorlagen": ("b2141992-3f79-4905-a9ee-785d876ad95e", "Vorlage", "Zweck"),
    "trendthemen": ("a744bdd5-1831-423c-8bb4-3c354fdaf149", "Thema", "Kernfrage"),
}

URTEILS_FORMATE = {"rechtsprechung", "urteil verständlich", "urteilsbesprechung"}


def art_von(format_: str) -> str:
    """beitrag, vorlage oder urteil – die drei Arten, die sich gegenseitig vertreten können."""
    f = (format_ or "").strip().lower()
    if f in URTEILS_FORMATE:
        return "urteil"
    if f == "vorlage":
        return "vorlage"
    return "beitrag"


def normiere_id(wert: str) -> str:
    return re.sub(r"[^0-9a-f]", "", (wert or "").lower())


def sprache_von(wert: str) -> str:
    """Sprachkürzel aus Dateikopf (`sprache: en`) oder Notion-Auswahl („Englisch“); leer = Deutsch."""
    w = (wert or "").strip().lower()
    return "en" if w in ("en", "englisch", "english") else "de"


def eintrag_aus_entwurf(text: str, pfad: str, quelle: str, pr: dict | None = None) -> dict | None:
    """Ein Beitrag aus seiner Markdown-Datei (nur die Felder des Kopfs)."""
    k = kopf(text)
    titel = k.get("titel", "")
    if not titel:
        return None
    kurzform = k.get("kurzform") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", Path(pfad).stem)
    status = k.get("status", "")
    veroeffentlicht = status.lower() == "veröffentlicht" or "/veroeffentlicht/" in pfad
    return {
        "quelle": quelle,
        "art": art_von(k.get("format", "")),
        "format": k.get("format", ""),
        "fassung": k.get("fassung", ""),
        "titel": titel,
        "kernfrage": k.get("kernfrage", ""),
        "schlagwoerter": k.get("schlagwoerter", ""),
        "kurzform": kurzform,
        "aktenzeichen": k.get("aktenzeichen", ""),
        "ecli": k.get("ecli", ""),
        "gericht": k.get("gericht", ""),
        "notion_id": normiere_id(k.get("notion_id", "")),
        "status": "veröffentlicht" if veroeffentlicht else "entwurf",
        "sprache": sprache_von(k.get("sprache", "")),
        "erstellt": k.get("erstellt", ""),
        "pfad": pfad,
        "pr": (pr or {}).get("number"),
        "pr_url": (pr or {}).get("url", ""),
        "pr_offen": bool(pr) and pr.get("state", "OPEN") == "OPEN",
        "link": f"{BASIS_URL}/fachwissen/{kurzform}/" if veroeffentlicht else "",
        "oeffentlich": True,
    }


# --------------------------------------------------------------------------
# Hauptzweig
# --------------------------------------------------------------------------

def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=WURZEL, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:300] or f"git {args[0]} fehlgeschlagen")
    return r.stdout


def texte_am_stand(ref: str) -> list[tuple[str, str]]:
    """(Pfad, Inhalt) aller Beiträge unter entwuerfe/ in einem bestimmten Stand (Commit oder Verweis)."""
    pfade = [p for p in _git("ls-tree", "-r", "--name-only", ref, "--", "entwuerfe").splitlines()
             if p.endswith(".md") and not p.lower().endswith("readme.md")]
    if not pfade:
        return []
    roh = subprocess.run(["git", "cat-file", "--batch"], cwd=WURZEL, capture_output=True, timeout=180,
                         input="".join(f"{ref}:{p}\n" for p in pfade).encode("utf-8"))
    if roh.returncode:
        raise RuntimeError(roh.stderr.decode("utf-8", "replace")[:300])
    texte, daten, stelle = [], roh.stdout, 0
    for pfad in pfade:
        zeilenende = daten.index(b"\n", stelle)
        kopfzeile = daten[stelle:zeilenende].decode("utf-8", "replace").split()
        stelle = zeilenende + 1
        if len(kopfzeile) < 3 or kopfzeile[1] == "missing":
            continue
        groesse = int(kopfzeile[2])
        texte.append((pfad, daten[stelle:stelle + groesse].decode("utf-8", "replace")))
        stelle += groesse + 1
    return texte


def hauptzweig_texte(warnungen: list[str]) -> list[tuple[str, str]]:
    """(Pfad, Inhalt) aller Beiträge auf dem neuesten Stand von main.

    Ohne Netz oder ohne git: der ausgecheckte Stand, mit Warnung.
    """
    try:
        flache_kopie = _git("rev-parse", "--is-shallow-repository").strip() == "true"
        # --depth nur in einer flachen Kopie: In einer vollständigen würde es sie flach machen.
        tiefe = ["--depth=1"] if flache_kopie else []
        _git("fetch", "--quiet", "--no-tags", *tiefe, "origin", f"+refs/heads/main:{REF}")
        return texte_am_stand(REF)
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as fehler:
        warnungen.append(f"Neuester Stand des Hauptzweigs nicht lesbar ({str(fehler)[:160]}) – "
                         "verwendet wird der ausgecheckte Stand.")
        ordner = WURZEL / "entwuerfe"
        return [(p.relative_to(WURZEL).as_posix(), p.read_text(encoding="utf-8", errors="replace"))
                for p in sorted(ordner.rglob("*.md")) if p.name.lower() != "readme.md"] if ordner.is_dir() else []


# --------------------------------------------------------------------------
# Pull Requests
# --------------------------------------------------------------------------

def _gh(*args: str) -> str:
    fehler = ""
    for versuch in range(3):
        r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
        if r.returncode == 0:
            return r.stdout
        fehler = r.stderr.strip()
        time.sleep(2 * (versuch + 1))
    raise RuntimeError(fehler[:300])


def repo_name() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or _gh("repo", "view", "--json", "nameWithOwner",
                                                      "--jq", ".nameWithOwner").strip()


def entwurfsdateien(pr: dict) -> list[str]:
    return [f["path"] for f in pr.get("files") or []
            if f["path"].startswith("entwuerfe/") and f["path"].endswith(".md")
            and not f["path"].lower().endswith("readme.md")]


def pull_requests(tage: int = TAGE_ZUSAMMENGEFUEHRT) -> list[dict]:
    """Offene und in den letzten `tage` Tagen zusammengeführte Pull Requests mit Entwurfsdateien."""
    repo = repo_name()
    felder = "number,url,title,headRefName,files,state,isDraft,createdAt,mergedAt,mergeCommit"
    offen = json.loads(_gh("pr", "list", "--repo", repo, "--state", "open", "--limit", "100", "--json", felder))
    seit = (datetime.now(timezone.utc) - timedelta(days=tage)).strftime("%Y-%m-%d")
    zusammen = json.loads(_gh("pr", "list", "--repo", repo, "--state", "merged", "--search", f"merged:>={seit}",
                              "--limit", "100", "--json", felder))
    return [pr for pr in offen + zusammen if entwurfsdateien(pr)]


def pr_datei(repo: str, nummer: int, pfad: str) -> str:
    return _gh("api", "-H", "Accept: application/vnd.github.raw+json",
               f"repos/{repo}/contents/{urllib.parse.quote(pfad)}?ref=refs/pull/{nummer}/head")


def pr_texte(vorhandene_pfade: set[str], warnungen: list[str]) -> list[dict]:
    """Entwurfsdateien aus Pull Requests, die (noch) nicht auf dem Hauptzweig liegen.

    Offene Pull Requests liefern neue Entwürfe. Zusammengeführte zählen nur mit
    Dateien, die es auf main nicht mehr gibt (etwa eine wieder entfernte
    Doppelung) – sonst gilt der Stand von main. Verglichen wird der Dateiname:
    Nach der Veröffentlichung liegt dieselbe Datei unter veroeffentlicht/.
    Ergebnis: [{"pfad", "text", "pr"}].
    """
    vorhandene_namen = {Path(p).name for p in vorhandene_pfade}
    if not shutil.which("gh"):
        warnungen.append("GitHub-CLI fehlt – Entwürfe in Pull Requests werden nicht berücksichtigt.")
        return []
    texte = []
    try:
        repo = repo_name()
        for pr in pull_requests():
            for pfad in entwurfsdateien(pr):
                if pr.get("state") == "MERGED" and Path(pfad).name in vorhandene_namen:
                    continue
                try:
                    texte.append({"pfad": pfad, "text": pr_datei(repo, pr["number"], pfad), "pr": pr})
                except RuntimeError:
                    continue            # im Pull Request gelöscht
    except (RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
        warnungen.append(f"Pull Requests nicht lesbar ({str(fehler)[:160]}) – Entwürfe dort werden "
                         "nicht berücksichtigt.")
    return texte


def texte(warnungen: list[str], prs: bool = True) -> list[dict]:
    """Alle Beitragstexte: neuester Stand von main und Pull Requests.
    Ergebnis: [{"pfad", "text", "quelle", "pr"}] (pr nur bei Pull Requests)."""
    haupt = hauptzweig_texte(warnungen)
    liste = [{"pfad": p, "text": t, "quelle": "hauptzweig", "pr": None} for p, t in haupt]
    if prs:
        liste += [dict(t, quelle="pull_request") for t in pr_texte({p for p, _ in haupt}, warnungen)]
    return liste


# --------------------------------------------------------------------------
# Notion
# --------------------------------------------------------------------------

def notion_eintrag(seite: dict, liste: str) -> dict | None:
    from trend_notion import klartext
    _, titel_feld, frage_feld = NOTION_LISTEN[liste]
    e = seite.get("properties") or {}
    titel = " ".join(klartext(e.get(titel_feld)).split())
    if not titel:
        return None
    status = ((e.get("Status") or {}).get("select") or {}).get("name", "")
    format_ = "Vorlage" if liste == "vorlagen" else ((e.get("Format") or {}).get("select") or {}).get("name", "")
    return {
        "quelle": "notion",
        "liste": liste,
        "art": art_von(format_),
        "format": format_,
        "titel": titel,
        "kernfrage": " ".join(klartext(e.get(frage_feld)).split()),
        "notion_id": normiere_id(seite.get("id", "")),
        "notion_url": seite.get("url", ""),
        "status": status,
        "sprache": sprache_von(((e.get("Sprache") or {}).get("select") or {}).get("name", "")),
        "prioritaet": ((e.get("Priorität") or {}).get("select") or {}).get("name", ""),
        "erstellt": seite.get("created_time", ""),
        "oeffentlich": False,
    }


def notion_bestand(warnungen: list[str]) -> list[dict]:
    if not os.environ.get("NOTION_TOKEN", "").strip():
        warnungen.append("NOTION_TOKEN fehlt – die Notion-Listen werden nicht berücksichtigt.")
        return []
    from trend_notion import NotionFehler, abfragen
    eintraege = []
    for liste, (quelle, _, _) in NOTION_LISTEN.items():
        try:
            for seite in abfragen(quelle):
                e = notion_eintrag(seite, liste)
                if e:
                    eintraege.append(e)
        except NotionFehler as fehler:
            warnungen.append(f"Notion-Liste „{liste}“ nicht lesbar ({fehler}).")
    return eintraege


# --------------------------------------------------------------------------

def laden(notion: bool = True, prs: bool = True) -> dict:
    """Der gesamte Bestand: {"eintraege": [...], "warnungen": [...], "stand": ISO-Zeit}."""
    warnungen: list[str] = []
    eintraege = [e for e in (eintrag_aus_entwurf(t["text"], t["pfad"], t["quelle"], t["pr"])
                             for t in texte(warnungen, prs)) if e]
    # Ein Beitrag, den es auf main schon gibt, zählt nur einmal – mit dem Stand von main
    # (etwa ältere Pull Requests mit einem früheren Dateinamen).
    auf_main = {e["kurzform"] for e in eintraege if e["quelle"] == "hauptzweig"}
    eintraege = [e for e in eintraege if e["quelle"] == "hauptzweig" or e["kurzform"] not in auf_main]
    if notion:
        eintraege += notion_bestand(warnungen)
    return {"eintraege": eintraege, "warnungen": warnungen,
            "stand": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def speichern(bestand: dict, pfad: Path) -> None:
    pfad.write_text(json.dumps(bestand, ensure_ascii=False, indent=1), encoding="utf-8")


def lesen(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--json", type=Path, help="Bestand als JSON in diese Datei schreiben")
    p.add_argument("--ohne-notion", action="store_true")
    p.add_argument("--ohne-pr", action="store_true")
    a = p.parse_args()
    b = laden(notion=not a.ohne_notion, prs=not a.ohne_pr)
    zaehler: dict[str, int] = {}
    for e in b["eintraege"]:
        schluessel = f"{e['quelle']}/{e.get('liste') or e['status']}"
        zaehler[schluessel] = zaehler.get(schluessel, 0) + 1
    for schluessel in sorted(zaehler):
        print(f"{schluessel}: {zaehler[schluessel]}")
    for w in b["warnungen"]:
        print(f"::warning title=Bestand::{w}")
    if a.json:
        speichern(b, a.json)
        print(f"Gespeichert: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
