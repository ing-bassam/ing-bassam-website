"""Englische Fachbeiträge („Guides“) unter /en/guides/.

Warum ein eigener Ordner und ein eigenes Modul: Alle Werkzeuge des deutschen
Artikel-Betriebs (Seitenbauer, Bestandsliste, Veröffentlichen, Linkprüfung,
Trendsignale, Doppelungsprüfung) lesen entwuerfe/ vollständig ein. Ein
englischer Text dort würde als deutscher Beitrag gebaut, nach den deutschen
Regeln geprüft und als Dublette seines Originals gemeldet. Die englischen
Entwürfe liegen deshalb in entwuerfe-en/.

Jeder Leitfaden ist die englische Fassung eines veröffentlichten deutschen
Beitrags (Frontmatter-Feld ``original`` = dessen Kurzform). Er übernimmt dessen
Fakten und Quellen; eine neue fachliche Aussage gehört zuerst in den deutschen
Beitrag. Beide Fassungen verweisen per hreflang aufeinander.

Gebaut wird von tools/artikel_generator.py: Er lädt die Leitfäden mit laden(),
verknüpft sie mit den deutschen Beiträgen und schreibt Seiten, Übersicht,
Sitemap und llms.txt. Dieses Modul erzeugt nur Text. laden() und pruefen()
brauchen nur PyYAML; markdown wird erst beim Umwandeln geladen, damit die Tests
(tests/test_leitfaeden_en.py) ohne auskommen.

Frontmatter eines Leitfadens:

    titel              höchstens 60 Zeichen (Google kürzt längere Titel)
    kurzform           englische Adresse, z. B. mould-in-flats-defect-or-ventilation
    original           Kurzform des deutschen Beitrags
    meta_beschreibung  70 bis 160 Zeichen
    schlagwoerter      Liste
    leistung           englische Leistungsseite aus tools/leistungen.py (ENGLISCH),
                       z. B. en/mould-survey-berlin/
    autor              M. Sc. Karim Abu Elkheir
    erstellt           Datum JJJJ-MM-TT; aktualisiert optional
    status             Veröffentlicht oder Entwurf

Text: Markdown wie bei den deutschen Beiträgen – eine H1, Abschnitte mit H2,
„## Frequently asked questions“ (Frage fett in einem eigenen Absatz, Antwort im
nächsten), „## Note“, Trennlinie, „**About the author**“ und die Fußnoten mit
den Quellen des Originals.
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leistungen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
ORDNER = WURZEL / "entwuerfe-en"
PFAD = "en/guides/"
ZIEL = WURZEL / "en" / "guides"
BASIS_URL = "https://ing-bassam.de"
UEBERSICHT_URL = f"{BASIS_URL}/{PFAD}"
VORSCHAUBILD = BASIS_URL + "/vorschau.png"
FIRMA = "Bassam Ingenieurbüro für Bauwesen GmbH"
FIRMA_ID = BASIS_URL + "/#organization"
AUTOR_VORGABE = "M. Sc. Karim Abu Elkheir"
STATUS_OEFFENTLICH = "veröffentlicht"
FAQ_UEBERSCHRIFT = "Frequently asked questions"

TITEL_HOECHSTENS = 60
BESCHREIBUNG_GRENZEN = (70, 160)
FAQ_MINDEST = 3

MONATE = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def text(wert) -> str:
    if wert is None:
        return ""
    if isinstance(wert, date):
        return wert.isoformat()[:10]
    return str(wert).strip()


def liste(wert) -> list[str]:
    if wert is None:
        return []
    if isinstance(wert, list):
        return [text(w) for w in wert if text(w)]
    return [teil.strip() for teil in str(wert).split(",") if teil.strip()]


def datum(wert) -> str:
    roh = text(wert)
    return roh if re.fullmatch(r"\d{4}-\d{2}-\d{2}", roh) else ""


def datum_en(iso: str) -> str:
    jahr, monat, tag = iso.split("-")
    return f"{int(tag)} {MONATE[int(monat) - 1]} {jahr}"


def slug(roh: str) -> str:
    ersatz = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
    roh = "".join(ersatz.get(z, z) for z in roh)
    roh = unicodedata.normalize("NFKD", roh).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", roh).strip("-")


def autor_aufteilen(autor: str) -> tuple[str, str]:
    """„M. Sc. Karim Abu Elkheir“ -> („Karim Abu Elkheir“, „M. Sc.“)."""
    treffer = re.match(
        r"^\s*(?:(?:(?:M|B)\.\s?(?:Sc|Eng|A)\.|Dipl\.-Ing\.(?:\s?\(FH\))?|Dr\.-Ing\.|Dr\.)\s+)+", autor)
    if not treffer:
        return autor.strip(), ""
    return autor[treffer.end():].strip(), treffer.group(0).strip()


def h1_abtrennen(rumpf: str) -> tuple[str, str]:
    """Die erste Zeile „# …“ ist der Titel; im Seitentext stünde sie doppelt."""
    zeilen = rumpf.strip("\n").split("\n")
    if zeilen and zeilen[0].startswith("# "):
        return zeilen[0][2:].strip(), "\n".join(zeilen[1:]).strip("\n") + "\n"
    return "", rumpf


def haupttext(rumpf: str) -> str:
    """Text bis vor „## Note“, Trennlinie oder Fußnoten – Grundlage der Lesezeit."""
    ende = re.search(r"^(## Note\b|---\s*$|\[\^[^\]]+\]:)", rumpf, flags=re.M)
    return rumpf[: ende.start()] if ende else rumpf


def json_text(daten) -> str:
    """JSON für <script type="application/ld+json">: leere Werte weg, „<“ maskiert,
    damit ein „</script>“ im Text das Element nicht beenden kann."""
    def bereinigt(wert):
        if isinstance(wert, dict):
            return {k: bereinigt(v) for k, v in wert.items() if v not in (None, "", [], {})}
        if isinstance(wert, list):
            return [bereinigt(v) for v in wert]
        return wert
    return json.dumps(bereinigt(daten), ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def markdown_zu_html(rumpf: str) -> str:
    import markdown  # erst hier: laden(), pruefen() und die Tests kommen ohne aus

    umwandler = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"slugify": lambda wert, trenner: slug(wert), "toc_depth": "2-3"}},
        output_format="html5",
    )
    inhalt = umwandler.convert(rumpf)
    inhalt = re.sub(r"<blockquote>\s*<p>(\s*TODO:)",
                    r'<blockquote class="todo"><p><strong>Open:</strong>\1', inhalt)
    inhalt = inhalt.replace("<li>[ ] ", '<li class="abhaken">')
    return inhalt.replace("<li>[x] ", '<li class="abhaken erledigt">')


def faq_aus_html(inhalt: str) -> list[tuple[str, str]]:
    """Fragen und Antworten unter „Frequently asked questions“ – für das FAQPage-Markup.

    Wie bei den deutschen Beiträgen: Frage als fett gesetzter Absatz, Antwort in
    den folgenden Absätzen bis zur nächsten Frage oder Überschrift."""
    teil = re.split(rf"<h2[^>]*>\s*{FAQ_UEBERSCHRIFT}\s*</h2>", inhalt, maxsplit=1)
    if len(teil) < 2:
        return []
    bereich = re.split(r"<h[1-6]|<hr\b", teil[1], maxsplit=1)[0]

    def blank(roh: str) -> str:
        ohne_marken = re.sub(r"<sup\b[^>]*>.*?</sup>", "", roh, flags=re.S)
        return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", ohne_marken))).strip()

    paare: list[list[str]] = []
    for absatz in re.findall(r"<p>(.*?)</p>", bereich, re.S):
        frage = re.fullmatch(r"\s*<strong>(.*?)</strong>\s*", absatz, re.S)
        if frage:
            paare.append([blank(frage.group(1)), ""])
        elif paare:
            paare[-1][1] = (paare[-1][1] + " " + blank(absatz)).strip()
    return [(f, a) for f, a in paare if f.endswith("?") and a]


def leistungsseite(pfad: str):
    return next((s for s in leistungen.ENGLISCH if s.pfad == pfad), None)


# --------------------------------------------------------------------------
# Datenmodell
# --------------------------------------------------------------------------

class Leitfaden:
    def __init__(self, pfad: Path):
        roh = pfad.read_text(encoding="utf-8").replace("\r\n", "\n")
        treffer = re.match(r"^---\n(.*?)\n---\n?(.*)$", roh, re.S)
        if not treffer:
            raise ValueError("kein YAML-Frontmatter gefunden")
        try:
            kopf = yaml.safe_load(treffer.group(1)) or {}
        except yaml.YAMLError as fehler:
            raise ValueError(f"Frontmatter ist kein gültiges YAML – {fehler}")
        if not isinstance(kopf, dict):
            raise ValueError("Frontmatter ist keine Zuordnung von Feldern")

        self.pfad = pfad
        h1, self.rumpf = h1_abtrennen(treffer.group(2))
        self.titel = text(kopf.get("titel")) or h1
        if not self.titel:
            raise ValueError("weder titel im Frontmatter noch H1 im Text")
        self.kurzform = slug(text(kopf.get("kurzform")) or pfad.stem)
        self.original = slug(text(kopf.get("original")))
        self.meta_beschreibung = " ".join(text(kopf.get("meta_beschreibung")).split())
        self.schlagwoerter = liste(kopf.get("schlagwoerter"))
        self.leistung = text(kopf.get("leistung"))
        self.autor = text(kopf.get("autor")) or AUTOR_VORGABE
        self.autor_name, self.autor_grad = autor_aufteilen(self.autor)
        self.erstellt = datum(kopf.get("erstellt"))
        if not self.erstellt:
            raise ValueError("erstellt fehlt oder ist kein Datum (JJJJ-MM-TT)")
        self.aktualisiert = datum(kopf.get("aktualisiert"))
        self.status = text(kopf.get("status")) or "Entwurf"
        self.todos = len(re.findall(r"^\s*>\s*TODO:", self.rumpf, flags=re.M))
        self.wortzahl = len(haupttext(self.rumpf).split())
        # Setzt der Seitenbauer, wenn das deutsche Original veröffentlicht ist.
        self.deutsch_url = ""
        self.deutsch_titel = ""
        self._inhalt_html: str | None = None

    @property
    def geaendert(self) -> str:
        return max(d for d in (self.erstellt, self.aktualisiert) if d)

    @property
    def freigegeben(self) -> bool:
        return self.status.strip().lower() == STATUS_OEFFENTLICH

    @property
    def oeffentlich(self) -> bool:
        """Freigegeben und ohne offenen Prüfpunkt (TODO) – wie bei den deutschen Beiträgen."""
        return self.freigegeben and not self.todos

    @property
    def adresse(self) -> str:
        return f"/{PFAD}{self.kurzform}/"

    @property
    def url(self) -> str:
        return f"{BASIS_URL}{self.adresse}"

    @property
    def lesezeit(self) -> int:
        return max(1, math.ceil(self.wortzahl / 200))

    @property
    def inhalt_html(self) -> str:
        if self._inhalt_html is None:
            self._inhalt_html = markdown_zu_html(self.rumpf)
        return self._inhalt_html

    @property
    def faq(self) -> list[tuple[str, str]]:
        return faq_aus_html(self.inhalt_html)


def entwurfsdateien() -> list[Path]:
    if not ORDNER.is_dir():
        return []
    return sorted(p for p in ORDNER.rglob("*.md") if p.name.lower() != "readme.md")


def laden() -> tuple[list[Leitfaden], list[str]]:
    """Alle Leitfäden aus entwuerfe-en/ und die Fehler, die einen Bau verhindern."""
    leitfaeden: list[Leitfaden] = []
    fehler: list[str] = []
    for pfad in entwurfsdateien():
        try:
            leitfaeden.append(Leitfaden(pfad))
        except Exception as ausnahme:  # eine kaputte Datei stoppt nicht alles
            fehler.append(f"entwuerfe-en/{pfad.name}: {ausnahme}")
    kurzformen: dict[str, str] = {}
    originale: dict[str, str] = {}
    for l in leitfaeden:
        if l.kurzform in kurzformen:
            fehler.append(f"entwuerfe-en/{l.pfad.name}: Kurzform „{l.kurzform}“ belegt schon "
                          f"{kurzformen[l.kurzform]}")
        kurzformen[l.kurzform] = l.pfad.name
        if l.original and l.original in originale:
            fehler.append(f"entwuerfe-en/{l.pfad.name}: Original „{l.original}“ hat schon eine englische "
                          f"Fassung ({originale[l.original]})")
        originale.setdefault(l.original, l.pfad.name)
        if l.freigegeben and l.todos:
            fehler.append(f"entwuerfe-en/{l.pfad.name}: Status „Veröffentlicht“, aber {l.todos} offene "
                          f"Prüfpunkte im Text. Die Seite bleibt bis dahin auf noindex.")
    return leitfaeden, fehler


def pruefen(l: Leitfaden) -> list[str]:
    """Mechanische Prüfung eines Leitfadens; der Seitenbauer meldet die Befunde,
    tests/test_leitfaeden_en.py verlangt, dass keiner offen ist."""
    befunde: list[str] = []
    if len(l.titel) > TITEL_HOECHSTENS:
        befunde.append(f"Titel hat {len(l.titel)} Zeichen, höchstens {TITEL_HOECHSTENS}")
    unten, oben = BESCHREIBUNG_GRENZEN
    if not unten <= len(l.meta_beschreibung) <= oben:
        befunde.append(f"meta_beschreibung hat {len(l.meta_beschreibung)} Zeichen, erwartet {unten}–{oben}")
    if not l.original:
        befunde.append("original (Kurzform des deutschen Beitrags) fehlt")
    if leistungsseite(l.leistung) is None:
        befunde.append(f"leistung „{l.leistung}“ ist keine englische Seite aus tools/leistungen.py")
    faq = re.split(rf"^## {FAQ_UEBERSCHRIFT}\s*$", l.rumpf, maxsplit=1, flags=re.M)
    fragen = re.findall(r"^\*\*[^*\n]+\?\*\*\s*$", faq[1], flags=re.M) if len(faq) == 2 else []
    if len(fragen) < FAQ_MINDEST:
        befunde.append(f"„## {FAQ_UEBERSCHRIFT}“ mit mindestens {FAQ_MINDEST} fett gesetzten Fragen fehlt")
    if "**About the author**" not in l.rumpf:
        befunde.append("Autorenkasten „**About the author**“ fehlt")
    definiert = set(re.findall(r"^\[\^([^\]]+)\]:", l.rumpf, flags=re.M))
    benutzt = set(re.findall(r"\[\^([^\]]+)\](?!:)", l.rumpf))
    if benutzt - definiert:
        befunde.append("Fußnoten ohne Quelle: " + ", ".join(sorted(benutzt - definiert)))
    if definiert - benutzt:
        befunde.append("Quellen ohne Fußnote im Text: " + ", ".join(sorted(definiert - benutzt)))
    if not definiert:
        befunde.append("keine Fußnoten – jede Tatsache braucht die Quelle des Originals")
    return befunde


def sortiert(leitfaeden: list[Leitfaden]) -> list[Leitfaden]:
    """Neueste zuerst; bei gleichem Datum nach Kurzform, damit die Reihenfolge stabil bleibt."""
    return sorted(leitfaeden, key=lambda l: (l.erstellt, l.kurzform), reverse=True)


# --------------------------------------------------------------------------
# Seiten
# --------------------------------------------------------------------------

KOPF = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titel_tag}</title>
<meta name="description" content="{beschreibung}">
<meta name="theme-color" content="#0a121d">
{robots}<link rel="canonical" href="{canonical}">
{alternates}<!--
  DATENSCHUTZ: Diese Richtlinie erlaubt nur Dateien von dieser Website selbst.
  Die Leitfäden kommen ohne JavaScript aus; Skripte sind vollständig gesperrt.
  Erzeugt von tools/artikel_generator.py mit tools/beitraege_en.py aus entwuerfe-en/.
-->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self' mailto:">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fachwissen/artikel.css">
{og}</head>
<body>

<a class="skip-link" href="#inhalt">Skip to content</a>

<header class="seiten-kopf">
  <div class="wrap kopf-innen">
    <a href="/en/" class="logo" aria-label="BIB Ingenieurbüro für Bauwesen – English home"><b>BIB</b><span>Ingenieurbüro für Bauwesen</span></a>
    <nav aria-label="Sections">
      <a href="/en/#services">Services</a>
      <a href="/en/guides/">Guides</a>
      <a href="/en/technical-due-diligence-berlin/">Due diligence</a>
      <a href="/en/#contact">Contact</a>
      <a href="{deutsch}" class="sprache" lang="de" hreflang="de">Deutsch</a>
    </nav>
  </div>
</header>
"""

FUSS = """
<footer class="seiten-fuss">
  <div class="wrap">
    <p><strong>{firma}</strong><br>Straße am Flugplatz 6a, 12487 Berlin</p>
    <p><a href="tel:+4917623581339">+49 176 23581339</a> · <a href="mailto:info@ing-bassam.de">info@ing-bassam.de</a> · We reply within one working day</p>
    <p class="rechtliches"><a href="/#impressum" lang="de">Impressum (legal notice)</a> · <a href="/#datenschutz" lang="de">Datenschutz (privacy)</a> · <a href="/en/">All services in English</a> · <a href="/en/guides/">All guides</a> · <a href="{deutsch}" lang="de">{deutsch_text}</a></p>
    <p class="klein">© {jahr} {firma} · No cookies. No tracking.</p>
  </div>
</footer>

<nav class="schnellkontakt" aria-label="Quick contact">
  <a href="tel:+4917623581339"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg>Call us</a>
  <a href="mailto:info@ing-bassam.de?subject=Enquiry%20via%20your%20English%20guides" class="primaer"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>Send enquiry</a>
</nav>

</body>
</html>
"""


def titel_tag(titel: str) -> str:
    for zusatz in (" | BIB Ingenieurbüro für Bauwesen", " | BIB Ingenieurbüro", " | BIB"):
        if len(titel) + len(zusatz) <= TITEL_HOECHSTENS:
            return titel + zusatz
    return titel


def og_block(titel: str, beschreibung: str, url: str, typ: str, *, deutsch: bool,
             zeit: str = "", geaendert: str = "", verfasser: str = "") -> str:
    zeilen = [
        f'<meta property="og:type" content="{typ}">',
        '<meta property="og:locale" content="en_GB">',
    ]
    if deutsch:
        zeilen.append('<meta property="og:locale:alternate" content="de_DE">')
    zeilen += [
        '<meta property="og:site_name" content="BIB Ingenieurbüro für Bauwesen">',
        f'<meta property="og:title" content="{html.escape(titel, quote=True)}">',
        f'<meta property="og:description" content="{html.escape(beschreibung, quote=True)}">',
        f'<meta property="og:url" content="{html.escape(url, quote=True)}">',
        f'<meta property="og:image" content="{VORSCHAUBILD}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="BIB Ingenieurbüro für Bauwesen – building surveys and guides, Berlin">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if zeit:
        zeilen.append(f'<meta property="article:published_time" content="{zeit}">')
    if geaendert:
        zeilen.append(f'<meta property="article:modified_time" content="{geaendert}">')
    if verfasser:
        zeilen.append(f'<meta name="author" content="{html.escape(verfasser, quote=True)}">')
    return "\n".join(zeilen) + "\n"


def robots(indexierbar: bool) -> str:
    return ('<meta name="robots" content="max-snippet:-1, max-image-preview:large">\n' if indexierbar
            else '<meta name="robots" content="noindex, follow">\n')


def fuss(deutsch: str, deutsch_text: str) -> str:
    return FUSS.format(firma=html.escape(FIRMA), deutsch=deutsch, deutsch_text=deutsch_text,
                       jahr=date.today().year)


def strukturierte_daten(l: Leitfaden) -> str:
    knoten: list[dict] = [
        {
            "@type": "Article",
            "@id": l.url + "#article",
            "headline": l.titel,
            "description": l.meta_beschreibung,
            "inLanguage": "en",
            "datePublished": l.erstellt,
            "dateModified": l.geaendert,
            "author": {"@type": "Person", "name": l.autor_name, "honorificPrefix": l.autor_grad or None,
                       "worksFor": {"@id": FIRMA_ID}},
            "publisher": {"@id": FIRMA_ID},
            "mainEntityOfPage": {"@type": "WebPage", "@id": l.url},
            "image": VORSCHAUBILD,
            "keywords": l.schlagwoerter or None,
            "isPartOf": {"@type": "CollectionPage", "@id": UEBERSICHT_URL},
            # Die deutsche Fassung trägt umgekehrt workTranslation (artikel_generator.py).
            "translationOfWork": {"@id": l.deutsch_url + "#artikel"} if l.deutsch_url else None,
            "wordCount": l.wortzahl,
            "isAccessibleForFree": True,
        },
        {"@type": "Organization", "@id": FIRMA_ID, "name": FIRMA, "url": BASIS_URL + "/",
         "logo": VORSCHAUBILD},
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Services in English", "item": f"{BASIS_URL}/en/"},
                {"@type": "ListItem", "position": 2, "name": "Guides", "item": UEBERSICHT_URL},
                {"@type": "ListItem", "position": 3, "name": l.titel},
            ],
        },
    ]
    if l.faq:
        knoten.append({
            "@type": "FAQPage",
            "@id": l.url + "#faq",
            "mainEntity": [
                {"@type": "Question", "name": frage, "acceptedAnswer": {"@type": "Answer", "text": antwort}}
                for frage, antwort in l.faq
            ],
        })
    return json_text({"@context": "https://schema.org", "@graph": knoten})


def leistungskasten(l: Leitfaden) -> str:
    seite = leistungsseite(l.leistung) or leistungsseite("en/")
    ziel = f"/{seite.pfad}"
    knopf = "All services and fees" if seite.pfad == "en/" else "Scope and prices"
    return f"""      <aside class="leistungskasten" aria-labelledby="leistung-titel">
        <span class="eyebrow">Related service</span>
        <h2 id="leistung-titel"><a href="{ziel}">{html.escape(seite.name)}</a></h2>
        <p>{html.escape(seite.kurztext)}</p>
        <p class="aktionen"><a class="btn btn-primary" href="{ziel}">{knopf}</a><a class="btn btn-outline" href="/en/#contact">Send enquiry</a></p>
        <p class="klein">We reply within one working day · Berlin and Brandenburg · Reports in English or German</p>
      </aside>
"""


def karte(l: Leitfaden, ebene: str) -> str:
    return f"""          <li class="karte">
            <{ebene}><a href="{l.adresse}">{html.escape(l.titel)}</a></{ebene}>
            <p>{html.escape(l.meta_beschreibung)}</p>
            <p class="karte-meta"><time datetime="{l.erstellt}">{datum_en(l.erstellt)}</time> · about {l.lesezeit} minutes</p>
          </li>"""


def weitere(l: Leitfaden, oeffentlich: list[Leitfaden]) -> str:
    andere = [b for b in sortiert(oeffentlich) if b.kurzform != l.kurzform]
    if not andere:
        return ""
    return ("""      <nav class="weiterlesen" aria-labelledby="weiterlesen-titel">
        <h2 id="weiterlesen-titel">More guides in English</h2>
        <ul class="karten">
""" + "\n".join(karte(b, "h3") for b in andere) + """
        </ul>
      </nav>""")


def seite(l: Leitfaden, oeffentlich: list[Leitfaden]) -> str:
    """Die Seite eines Leitfadens unter /en/guides/<kurzform>/."""
    verknuepft = bool(l.deutsch_url and l.oeffentlich)
    deutsch = l.deutsch_url[len(BASIS_URL):] if verknuepft else "/fachwissen/"
    alternates = ""
    if verknuepft:
        alternates = (f'<link rel="alternate" hreflang="en" href="{l.url}">\n'
                      f'<link rel="alternate" hreflang="de" href="{l.deutsch_url}">\n'
                      f'<link rel="alternate" hreflang="x-default" href="{l.deutsch_url}">\n')
    kopf = KOPF.format(
        titel_tag=html.escape(titel_tag(l.titel)),
        beschreibung=html.escape(l.meta_beschreibung, quote=True),
        robots=robots(l.oeffentlich),
        canonical=html.escape(l.url, quote=True),
        alternates=alternates,
        deutsch=deutsch,
        og=og_block(l.titel, l.meta_beschreibung, l.url, "article", deutsch=verknuepft,
                    zeit=l.erstellt, geaendert=l.geaendert, verfasser=l.autor),
    )

    warnung = ""
    if not l.oeffentlich:
        warnung = ('<div class="entwurfswarnung" role="status"><strong>Draft – not yet published.</strong> '
                   "This page is excluded from search engines and does not appear in the guide list or the "
                   f"sitemap. Status: <code>{html.escape(l.status)}</code>."
                   + (f" Open review points in the text: {l.todos}." if l.todos else "") + "</div>")

    stand = ""
    if l.geaendert != l.erstellt:
        stand = f' · Updated <time datetime="{l.geaendert}">{datum_en(l.geaendert)}</time>'
    herkunft = ""
    if verknuepft:
        herkunft = (f'<br>\n          English version of our German article '
                    f'<a href="{deutsch}" lang="de" hreflang="de">{html.escape(l.deutsch_titel)}</a>')

    return (kopf + f"""
<main id="inhalt">
  <article class="artikel">
    <div class="wrap schmal">
      {warnung}
      <nav class="brotkrumen" aria-label="You are here">
        <a href="/en/">Services in English</a> <span aria-hidden="true">›</span>
        <a href="/en/guides/">Guides</a> <span aria-hidden="true">›</span>
        <span>{html.escape(l.titel)}</span>
      </nav>

      <header class="artikel-kopf">
        <span class="marke">Guide</span>
        <h1>{html.escape(l.titel)}</h1>
        <p class="artikel-meta">
          By {html.escape(l.autor)} ·
          <time datetime="{l.erstellt}">{datum_en(l.erstellt)}</time>{stand} ·
          about {l.lesezeit} minutes to read{herkunft}
        </p>
      </header>

      <div class="prosa">
{l.inhalt_html}
      </div>
{leistungskasten(l)}{weitere(l, oeffentlich)}
    </div>
  </article>
</main>

<script type="application/ld+json">{strukturierte_daten(l)}</script>
""" + fuss(deutsch, "Deutsche Fassung" if verknuepft else "Fachbeiträge auf Deutsch"))


UEBERSICHT_TITEL = "Guides in English – buying and building in Germany"
UEBERSICHT_BESCHREIBUNG = ("Guides in English from a Berlin engineering office: documents before buying, "
                           "flats and owners' associations, mould, warranty periods, surveyor fees.")


def uebersicht(oeffentlich: list[Leitfaden]) -> str:
    """Die Übersicht /en/guides/ – ohne hreflang, weil es auf Deutsch kein
    gleichwertiges Gegenstück gibt (die Fachwissen-Übersicht hat 50 Beiträge)."""
    liste_sortiert = sortiert(oeffentlich)
    kopf = KOPF.format(
        titel_tag=html.escape(titel_tag(UEBERSICHT_TITEL)),
        beschreibung=html.escape(UEBERSICHT_BESCHREIBUNG, quote=True),
        robots=robots(True),
        canonical=UEBERSICHT_URL,
        alternates="",
        deutsch="/fachwissen/",
        og=og_block(UEBERSICHT_TITEL, UEBERSICHT_BESCHREIBUNG, UEBERSICHT_URL, "website", deutsch=False),
    )
    daten = json_text({"@context": "https://schema.org", "@graph": [
        {
            "@type": "CollectionPage",
            "@id": UEBERSICHT_URL,
            "name": UEBERSICHT_TITEL,
            "description": UEBERSICHT_BESCHREIBUNG,
            "inLanguage": "en",
            "publisher": {"@id": FIRMA_ID},
            "mainEntity": {
                "@type": "ItemList",
                "itemListElement": [
                    {"@type": "ListItem", "position": i, "url": l.url, "name": l.titel}
                    for i, l in enumerate(liste_sortiert, start=1)
                ],
            },
        },
        {"@type": "Organization", "@id": FIRMA_ID, "name": FIRMA, "url": BASIS_URL + "/",
         "logo": VORSCHAUBILD},
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Services in English", "item": f"{BASIS_URL}/en/"},
                {"@type": "ListItem", "position": 2, "name": "Guides"},
            ],
        },
    ]})
    karten = "\n".join(karte(l, "h2") for l in liste_sortiert)
    return (kopf + f"""
<main id="inhalt">
  <div class="wrap">
    <nav class="brotkrumen" aria-label="You are here">
      <a href="/en/">Services in English</a> <span aria-hidden="true">›</span>
      <span>Guides</span>
    </nav>

    <header class="uebersicht-kopf">
      <h1>Guides in English</h1>
      <p>Practical guides from our engineering office in Berlin – for international buyers, owners, tenants and
      lawyers dealing with buildings in Germany. Each guide is the English version of one of our German technical
      articles and cites the same sources. German terms you will meet in contracts, letters and court are given in
      brackets. More than 50 further articles are available in German under
      <a href="/fachwissen/" lang="de" hreflang="de">Fachwissen</a>.</p>
    </header>

    <ul class="karten">
{karten}
    </ul>

    <aside class="leistungskasten" aria-labelledby="leistung-titel">
      <span class="eyebrow">Need an engineer on site?</span>
      <h2 id="leistung-titel"><a href="/en/">Building surveyors in Berlin – reports in English</a></h2>
      <p>Pre-purchase surveys, mould and water damage, new-build inspections, condition surveys and expert reports for
      disputes. Fixed prices for defined scopes, otherwise €150 per hour; travel within Berlin included.</p>
      <p class="aktionen"><a class="btn btn-primary" href="/en/#services">All services and fees</a><a class="btn btn-outline" href="/en/#contact">Send enquiry</a></p>
      <p class="klein">We reply within one working day · Berlin and Brandenburg · Reports in English or German</p>
    </aside>
  </div>
</main>

<script type="application/ld+json">{daten}</script>
""" + fuss("/fachwissen/", "Fachbeiträge auf Deutsch"))


# --------------------------------------------------------------------------
# Sitemap und llms.txt
# --------------------------------------------------------------------------

def sitemap_eintraege(oeffentlich: list[Leitfaden]) -> list[tuple[str, str, str, str]]:
    """(Adresse, lastmod, changefreq, priority) – Stand aus den Daten, nie das Laufdatum,
    damit zwei Läufe dasselbe Ergebnis liefern."""
    if not oeffentlich:
        return []
    neuester = max(l.geaendert for l in oeffentlich)
    return [(UEBERSICHT_URL, neuester, "monthly", "0.7")] + [
        (l.url, l.geaendert, "yearly", "0.7") for l in sorted(oeffentlich, key=lambda l: l.kurzform)
    ]


def llms_zeilen(oeffentlich: list[Leitfaden]) -> list[str]:
    if not oeffentlich:
        return []
    return ["", f"## Guides in English ({UEBERSICHT_URL})", ""] + [
        f"- [{l.titel}]({l.url}): {l.meta_beschreibung}" for l in sortiert(oeffentlich)
    ]
