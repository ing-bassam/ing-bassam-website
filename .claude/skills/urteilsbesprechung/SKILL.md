---
name: urteilsbesprechung
description: Wählt aus einer vorsortierten Liste amtlicher Gerichtsentscheidungen eine baurelevante aus, prüft sie am Volltext und schreibt daraus eine Urteilsbesprechung als Fachartikel für ing-bassam.de. Wird vom Workflow „Urteilsbesprechung" mit dem Pfad zur Kandidatenliste aufgerufen und läuft ohne Rückfragen.
allowed-tools: Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, Bash(git checkout:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr list:*), Bash(wc:*)
---

# Urteilsbesprechung

Du schreibst die Besprechung einer Gerichtsentscheidung für den Blog der Bassam Ingenieurbüro für Bauwesen GmbH. Leser sind Bauherren, Bauunternehmer, Hausverwaltungen und Kollegen – keine Juristen. Der Artikel erklärt, was die Entscheidung **für die Baupraxis** bedeutet: für Gutachten, Kalkulation, Nachträge, Bauablauf und Dokumentation.

## Zuerst lesen

**Lies `.claude/skills/fachartikel/SKILL.md` vollständig, bevor du irgendetwas anderes tust.** Alles dort gilt unverändert: die harten Regeln, der Aufbau, die Fließtext-Regel, die Zitierfähigkeit, die Fußnoten, die Prüfung vor dem Commit, die Abgabe, der Frontmatter-Kopf. Dieser Skill ändert nur die unten genannten Punkte und ergänzt sie. Bei Widerspruch gilt der jeweils strengere Satz.

Das Format ist immer `Rechtsprechung`, damit Gruppe B gilt: wissenschaftlicher Aufbau, dichte Argumentation, Fachsprache ohne Vereinfachung.

## Was diesen Lauf unterscheidet

Nicht du suchst das Thema – die Entscheidung bringt es mit. Der Workflow hat dir unter dem im Prompt genannten Pfad eine Kandidatenliste hingelegt. Sie ist **vorsortiert, nicht geprüft**: Ein Treffer kann das Wort „Bauvertrag" enthalten und trotzdem eine Kostenbeschwerde sein.

## Ablauf

Die Turn-Regel aus dem Fachartikel-Skill gilt: Beende vor der Abschlussnachricht nie einen Turn ohne Tool-Aufruf.

1. **Kandidatenliste lesen** (Read). Fehlt sie oder enthält sie keine Kandidaten, endest du mit `ERGEBNIS: KEINE KANDIDATEN`, ohne Branch und ohne Pull Request.

2. **Vorauswahl.** Nimm die ersten sechs bis acht Kandidaten in der Reihenfolge der Liste. Berlin und Brandenburg stehen bewusst oben; gib ihnen den Vorzug, solange die Entscheidung fachlich trägt.

3. **Volltext prüfen** (WebFetch, höchstens 12 Abrufe). Für jeden Kandidaten in der Reihenfolge der Liste: Hole den Volltext von der in der Liste genannten amtlichen Adresse und beantworte drei Fragen.
   - *Betrifft sie das Themenfeld?* Bauvertrag, Werkvertrag am Bau, Architekten- oder Ingenieurvertrag, Baumangel, Abnahme, Werklohn, Nachtrag, gestörter Bauablauf, Bauzeit, Behinderung, Kalkulation, Planungsfehler, Beweissicherung, Sachverständigenbeweis am Bau. Reine Miet-, Kauf-, Insolvenz-, Vergabe-, Kosten- oder Verfahrensfragen ohne Baubezug scheiden aus, auch wenn ein Suchbegriff vorkommt.
   - *Trägt sie einen Beitrag?* Eine Entscheidung trägt, wenn sie eine Rechtsfrage klärt, eine Abgrenzung schärft, von der bisherigen Linie abweicht oder eine für die Praxis wiederkehrende Konstellation behandelt. Eine Nichtzulassungsbeschwerde ohne Begründung, ein Hinweisbeschluss ohne Aussage oder eine reine Einzelfallwürdigung trägt nicht.
   - *Reicht der Volltext?* Enthält die Entscheidung Tatbestand und Entscheidungsgründe, oder nur einen Tenor? Ohne Gründe kannst du sie nicht besprechen.

   Notiere je Kandidat in einem Satz, warum er taugt oder ausscheidet. Diese Notizen kommen später in den Pull Request.

4. **Eine auswählen.** Genau eine Entscheidung wird besprochen. Findest du unter den geprüften Kandidaten keine geeignete, prüfe weitere aus der Liste. Ist die Liste erschöpft, endest du mit `ERGEBNIS: KEINE GEEIGNETE ENTSCHEIDUNG` und nennst in der Abschlussnachricht, was du geprüft und warum du es verworfen hast. Du weichst nicht auf eine Entscheidung außerhalb der Liste aus.

5. **Fundstelle dreifach sichern.** Bevor du schreibst, stimmen Gericht, Spruchkörper, Entscheidungsdatum, Aktenzeichen und – falls vorhanden – ECLI **wörtlich** mit dem Volltext auf der amtlichen Seite überein. Du übernimmst sie von dort, nie aus der Kandidatenliste und nie aus dem Gedächtnis. Weicht die Liste vom Volltext ab, gilt der Volltext, und du vermerkst die Abweichung im Pull Request. Das ersetzt für diese eine Fundstelle die dreistufige Absicherung des Fachartikel-Skills; für **jede weitere** genannte Entscheidung, Norm oder Vorschrift gilt sie unverändert.

6. **Schreiben, prüfen, abgeben** wie im Fachartikel-Skill beschrieben.

## Quellen

Zulässig sind ausschließlich amtliche Quellen:

- `rechtsprechung-im-internet.de` – Bundesministerium der Justiz und Bundesamt für Justiz
- `gerichtsentscheidungen.brandenburg.de` – Landesrechtsportal Brandenburg
- Rechtsprechungsdatenbanken weiterer Länder über `justiz.de/onlinedienste/rechtsprechung`
- `gesetze-im-internet.de` für Gesetzeswortlaut
- die Internetauftritte der Gerichte selbst

Nicht zulässig sind Anwaltskanzlei-Blogs, Portale wie dejure oder openJur als **Beleg** und KI-Zusammenfassungen. Du darfst dort nachsehen, ob eine Entscheidung besprochen wurde, belegst aber immer an der amtlichen Fundstelle.

Ein Hinweis zur Abdeckung, der in jeden Pull Request gehört, wenn keine Berliner Entscheidung dabei ist: Die Berliner Datenbank ist ohne JavaScript nicht abrufbar, Entscheidungen des Kammergerichts fehlen deshalb systematisch.

## Aufbau der Besprechung

Der Aufbau aus dem Fachartikel-Skill gilt, mit dieser Belegung der H2-Abschnitte. Sechs bis zehn H2, Fließtext, keine H3.

Der **erste Absatz** nennt in zwei bis drei Sätzen, was das Gericht entschieden hat und was daraus für die Baupraxis folgt – ohne Vorrede, ohne „In diesem Beitrag". Gericht, Datum und Aktenzeichen stehen im ersten oder zweiten Satz.

Danach in dieser Reihenfolge:

- **Worum gestritten wurde.** Der Sachverhalt in eigenen Worten, so weit er aus der Entscheidung hervorgeht. Beteiligte heißen „der Bauherr", „das Unternehmen", „der Architekt". Keine Namen, keine Orte, auch wenn sie im Volltext stehen.
- **Der Verfahrensgang**, knapp: Was hat die Vorinstanz entschieden, was hat das Gericht daran geändert.
- **Die tragenden Gründe.** Die Argumentation des Gerichts, nachvollziehbar wiedergegeben, mit den maßgeblichen Vorschriften. Hier gehört der Kern des Beitrags hin.
- **Einordnung.** Steht die Entscheidung auf der bisherigen Linie, schärft sie eine Abgrenzung, weicht sie ab? Abweichende Auffassungen benennst du als solche.
- **Was daraus für die Baupraxis folgt.** Der eigentliche Zweck des Beitrags: Was bedeutet die Entscheidung für Dokumentation, Aufmaß, Nachtragsbegründung, Bauzeitnachweis, Mängelrüge, Beweissicherung oder die Arbeit des Sachverständigen? Dieser Abschnitt ist der längste.
- **Was die Entscheidung nicht sagt.** Die Grenze des Anwendungsbereichs. Wer sie überdehnt, zieht falsche Schlüsse.

Danach FAQ, Hinweis, Autorenkasten und Quellenverzeichnis wie im Fachartikel-Skill.

## Zitierweise

Im Text bei der ersten Nennung vollständig: Gericht, Spruchkörper, Datum, Aktenzeichen, dazu die Fußnote mit ECLI und Adresse der amtlichen Fundstelle. Danach verkürzt.

Beispiel: „Das Oberlandesgericht Brandenburg hat mit Urteil vom 4. Juni 2026 (Aktenzeichen 10 U 14/24) entschieden, dass …"

Vorschriften nennst du mit Kurzbezeichnung und Paragraf, bei der ersten Nennung je Abschnitt vollständig, belegt über `gesetze-im-internet.de`.

## Was du in diesem Format nicht tust

- **Keine Prognose.** Du sagst nicht, wie ein vergleichbarer Fall ausginge oder wie ein Revisionsverfahren enden wird. Ist die Entscheidung nicht rechtskräftig oder ist ein Rechtsmittel anhängig und das aus dem Volltext ersichtlich, schreibst du es hin.
- **Keine Partei ergreifen.** Weder Bauherr noch Unternehmer bekommen Recht zugesprochen. Du referierst, was das Gericht entschieden hat.
- **Keine Handlungsempfehlung mit Rechtsfolge.** „Wer so dokumentiert, gewinnt den Prozess" ist verboten. Erlaubt ist: „Das Gericht hat die Dokumentation in diesem Fall als ausreichend angesehen; welche Anforderungen im Einzelfall gelten, beurteilt ein Rechtsanwalt."
- **Keine erfundenen Parallelentscheidungen.** Eine weitere Entscheidung nennst du nur, wenn du sie in diesem Lauf an einer amtlichen Quelle bestätigt hast.
- **Keine Mandantendaten, keine Klarnamen** aus dem Volltext.

## Frontmatter

Zusätzlich zu den Feldern aus dem Fachartikel-Skill, unmittelbar hinter `kernfrage`:

```
gericht: <Gericht und Spruchkörper, wie im Volltext>
aktenzeichen: <wie im Volltext>
ecli: <falls vorhanden, sonst leer>
entscheidungsdatum: <JJJJ-MM-TT>
fundstelle: <Adresse der amtlichen Fundstelle>
```

`format` ist `Rechtsprechung`. `kategorie` ist `Gutachter & Recht`, außer die Entscheidung betrifft eindeutig Baubetrieb, Kalkulation oder Nachtragsmanagement – dann `Baubetrieb`. `quelle` ist `rechtsprechung`. `notion_id` und `notion_url` bleiben leer: Das Thema stammt aus der Rechtsprechung, nicht aus dem Themenspeicher, und dieser Lauf schreibt nichts nach Notion.

Das Feld `aktenzeichen` ist wichtig: Der Kandidatenfinder liest es aus den vorhandenen Entwürfen und schlägt dieselbe Entscheidung kein zweites Mal vor.

## Umfang

Es gelten die 5.000 Wörter aus dem Fachartikel-Skill. Trägt die Entscheidung das nicht, **füllst du nicht auf**. Du erweiterst stattdessen die Einordnung: wie die Frage bisher behandelt wurde, welche bauwirtschaftliche oder bautechnische Bedeutung sie hat, was sie für Dokumentation und Beweisführung ändert. Trägt sie auch das nicht, war es die falsche Entscheidung – geh zurück zu Schritt 4 und nimm eine andere.

## Dateiname und Branch

Datei: `entwuerfe/JJJJ-MM-TT-<kurzform>.md`, wobei das Datum das des Laufs ist und die Kurzform das Thema beschreibt, nicht das Aktenzeichen. Gut: `bauzeitnachweis-gestoerter-bauablauf`. Schlecht: `olg-brandenburg-10-u-14-24`.

Branch: `entwurf/<kurzform>`. Titel des Pull Requests: `Entwurf: <Thema>`.

## Zusätzlich in den Pull Request

Über die Vorlage des Fachartikel-Skills hinaus:

```
### Besprochene Entscheidung

- Gericht: <…>
- Datum: <…>
- Aktenzeichen: <…>
- ECLI: <… oder „nicht vergeben">
- Fundstelle: <Adresse>
- Rechtskraft: <aus dem Volltext ersichtlich / nicht ersichtlich>

### Geprüfte und verworfene Kandidaten

<je eine Zeile: Gericht, Datum, Aktenzeichen – Grund der Verwerfung>

### Abdeckungslücke

<Hinweis zum Kammergericht, falls keine Berliner Entscheidung dabei ist>
```
