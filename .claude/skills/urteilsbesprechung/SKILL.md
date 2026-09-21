---
name: urteilsbesprechung
description: Wählt aus einer vorsortierten Liste amtlicher Gerichtsentscheidungen eine baurelevante aus, prüft sie am Volltext und schreibt daraus eine Urteilsbesprechung als Fachartikel für ing-bassam.de. Wird vom Workflow „Urteilsbesprechung" mit dem Pfad zur Kandidatenliste aufgerufen und läuft ohne Rückfragen.
allowed-tools: Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, Bash(git checkout:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr list:*), Bash(wc:*), Bash(python tools/artikel_generator.py:*), Bash(python tools/fussnoten_ordnen.py:*)
---

# Urteilsbesprechung

Du schreibst die Besprechung einer Gerichtsentscheidung für den Blog der Bassam Ingenieurbüro für Bauwesen GmbH. Leser sind Bauherren, Bauunternehmer, Hausverwaltungen und Kollegen – keine Juristen. Der Artikel erklärt, was die Entscheidung **für die Baupraxis** bedeutet: für Gutachten, Kalkulation, Nachträge, Bauablauf und Dokumentation.

## Zuerst lesen

**Lies `.claude/skills/fachartikel/SKILL.md` vollständig, bevor du irgendetwas anderes tust.** Alles dort gilt unverändert: die harten Regeln, der Aufbau, die Fließtext-Regel, die Zitierfähigkeit, die Fußnoten, die Prüfung vor dem Commit, die Abgabe, der Frontmatter-Kopf. Dieser Skill ändert nur die unten genannten Punkte und ergänzt sie. Bei Widerspruch gilt der jeweils strengere Satz.

Das Format ist immer `Rechtsprechung`, damit Gruppe B gilt: wissenschaftlicher Aufbau, dichte Argumentation, Fachsprache ohne Vereinfachung.

## Was diesen Lauf unterscheidet

Nicht du suchst das Thema – die Entscheidung bringt es mit. Der Workflow hat dir unter dem im Prompt genannten Pfad eine Kandidatenliste hingelegt. Sie ist **vorsortiert, nicht geprüft**: Ein Treffer kann das Wort „Bauvertrag" enthalten und trotzdem eine Kostenbeschwerde sein.

Nach deinem Lauf prüfen zwei unabhängige Instanzen deinen Entwurf: die **Faktenprüfung** jede Aussage über die Entscheidung an ihrer Randnummer, die **Schlussprüfung** jede Fußnote am heruntergeladenen Wortlaut der Quelle. Was nicht trägt, wird gestrichen und fehlt dann im Text. Was du nicht belegen kannst, schreibst du deshalb gar nicht erst.

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

     Ob die Revision zugelassen wurde, steht am Ende der Entscheidungsgründe. Ob es sich um ein Teil- oder Grundurteil handelt, steht im Tenor oder in der Bezeichnung. Steht dort nichts davon, ist es ein Endurteil. Dass gegen ein Urteil ohne zugelassene Revision noch eine Nichtzulassungsbeschwerde laufen kann, steht der Besprechung nicht entgegen. **Im Text steht dazu nur, was der Volltext sagt:** dass die Revision nicht zugelassen wurde, mit Randnummer. Ob eine Beschwerde eingelegt wurde oder noch möglich ist, bei welchem Gericht und in welcher Frist, schreibst du nicht – das weißt du nicht. Beim Beitrag zu OVG 6 A 1/25 war genau dieser Satz falsch. Im Pull Request steht unter „Abschluss“: „Rechtskraft nicht geprüft“.

   Die Liste nennt je Kandidat die Zahl der gefundenen Begriffe aus dem Themenfeld. Das ist ein grober Hinweis, keine Aussage über die Eignung: Ein hoher Wert kann auch eine Kostenentscheidung in einer Bausache treffen, ein niedriger eine grundlegende Entscheidung. Du liest trotzdem selbst.

   Notiere je Kandidat in einem Satz, warum er taugt oder ausscheidet. Diese Notizen kommen später in den Pull Request.

4. **Eine auswählen.** Genau eine Entscheidung wird besprochen. Findest du unter den geprüften Kandidaten keine geeignete, prüfe weitere aus der Liste. Ist die Liste erschöpft, endest du mit `ERGEBNIS: KEINE GEEIGNETE ENTSCHEIDUNG` und nennst in der Abschlussnachricht, was du geprüft und warum du es verworfen hast. Du weichst nicht auf eine Entscheidung außerhalb der Liste aus.

5. **Fundstelle sichern.** Gericht, Spruchkörper, Entscheidungsdatum, Aktenzeichen und – falls vergeben – ECLI übernimmst du **wörtlich aus dem Kopf der Volltextdatei**. Dieser Kopf stammt unverändert aus der amtlichen Quelle; das Skript hat nichts umformuliert. Niemals aus dem Gedächtnis, niemals aus der Überschrift der Kandidatenliste.

   Liegt die Entscheidung bei einer Landesdatenbank und ist die Fundstelle eine gewöhnliche Internetadresse, die sich ohne JavaScript lesen lässt (Brandenburg, Nordrhein-Westfalen), rufst du sie zusätzlich einmal mit WebFetch ab und vergleichst Datum und Aktenzeichen. Bei den juris-Portalen – erkennbar an einer Fundstelle der Form `…/perma?d=…` – entfällt der Abgleich, weil die Seite ihren Inhalt erst im Browser aufbaut; die Angaben stammen dort unmittelbar aus der Schnittstelle des Portals. Stimmt etwas nicht überein, gilt der Volltext, und du vermerkst die Abweichung im Pull Request. Beim Bund entfällt dieser Abgleich, weil dort nur das ZIP-Archiv bereitsteht – die Angaben stammen dann direkt aus der amtlichen XML-Datei darin.

   Das ersetzt für die **Fundstelle selbst** – Gericht, Datum, Aktenzeichen, ECLI – die dreistufige Absicherung des Fachartikel-Skills. **Es ersetzt nicht die Prüfung dessen, was du über die Entscheidung schreibst.** Jede solche Aussage muss an einer bestimmten Randnummer des Volltexts stehen und trägt diese Randnummer im Text (siehe Zitierweise); nach deinem Lauf vergleicht eine unabhängige Faktenprüfung jede Aussage mit genau dieser Stelle. Für **jede weitere** genannte Entscheidung, Norm oder Vorschrift gilt die dreistufige Absicherung unverändert.

6. **Belegauszug anlegen** (ein bis zwei Turns), bevor du schreibst. Lege mit Write im Verzeichnis der Kandidatenliste die Datei `belegauszug.md` an. Abweichend von Regel 3 des Fachartikel-Skills ist sie neben `pr-body.md` die zweite zulässige Datei außerhalb des Repositorys. Sie enthält:
   - den **Verfahrensweg** mit Randnummer: Hat das Gericht in erster Instanz entschieden, über eine Berufung oder über eine Revision? Gibt es eine Vorinstanz, und was hat sie entschieden?
   - den Tenor in eigenen Worten und die Randnummer, an der steht, ob die Revision zugelassen wurde;
   - für jede Aussage, die du über die Entscheidung treffen willst, die Randnummer mit einem **wörtlichen Belegstück** von höchstens 25 Wörtern: den Sachverhalt, jeden tragenden Grund in der Reihenfolge des Gerichts, jede Gewichtung („regelmäßig“, „untergeordnet“, „im Ergebnis“), jede Entscheidung, die das Gericht selbst anführt, und jede Norm, die es heranzieht, in der Fassung, die es nennt.

   Beim Schreiben ist diese Datei deine Grundlage für alles, was du über die Entscheidung sagst. Was nicht darin steht, schlägst du mit Grep im Volltext nach, bevor du es schreibst. Beim ersten Artikel dieses Agenten entstanden fünfzehn Abweichungen, weil über viele Züge aus der Erinnerung geschrieben wurde.

7. **Schreiben, prüfen, abgeben** wie im Fachartikel-Skill beschrieben.

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

Der Aufbau aus dem Fachartikel-Skill gilt, mit dieser Belegung der H2-Abschnitte. Sechs bis acht H2, Fließtext, keine H3.

Der **erste Absatz** nennt in zwei bis drei Sätzen, was das Gericht entschieden hat und was daraus für die Baupraxis folgt – ohne Vorrede, ohne „In diesem Beitrag". Gericht, Datum und Aktenzeichen stehen im ersten oder zweiten Satz.

Danach folgen diese Funktionen in dieser Reihenfolge. **Es sind Funktionen, keine Überschriften:** Jede H2 ist eine sprechende Aussage, die zu diesem Fall passt, und sie setzt nichts voraus, was der Belegauszug nicht trägt. Über dem Beitrag zu OVG 6 A 1/25 stand „Der Verfahrensgang und was das Gericht daran geändert hat“, obwohl das Oberverwaltungsgericht in erster Instanz entschieden hatte – es gab nichts zu ändern.

- **Worum gestritten wurde.** Der Sachverhalt in eigenen Worten, so weit er aus der Entscheidung hervorgeht. Beteiligte heißen „der Bauherr", „das Unternehmen", „der Architekt". Keine Namen, keine Orte, auch wenn sie im Volltext stehen.
- **Der Verfahrensgang**, knapp und nur, wenn es einen gibt: Was hat die Vorinstanz entschieden, was hat das Gericht daran geändert. Hat das Gericht in erster Instanz entschieden, entfällt dieser Abschnitt; Klage und Anträge stehen dann im Sachverhalt.
- **Die tragenden Gründe.** Die Argumentation des Gerichts, nachvollziehbar wiedergegeben, mit den maßgeblichen Vorschriften. Hier gehört der Kern des Beitrags hin.
- **Einordnung.** Steht die Entscheidung auf der bisherigen Linie, schärft sie eine Abgrenzung, weicht sie ab? Abweichende Auffassungen benennst du als solche. Grundlage sind die Entscheidungen und Fundstellen, die das Gericht selbst anführt, und Quellen, die du nach dem Fachartikel-Skill abgesichert hast. Erläuterst du eine Norm, die das Gericht nicht heranzieht, steht sie erkennbar getrennt von der Entscheidung und wird nicht mit ihr verknüpft („spiegelt den Gedanken des Senats“, „der Senat überträgt diese Sicht“). So wurde beim Beitrag zu OVG 6 A 1/25 dem Senat § 649 BGB zugeschrieben, den er nicht zitiert.
- **Was daraus für die Baupraxis folgt.** Der eigentliche Zweck des Beitrags: Was bedeutet die Entscheidung für Dokumentation, Aufmaß, Nachtragsbegründung, Bauzeitnachweis, Mängelrüge, Beweissicherung oder die Arbeit des Sachverständigen? Dieser Abschnitt ist der längste.
- **Was die Entscheidung nicht sagt.** Die Grenze des Anwendungsbereichs. Wer sie überdehnt, zieht falsche Schlüsse.

Danach FAQ, Hinweis, Autorenkasten und Quellenverzeichnis wie im Fachartikel-Skill.

## Zitierweise

Im Text bei der ersten Nennung vollständig: Gericht, Spruchkörper, Datum, Aktenzeichen, dazu die Fußnote mit ECLI und Adresse der amtlichen Fundstelle. Danach verkürzt.

Beispiel: „Das Oberlandesgericht Brandenburg hat mit Urteil vom 4. Juni 2026 (Aktenzeichen 10 U 14/24) entschieden, dass …"

Vorschriften nennst du mit Kurzbezeichnung und Paragraf, bei der ersten Nennung je Abschnitt vollständig, belegt über `gesetze-im-internet.de`.

**Randnummern sind Pflicht.** Jeder Absatz, der Sachverhalt, Verfahrensgang, Begründung oder Gewichtung der besprochenen Entscheidung wiedergibt, nennt die Randnummer, auf der er beruht, im Text: „(Rn. 146)“, „(Rn. 124–135)“. Eine Sammelangabe wie „Rn. 1 bis 198“ in der Fußnote ersetzt das nicht. Schreibst du einen Satz, zu dem du keine Randnummer angeben kannst, gehört er nicht in den Artikel. Die Fußnote zur Entscheidung steht wie bisher bei der ersten Nennung.

**Zuschreibung.** Leitsätze stammen vom Gericht. Orientierungssätze stammen bei juris-Quellen von der Dokumentationsstelle, nicht vom Senat – der Kopf der Volltextdatei sagt es. Meinungen aus der Kommentarliteratur, die das Gericht referiert, sind Literatur, nicht Gericht; Ausführungen des Sachverständigen sind des Sachverständigen, bis das Gericht sie sich zu eigen macht.

## Genauigkeit gegenüber dem Volltext

Beim ersten Artikel dieses Agenten sind fünfzehn Abweichungen vom Urteil entstanden – nicht weil der Volltext fehlte, sondern weil über viele Züge aus der Erinnerung geschrieben wurde. Diese Regeln verhindern die wiederkehrenden Muster:

- **Nichts beschreiben, was nicht dasteht.** Art, Lage und Größe des Vorhabens, Rolle der Beteiligten: nur mit den Worten des Urteils.
- **Dauern berechnen.** Liegen zwei Daten vor, nennst du den Abstand, den sie ergeben – nie „Monate später“, wenn es sieben Wochen sind.
- **Die Gewichtung des Gerichts übernehmen.** Wo das Gericht etwas „untergeordnet“, „lediglich ergänzend“, „daneben“ oder „im Ergebnis“ nennt, stellst du es nicht als tragend dar.
- **Alle Gründe, in der Reihenfolge des Gerichts.** Nennt das Gericht mehrere Gründe oder stellt es zuerst auf eine prozessuale Frage ab (Verspätung, Unschlüssigkeit, fehlende Fälligkeit), gibst du das so wieder.
- **„Neu“ nur mit Deckung.** Zitiert das Gericht für denselben Satz eigene oder höchstrichterliche Rechtsprechung, ist er nicht neu – dann „bekräftigt“ oder „wendet an“.
- **Keine These gegen einen Befund.** Verwertet das Gericht etwas, das deiner Aussage widerspricht, gehört es in denselben Absatz.
- **Titel, Beschreibung und FAQ nicht zuspitzen.** Sie sagen nicht mehr als die Entscheidung. „Der Senat hielt 27 Monate für ausreichend“ steht so nicht im Urteil, wenn der Senat nur vorrechnet, dass 27 Monate zur Verfügung standen.
- **Keine Regel aus dem Einzelfall.** „… dann ist das vereinbarte Preisniveau festgeschrieben, und zwar auch dann, wenn der Markt sich bewegt“ ist eine allgemeine Regel, die das Urteil nicht aufstellt – auch nicht in einem Praxisabsatz.
- **Normen in der Fassung des Falls.** Vorschriften, die das Gericht anwendet, gibst du so wieder, wie das Gericht sie heranzieht, in der Fassung, die zum Zeitpunkt des Sachverhalts galt. gesetze-im-internet.de zeigt nur die heutige Fassung. Liegt der Sachverhalt vor einer Neufassung, zitierst du den heutigen Wortlaut nicht als damaligen. *Beispiel:* § 23 Abs. 3 WEG verlangt heute Zustimmung in Textform; für den Sachverhalt der Jahre 2019 und 2020 galt die Fassung vor dem 1. Dezember 2020 mit schriftlicher Zustimmung.
- **Randnummern nur an Aussagen über die Entscheidung.** Eine bautechnische Erläuterung bekommt keine Randnummer, auch wenn sie im selben Absatz steht. „… verändern die bauphysikalische Situation der Räume in der Regel spürbar (Rn. 80)“ – Randnummer 80 nennt die Arbeiten, sagt aber nichts über Bauphysik.

## Was du in diesem Format nicht tust

- **Keine Prognose.** Du sagst nicht, wie ein vergleichbarer Fall ausginge oder wie ein Revisionsverfahren enden wird. Im Abschnitt „Was die Entscheidung nicht sagt" hältst du fest, wie weit der Streit entschieden ist: ob die Revision zugelassen wurde, ob es sich um ein Endurteil handelt und ob nach dem Volltext noch etwas offen ist – jeweils mit Randnummer. Nichts darüber, ob ein Rechtsmittel eingelegt wurde, eingelegt werden kann, bei welchem Gericht oder in welcher Frist.
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

`format` ist `Rechtsprechung`. `kategorie` ist `Gutachten & Recht`, außer die Entscheidung betrifft eindeutig Baubetrieb, Kalkulation oder Nachtragsmanagement – dann `Baubetrieb`. `quelle` ist `rechtsprechung`. `notion_id` und `notion_url` bleiben leer: Das Thema stammt aus der Rechtsprechung, nicht aus dem Themenspeicher, und dieser Lauf schreibt nichts nach Notion.

Das Feld `aktenzeichen` ist wichtig: Der Kandidatenfinder liest es aus den vorhandenen Entwürfen und schlägt dieselbe Entscheidung kein zweites Mal vor.

## Umfang

Es gilt der Umfang aus dem Fachartikel-Skill: 3.000 bis 5.000 Wörter Haupttext, also 15 bis 25 Minuten Lesezeit, Zielwert 3.800 bis 4.500. Trägt die Entscheidung auch 3.000 Wörter nicht, **füllst du nicht auf**. Du erweiterst stattdessen die Einordnung: wie die Frage bisher behandelt wurde, welche bauwirtschaftliche oder bautechnische Bedeutung sie hat, was sie für Dokumentation und Beweisführung ändert – belegt wie alles andere, nie aus dem Gedächtnis. Trägt sie auch das nicht, war es die falsche Entscheidung – geh zurück zu Schritt 4 und nimm eine andere.

## Dateiname und Branch

Datei: `entwuerfe/JJJJ-MM-TT-<kurzform>.md`, wobei das Datum das des Laufs ist und die Kurzform das Thema beschreibt, nicht das Aktenzeichen. Gut: `bauzeitnachweis-gestoerter-bauablauf`. Schlecht: `olg-brandenburg-10-u-14-24`.

Branch: `entwurf/<kurzform>`. Titel des Pull Requests: `Entwurf: <Thema>`.

## Zusätzlich in den Pull Request

Es gilt die Vorlage des Fachartikel-Skills mit ihrer Reihenfolge: Leselink und Dreizeiler oben, der Prüfbericht zugeklappt darunter. Der Block „Besprochene Entscheidung“ gehört **oberhalb** des zugeklappten Bereichs, unmittelbar unter die Kennzahlenzeilen – er sagt, worum es überhaupt geht. Die beiden anderen Blöcke stehen **innerhalb** des Prüfberichts, hinter den Hinweisen zum Lauf.

Ebenso gilt der Pflichtschritt `python tools/artikel_generator.py` vor dem Commit; die gebaute Seite geht mit in denselben Pull Request.

```
### Besprochene Entscheidung

- Gericht: <…>
- Datum: <…>
- Aktenzeichen: <…>
- ECLI: <… oder „nicht vergeben">
- Fundstelle: <Adresse>
- Entscheidungsart: <Endurteil / Berufungsurteil ohne zugelassene Revision / BGH-Entscheidung>
- Verfahrensweg: <erste Instanz / Berufung gegen … / Revision gegen …>
- Abschluss: <was die Entscheidung erledigt und was nach dem Volltext offen bleibt; Revision zugelassen ja oder nein, mit Randnummer; „Rechtskraft nicht geprüft“>

### Geprüfte und verworfene Kandidaten

<je eine Zeile: Gericht, Datum, Aktenzeichen – Grund der Verwerfung>

### Abdeckungslücke

<Hinweis zum Kammergericht, falls keine Berliner Entscheidung dabei ist>
```
