#!/usr/bin/env python3
"""Schreibt die festen Abschnitte der Seiten zur Kaufbegutachtung aus daten.js.

Warum: Leistungsumfang, Hinweise, Unterlagen und Texte der Kaufbegutachtung
stehen an EINER Stelle – werkzeuge/kaufbegutachtung/daten.js. Der
Hinweis-Assistent im Browser liest sie dort. Preise stehen nirgends auf der
Website: Preise und Leistungsübersicht verschickt das Büro nur auf Anfrage per
E-Mail (deshalb auch keine Offer-/Preisangaben in den Strukturdaten).

Damit Suchmaschinen und KI-Crawler (die kein JavaScript ausführen) dieselben
Inhalte sehen, stehen sie zusätzlich als festes HTML in den Seiten. Dieses
Skript erzeugt dieses HTML aus den Daten und ersetzt die Abschnitte zwischen
den Markierungen

    <!-- DATEN:name -->  …  <!-- /DATEN:name -->

in leistungen/kaufbegutachtung/index.html und
en/pre-purchase-inspection-berlin/index.html. Alles außerhalb der Markierungen
(Kopf, Navigation, Formular, Fuß) bleibt von Hand gepflegt.

Aufruf:
    python tools/kaufbegutachtung_bauen.py            Abschnitte neu schreiben
    python tools/kaufbegutachtung_bauen.py --pruefen  nur prüfen (Rückgabewert 1 bei Abweichung)

tests/test_kaufbegutachtung.py ruft die Prüfung auf: Wer daten.js ändert und
das Skript nicht ausführt, bekommt einen roten Test.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
DATEN_JS = WURZEL / "werkzeuge" / "kaufbegutachtung" / "daten.js"
SEITEN = {
    "de": WURZEL / "leistungen" / "kaufbegutachtung" / "index.html",
    "en": WURZEL / "en" / "pre-purchase-inspection-berlin" / "index.html",
}
KATEGORIEN = ["pflicht", "miete", "pruefen", "foerderung"]
OBJEKTE = ["etw", "efh"]
# Kennungen der festen Abschnitte je Objektart und Sprache (Ziele der Anker auf der Seite).
LEISTUNG_ID = {"de": {"etw": "leistung-wohnung", "efh": "leistung-haus"},
               "en": {"etw": "service-flat", "efh": "service-house"}}
UNTERLAGEN_ID = {"de": {"etw": "unterlagen-wohnung", "efh": "unterlagen-haus"},
                 "en": {"etw": "documents-flat", "efh": "documents-house"}}
MARKE = re.compile(r"^([ \t]*)<!-- DATEN:([a-z_]+) -->\n.*?^[ \t]*<!-- /DATEN:\2 -->$", re.S | re.M)


# ------------------------------------------------------------------ Daten

def daten_laden(pfad: Path = DATEN_JS) -> dict:
    """Liest das JSON zwischen /* DATEN-ANFANG */ und /* DATEN-ENDE */ aus daten.js."""
    text = pfad.read_text(encoding="utf-8")
    treffer = re.search(r"/\* DATEN-ANFANG \*/(.*)/\* DATEN-ENDE \*/", text, re.S)
    if not treffer:
        raise SystemExit(f"FEHLER: Markierungen DATEN-ANFANG/DATEN-ENDE fehlen in {pfad}")
    return json.loads(treffer.group(1))


# ------------------------------------------------------------- Bausteine

def e(text) -> str:
    return html.escape(str(text), quote=True)


def ersetzen(vorlage: str, **werte) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(werte.get(m.group(1), m.group(0))), vorlage)


def einsetzen(daten: dict, text: str, sprache: str) -> str:
    """Platzhalter in Seitentexten: {text:SCHLUESSEL} wird durch daten.text[sprache][SCHLUESSEL] ersetzt."""
    return re.sub(r"\{text:(\w+)\}", lambda m: daten["text"][sprache][m.group(1)], text)


def oder(liste: list[str], sprache_ui: dict) -> str:
    if len(liste) <= 1:
        return "".join(liste)
    return ", ".join(liste[:-1]) + f" {sprache_ui['oder']} " + liste[-1]


def label(daten: dict, feld: str, ids: list[str], sprache: str) -> list[str]:
    """Anzeigenamen der Auswahlwerte; „Weiß ich nicht“ heißt in Bedingungen „unbekannt“."""
    namen = {x["id"]: x[sprache] for x in daten["eingaben"][feld]}
    namen["unbekannt"] = daten["seite"][sprache]["ui"]["unbekannt"]
    return [namen[i] for i in ids]


def bedingung_regel(daten: dict, regel: dict, sprache: str) -> str:
    """„Haus · Baujahr bis 2001 · Heizung: Ölheizung“ – woran die Regel hängt."""
    t = daten["seite"][sprache]["ui"]
    teile = [t["objekt_kurz"][regel["objekt"]]]
    if "von" in regel and "bis" in regel:
        teile.append(ersetzen(t["baujahr_von_bis"], von=regel["von"], bis=regel["bis"]))
    elif "bis" in regel:
        teile.append(ersetzen(t["baujahr_bis"], bis=regel["bis"]))
    elif "von" in regel:
        teile.append(ersetzen(t["baujahr_ab"], von=regel["von"]))
    for feld, vorlage in (("heizung", "heizung_bed"), ("nutzung", "nutzung_bed"), ("region", "region_bed")):
        if feld in regel:
            teile.append(ersetzen(t[vorlage], liste=oder(label(daten, feld, regel[feld], sprache), t)))
    for name in daten["eingaben"]["schalter"]:
        if regel.get(name):
            teile.append(daten["eingaben"]["schalter"][name][sprache])
    return " · ".join(teile)


def bedingung_unterlage(daten: dict, u: dict, sprache: str) -> str:
    t = daten["seite"][sprache]["ui"]
    teile = []
    if "von" in u and "bis" in u:
        teile.append(ersetzen(t["u_baujahr_von_bis"], von=u["von"], bis=u["bis"]))
    elif "bis" in u:
        teile.append(ersetzen(t["u_baujahr_bis"], bis=u["bis"]))
    elif "von" in u:
        teile.append(ersetzen(t["u_baujahr_ab"], von=u["von"]))
    if "heizung" in u:
        teile.append(ersetzen(t["u_heizung"], liste=oder(label(daten, "heizung", u["heizung"], sprache), t)))
    if "nutzung" in u:
        teile.append(t["u_vermietet"])
    for name in daten["eingaben"]["schalter"]:
        if u.get(name):
            teile.append(ersetzen(t["u_schalter"], name=daten["eingaben"]["schalter"][name][sprache]))
    return " · ".join(teile)


def quelle_html(regel: dict, sprache: str, t: dict) -> str:
    q = regel["quelle"]
    sprach_attr = ' lang="de"' if sprache == "en" else ""
    if q.get("url"):
        return f'{e(t["quelle"])}: <a href="{e(q["url"])}"{sprach_attr} rel="noopener">{e(q["titel"])}</a>'
    return f'{e(t["quelle"])}: <span{sprach_attr}>{e(q["titel"])}</span>'


# --------------------------------------------------------------- Abschnitte

def block_kopf(daten: dict, sprache: str) -> str:
    text = daten["text"][sprache]
    seite = daten["seite"][sprache]
    vorne, _, hinten = text["titel"].partition(" – ")
    titel = f'{e(vorne)} – <span class="accent">{e(hinten)}</span>' if hinten else e(vorne)
    nutzen = [f'  <li><b>{e(n["t"])}</b><span>{e(n["d"])}</span></li>' for n in text["nutzen"]]
    extra = text["nutzen_etw_extra"]
    nutzen.append(f'  <li data-objekt-nur="etw"><small>{e(seite["ui"]["nur_wohnung"])}</small>'
                  f'<b>{e(extra["t"])}</b><span>{e(extra["d"])}</span></li>')
    return "\n".join([
        f'<span class="eyebrow">{e(text["kopf_unter"])}</span>',
        f'<h1 id="titel">{titel}</h1>',
        f'<p class="hero-lead">{e(seite["unterzeile"])}</p>',
        '<ul class="nutzen-liste">', *nutzen, "</ul>",
        f'<p class="vertrauen-satz">{e(text["vertrauen"])}</p>',
        *([f'<p class="sprach-hinweis">{e(einsetzen(daten, seite["sprach_hinweis"], sprache))}</p>']
          if seite.get("sprach_hinweis") else []),
    ])


def block_rechner_kopf(daten: dict, sprache: str) -> str:
    text = daten["text"][sprache]
    return "\n".join([
        '<div class="schritt-kopf">',
        f'  <h2 id="rechner-titel">{e(text["qr_titel"])}</h2>',
        f'  <p>{e(text["qr_text"])}</p>',
        "</div>",
    ])


def block_objektwahl(daten: dict, sprache: str) -> str:
    text = daten["text"][sprache]
    zeilen = ['<ul class="wahl" data-spalten="2">']
    for objekt in OBJEKTE:
        geprueft = " checked" if objekt == "etw" else ""
        zeilen.append(f'  <li><label><input type="radio" name="objekt" value="{objekt}"{geprueft}>'
                      f'<span class="titel">{e(text["objekt_" + objekt])}</span>'
                      f'<span class="text">{e(text["objekt_" + objekt + "_unter"])}</span></label></li>')
    zeilen.append("</ul>")
    return "\n".join(zeilen)


def block_leistungsumfang(daten: dict, sprache: str) -> str:
    """Leistungsumfang je Objektart (ohne Preise) und der Hinweis „Preise auf Anfrage per E-Mail“."""
    text = daten["text"][sprache]
    seite = daten["seite"][sprache]
    t = seite["ui"]
    kontakt = daten["kontakt"]
    zeilen = []
    if seite.get("sprach_hinweis"):
        zeilen.append(f'<p class="pauschal">{e(einsetzen(daten, seite["sprach_hinweis"], sprache))}</p>')
    zeilen.append('<div class="leistung-spalten">')
    for objekt in OBJEKTE:
        kennung = LEISTUNG_ID[sprache][objekt]
        zeilen += [
            f'  <section class="leistungsblock" id="{kennung}" aria-labelledby="{kennung}-titel">',
            f'    <h3 id="{kennung}-titel">{e(text["objekt_" + objekt])} <small>{e(text["objekt_" + objekt + "_unter"])}</small></h3>',
            f'    <p class="leistung-unter">{e(t["leistung_titel"])}</p>',
            '    <ul class="liste-haken">',
            *(f"      <li>{e(x)}</li>" for x in daten["leistungen"][objekt][sprache]),
            '    </ul>',
        ]
        if objekt == "etw":
            a = seite["anteil"]
            zeilen.append(f'    <p class="anteil-beispiel"><b>{e(a["titel"])}:</b> {e(a["text"])} {e(a["beispiel"])}. '
                          f'{e(a["hinweis"])}</p>')
        zeilen.append('  </section>')
    telefon = re.sub(r"[^+\d]", "", kontakt["telefon"])
    zeilen += ['</div>',
               f'<p class="preise-anfrage"><b>{e(text["preise"])}</b> '
               f'<a href="mailto:{e(kontakt["email"])}">{e(kontakt["email"])}</a> · '
               f'<a href="tel:{telefon}">{e(kontakt["telefon"])}</a></p>',
               f'<p class="pauschal">{e(text["ausserhalb"])}</p>']
    return "\n".join(zeilen)


def block_hinweise(daten: dict, sprache: str) -> str:
    seite = daten["seite"][sprache]
    t = seite["ui"]
    zeilen = [f'<h2 id="{"hinweise" if sprache == "de" else "notes"}">{e(seite["hinweise_titel"])}</h2>',
              f'<p class="hinweise-einleitung">{e(seite["hinweise_unter"])}</p>',
              f'<p class="rechtsstand">{e(daten["text"][sprache]["rechtsstand"])}</p>',
              '<div class="hinweis-gruppen">']
    for kategorie in KATEGORIEN:
        zeilen += [f'  <section class="hinweis-gruppe" data-kategorie="{kategorie}" aria-labelledby="kategorie-{kategorie}">',
                   f'    <h3 id="kategorie-{kategorie}">{e(seite["kategorien"][kategorie])}</h3>']
        for regel in (r for r in daten["regeln"] if r["kategorie"] == kategorie):
            rt = regel[sprache]
            inhalt = [f'<p>{e(rt["text"])}</p>']
            inhalt.append(f'<p class="quelle">{quelle_html(regel, sprache, t)}</p>')
            zeilen += [
                f'    <details class="abschnitt hinweis" data-regel="{regel["id"]}">',
                f'      <summary><span class="hinweis-kopf"><span class="hinweis-titel">{e(rt["titel"])}</span>'
                f'<small class="hinweis-bedingung">{e(bedingung_regel(daten, regel, sprache))}</small></span></summary>',
                f'      <div class="abschnitt-inhalt">{"".join(inhalt)}</div>',
                '    </details>',
            ]
        zeilen.append('  </section>')
    zeilen.append('</div>')
    return "\n".join(zeilen)


def block_unterlagen(daten: dict, sprache: str) -> str:
    text = daten["text"][sprache]
    t = daten["seite"][sprache]["ui"]
    zeilen = [f'<h2 id="{"unterlagen" if sprache == "de" else "documents"}">{e(text["unterlagen_titel"])}</h2>',
              f'<p class="unterlagen-einleitung">{e(text["unterlagen_unter"])}</p>',
              '<div class="unterlagen-spalten">']
    for objekt in OBJEKTE:
        kennung = UNTERLAGEN_ID[sprache][objekt]
        zeilen += [f'  <section id="{kennung}" aria-labelledby="{kennung}-titel">',
                   f'    <h3 id="{kennung}-titel">{e(text["objekt_" + objekt])}</h3>']
        for prio in (1, 2, 3):
            teil = [u for u in daten["unterlagen"][objekt] if u["prio"] == prio]
            if not teil:
                continue
            zeilen += [f'    <h4 class="prio prio-{prio}">{e(text["prio"][str(prio)])}</h4>', '    <ul class="unterlagen-liste">']
            for u in teil:
                bedingung = bedingung_unterlage(daten, u, sprache)
                zusatz = f" · {e(bedingung)}" if bedingung else ""
                zeilen.append(f'      <li data-unterlage="{u["id"]}"><span>{e(u[sprache])}</span>'
                              f'<small>{e(t["wo_kurz"])}: {e(u["wo_" + sprache])}{zusatz}</small></li>')
            zeilen.append('    </ul>')
        zeilen.append('  </section>')
    zeilen.append('</div>')
    return "\n".join(zeilen)


def block_ablauf(daten: dict, sprache: str) -> str:
    text = daten["text"][sprache]
    t = daten["seite"][sprache]["ui"]
    zeilen = ['<ol class="ablauf">']
    for schritt in text["ablauf"]:
        zeilen.append(f'  <li><b>{e(schritt["t"])}</b> <span class="wann">{e(schritt["w"])}</span> – {e(schritt["d"])}</li>')
    zeilen += ['</ol>', '<div class="info-raster">',
               f'  <div><h3>{e(t["bekommen_titel"])}</h3><ul class="liste-haken">'
               + "".join(f"<li>{e(x)}</li>" for x in text["bekommen"]) + "</ul></div>",
               f'  <div><h3>{e(t["grenzen_titel"])}</h3><ul class="liste-grenzen">'
               + "".join(f"<li>{e(x)}</li>" for x in text["grenzen"]) + "</ul></div>",
               '</div>']
    return "\n".join(zeilen)


def block_beauftragen(daten: dict, sprache: str) -> str:
    text = daten["text"][sprache]
    return "\n".join([
        '<ul class="leistung-liste">', *(f"  <li>{e(x)}</li>" for x in text["qualifikation"]), "</ul>",
        f'<p>{e(text["vertrauen"])}</p>',
        f'<p class="beauftragen"><b>{e(text["beauftragen"])}</b></p>',
        f'<p>{e(text["preise"])} {e(text["ausserhalb"])}</p>',
    ])


def block_beauftragen_hinweis(daten: dict, sprache: str) -> str:
    """Unter dem Knopf „Angebot anfordern“: Preise auf Anfrage, dann Beauftragung und Widerruf."""
    text = daten["text"][sprache]
    return "\n".join([
        f'<p class="hilfe preise-anfrage-kurz"><b>{e(text["preise"])}</b></p>',
        f'<p class="hilfe">{e(text["beauftragen"])}</p>',
    ])


def block_anteil_kopf(daten: dict, sprache: str) -> str:
    a = daten["seite"][sprache]["anteil"]
    return "\n".join([
        f'<h3 class="schritt-titel" id="anteil-titel">{e(a["titel"])}</h3>',
        f'<p class="schritt-text">{e(a["text"])} {e(a["beispiel"])}.</p>',
    ])


def block_anteil_hinweis(daten: dict, sprache: str) -> str:
    return f'<p class="hilfe">{e(daten["seite"][sprache]["anteil"]["hinweis"])}</p>'


def faq(daten: dict, sprache: str) -> list[tuple[str, str]]:
    """Fragen und Antworten mit eingesetzten Texten (sichtbar und in den Strukturdaten gleich)."""
    return [(f["f"], einsetzen(daten, f["a"], sprache)) for f in daten["seite"][sprache]["faq"]]


def block_faq(daten: dict, sprache: str) -> str:
    return "\n".join(
        f'<details class="abschnitt"><summary>{e(frage)}</summary><div class="abschnitt-inhalt"><p>{e(antwort)}</p></div></details>'
        for frage, antwort in faq(daten, sprache))


def strukturdaten(daten: dict, sprache: str) -> dict:
    seite = daten["seite"][sprache]
    text = daten["text"][sprache]
    url = daten["urls"][sprache]
    # Bewusst ohne Offer, price oder priceSpecification: Preise gibt es nur auf Anfrage per E-Mail.
    if sprache == "de":
        krumen = [("Start", "https://ing-bassam.de/"), ("Leistungen", "https://ing-bassam.de/leistungen/"),
                  ("Kaufbegutachtung", url)]
        name, anderer = "Kaufbegutachtung Berlin", "Pre-purchase inspection Berlin"
    else:
        krumen = [("Services in English", "https://ing-bassam.de/en/"), ("Pre-purchase inspection", url)]
        name, anderer = "Pre-purchase inspection Berlin", "Kaufbegutachtung Berlin"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(krumen, 1)]},
            {"@type": "Service", "@id": f"{url}#service", "name": name, "alternateName": anderer,
             "serviceType": text["kopf_unter"].split(" · ")[0], "description": seite["dienst"],
             "provider": {"@id": "https://ing-bassam.de/#organization"},
             "areaServed": [{"@type": "City", "name": "Berlin"}, {"@type": "State", "name": "Brandenburg"}],
             "availableChannel": {"@type": "ServiceChannel", "availableLanguage": ["de", "en"]},
             "url": url},
            {"@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": frage, "acceptedAnswer": {"@type": "Answer", "text": antwort}}
                for frage, antwort in faq(daten, sprache)]},
        ],
    }


def json_kompakt(wert, einzug: int = 0, breite: int = 200) -> str:
    """JSON wie auf den übrigen Leistungsseiten: kurze Objekte auf einer Zeile, lange aufgeklappt."""
    zeile = json.dumps(wert, ensure_ascii=False, separators=(", ", ": "))
    if not isinstance(wert, (dict, list)) or len(zeile) + einzug <= breite:
        return zeile
    innen = " " * (einzug + 2)
    if isinstance(wert, dict):
        teile = [f"{innen}{json.dumps(k, ensure_ascii=False)}: {json_kompakt(v, einzug + 2, breite)}" for k, v in wert.items()]
        return "{\n" + ",\n".join(teile) + "\n" + " " * einzug + "}"
    teile = [innen + json_kompakt(v, einzug + 2, breite) for v in wert]
    return "[\n" + ",\n".join(teile) + "\n" + " " * einzug + "]"


def block_strukturdaten(daten: dict, sprache: str) -> str:
    inhalt = json_kompakt(strukturdaten(daten, sprache))
    # „</“ darf in einem <script>-Block nicht vorkommen.
    inhalt = inhalt.replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{inhalt}\n</script>'


BLOECKE = {
    "strukturdaten": block_strukturdaten,
    "kopf": block_kopf,
    "rechner_kopf": block_rechner_kopf,
    "objektwahl": block_objektwahl,
    "leistungsumfang": block_leistungsumfang,
    "hinweise": block_hinweise,
    "unterlagen": block_unterlagen,
    "ablauf": block_ablauf,
    "beauftragen": block_beauftragen,
    "beauftragen_hinweis": block_beauftragen_hinweis,
    "anteil_kopf": block_anteil_kopf,
    "anteil_hinweis": block_anteil_hinweis,
    "faq": block_faq,
}


# ---------------------------------------------------------------- Ersetzen

def seite_bauen(roh: str, daten: dict, sprache: str) -> tuple[str, list[str]]:
    """Ersetzt alle markierten Abschnitte; gibt den neuen Text und fehlende Markierungen zurück."""
    gefunden = set()

    def ersetze(m: re.Match) -> str:
        einzug, name = m.group(1), m.group(2)
        if name not in BLOECKE:
            raise SystemExit(f"FEHLER: unbekannter Abschnitt DATEN:{name}")
        gefunden.add(name)
        inhalt = BLOECKE[name](daten, sprache)
        eingerueckt = "\n".join(einzug + z if z else z for z in inhalt.split("\n"))
        return f"{einzug}<!-- DATEN:{name} -->\n{eingerueckt}\n{einzug}<!-- /DATEN:{name} -->"

    neu = MARKE.sub(ersetze, roh)
    return neu, sorted(set(BLOECKE) - gefunden)


def pruefen(daten: dict | None = None) -> list[str]:
    """Abweichungen zwischen Daten und Seiten (leer = alles aktuell)."""
    daten = daten or daten_laden()
    befunde = []
    for sprache, pfad in SEITEN.items():
        roh = pfad.read_text(encoding="utf-8")
        neu, fehlend = seite_bauen(roh, daten, sprache)
        ort = pfad.relative_to(WURZEL).as_posix()
        befunde += [f"{ort}: Markierung DATEN:{name} fehlt" for name in fehlend]
        if neu != roh:
            befunde.append(f"{ort}: Abschnitte weichen von daten.js ab – python tools/kaufbegutachtung_bauen.py ausführen")
    return befunde


def main() -> int:
    zerleger = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    zerleger.add_argument("--pruefen", action="store_true", help="nur prüfen, nichts schreiben")
    argumente = zerleger.parse_args()
    daten = daten_laden()
    if argumente.pruefen:
        befunde = pruefen(daten)
        for b in befunde:
            print(f"ABWEICHUNG: {b}")
        print("Seiten zur Kaufbegutachtung sind aktuell." if not befunde else f"{len(befunde)} Abweichung(en).")
        return 1 if befunde else 0
    for sprache, pfad in SEITEN.items():
        roh = pfad.read_text(encoding="utf-8")
        neu, fehlend = seite_bauen(roh, daten, sprache)
        for name in fehlend:
            print(f"HINWEIS: {pfad.relative_to(WURZEL).as_posix()} hat keine Markierung DATEN:{name}")
        if neu != roh:
            with open(pfad, "w", encoding="utf-8", newline="\n") as f:
                f.write(neu)
            print(f"geschrieben: {pfad.relative_to(WURZEL).as_posix()}")
        else:
            print(f"unverändert: {pfad.relative_to(WURZEL).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
