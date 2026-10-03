# Berliner Modell für den Wertrechner (Modellkonformität nach § 10 ImmoWertV)

Der Rechner darf die Berliner Sachwertfaktoren und Liegenschaftszinssätze nur
anwenden, wenn er **genau so rechnet, wie der Gutachterausschuss sie abgeleitet
hat** (§ 10 ImmoWertV; ImmoWertA zu § 10). Diese Datei hält jeden Modellparameter
mit Fundstelle fest. Sie ist die verbindliche Vorgabe für `wertrechner/rechenkern.js`
und für die Zahlen in `daten/marktdaten.xlsx`. Weicht etwas ab, ist das Ergebnis
falsch – auch wenn jede Formel für sich stimmt.

Quellen (alle in diesem Ordner, Einzelheiten in `README.md`):

| Kürzel | Dokument | Stand |
|---|---|---|
| **SWF 2025** | Gutachterausschuss Berlin, *Sachwertfaktoren 2025* zum Stichtag 31.12.2024 (Amtsblatt Nr. 29 vom 11.07.2025, S. 1852 ff.), `Berlin-Sachwertfaktoren-2025.pdf` | 04.02.2026 |
| **LZ 2025** | Gutachterausschuss Berlin, *Liegenschaftszinssätze 2025* zum Stichtag 31.12.2024 (Amtsblatt Nr. 39 vom 19.09.2025, S. 2477 ff.), `Berlin-Liegenschaftszinssaetze-2025.pdf` | 24.10.2025 |
| **GFZ-W** | GFZ-Umrechnungskoeffizienten für Wohnbauland 2004 (Wohn-04), `Berlin-GFZ-Umrechnungskoeffizienten-Wohnbauland-2004.pdf` | 12.10.2022 |
| **GFZ-D** | GFZ-Umrechnungskoeffizienten für Dienstleistungs- und Büronutzung 2004 (Dienst-04), `Berlin-GFZ-Umrechnungskoeffizienten-Dienstleistung-2004.pdf` | 12.10.2022 |
| **ImmoWertV** | Immobilienwertermittlungsverordnung vom 14.07.2021 (BGBl. I S. 2805), `ImmoWertV-2021.pdf` | in Kraft seit 01.01.2022 |
| **ImmoWertA** | Muster-Anwendungshinweise zur ImmoWertV, Fachkommission Städtebau 20.09.2023, `ImmoWertA-2023.pdf` | 2023 |

Seitenangaben beziehen sich auf die Seitenzählung der jeweiligen PDF-Datei.

---

## 1 Gemeinsame Grundlagen

| Parameter | Ansatz | Fundstelle |
|---|---|---|
| Wertermittlungsstichtag der Faktoren | **31.12.2024**. Beide Faktorensätze gelten zu diesem Stichtag; eine deutliche Marktentwicklung danach ist nicht enthalten. Der Rechner weist den Stichtag aus und extrapoliert den Zeitterm der Formeln **nicht** über den 31.12.2024 hinaus. | SWF 2025 S. 1, 8; LZ 2025 S. 1 |
| Bodenrichtwert-Stichtag | **01.01.2024** – ausdrücklich „im Rahmen der Modellkonformität“ für beide Verfahren. Der aktuelle Bodenrichtwert (01.01.2026) wird nur zur Information angezeigt. | SWF 2025 S. 4 (Abschnitt B 2); LZ 2025 S. 4 (2.1) |
| Altbezirke (23 Bezirke vor 2001) | Zuordnung über den Ortsteil der Adresse (Tabelle 1 der LZ 2025, vollständig übernommen in `daten/marktdaten.xlsx`, Blatt „Ortsteile“) | LZ 2025 S. 5–8 |
| Stadträumliche Wohnlage | einfach / mittel / gut / sehr gut; Grundlage ist das Straßenverzeichnis zum Berliner Mietspiegel (Wohnlagenkarte). Der Rechner liest die Wohnlage automatisch aus dem offenen Datensatz „Wohnlagen nach Adressen zum Berliner Mietspiegel 2024“ (nur einfach/mittel/gut). | SWF 2025 S. 4 (B 5); LZ 2025 S. 4 (2.3); Glossar GAA artikel.158011.php |
| Baulicher Zustand | 3 Zustandsnoten: **gut** (neuwertig oder sehr geringe Abnutzung, unbedeutender Reparaturaufwand), **normal** (geringe/normale Verschleißerscheinungen, geringer bis mittlerer Instandhaltungsstau), **schlecht** (desolat, hoher Reparaturstau). Eine Innenbesichtigung lag der Ableitung nicht zugrunde. | SWF 2025 S. 4–5 (B 6); LZ 2025 S. 8 (2.5); Glossar GAA artikel.156899.php |
| Baujahr | Es gilt nur das **ursprüngliche Baujahr**. Keine Korrektur (fiktives Baujahr) wegen Modernisierungen. | SWF 2025 S. 2 (B); Vergleichsfaktoren S. 4 |

---

## 2 Sachwertverfahren – Ein- und Zweifamilienhäuser (§§ 35–39 ImmoWertV)

### 2.1 Anwendungsbereich

| Punkt | Ansatz | Fundstelle |
|---|---|---|
| Teilmarkt | Einfamilienhäuser, Einfamilienhäuser mit Einliegerwohnung, Zweifamilienhäuser; freistehend, Doppelhaushälfte, Reihenendhaus, Reihenmittelhaus; Massiv- und Fertighaus | SWF 2025 S. 2 (A 2), S. 5 (Tabelle 1) |
| Nicht anwendbar | **Villen und Landhäuser** (keine Faktoren ableitbar); vermietete Objekte, Grundstücke mit Wasserlage oder Denkmalschutz, Mischbaujahre, Erbbaurecht/Nießbrauch waren aus der Ableitung ausgeschlossen → der Rechner gibt dafür keinen Wert aus | SWF 2025 S. 1–2, S. 5, Fn. 9 |
| Gültigkeitsbereich (5 %- bis 95 %-Perzentile; nur darin „statistisch verlässlich anwendbar“) | vorläufiger Sachwert des Grundstücks **289.845 – 1.114.060 €**; Grundstücksfläche 212 – 993 m²; BGF 146 – 430 m²; Bodenrichtwert 410 – 1.200 €/m²; NHK (Stufe 4) 825 – 1.215 €/m²; tatsächliche GFZ 0,10 – 0,54 | SWF 2025 S. 6–7 (Tabellen 2 und 3), S. 8–9 |

Außerhalb des Gültigkeitsbereichs erscheint kein Wert, sondern ein Hinweis mit Anfrageknopf.

### 2.2 Herstellungskosten

| Parameter | Ansatz | Fundstelle |
|---|---|---|
| Kostenkennwerte | **NHK 2010 nach Anlage 4 ImmoWertV, immer Standardstufe 4** – keine Einstufung über Wägungsanteile | SWF 2025 S. 3 (B 1) |
| Gebäudeart (NHK-Typ) | nach Gebäudestellung (freistehend / Doppelhaus- oder Reihenendhaus / Reihenmittelhaus), Unterkellerung und Dachgeschoss. Regeln: Dachgeschoss unter 50 % ausgebaut → Typ „nicht ausgebaut“; ab 50 % → Typ „ausgebaut“. Teil- und Tiefkeller → Typ „unterkellert“. 3-geschossige Gebäude wie 2-geschossige behandeln. | SWF 2025 S. 3 |
| Brutto-Grundfläche | nach DIN 277-1:2005-02 (Anlage 4 ImmoWertV). Dachgeschoss mit Giebelhöhe ≤ 1,50 m zählt nicht; nicht nutzbare Spitzböden zählen nicht; **Garagen zählen nicht** (Ausnahme: von Geschossen überbaute Garagen) | SWF 2025 S. 3 |
| Zweifamilienhaus | keine Korrektur gegenüber Einfamilienhaus | SWF 2025 S. 3 |
| Baunebenkosten | in den NHK 2010 enthalten (Kostengruppen 730 und 771 DIN 276) | ImmoWertV Anlage 4 Nr. I 1 (3) |
| Regionalfaktor | **1,0** | SWF 2025 S. 3 |
| Baupreisindex | Preisindex für den Neubau von Wohngebäuden einschl. Umsatzsteuer, Destatis, **IV. Quartal 2024 = 130,8 (2021 = 100)**, umbasiert mit Faktor 1,4124 auf 2010 = 100 → **184,7**. Für die Anwendung der Sachwertfaktoren 2025 ist dieser Wert fest vorgegeben. | SWF 2025 S. 3–4 (B 1 und B 3) |

Herstellungskosten = BGF × NHK(Typ, Stufe 4) × 184,7 / 100 × 1,0.
Zu- oder Abschläge für bauliche Besonderheiten (z. B. Wintergarten) sind wie im
Referenzfall als Betrag auf die Herstellungskosten 2010 möglich, bevor indexiert wird.

### 2.3 Alterswertminderung

| Parameter | Ansatz | Fundstelle |
|---|---|---|
| Gesamtnutzungsdauer | **80 Jahre** (Anlage 1 ImmoWertV) | SWF 2025 S. 3 |
| Verfahren | **linear**: Alterswertminderungsfaktor = RND / GND; Alter = Stichtagsjahr − Baujahr | SWF 2025 S. 3; § 38 ImmoWertV |
| Restnutzungsdauer | **feste Tabellen nach Baujahr, Baualter und Bauzustand** (unten). **Keine Modernisierungspunkte** nach Anlage 2 ImmoWertV. | SWF 2025 S. 3–4 |

Baujahre **bis 1948**: gut 55 Jahre, normal 40 Jahre, schlecht 25 Jahre.

Baujahre **ab 1949** (Baualter in Jahren → RND in Jahren):

| Baualter | gut | normal | schlecht |
|---|---|---|---|
| bis 2 | 80 | 75 | 70 |
| 3 – 7 | 75 | 70 | 65 |
| 8 – 12 | 70 | 65 | 60 |
| 13 – 17 | 65 | 60 | 55 |
| 18 – 22 | 60 | 55 | 50 |
| 23 – 27 | 55 | 50 | 45 |
| 28 – 32 | 55 | 45 | 40 |
| 33 – 37 | 55 | 40 | 35 |
| 38 – 42 | 55 | 40 | 30 |
| 43 – 47 | 55 | 40 | 25 |
| 48 – 52 | 55 | 40 | 25 |
| 53 – 57 | 55 | 40 | 25 |
| ab 58 | 55 | 40 | 25 |

Hinweis: Die Tabelle lässt bei alten Häusern in gutem Zustand eine RND von 55 Jahren
zu, also mehr als GND − Alter. Das ist gewollt (modifizierte RND) und wird so übernommen.

### 2.4 Außenanlagen, Nebenanlagen, Bodenwert

| Parameter | Ansatz | Fundstelle |
|---|---|---|
| Typische Außenanlagen (Einfriedung, Hausanschlüsse, normale Hofbefestigung) | **im Bodenwert enthalten – kein eigener Ansatz** | SWF 2025 S. 3 |
| Besondere Nebenanlagen (Garagen, Geräteschuppen), besondere Außenanlagen (Brunnen, aufwendige Befestigungen), Nebenflächen | wurden aus den Kaufpreisen herausgerechnet → gesondert als Zeitwert hinzurechnen (im Rechner als optionale Angabe, deutlich gekennzeichnet) | SWF 2025 S. 4 (B 4) |
| Bodenwert | Grundstücksfläche × Bodenrichtwert 01.01.2024, **ohne GFZ-Anpassung** | SWF 2025 S. 4 (B 2) |

### 2.5 Sachwertfaktor (Marktanpassung)

Formel zum Stichtag 31.12.2024 (SWF 2025 S. 8–9, Tabellen 4–6):

    SWF = 1,398 − 0,000000280 × vorläufiger Sachwert des Grundstücks [€]
                − 0,0002759 × 1.096 Tage (31.12.2021 bis 31.12.2024)
                + Gruppenkorrektur + Korrekturen

Der Zeitterm ist mit −0,0002759 × 1.096 = **−0,30239** fest. Kontrolle: Gruppe 1,
300.000 € → 1,398 − 0,084 − 0,302 = 1,012 ≙ veröffentlicht 1,01.

Altbezirksgruppen (SWF 2025 S. 5, Tabelle 1; S. 8–9):

| Gruppe | Altbezirke | Korrektur |
|---|---|---|
| 1 | Treptow, Lichtenberg, Charlottenburg, Spandau, Wilmersdorf, Zehlendorf, Steglitz, Pankow | ±0 |
| 2 | Tempelhof, Neukölln, Hohenschönhausen | −0,062 |
| 3 | Köpenick, Weißensee, Reinickendorf, Marzahn, Hellersdorf | −0,105 |

Für die Altbezirke Mitte, Tiergarten, Wedding, Prenzlauer Berg, Friedrichshain, Kreuzberg
und Schöneberg sind **keine Sachwertfaktoren veröffentlicht** (keine Kauffälle in der
Stichprobe, Tabelle 7). Der Rechner gibt dort keinen Sachwert aus.

Korrekturen (SWF 2025 S. 9–10), additiv auf den Faktor:

| Merkmal | Ausprägung | Korrektur |
|---|---|---|
| Baujahresgruppe | bis 1919 | ±0 |
| | 1920 – 1948 | −0,061 |
| | 1949 – 1970 | −0,123 |
| | 1971 – 1990 | ±0 |
| | 1991 – 2009 | +0,106 |
| | 2010 – 2019 | ±0 |
| | ab 2020 | ±0 |
| Gebäudeart | freistehendes Ein-/Zweifamilienhaus | ±0 |
| | Doppelhaushälfte | +0,084 |
| | Reihenendhaus | +0,201 |
| | Reihenmittelhaus | +0,341 |
| Bauzustand | gut | +0,179 |
| | normal | ±0 |
| | schlecht | −0,141 |
| Gebäudekonstruktion | Massivhaus / Fertighaus massiv | ±0 |
| | Fertighaus Holz | −0,072 |
| Stadträumliche Wohnlage | einfach | −0,043 |
| | mittel | ±0 |
| | gut | +0,075 |
| | sehr gut | *nicht veröffentlicht* → wie „gut“ (+0,075), mit Hinweis |
| Bauerrichtungsvertrag | mit Kaufvertrag beurkundet (Neubau vom Bauträger) | −0,081 |
| | nicht beurkundet (Bestandskauf) | ±0 → Standard im Rechner |

Rundung: Der Faktor wird wie in den Tabellen auf **2 Nachkommastellen** gerundet
angewendet (offener Punkt 1, siehe unten).

Ablauf: vorläufiger Sachwert (Gebäude + besondere Nebenanlagen + Bodenwert) × SWF
= marktangepasster vorläufiger Sachwert; ± besondere objektspezifische
Grundstücksmerkmale (§ 8 Abs. 3 ImmoWertV) = Sachwert; Rundung auf volle 1.000 €.

---

## 3 Ertragswertverfahren – Mietwohnhäuser, Wohn- und Geschäftshäuser (§§ 27–34 ImmoWertV)

### 3.1 Anwendungsbereich

| Punkt | Ansatz | Fundstelle |
|---|---|---|
| Teilmarkt | Mietwohnhäuser und Mietwohngeschäftshäuser mit **mindestens 4 Mieteinheiten** und **gewerblichem Mietanteil ≤ 80 %** des Nettojahresrohertrags; Baujahr ab 1865; Bodenrichtwertzonen W, M1, M2, G, Gp (bei W nur gebietstypische GFZ ≥ 0,4) | LZ 2025 S. 1–2 |
| Nicht anwendbar | Ein-, Zwei-, Dreifamilienhäuser, Wohnungs-/Teileigentum, Paketverkäufe, Objekte mit Leerstand > 20 %, Erbbaurecht/Nießbrauch | LZ 2025 S. 1–2 |
| Gültigkeitsbereich (5 %- bis 95 %-Perzentile) | durchschnittliche Objektkaltmiete **5,60 – 12,10 €/m²** (Tabellenbereich 4,00 – 20,00 €/m² als Minimum/Maximum); gewerblicher Mietanteil 0 – 49,2 %; Grundstücksfläche 364 – 2.341 m²; Wohn-/Nutzfläche 407 – 3.318 m²; tatsächliche GFZ 0,53 – 4,42; Bodenrichtwert 600 – 6.500 €/m²; Bodenwert 613 – 8.490 €/m²; Alter 30 – 141 Jahre; RND 35 – 50 Jahre | LZ 2025 S. 16 (Tabellen 12–14) |

### 3.2 Rohertrag und Bewirtschaftungskosten

| Parameter | Ansatz | Fundstelle |
|---|---|---|
| Rohertrag | tatsächliche **Nettokaltmiete** je Nutzungsart (Wohnen, Gewerbe, Sonstiges wie Stellplätze) als Jahresbetrag; die durchschnittliche Objektkaltmiete in €/m² Wohn-/Nutzfläche und Monat steuert den Liegenschaftszinssatz | LZ 2025 S. 8 (2.6) |
| Instandhaltungskosten | Wohnen **13,80 €/m² Wohnfläche p. a.**; Garage 104 € je Platz; offener Stellplatz 52 € je Platz; Gewerbe (Büro, Praxis, Laden) **100 %** des Wohnansatzes je m²; Nebennutzung (Lager, Werkstatt im Keller) **30 %** | LZ 2025 S. 9 |
| Verwaltungskosten | Wohnen **351 € je Wohnung p. a.**; Gewerbe und Sonstiges **3 %** des jeweiligen Mietertrags | LZ 2025 S. 9 |
| Mietausfallwagnis | Wohnen **2 %**, Gewerbe und Sonstiges **4 %** der Nettokaltmiete | LZ 2025 S. 9 |
| Betriebskosten | kein eigener Ansatz (nicht umlagefähige Betriebskosten sind im Modell nicht enthalten) | LZ 2025 S. 8–9 (keine Position) |
| Indexierung | Ansätze gelten für Kaufjahr 2024, hochgerechnet mit VPI Deutschland (2020 = 100): Oktober 2001 = 77,1 → Oktober 2023 = 117,8. Bei neuen Liegenschaftszinssätzen die dort genannten Werte übernehmen. | LZ 2025 S. 9 |

### 3.3 Restnutzungsdauer

Baujahre **bis 1918 (Altbau)** und **1919 – 1948 (Zwischenkriegsbau)** – LZ 2025 S. 10, Tabellen 2–4:

| Bauzustand | RND |
|---|---|
| gut | 55 |
| normal | 40 |
| schlecht | 25 |

Ausstattungsabschläge: Altbau vollständig mit Zentral-/Etagenheizung **oder** Bädern: −5 Jahre; weder noch: −10 Jahre. Zwischenkriegsbau nicht vollständig mit Zentralheizung: −5 Jahre.

Baujahre **ab 1949** – LZ 2025 S. 11, Tabelle 5 (leere Felder: Kombination kommt nicht vor; der Rechner meldet das):

| Baualter | gut | normal | schlecht |
|---|---|---|---|
| bis 2 | 80 | – | – |
| 3 – 7 | 75 | 70 | – |
| 8 – 12 | 70 | 65 | 60 |
| 13 – 17 | 65 | 60 | 55 |
| 18 – 22 | 60 | 55 | 50 |
| 23 – 27 | 55 | 50 | 45 |
| 28 – 32 | 55 | 45 | 40 |
| 33 – 37 | 55 | 40 | 35 |
| 38 – 42 | 55 | 40 | 30 |
| 43 – 47 | 55 | 40 | 25 |
| 48 – 52 | 55 | 40 | 25 |
| 53 – 57 | 55 | 40 | 25 |
| ab 58 | 55 | 40 | 25 |

Bei mehreren Gebäudeteilen: nach Mietanteilen gewichtete mittlere RND (Referenzfall A).

### 3.4 Bodenwert im Ertragswertverfahren

| Parameter | Ansatz | Fundstelle |
|---|---|---|
| Bodenrichtwert | 01.01.2024 | LZ 2025 S. 4 (2.1) |
| GFZ-Anpassung | Bodenrichtwert wird von der GFZ der Richtwertzone auf die **tatsächliche wertrelevante GFZ** des Grundstücks umgerechnet: BW/m² = BRW × K(GFZ tatsächlich) / K(GFZ Zone) | LZ 2025 S. 4 (2.1); GFZ-W S. 3; GFZ-D S. 3 |
| Koeffizienten Wohnbauland (Zonen W) | Tabelle GFZ-W (0,8 – 5,0), Formel Kaufpreis/m² = −25,191 + 311,62·GFZ − 24,879·GFZ², Tabelle auf GFZ 2,0 = 1,0000 basiert | GFZ-W S. 1–2 |
| Koeffizienten Dienstleistung/Büro (Citylagen, Büroanteil ≥ 80 %) | Tabelle GFZ-D (2,0 – 7,0), Näherung K = 0,2047·GFZ + 0,181, Tabelle auf GFZ 4,0 = 1,0000 basiert | GFZ-D S. 1–2 |
| Mischgebiete M2 | nach Nutzflächenanteilen gewichtetes Mittel beider Koeffizienten (Empfehlung GAA) | GFZ-W S. 1; GFZ-D S. 2 |
| Außerhalb der Tabellenbereiche | keine Umrechnung möglich → Hinweis, Bodenwert ohne Anpassung nur als Näherung mit Kennzeichnung (offener Punkt 2) | – |
| Wertrelevante GFZ | Flächen aller oberirdischen Geschosse (ohne nicht ausbaufähige Dachgeschosse) nach Außenmaßen ÷ Grundstücksfläche | ImmoWertV § 16 Abs. 5; Glossar GAA artikel.757391.php |

### 3.5 Liegenschaftszinssatz

Grundformel zum Stichtag 31.12.2024 (LZ 2025 S. 12–15, Tabellen 6–11), Ergebnis in Prozent:

    LZ = 0,644 + 0,132 × Objektkaltmiete [€/m² Wohn-/Nutzfläche und Monat]
             + 0,0013304 × 1.096 Tage (01.01.2022 bis 31.12.2024)
             + Gebietsgruppenzuschlag + Altbezirkskorrektur
             + Baujahreskorrektur + Gewerbekorrektur

Zeitterm fest: 0,0013304 × 1.096 = **1,45812**. Kontrolle: Südost, 6,00 €/m² →
0,644 + 0,792 + 1,458 = 2,894 ≙ veröffentlicht 2,9; City → + 0,167 = 3,061 ≙ 3,1.

| Gebietsgruppe (nach Ortsteil, Tabelle 1) | Zuschlag | Altbezirkskorrektur |
|---|---|---|
| Südost | ±0 | – |
| Südwest | ±0 | – |
| Nord | ±0 | Reinickendorf +0,2 |
| City | +0,167 | Mitte −0,6; Charlottenburg −0,3 |
| Ost | +0,167 | – |
| West | +0,167 | – |

Weitere Korrekturen (LZ 2025 S. 15):

| Merkmal | Ausprägung | Korrektur |
|---|---|---|
| Baujahresgruppe | vor 1919; 1919–1948; 1949–1972; 1991–2002; nach 2002 | ±0 |
| | 1973 – 1990 im **Westteil** (Stadtlage West nach Tabelle 1) | +0,3 |
| | 1973 – 1990 im Ostteil | ±0 |
| Gewerblicher Anteil am Nettojahresrohertrag | je 10 Prozentpunkte +0,08 (0 % ±0 … 80 % +0,64); der Rechner interpoliert linear mit **+0,008 je Prozentpunkt** | LZ 2025 S. 15 |

Rundung: Der Liegenschaftszinssatz wird wie in den Tabellen auf **1 Nachkommastelle**
gerundet angewendet (offener Punkt 1). Kapitalisierung nach § 34 ImmoWertV mit dem
Barwertfaktor (qⁿ − 1) / (qⁿ · (q − 1)), q = 1 + LZ/100, n = RND, auf 4 Nachkommastellen.

Ablauf: Jahresrohertrag − Bewirtschaftungskosten = Reinertrag; − Bodenwertverzinsung
(Bodenwert × LZ) = Gebäudereinertrag; × Barwertfaktor = Gebäudeertragswert; + Bodenwert
= vorläufiger Ertragswert; Marktanpassungsfaktor 1,0 (die Liegenschaftszinssätze sind
bereits aus Kaufpreisen abgeleitet); ± besondere objektspezifische Grundstücksmerkmale;
Rundung auf volle 1.000 €. Ist der Gebäudereinertrag ≤ 0, erscheint kein Wert, sondern
der Hinweis auf eine Liquidationsbetrachtung.

---

## 4 Bodenrichtwerte und Adressdaten (Datengrundlage des Rechners)

| Datensatz | Dienst | Lizenz | Verwendung |
|---|---|---|---|
| Bodenrichtwerte 01.01.2024 (1.621 Zonen) | `https://gdi.berlin.de/services/wfs/brw2024` | dl-de/zero-2.0 | Modellstichtag für beide Verfahren |
| Bodenrichtwerte 01.01.2026 (1.623 Zonen) | `https://gdi.berlin.de/services/wfs/brw2026` | dl-de/zero-2.0 | nur Anzeige „aktueller Bodenrichtwert“ |
| Adressen Berlin (402.756 Punkte) | `https://gdi.berlin.de/services/wfs/adressen_berlin` | dl-de/zero-2.0 | Adresssuche, Ortsteil → Altbezirk/Gebietsgruppe |
| Wohnlagen nach Adressen zum Mietspiegel 2024 (401.095 Punkte) | `https://gdi.berlin.de/services/wfs/wohnlagenadr2024` | dl-de/zero-2.0 | Wohnlage einfach/mittel/gut je Adresse |

Zonenattribute, die der Rechner auswertet: `brw` (€/m²), `nutzung` (W, W-EFH, M1, M2, G,
Gp, GB, SF, LF, S-…), `gfz` (gebietstypische wertrelevante GFZ), `beitragszustand`
(fast immer „Beitragsfrei nach BauGB“), `verfahrensart`/`anwert` (städtebaulicher
Entwicklungsbereich: „Entw“ / „EU“ – dann Hinweis). Zonen ohne Baulandnutzung
(SF, LF, GB, S-WO, SF-KGA usw.) liefern keinen Bodenwert für Wohngebäude → Hinweis.

Pflichtangabe auf der Seite: „Bodenrichtwerte: Gutachterausschuss für Grundstückswerte
in Berlin, Geoportal Berlin, Stichtag 01.01.2024 (Modell) bzw. 01.01.2026 (aktuell),
Datenlizenz Deutschland – Zero – Version 2.0.“

---

## 5 Abweichungen gegenüber dem ursprünglichen Prompt – bewusst, wegen Modellkonformität

| Prompt sah vor | Berliner Modell verlangt | Folge für den Rechner |
|---|---|---|
| Standardstufe über Wägungsanteile (Anlage 4) | feste Standardstufe 4 | keine Ausstattungsabfrage für die NHK; stattdessen fließt der Zustand über die RND und den Sachwertfaktor ein |
| Modernisierungspunkte nach Anlage 2 | RND-Tabellen nach Baualter und Bauzustand | Checkliste entfällt; Abfrage „baulicher Zustand“ in drei Stufen mit Erläuterung |
| Außenanlagen als eigener Posten | typische Außenanlagen im Bodenwert | nur besondere Nebenanlagen (Garage, Carport) als optionaler Zeitwert |
| Bewirtschaftungskosten nach Anlage 3, indexiert | Berliner Ansätze (13,80 €/m², 351 €/WE, 2 %/4 %) | Berliner Werte sind maßgeblich; Anlage 3 nur Hintergrund |
| Bodenrichtwert aktuell | Bodenrichtwert 01.01.2024 | Rechner rechnet mit 2024, zeigt 2026 zur Information |
| Modellkonforme GFZ-Anpassung offen | Ertragswert: ja (Koeffizienten 2004); Sachwert: nein | zwei unterschiedliche Bodenwertroutinen |

---

## 6 Was der Rechner nicht abbildet (Hinweise auf der Ergebnisseite)

Bausubstanz und Bauschäden, Altlasten, Baulasten, Denkmalschutz, Rechte und Belastungen
(Erbbaurecht, Nießbrauch, Wohnrechte), Wasserlage, Villen/Landhäuser, Teilmärkte
außerhalb der Gültigkeitsbereiche, Marktentwicklung nach dem 31.12.2024, Leerstand,
Paketverkäufe, Share Deals, Grundstücksteilbarkeit, übergroße Grundstücke (Hinweis ab
dem 95 %-Perzentil der Grundstücksfläche).

---

## 7 Offene Punkte zur Entscheidung

1. **Rundung der Faktoren**: Sachwertfaktor auf 2 und Liegenschaftszinssatz auf 1
   Nachkommastelle (wie in den Tabellen) oder ungerundet aus der Formel? Die
   professionelle Software des Auftraggebers gibt die Praxis vor.
2. **GFZ außerhalb der Koeffiziententabellen** (W: < 0,8; Büro: < 2,0): ohne Anpassung
   rechnen und kennzeichnen – oder keinen Wert ausgeben?
3. **Wohnlage „sehr gut“**: wie „gut“ behandeln (Vorschlag) oder keinen Sachwert ausgeben?
4. **Sachwert in den Altbezirken ohne Faktoren** (Mitte, Tiergarten, Wedding, Prenzlauer
   Berg, Friedrichshain, Kreuzberg, Schöneberg): kein Wert (Vorschlag) – dort gibt es
   praktisch keine Eigenheime in der Stichprobe.
5. **Wertspanne**: ±15 % als Startwert; die 5 %-/95 %-Perzentile des Verhältnisses
   Kaufpreis/Sachwert (0,635 – 1,627 um den Mittelwert 1,06) zeigen, dass die reale
   Streuung größer ist. Vorschlag: Spanne ±15 % anzeigen und zusätzlich den Satz
   „Einzelne Kaufpreise weichen deutlich stärker ab“.
