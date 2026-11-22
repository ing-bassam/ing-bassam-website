"""Prüft, wie das Suchskript der Urteils-Agenten Volltexte aufbereitet.

Hintergrund: Die Agenten lesen nur die Textdatei. Fehlen dort die Randnummern
oder steht nicht dabei, dass der Bundesgerichtshof die Sache zurückverwiesen
hat, entstehen Beiträge, die einen Sieger nennen, den es noch nicht gibt.
Die Tests laufen ohne Netz.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import urteile_finden as uf  # noqa: E402

BUND_XML = """<?xml version="1.0" encoding="UTF-8"?>
<dokument>
   <doknr>KORE000000001</doknr>
   <ecli>ECLI:DE:BGH:2023:010123UVIIZR1.22.0</ecli>
   <gertyp>BGH</gertyp>
   <spruchkoerper>7. Zivilsenat</spruchkoerper>
   <entsch-datum>20230101</entsch-datum>
   <aktenzeichen>VII ZR 1/22</aktenzeichen>
   <doktyp>Urteil</doktyp>
   <norm>§ 634 BGB, § 637 BGB</norm>
   <vorinstanz>vorgehend OLG Musterstadt, 1. Februar 2022, Az: 1 U 2/21<br/>vorgehend LG Musterstadt, 3. März 2021, Az: 4 O 5/20<br/>
   </vorinstanz>
   <titelzeile><dl><dt/><dd><p>Vorschuss auf Mängelbeseitigung</p></dd></dl></titelzeile>
   <leitsatz><dl><dt/><dd><p>Der Besteller kann einen Vorschuss auch dann verlangen, wenn er den Mangel noch nicht beseitigt hat.</p></dd></dl></leitsatz>
   <sonstosatz/>
   <tenor><div><dl><dt/><dd><p>Auf die Revision des Klägers wird das Urteil des Oberlandesgerichts aufgehoben.</p></dd></dl>
   <dl><dt/><dd><p>Die Sache wird zur neuen Verhandlung und Entscheidung an das Berufungsgericht zurückverwiesen.</p></dd></dl></div></tenor>
   <tatbestand><div><dl><dt><a name="rd_1">1</a></dt><dd><p>Der Kläger verlangt Vorschuss.</p></dd></dl></div></tatbestand>
   <entscheidungsgruende><div>
     <dl><dt><a name="rd_2">2</a></dt><dd><p>Das Berufungsgericht hat ausgeführt, ein Anspruch bestehe nicht.</p></dd></dl>
     <dl><dt><a name="rd_3">3</a></dt><dd><p>Das hält der rechtlichen Nachprüfung nicht stand.</p></dd></dl>
   </div></entscheidungsgruende>
</dokument>
"""


class BundLesen(unittest.TestCase):
    def setUp(self):
        self.text, self.kopf = uf.bund_lesen(BUND_XML)

    def test_randnummern_tragen_die_marke(self):
        self.assertIn("Randnummer 1 Der Kläger verlangt Vorschuss.", self.text)
        self.assertIn("Randnummer 3 Das hält der rechtlichen Nachprüfung nicht stand.", self.text)

    def test_abschnitte_sind_benannt_und_geordnet(self):
        stellen = [self.text.index(t) for t in ("LEITSATZ", "TENOR", "TATBESTAND", "ENTSCHEIDUNGSGRÜNDE")]
        self.assertEqual(stellen, sorted(stellen))
        self.assertIn("NICHT VOM GERICHT", self.text.split("LEITSATZ")[0])

    def test_leere_abschnitte_fehlen(self):
        self.assertNotIn("ORIENTIERUNGSSATZ", self.text)

    def test_kopf_nennt_vorinstanzen_und_art(self):
        kopf = "\n".join(self.kopf)
        self.assertIn("Entscheidungsart: Urteil", kopf)
        self.assertIn("vorgehend OLG Musterstadt, 1. Februar 2022, Az: 1 U 2/21; vorgehend LG Musterstadt", kopf)
        self.assertIn("§ 634 BGB", kopf)

    def test_metadaten_stehen_nicht_im_text(self):
        self.assertNotIn("KORE000000001", self.text)


class Verfahrensstand(unittest.TestCase):
    def test_zurueckverweisung_wird_gemeldet(self):
        text, _ = uf.bund_lesen(BUND_XML)
        hinweise = uf.verfahrensstand(text, "Urteil")
        self.assertTrue(any(h.startswith("Aufhebung und Zurückverweisung") for h in hinweise), hinweise)

    def test_revision_nicht_zugelassen(self):
        text = "Tenor: Die Berufung wird zurückgewiesen. " + "x " * 4000 + \
               "Die Revision war nicht zuzulassen, weil die Voraussetzungen nicht vorliegen."
        self.assertEqual(uf.verfahrensstand(text, "Urteil"),
                         ["Revision nach dem Schluss der Gründe nicht zugelassen"])

    def test_gruende_fuer_zulassung_liegen_nicht_vor(self):
        text = "Die Berufung wird zurückgewiesen. " + "x " * 4000 + \
               "Gründe für die Zulassung der Revision (§ 543 Abs. 2 ZPO) liegen nicht vor."
        self.assertIn("Revision nach dem Schluss der Gründe nicht zugelassen",
                      uf.verfahrensstand(text, "Urteil"))

    def test_revision_zugelassen(self):
        text = "Die Berufung wird zurückgewiesen. " + "x " * 4000 + \
               "Die Revision wird wegen grundsätzlicher Bedeutung zugelassen."
        hinweise = uf.verfahrensstand(text, "Urteil")
        self.assertTrue(any(h.startswith("Revision zugelassen") for h in hinweise), hinweise)

    def test_teilurteil_aus_der_entscheidungsart(self):
        hinweise = uf.verfahrensstand("Der Beklagte wird verurteilt …", "Teilurteil")
        self.assertTrue(hinweise and hinweise[0].startswith("Teilurteil"), hinweise)

    def test_gewoehnliches_endurteil_ohne_hinweis(self):
        self.assertEqual(uf.verfahrensstand("Die Klage wird abgewiesen. Gründe: …", "Urteil"), [])


class Gewicht(unittest.TestCase):
    def fund(self, gericht, art, leitsatz, stand):
        f = uf.Fund(gericht=gericht, datum="2020-01-01", aktenzeichen="1 U 1/19",
                    link="https://example.invalid", quelle="Test", grund="Test", region="Bund")
        f.art, f.leitsatz, f.stand, f.treffer = art, leitsatz, stand, 6
        uf.gewichten(f)
        return f

    def test_zugelassene_revision_senkt_das_gewicht_eines_olg(self):
        ohne = self.fund("OLG Musterstadt", "Urteil", True, [])
        mit = self.fund("OLG Musterstadt", "Urteil", True,
                        ["Revision zugelassen – der Streit kann beim Bundesgerichtshof weitergehen"])
        self.assertLess(mit.gewicht, ohne.gewicht)

    def test_bgh_mit_leitsatz_bleibt_trotz_zurueckverweisung_oben(self):
        ohne = self.fund("BGH 7. Zivilsenat", "Urteil", True, [])
        mit = self.fund("BGH 7. Zivilsenat", "Urteil", True,
                        ["Aufhebung und Zurückverweisung im Tenor – wer am Ende gewinnt, "
                         "ist mit dieser Entscheidung nicht entschieden"])
        self.assertEqual(mit.gewicht, ohne.gewicht)

    def test_nichtzulassungsbeschwerde_sinkt(self):
        ohne = self.fund("BGH 7. Zivilsenat", "Beschluss", False, [])
        mit = self.fund("BGH 7. Zivilsenat", "Beschluss", False,
                        ["Entscheidung über eine Nichtzulassungsbeschwerde – meist auf den "
                         "Einzelfall bezogen, selten eine Grundsatzaussage"])
        self.assertLess(mit.gewicht, ohne.gewicht)


class Kopf(unittest.TestCase):
    def test_zusatzzeilen_und_randnummernhinweis(self):
        kopf = uf.volltext_kopf("BGH", "2023-01-01", "VII ZR 1/22", "", "https://example.invalid",
                                "Test", False, "2026-01-01", ["Entscheidungsart: Urteil"])
        self.assertIn("Entscheidungsart: Urteil", kopf)
        self.assertIn("Jede Randnummer beginnt mit", kopf)

    def test_fehlende_randnummern_werden_gesagt(self):
        kopf = uf.volltext_kopf("LG", "2023-01-01", "1 O 1/22", "", "https://example.invalid",
                                "Test", False, "2026-01-01", randnummern=False)
        self.assertIn("trägt die Marke „Randnummer <n>“ nicht", kopf)
        self.assertNotIn("Jede Randnummer beginnt mit", kopf)


if __name__ == "__main__":
    unittest.main()
