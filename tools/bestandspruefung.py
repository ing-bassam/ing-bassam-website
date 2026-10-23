#!/usr/bin/env python3
"""Fasst die Prüfung der veröffentlichten Beiträge zu einem Bericht zusammen – nur lokal.

Nur für den PC des Inhabers. Das Werkzeug liest die JSON-Ergebnisse von
tools/wortgleich_pruefen.py und tools/normstand_pruefen.py über
entwuerfe/veroeffentlicht/ – dieselben Werkzeuge wie vor jeder Freigabe – und
schreibt einen Bericht in eine lokale Datei. Er nennt je Stelle Beitrag, Zeile,
Werk-Kennung und Seite bzw. Regelwerk und Ausgaben, nie Text aus der Bibliothek
oder aus den Beiträgen. Werk und Seite sind hier erlaubt, weil der Bericht nie
veröffentlicht wird: kein Issue, kein Pull Request, kein Kommentar, kein Commit,
keine Ausgabe in einem Workflow. Eine öffentliche Liste wörtlicher
Übereinstimmungen veröffentlichter Beiträge wäre selbst ein Risiko; deshalb
gibt es dafür keinen Job in der Wöchentlichen Prüfung mehr, und in GitHub
Actions bricht das Werkzeug ab (Rückgabewert 2).

Aufruf (lokal, Fachbibliothek unter .bibliothek, Ergebnisse außerhalb des Repositorys):
    python tools/wortgleich_pruefen.py entwuerfe/veroeffentlicht/*.md --bibliothek .bibliothek --json <tmp>/wortgleich.json
    python tools/normstand_pruefen.py entwuerfe/veroeffentlicht/*.md --ausgaben .bibliothek/normen/ausgaben.yml --json <tmp>/normstand.json
    python tools/bestandspruefung.py --wortgleich <tmp>/wortgleich.json --normstand <tmp>/normstand.json --bericht <tmp>/bestand.md

Letzte Ausgabezeile: „befund=<n>“ (Stellen mit wörtlicher Übereinstimmung plus FEHLER der
Normstand-Prüfung) oder „befund=nicht-geprueft“, wenn ein Ergebnis fehlt oder unlesbar ist.
Rückgabewert 0 – außer in GitHub Actions (2, dann wird nichts geschrieben).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HOECHSTLAENGE = 60000        # so bleibt der Bericht überschaubar
JE_BEITRAG = 12              # so viele Fundstellen je Beitrag ausgeschrieben, der Rest gezählt
NUR_LOKAL = ("tools/bestandspruefung.py läuft nur lokal am PC des Inhabers: Der Bericht nennt Werk und Seite "
             "und wird nie veröffentlicht – in GitHub Actions ist nichts geschrieben worden.")


def lesen(pfad: Path | None) -> dict | None:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8")) if pfad else None
    except (OSError, ValueError):
        return None
    return daten if isinstance(daten, dict) and daten.get("geprueft") else None


def zelle(wert) -> str:
    return "–" if wert in (None, "") else str(wert).replace("|", "\\|")


def bericht(wortgleich: dict | None, normstand: dict | None) -> tuple[str, str]:
    """(Text des lokalen Berichts, Befund-Zeile)."""
    zeilen = ["Lokale Prüfung der veröffentlichten Beiträge (`entwuerfe/veroeffentlicht/`) ohne KI – mit denselben "
              "Werkzeugen wie vor jeder Freigabe (`tools/wortgleich_pruefen.py`, `tools/normstand_pruefen.py`). "
              "Nur für den Inhaber: Der Bericht nennt Werk und Seite und wird nie veröffentlicht (kein Issue, kein "
              "Pull Request, kein Kommentar, kein Commit). Genannt werden nur Fundstellen, nie Text.", ""]
    if wortgleich is None or normstand is None:
        fehlt = " und ".join(n for n, d in (("Wortgleich-Prüfung", wortgleich), ("Normstand-Prüfung", normstand))
                             if d is None)
        zeilen += [f"⚠️ Nicht geprüft: {fehlt} ohne Ergebnis (Fachbibliothek oder Normenindex nicht verfügbar)."]
        return "\n".join(zeilen) + "\n", "befund=nicht-geprueft"

    treffer = [t for t in wortgleich.get("treffer", []) if isinstance(t, dict)]
    fehler = [z for z in normstand.get("zeilen", []) if isinstance(z, dict) and z.get("stufe") == "FEHLER"]
    je_datei: dict[str, list[dict]] = {}
    for t in treffer:
        je_datei.setdefault(Path(str(t.get("datei", "?"))).name, []).append(t)
    zeilen += [f"**Wörtliche Übernahmen:** {len(treffer)} Stelle(n) in {len(je_datei)} Beitrag/Beiträgen "
               f"(Grenze {wortgleich.get('grenze', '?')} Wörter, {wortgleich.get('werke', '?')} Werke).", ""]
    if je_datei:
        zeilen += ["| Beitrag | Stellen | Zeile (Werk, Seite) |", "|---|---|---|"]
        for name, liste in sorted(je_datei.items(), key=lambda e: (-len(e[1]), e[0])):
            orte = [f"{t.get('zeile')} ({t.get('werk') or t.get('art')}" + (f" S. {t['seite']}" if t.get("seite") else "")
                    + ")" for t in sorted(liste, key=lambda t: t.get("zeile") or 0)[:JE_BEITRAG]]
            rest = len(liste) - JE_BEITRAG
            zeilen.append(f"| {zelle(name)} | {len(liste)} | {zelle(', '.join(orte) + (f' … und {rest} weitere' if rest > 0 else ''))} |")
        zeilen.append("")
    zeilen += [f"**Veraltete Normausgaben (FEHLER):** {len(fehler)} (Normenindex Stand "
               f"{normstand.get('stand_index', '?')}).", ""]
    if fehler:
        zeilen += ["| Beitrag | Zeile | Regelwerk | genannt | neueste |", "|---|---|---|---|---|"]
        for z in fehler:
            zeilen.append("| " + " | ".join(zelle(w) for w in (Path(str(z.get("datei", "?"))).name, z.get("zeile"),
                                                                  z.get("regelwerk"), z.get("genannt"),
                                                                  z.get("neueste"))) + " |")
        zeilen.append("")
    zeilen += ["Was zu tun ist: jede Stelle in eigene Worte fassen (Werk und Seite als Fundstelle behalten), jede "
               "Ausgabe aktualisieren oder im Satz als frühere Fassung kennzeichnen. Bis dahin kann ein Beitrag "
               "zurückgenommen werden (`status: Entwurf`). Werk und Seite aus diesem Bericht nie in Commits, "
               "Pull Requests, Kommentare oder Issues übernehmen."]
    text = "\n".join(zeilen) + "\n"
    if len(text) > HOECHSTLAENGE:
        text = text[:HOECHSTLAENGE].rsplit("\n", 1)[0] + "\n\n… gekürzt.\n"
    return text, f"befund={len(treffer) + len(fehler)}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--wortgleich", type=Path)
    p.add_argument("--normstand", type=Path)
    p.add_argument("--bericht", type=Path, required=True, help="lokale Datei für den Bericht (nie veröffentlichen)")
    a = p.parse_args()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(NUR_LOKAL)
        print("befund=nicht-geprueft")
        return 2
    text, befund = bericht(lesen(a.wortgleich), lesen(a.normstand))
    a.bericht.write_text(text, encoding="utf-8", newline="\n")
    print(befund)
    return 0


if __name__ == "__main__":
    sys.exit(main())
