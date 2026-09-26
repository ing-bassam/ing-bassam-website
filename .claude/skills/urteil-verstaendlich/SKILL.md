---
name: urteil-verstaendlich
description: Wählt wie der Urteilsbesprechungs-Agent eine baurelevante Gerichtsentscheidung aus amtlichen Quellen aus und schreibt daraus eine kurze, leicht verständliche und spannend erzählte Besprechung für Bauherren, Eigentümer und Hausverwaltungen (höchstens 10 Minuten Lesezeit, Format „Urteil verständlich“). Wird vom Workflow „Urteil verständlich“ mit dem Pfad zur Kandidatenliste aufgerufen und läuft ohne Rückfragen.
allowed-tools: Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, Bash(git checkout:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr list:*), Bash(wc:*), Bash(python tools/artikel_generator.py:*), Bash(python tools/fussnoten_ordnen.py:*), Bash(python tools/bibliothek_suchen.py:*)
---

# Urteil verständlich

Du schreibst über eine Gerichtsentscheidung so, dass ein Bauherr, ein Wohnungseigentümer oder eine Hausverwaltung sie in unter zehn Minuten liest, versteht und weiß, was sie für ihn bedeutet. Kein Jurist, kein Fachkollege – ein Leser, der gerade selbst baut, kauft oder verwaltet und sich fragt: „Was heißt das für mich?“

## Zuerst lesen

**Lies `.claude/skills/fachartikel/SKILL.md` und `.claude/skills/urteilsbesprechung/SKILL.md` vollständig, bevor du irgendetwas anderes tust.** Aus dem Urteilsbesprechungs-Skill gelten unverändert: die Kandidatenauswahl (Schritte 1 bis 5 – Themenfeld, Tragfähigkeit, Volltext, **nur entschiedene Fälle**), das Sichern der Fundstelle, der **Belegauszug** vor dem Schreiben (Schritt 6), die Randnummernpflicht, die Zuschreibungsregel, der Abschnitt „Genauigkeit gegenüber dem Volltext“, „Was du in diesem Format nicht tust“, das Frontmatter mit `gericht`, `aktenzeichen`, `ecli`, `entscheidungsdatum`, `fundstelle`, die Quellenregeln, Dateiname und Branch sowie die zusätzlichen PR-Blöcke. Aus dem Fachartikel-Skill gelten die harten Regeln, die Zitierfähigkeit, die Dreifach-Absicherung für Normen, die Fachbibliothek, Fußnoten, Seite bauen, Abgabe und Abschlussnachricht.

**Dieser Skill ersetzt** Format, Stil, Umfang, Aufbau, FAQ und Prüfschwellen. Bei Widerspruch zu den beiden anderen Skills gilt in diesen Punkten dieser Skill; in allem, was die Genauigkeit gegenüber dem Urteil betrifft, gilt der strengere Satz.

Nach deinem Lauf prüfen die Faktenprüfung (jede Aussage über die Entscheidung an ihrer Randnummer) und die Schlussprüfung (jede Fußnote am Quelltext) deinen Entwurf. Was nicht trägt, wird gestrichen.

## Format und Leser

`format` ist `Urteil verständlich`. `kategorie` ist `Gutachten & Recht`, bei Entscheidungen zu Kalkulation, Nachträgen oder Bauablauf `Baubetrieb`. `zielgruppe` nennt die Beteiligten, die der Fall betrifft – etwa `Privat, Hausverwaltung` bei einem Streit um Mängel am Gemeinschaftseigentum, `Gewerblich` bei einem Streit zwischen Unternehmer und Auftraggeber. Für die Sprache gilt **Gruppe A** des Fachartikel-Skills (einfache Sprache, Anrede „Sie“, Fachbegriffe im selben Satz erklärt), obwohl es eine Urteilsbesprechung ist.

## Keine offenen Prüfpunkte

Der Auftraggeber will Beiträge ohne TODO-Blöcke. Die Reihenfolge bei einer unsicheren Aussage ist deshalb: erstens tiefer recherchieren – Volltext, Fachbibliothek, Primärquelle, Bestätigung; zweitens die Aussage weglassen oder so umschreiben, dass sie ohne die unsichere Angabe richtig bleibt; drittens, **nur** wenn der Beitrag ohne die Aussage nicht funktioniert, ein TODO nach dem Format des Fachartikel-Skills. Der Zielwert ist null. Zwei oder mehr TODOs bedeuten in der Regel, dass die Entscheidung oder der Zuschnitt nicht passt – dann Schritt 4 des Urteilsbesprechungs-Skills: andere Entscheidung.

## Umfang

Höchstens 10 Minuten Lesezeit: **1.200 bis 2.000 Wörter Haupttext**, Zielwert 1.400 bis 1.800. Das ist ein Drittel einer Fachbesprechung. Auswählen statt verdichten: Du erzählst **einen** Streit, **eine** Entscheidung und **die zwei oder drei Gründe**, die sie tragen. Nebenaspekte, Hilfserwägungen und prozessuale Feinheiten nennst du in einem Satz oder gar nicht – aber du verschweigst keinen Befund, der die Aussage einschränkt (Regel „Keine These gegen einen Befund“).

Messung: `wc -w` auf die Datei vor den Anhängen muss zwischen **1.350 und 2.150** liegen, plus 100 je TODO-Block. Darunter erweiterst du in höchstens **zwei** Runden à mindestens 150 Wörter, darüber kürzt du in einer Runde ganze Absätze. `wortzahl` ist der Messwert minus 150, minus 100 je TODO, abgerundet auf Zehner.

## Aufbau

Drei bis fünf H2 im Hauptteil, dazu `## Häufige Fragen` mit drei bis vier Fragen. Die H2 sind sprechende Sätze oder Fragen, keine Funktionsnamen. Die Funktionen in dieser Reihenfolge:

**Erster Absatz – die Geschichte und die Antwort.** Drei bis fünf Sätze, 60 bis 110 Wörter. Erst die Szene, wie sie im Urteil steht: Wer wollte was von wem, und woran hing es? Dann in einem Satz, was das Gericht entschieden hat, mit Gericht, Datum und Aktenzeichen. Jede Tatsache mit Randnummer. Der Leser kennt nach diesem Absatz Konflikt und Ausgang. Kein „In diesem Beitrag“, keine Definition, keine Vorrede.

**Worum gestritten wurde.** Der Sachverhalt als Geschichte in eigenen Worten: Reihenfolge der Ereignisse, die Beträge und Fristen, um die es ging (nur aus dem Urteil, mit Randnummer), die Positionen beider Seiten – beide fair, keine gewinnt in deinem Text. Beteiligte heißen „der Bauherr“, „das Unternehmen“, „die Eigentümer“, „die Hausverwaltung“. Keine Namen, keine Orte.

**Was das Gericht entschieden hat – und warum.** Die tragenden Gründe in der Reihenfolge des Gerichts, jeder in ein bis zwei Absätzen Alltagssprache. Die Vorschrift, die das Gericht anwendet, nennst du beim Namen und erklärst im selben Satz, was sie regelt („§ 640 BGB, also die Regel dazu, wann ein Bau als abgenommen gilt“). Paragrafenketten bleiben in der Fußnote. Gewichtungen des Gerichts („regelmäßig“, „im Ergebnis“, „untergeordnet“) übernimmst du.

**Was das für Sie bedeutet.** Der längste Abschnitt. Was sollte ein Bauherr, ein Eigentümer, eine Hausverwaltung aus diesem Fall mitnehmen – für Verträge, Dokumentation, Fristen, Abnahme, Beweissicherung? Ein bis zwei typisierte Beispiele („Wer als Bauherr …“). Keine Rechtsfolgen versprechen, keine Prognose; der Anwaltshinweis nach Regel 7 steht in diesem Abschnitt. Hier gehört der interne Verweis auf die Leistung des Büros hin (Beweissicherung, Gutachten, Bauherrenvertretung – ein ruhiger Satz).

**Was das Urteil nicht sagt.** Drei bis fünf Sätze: die Grenze des Falls, und ob die Entscheidung endgültig ist – nur, was der Volltext dazu sagt (Revision zugelassen oder nicht, mit Randnummer). Nichts über Rechtsmittel, die eingelegt sein könnten.

**Häufige Fragen.** Drei bis vier Fragen, wie Betroffene sie stellen („Gilt das auch für meinen Vertrag mit einem Handwerker?“). Jede Antwort drei bis fünf Sätze, jede Aussage über das Urteil mit Randnummer, keine Zuspitzung über das Urteil hinaus.

Danach `## Hinweis`, Autorenkasten und `## Quellen und Fußnoten` wie im Fachartikel-Skill.

## So schreibst du, dass es spannend und verständlich ist

- **Konflikt zuerst, Auflösung danach.** Der Leser will wissen, wie es ausgeht – das trägt den Text. Spannung entsteht aus dem echten Streit, nie aus Dramatisierung: keine Ausrufezeichen, kein „Schock-Urteil“, kein Clickbait, keine Wertung der Parteien.
- **Sätze bis 20 Wörter, ein Gedanke je Satz, Aktiv.** Kein Nominalstil („die Geltendmachung des Anspruchs“ → „den Anspruch geltend machen“ → besser: „das Geld verlangen“).
- **Jeder Fachbegriff wird im selben Satz erklärt** – auch Abnahme, Nachtrag, Gewährleistung, Werklohn, Vorbehalt, fiktive Abnahme, Beweislast. Danach darfst du ihn verwenden.
- **Zahlen greifbar machen:** Beträge, Fristen und Zeiträume aus dem Urteil nennst du konkret (mit Randnummer) und ordnest sie ein („rund ein Drittel der Auftragssumme“ – nur wenn die Rechnung aus den Zahlen des Urteils folgt).
- **Anschaulich nur mit Tatsachen aus dem Urteil:** Der Leser soll die Baustelle, das Protokoll, den Brief vor Augen haben – aber nur so, wie der Volltext sie beschreibt. Kein Adjektiv, kein Detail, keine Stimmung, die dort nicht steht („mitten im Winter“, „verärgert“, „die Baustelle stand still“ nur mit Randnummer).
- **Absätze tragen sich selbst** (Zitierfähigkeit): kein Absatz beginnt mit „dabei“, „dies“, „hier“; Pronomen werden aufgelöst; das Thema steht in jedem Absatz.
- **Fußnoten sparsam:** die Entscheidung als Fußnote 1 bei der ersten Nennung, danach nur Randnummern im Text; jede weitere Norm oder Quelle mit Fußnote nach dem Fachartikel-Skill. Richtwert drei bis sechs Fußnoten. Fachliteratur aus der Fachbibliothek ist willkommen, wenn sie eine Aussage für die Praxis trägt.

## Vereinfachen, ohne zu verfälschen

Einfache Sprache verändert die Form, nie den Inhalt. **Diese Regeln gehen jeder Stilregel dieses Skills vor.** Sie stammen aus den Korrekturen der Faktenprüfung an den ersten Beiträgen dieses Formats (15 und 23 Korrekturen je Beitrag); jede Regel verhindert eine der häufigsten Fehlerarten.

1. **Randnummer aus dem Belegauszug, nicht aus der Erinnerung.** Jeden Satz mit „(Rn. n)“ schreibst du aus der Zeile des Belegauszugs, die diese Randnummer trägt. Fasst ein Satz zwei Stellen zusammen, nennt er beide Randnummern. Findest du die Stelle im Belegauszug nicht, liest du sie im Volltext nach, bevor du den Satz schreibst. *Häufigster Fehler: Die Randnummer steht am Satz, trägt ihn aber nicht.*
2. **Parteivortrag bleibt Parteivortrag.** Was eine Seite behauptet, schreibst du als Behauptung („nach Darstellung der Vermieterin“, „das Unternehmen meinte“) – auch wenn es für die Geschichte spannender wäre, es als Tatsache zu erzählen. Als Tatsache gilt nur, was das Gericht feststellt oder als unstreitig bezeichnet. Gutachter, Vorinstanz und Gericht werden auseinandergehalten.
3. **Mehrere Gründe bleiben mehrere Gründe.** Nennt das Gericht zwei Gründe, die *zusammen* tragen („leicht zu erkennen **und** schnell und günstig zu beseitigen“), machst du daraus weder einen einzigen noch zwei austauschbare. Die Reihenfolge des Gerichts und seine Gewichtungswörter („jedenfalls“, „hilfsweise“, „im Übrigen“) bleiben erhalten.
4. **Der Verfahrensweg ist vollständig.** Welche Instanz hat was entschieden, wer hat Rechtsmittel eingelegt, gab es einen Parteiwechsel (etwa einen Erben, der den Rechtsstreit fortführt), wie endete es? Ein Satz genügt, aber er darf nichts auslassen.
5. **Keine Verallgemeinerung über den Fall hinaus** – besonders in Titel, `meta_beschreibung`, erstem Absatz und FAQ. „Wann ist eine verschmutzte Fassade ein Mangel?“ beantwortest du mit dem, was das Gericht für *diesen* Vertrag und *diese* Umstände entschieden hat, und sagst das auch so.
6. **Zahlen, Daten, Beträge, Fristen** übernimmst du wörtlich aus dem Belegauszug; Zeiträume rechnest du aus den Daten aus, statt sie zu schätzen.
7. **Kein beschreibendes Wort ohne Grundlage.** „Neubau“, „Einfamilienhaus“, „kleiner Betrieb“, „langjähriger Kunde“ nur, wenn der Volltext es sagt.

Bevor du den Entwurf committest, liest du ihn einmal vollständig gegen den Belegauszug und prüfst jeden Satz mit Randnummer auf die Regeln 1 bis 3 – das ist der Schritt, der die meisten späteren Korrekturen erspart.

## Prüfung vor dem Commit

Es gilt die Prüfliste des Fachartikel-Skills mit diesen abweichenden Sollwerten: Wortzahl nach diesem Skill; 3 bis 5 H2 im Hauptteil; FAQ 3 bis 4; Sätze bis 20 Wörter (Grep auf Sätze mit mehr als 20 Wörtern ist nicht mechanisch möglich – prüfe beim Lesen deiner eigenen Write- und Edit-Eingaben); jeder Absatz über die Entscheidung mit „(Rn. n)“ (der Seitenbauer meldet fehlende Randnummern als `PRUEFUNG`); keine Wendung „ständige Rechtsprechung“, „gefestigt“, „herrschende Meinung“ ohne Quelle; keine Aussage zu Rechtsmitteln über den Volltext hinaus. `python tools/artikel_generator.py` vor dem Commit; die Lesezeit muss 4 bis 10 Minuten zeigen.

## Pull Request

Es gilt die Vorlage des Fachartikel-Skills mit den Blöcken des Urteilsbesprechungs-Skills („Besprochene Entscheidung“ mit Verfahrensweg und Abschluss, „Geprüfte und verworfene Kandidaten“, „Abdeckungslücke“). Der Dreizeiler oben sagt in normaler Sprache, worum es ging und was der Leser mitnimmt. Unter „Worauf ich mir am unsichersten bin“ nennst du zusätzlich die Stelle, an der du am stärksten vereinfacht hast, mit der Randnummer.
