#!/usr/bin/env python3
"""Prüft die Quellen-Links aller veröffentlichten Beiträge.

Läuft wöchentlich im Workflow „Wöchentliche Prüfung“ – ohne KI, ohne
Kontingent. Anlass: Im Aufmaß-Beitrag führte die Fußnote zu BGH VII ZR 34/20
nach einiger Zeit nur noch auf die Startseite des Bundesgerichtshofs. Solche
Adressen sollen auffallen, bevor ein Leser sie bemerkt.

Aufruf:
    python tools/links_pruefen.py <bericht.md>

Schreibt einen Bericht in Markdown. Die letzte Zeile der Ausgabe ist die Zahl
der sicher defekten Adressen (0 = alles in Ordnung). Adressen, die nur den
automatischen Abruf ablehnen oder gerade nicht erreichbar sind, stehen als
„unklar“ im Bericht, zählen aber nicht: Das ist oft vorübergehend oder eine
Sperre für Programme, und ein dauerhaft offenes Issue ohne echten Fehler
würde nur stören.
"""
from __future__ import annotations

import sys
import time
import urllib.error
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quellen_laden as ql  # noqa: E402

# quellen_laden begrenzt die Abrufe für einen einzelnen Entwurf; hier werden
# alle veröffentlichten Beiträge geprüft.
ql.HOECHSTZAHL_ABRUFE = 2000

WURZEL = Path(__file__).resolve().parent.parent


def pruefen(url: str) -> tuple[str, str]:
    """Liefert Klasse (ok, defekt, unklar) und Beschreibung."""
    for versuch in range(2):
        try:
            _daten, _typ, endgueltig = ql.holen(url, grenze=200_000)
        except urllib.error.HTTPError as fehler:
            if fehler.code in (404, 410):
                return "defekt", f"Seite existiert nicht mehr (HTTP {fehler.code})"
            if fehler.code >= 500 and versuch == 0:
                time.sleep(20)
                continue
            if fehler.code == 401:
                return "unklar", ("HTTP 401 – verlangt eine Anmeldung, für Leser also "
                                  "vermutlich nicht frei zugänglich")
            if fehler.code in (403, 429):
                return "unklar", f"HTTP {fehler.code} – vermutlich nur für automatische Abrufe gesperrt"
            return "unklar", f"HTTP {fehler.code}"
        except ql.Abgelehnt as grund:
            return "unklar", f"nicht geprüft: {grund}"
        except (urllib.error.URLError, TimeoutError, OSError) as fehler:
            text = str(fehler)
            if "nicht auflösbar" in text:
                return "defekt", "Adresse existiert nicht mehr (Name nicht auflösbar)"
            if "CERTIFICATE_VERIFY_FAILED" in text:
                return "unklar", ("Sicherheitszertifikat der Seite nicht prüfbar – im Browser "
                                  "meist trotzdem erreichbar")
            if versuch == 0:
                time.sleep(20)
                continue
            return "unklar", "nicht erreichbar (Zeitüberschreitung oder Verbindungsfehler)"
        hinweis, auf_startseite = ql.umleitung(url, endgueltig)
        if auf_startseite:
            return "defekt", f"führt nur noch auf die Startseite ({endgueltig})"
        return "ok", hinweis
    return "unklar", "nicht erreichbar"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    ziel = Path(sys.argv[1])

    beitraege = []
    for pfad in sorted((WURZEL / "entwuerfe").glob("*.md")):
        kopf, _absaetze, fussnoten = ql.zerlegen(pfad.read_text(encoding="utf-8"))
        if kopf.get("status", "").strip().lower() == "veröffentlicht":
            beitraege.append((pfad, kopf, fussnoten))

    ergebnisse: dict[str, tuple[str, str]] = {}
    befunde = []
    for pfad, kopf, fussnoten in beitraege:
        funde = []
        for nummer in sorted(fussnoten):
            for _rolle, url in ql.adressen(fussnoten[nummer]):
                if url not in ergebnisse:
                    ergebnisse[url] = pruefen(url)
                    print(f"{ergebnisse[url][0]:<7} {url}")
                klasse, text = ergebnisse[url]
                if klasse != "ok":
                    funde.append((klasse, nummer, url, text))
        befunde.append((pfad, kopf, funde))

    defekt = sum(1 for *_x, funde in befunde for f in funde if f[0] == "defekt")
    unklar = sum(1 for *_x, funde in befunde for f in funde if f[0] == "unklar")

    def anzahl(n: int, einzahl: str, mehrzahl: str) -> str:
        return f"{n} {einzahl if n == 1 else mehrzahl}"

    zeilen = [
        f"## Quellen-Links der veröffentlichten Beiträge – Stand {date.today():%d.%m.%Y}",
        "",
        f"**{anzahl(defekt, 'defekte Adresse', 'defekte Adressen')}** · {unklar} unklar · "
        f"{anzahl(len(ergebnisse), 'Adresse', 'Adressen')} in "
        f"{anzahl(len(beitraege), 'veröffentlichtem Beitrag', 'veröffentlichten Beiträgen')} geprüft",
        "",
    ]
    if defekt:
        zeilen += [
            "❌ **Defekt** heißt: Die Adresse führt nicht mehr zur zitierten Quelle. "
            "So beheben Sie das: Actions → „Entwurf prüfen“ → Datei eintragen → "
            "„nur Schlussprüfung“. Die Schlussprüfung sucht die aktuelle Adresse "
            "desselben Dokuments und legt die Korrektur als Pull Request vor. "
            "Oder Sie ersetzen die Adresse in der Fußnote selbst.",
            "",
        ]
    for pfad, kopf, funde in befunde:
        if not funde:
            continue
        zeilen += [
            f"### {kopf.get('titel') or pfad.stem}",
            f"`{pfad.relative_to(WURZEL).as_posix()}` · "
            f"https://ing-bassam.de/fachwissen/{kopf.get('kurzform', '')}/",
            "",
        ]
        for klasse, nummer, url, text in funde:
            zeichen = "❌" if klasse == "defekt" else "⚠️"
            zeilen.append(f"- {zeichen} Fußnote {nummer}: {text} – {url}")
        zeilen.append("")
    if unklar:
        zeilen += [
            "⚠️ **Unklar** heißt: Die Seite hat den automatischen Abruf abgelehnt oder "
            "war gerade nicht erreichbar. Das ist oft vorübergehend oder eine Sperre "
            "für Programme; im Browser lässt es sich schnell prüfen.",
            "",
        ]
    zeilen.append("Diese Prüfung läuft jeden Montag automatisch und aktualisiert dieses "
                  "Issue. Sind alle Adressen wieder in Ordnung, wird es geschlossen.")

    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(ergebnisse)} Adressen geprüft: {defekt} defekt, {unklar} unklar.")
    print(defekt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
