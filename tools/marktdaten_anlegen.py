#!/usr/bin/env python3
"""Legt daten/marktdaten.xlsx einmalig an – mit allen Werten des Berliner Modells.

Danach ist die Excel-Datei die Pflegedatei des Büros (siehe daten/ANLEITUNG.md);
dieses Skript dient nur dazu, sie bei Bedarf neu aufzubauen. Jede Zahl hier hat
ihre Fundstelle in fachliteratur/MODELL-BERLIN.md.

Aufruf:
    python tools/marktdaten_anlegen.py            schreibt daten/marktdaten.xlsx
    python tools/marktdaten_anlegen.py --erzwingen überschreibt eine vorhandene Datei
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:  # pragma: no cover
    sys.exit("openpyxl fehlt: python -m pip install openpyxl")

WURZEL = Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "daten" / "marktdaten.xlsx"

SWF = "Sachwertfaktoren 2025 (Stand 04.02.2026)"
LZ = "Liegenschaftszinssätze 2025 (Stand 24.10.2025)"
GFZW = "GFZ-Umrechnungskoeffizienten Wohnbauland 2004 (Stand 12.10.2022)"
GFZD = "GFZ-Umrechnungskoeffizienten Dienstleistung 2004 (Stand 12.10.2022)"
ANL4 = "ImmoWertV Anlage 4 (BGBl. I 2021 S. 2824 ff.)"
ANNAHME = "Annahme BIB – bitte prüfen (MODELL-BERLIN.md Abschnitt 7)"

# --------------------------------------------------------------------------
# Blatt Modellparameter
# --------------------------------------------------------------------------
MODELLPARAMETER = [
    ("Schlüssel", "Wert", "Einheit", "Beschreibung", "Quelle/Stand"),
    ("stichtag_faktoren", dt.date(2024, 12, 31), "Datum", "Wertermittlungsstichtag der Sachwertfaktoren und Liegenschaftszinssätze", f"{SWF} S. 1; {LZ} S. 1"),
    ("brw_stichtag_modell", dt.date(2024, 1, 1), "Datum", "Bodenrichtwert, mit dem gerechnet wird (Modellkonformität)", f"{SWF} S. 4; {LZ} S. 4"),
    ("brw_stichtag_aktuell", dt.date(2026, 1, 1), "Datum", "Aktueller Bodenrichtwert, nur zur Anzeige", "Geoportal Berlin, WFS brw2026"),
    ("gnd_wohnen", 80, "Jahre", "Gesamtnutzungsdauer Ein- und Zweifamilienhäuser, Mehrfamilienhäuser", f"{SWF} S. 3; ImmoWertV Anlage 1"),
    ("regionalfaktor", 1.0, "Faktor", "Regionalfaktor Berlin", f"{SWF} S. 3"),
    ("nhk_standardstufe", 4, "Stufe", "Feste Standardstufe der NHK 2010 im Berliner Modell", f"{SWF} S. 3"),
    ("nhk_baunebenkosten_prozent", 17, "%", "In den NHK 2010 für Ein-/Zweifamilienhäuser enthaltene Baunebenkosten (nur Information)", f"{ANL4} Fußnote 1"),
    ("zfh_korrekturfaktor", 1.0, "Faktor", "Anlage 4 nennt 1,05 für freistehende Zweifamilienhäuser; Berlin: keine Korrektur", f"{SWF} S. 3; {ANL4} Fußnote 2"),
    ("bpi_quartal", "IV. Quartal 2024", "Text", "Baupreisindex Neubau Wohngebäude einschl. Umsatzsteuer, Destatis", f"{SWF} S. 4"),
    ("bpi_2021", 130.8, "Index 2021=100", "Veröffentlichter Indexwert", f"{SWF} S. 4; Destatis GENESIS 61261-0002"),
    ("bpi_umbasierung", 1.4124, "Faktor", "Umbasierung von 2021=100 auf 2010=100", f"{SWF} S. 4"),
    ("bpi_2010", 184.7, "Index 2010=100", "Anzuwendender Baupreisindex (bpi_2021 × bpi_umbasierung, gerundet wie veröffentlicht)", f"{SWF} S. 4"),
    ("swf_rundung_nachkommastellen", 2, "Stellen", "Sachwertfaktor wird wie in den Tabellen gerundet angewendet", ANNAHME),
    ("lz_rundung_nachkommastellen", 1, "Stellen", "Liegenschaftszinssatz wird wie in den Tabellen gerundet angewendet", ANNAHME),
    ("barwertfaktor_nachkommastellen", 4, "Stellen", "Rundung Barwert-/Kapitalisierungsfaktor", "Wertermittlungspraxis; Referenzfall A"),
    ("alterswertminderung_nachkommastellen", 4, "Stellen", "Rundung Alterswertminderungsfaktor", "Wertermittlungspraxis; Referenzfall A"),
    ("ergebnis_rundung_euro", 1000, "€", "Endergebnis auf volle 1.000 € runden", "Wertermittlungspraxis; Referenzfall A"),
    ("spanne_prozent", 15, "%", "Breite der angezeigten Wertspanne (±)", f"{ANNAHME}; Streuung Kaufpreis/Sachwert 0,635–1,627 lt. {SWF} Tabelle 2"),
    ("wohnflaeche_anteil_vollgeschoss", 0.80, "Anteil", "Schätzung der BGF aus der Wohnfläche: Wohnfläche eines Vollgeschosses im Verhältnis zur Grundfläche nach Außenmaßen", f"{ANNAHME}; Erfahrungswert 70–80 % (Wandanteile, Treppe)"),
    ("wohnflaeche_anteil_dachgeschoss", 0.55, "Anteil", "Schätzung der BGF aus der Wohnfläche: Wohnfläche eines voll ausgebauten Dachgeschosses im Verhältnis zur Grundfläche", ANNAHME),
    ("bgf_anteil_dachgeschoss", 0.80, "Anteil", "Anrechenbare Dachgeschossfläche (nutzbar, Giebelhöhe > 1,50 m) im Verhältnis zur Grundfläche – für die Ableitung der BGF aus Grundfläche oder Wohnfläche", f"{ANNAHME}; BGF-Regeln {SWF} S. 3"),
    ("ertragswert_mindest_mieteinheiten", 4, "Anzahl", "Liegenschaftszinssätze gelten ab vier Mieteinheiten", f"{LZ} S. 1"),
    ("ertragswert_max_gewerbeanteil_prozent", 80, "%", "Gewerblicher Anteil am Nettojahresrohertrag höchstens", f"{LZ} S. 1"),
    ("ertragswert_baujahr_min", 1865, "Jahr", "Jüngstes Baujahr in der Ableitung", f"{LZ} S. 2"),
    ("gfz_w_formel", "K(GFZ) = (−25,191 + 311,62·GFZ − 24,879·GFZ²) / 498,533; gültig 0,8–5,0; auf GFZ 2,0 = 1,0000 basiert", "Text", "Hintergrund der Tabelle Wohn-04; der Rechner nutzt die Tabelle mit linearer Zwischenwertbildung", f"{GFZW} S. 2"),
    ("gfz_d_formel", "K(GFZ) = 0,2047·GFZ + 0,181; gültig 2,0–7,0; auf GFZ 4,0 = 1,0000 basiert", "Text", "Hintergrund der Tabelle Dienst-04", f"{GFZD} S. 2"),
    ("wohnlagen_datensatz", "Wohnlagen nach Adressen zum Berliner Mietspiegel 2024", "Text", "Quelle der automatischen Wohnlage je Adresse", "Geoportal Berlin, WFS wohnlagenadr2024"),
]

# --------------------------------------------------------------------------
# Blatt Sachwertfaktoren (Formel) und SWF_Korrekturen
# --------------------------------------------------------------------------
SACHWERTFAKTOREN = [
    ("Schlüssel", "Wert", "Beschreibung", "Quelle/Stand"),
    ("konstante", 1.398, "Konstante der Regressionsformel", f"{SWF} S. 8"),
    ("koeff_sachwert", -0.000000280, "je € vorläufiger Sachwert des Grundstücks", f"{SWF} S. 8"),
    ("koeff_tag", -0.0002759, "je Tag seit 31.12.2021", f"{SWF} S. 8"),
    ("tage", 1096, "Tage vom 31.12.2021 bis 31.12.2024 (fest; keine Fortschreibung)", f"{SWF} S. 8"),
    ("gruppe_1", 0, "Treptow, Lichtenberg, Charlottenburg, Spandau, Wilmersdorf, Zehlendorf, Steglitz, Pankow", f"{SWF} S. 5, 8"),
    ("gruppe_2", -0.062, "Tempelhof, Neukölln, Hohenschönhausen", f"{SWF} S. 5, 8"),
    ("gruppe_3", -0.105, "Köpenick, Weißensee, Reinickendorf, Marzahn, Hellersdorf", f"{SWF} S. 5, 9"),
    ("bauerrichtungsvertrag_standard", "nicht_beurkundet", "Annahme für Bestandsobjekte", f"{SWF} S. 10; {ANNAHME}"),
    ("wohnlage_sehr_gut_wie", "gut", "Für „sehr gut“ ist keine Korrektur veröffentlicht", ANNAHME),
]

SWF_KORREKTUREN = [("Merkmal", "Ausprägung", "von", "bis", "Korrektur", "Quelle/Stand")]
for von, bis, k in ((None, 1919, 0), (1920, 1948, -0.061), (1949, 1970, -0.123), (1971, 1990, 0),
                    (1991, 2009, 0.106), (2010, 2019, 0), (2020, None, 0)):
    SWF_KORREKTUREN.append(("baujahresgruppe", f"{von or 'bis'}–{bis or 'heute'}".replace("bis–", "bis "), von, bis, k, f"{SWF} S. 9"))
for merkmal, zeilen in (
    ("gebaeudeart", (("freistehend", 0), ("doppelhaushaelfte", 0.084), ("reihenendhaus", 0.201), ("reihenmittelhaus", 0.341))),
    ("bauzustand", (("gut", 0.179), ("normal", 0), ("schlecht", -0.141))),
    ("konstruktion", (("massiv", 0), ("fertighaus_massiv", 0), ("fertighaus_holz", -0.072))),
    ("wohnlage", (("einfach", -0.043), ("mittel", 0), ("gut", 0.075))),
    ("bauerrichtungsvertrag", (("beurkundet", -0.081), ("nicht_beurkundet", 0))),
):
    for auspraegung, k in zeilen:
        SWF_KORREKTUREN.append((merkmal, auspraegung, None, None, k, f"{SWF} S. 9–10"))
SWF_KORREKTUREN.append(("wohnlage", "sehr_gut", None, None, 0.075, f"{ANNAHME} – wie „gut“"))

# --------------------------------------------------------------------------
# Blatt Liegenschaftszinssaetze
# --------------------------------------------------------------------------
LIEGENSCHAFTSZINSSAETZE = [
    ("Schlüssel", "Wert", "Beschreibung", "Quelle/Stand"),
    ("konstante", 0.644, "Konstante der Regressionsformel (Ergebnis in %)", f"{LZ} S. 12"),
    ("koeff_miete", 0.132, "je €/m² durchschnittliche monatliche Objektkaltmiete (Wohn-/Nutzfläche)", f"{LZ} S. 12"),
    ("koeff_tag", 0.0013304, "je Tag seit 01.01.2022", f"{LZ} S. 12"),
    ("tage", 1096, "Tage vom 01.01.2022 bis 31.12.2024 (fest; keine Fortschreibung)", f"{LZ} S. 12"),
    ("zuschlag_suedost", 0, "Gebietsgruppe Südost", f"{LZ} S. 12"),
    ("zuschlag_suedwest", 0, "Gebietsgruppe Südwest", f"{LZ} S. 13"),
    ("zuschlag_nord", 0, "Gebietsgruppe Nord", f"{LZ} S. 13"),
    ("zuschlag_city", 0.167, "Gebietsgruppe City", f"{LZ} S. 14"),
    ("zuschlag_ost", 0.167, "Gebietsgruppe Ost", f"{LZ} S. 14"),
    ("zuschlag_west", 0.167, "Gebietsgruppe West", f"{LZ} S. 15"),
    ("altbezirk_reinickendorf", 0.2, "Korrektur Altbezirk Reinickendorf (Gebietsgruppe Nord)", f"{LZ} S. 13"),
    ("altbezirk_mitte", -0.6, "Korrektur Altbezirk Mitte (Gebietsgruppe City)", f"{LZ} S. 14"),
    ("altbezirk_charlottenburg", -0.3, "Korrektur Altbezirk Charlottenburg (Gebietsgruppe City)", f"{LZ} S. 14"),
    ("baujahr_1973_1990_west", 0.3, "Korrektur Baujahre 1973–1990 im Westteil (Stadtlage West)", f"{LZ} S. 15"),
    ("gewerbe_je_prozentpunkt", 0.008, "Korrektur je Prozentpunkt gewerblicher Anteil am Nettojahresrohertrag (+0,08 je 10 %)", f"{LZ} S. 15"),
    ("marktanpassungsfaktor", 1.0, "Die Zinssätze sind aus Kaufpreisen abgeleitet; keine weitere Marktanpassung", f"{LZ} S. 1 (Nr. 4)"),
]

# --------------------------------------------------------------------------
# Blatt Bewirtschaftungskosten
# --------------------------------------------------------------------------
BEWIRTSCHAFTUNGSKOSTEN = [
    ("Position", "Nutzung", "Wert", "Einheit", "Quelle/Stand"),
    ("instandhaltung", "wohnen", 13.80, "€ je m² Wohnfläche und Jahr", f"{LZ} S. 9"),
    ("instandhaltung", "garage", 104, "€ je Platz und Jahr", f"{LZ} S. 9"),
    ("instandhaltung", "stellplatz", 52, "€ je Platz und Jahr (offener Wagenabstellplatz)", f"{LZ} S. 9"),
    ("instandhaltung", "gewerbe", 100, "% des Wohnansatzes je m² Nutzfläche (Büro, Praxis, Laden)", f"{LZ} S. 9; ImmoWertV Anlage 3"),
    ("instandhaltung", "nebennutzung", 30, "% des Wohnansatzes je m² (Lager, Werkstatt im Keller)", f"{LZ} S. 9; ImmoWertV Anlage 3"),
    ("verwaltung", "wohnen", 351, "€ je Wohnung und Jahr", f"{LZ} S. 9"),
    ("verwaltung", "gewerbe", 3, "% des Mietertrags", f"{LZ} S. 9"),
    ("verwaltung", "sonstiges", 3, "% des Mietertrags (Stellplätze, Garagen)", f"{LZ} S. 9"),
    ("mietausfallwagnis", "wohnen", 2, "% der Nettokaltmiete", f"{LZ} S. 9"),
    ("mietausfallwagnis", "gewerbe", 4, "% der Nettokaltmiete", f"{LZ} S. 9"),
    ("mietausfallwagnis", "sonstiges", 4, "% der Nettokaltmiete", f"{LZ} S. 9"),
    ("betriebskosten", "alle", 0, "€ – kein Ansatz im Berliner Modell", f"{LZ} S. 8–9 (keine Position)"),
    ("indexierung", "alle", "VPI (2020=100): Oktober 2001 = 77,1 → Oktober 2023 = 117,8", "Text", f"{LZ} S. 9; Destatis GENESIS 61111-0002"),
]

# --------------------------------------------------------------------------
# Blatt RND – Restnutzungsdauer nach Baujahr/Baualter und Bauzustand
# --------------------------------------------------------------------------
BAUALTER_SW = [(0, 2, 80, 75, 70), (3, 7, 75, 70, 65), (8, 12, 70, 65, 60), (13, 17, 65, 60, 55), (18, 22, 60, 55, 50),
               (23, 27, 55, 50, 45), (28, 32, 55, 45, 40), (33, 37, 55, 40, 35), (38, 42, 55, 40, 30), (43, 47, 55, 40, 25),
               (48, 52, 55, 40, 25), (53, 57, 55, 40, 25), (58, None, 55, 40, 25)]
BAUALTER_EW = [(0, 2, 80, None, None), (3, 7, 75, 70, None)] + BAUALTER_SW[2:]
RND = [("Verfahren", "Regel", "von", "bis", "gut", "normal", "schlecht", "Quelle/Stand")]
RND.append(("sachwert", "baujahr", None, 1948, 55, 40, 25, f"{SWF} S. 3"))
RND += [("sachwert", "baualter", v, b, g, n, s, f"{SWF} S. 3–4") for v, b, g, n, s in BAUALTER_SW]
RND.append(("ertragswert", "baujahr", None, 1948, 55, 40, 25, f"{LZ} S. 10 (Tabelle 2)"))
RND.append(("ertragswert", "abschlag_altbau_teilweise", None, 1918, -5, -5, -5, f"{LZ} S. 10 (Tabelle 3): vollständig mit Zentralheizung oder Bädern"))
RND.append(("ertragswert", "abschlag_altbau_ohne", None, 1918, -10, -10, -10, f"{LZ} S. 10 (Tabelle 3): weder Zentralheizung noch Bäder vollständig"))
RND.append(("ertragswert", "abschlag_zwischenkrieg_ohne_zh", 1919, 1948, -5, -5, -5, f"{LZ} S. 10 (Tabelle 4): nicht vollständig mit Zentralheizung"))
RND += [("ertragswert", "baualter", v, b, g, n, s, f"{LZ} S. 11 (Tabelle 5)") for v, b, g, n, s in BAUALTER_EW]

# --------------------------------------------------------------------------
# Blatt NHK2010 – Kostenkennwerte Ein-/Zweifamilienhäuser (Anlage 4 ImmoWertV, Grafik)
# --------------------------------------------------------------------------
NHK_BLOECKE = [
    # (Typ-Zehner, Keller, Geschosse, Dach, Stufen 1–5 für freistehend / Doppel+Reihenend / Reihenmittel)
    ("1.01", "2.01", "3.01", "unterkellert", "KG+EG", "voll_ausgebaut", (655, 725, 835, 1005, 1260), (615, 685, 785, 945, 1180), (575, 640, 735, 885, 1105)),
    ("1.02", "2.02", "3.02", "unterkellert", "KG+EG", "nicht_ausgebaut", (545, 605, 695, 840, 1050), (515, 570, 655, 790, 985), (480, 535, 615, 740, 925)),
    ("1.03", "2.03", "3.03", "unterkellert", "KG+EG", "flachdach", (705, 785, 900, 1085, 1360), (665, 735, 845, 1020, 1275), (620, 690, 795, 955, 1195)),
    ("1.11", "2.11", "3.11", "unterkellert", "KG+EG+OG", "voll_ausgebaut", (655, 725, 835, 1005, 1260), (615, 685, 785, 945, 1180), (575, 640, 735, 885, 1105)),
    ("1.12", "2.12", "3.12", "unterkellert", "KG+EG+OG", "nicht_ausgebaut", (570, 635, 730, 880, 1100), (535, 595, 685, 825, 1035), (505, 560, 640, 775, 965)),
    ("1.13", "2.13", "3.13", "unterkellert", "KG+EG+OG", "flachdach", (665, 740, 850, 1025, 1285), (625, 695, 800, 965, 1205), (585, 650, 750, 905, 1130)),
    ("1.21", "2.21", "3.21", "nicht_unterkellert", "EG", "voll_ausgebaut", (790, 875, 1005, 1215, 1515), (740, 825, 945, 1140, 1425), (695, 770, 885, 1065, 1335)),
    ("1.22", "2.22", "3.22", "nicht_unterkellert", "EG", "nicht_ausgebaut", (585, 650, 745, 900, 1125), (550, 610, 700, 845, 1055), (515, 570, 655, 790, 990)),
    ("1.23", "2.23", "3.23", "nicht_unterkellert", "EG", "flachdach", (920, 1025, 1180, 1420, 1775), (865, 965, 1105, 1335, 1670), (810, 900, 1035, 1250, 1560)),
    ("1.31", "2.31", "3.31", "nicht_unterkellert", "EG+OG", "voll_ausgebaut", (720, 800, 920, 1105, 1385), (675, 750, 865, 1040, 1300), (635, 705, 810, 975, 1215)),
    ("1.32", "2.32", "3.32", "nicht_unterkellert", "EG+OG", "nicht_ausgebaut", (620, 690, 790, 955, 1190), (580, 645, 745, 895, 1120), (545, 605, 695, 840, 1050)),
    ("1.33", "2.33", "3.33", "nicht_unterkellert", "EG+OG", "flachdach", (785, 870, 1000, 1205, 1510), (735, 820, 940, 1135, 1415), (690, 765, 880, 1060, 1325)),
]
NHK2010 = [("Typ", "Gebäudestellung", "Keller", "Geschosse", "Dachgeschoss", "Stufe_1", "Stufe_2", "Stufe_3", "Stufe_4", "Stufe_5", "Quelle/Stand")]
for t1, t2, t3, keller, geschosse, dach, s1, s2, s3 in NHK_BLOECKE:
    for typ, stellung, stufen in ((t1, "freistehend", s1), (t2, "doppelhaus_reihenend", s2), (t3, "reihenmittel", s3)):
        NHK2010.append((typ, stellung, keller, geschosse, dach, *stufen, f"{ANL4}, Tabelle 1 (Grafik), einschl. 17 % Baunebenkosten"))

# --------------------------------------------------------------------------
# Blatt GFZ_Koeffizienten
# --------------------------------------------------------------------------
GFZ_W = [0.4176, 0.4716, 0.5246, 0.5767, 0.6277, 0.6777, 0.7268, 0.7748, 0.8218, 0.8679, 0.9129, 0.9570, 1.0000,
         1.0420, 1.0831, 1.1231, 1.1622, 1.2003, 1.2373, 1.2734, 1.3084, 1.3425, 1.3756, 1.4076, 1.4387, 1.4688,
         1.4978, 1.5259, 1.5530, 1.5791, 1.6041, 1.6282, 1.6513, 1.6734, 1.6945, 1.7146, 1.7336, 1.7517, 1.7688,
         1.7849, 1.8000, 1.8141, 1.8272]                                   # GFZ 0,8 … 5,0
GFZ_D = [0.5906, 0.6111, 0.6316, 0.6520, 0.6725, 0.6930, 0.7134, 0.7339, 0.7544, 0.7749, 0.7953, 0.8158, 0.8363,
         0.8567, 0.8772, 0.8977, 0.9181, 0.9386, 0.9591, 0.9795, 1.0000, 1.0205, 1.0409, 1.0614, 1.0819, 1.1023,
         1.1228, 1.1433, 1.1637, 1.1842, 1.2047, 1.2251, 1.2456, 1.2661, 1.2866, 1.3070, 1.3275, 1.3480, 1.3684,
         1.3889, 1.4094, 1.4298, 1.4503, 1.4708, 1.4912, 1.5117, 1.5322, 1.5526, 1.5731, 1.5936, 1.6140]  # GFZ 2,0 … 7,0
GFZ_KOEFFIZIENTEN = [("Tabelle", "GFZ", "Koeffizient", "Quelle/Stand")]
GFZ_KOEFFIZIENTEN += [("wohn04", round(0.8 + i / 10, 1), k, f"{GFZW} S. 1") for i, k in enumerate(GFZ_W)]
GFZ_KOEFFIZIENTEN += [("dienst04", round(2.0 + i / 10, 1), k, f"{GFZD} S. 1") for i, k in enumerate(GFZ_D)]
assert len(GFZ_W) == 43 and len(GFZ_D) == 51

# --------------------------------------------------------------------------
# Blatt Ortsteile – Tabelle 1 der Liegenschaftszinssätze 2025 (S. 5–8)
# --------------------------------------------------------------------------
SWF_GRUPPE = {**{a: 1 for a in ("Treptow", "Lichtenberg", "Charlottenburg", "Spandau", "Wilmersdorf", "Zehlendorf", "Steglitz", "Pankow")},
              **{a: 2 for a in ("Tempelhof", "Neukölln", "Hohenschönhausen")},
              **{a: 3 for a in ("Köpenick", "Weißensee", "Reinickendorf", "Marzahn", "Hellersdorf")}}
ORTSTEILE_ROH = [
    # (Bezirk-Nr, Bezirk, Altbezirk, [ (Ortsteil, Gebietsgruppe, Stadtlage) ... ])
    ("01", "Mitte", "Mitte", [("Mitte", "City", "Ost")]),
    ("01", "Mitte", "Tiergarten", [("Moabit", "City", "West"), ("Hansaviertel", "City", "West"), ("Tiergarten", "City", "West")]),
    ("01", "Mitte", "Wedding", [("Wedding", "Nord", "West"), ("Gesundbrunnen", "Nord", "West")]),
    ("02", "Friedrichshain-Kreuzberg", "Friedrichshain", [("Friedrichshain", "City", "Ost")]),
    ("02", "Friedrichshain-Kreuzberg", "Kreuzberg", [("Kreuzberg", "City", "West")]),
    ("03", "Pankow", "Prenzlauer Berg", [("Prenzlauer Berg", "City", "Ost")]),
    ("03", "Pankow", "Weißensee", [("Weißensee", "Nord", "Ost"), ("Blankenburg", "Nord", "Ost"), ("Heinersdorf", "Nord", "Ost"), ("Karow", "Nord", "Ost"), ("Stadtrandsiedlung Malchow", "Nord", "Ost")]),
    ("03", "Pankow", "Pankow", [("Pankow", "Nord", "Ost"), ("Blankenfelde", "Nord", "Ost"), ("Buch", "Nord", "Ost"), ("Französisch Buchholz", "Nord", "Ost"), ("Niederschönhausen", "Nord", "Ost"), ("Rosenthal", "Nord", "Ost"), ("Wilhelmsruh", "Nord", "Ost")]),
    ("04", "Charlottenburg-Wilmersdorf", "Charlottenburg", [("Charlottenburg", "City", "West"), ("Westend", "Südwest", "West"), ("Charlottenburg-Nord", "Nord", "West")]),
    ("04", "Charlottenburg-Wilmersdorf", "Wilmersdorf", [("Wilmersdorf", "City", "West"), ("Schmargendorf", "Südwest", "West"), ("Grunewald", "Südwest", "West"), ("Halensee", "City", "West")]),
    ("05", "Spandau", "Spandau", [(o, "West", "West") for o in ("Spandau", "Haselhorst", "Siemensstadt", "Staaken", "Gatow", "Kladow", "Hakenfelde", "Falkenhagener Feld", "Wilhelmstadt")]),
    ("06", "Steglitz-Zehlendorf", "Steglitz", [(o, "Südwest", "West") for o in ("Steglitz", "Lichterfelde", "Lankwitz")]),
    ("06", "Steglitz-Zehlendorf", "Zehlendorf", [(o, "Südwest", "West") for o in ("Zehlendorf", "Dahlem", "Nikolassee", "Wannsee", "Schlachtensee")]),
    ("07", "Tempelhof-Schöneberg", "Schöneberg", [("Schöneberg", "City", "West"), ("Friedenau", "City", "West")]),
    ("07", "Tempelhof-Schöneberg", "Tempelhof", [("Tempelhof", "City", "West"), ("Mariendorf", "Südost", "West"), ("Marienfelde", "Südost", "West"), ("Lichtenrade", "Südost", "West")]),
    ("08", "Neukölln", "Neukölln", [("Neukölln", "City", "West"), ("Britz", "Südost", "West"), ("Buckow", "Südost", "West"), ("Rudow", "Südost", "West"), ("Gropiusstadt", "Südost", "West")]),
    ("09", "Treptow-Köpenick", "Treptow", [(o, "Südost", "Ost") for o in ("Alt-Treptow", "Plänterwald", "Baumschulenweg", "Johannisthal", "Niederschöneweide", "Altglienicke", "Adlershof", "Bohnsdorf")]),
    ("09", "Treptow-Köpenick", "Köpenick", [(o, "Südost", "Ost") for o in ("Oberschöneweide", "Köpenick", "Friedrichshagen", "Rahnsdorf", "Grünau", "Müggelheim", "Schmöckwitz")]),
    ("10", "Marzahn-Hellersdorf", "Marzahn", [("Marzahn", "Ost", "Ost"), ("Biesdorf", "Ost", "Ost")]),
    ("10", "Marzahn-Hellersdorf", "Hellersdorf", [("Kaulsdorf", "Ost", "Ost"), ("Mahlsdorf", "Ost", "Ost"), ("Hellersdorf", "Ost", "Ost")]),
    ("11", "Lichtenberg", "Lichtenberg", [(o, "Ost", "Ost") for o in ("Friedrichsfelde", "Karlshorst", "Lichtenberg", "Fennpfuhl", "Rummelsburg")]),
    ("11", "Lichtenberg", "Hohenschönhausen", [(o, "Ost", "Ost") for o in ("Falkenberg", "Malchow", "Wartenberg", "Neu-Hohenschönhausen", "Alt-Hohenschönhausen")]),
    ("12", "Reinickendorf", "Reinickendorf", [(o, "Nord", "West") for o in ("Reinickendorf", "Tegel", "Konradshöhe", "Heiligensee", "Frohnau", "Hermsdorf", "Waidmannslust", "Lübars", "Wittenau", "Märkisches Viertel", "Borsigwalde")]),
]
ORTSTEILE = [("Bezirk_Nr", "Bezirk", "Altbezirk", "Ortsteil", "Gebietsgruppe", "Stadtlage", "SWF_Gruppe", "Quelle/Stand")]
for nr, bezirk, altbezirk, liste in ORTSTEILE_ROH:
    for ortsteil, gruppe, lage in liste:
        quelle = f"{LZ} S. 5–8 (Tabelle 1)"
        if ortsteil == "Tiergarten":
            quelle += "; dort als „Tiergarten-Süd“ geführt"
        if ortsteil == "Staaken":
            quelle += "; West-Staaken (ehem. Ostteil) hat dort Stadtlage Ost – im Adressdatensatz nicht unterscheidbar"
        ORTSTEILE.append((nr, bezirk, altbezirk, ortsteil, gruppe, lage, SWF_GRUPPE.get(altbezirk), quelle))
assert len(ORTSTEILE) - 1 == 97, len(ORTSTEILE) - 1

# --------------------------------------------------------------------------
# Blatt Gueltigkeit – 5 %- bis 95 %-Perzentile der Ableitung
# --------------------------------------------------------------------------
GUELTIGKEIT = [("Verfahren", "Größe", "Schlüssel", "Min", "Max", "Einheit", "Quelle/Stand")]
GUELTIGKEIT += [("sachwert",) + z + (f"{SWF} S. 6–7 (Tabellen 2–3)",) for z in (
    ("vorläufiger Sachwert des Grundstücks", "vorlaeufiger_sachwert", 289845, 1114060, "€"),
    ("Grundstücksfläche", "grundstuecksflaeche", 212, 993, "m²"),
    ("Brutto-Grundfläche", "bgf", 146, 430, "m²"),
    ("Bodenrichtwert", "brw", 410, 1200, "€/m²"),
    ("NHK 2010 (Stufe 4)", "nhk", 825, 1215, "€/m²"),
    ("tatsächliche GFZ", "gfz", 0.10, 0.54, "–"),
)]
GUELTIGKEIT += [("ertragswert",) + z + (f"{LZ} S. 16 (Tabellen 12–14)",) for z in (
    ("durchschnittliche Objektkaltmiete (5–95 %)", "objektmiete", 5.60, 12.10, "€/m² Monat"),
    ("Objektkaltmiete, Tabellenbereich (Min/Max)", "objektmiete_tabelle", 4.00, 20.00, "€/m² Monat"),
    ("gewerblicher Mietanteil", "gewerbeanteil", 0, 49.2, "%"),
    ("Grundstücksfläche", "grundstuecksflaeche", 364, 2341, "m²"),
    ("Wohn-/Nutzfläche", "wohn_nutzflaeche", 407, 3318, "m²"),
    ("tatsächliche GFZ", "gfz", 0.53, 4.42, "–"),
    ("Bodenrichtwert", "brw", 600, 6500, "€/m²"),
    ("Bodenwert je m² (GFZ-angepasst)", "bodenwert_m2", 613, 8490, "€/m²"),
    ("Alter", "alter", 30, 141, "Jahre"),
    ("Restnutzungsdauer", "rnd", 35, 50, "Jahre"),
)]

BAUPREISINDEX = [
    ("Jahr", "Quartal", "Index_2021", "Index_2010", "Verwendung", "Quelle/Stand"),
    (2024, "IV", 130.8, 184.7, "Sachwertfaktoren 2025 (anzuwendender Wert)", f"{SWF} S. 4; Destatis GENESIS 61261-0002"),
]

QUELLEN = [
    ("Kürzel", "Dokument", "Link", "Quelle/Stand"),
    ("SWF 2025", "Sachwertfaktoren 2025 zum Stichtag 31.12.2024, Gutachterausschuss Berlin", "https://www.berlin.de/gutachterausschuss/_assets/amarktinformationen/adaten-zur-wertermittlung/05-03-010-2500.pdf", "Stand 04.02.2026"),
    ("LZ 2025", "Liegenschaftszinssätze 2025 zum Stichtag 31.12.2024, Gutachterausschuss Berlin", "https://www.berlin.de/gutachterausschuss/_assets/amarktinformationen/adaten-zur-wertermittlung/05-02-010-2500.pdf", "Stand 24.10.2025"),
    ("GFZ-W", "GFZ-Umrechnungskoeffizienten Wohnbauland 2004", "https://www.berlin.de/gutachterausschuss/_assets/amarktinformationen/adaten-zur-wertermittlung/05-01-010-0400.pdf", "Stand 12.10.2022"),
    ("GFZ-D", "GFZ-Umrechnungskoeffizienten Dienstleistung/Büro 2004", "https://www.berlin.de/gutachterausschuss/_assets/amarktinformationen/adaten-zur-wertermittlung/05-01-020-0400.pdf", "Stand 12.10.2022"),
    ("ImmoWertV", "Immobilienwertermittlungsverordnung vom 14.07.2021", "https://www.gesetze-im-internet.de/immowertv_2022/", "BGBl. I 2021 S. 2805"),
    ("ImmoWertA", "Muster-Anwendungshinweise zur ImmoWertV", "https://www.bmwsb.bund.de/ImmoWertA", "20.09.2023"),
    ("BRW", "Bodenrichtwerte Berlin (WFS brw2024, brw2026)", "https://gdi.berlin.de/services/wfs/brw2024", "Stichtage 01.01.2024 / 01.01.2026"),
    ("Wohnlagen", "Wohnlagen nach Adressen zum Berliner Mietspiegel 2024", "https://gdi.berlin.de/services/wfs/wohnlagenadr2024", "Stand 31.07.2024"),
    ("Adressen", "Adressen Berlin (WFS adressen_berlin)", "https://gdi.berlin.de/services/wfs/adressen_berlin", "laufend"),
    ("Destatis BPI", "Preisindizes für die Bauwirtschaft, Tabelle 61261-0002", "https://www-genesis.destatis.de/datenbank/online/statistic/61261/table/61261-0002", "vierteljährlich"),
]

BLAETTER = [
    ("Modellparameter", MODELLPARAMETER), ("Sachwertfaktoren", SACHWERTFAKTOREN), ("SWF_Korrekturen", SWF_KORREKTUREN),
    ("Liegenschaftszinssaetze", LIEGENSCHAFTSZINSSAETZE), ("Bewirtschaftungskosten", BEWIRTSCHAFTUNGSKOSTEN), ("RND", RND),
    ("NHK2010", NHK2010), ("GFZ_Koeffizienten", GFZ_KOEFFIZIENTEN), ("Ortsteile", ORTSTEILE), ("Gueltigkeit", GUELTIGKEIT),
    ("Baupreisindex", BAUPREISINDEX), ("Quellen", QUELLEN),
]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--erzwingen", action="store_true")
    a = p.parse_args()
    if ZIEL.exists() and not a.erzwingen:
        print(f"{ZIEL.relative_to(WURZEL)} gibt es schon – mit --erzwingen überschreiben.")
        return 1

    wb = Workbook()
    wb.remove(wb.active)
    kopf = Font(bold=True)
    fuellung = PatternFill("solid", fgColor="E0DDD5")
    for name, zeilen in BLAETTER:
        ws = wb.create_sheet(name)
        for zeile in zeilen:
            ws.append(list(zeile))
        for zelle in ws[1]:
            zelle.font = kopf
            zelle.fill = fuellung
            zelle.alignment = Alignment(vertical="top", wrap_text=True)
        ws.freeze_panes = "A2"
        for spalte in range(1, ws.max_column + 1):
            breite = max(len(str(ws.cell(row=r, column=spalte).value or "")) for r in range(1, ws.max_row + 1))
            ws.column_dimensions[get_column_letter(spalte)].width = min(max(10, breite + 2), 70)
        for zeile in ws.iter_rows(min_row=2):
            for zelle in zeile:
                if isinstance(zelle.value, dt.date):
                    zelle.number_format = "DD.MM.YYYY"
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ZIEL)
    print(f"Geschrieben: {ZIEL.relative_to(WURZEL)} ({len(BLAETTER)} Blätter)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
