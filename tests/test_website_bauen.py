"""Prüft die Auslieferung der Website (tools/website_bauen.py).

- Jeder Eintrag der obersten Ebene ist zugeordnet: Website oder intern.
- Nichts Internes wird ausgeliefert (Agenten, Workflows, Werkzeuge, Tests,
  Entwürfe, Marketing, Fachliteratur, Rohdaten, Quelltexte wie .md/.py/.yml).
- Jede ausgelieferte Seite verweist nur auf ausgelieferte Dateien: Links,
  Bilder, Schriften, Stylesheets, Skripte, Module und Downloads. Fehlte eine
  Datei in der Positivliste, wäre die Seite nach der Umstellung kaputt.
- Jede Adresse der Sitemap ist eine ausgelieferte Seite.

Aufruf: python -m unittest discover -s tests
"""
from __future__ import annotations

import posixpath
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import website_bauen as w  # noqa: E402

HOST = "ing-bassam.de"
ATTRIBUTE = {"href", "src", "poster", "data", "action"}


class Verweise(HTMLParser):
    """Sammelt Verweise aus Attributen und eingebetteten Stilen einer Seite."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ziele: list[str] = []
        self._im_stil = False

    def handle_starttag(self, tag, attrs):
        werte = dict(attrs)
        for name, wert in attrs:
            if name in ATTRIBUTE and wert:
                self.ziele.append(wert)
        # Vorschaubild und Seitenadresse für Suchmaschinen und soziale Netze
        if tag == "meta" and werte.get("content", "").startswith(f"https://{HOST}/"):
            self.ziele.append(werte["content"])
        if tag == "style":
            self._im_stil = True

    def handle_endtag(self, tag):
        if tag == "style":
            self._im_stil = False

    def handle_data(self, data):
        if self._im_stil:
            self.ziele += css_verweise(data)


def css_verweise(text: str) -> list[str]:
    return [m.group(2) for m in re.finditer(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", text)]


def js_verweise(text: str) -> list[str]:
    """Statische Modul-Importe (import … from './x.js', import('./x.js'))."""
    return re.findall(r"""(?:\bfrom\s*|\bimport\s*\(?\s*)['"](\.{1,2}/[^'"]+)['"]""", text)


def aufloesen(von: str, ziel: str) -> str | None:
    """Pfad im Repository, auf den ein Verweis zeigt – None bei externen Zielen."""
    teile = urlsplit(ziel)
    if teile.scheme in ("mailto", "tel", "data", "javascript"):
        return None
    if teile.scheme in ("http", "https"):
        if teile.netloc != HOST:
            return None
        pfad = teile.path
    elif teile.scheme or ziel.startswith("//"):
        return None
    else:
        pfad = teile.path
    if pfad == "" and teile.fragment:          # reiner Sprung innerhalb der Seite
        return None
    pfad = unquote(pfad)
    if pfad.startswith("/"):
        voll = pfad.lstrip("/")
    elif not pfad:                                 # nur Abfrage, etwa "?v=2"
        voll = von
    else:
        voll = posixpath.normpath(posixpath.join(posixpath.dirname(von), pfad))
        if voll == ".":
            voll = ""
        elif pfad.endswith("/"):                   # normpath entfernt den Schrägstrich am Ende
            voll += "/"
    if voll == "" or voll.endswith("/"):
        voll += "index.html"
    return voll


class Auslieferung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.alle = w.repo_dateien()
        cls.website = set(w.auswahl(cls.alle))

    def test_jeder_eintrag_ist_zugeordnet(self):
        self.assertEqual(w.nicht_zugeordnet(self.alle), [],
                         "Neue Einträge in tools/website_bauen.py zuordnen: DATEIEN/ORDNER (Website) oder INTERN")

    def test_nichts_internes_wird_ausgeliefert(self):
        verboten = []
        for pfad in sorted(self.website):
            oben = pfad.split("/", 1)[0]
            endung = PurePosixPath(pfad).suffix.lower()
            if oben in w.INTERN or endung in {".md", ".py", ".yml", ".yaml", ".mjs", ".ttf"} \
                    or "/." in f"/{pfad}" and pfad not in {".nojekyll"}:
                verboten.append(pfad)
        self.assertEqual(verboten, [])

    def test_kernseiten_werden_ausgeliefert(self):
        for pfad in ("index.html", "404.html", "robots.txt", "sitemap.xml", "llms.txt", "CNAME",
                     "fachwissen/index.html", "fachwissen/artikel.css", "leistungen/index.html",
                     "en/index.html", "en/guides/index.html", "werkzeuge/index.html", "wertrechner/index.html"):
            self.assertIn(pfad, self.website, pfad)

    def test_verweise_zeigen_auf_ausgelieferte_dateien(self):
        fehlend = []
        for pfad in sorted(self.website):
            datei = WURZEL / pfad
            endung = datei.suffix.lower()
            if endung == ".html":
                leser = Verweise()
                leser.feed(datei.read_text(encoding="utf-8"))
                ziele = leser.ziele
            elif endung == ".css":
                ziele = css_verweise(datei.read_text(encoding="utf-8"))
            elif endung == ".js":
                ziele = js_verweise(datei.read_text(encoding="utf-8"))
            else:
                continue
            for ziel in ziele:
                aufgeloest = aufloesen(pfad, ziel)
                if aufgeloest is None or aufgeloest in self.website:
                    continue
                # /ordner ohne Schrägstrich: GitHub Pages leitet auf /ordner/ weiter.
                if f"{aufgeloest}/index.html" in self.website:
                    continue
                fehlend.append(f"{pfad} → {ziel}")
        self.assertEqual(sorted(set(fehlend)), [])

    def test_sitemap_nur_ausgelieferte_seiten(self):
        text = (WURZEL / "sitemap.xml").read_text(encoding="utf-8")
        fehlend = [url for url in re.findall(r"<loc>(.*?)</loc>", text)
                   if aufloesen("sitemap.xml", url.strip()) not in self.website]
        self.assertEqual(fehlend, [])

    def test_bauen(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "_site"
            dateien = w.bauen(ziel)
            self.assertEqual(len(dateien), len(self.website))
            self.assertTrue((ziel / "index.html").is_file())
            self.assertFalse((ziel / "tools").exists())
            self.assertFalse((ziel / ".claude").exists())
            self.assertFalse((ziel / "entwuerfe").exists())
            with self.assertRaises(SystemExit):
                w.bauen(ziel)          # nie in ein gefülltes Verzeichnis


class Aufloesen(unittest.TestCase):
    def test_regeln(self):
        self.assertEqual(aufloesen("index.html", "/"), "index.html")
        self.assertEqual(aufloesen("index.html", "/#kontakt"), "index.html")
        self.assertIsNone(aufloesen("index.html", "#kontakt"))
        self.assertEqual(aufloesen("fachwissen/x/index.html", "../../leistungen/"), "leistungen/index.html")
        self.assertEqual(aufloesen("fachwissen/x/index.html", "../artikel.css"), "fachwissen/artikel.css")
        self.assertEqual(aufloesen("index.html", "fonts/a.woff2"), "fonts/a.woff2")
        self.assertEqual(aufloesen("en/index.html", "https://ing-bassam.de/vorschau.png"), "vorschau.png")
        self.assertIsNone(aufloesen("index.html", "https://www.baukammerberlin.de/"))
        self.assertIsNone(aufloesen("index.html", "mailto:info@ing-bassam.de?subject=x"))
        self.assertEqual(aufloesen("werkzeuge/taupunkt/app.js", "./taupunkt.js"), "werkzeuge/taupunkt/taupunkt.js")


if __name__ == "__main__":
    unittest.main()
