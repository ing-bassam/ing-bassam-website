#!/usr/bin/env python3
"""Wochenbericht der Agenten als GitHub-Issue (GitHub schickt dazu eine E-Mail).

Läuft montags im Workflow „Wöchentliche Prüfung“, ohne KI. Der Bericht zeigt:

    - was zur Freigabe bereitliegt (Pull Requests, Prüfungen fertig)
    - was noch geprüft wird (Pull Requests im Entwurfsstatus)
    - was in den letzten sieben Tagen online ging
    - welche Entwürfe zurückgehalten werden, und warum (tools/veroeffentlichen.py)
    - wie viele Themen als Doppelung übersprungen wurden
    - wie die Agentenläufe ausgingen, und ob das Kontingent pausiert

Das Repository ist öffentlich, also auch dieses Issue: Es nennt nur, was
ohnehin öffentlich ist (Pull Requests, Beiträge, Läufe) – keine Titel aus
Notion, also keine geplanten Themen. Der vorige Wochenbericht wird
geschlossen, damit nur der aktuelle offen ist.

Aufruf:
    python tools/wochenbericht.py --veroeffentlichen DATEI [--probelauf]
      DATEI: JSON aus „veroeffentlichen.py --automatisch --probelauf --bericht DATEI“
      --probelauf: Bericht nur ausgeben, kein Issue
Benötigt die GitHub-CLI (GH_TOKEN: issues write, pull-requests read,
actions read), git und – für die Doppelungen – NOTION_TOKEN.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bestand  # noqa: E402
import kontingent  # noqa: E402

LABEL = "wochenbericht"
AGENTEN = ("Fachartikel-Entwurf", "Vorlagen und Checklisten", "Urteilsbesprechung", "Urteil verständlich", "Trend-Agent",
           "Entwürfe veröffentlichen")
ZEITPLAN = ("Mo 00:37 Fachartikel (2) · Di 00:37 Vorlagen (2) und Urteil verständlich (1) · Mi 00:37 "
            "Urteilsbesprechung (1) · Mi 04:17 Trend-Agent (1) · Do 00:37 Fachartikel (2) · Mo–Fr 07:43 "
            "freigegebene Entwürfe online (höchstens 2 je Tag), danach der Stichwortzettel in Notion · "
            "Fr 08:07 dieser Bericht · Samstag und Sonntag: Zeit für Ihre Videos")


def gh_json(*args: str):
    return json.loads(kontingent.gh(*args) or "null")


def datum(utc: datetime) -> str:
    return f"{kontingent.berlin(utc):%d.%m.}"


def pull_requests(repo: str) -> tuple[list[dict], list[dict]]:
    """Offene Pull Requests der Agenten: (bereit zur Freigabe, noch in Prüfung)."""
    prs = gh_json("pr", "list", "--repo", repo, "--state", "open", "--limit", "100",
                  "--json", "number,title,url,isDraft,createdAt,headRefName")
    agenten = [p for p in prs if kontingent.AGENTEN_ZWEIGE.match(p.get("headRefName", ""))]
    return [p for p in agenten if not p.get("isDraft")], [p for p in agenten if p.get("isDraft")]


def online_gegangen(seit: datetime) -> list[tuple[str, str]]:
    """(Titel, Adresse) der Beiträge, die seit `seit` online gingen: veröffentlicht im
    ausgecheckten Stand, aber nicht im letzten Stand vor `seit` (braucht die Historie,
    im Workflow fetch-depth: 0)."""
    vorher = subprocess.run(["git", "rev-list", "-1", f"--before={seit.isoformat()}", "HEAD"],
                            cwd=bestand.WURZEL, capture_output=True, text=True).stdout.strip()
    if not vorher:
        raise RuntimeError("kein Stand vor Wochenbeginn in der Historie")
    damals = {e["kurzform"] for e in (bestand.eintrag_aus_entwurf(t, p, "hauptzweig")
                                      for p, t in bestand.texte_am_stand(vorher)) if e and e["status"] == "veröffentlicht"}
    jetzt = [e for e in (bestand.eintrag_aus_entwurf(t, p, "hauptzweig") for p, t in bestand.texte_am_stand("HEAD"))
             if e and e["status"] == "veröffentlicht" and e["kurzform"] not in damals]
    return [(e["titel"], e["link"]) for e in sorted(jetzt, key=lambda e: e["kurzform"])]


def doppelungen_seit(seit: datetime) -> list[str]:
    """Adressen (ohne Titel) der Notion-Seiten, die seit `seit` als Doppelung markiert wurden."""
    if not os.environ.get("NOTION_TOKEN", "").strip():
        return []
    from trend_notion import abfragen
    filter_ = {"and": [{"property": "Status", "select": {"equals": "Doppelung"}},
                       {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": kontingent.iso(seit)}}]}
    adressen = []
    for quelle, _, _ in bestand.NOTION_LISTEN.values():
        for seite in abfragen(quelle, filter_):
            adressen.append("https://www.notion.so/" + bestand.normiere_id(seite.get("id", "")))
    return adressen


def stichwortzettel_seit(seit: datetime) -> list[tuple[str, str, str]]:
    """(Titel, Notion-Adresse, Beitragsadresse) der Stichwortzettel, die seit `seit` entstanden sind."""
    if not os.environ.get("NOTION_TOKEN", "").strip():
        return []
    from trend_notion import STICHWORTZETTEL, abfragen, klartext
    filter_ = {"timestamp": "created_time", "created_time": {"on_or_after": kontingent.iso(seit)}}
    ergebnis = []
    for seite in abfragen(STICHWORTZETTEL, filter_):
        e = seite.get("properties") or {}
        ergebnis.append((klartext(e.get("Beitrag")), seite.get("url", ""), (e.get("Link") or {}).get("url") or ""))
    return ergebnis


def laeufe(repo: str, seit: datetime) -> dict[str, dict]:
    """Je Agent: Zahl der Läufe nach Ausgang, und Adressen der fehlgeschlagenen."""
    runs = gh_json("run", "list", "--repo", repo, "--limit", "300", "--created", f">={seit:%Y-%m-%d}",
                   "--json", "workflowName,conclusion,status,createdAt,url,event")
    tabelle: dict[str, dict] = {}
    for run in runs:
        name = run.get("workflowName", "")
        if name not in AGENTEN:
            continue
        zeile = tabelle.setdefault(name, {"success": 0, "failure": 0, "andere": 0, "fehler": []})
        ausgang = run.get("conclusion") or run.get("status") or ""
        if ausgang in ("success", "failure"):
            zeile[ausgang] += 1
        else:
            zeile["andere"] += 1
        if ausgang == "failure":
            erstellt = kontingent.iso_lesen(run.get("createdAt", "")) or seit
            zeile["fehler"].append(f"[{name}, {datum(erstellt)} {kontingent.berlin(erstellt):%H:%M}]({run['url']})")
    return tabelle


def bericht_bauen(*, jetzt: datetime, bereit: list[dict], in_pruefung: list[dict], online: list[tuple[str, str]],
                  veroeffentlichen: dict, doppelt: list[str], tabelle: dict[str, dict], neue: int | None,
                  pause: list[dict], zettel: list[tuple[str, str, str]] = ()) -> tuple[str, str]:
    seit = jetzt - timedelta(days=7)
    titel = f"Wochenbericht der Agenten {datum(seit)}–{datum(jetzt - timedelta(days=1))}{kontingent.berlin(jetzt):%Y}"
    zurueck = [e for e in veroeffentlichen.get("eintraege", []) if e.get("ergebnis") == "zurückgehalten"]
    wartend = sum(1 for e in veroeffentlichen.get("eintraege", []) if e.get("ergebnis") in ("wartet", "veröffentlicht"))
    fehlgeschlagen = sum(z["failure"] for z in tabelle.values())
    fazit = (f"**Fazit der Woche:** {len(online)} Beitrag/Beiträge online gegangen, {len(bereit)} warten auf Ihre "
             f"Freigabe, {len(zettel)} Stichwortzettel für das Wochenende, {fehlgeschlagen} fehlgeschlagene(r) Lauf/Läufe.")
    z = [f"# {titel}", "", fazit, "", "## Auf einen Blick", ""]
    z.append(f"- **Bitte lesen und freigeben:** {len(bereit)} Entwurf/Entwürfe" if bereit
             else "- **Bitte lesen und freigeben:** nichts")
    z.append(f"- **Noch in Prüfung:** {len(in_pruefung)}")
    z.append(f"- **Online gegangen:** {len(online)}")
    z.append(f"- **Freigegeben, geht in den nächsten Tagen online:** {wartend}")
    z.append(f"- **Zurückgehalten:** {len(zurueck)}")
    z.append(f"- **Als Doppelung übersprungen:** {len(doppelt)} Thema/Themen")
    if neue is not None:
        z.append(f"- **Kontingent:** {neue} von {kontingent.WOCHENGRENZE} Entwürfen seit "
                 f"{kontingent.berlin_text(kontingent.wochenbeginn(jetzt))}")
    if pause:
        z.append(f"- **Pause:** Die Agenten pausieren bis {kontingent.berlin_text(pause[0]['bis'])} "
                 f"(#{pause[0]['number']}).")
    z.append(f"- **Fehlgeschlagene Läufe:** {fehlgeschlagen}")

    if bereit:
        z += ["", "## Bereit zur Freigabe", "",
              "Fakten- und Schlussprüfung sind fertig. Bitte lesen und auf „Merge“ klicken – oder schließen, wenn "
              "der Beitrag nicht erscheinen soll.", ""]
        for p in sorted(bereit, key=lambda p: p["createdAt"]):
            erstellt = kontingent.iso_lesen(p["createdAt"]) or jetzt
            z.append(f"- [#{p['number']} {p['title']}]({p['url']}) – seit {datum(erstellt)}")
    if in_pruefung:
        z += ["", "## Noch in Prüfung", "",
              "Diese Pull Requests sind als Entwurf markiert, bis die Prüfungen fertig sind. Bitte noch nicht "
              "zusammenführen.", ""]
        z += [f"- [#{p['number']} {p['title']}]({p['url']})" for p in in_pruefung]
    if online:
        z += ["", "## Online gegangen", ""]
        z += [f"- [{t}]({link})" for t, link in online]
    if zettel:
        z += ["", "## Stichwortzettel für Ihre Videos", "",
              "Je Beitrag die drei stärksten Kernaussagen mit Fußnote – in Notion, Liste „Stichwortzettel Videos“. "
              "Das Häkchen „Video erstellt“ setzen Sie dort selbst.", ""]
        z += [f"- [{t}]({n}) – [Beitrag]({l})" for t, n, l in zettel]
    if zurueck:
        z += ["", "## Zurückgehalten", "",
              "Diese Entwürfe sind freigegeben, gehen aber nicht automatisch online:", ""]
        for e in zurueck:
            z.append(f"- `{e['kurzform']}`: " + "; ".join(e.get("gruende", [])))
    if veroeffentlichen.get("hinweis"):
        z += ["", f"_Hinweis zur Veröffentlichung: {veroeffentlichen['hinweis']}_"]
    if doppelt:
        z += ["", "## Als Doppelung übersprungen", "",
              "Diese Notion-Themen deckt schon ein vorhandener Beitrag ab. Sie stehen in Notion auf „Doppelung“, "
              "mit einem Hinweis auf den Beitrag. Soll es doch einen eigenen Beitrag geben: Status zurück auf "
              "„Idee“ und die Abgrenzung notieren. (Die Titel stehen bewusst nicht hier – das Repository ist "
              "öffentlich.)", ""]
        z += [f"- [Notion-Seite {i}]({a})" for i, a in enumerate(doppelt, 1)]
    if tabelle:
        z += ["", "## Agentenläufe", "", "| Agent | erfolgreich | fehlgeschlagen | sonstige |", "|---|---|---|---|"]
        for name in AGENTEN:
            if name in tabelle:
                t = tabelle[name]
                z.append(f"| {name} | {t['success']} | {t['failure']} | {t['andere']} |")
        fehler = [f for t in tabelle.values() for f in t["fehler"]]
        if fehler:
            z += ["", "Fehlgeschlagen (die letzten acht): " + " · ".join(fehler[:8])]
    z += ["", "## Zeitplan", "", ZEITPLAN, "",
          "_Erstellt vom Workflow „Wöchentliche Prüfung“, ohne KI._"]
    return titel, "\n".join(z) + "\n"


def veroeffentlichen_issue(repo: str, titel: str, koerper: str) -> str:
    kontingent.gh("label", "create", LABEL, "--repo", repo, "--color", "0E8A16", "--force",
                  "--description", "Wöchentlicher Bericht der Agenten")
    alte = gh_json("issue", "list", "--repo", repo, "--label", LABEL, "--state", "open", "--json", "number")
    adresse = kontingent.gh("issue", "create", "--repo", repo, "--title", titel, "--body", koerper,
                            "--label", LABEL).strip()
    for issue in alte:
        kontingent.gh("issue", "close", str(issue["number"]), "--repo", repo, "--comment",
                      f"Abgelöst durch den neuen Wochenbericht: {adresse}")
    return adresse


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--veroeffentlichen", type=Path, help="JSON aus veroeffentlichen.py --bericht")
    p.add_argument("--probelauf", action="store_true", help="nur ausgeben, kein Issue")
    a = p.parse_args()
    jetzt = datetime.now(timezone.utc)
    seit = jetzt - timedelta(days=7)
    repo = kontingent.repo()
    warnungen = []

    def versuch(name: str, aufruf, ersatz):
        try:
            return aufruf()
        except Exception as fehler:      # ein Teil fehlt, der Bericht entsteht trotzdem
            warnungen.append(f"{name}: {str(fehler)[:160]}")
            return ersatz

    bereit, in_pruefung = versuch("Pull Requests", lambda: pull_requests(repo), ([], []))
    veroeffentlichen = {}
    if a.veroeffentlichen and a.veroeffentlichen.is_file():
        veroeffentlichen = json.loads(a.veroeffentlichen.read_text(encoding="utf-8"))
    titel, koerper = bericht_bauen(
        jetzt=jetzt, bereit=bereit, in_pruefung=in_pruefung,
        online=versuch("Veröffentlichte Beiträge", lambda: online_gegangen(seit), []),
        veroeffentlichen=veroeffentlichen,
        doppelt=versuch("Notion", lambda: doppelungen_seit(seit), []),
        tabelle=versuch("Agentenläufe", lambda: laeufe(repo, seit), {}),
        neue=versuch("Kontingent", lambda: kontingent.entwuerfe_seit(kontingent.wochenbeginn(jetzt)), None),
        pause=versuch("Pause", lambda: [i for i in kontingent.pausen() if i["bis"] and i["bis"] > jetzt], []),
        zettel=versuch("Stichwortzettel", lambda: stichwortzettel_seit(seit), []))
    if warnungen:
        koerper += "\n_Nicht vollständig: " + "; ".join(warnungen) + "_\n"
    if re.search(r"@claude", koerper, re.I):          # löst sonst den Workflow „Claude Code“ aus
        koerper = re.sub(r"@claude", "claude", koerper, flags=re.I)
    print(koerper)
    if a.probelauf:
        return 0
    print(f"Wochenbericht: {veroeffentlichen_issue(repo, titel, koerper)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
