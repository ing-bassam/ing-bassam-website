"""Tests für tools/doppelungen.py – mit den echten Beiträgen des Repositorys.

Aufruf: python -m unittest discover -s tests
Notion-Titel kommen hier bewusst nicht vor (das Repository ist öffentlich); die
Beispiele für Doppelungen sind aus veröffentlichten Beiträgen abgeleitet.
"""
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))

import bestand  # noqa: E402
import doppelungen as d  # noqa: E402

# Bekannte, schon veröffentlichte Paare, die nach heutiger Regel Doppelungen sind –
# beide Seiten sind online; entschieden hat der Auftraggeber (kein Fehler der Prüfung).
BEKANNTE_PAARE = {frozenset({"nachbesserung-verweigert-werklohn", "schweissnaht-beweislast-vor-abnahme"})}


def repo_bestand() -> list[dict]:
    eintraege = []
    for pfad in sorted((WURZEL / "entwuerfe").rglob("*.md")):
        if pfad.name.lower() == "readme.md":
            continue
        e = bestand.eintrag_aus_entwurf(pfad.read_text(encoding="utf-8"), pfad.relative_to(WURZEL).as_posix(),
                                        "hauptzweig")
        if e:
            eintraege.append(e)
    return eintraege


def thema(titel: str, kernfrage: str = "", art: str = "beitrag", **weitere) -> dict:
    return {"quelle": "auftrag", "art": art, "titel": titel, "kernfrage": kernfrage, **weitere}


def notion_seite(seiten_id: str, titel: str, kernfrage: str) -> dict:
    return {"id": seiten_id, "url": "https://www.notion.so/" + seiten_id, "created_time": "2026-10-01T00:00:00Z",
            "properties": {"Thema": {"title": [{"plain_text": titel}]},
                           "Kernfrage": {"rich_text": [{"plain_text": kernfrage}]},
                           "Status": {"select": {"name": "Idee"}}, "Format": {"select": {"name": "Ratgeber"}}}}


def entwurf(kurzform: str, titel: str, *, status: str = "entwurf", erstellt: str = "2026-10-02", **felder) -> dict:
    return {"quelle": "hauptzweig", "art": felder.pop("art", "beitrag"), "titel": titel, "kurzform": kurzform,
            "status": status, "erstellt": erstellt, "pfad": f"entwuerfe/entwurf/{erstellt}-{kurzform}.md",
            "link": f"https://ing-bassam.de/fachwissen/{kurzform}/" if status == "veröffentlicht" else "",
            "oeffentlich": True, **felder}


class Begriffe(unittest.TestCase):
    def test_gleichbedeutende_woerter(self):
        self.assertIn("mangelanzeige", d.begriffe("Mängelrüge richtig schreiben"))
        self.assertIn("mangelanzeige", d.begriffe("Mängelanzeige mit Fristsetzung"))
        self.assertIn("sachverstaendiger", d.begriffe("Was kostet ein Baugutachter?"))
        self.assertIn("sachverstaendiger", d.begriffe("Termin mit dem Bausachverständigen"))
        self.assertIn("regeln-der-technik", d.begriffe("Anerkannte Regeln der Technik"))

    def test_verkuerzte_zusammensetzung(self):
        b = d.begriffe("Behinderungs- und Bedenkenanzeige stellen")
        self.assertIn("behinderungsanzeige", b)
        self.assertIn("bedenkenanzeige", b)

    def test_fuellwoerter_zaehlen_nicht(self):
        self.assertEqual(d.begriffe("Was muss ich richtig tun?"), frozenset())

    def test_umlaute_und_endungen(self):
        self.assertEqual(d.begriffe("Fristen"), d.begriffe("Frist"))
        self.assertEqual(d.begriffe("Bauschäden"), d.begriffe("Bauschaden"))


class Urteile(unittest.TestCase):
    # Die beiden Entwürfe zu OLG Stuttgart 10 U 308/20 vom 02.10.2026 (der zweite ist entfernt).
    ERSTER = entwurf("pauschalpreis-bauvertrag-leistungsbeschreibung",
                     "Pauschalpreis im Bauvertrag: Was ist wirklich enthalten?", art="urteil",
                     kernfrage="Was ist in einem Pauschalpreis enthalten, und wofür darf die Baufirma zusätzlich Geld verlangen?",
                     aktenzeichen="10 U 308/20", ecli="ECLI:DE:OLGSTUT:2021:0309.10U308.20.00")
    ZWEITER = entwurf("pauschalpreis-leistungsbeschreibung-nachforderung",
                      "Pauschalpreis: Stahl kostete 106.694 Euro extra", art="urteil",
                      kernfrage="Deckt ein Pauschalpreis im Bauvertrag wirklich alle Leistungen ab?",
                      aktenzeichen="10 U 308/20", ecli='"ECLI:DE:OLGSTUT:2021:0309.10U308.20.00"',
                      erstellt="2026-10-02")

    def test_dasselbe_urteil_ist_doppelung(self):
        v = d.Vergleich([self.ERSTER, self.ZWEITER])
        self.assertEqual(v.urteil(self.ZWEITER, self.ERSTER)[:2], ("doppelung", "dasselbe Urteil"))

    def test_bestand_pruefen_meldet_den_juengeren(self):
        zweiter = dict(self.ZWEITER, pfad="entwuerfe/entwurf/2026-10-02-z.md")
        funde = d.bestand_pruefen([self.ERSTER, zweiter])
        self.assertEqual(len(funde), 1)
        self.assertIs(funde[0][0], zweiter)

    def test_ecli_allein_reicht(self):
        a = dict(self.ERSTER, aktenzeichen="")
        b = dict(self.ZWEITER, aktenzeichen="10 U 308/20 (anders geschrieben)")
        self.assertTrue(d.gleiches_urteil(a, b))

    def test_verschiedene_urteile_zum_selben_thema_hoechstens_verwandt(self):
        anderes = dict(self.ZWEITER, aktenzeichen="7 U 1/22", ecli="")
        self.assertNotEqual(d.Vergleich([self.ERSTER, anderes]).urteil(anderes, self.ERSTER)[0], "doppelung")


class Sprachen(unittest.TestCase):
    DEUTSCH = entwurf("technische-due-diligence-immobilienkauf", "Technische Due Diligence beim Immobilienkauf",
                      status="veröffentlicht", kernfrage="Was prüft eine technische Due Diligence vor dem Kauf?")

    def test_uebersetzung_ist_keine_doppelung(self):
        englisch = thema("Technical Due Diligence for Real Estate in Germany",
                         "What does a technical due diligence cover before buying a property?", sprache="en")
        self.assertEqual(d.Vergleich([self.DEUTSCH, englisch]).urteil(englisch, self.DEUTSCH)[0], "neu")

    def test_gleiche_sprache_bleibt_doppelung(self):
        deutsch = thema("Technische Due Diligence beim Kauf einer Immobilie",
                        "Was prüft eine technische Due Diligence vor dem Kauf?")
        self.assertEqual(d.Vergleich([self.DEUTSCH, deutsch]).urteil(deutsch, self.DEUTSCH)[0], "doppelung")

    def test_sprache_aus_dateikopf_und_notion(self):
        self.assertEqual(bestand.sprache_von("Englisch"), "en")
        self.assertEqual(bestand.sprache_von("en"), "en")
        self.assertEqual(bestand.sprache_von(""), "de")
        text = "---\ntitel: \"X\"\nsprache: en\nkurzform: x\n---\n"
        self.assertEqual(bestand.eintrag_aus_entwurf(text, "entwuerfe/entwurf/x.md", "hauptzweig")["sprache"], "en")


class EchterBestand(unittest.TestCase):
    """Die Schwellen dürfen keinen der vorhandenen Beiträge zur Doppelung eines anderen machen."""

    @classmethod
    def setUpClass(cls):
        cls.bestand = repo_bestand()
        cls.vergleich = d.Vergleich(cls.bestand)
        cls.nach_kurzform = {e["kurzform"]: e for e in cls.bestand}

    def test_keine_doppelung_unter_vorhandenen_beitraegen(self):
        paare = set()
        for a in self.bestand:
            for b in self.bestand:
                if a is not b and self.vergleich.urteil(a, b)[0] == "doppelung":
                    paare.add(frozenset({a["kurzform"], b["kurzform"]}))
        self.assertEqual(paare - BEKANNTE_PAARE, set())

    def pruefen(self, t: dict) -> dict:
        return d.Vergleich(self.bestand + [t]).pruefen(t, self.bestand)

    def test_umschriebenes_thema_einer_vorlage_ist_doppelung(self):
        for t, erwartet in (
            (thema("Ortstermin mit dem Bausachverständigen vorbereiten",
                   "Wie bereite ich mich auf den Ortstermin mit dem Sachverständigen vor?"),
             "vorbereitung-gutachter-ortstermin"),
            (thema("Mängelrüge an die Baufirma: Frist setzen und richtig zustellen",
                   "Wie zeige ich dem Bauunternehmen einen Mangel an, und welche Frist setze ich?"),
             "maengelanzeige-mit-fristsetzung"),
        ):
            if erwartet not in self.nach_kurzform:
                self.skipTest(f"{erwartet} nicht mehr im Bestand")
            ergebnis = self.pruefen(t)
            self.assertEqual(ergebnis["urteil"], "doppelung", t["titel"])
            self.assertEqual(ergebnis["doppelungen"][0][0]["kurzform"], erwartet)

    def test_neues_thema_bleibt_neu(self):
        self.assertEqual(self.pruefen(thema("Radon im Keller messen", "Wie messe ich Radon im Haus?"))["urteil"],
                         "neu")

    def test_vorlage_zum_thema_eines_fachbeitrags_ist_keine_doppelung(self):
        if "abnahme-bautraeger-sonder-gemeinschaftseigentum" not in self.nach_kurzform:
            self.skipTest("Beitrag nicht mehr im Bestand")
        t = thema("Checkliste Abnahme vom Bauträger: Sonder- und Gemeinschaftseigentum",
                  "Wie läuft die Abnahme einer neuen Eigentumswohnung ab, und wer nimmt das Gemeinschaftseigentum ab?",
                  art="vorlage")
        self.assertNotEqual(self.pruefen(t)["urteil"], "doppelung")

    def test_eigener_entwurf_heisst_vorhanden(self):
        mit_id = [e for e in self.bestand if e.get("notion_id")]
        if not mit_id:
            self.skipTest("kein Entwurf mit Notion-Seite im Bestand")
        t = thema("ganz anderer Titel", notion_id=mit_id[0]["notion_id"])
        self.assertEqual(self.pruefen(t)["urteil"], "vorhanden")


class Auswahl(unittest.TestCase):
    BESTAND = [entwurf("vorbereitung-gutachter-ortstermin", "Checkliste Ortstermin mit dem Bausachverständigen",
                       status="veröffentlicht", art="vorlage",
                       kernfrage="Wie bereite ich mich auf den Termin mit dem Bausachverständigen vor?")]
    DOPPELT = notion_seite("aaaaaaaa00b481c59a72fc598789e602", "Ortstermin mit dem Bausachverständigen vorbereiten",
                           "Wie bereite ich mich auf den Ortstermin mit dem Sachverständigen vor?")
    NEU = notion_seite("bbbbbbbb00b481c59a72fc598789e602", "Radon im Keller messen", "Wie messe ich Radon?")

    def setUp(self):
        self.aufrufe = []

    def senden(self, methode, pfad, daten=None):
        self.aufrufe.append((methode, pfad, daten))
        return {}

    def test_doppelung_wird_markiert_und_das_naechste_gewaehlt(self):
        seite, ergebnis, zeilen = d.auswaehlen([self.DOPPELT, self.NEU], "themenspeicher", self.BESTAND,
                                               senden=self.senden, hinweis_pruefen=lambda _: False)
        self.assertEqual(seite["id"], self.NEU["id"])
        self.assertEqual(ergebnis["urteil"], "neu")
        status = [a for a in self.aufrufe if a[1] == f"/pages/{self.DOPPELT['id']}"]
        self.assertEqual(status[0][2]["properties"]["Status"]["select"]["name"], "Doppelung")
        hinweis = [a for a in self.aufrufe if a[1].startswith(f"/blocks/{self.DOPPELT['id']}")]
        self.assertEqual(hinweis[0][2]["children"][0]["type"], "callout")
        # Im öffentlichen Protokoll kein Notion-Titel
        self.assertFalse(any("Radon" in z or "vorbereiten" in z for z in zeilen))

    def test_freigegebene_doppelung_wird_geschrieben(self):
        seite, ergebnis, _ = d.auswaehlen([self.DOPPELT, self.NEU], "themenspeicher", self.BESTAND,
                                          senden=self.senden, hinweis_pruefen=lambda _: True)
        self.assertEqual(seite["id"], self.DOPPELT["id"])
        self.assertTrue(ergebnis["freigegeben"])
        self.assertEqual(self.aufrufe, [])
        self.assertIn("ausdrücklich freigegeben", d.abschnitt_verwandte(ergebnis, freigegeben=True))

    def test_probelauf_aendert_nichts(self):
        seite, _, _ = d.auswaehlen([self.DOPPELT, self.NEU], "themenspeicher", self.BESTAND, markieren=False,
                                   senden=self.senden, hinweis_pruefen=lambda _: False)
        self.assertEqual(seite["id"], self.NEU["id"])
        self.assertEqual(self.aufrufe, [])

    def test_hoechstzahl_der_markierungen(self):
        viele = [dict(self.DOPPELT, id=f"{i:08d}00b481c59a72fc598789e602") for i in range(d.HOECHSTENS_MARKIEREN + 2)]
        seite, _, _ = d.auswaehlen(viele, "themenspeicher", self.BESTAND, senden=self.senden,
                                   hinweis_pruefen=lambda _: False)
        self.assertIsNone(seite)
        markiert = [a for a in self.aufrufe if a[0] == "PATCH" and a[1].startswith("/pages/")]
        self.assertEqual(len(markiert), d.HOECHSTENS_MARKIEREN)


class Abschnitt(unittest.TestCase):
    def test_nur_veroeffentlichte_mit_adresse(self):
        online = entwurf("a-b-c", "Online", status="veröffentlicht", kernfrage="Frage A?")
        offen = entwurf("d-e-f", "Offen", kernfrage="Frage B?")
        text = d.abschnitt_verwandte({"doppelungen": [], "verwandte": [(online, "", {}), (offen, "", {})]})
        self.assertIn("https://ing-bassam.de/fachwissen/a-b-c/", text)
        self.assertNotIn("fachwissen/d-e-f", text)
        self.assertIn("nicht verlinken", text)

    def test_notion_eintraege_erscheinen_nicht(self):
        notion = {"quelle": "notion", "titel": "Geheimes Thema", "kurzform": "", "status": "Idee"}
        text = d.abschnitt_verwandte({"doppelungen": [], "verwandte": [(notion, "", {})]})
        self.assertNotIn("Geheimes Thema", text)


if __name__ == "__main__":
    unittest.main()
