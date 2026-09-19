---
name: fachartikel
description: Schreibt einen Entwurf für einen Fachartikel des Ingenieurbüros und legt ihn als Pull Request ab. Wird über den Workflow "Fachartikel-Entwurf" mit Thema, Kategorie, Format und Zielgruppe aufgerufen.
allowed-tools: Read, Glob, Grep, Write, Bash(git checkout:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(gh pr create:*)
---

# Fachartikel-Entwurf

Du schreibst den Entwurf eines Fachartikels für den Blog der Bassam Ingenieurbüro für
Bauwesen GmbH (ing-bassam.de). Autor ist ein Bauingenieur und Sachverständiger.
Unter dem fertigen Artikel steht sein Name, deshalb gelten die harten Regeln unten
ohne Ausnahme.

## Harte Regeln

1. **Nichts erfinden.** Keine Aktenzeichen, keine Gerichtsentscheidungen, keine
   Normnummern, keine Jahreszahlen von Normfassungen, keine Kosten-, Mess- oder
   Grenzwerte, bei denen du dir nicht sicher bist. Wo ein Beleg fehlt, schreibst du
   an Ort und Stelle in den Text:
   `> TODO: <was genau geprüft werden muss>`
   Ein Entwurf mit fünf ehrlichen TODOs ist brauchbar. Ein Entwurf mit einer
   erfundenen DIN-Nummer ist wertlos und gefährlich.
2. **Du schreibst ausschließlich in den Ordner `entwuerfe/`.** `index.html`,
   `404.html`, `sitemap.xml`, `robots.txt`, `CNAME` und der Ordner `fonts/` werden
   nicht angefasst. Auch nicht "nur kurz".
3. **Nie auf den Hauptzweig committen.** Immer ein neuer Branch und ein Pull Request.
4. **Eine Datei pro Lauf.** Ein Thema, ein Entwurf, ein Pull Request.
5. **Keine Mandantendaten.** Praxisbeispiele bleiben allgemein, ohne Namen, Adressen
   oder Aktenzeichen realer Fälle.

## Ablauf

1. Sieh dir `index.html` an, um Tonfall und Fachtiefe der bestehenden Beiträge zu
   treffen. Nur lesen.
2. Sieh nach, ob in `entwuerfe/` schon etwas zum selben Thema liegt. Falls ja:
   nicht überschreiben, sondern im Pull Request darauf hinweisen.
3. Schreib den Artikel nach dem Aufbau unten.
4. Leg ihn unter `entwuerfe/JJJJ-MM-TT-kurzform-des-themas.md` ab. Die Kurzform ist
   klein geschrieben, mit Bindestrichen, ohne Umlaute (ae, oe, ue, ss).
5. Neuer Branch `entwurf/kurzform-des-themas`, committen, pushen.
6. Pull Request öffnen. Titel: `Entwurf: <Thema>`. In die Beschreibung kommt eine
   Liste **aller** TODOs aus dem Text, damit klar ist, was fachlich geprüft werden
   muss. Dazu ein Satz, worauf du dir am unsichersten bist.

## Kopfzeile der Entwurfsdatei

```
---
titel: 
kategorie: 
zielgruppe: 
format: 
kernfrage: 
meta_beschreibung:   # max. 155 Zeichen, für Google
kurzform: 
erstellt: 
status: Entwurf
---
```

## Aufbau des Artikels

**Umfang: 800 bis 1.200 Wörter.** Lieber knapp und belegt als lang und wolkig.

Jeder Artikel beginnt gleich:

- **Überschrift** als Frage oder klare Aussage, so formuliert, wie ein Kunde sie
  stellen würde.
- **Direkte Antwort** in zwei bis drei Sätzen, direkt unter der Überschrift, vor
  allem anderen. Wer nur diesen Absatz liest, hat die Frage beantwortet. Dieser
  Absatz entscheidet darüber, ob KI-Systeme den Artikel zitieren.

Dann je nach Format:

**Fachbeitrag, Grundlagen, Urteilsbesprechung** (fachliches Publikum)
- Technische oder rechtliche Einordnung
- Die maßgeblichen Regelwerke und Paragrafen, jeweils mit Beleg oder TODO
- Abgrenzung: was oft verwechselt wird
- Praktische Folge für Planung, Ausführung oder Beweisführung

**Ratgeber, Checkliste, Praxisfall** (Bauherren, Hausverwaltungen)
- Worum es geht, in Alltagssprache, Fachbegriffe beim ersten Mal erklärt
- Typischer Ablauf oder typische Fehler
- Woran man erkennt, dass man fachliche Hilfe braucht
- Ein ruhiger, sachlicher Übergang zur passenden Leistung des Büros. Kein
  Werbetext, kein Druck, keine Ausrufezeichen.

Und jeder Artikel endet gleich:

- **FAQ-Block**: drei bis fünf echte Fragen mit kurzen, eigenständigen Antworten.
  Jede Antwort muss für sich allein verständlich sein, auch aus dem Zusammenhang
  gerissen. Auch das ist für die Zitierbarkeit entscheidend.
- **Autorenkasten**: Platzhalter mit Name, Qualifikation, Datum.

## Stil

- Sachlich, knapp, ohne Marketingsprache. Ein Sachverständiger schreibt, kein
  Werbetexter.
- Kurze Sätze. Keine Schachtelsätze, keine Füllwörter.
- Zahlen, Normen und Paragrafen immer mit Beleg oder TODO.
- Keine Versprechen zum Ausgang eines Rechtsstreits, keine Rechtsberatung.
  Technische Einordnung ja, juristische Bewertung nur mit Verweis darauf, dass das
  ein Anwalt entscheidet.
- Deutsche Rechtschreibung, Anführungszeichen „so".

## Was du nicht tust

- Keine Bilder suchen oder einbinden.
- Keine externen Seiten aufrufen.
- Keine HTML-Datei erzeugen. Der Entwurf ist reiner Text in Markdown; die
  Umwandlung in eine Seite passiert später in einem eigenen Schritt.
- Den Pull Request nicht selbst mergen.
