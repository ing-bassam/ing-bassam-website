# Fachliteratur und Datengrundlagen des Wertrechners

Dieser Ordner enthält ausschließlich **amtliche, frei verwendbare Dokumente**.
Fachbücher, Kommentare und Unterlagen kommerzieller Bewertungssoftware gehören in
den Ordner `fachliteratur-privat/`, der in `.gitignore` steht und nie ins
Repository gelangt.

Maßgeblich für die Programmierung sind die **ImmoWertV 2021** und die **ImmoWertA**;
die Berliner Veröffentlichungen legen das Modell fest (siehe `MODELL-BERLIN.md`).
Die früheren Richtlinien (SW-RL, EW-RL) dienen nur als Hintergrund.

## Dokumente in diesem Ordner

| Datei | Titel | Stand | Herkunft | Verwendungszweck |
|---|---|---|---|---|
| `ImmoWertV-2021.pdf` | Immobilienwertermittlungsverordnung vom 14. Juli 2021 (BGBl. I S. 2805) mit Anlagen 1–4 (Gesamtnutzungsdauern, Restnutzungsdauer/Modernisierung, Bewirtschaftungskosten, NHK 2010) | in Kraft seit 01.01.2022; Abruf 03.10.2026 | Bundesministerium der Justiz, gesetze-im-internet.de: https://www.gesetze-im-internet.de/immowertv_2022/ (PDF: `ImmoWertV.pdf`) | Rechtsgrundlage aller Rechenschritte; Anlage 4 liefert die NHK 2010 |
| `ImmoWertA-2023.pdf` | Muster-Anwendungshinweise zur Immobilienwertermittlungsverordnung (ImmoWertA), beschlossen von der Fachkommission Städtebau am 20.09.2023 | 2023; Abruf 03.10.2026 | BMWSB: https://www.bmwsb.bund.de/SharedDocs/downloads/DE/veroeffentlichungen/wohnen/immowerta.pdf?__blob=publicationFile&v=1 (Kurzlink www.bmwsb.bund.de/ImmoWertA) | Auslegung der ImmoWertV, Ablaufschemata, Modellkonformität (zu § 10), Rechenbeispiele |
| `Berlin-Sachwertfaktoren-2025.pdf` | Sachwertfaktoren 2025 – Faktoren zur Anpassung des Sachwertes von Grundstücken mit Eigenheimen an die Lage auf dem Grundstücksmarkt in Berlin zum Stichtag 31.12.2024 (Amtsblatt Nr. 29 vom 11.07.2025, S. 1852 ff.) | 04.02.2026 | Gutachterausschuss für Grundstückswerte in Berlin: https://www.berlin.de/gutachterausschuss/marktinformationen/daten-zur-wertermittlung/artikel.174909.php (Datei `05-03-010-2500.pdf`) | Modellbeschreibung und Faktoren für das Sachwertverfahren (Ein-/Zweifamilienhäuser) |
| `Berlin-Liegenschaftszinssaetze-2025.pdf` | Liegenschaftszinssätze 2025 für Mietwohnhäuser und Mietwohngeschäftshäuser (gewerblicher Mietanteil bis 80 %, mindestens vier Mieteinheiten) zum Stichtag 31.12.2024 (Amtsblatt Nr. 39 vom 19.09.2025, S. 2477 ff.) | 24.10.2025 | Gutachterausschuss Berlin: https://www.berlin.de/gutachterausschuss/marktinformationen/daten-zur-wertermittlung/artikel.174905.php (Datei `05-02-010-2500.pdf`) | Modellbeschreibung und Zinssätze für das Ertragswertverfahren; Tabelle 1 (Ortsteile → Altbezirk, Gebietsgruppe, Stadtlage) |
| `Berlin-Vergleichsfaktoren-Wohnungseigentum-2025.pdf` | Vergleichsfaktoren für den Teilmarkt des Wohnungseigentums zur Verwendung für steuerliche Zwecke zum Stichtag 31.12.2024 (Amtsblatt Nr. 50 vom 05.12.2025, S. 3179 ff.) | 02.03.2026 | Gutachterausschuss Berlin: https://www.berlin.de/gutachterausschuss/marktinformationen/daten-zur-wertermittlung/artikel.1377983.php (Datei `05-05-020-2500.pdf`) | **Nur Dokumentation.** Ausdrücklich für die steuerliche Bewertung bestimmt; der Rechner berechnet für Eigentumswohnungen keinen Wert (Entscheidung vom 03.10.2026) |
| `Berlin-GFZ-Umrechnungskoeffizienten-Wohnbauland-2004.pdf` | Umrechnungskoeffizienten für den Einfluss der realisierbaren GFZ auf den Wert von Wohnbauland in Gebieten der geschlossenen Bauweise (Wohn-04), Amtsblatt Nr. 12 vom 19.03.2004 | 12.10.2022 | Gutachterausschuss Berlin: https://www.berlin.de/gutachterausschuss/marktinformationen/daten-zur-wertermittlung/artikel.174898.php (Datei `05-01-010-0400.pdf`) | GFZ-Anpassung des Bodenwerts im Ertragswertverfahren (Zonen W, M1, M2) |
| `Berlin-GFZ-Umrechnungskoeffizienten-Dienstleistung-2004.pdf` | Umrechnungskoeffizienten für Bauland für Dienstleistungs- und Büronutzung in Citylagen (Dienst-04), Amtsblatt Nr. 12 vom 19.03.2004 | 12.10.2022 | wie vor (Datei `05-01-020-0400.pdf`) | GFZ-Anpassung bei überwiegender Büronutzung und für das gewichtete Mittel in M2-Gebieten |
| `Berlin-Nutzungsbestimmungen-Abruf-2026-10-03.txt` | Nutzungsbestimmungen des Gutachterausschusses (Textauszug) | Abruf 03.10.2026 | https://www.berlin.de/gutachterausschuss/marktinformationen/artikel.163608.php | Nachweis, dass die Fachdaten seit 01.03.2025 unter der Datenlizenz Deutschland – Zero – Version 2.0 stehen |
| `MODELL-BERLIN.md` | Zusammenstellung aller Modellparameter mit Fundstellen | laufend | eigene Auswertung der obigen Dokumente | verbindliche Vorgabe für `wertrechner/rechenkern.js` und `daten/marktdaten.xlsx` |

Urheberrecht: Die ImmoWertV ist als Gesetzestext gemeinfrei (§ 5 Abs. 1 UrhG). Die
ImmoWertA ist eine amtliche Veröffentlichung des BMWSB zur allgemeinen Kenntnisnahme.
Die Berliner Veröffentlichungen stehen unter dl-de/zero-2.0 (siehe Nutzungsbestimmungen).

## Offene Geodaten (werden nicht abgelegt, sondern vom Skript geladen)

`tools/adressdaten_bauen.py` lädt die folgenden Dienste des Geoportals Berlin einmal
jährlich in den lokalen Ordner `.wertrechner-cache/` und erzeugt daraus die kleinen
JSON-Dateien unter `wertrechner/data/adressen/`. Alle Dienste: WFS 2.0, Koordinaten
EPSG:25833, Lizenz **Datenlizenz Deutschland – Zero – Version 2.0**, keine
Zugriffsbeschränkungen.

| Datensatz | Dienst | Umfang | Verwendung |
|---|---|---|---|
| Bodenrichtwerte 01.01.2024 | https://gdi.berlin.de/services/wfs/brw2024 (`brw2024:brw_2024_vector`) | 1.621 Zonen, ca. 8,6 MB GeoJSON | Modellstichtag beider Verfahren |
| Bodenrichtwerte 01.01.2026 | https://gdi.berlin.de/services/wfs/brw2026 (`brw2026:brw2026_vector`) | 1.623 Zonen, ca. 8,6 MB GeoJSON | Anzeige des aktuellen Bodenrichtwerts |
| Adressen Berlin | https://gdi.berlin.de/services/wfs/adressen_berlin (`adressen_berlin:adressen_berlin`) | 402.756 Adresspunkte, ca. 136 MB GeoJSON (reduzierte Attribute) | Adresssuche, Ortsteil |
| Wohnlagen nach Adressen zum Berliner Mietspiegel 2024 | https://gdi.berlin.de/services/wfs/wohnlagenadr2024 (`wohnlagenadr2024:wohnlagenadr2024`) | 401.095 Punkte, ca. 116 MB GeoJSON (reduzierte Attribute) | Wohnlage einfach/mittel/gut |

Metadaten und Lizenzangaben: https://daten.berlin.de/datensaetze/adressen-berlin-wfs-634ab8ba,
https://daten.berlin.de/datensaetze/wohnlagen-nach-adressen-zum-berliner-mietspiegel-2024-wfs-eddbff85,
https://www.berlin.de/gutachterausschuss/marktinformationen/bodenrichtwerte/

## Weitere Quellen (nur Links, keine Dateien)

| Quelle | Link | Verwendungszweck |
|---|---|---|
| Destatis, Preisindizes für die Bauwirtschaft, GENESIS-Tabelle 61261-0002 (Baupreisindex Wohngebäude, 2021 = 100) | https://www-genesis.destatis.de/datenbank/online/statistic/61261/table/61261-0002 | Baupreisindex; Berlin gibt den anzuwendenden Wert in der jeweiligen Sachwertfaktoren-Veröffentlichung vor (2025: IV. Quartal 2024 = 130,8 → ×1,4124 = 184,7 auf Basis 2010) |
| Destatis, Verbraucherpreisindex (2020 = 100), GENESIS-Tabelle 61111-0002 | https://www-genesis.destatis.de/datenbank/online/statistic/61111/table/61111-0002 | Indexierung der Bewirtschaftungskosten laut Berliner Modell (Oktober 2001 = 77,1 → Oktober 2023 = 117,8) |
| Gutachterausschuss Berlin, Übersicht Daten zur Wertermittlung | https://www.berlin.de/gutachterausschuss/marktinformationen/daten-zur-wertermittlung/ | Einstieg für die jährliche Aktualisierung |
| Gutachterausschuss Berlin, Glossar: stadträumliche Wohnlagen | https://www.berlin.de/gutachterausschuss/service/glossar/artikel.158011.php | Definition der Wohnlagen |
| Gutachterausschuss Berlin, Glossar: baulicher Zustand | https://www.berlin.de/gutachterausschuss/service/glossar/artikel.156899.php | Definition der Zustandsnoten (Erläuterungstexte im Rechner) |
| Gutachterausschuss Berlin, Glossar: Altbezirke | https://www.berlin.de/gutachterausschuss/service/glossar/artikel.156764.php | Zuordnung der 23 Altbezirke |
| Gutachterausschuss Berlin, Glossar: wertrelevante GFZ | https://www.berlin.de/gutachterausschuss/service/glossar/artikel.757391.php | Erläuterung der GFZ-Angabe |
| Sachwertrichtlinie (SW-RL) vom 05.09.2012, BAnz AT 18.10.2012 B1; Ertragswertrichtlinie (EW-RL) vom 12.11.2015, BAnz AT 04.12.2015 B4 | Bundesanzeiger (www.bundesanzeiger.de) | nur Hintergrund; durch ImmoWertV 2021/ImmoWertA abgelöst |

## Jährliche Aktualisierung

Welche Werte wann zu erneuern sind, beschreibt `daten/ANLEITUNG.md`. Kurz: Im Frühjahr
erscheinen die neuen Bodenrichtwerte (01.01.), im Sommer/Herbst die neuen
Sachwertfaktoren und Liegenschaftszinssätze. Jede neue Veröffentlichung nennt den
anzuwendenden Bodenrichtwert-Stichtag und den Baupreisindex – beide müssen zusammen
umgestellt werden (`daten/marktdaten.xlsx` und `tools/adressdaten_bauen.py`).
