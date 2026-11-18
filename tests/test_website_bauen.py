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
                     "en/index.html", "en/guides/index.html", "leistungen/seiten.css"):
            self.assertIn(pfad, self.website, pfad)

    def test_entfernte_rechner_werden_nicht_ausgeliefert(self):
        # November 2026: Wertrechner, Gewährleistungsfrist- und Taupunkt-Rechner
        # und die Übersicht „Werkzeuge“ wurden entfernt. Unter den alten Adressen
        # liegen nur noch Weiterleitungen, die erst beim Bauen entstehen.
        reste = sorted(p for p in self.website
                       if p.startswith(("wertrechner/", "en/property-valuation/", "werkzeuge/taupunkt/",
                                        "werkzeuge/gewaehrleistungsfrist/")) or p == "werkzeuge/index.html")
        self.assertEqual(reste, [])

    def test_weiterleitungen_sind_stimmig(self):
        self.assertEqual(w.weiterleitungen_pruefen(sorted(self.website)), [])
        for alt, (ziel, titel, sprache) in w.WEITERLEITUNGEN.items():
            self.assertTrue(alt.endswith("/") and not alt.startswith("/"), alt)
            self.assertTrue(ziel.startswith("/") and ziel.endswith("/"), ziel)
            self.assertIn(sprache, ("de", "en"))
            # Keine Kette: Das Ziel ist selbst keine weitergeleitete Adresse.
            self.assertNotIn(ziel.strip("/") + "/", w.WEITERLEITUNGEN, ziel)
            html = w.weiterleitung_html(ziel, titel, sprache)
            self.assertIn(f'<meta http-equiv="refresh" content="0; url={ziel}">', html)
            self.assertIn(f'<link rel="canonical" href="https://ing-bassam.de{ziel}">', html)
            self.assertNotIn("<script", html)

    def test_alte_adressen_stehen_nicht_in_sitemap_und_llms(self):
        alte = {f"https://ing-bassam.de/{alt}" for alt in w.WEITERLEITUNGEN}
        for name in ("sitemap.xml", "llms.txt"):
            text = (WURZEL / name).read_text(encoding="utf-8")
            # Ganze Adressen vergleichen: /werkzeuge/maengelanzeige/ gibt es weiterhin.
            adressen = set(re.findall(r"https://ing-bassam\.de/[^\s<>()\"']*", text))
            self.assertEqual(sorted(alte & adressen), [], name)

    def test_verweise_zeigen_auf_ausgelieferte_dateien(self):
        # Unter den Adressen aus WEITERLEITUNGEN legt der Bau eine Weiterleitung ab,
        # ein Verweis dorthin ist also nicht tot. Das betrifft Vorschauseiten von
        # Entwürfen, die vor dem Entfernen der Rechner entstanden sind: Sie tragen den
        # alten Kopf, bis der Seitenbau auf main sie neu erzeugt. Ohne diese Ausnahme
        # fiele die Freigabeprüfung („main + Entwurf“) für jeden offenen Entwurf durch.
        weitergeleitet = {f"{alt}index.html" for alt in w.WEITERLEITUNGEN}
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
                if aufgeloest is None or aufgeloest in self.website or aufgeloest in weitergeleitet:
                    continue
                # /ordner ohne Schrägstrich: GitHub Pages leitet auf /ordner/ weiter.
                if f"{aufgeloest}/index.html" in self.website or f"{aufgeloest}/index.html" in weitergeleitet:
                    continue
                fehlend.append(f"{pfad} → {ziel}")
        self.assertEqual(sorted(set(fehlend)), [])

    def test_gepflegte_seiten_nennen_keine_alten_adressen(self):
        # Streng für alles, was von Hand gepflegt wird, und für die Übersichten:
        # Startseite, Leistungsseiten, en/, 404, Fachwissen, Vorlagen, Guides.
        # Beitragsseiten sind ausgenommen (Vorschau eines Entwurfs mit altem Kopf,
        # siehe oben); ihren Inhalt prüft der nächste Test an der Quelle.
        weitergeleitet = {f"{alt}index.html" for alt in w.WEITERLEITUNGEN}
        beitrag = re.compile(r"(fachwissen|en/guides)/(?!vorlagen/)[^/]+/index\.html")
        alte, geprueft = [], 0
        for pfad in sorted(self.website):
            if not pfad.endswith(".html") or beitrag.fullmatch(pfad):
                continue
            geprueft += 1
            leser = Verweise()
            leser.feed((WURZEL / pfad).read_text(encoding="utf-8"))
            for ziel in leser.ziele:
                aufgeloest = aufloesen(pfad, ziel)
                if aufgeloest is None:
                    continue
                if aufgeloest in weitergeleitet or f"{aufgeloest}/index.html" in weitergeleitet:
                    alte.append(f"{pfad} → {ziel}")
        self.assertEqual(sorted(set(alte)), [])
        self.assertGreater(geprueft, 25)       # Schutz vor einer leeren Prüfung

    def test_quellen_nennen_keine_alten_adressen(self):
        # Entwürfe, englische Leitfäden, Vorlagen und die Bausteine des Seitenbaus
        # dürfen nicht auf entfernte Seiten verweisen. Geprüft wird die Quelle, damit
        # ein solcher Verweis bei der Freigabe des einen Entwurfs auffällt – und nicht
        # erst nach der Veröffentlichung auf main, wo er jede weitere Freigabe aufhielte.
        # Kein Treffer: /werkzeuge/maengelanzeige/ (gibt es weiterhin) und Adressen
        # anderer Websites wie https://www.beispiel.de/werkzeuge/.
        muster = re.compile("|".join(rf"/{re.escape(alt.rstrip('/'))}/?(?![\w/-])"
                                     for alt in sorted(w.WEITERLEITUNGEN, key=len, reverse=True)))
        fremd = re.compile(rf"(?:^|//)(?!(?:www\.)?{re.escape(HOST)})[\w-]+(?:\.[\w-]+)+(?:[/:?#].*)?$")

        def alte_adresse(zeile):
            for fund in muster.finditer(zeile):
                # Was unmittelbar vor dem Fund steht, zeigt, zu welcher Website die Adresse gehört.
                anfang = max(zeile.rfind(zeichen, 0, fund.start()) for zeichen in " \t\"'`()<>[]|") + 1
                if not fremd.search(zeile[anfang:fund.start()]):
                    return True
            return False

        for zeile in ("[Rechner](/werkzeuge/)", "https://ing-bassam.de/wertrechner", "../../werkzeuge/taupunkt/#frist",
                      "siehe www.ing-bassam.de/en/property-valuation/"):
            self.assertTrue(alte_adresse(zeile), zeile)
        for zeile in ("[Mängelanzeige](/werkzeuge/maengelanzeige/)", "Werkzeuge und Vorlagen",
                      "[Rechner](https://www.beispiel.de/service/werkzeuge/)", "www.beispiel.de/wertrechner"):
            self.assertFalse(alte_adresse(zeile), zeile)

        quellen = [*WURZEL.glob("entwuerfe/**/*.md"), *WURZEL.glob("entwuerfe-en/**/*.md"),
                   *WURZEL.glob("vorlagen/**/*.yml"),
                   *(WURZEL / "tools" / name for name in ("artikel_generator.py", "beitraege_en.py", "leistungen.py"))]
        self.assertGreater(len(quellen), 50)
        treffer = [f"{datei.relative_to(WURZEL).as_posix()}:{nr}: {zeile.strip()[:100]}"
                   for datei in quellen
                   for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1)
                   if alte_adresse(zeile)]
        self.assertEqual(treffer, [], "Verweis auf eine entfernte Seite – bitte streichen oder auf die neue Seite zeigen "
                                      "(Tabelle WEITERLEITUNGEN in tools/website_bauen.py)")

    def test_sitemap_nur_ausgelieferte_seiten(self):
        text = (WURZEL / "sitemap.xml").read_text(encoding="utf-8")
        fehlend = [url for url in re.findall(r"<loc>(.*?)</loc>", text)
                   if aufloesen("sitemap.xml", url.strip()) not in self.website]
        self.assertEqual(fehlend, [])

    def test_bauen(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "_site"
            dateien = w.bauen(ziel)
            self.assertEqual(len(dateien), len(self.website) + len(w.WEITERLEITUNGEN))
            self.assertTrue((ziel / "index.html").is_file())
            for alt, (adresse, _, _) in w.WEITERLEITUNGEN.items():
                seite = ziel / alt / "index.html"
                self.assertTrue(seite.is_file(), alt)
                self.assertIn(f"url={adresse}", seite.read_text(encoding="utf-8"))
                self.assertTrue((ziel / adresse.strip("/") / "index.html").is_file(), adresse)
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
        self.assertEqual(aufloesen("werkzeuge/maengelanzeige/app.js", "./brief.js"), "werkzeuge/maengelanzeige/brief.js")


if __name__ == "__main__":
    unittest.main()
