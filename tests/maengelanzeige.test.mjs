// Tests für den Rechenkern des Mängelanzeige-Generators.
import test from "node:test";
import assert from "node:assert/strict";
import { ANLAGEN, PRUEFLISTE, briefErzeugen, briefText, pruefen } from "../werkzeuge/maengelanzeige/brief.js";

function eingabe(aenderungen = {}) {
  return {
    einzelperson: false,
    absender: { name: "Eigentümergemeinschaft Musterstraße 1", strasse: "Musterstraße 1", plzOrt: "12487 Berlin", telefon: "030 1234567", email: "verwaltung@example.org" },
    empfaenger: { firma: "Bau GmbH", strasse: "Werkstraße 5", plzOrt: "10115 Berlin" },
    ort: "Berlin",
    datum: "2026-10-05",
    bauvorhaben: "Musterstraße 1, 12487 Berlin",
    leistung: "die Fliesenarbeiten im Erdgeschoss",
    vertragsdatum: "2025-03-01",
    vertragsart: "bgb",
    abnahme: "ja",
    abnahmeDatum: "2026-02-15",
    maengel: [{ ort: "Bad im Erdgeschoss, Wand zur Küche", erscheinung: "mehrere Bodenfliesen klingen hohl und eine Fuge ist auf 60 cm Länge gerissen", datum: "2026-09-28" }],
    frist: "2026-10-30",
    rueckmeldung: "2026-10-14",
    zeiten: "montags bis freitags 8 bis 16 Uhr",
    zugang: "Bad und Flur",
    anlagen: ["fotos"],
    ...aenderungen,
  };
}

test("Vollständige Eingabe ergibt einen Brief mit allen Pflichtteilen", () => {
  const e = briefErzeugen(eingabe());
  assert.equal(e.ok, true, e.fehler.join(" "));
  const t = briefText(e.brief);
  assert.match(t, /^Eigentümergemeinschaft Musterstraße 1\n/);
  assert.match(t, /Bau GmbH\nWerkstraße 5\n10115 Berlin/);
  assert.match(t, /Berlin, den 05\.10\.2026/);
  assert.match(t, /Mängelanzeige mit Fristsetzung – Bauvorhaben Musterstraße 1, 12487 Berlin, die Fliesenarbeiten im Erdgeschoss/);
  assert.match(t, /Bauvertrag vom 01\.03\.2025 über die Fliesenarbeiten/);
  assert.match(t, /Werkvertragsrecht des Bürgerlichen Gesetzbuchs/);
  assert.match(t, /Die Abnahme erfolgte am 15\.02\.2026\./);
  assert.match(t, /Am 28\.09\.2026 haben wir Folgendes festgestellt: Bad im Erdgeschoss, Wand zur Küche – mehrere Bodenfliesen/);
  assert.match(t, /Die Ursache der beschriebenen Erscheinung benennen wir nicht/);
  assert.match(t, /Lichtbilder mit Datum und Maßangabe ist diesem Schreiben als Anlage beigefügt/);
  assert.match(t, /bis zum 30\.10\.2026 vollständig zu beseitigen/);
  assert.match(t, /montags bis freitags 8 bis 16 Uhr\. Bitte stimmen Sie den Termin vorher mit Eigentümergemeinschaft Musterstraße 1, 030 1234567, verwaltung@example.org ab\. Den Zugang zu Bad und Flur stellen wir sicher\./);
  assert.match(t, /Weitere Rechte behalten wir uns ausdrücklich vor/);
  assert.match(t, /bis zum 14\.10\.2026 mit, wann Sie die Arbeiten ausführen/);
  assert.match(t, /Mit freundlichen Grüßen\n\n\nEigentümergemeinschaft Musterstraße 1\n\nAnlagen:\n– Lichtbilder mit Datum und Maßangabe$/);
  assert.doesNotMatch(t, /weiteren Schäden/);
});

test("Ich-Form für Einzelpersonen", () => {
  const t = briefText(briefErzeugen(eingabe({ einzelperson: true, absender: { name: "Max Muster", strasse: "Weg 2", plzOrt: "12487 Berlin" } })).brief);
  assert.match(t, /zwischen Ihnen als Auftragnehmer und mir als Auftraggeber/);
  assert.match(t, /Hiermit zeige ich einen Mangel an und fordere Sie zu dessen Beseitigung auf/);
  assert.match(t, /habe ich Folgendes festgestellt/);
  assert.match(t, /benenne ich nicht\. Ich beschreibe/);
  assert.match(t, /Ich fordere Sie auf/);
  assert.match(t, /behalte ich mir ausdrücklich vor\. Nach Ablauf der Frist prüfe ich, welche Mängelrechte mir zustehen/);
  assert.match(t, /Bitte bestätigen Sie mir den Erhalt/);
  assert.doesNotMatch(t, /\bwir\b/);
});

test("Mehrere Mängel werden nummeriert aufgelistet", () => {
  const e = briefErzeugen(eingabe({ maengel: [
    { ort: "Bad EG", erscheinung: "hohl klingende Fliesen", datum: "2026-09-28" },
    { ort: "Flur EG", erscheinung: "Riss in der Fuge", datum: "2026-09-29" },
  ] }));
  const t = briefText(e.brief);
  assert.match(t, /Hiermit zeigen wir Mängel an und fordern Sie zu deren Beseitigung auf/);
  assert.match(t, /Wir haben folgende Mängel festgestellt:\n\n1\. Bad EG – hohl klingende Fliesen \(festgestellt am 28\.09\.2026\)\n2\. Flur EG – Riss in der Fuge \(festgestellt am 29\.09\.2026\)/);
  assert.match(t, /die vorstehend beschriebenen Mängel bis zum/);
  assert.match(t, /Auf welche Weise Sie die Mängel beseitigen/);
});

test("VOB/B, Abnahme mit Vorbehalt, Gefahrhinweis", () => {
  const e = briefErzeugen(eingabe({ vertragsart: "vob", abnahme: "vorbehalt", vorbehaltNr: "7", gefahr: true, sicherung: "die Absperrung des Bereichs" }));
  const t = briefText(e.brief);
  assert.match(t, /In diesen Vertrag ist die VOB\/B einbezogen/);
  assert.match(t, /der nachstehende Mangel ist im Abnahmeprotokoll unter Nummer 7 vorbehalten/);
  assert.match(t, /Wir haben die Absperrung des Bereichs veranlasst und bitten um Rückmeldung bis zum 14\.10\.2026/);
});

test("Nicht abgenommen, ohne Zeiten und Anlagen", () => {
  const e = briefErzeugen(eingabe({ abnahme: "nein", abnahmeDatum: "", zeiten: "", anlagen: [], rueckmeldung: "" }));
  const t = briefText(e.brief);
  assert.match(t, /Die Leistung ist bisher nicht abgenommen\./);
  assert.doesNotMatch(t, /Für die Ausführung stehen/);
  assert.doesNotMatch(t, /Anlage/);
  assert.match(t, /Erhalt dieses Schreibens und teilen uns mit, wann/);
});

test("Weitere Anlagen und Aufzählung", () => {
  const e = briefErzeugen(eingabe({ anlagen: ["fotos", "liste", "vertrag"], anlagenWeitere: "Schriftverkehr vom 12.09.2026; Angebot vom 01.02.2025" }));
  assert.equal(e.brief.anlagen.length, 5);
  assert.match(briefText(e.brief), /Lichtbilder mit Datum und Maßangabe, Nummerierte Mängelliste mit Ort und Erscheinungsbild, Kopie des Bauvertrags oder des Abnahmeprotokolls, Schriftverkehr vom 12\.09\.2026 und Angebot vom 01\.02\.2025 sind diesem Schreiben als Anlage beigefügt/);
});

test("Fehlende Pflichtangaben verhindern den Brief", () => {
  const e = briefErzeugen(eingabe({ empfaenger: { firma: "" }, maengel: [{ ort: "", erscheinung: "", datum: "" }] }));
  assert.equal(e.ok, false);
  assert.ok(e.fehler.some((f) => /Unternehmen/.test(f)));
  assert.ok(e.fehler.some((f) => /mindestens einen Mangel/.test(f)));
  const f = briefErzeugen(eingabe({ frist: "2026-10-01" }));
  assert.equal(f.ok, false);
  assert.ok(f.fehler.some((x) => /nach dem Datum des Schreibens/.test(x)));
  const v = briefErzeugen(eingabe({ abnahme: "vorbehalt", vorbehaltNr: "" }));
  assert.ok(v.fehler.some((x) => /Nummer des Vorbehalts/.test(x)));
});

test("Hinweise: kurze Frist, Ursachenbehauptung, VOB/B vor Abnahme, Zugang", () => {
  const p = pruefen(eingabe({ frist: "2026-10-10", vertragsart: "vob", abnahme: "nein",
    maengel: [{ ort: "Keller", erscheinung: "Feuchtefleck, verursacht durch fehlerhafte Abdichtung", datum: "2026-09-28" }] }));
  assert.equal(p.fehler.length, 0);
  assert.ok(p.hinweise.some((h) => /nur 5 Tage/.test(h)));
  assert.ok(p.hinweise.some((h) => /Ursachenbehauptung/.test(h)));
  assert.ok(p.hinweise.some((h) => /§ 4 Abs\. 7 VOB\/B/.test(h)));
  assert.ok(p.hinweise.some((h) => /Zugang zählt/.test(h)));
});

test("Prüfliste und Anlagenarten sind vollständig", () => {
  assert.equal(PRUEFLISTE.length, 20);
  assert.deepEqual(Object.keys(ANLAGEN), ["fotos", "liste", "vertrag", "gutachten"]);
});
