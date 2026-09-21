#!/usr/bin/env python3
"""Lädt den Volltext der Entscheidung, die ein vorhandener Entwurf bespricht.

Die Urteilsbesprechung legt den Volltext nur während ihres Laufs ab. Für eine
spätere Faktenprüfung desselben Entwurfs holt dieses Skript ihn anhand der
Frontmatter-Felder ``fundstelle``, ``aktenzeichen``, ``gericht`` und
``entscheidungsdatum`` erneut von der amtlichen Quelle – im selben Format wie
das Suchskript.

Aufruf:
    python tools/volltext_laden.py <entwurf.md> <zielordner>

Ausgabe: der Pfad der Volltextdatei in der letzten Zeile. Rückgabewert 2, wenn
der Entwurf keine Urteilsbesprechung ist oder die Quelle nicht lesbar ist.
"""
from __future__ import annotations

import sys
import urllib.parse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import urteile_finden as uf  # noqa: E402


def kopfwerte(pfad: Path) -> dict[str, str]:
    """Liest die einfachen ``schlüssel: wert``-Zeilen des Frontmatters."""
    text = pfad.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    kopf = text.split("---", 2)[1]
    werte: dict[str, str] = {}
    for zeile in kopf.splitlines():
        if ":" in zeile and not zeile.startswith(" "):
            schluessel, wert = zeile.split(":", 1)
            werte[schluessel.strip()] = wert.strip().strip('"').strip("'")
    return werte


def juris_portal(fundstelle: str) -> tuple[str, str] | None:
    """Ordnet eine Fundstelle einem juris-Landesportal zu."""
    host = urllib.parse.urlparse(fundstelle).netloc.lower()
    for basis, portal, _land, _gruppe in uf.JURIS_PORTALE:
        if urllib.parse.urlparse(basis).netloc.lower() == host:
            return basis, portal
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    entwurf, ordner = Path(sys.argv[1]), Path(sys.argv[2])
    werte = kopfwerte(entwurf)
    fundstelle = werte.get("fundstelle", "")
    aktenzeichen = werte.get("aktenzeichen", "")
    if not (fundstelle and aktenzeichen):
        print(f"FEHLER: {entwurf.name} hat kein Feld fundstelle oder aktenzeichen – "
              "keine Urteilsbesprechung.")
        return 2

    portal = juris_portal(fundstelle)
    try:
        if portal:
            doc_id = urllib.parse.parse_qs(urllib.parse.urlparse(fundstelle).query).get("d", [""])[0]
            if not doc_id:
                doc_id = fundstelle.rstrip("/").rsplit("/", 1)[-1]
            sitzung = uf.juris_sitzung(*portal)
            text = sitzung.volltext(doc_id)
            herausgeber = next(land for b, p, land, _g in uf.JURIS_PORTALE if p == portal[1])
        else:
            if fundstelle.endswith(".zip"):
                print("FEHLER: Bundes-Fundstellen als ZIP werden hier nicht unterstützt.")
                return 2
            text = uf.nur_text(uf.abrufen(fundstelle))
            herausgeber = urllib.parse.urlparse(fundstelle).netloc
    except Exception as ausnahme:  # Netzfehler sollen sichtbar enden, nicht still
        print(f"FEHLER: Volltext nicht abrufbar ({ausnahme})")
        return 2

    ecli = werte.get("ecli", "")
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"{uf.dateiname(aktenzeichen)}.txt"
    kopf = uf.volltext_kopf(werte.get("gericht", ""), werte.get("entscheidungsdatum", ""),
                            aktenzeichen, ecli, fundstelle, herausgeber, bool(portal),
                            date.today().isoformat())
    ziel.write_text(kopf + uf.umbrechen(text), encoding="utf-8", newline="\n")
    print(f"Volltext: {aktenzeichen} – {len(text.split())} Wörter")
    print(ziel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
