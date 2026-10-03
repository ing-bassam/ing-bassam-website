# Beispielobjekte für den Abgleich mit der Bewertungssoftware (Phase 4)

Automatisch erzeugt von `tools/beispiele_rechnen.mjs` aus dem Rechenkern und den Marktdaten des Repositories. Stichtagsjahr für das Alter: 2026. Faktoren zum Stichtag 2024-12-31; Bodenrichtwert 2024-01-01. Die Adressen sind echte Berliner Adressen aus den offenen Daten; die Gebäudeangaben sind angenommen.

Zum Abgleich: Jede Zeile des Rechenwegs nennt Formel, Ergebnis und Rechtsgrundlage. Abweichungen zur Software deuten auf unterschiedliche Modellannahmen hin (siehe `MODELL-BERLIN.md`), nicht auf Rechenfehler – die Arithmetik ist über den Referenzfall A abgesichert.

## Beispiel 1 – freistehendes Einfamilienhaus, Johannisthal (Sachwertverfahren)

**Adresse:** Akeleiweg 1, 12487 Berlin (Johannisthal)

**Eingaben**

- freistehend, unterkellert, 1 Vollgeschoss, Dachgeschoss ausgebaut (NHK-Typ 1.01)
- Baujahr 1965, baulicher Zustand normal, Massivbau
- Brutto-Grundfläche 220 m² (angegeben)
- Grundstück 600 m²
- keine besonderen Nebenanlagen

**Modellparameter**

| Parameter | Wert |
| --- | --- |
| NHK-2010-Typ / Kostenkennwert Stufe 4 | 1.01 / 1.005 €/m² |
| Brutto-Grundfläche | 220 m² (angegeben) |
| Baupreisindex (2010 = 100) / Regionalfaktor | 184,7 / 1 |
| Gesamtnutzungsdauer / Alter / Restnutzungsdauer | 80 / 61 / 40 Jahre (Sachwertfaktoren 2025 (Stand 04.02.2026) S. 3–4) |
| Bodenrichtwert 01.01.2024 (Modell) / 01.01.2026 (aktuell) | 650 / 590 €/m² |
| Wohnlage / Altbezirk / SWF-Gruppe | mittel / Treptow / 1 |
| Sachwertfaktor Formel → angewendet | 0,8062 → 0,81 |

**Rechenweg**

| # | Schritt | Rechnung | Ergebnis | Grundlage |
| --- | --- | --- | --- | --- |
| 1 | Wohngebäude: Herstellungskosten 2010 | 220 m² × 1.005 €/m² | 221.100,00 € | § 36 Abs. 2 ImmoWertV (NHK × BGF, Zuschläge für nicht erfasste Bauteile), Anlage 4; ImmoWertA zu § 36, S. 36 |
| 2 | Wohngebäude: Herstellungskosten zum Stichtag | 221.100 € × 184,7 / 100 × Regionalfaktor 1 | 408.371,70 € | § 36 Abs. 2 Satz 4 und Abs. 3 ImmoWertV (Baupreisindex, Regionalfaktor); ImmoWertA zu § 36, S. 36 |
| 3 | Wohngebäude: Alterswertminderungsfaktor | Restnutzungsdauer 40 Jahre / Gesamtnutzungsdauer 80 Jahre | 0,5 | § 38 ImmoWertV (linear); ImmoWertA zu § 38, S. 37 |
| 4 | Wohngebäude: vorläufiger Sachwert der baulichen Anlage | 408.371,7 € × 0,5 | 204.185,85 € | § 36 Abs. 1 ImmoWertV |
| 5 | Summe vorläufige Sachwerte der baulichen Anlagen | 204.185,85 € | 204.185,85 € | § 35 Abs. 2 Nr. 1 ImmoWertV |
| 6 | Vorläufiger Sachwert der baulichen Außenanlagen und sonstigen Anlagen | Zeitwert nach Erfahrungssätzen | 0,00 € | § 37 ImmoWertV; ImmoWertA zu § 37, S. 36 |
| 7 | Bodenwert | 600 m² × 650 €/m² | 390.000,00 € | §§ 40 Abs. 2, 16 ImmoWertV; ImmoWertA zu § 40, S. 37 |
| 8 | Vorläufiger Sachwert des Grundstücks | 204.185,85 € + 0 € + 390.000 € | 594.185,85 € | § 35 Abs. 2 ImmoWertV; ImmoWertA zu § 35, S. 35 |
| 9 | Marktangepasster vorläufiger Sachwert | 594.185,85 € × Sachwertfaktor 0,81 | 481.290,54 € | § 35 Abs. 3, § 39, § 21 Abs. 3 ImmoWertV; ImmoWertA zu § 39, S. 37 |
| 10 | Sachwert des Grundstücks | 481.290,54 € + 0 € | 481.290,54 € | § 35 Abs. 4 ImmoWertV |
| 11 | Sachwert, gerundet | auf volle 1.000 € | 481.000,00 € | Wertermittlungspraxis |

**Zusammensetzung Sachwertfaktor**

| Bestandteil | Wert |
| --- | --- |
| Konstante | 1,398 |
| -0,00000028 × vorläufiger Sachwert 594.185,85 € | -0,166372 |
| -0,0002759 × 1.096 Tage (31.12.2021 bis 31.12.2024) | -0,302386 |
| Altbezirksgruppe 1 | 0 |
| Baujahresgruppe 1949–1970 | -0,123 |
| Gebäudeart freistehend | 0 |
| Bauzustand normal | 0 |
| Gebäudekonstruktion massiv | 0 |
| Stadträumliche Wohnlage mittel | 0 |
| Bauerrichtungsvertrag nicht_beurkundet | 0 |
| Summe (ungerundet) | 0,806242 |
| angewendet (gerundet) | 0,81 |

**Gültigkeitsprüfung**

| Größe | Wert | Bereich | Ergebnis |
| --- | --- | --- | --- |
| vorläufiger Sachwert des Grundstücks | 594.185,85 € | 289.845 – 1.114.060 € | innerhalb |
| Grundstücksfläche | 600 m² | 212 – 993 m² | innerhalb |
| Brutto-Grundfläche | 220 m² | 146 – 430 m² | innerhalb |
| Bodenrichtwert | 650 €/m² | 410 – 1.200 €/m² | innerhalb |
| NHK 2010 (Stufe 4) | 1.005 €/m² | 825 – 1.215 €/m² | innerhalb |

**Ergebnis: 481.000 € – Spanne 409.000 € bis 553.000 € (±15 %)**

## Beispiel 2 – Reihenmittelhaus, Mahlsdorf (Sachwertverfahren)

**Adresse:** Akazienallee 1, 12623 Berlin (Mahlsdorf)

**Eingaben**

- Reihenmittelhaus, nicht unterkellert, 2 Vollgeschosse, Dachgeschoss nicht ausgebaut (NHK-Typ 3.32)
- Baujahr 1998, baulicher Zustand gut, Massivbau
- Grundfläche nach Außenmaßen 65 m² → BGF abgeleitet
- Grundstück 300 m²
- besondere Nebenanlagen (Carport) 8.000 € Zeitwert

**Modellparameter**

| Parameter | Wert |
| --- | --- |
| NHK-2010-Typ / Kostenkennwert Stufe 4 | 3.32 / 840 €/m² |
| Brutto-Grundfläche | 182 m² (aus Grundfläche 65 m² × 2,8 Ebenen) |
| Baupreisindex (2010 = 100) / Regionalfaktor | 184,7 / 1 |
| Gesamtnutzungsdauer / Alter / Restnutzungsdauer | 80 / 28 / 55 Jahre (Sachwertfaktoren 2025 (Stand 04.02.2026) S. 3–4) |
| Bodenrichtwert 01.01.2024 (Modell) / 01.01.2026 (aktuell) | 540 / 490 €/m² |
| Wohnlage / Altbezirk / SWF-Gruppe | gut / Hellersdorf / 3 |
| Sachwertfaktor Formel → angewendet | 1,5897 → 1,59 |

**Rechenweg**

| # | Schritt | Rechnung | Ergebnis | Grundlage |
| --- | --- | --- | --- | --- |
| 1 | Wohngebäude: Herstellungskosten 2010 | 182 m² × 840 €/m² | 152.880,00 € | § 36 Abs. 2 ImmoWertV (NHK × BGF, Zuschläge für nicht erfasste Bauteile), Anlage 4; ImmoWertA zu § 36, S. 36 |
| 2 | Wohngebäude: Herstellungskosten zum Stichtag | 152.880 € × 184,7 / 100 × Regionalfaktor 1 | 282.369,36 € | § 36 Abs. 2 Satz 4 und Abs. 3 ImmoWertV (Baupreisindex, Regionalfaktor); ImmoWertA zu § 36, S. 36 |
| 3 | Wohngebäude: Alterswertminderungsfaktor | Restnutzungsdauer 55 Jahre / Gesamtnutzungsdauer 80 Jahre | 0,6875 | § 38 ImmoWertV (linear); ImmoWertA zu § 38, S. 37 |
| 4 | Wohngebäude: vorläufiger Sachwert der baulichen Anlage | 282.369,36 € × 0,6875 | 194.128,94 € | § 36 Abs. 1 ImmoWertV |
| 5 | Summe vorläufige Sachwerte der baulichen Anlagen | 194.128,94 € | 194.128,94 € | § 35 Abs. 2 Nr. 1 ImmoWertV |
| 6 | Vorläufiger Sachwert der baulichen Außenanlagen und sonstigen Anlagen | Zeitwert nach Erfahrungssätzen | 8.000,00 € | § 37 ImmoWertV; ImmoWertA zu § 37, S. 36 |
| 7 | Bodenwert | 300 m² × 540 €/m² | 162.000,00 € | §§ 40 Abs. 2, 16 ImmoWertV; ImmoWertA zu § 40, S. 37 |
| 8 | Vorläufiger Sachwert des Grundstücks | 194.128,94 € + 8.000 € + 162.000 € | 364.128,94 € | § 35 Abs. 2 ImmoWertV; ImmoWertA zu § 35, S. 35 |
| 9 | Marktangepasster vorläufiger Sachwert | 364.128,94 € × Sachwertfaktor 1,59 | 578.965,01 € | § 35 Abs. 3, § 39, § 21 Abs. 3 ImmoWertV; ImmoWertA zu § 39, S. 37 |
| 10 | Sachwert des Grundstücks | 578.965,01 € + 0 € | 578.965,01 € | § 35 Abs. 4 ImmoWertV |
| 11 | Sachwert, gerundet | auf volle 1.000 € | 579.000,00 € | Wertermittlungspraxis |

**Zusammensetzung Sachwertfaktor**

| Bestandteil | Wert |
| --- | --- |
| Konstante | 1,398 |
| -0,00000028 × vorläufiger Sachwert 364.128,94 € | -0,101956 |
| -0,0002759 × 1.096 Tage (31.12.2021 bis 31.12.2024) | -0,302386 |
| Altbezirksgruppe 3 | -0,105 |
| Baujahresgruppe 1991–2009 | 0,106 |
| Gebäudeart reihenmittelhaus | 0,341 |
| Bauzustand gut | 0,179 |
| Gebäudekonstruktion massiv | 0 |
| Stadträumliche Wohnlage gut | 0,075 |
| Bauerrichtungsvertrag nicht_beurkundet | 0 |
| Summe (ungerundet) | 1,589657 |
| angewendet (gerundet) | 1,59 |

**Gültigkeitsprüfung**

| Größe | Wert | Bereich | Ergebnis |
| --- | --- | --- | --- |
| vorläufiger Sachwert des Grundstücks | 364.128,94 € | 289.845 – 1.114.060 € | innerhalb |
| Grundstücksfläche | 300 m² | 212 – 993 m² | innerhalb |
| Brutto-Grundfläche | 182 m² | 146 – 430 m² | innerhalb |
| Bodenrichtwert | 540 €/m² | 410 – 1.200 €/m² | innerhalb |
| NHK 2010 (Stufe 4) | 840 €/m² | 825 – 1.215 €/m² | innerhalb |

**Hinweise**

- Die Brutto-Grundfläche wurde aus der Grundfläche abgeleitet (65 m² × 2,8 anrechenbare Ebenen ≈ 182 m²).

**Ergebnis: 579.000 € – Spanne 492.000 € bis 666.000 € (±15 %)**

## Beispiel 3 – Altbau-Mietwohnhaus mit Laden, Neukölln (Ertragswertverfahren)

**Adresse:** Anzengruberstraße 1, 12043 Berlin (Neukölln)

**Eingaben**

- Baujahr 1905, baulicher Zustand normal, vollständig mit Zentralheizung und Bädern
- Wohnen: 1.200 m², 16 Wohnungen, 9.000 €/Monat nettokalt (7,50 €/m²)
- Gewerbe (Laden): 200 m², 2.400 €/Monat nettokalt (12,00 €/m²)
- 4 offene Stellplätze, 200 €/Monat
- Grundstück 800 m², Geschossfläche oberirdisch 1.750 m² (GFZ 2,19)

**Modellparameter**

| Parameter | Wert |
| --- | --- |
| Ø Objektkaltmiete / gewerblicher Anteil | 8,29 €/m² / 20,69 % |
| Gebietsgruppe / Stadtlage / Altbezirk | City / West / Neukölln |
| Liegenschaftszinssatz Formel → angewendet | 3,529 % → 3,5 % |
| Alter / Restnutzungsdauer | 121 / 40 Jahre (Liegenschaftszinssätze 2025 (Stand 24.10.2025) S. 10 (Tabelle 2)) |
| Bodenrichtwert 01.01.2024 (Modell) / 01.01.2026 (aktuell) | 2.200 / 2.200 €/m² |
| GFZ Richtwertzone / Grundstück → Anpassungsfaktor | 2,5 / 2,19 → 0,8989 |

**Rechenweg**

| # | Schritt | Rechnung | Ergebnis | Grundlage |
| --- | --- | --- | --- | --- |
| 1 | Wohnen: Jahresrohertrag | 9.000 €/Monat × 12 | 108.000,00 € | § 31 Abs. 2 ImmoWertV (marktüblich erzielbare, hier tatsächliche Nettokaltmiete); ImmoWertA zu § 31, S. 33 |
| 2 | Gewerbe (Büro, Praxis, Laden): Jahresrohertrag | 2.400 €/Monat × 12 | 28.800,00 € | § 31 Abs. 2 ImmoWertV (marktüblich erzielbare, hier tatsächliche Nettokaltmiete); ImmoWertA zu § 31, S. 33 |
| 3 | Stellplätze: Jahresrohertrag | 200 €/Monat × 12 | 2.400,00 € | § 31 Abs. 2 ImmoWertV (marktüblich erzielbare, hier tatsächliche Nettokaltmiete); ImmoWertA zu § 31, S. 33 |
| 4 | Jahresrohertrag gesamt | 108.000 € + 28.800 € + 2.400 € | 139.200,00 € | § 31 Abs. 2 ImmoWertV |
| 5 | Verwaltungskosten Wohnen | 351 € × 16 Einheit(en) | 5.616,00 € | § 32 Abs. 1 Nr. 1, Abs. 2 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 6 | Verwaltungskosten Gewerbe (Büro, Praxis, Laden) | 3 % vom Rohertrag | 864,00 € | § 32 Abs. 1 Nr. 1, Abs. 2 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 7 | Verwaltungskosten Stellplätze | 3 % vom Rohertrag | 72,00 € | § 32 Abs. 1 Nr. 1, Abs. 2 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 8 | Instandhaltungskosten Wohnen | 13,8 €/m² × 1.200 m² | 16.560,00 € | § 32 Abs. 1 Nr. 2, Abs. 3 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 9 | Instandhaltungskosten Gewerbe (Büro, Praxis, Laden) | 13,8 €/m² × 200 m² | 2.760,00 € | § 32 Abs. 1 Nr. 2, Abs. 3 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 10 | Instandhaltungskosten Stellplätze | 52 € × 4 Einheit(en) | 208,00 € | § 32 Abs. 1 Nr. 2, Abs. 3 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 11 | Mietausfallwagnis Wohnen | 2 % vom Rohertrag | 2.160,00 € | § 32 Abs. 1 Nr. 3, Abs. 4 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 12 | Mietausfallwagnis Gewerbe (Büro, Praxis, Laden) | 4 % vom Rohertrag | 1.152,00 € | § 32 Abs. 1 Nr. 3, Abs. 4 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 13 | Mietausfallwagnis Stellplätze | 4 % vom Rohertrag | 96,00 € | § 32 Abs. 1 Nr. 3, Abs. 4 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 14 | Bewirtschaftungskosten gesamt | Verwaltungskosten 6.552 € + Instandhaltungskosten 19.528 € + Mietausfallwagnis 3.408 € + Nicht umlagefähige Betriebskosten 0 € | 29.488,00 € | § 32 Abs. 1 ImmoWertV |
| 15 | Jahresreinertrag | 139.200 € − 29.488 € | 109.712,00 € | § 31 Abs. 1 ImmoWertV; ImmoWertA zu § 31, S. 33 |
| 16 | Bodenwert | 800 m² × 2.200 €/m² × 0,8989 | 1.582.064,00 € | §§ 40 Abs. 2, 16 ImmoWertV; ImmoWertA zu § 40, S. 37 |
| 17 | Bodenwertverzinsungsbetrag | 1.582.064 € × 3,5 % | 55.372,24 € | § 28 Satz 1 Nr. 1 und Satz 2 ImmoWertV; ImmoWertA zu § 28, S. 31 |
| 18 | Reinertragsanteil der baulichen Anlagen | 109.712 € − 55.372,24 € | 54.339,76 € | § 28 Satz 1 Nr. 1 ImmoWertV |
| 19 | Restnutzungsdauer | vorgegeben | 40 Jahre | § 28 Satz 3 ImmoWertV |
| 20 | Barwertfaktor (Kapitalisierungsfaktor) | (qⁿ − 1) / (qⁿ · (q − 1)) mit q = 1,035, n = 40 | 21,3551 | § 34 Abs. 2 ImmoWertV; ImmoWertA zu § 34, S. 34 |
| 21 | Vorläufiger Ertragswert der baulichen Anlagen | 54.339,76 € × 21,3551 | 1.160.431,01 € | § 28 Satz 1 Nr. 1 ImmoWertV |
| 22 | Vorläufiger Ertragswert | 1.160.431,01 € + 1.582.064 € | 2.742.495,01 € | § 28 Satz 1 ImmoWertV; ImmoWertA zu § 28, S. 31 |
| 23 | Marktangepasster vorläufiger Ertragswert | 2.742.495,01 € × 1 | 2.742.495,01 € | § 7 Abs. 2 ImmoWertV; ImmoWertA zu § 7 |
| 24 | Ertragswert des Grundstücks | 2.742.495,01 € + 0 € | 2.742.495,01 € | § 27 Abs. 4 ImmoWertV |
| 25 | Ertragswert, gerundet | auf volle 1.000 € | 2.742.000,00 € | Wertermittlungspraxis |

**Zusammensetzung Liegenschaftszinssatz**

| Bestandteil | Wert |
| --- | --- |
| Konstante | 0,644 |
| 0,132 × Objektkaltmiete 8,29 €/m² | 1,09428 |
| 0,0013304 × 1.096 Tage (01.01.2022 bis 31.12.2024) | 1,458118 |
| Gebietsgruppe City | 0,167 |
| Gewerblicher Anteil 20,7 % × 0,008 | 0,16552 |
| Summe (ungerundet) | 3,528918 |
| angewendet (gerundet) | 3,5 |

**Gültigkeitsprüfung**

| Größe | Wert | Bereich | Ergebnis |
| --- | --- | --- | --- |
| Objektkaltmiete, Tabellenbereich (Min/Max) | 8,29 €/m² Monat | 4 – 20 €/m² Monat | innerhalb |
| durchschnittliche Objektkaltmiete (5–95 %) | 8,29 €/m² Monat | 5,6 – 12,1 €/m² Monat | innerhalb |
| gewerblicher Mietanteil | 20,69 % | 0 – 49,2 % | innerhalb |
| Grundstücksfläche | 800 m² | 364 – 2.341 m² | innerhalb |
| Wohn-/Nutzfläche | 1.400 m² | 407 – 3.318 m² | innerhalb |
| tatsächliche GFZ | 2,19 – | 0,53 – 4,42 – | innerhalb |
| Bodenrichtwert | 2.200 €/m² | 600 – 6.500 €/m² | innerhalb |
| Bodenwert je m² (GFZ-angepasst) | 1.978 €/m² | 613 – 8.490 €/m² | innerhalb |
| Alter | 121 Jahre | 30 – 141 Jahre | innerhalb |
| Restnutzungsdauer | 40 Jahre | 35 – 50 Jahre | innerhalb |

**Hinweise**

- Das Grundstück liegt in einem städtebaulichen Entwicklungsbereich; der Bodenrichtwert gilt dort nur eingeschränkt.

**Ergebnis: 2.742.000 € – Spanne 2.331.000 € bis 3.153.000 € (±15 %)**

## Beispiel 4 – Mietwohnhaus der 1960er, Köpenick (Ertragswertverfahren)

**Adresse:** Alt-Köpenick 1, 12555 Berlin (Köpenick)

**Eingaben**

- Baujahr 1964, baulicher Zustand normal
- Wohnen: 800 m², 12 Wohnungen, 5.600 €/Monat nettokalt (7,00 €/m²)
- 6 offene Stellplätze, 240 €/Monat
- Grundstück 700 m², Geschossfläche oberirdisch 1.050 m² (GFZ 1,50)

**Modellparameter**

| Parameter | Wert |
| --- | --- |
| Ø Objektkaltmiete / gewerblicher Anteil | 7,3 €/m² / 0 % |
| Gebietsgruppe / Stadtlage / Altbezirk | Südost / Ost / Köpenick |
| Liegenschaftszinssatz Formel → angewendet | 3,066 % → 3,1 % |
| Alter / Restnutzungsdauer | 62 / 40 Jahre (Liegenschaftszinssätze 2025 (Stand 24.10.2025) S. 11 (Tabelle 5)) |
| Bodenrichtwert 01.01.2024 (Modell) / 01.01.2026 (aktuell) | 1.100 / 1.100 €/m² |
| GFZ Richtwertzone / Grundstück → Anpassungsfaktor | 1,5 / 1,5 → 1 |

**Rechenweg**

| # | Schritt | Rechnung | Ergebnis | Grundlage |
| --- | --- | --- | --- | --- |
| 1 | Wohnen: Jahresrohertrag | 5.600 €/Monat × 12 | 67.200,00 € | § 31 Abs. 2 ImmoWertV (marktüblich erzielbare, hier tatsächliche Nettokaltmiete); ImmoWertA zu § 31, S. 33 |
| 2 | Stellplätze: Jahresrohertrag | 240 €/Monat × 12 | 2.880,00 € | § 31 Abs. 2 ImmoWertV (marktüblich erzielbare, hier tatsächliche Nettokaltmiete); ImmoWertA zu § 31, S. 33 |
| 3 | Jahresrohertrag gesamt | 67.200 € + 2.880 € | 70.080,00 € | § 31 Abs. 2 ImmoWertV |
| 4 | Verwaltungskosten Wohnen | 351 € × 12 Einheit(en) | 4.212,00 € | § 32 Abs. 1 Nr. 1, Abs. 2 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 5 | Verwaltungskosten Stellplätze | 3 % vom Rohertrag | 86,40 € | § 32 Abs. 1 Nr. 1, Abs. 2 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 6 | Instandhaltungskosten Wohnen | 13,8 €/m² × 800 m² | 11.040,00 € | § 32 Abs. 1 Nr. 2, Abs. 3 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 7 | Instandhaltungskosten Stellplätze | 52 € × 6 Einheit(en) | 312,00 € | § 32 Abs. 1 Nr. 2, Abs. 3 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 8 | Mietausfallwagnis Wohnen | 2 % vom Rohertrag | 1.344,00 € | § 32 Abs. 1 Nr. 3, Abs. 4 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 9 | Mietausfallwagnis Stellplätze | 4 % vom Rohertrag | 115,20 € | § 32 Abs. 1 Nr. 3, Abs. 4 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34 |
| 10 | Bewirtschaftungskosten gesamt | Verwaltungskosten 4.298,4 € + Instandhaltungskosten 11.352 € + Mietausfallwagnis 1.459,2 € + Nicht umlagefähige Betriebskosten 0 € | 17.109,60 € | § 32 Abs. 1 ImmoWertV |
| 11 | Jahresreinertrag | 70.080 € − 17.109,6 € | 52.970,40 € | § 31 Abs. 1 ImmoWertV; ImmoWertA zu § 31, S. 33 |
| 12 | Bodenwert | 700 m² × 1.100 €/m² | 770.000,00 € | §§ 40 Abs. 2, 16 ImmoWertV; ImmoWertA zu § 40, S. 37 |
| 13 | Bodenwertverzinsungsbetrag | 770.000 € × 3,1 % | 23.870,00 € | § 28 Satz 1 Nr. 1 und Satz 2 ImmoWertV; ImmoWertA zu § 28, S. 31 |
| 14 | Reinertragsanteil der baulichen Anlagen | 52.970,4 € − 23.870 € | 29.100,40 € | § 28 Satz 1 Nr. 1 ImmoWertV |
| 15 | Restnutzungsdauer | vorgegeben | 40 Jahre | § 28 Satz 3 ImmoWertV |
| 16 | Barwertfaktor (Kapitalisierungsfaktor) | (qⁿ − 1) / (qⁿ · (q − 1)) mit q = 1,031, n = 40 | 22,7456 | § 34 Abs. 2 ImmoWertV; ImmoWertA zu § 34, S. 34 |
| 17 | Vorläufiger Ertragswert der baulichen Anlagen | 29.100,4 € × 22,7456 | 661.906,06 € | § 28 Satz 1 Nr. 1 ImmoWertV |
| 18 | Vorläufiger Ertragswert | 661.906,06 € + 770.000 € | 1.431.906,06 € | § 28 Satz 1 ImmoWertV; ImmoWertA zu § 28, S. 31 |
| 19 | Marktangepasster vorläufiger Ertragswert | 1.431.906,06 € × 1 | 1.431.906,06 € | § 7 Abs. 2 ImmoWertV; ImmoWertA zu § 7 |
| 20 | Ertragswert des Grundstücks | 1.431.906,06 € + 0 € | 1.431.906,06 € | § 27 Abs. 4 ImmoWertV |
| 21 | Ertragswert, gerundet | auf volle 1.000 € | 1.432.000,00 € | Wertermittlungspraxis |

**Zusammensetzung Liegenschaftszinssatz**

| Bestandteil | Wert |
| --- | --- |
| Konstante | 0,644 |
| 0,132 × Objektkaltmiete 7,3 €/m² | 0,9636 |
| 0,0013304 × 1.096 Tage (01.01.2022 bis 31.12.2024) | 1,458118 |
| Gebietsgruppe Südost | 0 |
| Summe (ungerundet) | 3,065718 |
| angewendet (gerundet) | 3,1 |

**Gültigkeitsprüfung**

| Größe | Wert | Bereich | Ergebnis |
| --- | --- | --- | --- |
| Objektkaltmiete, Tabellenbereich (Min/Max) | 7,3 €/m² Monat | 4 – 20 €/m² Monat | innerhalb |
| durchschnittliche Objektkaltmiete (5–95 %) | 7,3 €/m² Monat | 5,6 – 12,1 €/m² Monat | innerhalb |
| gewerblicher Mietanteil | 0 % | 0 – 49,2 % | innerhalb |
| Grundstücksfläche | 700 m² | 364 – 2.341 m² | innerhalb |
| Wohn-/Nutzfläche | 800 m² | 407 – 3.318 m² | innerhalb |
| tatsächliche GFZ | 1,5 – | 0,53 – 4,42 – | innerhalb |
| Bodenrichtwert | 1.100 €/m² | 600 – 6.500 €/m² | innerhalb |
| Bodenwert je m² (GFZ-angepasst) | 1.100 €/m² | 613 – 8.490 €/m² | innerhalb |
| Alter | 62 Jahre | 30 – 141 Jahre | innerhalb |
| Restnutzungsdauer | 40 Jahre | 35 – 50 Jahre | innerhalb |

**Ergebnis: 1.432.000 € – Spanne 1.217.000 € bis 1.647.000 € (±15 %)**

## Beispiel 5 – Altbau in Prenzlauer Berg bei 9 €/m²: Liquidationsfall (zur Demonstration)

**Adresse:** Christburger Straße 1, 10405 Berlin (Prenzlauer Berg)

**Eingaben**

- Baujahr 1905, baulicher Zustand normal, vollständig mit Zentralheizung und Bädern
- Wohnen: 1.200 m², 16 Wohnungen, 10.800 €/Monat nettokalt (9,00 €/m²)
- Gewerbe (Laden): 150 m², 2.100 €/Monat nettokalt (14,00 €/m²)
- Grundstück 900 m², Geschossfläche oberirdisch 2.100 m² (GFZ 2,33)
- Bodenrichtwert 5.000 €/m²: Die Bodenwertverzinsung übersteigt den Reinertrag – der Rechner gibt bewusst keinen Wert aus, sondern den Hinweis auf eine Liquidationsbetrachtung.

**Ergebnis: kein Wert (liquidation)**

- Der Reinertrag deckt die Bodenwertverzinsung nicht. Das Gebäude trägt wirtschaftlich nicht mehr zum Wert bei; in solchen Fällen ist eine Liquidationsbetrachtung erforderlich (ImmoWertA zu § 28). Es wird kein Ertragswert ausgegeben.


