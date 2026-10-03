# Prüfung vor der Veröffentlichung (Phase 4) – Stand 03.10.2026

## 1 Tests

`node --test "tests/**/*.test.mjs"` → **22 Tests, 22 bestanden, 0 fehlgeschlagen.**

- Referenzfall A (gegengerechnet mit professioneller Bewertungssoftware) wird exakt reproduziert:
  Sachwert 691.976,72 € → **692.000 €**, Ertragswert 686.826,08 € → **687.000 €**, einschließlich
  aller Zwischenwerte (Gebäudesachwerte 252.923,26 € / 374.978,76 €, mittlere RND 46,356 Jahre,
  Barwertfaktor 16,6622).
- Randfälle: RND 0, Liquidationsfall, fehlende Eingaben, Zinssatz 0 %.
- Berliner Tabellen: Sachwertfaktoren 1,01 / 0,79 / 0,89 / 0,79, Liegenschaftszinssätze 2,9 / 3,7 /
  3,9 / 3,4 / 3,0 / 3,5, GFZ-Beispiele der GAA-Broschüren (802 €/m², 2.295 €/m²), alle RND-Tabellen,
  97 Ortsteile, 36 NHK-Typen, Bewirtschaftungsansätze.
- Rechenkern-Module in Node und im Browser identisch (ES-Module ohne Abhängigkeiten).

## 2 Beispielobjekte zum Abgleich mit der Bewertungssoftware

Vollständige Rechenwege in `BEISPIELE-PHASE-4.md` (erzeugt mit `node tools/beispiele_rechnen.mjs`;
Stichtagsjahr 2026, Faktoren 31.12.2024, Bodenrichtwert 01.01.2024).

| Nr. | Objekt | Adresse (echte Richtwertzone) | Kernparameter | Ergebnis |
|---|---|---|---|---|
| 1 | freistehendes EFH, KG+EG+DG ausgebaut (NHK 1.01), Bj. 1965, normal, BGF 220 m², 600 m² | Akeleiweg 1, 12487 Johannisthal | BRW 650 €/m², RND 40 J., SWF 0,81 | **481.000 €** (409.000–553.000) |
| 2 | Reihenmittelhaus, EG+OG, DG nicht ausgebaut (NHK 3.32), Bj. 1998, gut, Grundfläche 65 m², 300 m², Carport 8.000 € | Akazienallee 1, 12623 Mahlsdorf | BRW 540 €/m², RND 55 J., SWF 1,59 | **579.000 €** (492.000–666.000) |
| 3 | Altbau-Mietwohnhaus mit Laden, Bj. 1905, 16 WE, 7,50 €/m² Wohnen, 12 €/m² Laden, 800 m², GFZ 2,19 | Anzengruberstraße 1, 12043 Neukölln | BRW 2.200 €/m², LZ 3,5 %, RND 40 J. | **2.742.000 €** (2.331.000–3.153.000) |
| 4 | Mietwohnhaus 1964, 12 WE, 7,00 €/m², 6 Stellplätze, 700 m², GFZ 1,50 | Alt-Köpenick 1, 12555 Köpenick | BRW 1.100 €/m², LZ 3,1 %, RND 40 J. | **1.432.000 €** (1.217.000–1.647.000) |
| 5 | Altbau Prenzlauer Berg, 9 €/m² Wohnen – Demonstration | Christburger Straße 1, 10405 | BRW 5.000 €/m² → Bodenwertverzinsung > Reinertrag | **kein Wert (Liquidationsfall)** |

Beim Abgleich zu beachten: Die Software muss modellkonform eingestellt sein (NHK 2010 Stufe 4,
Regionalfaktor 1,0, Baupreisindex 184,7 (2010 = 100), RND nach Berliner Tabellen ohne
Modernisierungspunkte, Bodenrichtwert 01.01.2024, Berliner Bewirtschaftungsansätze, Sachwertfaktor
und Liegenschaftszinssatz aus den Regressionsformeln, gerundet wie in den Tabellen). Abweichungen
an diesen Stellen sind Modell-, keine Rechenunterschiede. Die BGF-Ableitung aus Grundfläche
(Beispiel 2: 65 m² × 2,8 Ebenen = 182 m²) ist eine gekennzeichnete Annahme und soll hier kalibriert
werden (`Modellparameter`: `bgf_anteil_dachgeschoss`, `wohnflaeche_anteil_*`).

## 3 Netzwerk-Nachweis: keine Anfrage an fremde Domains

Mitschnitt aller Netzwerkanfragen im Browser (Chromium, eingebaute Vorschau) während eines
vollständigen Durchlaufs auf der deutschen und der englischen Seite:

```
GET /wertrechner/                                  200
GET /fonts/inter-v20-latin-regular.woff2           200
GET /fonts/space-grotesk-v22-latin-600.woff2       200
GET /wertrechner/wertrechner.css                   200
GET /wertrechner/assistent.js                      200
GET /wertrechner/berlin.js                         200
GET /wertrechner/texte.js                          200
GET /wertrechner/rechenkern.js                     200
GET /wertrechner/data/marktdaten.json              200
GET /fonts/fira-sans-v18-latin-300.woff2           200
GET /fonts/inter-v20-latin-500.woff2               200
GET /fonts/inter-v20-latin-600.woff2               200
GET /fonts/space-grotesk-v22-latin-500.woff2       200
GET /wertrechner/data/adressen/12487.json          200   (erst nach Eingabe der PLZ)
```

Alle Anfragen gehen an den eigenen Ursprung. Zusätzlich erzwingt die Content-Security-Policy der
Seite `default-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; script-src
'self'; style-src 'self'` – ein Aufruf einer fremden Domain würde vom Browser blockiert, bevor er
das Netz erreicht. Es gibt keine Inline-Skripte und keine Inline-Styles; die Browserkonsole bleibt
leer. Der Anfrage-Knopf erzeugt erst beim Klick einen `mailto:`-Link; vorher verlässt nichts den
Browser. Weder Cookies noch `localStorage`/`sessionStorage` werden verwendet.

## 4 Dateigrößen und Ladezeit

| Datei | roh | gzip (so liefert GitHub Pages aus) |
|---|---|---|
| wertrechner/index.html | 7,0 kB | 2,5 kB |
| wertrechner.css | 23,9 kB | 5,8 kB |
| assistent.js | 44,9 kB | 11,8 kB |
| berlin.js | 28,7 kB | 8,0 kB |
| rechenkern.js | 19,9 kB | 5,7 kB |
| texte.js (de + en) | 32,0 kB | 10,6 kB |
| data/marktdaten.json | 96,8 kB | 8,9 kB |
| **Erstaufruf gesamt (ohne Schriften)** | **253 kB** | **53 kB** |
| Schriften (6 × woff2, identisch mit der Startseite, meist im Cache) | 120 kB | – |
| PLZ-Datei, typisch (z. B. 12487) | 93 kB | 9,8 kB |
| PLZ-Datei, größte (12623 Mahlsdorf/Kaulsdorf) | 374 kB | 32,7 kB |
| alle 193 PLZ-Dateien zusammen (nur je eine wird geladen) | 11,8 MB | ca. 1,1 MB |

Bewertung: Der Erstaufruf liegt bei rund 55 kB übertragener Daten plus Schriften – auch im Mobilfunk
unter einer Sekunde Ladezeit. Die PLZ-Datei wird erst nach Eingabe der Postleitzahl geladen (10–35 kB
gzip). Keine externen Ressourcen, keine Bilder, kein Framework. Die Berechnung selbst dauert im
Browser unter einer Millisekunde.

## 5 Barrierearmut und Bedienung (Kurzprüfung)

- Alle Eingaben haben sichtbare `label`, Fehlermeldungen sind über `aria-describedby` verknüpft
  und per `aria-live` hörbar; Pflichtfelder sind markiert.
- Auswahlkarten sind native Radio-Buttons (Tastatur, Screenreader); die Straßensuche ist eine
  `combobox` mit `listbox`, Pfeiltasten/Enter/Escape funktionieren.
- Überschriften werden beim Schrittwechsel fokussiert; Kontraste entsprechen der Startseite
  (Text #0f1a28 auf #f4f3ef, Akzent #c2410c auf Weiß).
- `prefers-reduced-motion` schaltet Animationen ab; Druckstylesheet für das Ergebnis.
- Mobil (375 px): einspaltig, Buttons in voller Breite, keine horizontale Scrollleiste.

## 6 Wartung

Jahres-Checkliste und Pflegeablauf stehen in `daten/ANLEITUNG.md` (Abschnitt „Jahres-Checkliste“);
Quellen und Fundstellen in `fachliteratur/README.md` und `fachliteratur/MODELL-BERLIN.md`.
Kurzfassung: Februar/März neue Bodenrichtwerte (nur Anzeige), Sommer neue Sachwertfaktoren samt
Baupreisindex und ggf. Modell-Bodenrichtwert, Herbst neue Liegenschaftszinssätze, alle zwei Jahre
neue Wohnlagen; danach Excel pflegen → `marktdaten_bauen.py` → Tests → Beispiele → Pull Request.

## 7 Vor dem Merge noch zu entscheiden

1. Ergänzung der Datenschutzerklärung um den vorgeschlagenen Abschnitt 4a „Wertrechner“
   (nicht zwingend, da nichts übertragen wird; Vorschlag im Phase-3-Bericht).
2. Kalibrierung der BGF-Annahmen nach dem Abgleich der Beispiele 1 und 2 mit der Bewertungssoftware.
3. Englische Seite: Schrittnamen im Rechenweg bleiben deutsche Fachbegriffe (Zahlen englisch
   formatiert) – vollständige Übersetzung des Rechenwegs ist eine spätere Ausbaustufe.
