# Reichweite und Aufträge über die Website – Phasenplan

Stand: 2026-10-03. Ziel: mehr Anfragen über ing-bassam.de. Die Phasen bauen aufeinander auf;
jede endet mit einem Pull Request und einer kurzen Abnahme. Was BIB selbst tun muss, steht
unter „Dein Part“. Bewusst ausgeklammert, bis Referenzen vorliegen: Fallbeispiele,
Kundenstimmen, „Über uns“.

## Was schon da ist (nicht noch einmal einrichten)

- Google Search Console und Bing Webmaster Tools sind verifiziert (`google17d2…html`, `BingSiteAuth.xml`), Ahrefs ebenso.
- IndexNow meldet neue und geänderte Seiten automatisch nach jeder Auslieferung (`tools/indexnow.py`, Workflow „Website ausliefern“).
- Ausgeliefert werden nur die Website-Dateien (`tools/website_bauen.py`, Workflow „Website ausliefern“) – Agenten, Werkzeuge, Entwürfe und Unterlagen nicht.
- Sitemap und `llms.txt` erzeugt `tools/artikel_generator.py`; eigenständige Seiten stehen dort in `WEITERE_SEITEN`.
- Rund 50 Fachbeiträge mit FAQ und strukturierten Daten, 21 Vorlagen (PDF/Word) als Downloads.
- Wertrechner (DE/EN) und Leistungsseite Technische Due Diligence (DE/EN).

## Phase 1 – Fundament und Schnellgewinne (erledigt mit PR „Phase 1“)

- [x] Mobile Schnellkontakt-Leiste (Anrufen · Anfrage) auf Startseite, Fachbeiträgen, Wertrechner und Due-Diligence-Seiten
- [x] Antwortversprechen „Rückmeldung innerhalb eines Werktags“ im Kontaktbereich, Formular und Fußzeile der Fachbeiträge
- [x] Strukturierte Firmendaten der Startseite erweitert: Leistungskatalog, Sprachen, Kontaktstelle, Berlin + Brandenburg
- [x] 14 Beitragstitel auf höchstens 60 Zeichen gekürzt (Google schnitt sie ab)
- [x] Wertrechner und Due Diligence in Kopf- und Fußzeile aller Fachbeiträge verlinkt
- [x] Anliegen „Technische Due Diligence / Kaufberatung“ im Kontaktformular

## Phase 2 – Eine Seite je Leistung (PR „Phase 2“)

- [x] Übersicht `/leistungen/` mit allen Leistungen, Honorarlogik und Erstgespräch
- [x] Schimmelgutachten und Feuchteschäden (`/leistungen/schimmelgutachten/`)
- [x] Technische Beweissicherung (`/leistungen/technische-beweissicherung/`)
- [x] Baubegleitung und Bauabnahme (`/leistungen/baubegleitung-bauabnahme/`)
- [x] Wasserschaden-Gutachten (`/leistungen/wasserschaden-gutachten/`)
- [x] Privatgutachten für Bauprozesse (`/leistungen/privatgutachten-bauprozess/`)
- [x] Für Gerichte und Versicherer (`/leistungen/gerichte-versicherer/`)
- [x] Jede Seite: Umfang, Ablauf, Richtpreise, FAQ, strukturierte Daten, Verweise auf passende Fachbeiträge; Startseite, Navigation, Sitemap und llms.txt verlinken
- [x] Kasten „Passende Leistung“ am Ende jedes Fachbeitrags – Regeln in `tools/leistungen.py` (Frontmatter-Feld `leistung`, bei „Gutachten“ entscheidet das Thema), getestet in `tests/test_leistungen.py`
- [ ] Richtpreise vom Büro bestätigen; danach Bewertungsbitte-Vorlage für das Google-Unternehmensprofil

## Phase 3 – Werkzeuge und Checklisten als Einstieg

Geteilt in drei Lieferungen: 3a Übersicht + Vorlagen + Fristenrechner, 3b Taupunkt-Rechner, 3c Mängelanzeige-Generator.

- [x] 3a: Übersicht `/werkzeuge/` (Rechner, Checklisten, Protokolle, Musterschreiben)
- [x] 3a: Gewährleistungsfristen-Rechner `/werkzeuge/gewaehrleistungsfrist/` – BGB/VOB/B ab Abnahme, Hemmung (§§ 203, 204, 209 BGB), Mängelrüge und Mängelbeseitigung nach VOB/B, Anerkenntnis (§ 212 BGB), Werktagsregel (§ 193 BGB) mit Berliner Feiertagen; Rechenkern `frist.js` mit Node-Tests
- [x] 3a: Übersichtsseite „Checklisten und Vorlagen“ `/fachwissen/vorlagen/` – vom Seitenbauer aus den Vorlagen-Beiträgen erzeugt, aktualisiert sich mit jeder neuen Vorlage
- [x] 3a: Node-Tests laufen im Workflow „Werkzeuge testen“ mit; Navigation „Werkzeuge“ auf Startseite und Fachbeiträgen
- [x] 3b: Taupunkt- und Schimmelrisiko-Rechner `/werkzeuge/taupunkt/` – Magnus-Formel, Taupunkt, Oberflächenfeuchte, 80-%-Kriterium und Temperaturfaktor nach DIN 4108-2, zulässige Raumluftfeuchte; Rechenkern `taupunkt.js` mit Node-Tests
- [x] 3c: Mängelanzeige-Generator `/werkzeuge/maengelanzeige/` – Formular → vollständiges Schreiben nach dem Musterschreiben des Büros (Ich/Wir, BGB/VOB/B, Abnahmestand, Mängel, Frist, Anlagen, Gefahrhinweis), Prüfliste mit 20 Punkten, Drucken/PDF/Text kopieren, keine Speicherung; Rechenkern `brief.js` mit Node-Tests
- [x] Alle Werkzeuge: ohne Server, ohne Datenübertragung, mit Tests (Node-Tests im Workflow „Werkzeuge testen“)

## Phase 4 – Englisch ausbauen

Geteilt in 4a (Einstieg und Leistungsseiten) und 4b (englische Fachbeiträge).

- [x] 4a: Einstiegsseite `/en/` – alle Leistungen, Honorar, Arbeit mit Kunden im Ausland, Glossar mit 14 deutschen Baubegriffen, Kontakt, FAQ
- [x] 4a: Englische Leistungsseiten: `/en/mould-survey-berlin/`, `/en/water-damage-survey-berlin/`, `/en/new-build-inspection-berlin/` (snagging), `/en/condition-survey-berlin/`, `/en/construction-dispute-expert-berlin/` – gleiche Pakete und Preise wie auf Deutsch
- [x] 4a: hreflang-Paare Deutsch ↔ Englisch auf allen Gegenstücken (inkl. Startseite ↔ `/en/`), Sprachumschalter in der Kopfzeile, „English“ im Menü der Startseite; `tests/test_hreflang.py` prüft die Gegenseitigkeit
- [x] 4a: Liste der englischen Seiten zentral in `tools/leistungen.py` (`ENGLISCH`) → Sitemap und llms.txt („## English“)
- [x] 4b: Fünf Leitfäden auf Englisch unter `/en/guides/` (Hauskauf, Wohnungskauf, Schimmel, Gewährleistungsfristen, Gutachterkosten) – englische Fassungen veröffentlichter deutscher Beiträge mit denselben Quellen; Übersicht `/en/guides/`, Menüpunkt „Guides“ und Verweise auf den englischen Seiten
- [x] 4b: Seitenbauer baut englische Leitfäden aus `entwuerfe-en/` (`tools/beitraege_en.py`): hreflang in beide Richtungen, „English version“ und Sprachumschalter auf dem deutschen Original, Sitemap, llms.txt („## Guides in English“), IndexNow; `tests/test_leitfaeden_en.py` prüft Entwürfe, Original, Verknüpfung und verwaiste Seiten
- [ ] Englische Texte von einer Person mit sehr gutem Englisch gegenlesen lassen (Fachbegriffe, Ton)

## Phase 5 – Geschäftskunden

- [x] Seiten für Zielgruppen: `/leistungen/hausverwaltungen/`, `/leistungen/rechtsanwaelte/`, `/leistungen/versicherer/` – typische Anlässe, Arbeitsweise, Ablauf, Preise netto mit denselben Beträgen wie die Leistungsseiten, Anruf- und Anfrageknopf mit vorbereiteter E-Mail
- [x] Verlinkt von `/leistungen/` (Abschnitt „Für Verwaltungen, Kanzleien und Versicherer“), Startseite (Zielgruppen-Kachel, Fußzeile), Fußzeile aller Fachbeiträge, Gerichts- und Prozessseiten; Kasten „Passende Leistung“ zeigt bei Beiträgen mit Zielgruppe Hausverwaltung einen Hinweis auf deren Seite (`tools/leistungen.py`, getestet)
- [x] Neun LinkedIn-Entwürfe in `marketing/linkedin/`: acht aus Fachbeiträgen, einer für Versicherer aus der Leistungsseite; jede Aussage mit Beleg, Schlusszeile zur Seite der Zielgruppe
- [x] Liste der Verzeichnisse mit Eintragsdaten, Beschreibungstexten, Kosten und Bedingungen (IHK-Sachverständigenverzeichnis, Kammer, Fachverbände, Branchenbücher, Netzwerke der Zielgruppen) – bewusst **nicht** in diesem öffentlichen Repository, sondern beim Inhaber
- [x] Nicht belegte Erfahrungsaussagen und Selbstzuschreibungen auf bestehenden Seiten neutral formuliert („gehören zu unserem Alltag“, „unabhängig“, „hält vor Gericht“)

## Dein Part (ohne Code)

1. **Google Unternehmensprofil** anlegen oder vervollständigen: Hauptkategorie voraussichtlich „Baugutachter“
   (dazu „Bauingenieur“, „Gutachter“; im Profil-Editor prüfen), alle Leistungen eintragen, Beschreibung, Website-Link auf
   `https://ing-bassam.de/`. Nach jedem abgeschlossenen Auftrag eine Bewertungsbitte per Mail – Textvorlage folgt in Phase 2.
2. **Search Console** einmal im Monat öffnen: Leistung → Suchanfragen. Die zehn häufigsten Anfragen und die Seiten
   mit Position 5–20 sind die Vorlage für neue Leistungsseiten und Beiträge.
3. **Antwortversprechen** einhalten: Innerhalb eines Werktags reagieren – notfalls nur mit Terminvorschlag.
4. **Phase 5:** LinkedIn-Unternehmensseite anlegen und die Entwürfe aus `marketing/linkedin/` wöchentlich posten;
   Einträge nach der Verzeichnisliste vornehmen (zuerst Google, dann Bing, Branchenbücher, Verbände);
   Öffnungszeiten einmal festlegen und überall gleich angeben.
