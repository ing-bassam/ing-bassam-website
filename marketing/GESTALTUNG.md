# Gestaltung der Website – Konzept für die Überarbeitung 2026-11

Stand 09.11.2026. Gilt für alle von Hand gepflegten Seiten (Startseite, Leistungsseiten, Werkzeuge, Wertrechner, englische Seiten) und für die Vorlagen der erzeugten Seiten (Fachbeiträge, englische Leitfäden). Die Texte der Fachbeiträge selbst bleiben unverändert.

## 1. Ausgangslage

Geprüft wurden Startseite, 12 Leistungsseiten, 9 englische Seiten, Werkzeuge, Wertrechner, 404-Seite und die Vorlagen des Seitenbaus.

- **Textmenge.** Hero-Einleitungen haben 235 bis 420 Zeichen (drei bis vier Sätze), dazu je Seite eine Versprechensliste („Rückmeldung innerhalb eines Werktags“, „Ortstermin meist innerhalb von 5 Werktagen“), fünf bis sieben FAQ und ein dunkler Werbeblock („Warum BIB“, „Erstgespräch“). Dieselbe Zusage steht bis zu dreimal auf einer Seite (Versprechensliste, Kontaktblock, Fuß).
- **Ton.** Überschriften als Slogans: „Wir prüfen Gebäude, wenn es um Schaden, Streit oder Kauf geht.“, „Wissen, was Sie kaufen – bevor Sie zum Notar gehen.“, „ein Bauingenieur auf Ihrer Seite“, „Mängelprotokoll zur Abnahme, das hält“, „Bauphysik statt Bauchgefühl“, „Fünfzehn Minuten, die Klarheit bringen“, „kostenlos und verpflichtet zu nichts“, „Lieber direkt sprechen?“. Englisch entsprechend („Know what you’re buying“, „an engineer on your side“, „before anyone repaints“).
- **Anruf-Elemente.** Feste Leiste „Anrufen / Anfrage senden“ am unteren Bildschirmrand unter 860 px auf allen Seiten (auch auf allen Fachbeiträgen über die Vorlage), „Anrufen“-Knöpfe im Hero der Seiten für Hausverwaltungen, Rechtsanwälte und Versicherer, Telefon-Links in Hero, Kontaktblöcken, Fußzeilen, FAQ-Antworten und im Erfolgstext des Formulars.
- **Orange.** Drei Orangetöne (`#c2410c`, `#a3360a`, `#f26b2a`) in beiden Stylesheets und im eingebetteten CSS der Startseite: Knöpfe, Links, Fokusrahmen, Haken der Prüflisten, Markierungslinien, Schrittnummern, Maßkette, Textmarkierung, die Zeichnung im Hero (feste Farbwerte in den Verläufen), die Kategoriefarbe „Bauschäden“, die 404-Seite und das Favicon (Logo, bleibt).
- **Leistungsphasen 6 bis 8.** Nur als Nebensatz („bieten wir gesondert an“) auf der Startseite und der Seite Baubegleitung; keine eigene Darstellung, nicht in Übersicht und Navigation.

## 2. Farbe

Grundlage bleiben die dunklen Blautöne („Tinte“) und das Papier. Der Akzent wechselt von Orange zu einem gedeckten Stahlblau. Es gibt weiterhin genau einen Akzent; er markiert Handlungen (Knöpfe, Links, Fokus) und Messpunkte (Haken, Markierungslinien), nichts anderes.

| Variable | bisher | neu | Kontrast (WCAG) |
|---|---|---|---|
| `--ink-950` / `--ink-900` / `--ink-800` | `#0a121d` / `#0f1a28` / `#172334` | unverändert | – |
| `--paper` / `--surface` | `#f4f3ef` / `#ffffff` | unverändert | – |
| `--accent` (Knöpfe, Links, Haken, Fokus auf hellem Grund) | `#c2410c` | `#2b5a86` Stahlblau | auf Papier 6,5:1, auf Weiß 7,2:1, weißer Text darauf 7,2:1 |
| `--accent-hover` | `#a3360a` | `#234a70` | auf Papier 8,3:1, weißer Text darauf 9,2:1 |
| `--accent-bright` (nur auf dunklen Flächen: Links, Linien, Fokus, Zeichnung) | `#f26b2a` | `#8fb8de` | auf Ink-950 9,0:1, Ink-900 8,4:1, Ink-800 7,6:1 |
| `--accent-soft` (Hintergrund kleiner Symbole) | `rgba(194,65,12,.1)` | `rgba(43,90,134,.1)` | – |
| `--kat-bauschaeden` (Kategoriefarbe Fachbeiträge) | `#c2410c` | `#8a3a2f` Ziegelrot | auf Papier 6,9:1 |
| `--kat-energie-foerderung` | `#2f8a7a` (3,8:1, zu hell) | wird auf mindestens 4,5:1 abgedunkelt | – |
| Status „kritisch“ in Werkzeugen und Wertrechner (Zahlen auf dunklem Grund) | `--accent-bright` Orange | neue Variable `--error-bright: #f0998a` gedecktes Rot | auf Ink-950 8,6:1 |

Regeln:

- Ein Akzent, zwei Helligkeiten: `--accent` auf hellem Grund, `--accent-bright` auf dunklem Grund. Das helle Blau steht nie auf Papier (1,9:1), das dunkle nie auf Tinte.
- Fokusrahmen: 2 px, `--accent` auf hell, `--accent-bright` auf dunkel (beide über 3:1).
- Statusfarben bleiben eine Ampel: kritisch gedecktes Rot, Grenzbereich Bernstein `#e6b566` (bleibt), unkritisch Grün `#8fd4ad` (bleibt). Orange wird dort nicht durch Blau ersetzt, weil der Hinweis sonst seine Bedeutung verliert.
- Zeichnung im Hero der Startseite: Prüfstrahl, Feuchtefläche, Riss und Höhenkote in `--accent-bright`; die festen Orange-Werte in den Verläufen werden durch `#8fb8de` ersetzt.
- 404-Seite: Fokus und Linie auf `#8fb8de`.
- Alternative, falls das Stahlblau zu kräftig wirkt: Graublau `#3d5872` (auf Papier 6,7:1, weißer Text 7,4:1) mit `#8fb8de` auf dunklem Grund.
- Unverändert: Logo und Favicon (orangefarbene Linie unter „BIB“), Grautöne für Text (`--text-2` 7,1:1, `--text-3` 5,1:1 auf Papier), Fehlerrot `#b42318` in Formularen (5,9:1).

## 3. Schrift und Abstände

Schriften bleiben (Inter, Space Grotesk, Fira Sans für das Logo, Systemschrift mit fester Breite für Beschriftungen). Geändert werden Größen, Zeilenlängen und Abstände für kleine Bildschirme.

| Element | bisher | neu |
|---|---|---|
| Grundschrift | 16 px, Zeilenhöhe 1,65 (Fachbeiträge 17 px, 1,75) | unverändert |
| Zeilenlänge Fließtext | bis 68 Zeichen, Hero-Einleitung bis 60 | Absätze höchstens 62 Zeichen, Hero-Einleitung 52 |
| H1 Startseite | 36 bis 60 px | 32 bis 56 px, höchstens drei Zeilen auf 390 px (höchstens 60 Zeichen) |
| H1 Leistungsseiten | 34 bis 56 px | 30 bis 52 px |
| H2 Abschnitte | 32 bis 46 px | 26 bis 40 px |
| Hero-Einleitung | 17 bis 19 px, drei bis vier Sätze | 17 bis 19 px, höchstens zwei Sätze (220 Zeichen) |
| Abschnittsabstand | 80 bis 128 px | 56 bis 120 px |
| Hero unten (Leistungsseiten) | 56 bis 96 px | 48 bis 96 px; der Wertrechner behält den Überhang seiner Karte |
| Knöpfe | 48 px hoch, unter 640 px volle Breite | unverändert, höchstens zwei je Block, Beschriftung höchstens 24 Zeichen |
| Versprechensliste im Hero | vier Angaben nebeneinander, mit Trennstrichen | entfällt oder höchstens drei sachliche Angaben als Zeilen (Gebiet, Berichtsform, Sprache) |
| Karten „Für wen“ | drei Spalten, Text bis vier Sätze | untereinander, Überschrift und höchstens zwei Sätze |
| Prüfliste | zweispaltig ab 600 px | unverändert, höchstens acht Punkte |
| FAQ | fünf bis sieben, zugeklappt | höchstens fünf, Antworten höchstens drei Sätze, strukturierte Daten werden mitgeführt |
| Fußzeile Startseite | zwei Spalten unter 640 px | unverändert; Spalte „Kontakt“ nur mit E-Mail |
| Bewegung | Linien zeichnen sich, Prüfstrahl einmal | unverändert, nichts Neues |

## 4. Ton – Regeln für Texte

### 4.1 Berufsrecht

Fundstellen, nachgelesen am 09.11.2026:

- **Berliner Architekten- und Baukammergesetz (ABKG)**, Fassung vom 08.01.2026, gültig ab 22.01.2026 (gesetze.berlin.de, Gliederungs-Nr. 7102-6), § 53 Berufsordnung. Absatz 1 Satz 1: „Die nach diesem Gesetz der Berufsordnung Unterworfenen haben ihren Beruf gewissenhaft auszuüben und dem ihnen im Zusammenhang mit dem Beruf entgegengebrachten Vertrauen zu entsprechen.“ Absatz 2 Nummer 4: Die Berufsordnung soll Vorschriften enthalten über „den zulässigen Umfang der Werbung, insbesondere auch bei gleichzeitiger Ausübung einer gewerblichen Tätigkeit im Baubereich; vergleichende Werbung ist unzulässig“.
- **Berufsordnung der Baukammer Berlin** vom 15.06.2022 (Amtsblatt Nr. 9 vom 01.03.2024, S. 496; PDF auf baukammerberlin.de, Kammerrecht). § 9 Umfang der Werbung: „(1) Mitglieder werben durch fachliche Leistungen. Ihnen ist jede Form einer unlauteren oder aufdringlichen Werbung untersagt. (2) Werbung ist den Pflichtmitgliedern nur erlaubt, soweit sie über die berufliche Tätigkeit in Form und Inhalt sachlich unterrichtet.“ § 2 Absatz 2 Kollegialität: „Sie unterlassen jede Schädigung eines Kollegen. Sie wahren Objektivität bei der Beurteilung der Werke und Leistungen ihrer Kollegen und enthalten sich herabsetzender Äußerungen in der Öffentlichkeit.“ § 8 Absatz 1: „Irreführende Firmierungen des selbständigen Ingenieurs sind unzulässig.“ § 3 Absatz 3 (sinngemäß): Auf Verlangen ist der Auftraggeber vor Vertragsschluss über Berechnungsart, voraussichtliche Höhe und Fälligkeit des Honorars zu unterrichten; auf diese Möglichkeit ist hinzuweisen.
- **Erläuterungen des Rechtsausschusses zur Berufsordnung** (Fassung vom 27.10.1999, auf der Kammerseite verlinkt), zu § 9, sinngemäß: zulässig sind unter anderem die Nennung von Tätigkeitsschwerpunkten, eigene Broschüren mit Darstellung des Büros, redaktionelle Veröffentlichungen und sachlich gehaltene Mitteilungen; unzulässig sind unter anderem irreführende oder unwahre Angaben zu Tätigkeitsschwerpunkten, bezahlte Anzeigen, in denen um Aufträge geworben wird, Postwurfsendungen und Werbegeschenke.

Einordnung: Die Website ist die eigene Darstellung des Büros und damit zulässig, solange sie über die berufliche Tätigkeit sachlich unterrichtet, nicht aufdringlich ist, nicht vergleicht und nicht irreführt. Die Fachbeiträge sind redaktionelle Veröffentlichungen. Das Gesetz schließt vor allem Vergleiche aus, die Kammer darüber hinaus alles Anpreisende und Aufdringliche.

### 4.2 Regeln

1. **Jeder Satz unterrichtet.** Er nennt Leistung, Gegenstand, Umfang, Ablauf, Ergebnis (Berichtsform), Gebiet, Sprache, Qualifikation oder Kontaktweg. Werturteile über das eigene Büro entfallen („gründlich“, „verlässlich“, „auf Ihrer Seite“).
2. **Keine Superlative, keine Alleinstellung, keine Garantie.** Nicht „das hält“, „die Klarheit bringen“, „der einzige“, „führend“, „beste“.
3. **Kein Vergleich mit anderen** (Büros, Handwerksbetriebe, Gutachter, Gerichtsgutachter): keine Gegenüberstellungen („Bauphysik statt Bauchgefühl“), keine Abwertung fremder Gutachten. „Prüfung gegnerischer Gutachten“ wird zu „Stellungnahme zu einem vorliegenden Gutachten“.
4. **Nicht aufdringlich.** Je Seite höchstens eine Kontaktaufforderung im Inhalt, dazu die Angaben im Fuß. Keine festen Leisten, keine Dringlichkeit („jetzt“, „Lieber direkt sprechen?“), keine Anreize („kostenlos und verpflichtet zu nichts“), keine Fragen als Köder („Sie möchten Gewissheit?“).
5. **Überschriften benennen Leistung und Anlass**, keine Slogans: Substantiv plus Ort oder Anlass („Schimmelgutachten in Berlin“); die Unterzeile beschreibt den Fall. Keine „Wir …“-Sätze als Überschrift.
6. **„Wir“ nur für ein Vorgehen** („Wir messen die Oberflächentemperatur …“), nicht als Selbstbeschreibung („Wir prüfen Gebäude“, „Wir stellen Mängel fest“). Alternativ Substantive: „Feststellung von Schäden und Ursachen“.
7. **Zusagen nur, wenn belegbar.** Die Reaktionszeit steht einmal je Seite im Kontaktblock als „Antwort in der Regel innerhalb eines Werktags“, nicht als Plakette in Listen.
8. **Honorar.** Keine Preise auf öffentlichen Seiten. Hinweis, dass vor einer Beauftragung ein schriftliches Angebot mit Leistungsumfang und Berechnungsgrundlage vorliegt. Kein „günstig“, kein Preisvergleich, kein Hinweis auf das Unterschreiten von Vergütungsordnungen.
9. **Firmierung und Qualifikation exakt.** Firmenname wie im Handelsregister, Kammereintrag wie geführt, akademischer Grad. Keine Zusätze, die Bestellungen oder Zertifikate andeuten, die nicht bestehen.
10. **Sprache.** Sie-Anrede, Aussagesätze mit höchstens 20 Wörtern, keine Ausrufezeichen, keine rhetorischen Fragen, keine Gedankenstrich-Slogans in Überschriften. Englische Seiten nach denselben Regeln; deutsche Rechtsbegriffe bleiben in Klammern.

### 4.3 Vorher und Nachher

**Startseite, Hero**

- Vorher: Zeile „Baugutachten in Berlin und Brandenburg“. H1 „Wir prüfen Gebäude, wenn es um Schaden, Streit oder Kauf geht.“ Einleitung „Wir stellen Schäden und Mängel fest, klären ihre Ursachen und dokumentieren den Zustand von Gebäuden – für Gerichte, Versicherer, Hausverwaltungen, Käufer und Bauherren.“ Darunter „Lieber direkt sprechen? [Mobilnummer]“ und der Knopf „Anfrage senden“.
- Nachher: Zeile „Ingenieurbüro für Bauwesen · Berlin und Brandenburg“. H1 „Baugutachten, Beweissicherung und Bauüberwachung.“ Einleitung „Gutachten zu Bauschäden, Feuchte und Baumängeln, Beweissicherung vor und während Bauarbeiten, Begleitung von Kauf und Abnahme sowie Vergabe und Objektüberwachung nach HOAI. Für Eigentümer, Hausverwaltungen, Rechtsanwälte, Versicherer und Gerichte.“ Knopf „Leistungen“, Textlink „Anfrage per E-Mail“. Kein Telefon.

**Leistungsübersicht, Kontaktblock**

- Vorher: „Fünfzehn Minuten, die Klarheit bringen. Schildern Sie uns Ihr Anliegen. Wir sagen Ihnen, ob ein Gutachten nötig ist und welcher Umfang zur Frage passt – oder ob eine Fachfirma genügt. Preise und Leistungsübersicht senden wir Ihnen per E-Mail. Das Gespräch ist kostenlos und verpflichtet zu nichts.“ Knöpfe: E-Mail und Telefonnummer.
- Nachher: „Anfrage. Beschreiben Sie Ihr Anliegen per E-Mail, gern mit Fotos und Unterlagen. Sie erhalten eine Einschätzung, ob und in welchem Umfang ein Gutachten sinnvoll ist, und ein schriftliches Angebot mit Leistungsumfang. Antwort in der Regel innerhalb eines Werktags.“ Ein Knopf „Anfrage per E-Mail“, darunter die Anschrift.

**Schimmelgutachten, Werbeblock**

- Vorher: dunkler Block „Warum BIB“ mit der Überschrift „Bauphysik statt Bauchgefühl“, darunter Telefon, E-Mail und „Rückmeldung innerhalb eines Werktags“.
- Nachher: Der Block entfällt. Das Vorgehen steht im Abschnitt „Ablauf“: „Ursache: Messung der Oberflächentemperaturen und der Raumluftfeuchte, Prüfung der Bauteilfeuchte, bauphysikalische Berechnung der Wärmebrücke. Der Bericht benennt Ursache, Umfang und die fachlich erforderlichen Schritte.“ Kontakt nur noch im Kontaktblock am Seitenende.

**Englisch, Kaufbegutachtung**

- Vorher: „Know what you’re buying – before you sign at the notary.“
- Nachher: „Pre-purchase inspection in Berlin.“ Einleitung: „Inspection, document review and a written condition report with a defect list and a cost outlook for the next 10 to 15 years – for flats and houses.“

### 4.4 Wortliste

- Entfällt: „Lieber direkt sprechen?“, „Anrufen“, „Call us“, „Jetzt …“, „kostenlos und verpflichtet zu nichts“, „Warum BIB“, „Bauphysik statt Bauchgefühl“, „auf Ihrer Seite“, „an engineer on your side“, „das hält“, „Sie möchten Gewissheit?“, „Want certainty?“, „Fünfzehn Minuten, die Klarheit bringen“, „Know what you’re buying“, „before anyone repaints“.
- Ersetzt: „Wir prüfen Gebäude …“ → Leistungsbezeichnung; „Wir stellen fest“ → „Das Gutachten stellt fest“ oder „Feststellung von …“; „Termin anfragen“, „Anfrage senden“, „Angebot anfordern“ → „Anfrage per E-Mail“; „gegnerische Gutachten“ → „vorliegende Gutachten“; „Erstgespräch“ → „Anfrage“; „Was wir nicht tun“ → „Grenzen der Leistung“; dreifach „Rückmeldung innerhalb eines Werktags“ → einmal „Antwort in der Regel innerhalb eines Werktags“.

## 5. Kontakt

- E-Mail ist der Kontaktweg. Je Seite ein Knopf „Anfrage per E-Mail“ (mailto mit Betreff); auf der Startseite führt er zum Formular. Das Formular (mailto) bleibt, Überschrift „Anfrage per E-Mail“, Erfolgstext ohne Telefon.
- Die feste Schnellkontakt-Leiste entfällt überall: HTML der Seiten, Abschnitt „Mobiler Schnellkontakt“ in beiden Stylesheets, Skript auf der Startseite, Vorlagen für Fachbeiträge und englische Leitfäden. Der untere Seitenabstand, der für die Leiste reserviert war, entfällt mit ihr.
- „Anrufen“-Knöpfe und Telefon-Links entfallen: Hero, Kontaktblöcke, Fußzeilen, FAQ-Antworten („oder rufen Sie an“), Erfolgstext des Formulars, Leistungskasten der Fachbeiträge.
- Die Telefonnummer entfällt auf der gesamten Website, auch im Impressum und in der Datenschutzerklärung. Für die Anbieterkennzeichnung genügen E-Mail-Adresse und Kontaktformular (EuGH, Urteil vom 16.10.2008, C-298/07, zu § 5 TMG, heute § 5 DDG); die Berufsordnung der Baukammer Berlin verlangt keine Telefonangabe. Entfernt wird sie außerdem aus den strukturierten Daten (`telephone`), der Autorenzeile der Fachbeiträge (Quelle `entwuerfe/`, `entwuerfe-en/`), dem Leistungskasten und der Fußzeile der Vorlagen für Fachbeiträge und englische Leitfäden sowie aus den Downloads der Vorlagen (`tools/vorlage_bauen.py`, Downloads neu erzeugt).
- Kopfzeile Startseite: Knopf „Anfrage senden“ wird „Kontakt“ und führt zum Kontaktabschnitt. Auf den übrigen Seiten bleibt der Menüpunkt „Kontakt“.
- Englisch: „Send an enquiry“ wird „Enquiry by email“, „Call us“ entfällt.
- Test: `tests/test_kaufbegutachtung.py` erwartet bisher einen Telefon-Link auf den Kaufbegutachtungsseiten; die Prüfung wird gestrichen.

## 6. Aufbau der Seiten auf dem Handy

**Startseite**, von oben nach unten: Kopf (Logo, Menü) · Hero (Ortszeile, H1, Einleitung mit höchstens zwei Sätzen, ein Knopf, ein Textlink; Zeichnung unter 640 px ausgeblendet wie bisher) · Schriftfeld mit drei Angaben (Büro, Kammer, Gebiet) statt fünf · Leistungen als Liste mit sieben Einträgen (Anlass, Name, ein Satz) · Arbeitsweise mit vier Schritten (Überschrift, ein Satz) · Fachwissen und Werkzeuge (ein Satz, drei Links) · Kontakt (E-Mail-Adresse, Formular, Anschrift, Telefon als Text) · Fuß (Navigation, Impressum und Datenschutz aufklappbar).

**Leistungsseite**: Kopf, Brotkrumen · Hero (Anlass-Zeile, H1 „Leistung in Berlin“, Einleitung mit höchstens zwei Sätzen, Knopf „Anfrage per E-Mail“, Textlink „Leistungsumfang“; Versprechensliste entfällt oder drei Angaben als Zeilen) · „Für wen“ (drei Karten untereinander, je höchstens zwei Sätze) · „Leistungsumfang“ (Prüfliste bis acht Punkte, Pakete als Liste ohne Hervorhebung) · „Was Sie erhalten“ und „Grenzen der Leistung“ · „Ablauf“ (vier Schritte) · Kontaktblock (ein Satz, E-Mail-Knopf, Anschrift) · FAQ (höchstens fünf) · „Zum Weiterlesen“ (bis vier Beiträge) · Fuß (Firma, Anschrift, E-Mail, Impressum, Datenschutz, Sprachwechsel).

**Englische Seiten** wie die Leistungsseiten; das Glossar auf der englischen Startseite bleibt.

**Fachbeiträge**: Text unverändert. Geändert werden nur Leiste (entfällt), Leistungskasten (ein E-Mail-Knopf, ein Satz), Farben und die Überschriftengrößen auf dem Handy.

## 7. Leistungsphasen 6 bis 8 HOAI

Empfehlung: eine eigene Leistungsseite `leistungen/vergabe-objektueberwachung/` mit dem Titel „Vergabe und Objektüberwachung – Leistungsphasen 6 bis 8 HOAI“.

- **Inhalt** in eigenen Worten, Grundlage ist das Leistungsbild Objektplanung Gebäude der HOAI: Vorbereitung der Vergabe (Leistungsbeschreibungen mit Leistungsverzeichnissen, Mengenermittlung, Zusammenstellen der Vergabeunterlagen, Kostenkontrolle), Mitwirkung bei der Vergabe (Einholen und Prüfen der Angebote, Preisspiegel, Vergabevorschlag, Mitwirkung bei der Auftragserteilung), Objektüberwachung (Überwachung der Ausführung auf Übereinstimmung mit Genehmigung, Ausführungsplanung, Leistungsbeschreibung und anerkannten Regeln der Technik, Terminplan, Bautagebuch, gemeinsames Aufmaß, Rechnungsprüfung, Abnahme mit Feststellung von Mängeln, Kostenkontrolle und Kostenfeststellung, Übergabe und Dokumentation).
- **Für wen**: Bauherren mit Planung, aber ohne Bauleitung; Eigentümer und Eigentümergemeinschaften bei Instandsetzung und Sanierung; Hausverwaltungen; Übernahme bei laufenden Vorhaben.
- **Abgrenzung**: Die baubegleitende Qualitätskontrolle (Stichprobe im Auftrag des Bauherrn) bleibt eine eigene Seite. Beide Seiten verweisen aufeinander; die Nebensätze „bieten wir gesondert an“ werden durch den Verweis ersetzt.
- **Einbindung**: Startseite neue Leistungszeile („Sie lassen bauen oder sanieren und brauchen eine Bauleitung“), Leistungsübersicht neue Karte in „Bauen und Sanieren“, Fuß-Navigation der Startseite, strukturierte Daten (knowsAbout, Angebot), englische Übersicht mit einer Karte, die auf die deutsche Seite verweist (wie bei „Gutachten für Gerichte und Versicherer“). Neuer Eintrag in `tools/leistungen.py`, damit Sitemap, llms.txt und der Leistungskasten der Fachbeiträge die Seite kennen; die Zuordnung „Objektüberwachung“ zeigt dann auf die neue Seite.
- **Honorar**: keine Preise. Satz: „Honorar auf Grundlage der HOAI; Angebot nach Besprechung des Vorhabens.“
- **Alternative**: ein Abschnitt auf der Seite Baubegleitung. Nachteil: Stichprobe und Bauleitung stehen auf einer Seite, und die Leistung ist über Suchmaschinen schlechter zu finden.

## 8. Umsetzung und Prüfung

1. Farben, Anruf-Elemente und Leiste: beide Stylesheets, eingebettetes CSS und Skript der Startseite, 404-Seite, alle Seiten, Vorlagen in `tools/artikel_generator.py` und `tools/beitraege_en.py`, Test anpassen.
2. Texte: Startseite, Leistungsseiten, englische Seiten, Kurztexte in `tools/leistungen.py`, FAQ mit strukturierten Daten, Meta-Beschreibungen (höchstens 160 Zeichen). Neue Seite Vergabe und Objektüberwachung.
3. Seitenbau: `python tools/artikel_generator.py --pruefen`, dann ohne `--pruefen`; `node tools/angebot_verschluesseln.mjs --versionen`; `python -m unittest discover -s tests`; `node --test "tests/**/*.test.mjs"` (der Fehler `test_doppelungen … Radon` besteht schon auf main).
4. Darstellung: `layout_pruefen.mjs` mit dem Arbeitsstand bei 1440, 820 und 390 px ohne Befunde; Bildschirmfotos der Startseite und zweier Leistungsseiten bei 390 px, vorher und nachher.
5. Ablage: Konzept, Bildschirmfotos und Prüfbericht in `G:\Meine Ablage\05_Website\Website Neu\Ueberarbeitung 2026-11\`.

## 9. Nicht geändert

Logo und Favicon, Texte der Fachbeiträge und der englischen Leitfäden, Weiterleitungsseiten im Hauptordner, Rechenwege von Wertrechner und Werkzeugen, private Angebotsseiten (übernehmen nur die Farbvariablen), Workflows und Agenten-Anweisungen.
