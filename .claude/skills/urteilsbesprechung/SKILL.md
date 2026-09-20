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

3. **Volltext prüfen** (Read). Die Volltexte liegen bereits als Textdatei vor; die Liste nennt bei jedem Kandidaten den Pfad. Öffne sie mit **Read**, nicht mit WebFetch. Der Umweg über das Netz ist hier nicht nur unnötig, sondern beim Bund unmöglich: Dort liefert die amtliche Quelle ein ZIP-Archiv, das WebFetch nicht lesen kann. Das Skript hat es bereits entpackt.

   Fehlt bei einem Kandidaten der Pfad und steht dort „Achtung: Volltext nicht abrufbar", überspringe ihn und vermerke das im Pull Request.

   Für jeden Kandidaten in der Reihenfolge der Liste beantwortest du drei Fragen.
   - *Betrifft sie das Themenfeld?* Bauvertrag, Werkvertrag am Bau, Architekten- oder Ingenieurvertrag, Baumangel, Abnahme, Werklohn, Nachtrag, gestörter Bauablauf, Bauzeit, Behinderung, Kalkulation, Planungsfehler, Beweissicherung, Sachverständigenbeweis am Bau. Reine Miet-, Kauf-, Insolvenz-, Vergabe-, Kosten- oder Verfahrensfragen ohne Baubezug scheiden aus, auch wenn ein Suchbegriff vorkommt.
   - *Trägt sie einen Beitrag?* Eine Entscheidung trägt, wenn sie eine Rechtsfrage klärt, eine Abgrenzung schärft, von der bisherigen Linie abweicht oder eine für die Praxis wiederkehrende Konstellation behandelt. Eine Nichtzulassungsbeschwerde ohne Begründung, ein Hinweisbeschluss ohne Aussage oder eine reine Einzelfallwürdigung trägt nicht.
   - *Reicht der Volltext?* Enthält die Entscheidung Tatbestand und Entscheidungsgründe, oder nur einen Tenor? Ohne Gründe kannst du sie nicht besprechen.
   - *Ist der Streit entschieden?* Besprochen wird nur, was die Instanz abschließt. Das ist der wichtigste Filter, denn ein Beitrag über einen Fall, der weiterläuft, veraltet mit der nächsten Entscheidung.

     **Geeignet:** ein Endurteil, das den Rechtsstreit in der Instanz vollständig erledigt; jede Entscheidung des Bundesgerichtshofs, weil dort keine weitere Tatsacheninstanz folgt; ein Berufungsurteil, in dem die Revision **nicht** zugelassen wurde.

     **Nicht geeignet:** Teilurteil, Grundurteil, Zwischenurteil, Vorbehaltsurteil und Versäumnisurteil, weil über Grund oder Höhe noch gestritten wird; jedes Urteil, in dem die Revision **zugelassen** wurde, weil der Fall dann beim Bundesgerichtshof weitergeht; Hinweisbeschlüsse; Entscheidungen im einstweiligen Rechtsschutz; Beschlüsse über Prozesskostenhilfe, Streitwert oder Kosten.

     Ob die Revision zugelassen wurde, steht am Ende der Entscheidungsgründe. Ob es sich um ein Teil- oder Grundurteil handelt, steht im Tenor oder in der Bezeichnung. Steht dort nichts davon, ist es ein Endurteil. Dass gegen ein Berufungsurteil ohne zugelassene Revision noch eine Nichtzulassungsbeschwerde laufen kann, steht der Besprechung nicht entgegen – es wird im Text und im Pull Request vermerkt.

   Die Liste nennt je Kandidat die Zahl der gefundenen Begriffe aus dem Themenfeld. Das ist ein grober Hinweis, keine Aussage über die Eignung: Ein hoher Wert kann auch eine Kostenentscheidung in einer Bausache treffen, ein niedriger eine grundlegende Entscheidung. Du liest trotzdem selbst.

   Notiere je Kandidat in einem Satz, warum er taugt oder ausscheidet. Diese Notizen kommen später in den Pull Request.

4. **Eine auswählen.** Genau eine Entscheidung wird besprochen. Findest du unter den geprüften Kandidaten keine geeignete, prüfe weitere aus der Liste. Ist die Liste erschöpft, endest du mit `ERGEBNIS: KEINE GEEIGNETE ENTSCHEIDUNG` und nennst in der Abschlussnachricht, was du geprüft und warum du es verworfen hast. Du weichst nicht auf eine Entscheidung außerhalb der Liste aus.

5. **Fundstelle sichern.** Gericht, Spruchkörper, Entscheidungsdatum, Aktenzeichen und – falls vergeben – ECLI übernimmst du **wörtlich aus dem Kopf der Volltextdatei**. Dieser Kopf stammt unverändert aus der amtlichen Quelle; das Skript hat nichts umformuliert. Niemals aus dem Gedächtnis, niemals aus der Überschrift der Kandidatenliste.

   Liegt die Entscheidung bei einer Landesdatenbank und ist die Fundstelle eine gewöhnliche Internetadresse, die sich ohne JavaScript lesen lässt (Brandenburg, Nordrhein-Westfalen), rufst du sie zusätzlich einmal mit WebFetch ab und vergleichst Datum und Aktenzeichen. Bei den juris-Portalen – erkennbar an einer Fundstelle der Form `…/perma?d=…` – entfällt der Abgleich, weil die Seite ihren Inhalt erst im Browser aufbaut; die Angaben stammen dort unmittelbar aus der Schnittstelle des Portals. Stimmt etwas nicht überein, gilt der Volltext, und du vermerkst die Abweichung im Pull Request. Beim Bund entfällt dieser Abgleich, weil dort nur das ZIP-Archiv bereitsteht – die Angaben stammen dann direkt aus der amtlichen XML-Datei darin.

   Das ersetzt für diese eine Fundstelle die dreistufige Absicherung des Fachartikel-Skills. Für **jede weitere** genannte Entscheidung, Norm oder Vorschrift gilt sie unverändert.

6. **Schreiben, prüfen, abgeben** wie im Fachartikel-Skill beschrieben.

## Quellen

Zulässig sind ausschließlich amtliche Quellen:

- `rechtsprechung-im-internet.de` – Bundesministerium der Justiz und Bundesamt für Justiz
- `gerichtsentscheidungen.brandenburg.de` – Landesrechtsportal Brandenburg
- `nrwesuche.justiz.nrw.de` – Justiz Nordrhein-Westfalen
- `gesetze.berlin.de` und die gleichartigen Portale von Baden-Württemberg, Hamburg, Hessen, Mecklenburg-Vorpommern, Rheinland-Pfalz, Saarland, Sachsen-Anhalt, Schleswig-Holstein und Thüringen
- Rechtsprechungsdatenbanken weiterer Länder über `justiz.de/onlinedienste/rechtsprechung`
- `gesetze-im-internet.de` für Gesetzeswortlaut
- die Internetauftritte der Gerichte selbst

Nicht zulässig sind Anwaltskanzlei-Blogs, Portale wie dejure oder openJur als **Beleg** und KI-Zusammenfassungen. Du darfst dort nachsehen, ob eine Entscheidung besprochen wurde, belegst aber immer an der amtlichen Fundstelle.

Berlin ist seit dem Ausbau der Quellen enthalten, einschließlich Kammergericht und Landgericht Berlin. Nicht durchsucht werden Bayern, Niedersachsen, Bremen und Sachsen; fehlt eine Entscheidung aus diesen Ländern, ist das kein Versehen, sondern eine bekannte Lücke – erwähne sie im Pull Request nur, wenn sie für das Thema erheblich wäre.

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

- **Keine Prognose.** Du sagst nicht, wie ein vergleichbarer Fall ausginge oder wie ein Revisionsverfahren enden wird. Im Abschnitt „Was die Entscheidung nicht sagt" hältst du fest, wie weit der Streit entschieden ist: ob die Revision zugelassen wurde, ob es sich um ein Endurteil handelt und ob nach dem Volltext noch etwas offen ist.
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
- Entscheidungsart: <Endurteil / Berufungsurteil ohne zugelassene Revision / BGH-Entscheidung>
- Abschluss: <was die Entscheidung erledigt, und was nach dem Volltext offen bleibt>

### Geprüfte und verworfene Kandidaten

<je eine Zeile: Gericht, Datum, Aktenzeichen – Grund der Verwerfung>

### Abdeckungslücke

<Hinweis zum Kammergericht, falls keine Berliner Entscheidung dabei ist>
```
