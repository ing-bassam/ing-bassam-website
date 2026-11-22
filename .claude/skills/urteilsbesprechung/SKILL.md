---
name: urteilsbesprechung
description: Wählt aus einer vorsortierten Liste amtlicher Gerichtsentscheidungen eine baurelevante aus, prüft sie am Volltext und schreibt daraus eine Urteilsbesprechung als Fachartikel für ing-bassam.de. Wird vom Workflow „Urteilsbesprechung" mit dem Pfad zur Kandidatenliste aufgerufen und läuft ohne Rückfragen.
allowed-tools: Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, Bash(git checkout:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr list:*), Bash(wc:*), Bash(python tools/artikel_generator.py:*), Bash(python tools/fussnoten_ordnen.py:*), Bash(python tools/bibliothek_suchen.py:*), Bash(python tools/wortgleich_pruefen.py:*), Bash(python tools/normstand_pruefen.py:*)
---

# Urteilsbesprechung

Du schreibst die Besprechung einer Gerichtsentscheidung für den Blog der Bassam Ingenieurbüro für Bauwesen GmbH. Leser sind Bauherren, Bauunternehmer, Hausverwaltungen und Kollegen – keine Juristen. Der Artikel erklärt, was die Entscheidung **für die Baupraxis** bedeutet: für Gutachten, Kalkulation, Nachträge, Bauablauf und Dokumentation.

## Zuerst lesen

**Lies `.claude/skills/fachartikel/SKILL.md` vollständig, bevor du irgendetwas anderes tust.** Alles dort gilt unverändert: die harten Regeln, der Aufbau, die Fließtext-Regel, die Zitierfähigkeit, die Fußnoten, die Prüfung vor dem Commit, die Abgabe, der Frontmatter-Kopf. Dieser Skill ändert nur die unten genannten Punkte und ergänzt sie. Bei Widerspruch gilt der jeweils strengere Satz.

Ist die Fachbibliothek geladen, liest du danach `.bibliothek/erfahrungen.md` – vor der Kandidatenauswahl. Für Besprechungen zählt besonders Abschnitt 2: die Klassen, in denen die Faktenprüfung frühere Besprechungen am häufigsten korrigieren musste, mit Beispielen. Schreibe so, dass sie gar nicht erst entstehen.

Das Format ist immer `Rechtsprechung`, damit Gruppe B gilt: wissenschaftlicher Aufbau, dichte Argumentation, Fachsprache ohne Vereinfachung.

## Was diesen Lauf unterscheidet

Nicht du suchst das Thema – die Entscheidung bringt es mit. Der Workflow hat dir unter dem im Prompt genannten Pfad eine Kandidatenliste hingelegt. Sie ist **vorsortiert, nicht geprüft**: Ein Treffer kann das Wort „Bauvertrag" enthalten und trotzdem eine Kostenbeschwerde sein.

Nach deinem Lauf prüfen zwei unabhängige Instanzen deinen Entwurf: die **Faktenprüfung** jede Aussage über die Entscheidung an ihrer Randnummer, die **Schlussprüfung** jede Fußnote am heruntergeladenen Wortlaut der Quelle. Was nicht trägt, wird gestrichen und fehlt dann im Text. Was du nicht belegen kannst, schreibst du deshalb gar nicht erst.

## Ablauf

Die Turn-Regel aus dem Fachartikel-Skill gilt: Beende vor der Abschlussnachricht nie einen Turn ohne Tool-Aufruf.

1. **Kandidatenliste lesen** (Read). Fehlt sie oder enthält sie keine Kandidaten, endest du mit `ERGEBNIS: KEINE KANDIDATEN`, ohne Branch und ohne Pull Request.

2. **Vorauswahl.** Nimm die ersten sechs bis acht Kandidaten in der Reihenfolge der Liste. Berlin und Brandenburg stehen bewusst oben; gib ihnen den Vorzug, solange die Entscheidung fachlich trägt.

   Trägt die Liste den Abschnitt „Grundsatzentscheidungen aus mehreren Jahren“, sind die Kandidaten ein bis fünfzehn Jahre alt, über die Jahrgänge gestreut und je Gruppe nach **Gewicht** geordnet. Gesucht ist dann nicht die jüngste Entscheidung, sondern eine, auf der spätere aufbauen. Nimm die zwei bis drei gewichtigsten Kandidaten **jeder** Gruppe, auch die des Bundes, und bevorzuge Entscheidungen mit Leitsatz des Gerichts; bei gleichem Gewicht gehen Berlin und Brandenburg vor. Das Gewicht ist ein grober Hinweis des Suchskripts, keine fachliche Wertung – ob die Entscheidung trägt, entscheidest du am Volltext. Das Alter allein macht eine Entscheidung nicht wichtig.

3. **Volltext prüfen** (Read). Die Volltexte liegen bereits als Textdatei vor; die Liste nennt bei jedem Kandidaten den Pfad. Öffne sie mit **Read**, nicht mit WebFetch. Der Umweg über das Netz ist hier nicht nur unnötig, sondern beim Bund unmöglich: Dort liefert die amtliche Quelle ein ZIP-Archiv, das WebFetch nicht lesen kann. Das Skript hat es bereits entpackt.

   Fehlt bei einem Kandidaten der Pfad und steht dort „Achtung: Volltext nicht abrufbar", überspringe ihn und vermerke das im Pull Request.

   Für jeden Kandidaten in der Reihenfolge der Liste beantwortest du diese Fragen.
   - *Betrifft sie das Themenfeld?* Bauvertrag, Werkvertrag am Bau, Architekten- oder Ingenieurvertrag, Baumangel, Abnahme, Werklohn, Nachtrag, gestörter Bauablauf, Bauzeit, Behinderung, Kalkulation, Planungsfehler, Beweissicherung, Sachverständigenbeweis am Bau. Reine Miet-, Kauf-, Insolvenz-, Vergabe-, Kosten- oder Verfahrensfragen ohne Baubezug scheiden aus, auch wenn ein Suchbegriff vorkommt.
   - *Trägt sie einen Beitrag?* Eine Entscheidung trägt, wenn sie eine Rechtsfrage klärt, eine Abgrenzung schärft, von der bisherigen Linie abweicht oder eine für die Praxis wiederkehrende Konstellation behandelt. Eine Nichtzulassungsbeschwerde ohne Begründung, ein Hinweisbeschluss ohne Aussage oder eine reine Einzelfallwürdigung trägt nicht. Dasselbe gilt, wenn der Fall allein an der Beweisaufnahme hing – ein Zeuge wurde nicht geglaubt, ein Gutachten hat den Mangel nicht bestätigt, eine Seite blieb den Beweis schuldig – und das Gericht dabei keine Rechtsfrage beantwortet: Daraus lässt sich für andere Fälle nichts ableiten.
   - *Reicht der Volltext?* Enthält die Entscheidung Tatbestand und Entscheidungsgründe, oder nur einen Tenor? Ohne Gründe kannst du sie nicht besprechen.
   - *Ist der Streit entschieden?* Besprochen wird nur, was die Instanz abschließt. Das ist der wichtigste Filter, denn ein Beitrag über einen Fall, der weiterläuft, veraltet mit der nächsten Entscheidung.

     **Geeignet:** ein Endurteil, das den Rechtsstreit in der Instanz vollständig erledigt; ein Berufungsurteil, in dem die Revision **nicht** zugelassen wurde; ein Beschluss, der die Berufung zurückweist (§ 522 Abs. 2 ZPO), nur wenn der Volltext die Gründe selbst enthält und nicht bloß auf einen Hinweisbeschluss verweist – und nie als Grundsatzentscheidung, denn mit diesem Beschluss verneint das Gericht selbst die grundsätzliche Bedeutung.

     **Bundesgerichtshof – lies den Tenor, bevor du weiterliest.** Eine Entscheidung des Bundesgerichtshofs schließt den Streit nicht automatisch ab. Es gibt drei Ausgänge, und der Beitrag hängt davon ab, welcher vorliegt:
     - *Revision zurückgewiesen* oder *der Senat entscheidet in der Sache selbst*: Der Streit ist entschieden. Geeignet.
     - *Aufgehoben und zurückverwiesen* („… wird aufgehoben. Die Sache wird zur neuen Verhandlung und Entscheidung an das Berufungsgericht zurückverwiesen“): Der Senat hat eine **Rechtsfrage** beantwortet, an die das Berufungsgericht gebunden ist; **wer den Prozess gewinnt, ist offen**. Geeignet nur, wenn die beantwortete Rechtsfrage den Beitrag trägt – in der Regel hat die Entscheidung dann einen Leitsatz. Der Beitrag berichtet die Rechtsfrage und ihre Antwort, sagt im ersten Absatz und im Abschnitt „Was die Entscheidung nicht sagt“ mit Randnummer, dass der Fall an das Berufungsgericht zurückging, und spricht keiner Seite den Sieg zu („der Bauherr bekam recht“ ist dann falsch). Wie das Berufungsgericht danach entschieden hat, steht nicht im Volltext und nicht im Beitrag.
     - *Beschluss über eine Nichtzulassungsbeschwerde*: ohne Begründung ungeeignet. Hebt der Senat nur auf, weil das Berufungsgericht in diesem einen Fall Vortrag oder Beweisangebote übergangen hat (Verletzung des rechtlichen Gehörs), ist das eine Einzelfallkorrektur ohne Rechtssatz – in der Regel ungeeignet.

     Dasselbe gilt eine Stufe tiefer: Verweist ein Oberlandesgericht die Sache an das Landgericht zurück, ist der Streit nicht entschieden.

     **Nicht geeignet:** Teilurteil, Grundurteil, Zwischenurteil und Vorbehaltsurteil, weil über Grund, Höhe oder vorbehaltene Einwände noch gestritten wird; Versäumnis- und Anerkenntnisurteil, weil das Gericht dabei den Streitstoff nicht rechtlich durchprüft und begründet; jedes Urteil, in dem die Revision **zugelassen** wurde, weil der Fall dann beim Bundesgerichtshof weitergehen kann; Hinweisbeschlüsse; Entscheidungen im einstweiligen Rechtsschutz; Beschlüsse über Prozesskostenhilfe, Streitwert oder Kosten.

     Die Kandidatenliste und der Kopf der Volltextdatei tragen dazu **mechanische Hinweise des Suchskripts** („Verfahrensstand“, „Verfahrensgang laut Quelle“). Sie zeigen dir, wo du nachlesen musst, und ersetzen das Lesen von Tenor und Schluss der Gründe nicht; fehlt ein Hinweis, heißt das nicht, dass nichts offen ist.

     Ob die Revision zugelassen wurde, steht am Ende der Entscheidungsgründe. Ob es sich um ein Teil- oder Grundurteil handelt, steht im Tenor oder in der Bezeichnung. Steht dort nichts davon, ist es ein Endurteil. Dass gegen ein Urteil ohne zugelassene Revision noch eine Nichtzulassungsbeschwerde laufen kann, steht der Besprechung nicht entgegen. **Im Text steht dazu nur, was der Volltext sagt** – dass die Revision nicht zugelassen wurde, mit Randnummer – **und was du nach der folgenden Frage an einer amtlichen Fundstelle belegt hast.** Ob eine Beschwerde eingelegt wurde oder noch möglich ist, bei welchem Gericht und in welcher Frist, schreibst du ohne solchen Beleg nicht – das weißt du nicht. Beim Beitrag zu OVG 6 A 1/25 war genau dieser Satz falsch.
   - *Ist sie selbst aufgehoben worden?* Diese Frage stellst du bei **jeder** Entscheidung, die nicht vom Bundesgerichtshof stammt – unabhängig vom Alter. Auch ohne zugelassene Revision kann ein Berufungsurteil über eine Nichtzulassungsbeschwerde beim Bundesgerichtshof gelandet und dort aufgehoben worden sein; ein Beitrag über ein aufgehobenes Urteil erklärt eine Entscheidung, die es nicht mehr gibt. Nennt der Kopf der Volltextdatei unter „Verfahrensgang laut Quelle“ eine Entscheidung mit dem Vermerk „nachgehend“, ist das eine spätere Entscheidung in derselben Sache – dann gilt diese Frage auch für eine Entscheidung des Bundesgerichtshofs, und du liest die spätere Entscheidung, bevor du auswählst. Suche mit WebSearch nach Gericht und Aktenzeichen zusammen mit „nachgehend“, „BGH“, „Nichtzulassungsbeschwerde“ und „aufgehoben“; Nachweisdienste wie dejure zeigen den Verfahrensgang und dürfen dafür gelesen werden. Findest du eine spätere Entscheidung **in derselben Sache**, liest du sie an der amtlichen Fundstelle: Hat sie die Entscheidung ganz oder im tragenden Teil aufgehoben, ist der Kandidat **nicht geeignet**. Hat sie das Rechtsmittel zurückgewiesen, darfst du das im Beitrag sagen – mit Gericht, Datum, Aktenzeichen und Fußnote auf die amtliche Fundstelle nach der dreistufigen Absicherung; sonst nicht. Findest du nichts, schreibst du im Beitrag nichts dazu (auch nicht „rechtskräftig“) und vermerkst im Pull Request unter „Abschluss“ die Suchanfragen und „keine spätere Entscheidung in derselben Sache gefunden; Rechtskraft nicht geprüft“.
   - *Gilt sie heute noch?* Diese Frage stellst du bei jeder Entscheidung, die am Tag des Laufs älter als ein Jahr ist. Eine ältere Entscheidung ist wertvoll, wenn spätere auf ihr aufbauen – und schädlich, wenn der Beitrag eine Rechtslage erklärt, die nicht mehr gilt. Geprüft wird zweierlei.

     **Hat sich das Gesetz geändert?** Stelle fest, welche Vorschriften das Gericht in welcher Fassung anwendet, und vergleiche sie mit dem heutigen Wortlaut auf gesetze-im-internet.de. Einschnitte, nach denen du gezielt suchst und die du **an der Quelle prüfst, nicht aus dieser Aufzählung übernimmst**: das Bauvertragsrecht im BGB für Verträge ab dem 1. Januar 2018 (§§ 650a ff. BGB, geänderte Paragrafennummern im Werkvertragsrecht), die Fassungen der HOAI (2009, 2013, 2021), die Ausgaben der VOB/B, die WEG-Reform zum 1. Dezember 2020, das Gebäudeenergiegesetz anstelle der Energieeinsparverordnung.

     **Hat die Rechtsprechung die Linie verlassen?** Suche mit WebSearch nach dem Aktenzeichen zusammen mit „aufgegeben“, „Aufgabe der Rechtsprechung“, „hält nicht fest“ und „überholt“ sowie nach späteren Entscheidungen des Bundesgerichtshofs zur selben Frage. Blogs und Portale darfst du dafür lesen; **belegt** wird nur an der amtlichen Fundstelle der späteren Entscheidung (Abschnitt „Quellen“) mit der dreistufigen Absicherung.

     Das Ergebnis ist eines von dreien:
     - **Gilt unverändert** – du hast die heutige Fassung der tragenden Vorschriften gelesen und keine abweichende spätere Entscheidung gefunden: geeignet.
     - **Gesetz geändert, Kern trägt weiter** – die Regel steht heute an anderer Stelle oder in anderem Wortlaut, die Aussage der Entscheidung bleibt für heutige Fälle brauchbar: geeignet, wenn du die Fassung des Falls und die heutige Fassung je mit Quelle belegen kannst.
     - **Überholt oder nicht zu klären** – eine spätere Entscheidung hat die Linie aufgegeben, das Gesetz regelt die Frage heute anders, oder du kannst es nach der Recherche nicht sicher sagen: **nicht geeignet**, nächster Kandidat. Ein offener Prüfpunkt zu dieser Frage ist keine Lösung.

     Im Beitrag steht das Ergebnis im Absatz „Stand heute“ (siehe Aufbau), im Pull Request unter „Aktualität“.

   Die Liste nennt je Kandidat die Zahl der gefundenen Begriffe aus dem Themenfeld. Das ist ein grober Hinweis, keine Aussage über die Eignung: Ein hoher Wert kann auch eine Kostenentscheidung in einer Bausache treffen, ein niedriger eine grundlegende Entscheidung. Du liest trotzdem selbst.

   Notiere je Kandidat in einem Satz, warum er taugt oder ausscheidet. Diese Notizen kommen später in den Pull Request.

4. **Eine auswählen.** Genau eine Entscheidung wird besprochen. Findest du unter den geprüften Kandidaten keine geeignete, prüfe weitere aus der Liste. Ist die Liste erschöpft, endest du mit `ERGEBNIS: KEINE GEEIGNETE ENTSCHEIDUNG` und nennst in der Abschlussnachricht, was du geprüft und warum du es verworfen hast. Du weichst nicht auf eine Entscheidung außerhalb der Liste aus.

5. **Fundstelle sichern.** Gericht, Spruchkörper, Entscheidungsdatum, Aktenzeichen und – falls vergeben – ECLI übernimmst du **wörtlich aus dem Kopf der Volltextdatei**. Dieser Kopf stammt unverändert aus der amtlichen Quelle; das Skript hat nichts umformuliert. Niemals aus dem Gedächtnis, niemals aus der Überschrift der Kandidatenliste.

   Liegt die Entscheidung bei einer Landesdatenbank und ist die Fundstelle eine gewöhnliche Internetadresse, die sich ohne JavaScript lesen lässt (Brandenburg, Nordrhein-Westfalen), rufst du sie zusätzlich einmal mit WebFetch ab und vergleichst Datum und Aktenzeichen. Bei den juris-Portalen – erkennbar an einer Fundstelle der Form `…/perma?d=…` – entfällt der Abgleich, weil die Seite ihren Inhalt erst im Browser aufbaut; die Angaben stammen dort unmittelbar aus der Schnittstelle des Portals. Stimmt etwas nicht überein, gilt der Volltext, und du vermerkst die Abweichung im Pull Request. Beim Bund entfällt dieser Abgleich, weil dort nur das ZIP-Archiv bereitsteht – die Angaben stammen dann direkt aus der amtlichen XML-Datei darin.

   Das ersetzt für die **Fundstelle selbst** – Gericht, Datum, Aktenzeichen, ECLI – die dreistufige Absicherung des Fachartikel-Skills. **Es ersetzt nicht die Prüfung dessen, was du über die Entscheidung schreibst.** Jede solche Aussage muss an einer bestimmten Randnummer des Volltexts stehen und trägt diese Randnummer im Text (siehe Zitierweise); nach deinem Lauf vergleicht eine unabhängige Faktenprüfung jede Aussage mit genau dieser Stelle. Für **jede weitere** genannte Entscheidung, Norm oder Vorschrift gilt die dreistufige Absicherung unverändert.

   Trägt der Kopf der Volltextdatei den Vermerk, dass die Marke „Randnummer <n>“ fehlt, zitierst du so, wie der Kopf es beschreibt, und vermerkst das im Pull Request unter „Hinweise zum Lauf“ – die Prüfagenten suchen dann über kennzeichnende Wörter.

6. **Belegauszug anlegen** (ein bis zwei Turns), bevor du schreibst. Lege mit Write im Verzeichnis der Kandidatenliste die Datei `belegauszug.md` an. Abweichend von Regel 3 des Fachartikel-Skills ist sie neben `pr-body.md` die zweite zulässige Datei außerhalb des Repositorys. Sie enthält:
   - den **Verfahrensweg** mit Randnummer: Hat das Gericht in erster Instanz entschieden, über eine Berufung oder über eine Revision? Gibt es eine Vorinstanz, und was hat sie entschieden?
   - den Tenor in eigenen Worten, den **Ausgang** (Klage zugesprochen oder abgewiesen, ganz oder teilweise; Rechtsmittel zurückgewiesen; aufgehoben und zurückverwiesen) und die Randnummer, an der steht, ob die Revision zugelassen wurde;
   - **wer was von wem woraus verlangt:** das Begehren der klagenden Seite und die Anspruchsgrundlage, auf die das Gericht es prüft (etwa Werklohn, Vorschuss auf Mängelbeseitigung, Schadensersatz wegen eines Planungsfehlers), mit Randnummer;
   - **die Rechtsfrage in einem Satz** – die Frage, die das Gericht beantworten musste, um den Fall zu entscheiden. Kannst du sie nicht in einem Satz fassen, hast du die Entscheidung noch nicht verstanden; lies die Gründe erneut, bevor du weitermachst;
   - **den Vertrag, so weit der Volltext ihn mitteilt,** je mit Randnummer, sonst „nicht mitgeteilt“: Art (Bauvertrag, Architekten- oder Ingenieurvertrag, Bauträgervertrag, Kauf), Zeitpunkt des Vertragsschlusses, ob die VOB/B vereinbart war und in welcher Ausgabe, ob eine Seite Verbraucher war. Diese Angaben entscheiden, auf welche heutigen Fälle sich die Entscheidung übertragen lässt und welche Gesetzesfassung galt; was „nicht mitgeteilt“ ist, behauptet der Beitrag nicht;
   - **worauf das Ergebnis beruht:** auf der Antwort auf eine Rechtsfrage, auf der Würdigung der Beweise oder darauf, dass eine Seite etwas nicht dargelegt oder nicht bewiesen hat – mit Randnummer;
   - **was das Gericht ausdrücklich offenlässt** („kann dahinstehen“, „bedarf keiner Entscheidung“, „kann offenbleiben“) und **was es nur als Hinweis sagt**, ohne dass das Ergebnis davon abhängt („für das weitere Verfahren weist der Senat darauf hin“, „im Übrigen“, „selbst wenn“), je mit Randnummer;
   - für jede Aussage, die du über die Entscheidung treffen willst, die Randnummer mit einem **wörtlichen Belegstück** von höchstens 25 Wörtern aus dem Text des Gerichts (amtliches Werk, § 5 UrhG – nie aus juris-Orientierungssätzen, Kommentaren oder Büchern): den Sachverhalt, jeden tragenden Grund in der Reihenfolge des Gerichts, jede Gewichtung („regelmäßig“, „untergeordnet“, „im Ergebnis“), jede Entscheidung, die das Gericht selbst anführt, und jede Norm, die es heranzieht, in der Fassung, die es nennt.

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
- **Einordnung.** Steht die Entscheidung auf der bisherigen Linie, schärft sie eine Abgrenzung, weicht sie ab? Abweichende Auffassungen benennst du als solche. Grundlage sind die Entscheidungen und Fundstellen, die das Gericht selbst anführt, und Quellen, die du nach dem Fachartikel-Skill abgesichert hast. Für die bautechnische und baubetriebliche Einordnung ist die Fachbibliothek die erste Adresse (Abschnitt „Fachbibliothek“ im Fachartikel-Skill) – etwa Werke zum Sachverständigen-, Bau- und Vergaberecht, zur VOB/B und zur VOB/C. Achte auf ihren Stand: Ein Buch von 2018 kennt keine Rechtsprechung von 2026. Erläuterst du eine Norm, die das Gericht nicht heranzieht, steht sie erkennbar getrennt von der Entscheidung und wird nicht mit ihr verknüpft („spiegelt den Gedanken des Senats“, „der Senat überträgt diese Sicht“). So wurde beim Beitrag zu OVG 6 A 1/25 dem Senat § 649 BGB zugeschrieben, den er nicht zitiert.
- **Was daraus für die Baupraxis folgt.** Der eigentliche Zweck des Beitrags: Was bedeutet die Entscheidung für Dokumentation, Aufmaß, Nachtragsbegründung, Bauzeitnachweis, Mängelrüge, Beweissicherung oder die Arbeit des Sachverständigen? Dieser Abschnitt ist der längste.
- **Was die Entscheidung nicht sagt.** Die Grenze des Anwendungsbereichs. Wer sie überdehnt, zieht falsche Schlüsse. Hierher gehören aus dem Belegauszug: was das Gericht ausdrücklich offengelassen hat (mit Randnummer), auf welchen Vertrag und welche Umstände sich die Entscheidung bezieht, und – wenn der Fall zurückverwiesen wurde – dass der Streit selbst nicht entschieden ist. Zur **Reichweite** nennst du das Gericht mit seinem Rang und machst aus einer einzelnen Entscheidung keine Linie: „die Gerichte“, „die Rechtsprechung“ oder „es gilt“ für das Urteil eines Land- oder Oberlandesgerichts ist eine Überdehnung; ein anderes Gericht kann dieselbe Frage anders beurteilen. Dass eine Frage höchstrichterlich geklärt ist, schreibst du nur bei einer Entscheidung des Bundesgerichtshofs zu genau dieser Frage oder mit Fußnote auf eine solche.

  **Stand heute** – Pflicht, wenn die Entscheidung älter als ein Jahr ist: ein Absatz in diesem Abschnitt, der sagt, wann entschieden wurde, welche Fassung der Vorschriften das Gericht angewandt hat (mit Randnummer) und was davon heute gilt. Jede Aussage über die heutige Rechtslage trägt eine eigene Fußnote auf die amtliche Quelle – den heutigen Gesetzeswortlaut oder die spätere Entscheidung. Der Absatz schreibt dem Gericht nichts zu, was es nicht gesagt hat. *Beispiel:* „Der Senat wendet § 648a BGB in der damaligen Fassung an (Rn. 12). Die Bauhandwerkersicherung ist seit dem 1. Januar 2018 in § 650f BGB geregelt[^n].“ Ein Satz wie „gilt bis heute“ oder „ständige Rechtsprechung“ ohne Fußnote ist verboten: Dass **keine** abweichende Entscheidung ergangen ist, lässt sich nicht belegen. Findest du für die heutige Rechtslage keinen Beleg, nennst du nur das Entscheidungsdatum und die angewandte Fassung.

Danach FAQ, Hinweis, Autorenkasten und Quellenverzeichnis wie im Fachartikel-Skill.

## Zitierweise

Im Text bei der ersten Nennung vollständig: Gericht, Spruchkörper, Datum, Aktenzeichen, dazu die Fußnote mit ECLI und Adresse der amtlichen Fundstelle. Danach verkürzt.

Beispiel: „Das Oberlandesgericht Brandenburg hat mit Urteil vom 4. Juni 2026 (Aktenzeichen 10 U 14/24) entschieden, dass …"

Vorschriften nennst du mit Kurzbezeichnung und Paragraf, bei der ersten Nennung je Abschnitt vollständig, belegt über `gesetze-im-internet.de`.

**Randnummern sind Pflicht.** Jeder Absatz, der Sachverhalt, Verfahrensgang, Begründung oder Gewichtung der besprochenen Entscheidung wiedergibt, nennt die Randnummer, auf der er beruht, im Text: „(Rn. 146)“, „(Rn. 124–135)“. Eine Sammelangabe wie „Rn. 1 bis 198“ in der Fußnote ersetzt das nicht. Schreibst du einen Satz, zu dem du keine Randnummer angeben kannst, gehört er nicht in den Artikel. Die Fußnote zur Entscheidung steht wie bisher bei der ersten Nennung.

**Zuschreibung.** Leitsätze stammen vom Gericht. Orientierungssätze und Titelzeilen stammen von der Dokumentationsstelle, nicht vom Senat – der Kopf der Volltextdatei und die Abschnittsüberschriften sagen es. Meinungen aus der Kommentarliteratur, die das Gericht referiert, sind Literatur, nicht Gericht; Ausführungen des Sachverständigen sind des Sachverständigen, bis das Gericht sie sich zu eigen macht.

**Der Leitsatz ist eine Kurzfassung, nicht die Entscheidung.** Er gehört nicht zu den Gründen und ist oft allgemeiner formuliert, als der Fall es trägt. Was die Entscheidung sagt und wie weit sie reicht, ergibt sich aus den Gründen im Zusammenhang mit dem Sachverhalt. Jede Aussage, die du dem Leitsatz entnimmst, belegst du deshalb an der Randnummer der Gründe, die sie trägt; findest du dort eine Einschränkung, die der Leitsatz nicht nennt, steht sie im Beitrag.

**Wer spricht – in Entscheidungen über ein Rechtsmittel.** Ein Berufungs- oder Revisionsurteil gibt zuerst wieder, was die Vorinstanz entschieden und wie sie es begründet hat („Das Berufungsgericht hat ausgeführt …“, „Das Landgericht hat gemeint …“), und sagt erst danach, ob das hält („Das hält der rechtlichen Nachprüfung nicht stand“). Der erste Teil ist die Ansicht der Vorinstanz – oft genau die, die das Gericht anschließend verwirft. Du schreibst sie nie dem entscheidenden Gericht zu.

**Unterstellt ist nicht festgestellt.** Der Bundesgerichtshof erhebt keine Beweise; er prüft Rechtsfehler auf der Grundlage dessen, was die Vorinstanz festgestellt hat. Wo er schreibt „ist revisionsrechtlich zu unterstellen“, „nach dem Vortrag der Klägerin, von dem in der Revisionsinstanz auszugehen ist“ oder „zugunsten der Beklagten ist anzunehmen“, steht die Tatsache **nicht** fest – sie wird für die Rechtsprüfung nur angenommen. Im Beitrag steht sie als unterstellt oder als Vortrag, nie als Tatsache. „Ist revisionsrechtlich nicht zu beanstanden“ heißt, dass die Würdigung der Vorinstanz keinen Rechtsfehler zeigt – nicht, dass der Senat die Tatsachen selbst so festgestellt hat.

**Offen ist offen.** Was das Gericht dahinstehen lässt, hat es nicht entschieden – weder in die eine noch in die andere Richtung. **Hinweise sind keine Entscheidung:** Was das Gericht nur für das weitere Verfahren oder „im Übrigen“ anmerkt, gibst du als Hinweis wieder und nennst es so; es trägt weder Titel noch ersten Absatz noch eine FAQ-Antwort allein.

## Urheberrecht und Stand der Technik

Es gilt Regel 13 des Fachartikel-Skills (Regel des Inhabers). Der Text der Entscheidung ist ein amtliches Werk: Kurze wörtliche Zitate aus Tenor, Leitsätzen des Gerichts, Tatbestand und Gründen sind erlaubt, mit Randnummer. **Nicht amtlich** und deshalb nie wörtlich – weder im Beitrag noch im Pull Request – sind Orientierungssätze der Dokumentationsstelle (juris), redaktionelle Leitsätze, Kommentare, Fachbücher und Aufsätze, auch wenn das Gericht sie zitiert oder ein Portal sie mitliefert; ihren Inhalt gibst du in eigenen Worten mit Fundstelle wieder. Für Einordnung und Baupraxis gilt der Abschnitt „Eigene Fassung statt Umformulierung“ des Fachartikel-Skills: keine Gedankenfolge, Beispielreihe oder Definition einer Buchstelle nachbilden, Rechtsprechung aus der Literatur nur mit Gericht, Datum und Aktenzeichen.

Nennt die Besprechung eine Norm oder ein Regelwerk – etwa in der Einordnung oder im Abschnitt zur Baupraxis –, gilt der Abschnitt „Stand der Technik“ des Fachartikel-Skills sinngemäß: zuerst `python tools/bibliothek_suchen.py --norm "<Norm>"`, dann Stufe 2. Wendet das Gericht eine ältere Ausgabe an, gibst du sie als die des Falls wieder (mit Randnummer) und sagst, sofern belegt, welche Ausgabe heute gilt; Buchaussagen zu einer Norm übernimmst du nur, wenn die neueste Ausgabe sie trägt. Vor jedem `git commit` führst du `python tools/normstand_pruefen.py <entwurf> --ausgaben .bibliothek/normen/ausgaben.yml` und `python tools/wortgleich_pruefen.py <entwurf> --bibliothek .bibliothek` aus und fasst jeden Treffer in eigene Worte bzw. korrigierst die Ausgabe, bis beide 0 melden. Werk und Seite eines Treffers zeigt nur `--intern` – nur zur eigenen Überarbeitung, nie in `pr-body.md`, Kommentaren oder der Abschlussnachricht. Ein Treffer der Wortgleich-Prüfung wird nie committet: Bleibt er, streichst du die Stelle; geht das nicht, endet der Lauf mit `ERGEBNIS: ABBRUCH` (wie im Fachartikel-Skill, „Stand der Technik“ Punkt 3). Kurze Zitate aus der Entscheidung bleiben erlaubt; meldet die Prüfung eines davon (weil ein Buch oder eine geladene Quelle dieselbe Stelle abdruckt), fasst du es knapp in eigene Worte mit Randnummer. Eine Ausgabe, die das Gericht für den Fall nennt, ist inhaltlich kein Fehler und bleibt stehen; du kennzeichnest sie im selben Satz als damalige Fassung („die damals geltende Ausgabe“, „zum Zeitpunkt der Abnahme“) – dann meldet die Normstand-Prüfung nur einen Hinweis. Meldet sie trotzdem einen `FEHLER`, nennst du sie unter „Worauf ich mir am unsichersten bin“ mit Randnummer als Ausgabe des Falls; der Workflow lässt den Pull Request dann als Entwurf stehen, und der Auftraggeber entscheidet. Im Pull Request steht die Tabelle „Stand der Technik – Normausgaben“ aus der Vorlage des Fachartikel-Skills.

## Genauigkeit gegenüber dem Volltext

Beim ersten Artikel dieses Agenten sind fünfzehn Abweichungen vom Urteil entstanden – nicht weil der Volltext fehlte, sondern weil über viele Züge aus der Erinnerung geschrieben wurde. Diese Regeln verhindern die wiederkehrenden Muster:

- **Nichts beschreiben, was nicht dasteht.** Art, Lage und Größe des Vorhabens, Rolle der Beteiligten: nur mit den Worten des Urteils.
- **Dauern berechnen.** Liegen zwei Daten vor, nennst du den Abstand, den sie ergeben – nie „Monate später“, wenn es sieben Wochen sind.
- **Die Gewichtung des Gerichts übernehmen.** Wo das Gericht etwas „untergeordnet“, „lediglich ergänzend“, „daneben“ oder „im Ergebnis“ nennt, stellst du es nicht als tragend dar.
- **Alle Gründe, in der Reihenfolge des Gerichts.** Nennt das Gericht mehrere Gründe oder stellt es zuerst auf eine prozessuale Frage ab (Verspätung, Unschlüssigkeit, fehlende Fälligkeit), gibst du das so wieder.
- **„Neu“ nur mit Deckung.** Zitiert das Gericht für denselben Satz eigene oder höchstrichterliche Rechtsprechung, ist er nicht neu – dann „bekräftigt“ oder „wendet an“.
- **Keine These gegen einen Befund.** Verwertet das Gericht etwas, das deiner Aussage widerspricht, gehört es in denselben Absatz.
- **Titel, Beschreibung und FAQ nicht zuspitzen.** Sie sagen nicht mehr als die Entscheidung. „Der Senat hielt 27 Monate für ausreichend“ steht so nicht im Urteil, wenn der Senat nur vorrechnet, dass 27 Monate zur Verfügung standen.
- **Die Rechtsfrage zuerst.** Titel, erster Absatz und der Abschnitt zu den tragenden Gründen beantworten die Rechtsfrage aus dem Belegauszug – nicht eine verwandte, weitere oder interessantere Frage.
- **Keine Regel aus dem Einzelfall.** „… dann ist das vereinbarte Preisniveau festgeschrieben, und zwar auch dann, wenn der Markt sich bewegt“ ist eine allgemeine Regel, die das Urteil nicht aufstellt – auch nicht in einem Praxisabsatz.
- **Normen in der Fassung des Falls.** Vorschriften, die das Gericht anwendet, gibst du so wieder, wie das Gericht sie heranzieht, in der Fassung, die zum Zeitpunkt des Sachverhalts galt. gesetze-im-internet.de zeigt nur die heutige Fassung. Liegt der Sachverhalt vor einer Neufassung, zitierst du den heutigen Wortlaut nicht als damaligen. *Beispiel:* § 23 Abs. 3 WEG verlangt heute Zustimmung in Textform; für den Sachverhalt der Jahre 2019 und 2020 galt die Fassung vor dem 1. Dezember 2020 mit schriftlicher Zustimmung.
- **Randnummern nur an Aussagen über die Entscheidung.** Eine bautechnische Erläuterung bekommt keine Randnummer, auch wenn sie im selben Absatz steht. „… verändern die bauphysikalische Situation der Räume in der Regel spürbar (Rn. 80)“ – Randnummer 80 nennt die Arbeiten, sagt aber nichts über Bauphysik.

## Was du in diesem Format nicht tust

- **Keine Prognose.** Du sagst nicht, wie ein vergleichbarer Fall ausginge, wie ein Revisionsverfahren enden wird oder wie das Berufungsgericht nach einer Zurückverweisung entscheiden wird. Im Abschnitt „Was die Entscheidung nicht sagt" hältst du fest, wie weit der Streit entschieden ist: ob die Revision zugelassen wurde, ob es sich um ein Endurteil handelt und ob nach dem Volltext noch etwas offen ist – jeweils mit Randnummer. Nichts darüber, ob ein Rechtsmittel eingelegt wurde, eingelegt werden kann, bei welchem Gericht oder in welcher Frist.
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

Datei: `entwuerfe/entwurf/JJJJ-MM-TT-<kurzform>.md`, wobei das Datum das des Laufs ist und die Kurzform das Thema beschreibt, nicht das Aktenzeichen. Gut: `bauzeitnachweis-gestoerter-bauablauf`. Schlecht: `olg-brandenburg-10-u-14-24`.

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
- Entscheidungsart: <Endurteil / Berufungsurteil ohne zugelassene Revision / Beschluss nach § 522 Abs. 2 ZPO / Urteil oder Beschluss des BGH>
- Verfahrensweg: <erste Instanz / Berufung gegen … / Revision gegen …>
- Ausgang: <Klage zugesprochen / abgewiesen / teilweise; Rechtsmittel zurückgewiesen; in der Sache selbst entschieden; aufgehoben und zurückverwiesen – mit Randnummer oder „Tenor“>
- Rechtsfrage: <ein Satz aus dem Belegauszug>
- Vertrag: <Art, Vertragsschluss, VOB/B, Verbraucher – je mit Randnummer oder „nicht mitgeteilt“>
- Abschluss: <was die Entscheidung erledigt und was nach dem Volltext offen bleibt; Revision zugelassen ja oder nein, mit Randnummer; bei Entscheidungen unterhalb des BGH: mit welchen Suchanfragen du nach einer späteren Entscheidung in derselben Sache gesucht hast und was du gefunden hast; „Rechtskraft nicht geprüft“>
- Aktualität: <nur bei Entscheidungen, die älter als ein Jahr sind: „gilt unverändert“ oder „Gesetz geändert, Kern trägt weiter“; welche Vorschriften du mit der heutigen Fassung verglichen hast; mit welchen Suchanfragen du nach späteren abweichenden Entscheidungen gesucht hast und was du gefunden hast>

### Geprüfte und verworfene Kandidaten

<je eine Zeile: Gericht, Datum, Aktenzeichen – Grund der Verwerfung>

### Abdeckungslücke

<Hinweis zum Kammergericht, falls keine Berliner Entscheidung dabei ist>
```
