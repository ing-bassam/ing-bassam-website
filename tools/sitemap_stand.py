#!/usr/bin/env python3
"""Änderungsdatum (lastmod) der von Hand gepflegten Seiten in der Sitemap.

Startseite, Leistungsseiten, englische Seiten und das Mängelanzeige-Werkzeug
haben kein Frontmatter mit Datum. Früher standen sie mit dem Datum ihres ersten
Eintrags in der Sitemap, auch nachdem ihr Text geändert worden war; die
Startseite trug das Datum des neuesten Fachbeitrags. Google und Bing werten
lastmod aber nur aus, wenn es verlässlich zum Seiteninhalt passt.

Deshalb merkt sich der Seitenbau je Seite eine Kennung des Inhalts – als
XML-Kommentar im Eintrag der Sitemap, z. B. <!-- inhalt:1:3f2a9c1b7d4e -->.
Suchmaschinen überlesen Kommentare. Weicht die Kennung beim nächsten Lauf ab,
hat sich die Seite geändert und bekommt das Datum dieses Laufs.

Eigenes Modul neben tools/artikel_generator.py, damit die Regeln ohne markdown
und PyYAML getestet werden können (tests/test_sitemap_stand.py).
"""
from __future__ import annotations

import hashlib
import html
import re
from typing import Callable

# Fassung der Berechnung. Wer fingerabdruck() ändert, erhöht diese Zahl: Die
# alten Kennungen gelten dann als unbekannt und werden nur neu eingetragen.
# Sonst bekämen alle Seiten auf einen Schlag das heutige Datum.
KENNUNG_FASSUNG = "1"
KENNUNG = re.compile(r"<!--\s*inhalt:(\d+):([0-9a-f]{12})\s*-->")


def _sichtbarer_text(abschnitt: str) -> str:
    """Text eines HTML-Abschnitts, dazu Linkziele, Bildadressen und Bildtexte."""
    abschnitt = re.sub(r"<!--.*?-->", " ", abschnitt, flags=re.S)
    abschnitt = re.sub(r"<script\b.*?</script\s*>", " ", abschnitt, flags=re.S | re.I)
    abschnitt = re.sub(r"<style\b.*?</style\s*>", " ", abschnitt, flags=re.S | re.I)

    def angaben(marke: re.Match) -> str:
        werte = re.findall(r"""\s(?:href|src|alt)\s*=\s*(?:"([^"]*)"|'([^']*)')""",
                           marke.group(0), flags=re.I)
        return " " + " ".join(doppelt or einfach for doppelt, einfach in werte) + " "

    abschnitt = re.sub(r"<[^>]*>", angaben, abschnitt)
    return " ".join(html.unescape(abschnitt).split())


def fingerabdruck(seite: str) -> str:
    """Kurze Kennung dessen, was eine Seite inhaltlich ausmacht (12 Zeichen).

    Es zählt, was Suchmaschinen als wesentliche Änderung werten: Titel,
    Beschreibung, der Text im Hauptteil (<main>) samt Linkzielen, Bildern und
    Bildtexten sowie die Strukturdaten. Kopf- und Fußzeile, Gestaltung
    (Klassen, Stylesheets), Skripte, Leerraum und Zeilenenden zählen nicht –
    sonst bekäme jede Seite ein neues Datum, sobald sich nur das Menü ändert.
    """
    titel = re.search(r"<title\b[^>]*>(.*?)</title\s*>", seite, flags=re.S | re.I)
    beschreibung = ""
    for marke in re.findall(r"<meta\b[^>]*>", seite, flags=re.I):
        if re.search(r"""\sname\s*=\s*["']description["']""", marke, flags=re.I):
            inhalt = re.search(r"""\scontent\s*=\s*(?:"([^"]*)"|'([^']*)')""", marke, flags=re.I)
            if inhalt:
                beschreibung = inhalt.group(1) or inhalt.group(2) or ""
            break
    hauptteil = (re.search(r"<main\b[^>]*>(.*)</main\s*>", seite, flags=re.S | re.I)
                 or re.search(r"<body\b[^>]*>(.*)</body\s*>", seite, flags=re.S | re.I))
    strukturdaten = re.findall(
        r"""<script\b[^>]*\stype\s*=\s*["']application/ld\+json["'][^>]*>(.*?)</script\s*>""",
        seite, flags=re.S | re.I)
    teile = [
        _sichtbarer_text(titel.group(1)) if titel else "",
        " ".join(html.unescape(beschreibung).split()),
        _sichtbarer_text(hauptteil.group(1) if hauptteil else seite),
    ] + [" ".join(block.split()) for block in strukturdaten]
    return hashlib.sha256("\n".join(teile).encode("utf-8")).hexdigest()[:12]


def daten_lesen(sitemap: str) -> dict[str, str]:
    """Adresse -> lastmod aus dem Text einer Sitemap."""
    paare = re.findall(r"<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>", sitemap, re.S)
    return {ort.strip(): stand.strip() for ort, stand in paare}


def kennungen_lesen(sitemap: str) -> dict[str, str]:
    """Adresse -> Inhaltskennung aus dem Text einer Sitemap (nur Kennungen der aktuellen Fassung)."""
    kennungen: dict[str, str] = {}
    for block in re.findall(r"<url>(.*?)</url>", sitemap, re.S):
        ort = re.search(r"<loc>(.*?)</loc>", block, re.S)
        kennung = KENNUNG.search(block)
        if ort and kennung and kennung.group(1) == KENNUNG_FASSUNG:
            kennungen[ort.group(1).strip()] = kennung.group(2)
    return kennungen


def kennzeile(kennung: str) -> str:
    """Die Zeile, mit der die Kennung im Eintrag der Sitemap steht."""
    return f"    <!-- inhalt:{KENNUNG_FASSUNG}:{kennung} -->"


def datum(datum_alt: str | None, kennung_alt: str | None, kennung: str, heute: str) -> str:
    """Änderungsdatum einer von Hand gepflegten Seite.

    Weicht die Kennung von der gespeicherten ab, hat sich der Inhalt geändert:
    Es gilt das heutige Datum. Sonst bleibt das bisherige Datum stehen. Ist noch
    keine Kennung gespeichert, wird sie nur nachgetragen – ein neues Datum wäre
    ohne Vergleich geraten.
    """
    if not datum_alt:
        return heute
    if kennung_alt and kennung_alt != kennung:
        return heute
    return datum_alt


def staende(adressen: list[str], sitemap_alt: str,
            seite_lesen: Callable[[str], str | None], heute: str) -> dict[str, tuple[str, str | None]]:
    """Je Adresse (lastmod, Kennung) für die neue Sitemap.

    sitemap_alt: Text der bisherigen Sitemap (leer, wenn es noch keine gibt).
    seite_lesen: liefert das HTML zur Adresse oder None, wenn die Seite fehlt –
    dann bleibt das bisherige Datum stehen und es wird keine Kennung eingetragen.
    """
    daten = daten_lesen(sitemap_alt)
    kennungen = kennungen_lesen(sitemap_alt)
    ergebnis: dict[str, tuple[str, str | None]] = {}
    for url in adressen:
        seite = seite_lesen(url)
        if seite is None:
            ergebnis[url] = (daten.get(url) or heute, None)
            continue
        kennung = fingerabdruck(seite)
        ergebnis[url] = (datum(daten.get(url), kennungen.get(url), kennung, heute), kennung)
    return ergebnis
