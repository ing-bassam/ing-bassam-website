# Reichweite und Aufträge über die Website – Phasenplan

Stand: 2026-10-03. Ziel: mehr Anfragen über ing-bassam.de. Die Phasen bauen aufeinander auf;
jede endet mit einem Pull Request und einer kurzen Abnahme. Was BIB selbst tun muss, steht
unter „Dein Part“. Bewusst ausgeklammert, bis Referenzen vorliegen: Fallbeispiele,
Kundenstimmen, „Über uns“.

## Was schon da ist (nicht noch einmal einrichten)

- Google Search Console und Bing Webmaster Tools sind verifiziert (`google17d2…html`, `BingSiteAuth.xml`), Ahrefs ebenso.
- IndexNow meldet neue und geänderte Seiten automatisch (`tools/indexnow.py`, Workflow „Fachwissen-Seiten bauen“).
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

## Phase 2 – Eine Seite je Leistung

- [ ] Übersicht `/leistungen/` mit allen Leistungen
- [ ] Schimmelgutachten und Feuchteschäden
- [ ] Technische Beweissicherung
- [ ] Baubegleitung und Bauabnahme für private Bauherren
- [ ] Wasserschaden-Gutachten (Versicherungsfälle)
- [ ] Privatgutachten für Bauprozesse (Zielgruppe Anwälte)
- [ ] Für Gerichte und Versicherer (Fachgebiete, Kapazität, Bearbeitungszeit)
- [ ] Jede Seite: Umfang, Ablauf, Richtpreise, FAQ, strukturierte Daten; Startseite und Navigation verlinken
- [ ] Kasten „Passende Leistung“ am Ende jedes Fachbeitrags – gesteuert über das Frontmatter-Feld `leistung`

## Phase 3 – Werkzeuge und Checklisten als Einstieg

- [ ] Gewährleistungsfristen-Rechner (BGB/VOB: Abnahmedatum → Fristende, Hemmung, Neubeginn)
- [ ] Taupunkt- und Schimmelrisiko-Rechner (Raumklima, Oberflächentemperatur, 80-%-Kriterium)
- [ ] Mängelanzeige-Generator (Formular → fertiges Schreiben, Druck als PDF, alles im Browser)
- [ ] Übersichtsseite „Checklisten und Vorlagen“ für die vorhandenen Downloads
- [ ] Alle Werkzeuge: ohne Server, ohne Datenübertragung, mit Tests

## Phase 4 – Englisch ausbauen

- [ ] Einstiegsseite `/en/` mit allen Leistungen für internationale Käufer und Investoren
- [ ] Englische Fassungen der Leistungsseiten aus Phase 2
- [ ] Fünf Fachbeiträge auf Englisch (Hauskauf-Unterlagen, Wohnungskauf, Schimmel, Gewährleistung, Gutachterkosten)

## Phase 5 – Geschäftskunden

- [ ] Seiten „Für Hausverwaltungen“, „Für Anwälte“, „Für Versicherer“
- [ ] Acht LinkedIn-Beiträge aus bestehenden Fachbeiträgen vorformuliert (`marketing/linkedin/`)
- [ ] Liste der Verzeichnisse mit Eintragsdaten (IHK-Sachverständigenverzeichnis, Baukammer Berlin, Fachverbände)

## Dein Part (ohne Code)

1. **Google Unternehmensprofil** anlegen oder vervollständigen: Kategorie „Bausachverständiger“ (Zweitkategorien
   „Ingenieurbüro“, „Gutachter“), alle Leistungen eintragen, Beschreibung, Foto des Büros, Website-Link auf
   `https://ing-bassam.de/`. Nach jedem abgeschlossenen Auftrag eine Bewertungsbitte per Mail – Textvorlage folgt in Phase 2.
2. **Search Console** einmal im Monat öffnen: Leistung → Suchanfragen. Die zehn häufigsten Anfragen und die Seiten
   mit Position 5–20 sind die Vorlage für neue Leistungsseiten und Beiträge.
3. **Antwortversprechen** einhalten: Innerhalb eines Werktags reagieren – notfalls nur mit Terminvorschlag.
