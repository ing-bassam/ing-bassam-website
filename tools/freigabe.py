#!/usr/bin/env python3
"""Tore für den automatischen Merge eines Entwurfs (Workflow „Entwurf freigeben und veröffentlichen“).

Zwei Prüfungen ohne KI, beide fail-closed (im Zweifel: nicht mergen):

    vorpruefen  Liest das JSON von `gh pr view --json number,title,state,isDraft,author,files,labels,
                comments,mergeable,headRefOid` und prüft, ob der Pull Request überhaupt automatisch
                gemergt werden darf:
                  - offen, kein Entwurf (GitHub-Draft), Titel beginnt mit „Entwurf:“,
                  - geschrieben von einem der Schreib-Agenten (claude[bot] oder github-actions[bot]),
                  - ändert genau eine Beitragsdatei entwuerfe/entwurf/<name>.md und sonst nur deren
                    Vorschauseite unter fachwissen/<kurzform>/ – nie Werkzeuge, Workflows,
                    Anweisungen, Vorlagen oder andere Beiträge,
                  - trägt kein Label „Karim prüfen“ oder „nicht automatisch“,
                  - die Prüfungen der Schreib-Workflows sind durchgelaufen: ein Kommentar
                    „… bereit zur Freigabe“ von github-actions, und keiner der Warnkommentare
                    (Schlussprüfung nicht gelaufen oder unvollständig, Korrekturen nicht übernommen,
                    Befund bei wörtlichen Übernahmen),
                  - GitHub meldet den Pull Request als konfliktfrei mergebar.
                Ausgabe: je Grund eine Zeile „GRUND: …“; bei Erfolg „entwurf=…“, „kurzform=…“,
                „sha=…“ (für $GITHUB_OUTPUT). Rückgabewert 0 = darf weiter, 1 = bleibt für Karim.

    urteil      Liest urteil.json der Freigabeprüfung (Skill /freigabepruefung). Rückgabewert 0 nur,
                wenn die Datei genau das verlangte Format hat, alle vier Tore „bestanden“ sind und
                „freigabe“ true ist. Alles andere – fehlende Datei, kaputtes JSON, „unsicher“,
                zusätzliche oder fehlende Felder – ist 1.

    entwurf     Prüft die Beitragsdatei selbst: keine offenen Prüfpunkte („> TODO“), kein
                „zurueckhalten: ja“, Status „Entwurf“. Rückgabewert 0/1, Gründe wie oben.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AGENTEN = {"app/claude", "claude", "claude[bot]", "app/github-actions", "github-actions", "github-actions[bot]"}
SPERR_LABELS = {"karim prüfen", "nicht automatisch"}
TORE = ("urheberrecht", "fachlich", "recht", "ton")
ERGEBNISSE = {"bestanden", "nicht bestanden", "unsicher"}
BEITRAG = re.compile(r"^entwuerfe/entwurf/(?:\d{4}-\d{2}-\d{2}-)?([a-z0-9-]+)\.md$")
BEREIT = "bereit zur Freigabe"
# Warnkommentare der Schreib-Workflows (fachartikel.yml, urteil.yml, urteil-verstaendlich.yml,
# trendscout.yml): Steht einer davon im Pull Request, ist eine Prüfung nicht vollständig gelaufen.
WARNUNGEN = (
    "Schlussprüfung konnte nicht laufen",
    "nicht vollständig durchgelaufen",
    "Korrekturen der Schlussprüfung sind nicht übernommen",
    "Korrekturen der Faktenprüfung sind nicht übernommen",
    "Nicht zum Mergen freigegeben",
    "keine Entwurfsdatei gefunden",
    "Faktenprüfung konnte nicht laufen",
)


def _login(eintrag: dict | None) -> str:
    return ((eintrag or {}).get("login") or "").lower()


def vorpruefen(pr: dict) -> tuple[list[str], dict]:
    gruende: list[str] = []
    if pr.get("state") != "OPEN":
        gruende.append(f"Pull Request ist nicht offen ({pr.get('state')})")
    if pr.get("isDraft"):
        gruende.append("Pull Request ist noch ein Entwurf (Prüfungen nicht abgeschlossen oder Befund)")
    if not (pr.get("title") or "").startswith("Entwurf:"):
        gruende.append("Titel beginnt nicht mit „Entwurf:“ – nur Fachartikel-Entwürfe werden automatisch gemergt")
    if _login(pr.get("author")) not in AGENTEN:
        gruende.append("nicht von einem Schreib-Agenten angelegt")
    labels = {(l.get("name") or "").strip().lower() for l in pr.get("labels") or []}
    if labels & SPERR_LABELS:
        gruende.append("Label „" + ", ".join(sorted(labels & SPERR_LABELS)) + "“ gesetzt")

    pfade = [f.get("path") or "" for f in pr.get("files") or []]
    beitraege = [p for p in pfade if BEITRAG.match(p)]
    info: dict = {}
    if len(beitraege) != 1:
        gruende.append(f"ändert {len(beitraege)} Beitragsdateien statt genau einer")
    else:
        kurz = BEITRAG.match(beitraege[0]).group(1)
        info = {"entwurf": beitraege[0], "kurzform": kurz}
        fremd = [p for p in pfade if p != beitraege[0] and not p.startswith(f"fachwissen/{kurz}/")]
        if fremd:
            gruende.append("ändert weitere Dateien: " + ", ".join(sorted(fremd)[:5]))

    bot = [c for c in pr.get("comments") or [] if _login(c.get("author")) in AGENTEN]
    if not any(BEREIT in (c.get("body") or "") for c in bot):
        gruende.append("kein Freigabekommentar der Prüf-Workflows („bereit zur Freigabe“)")
    for c in bot:
        for w in WARNUNGEN:
            if w in (c.get("body") or ""):
                gruende.append(f"Warnung der Prüf-Workflows: „{w}“")
    if pr.get("mergeable") != "MERGEABLE":
        gruende.append(f"nicht konfliktfrei mergebar ({pr.get('mergeable')})")
    if not re.fullmatch(r"[0-9a-f]{40}", pr.get("headRefOid") or ""):
        gruende.append("Stand des Zweigs unbekannt")
    else:
        info["sha"] = pr["headRefOid"]
    return list(dict.fromkeys(gruende)), info


def urteil_lesen(pfad: Path) -> tuple[bool, list[str]]:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as fehler:
        return False, [f"Urteil der Freigabeprüfung nicht lesbar ({type(fehler).__name__})"]
    if not isinstance(daten, dict) or set(daten) != set(TORE) | {"freigabe"}:
        return False, ["Urteil der Freigabeprüfung hat nicht das verlangte Format"]
    gruende = []
    for tor in TORE:
        teil = daten[tor]
        if not isinstance(teil, dict) or teil.get("ergebnis") not in ERGEBNISSE:
            return False, [f"Urteil der Freigabeprüfung: Tor „{tor}“ ohne gültiges Ergebnis"]
        if teil["ergebnis"] != "bestanden":
            gruende.append(f"{tor}: {teil['ergebnis']}")
    if daten["freigabe"] is not True:
        gruende.append("Freigabeprüfung gibt nicht frei")
    return not gruende, gruende


def entwurf_pruefen(pfad: Path) -> list[str]:
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return ["Beitragsdatei nicht lesbar"]
    kopf = re.match(r"\A---\r?\n(.*?)\r?\n---", text, re.S)
    if not kopf:
        return ["Beitragsdatei ohne Dateikopf"]
    gruende = []
    if re.search(r"(?m)^>\s*TODO", text):
        gruende.append("offene Prüfpunkte (TODO) im Beitrag")
    if re.search(r"(?mi)^zurueckhalten:\s*[\"']?ja", kopf.group(1)):
        gruende.append("„zurueckhalten: ja“ im Dateikopf")
    status = re.search(r"(?m)^status:\s*[\"']?([^\"'\r\n]*)", kopf.group(1))
    if not status or status.group(1).strip().lower() != "entwurf":
        gruende.append("Status ist nicht „Entwurf“")
    return gruende


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    unter = p.add_subparsers(dest="befehl", required=True)
    a = unter.add_parser("vorpruefen")
    a.add_argument("pr_json", type=Path)
    b = unter.add_parser("urteil")
    b.add_argument("urteil_json", type=Path)
    c = unter.add_parser("entwurf")
    c.add_argument("datei", type=Path)
    args = p.parse_args()

    if args.befehl == "vorpruefen":
        try:
            pr = json.loads(args.pr_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print("GRUND: Angaben zum Pull Request nicht lesbar")
            return 1
        gruende, info = vorpruefen(pr)
        for g in gruende:
            print(f"GRUND: {g}")
        if gruende:
            return 1
        for k, v in info.items():
            print(f"{k}={v}")
        return 0
    if args.befehl == "urteil":
        ok, gruende = urteil_lesen(args.urteil_json)
        for g in gruende:
            print(f"GRUND: {g}")
        return 0 if ok else 1
    gruende = entwurf_pruefen(args.datei)
    for g in gruende:
        print(f"GRUND: {g}")
    return 1 if gruende else 0


if __name__ == "__main__":
    sys.exit(main())
