// Tests für den Rechenkern der Kaufbegutachtung (werkzeuge/kaufbegutachtung/kaufbegutachtung.js).
// Prüfwerte: Preise aus daten.js, brutto = netto × 1,19 auf Cent gerundet.
import test from "node:test";
import assert from "node:assert/strict";
import {
  DATEN, MAIL_GRENZE, anfrage, anteil, brutto, bruttoCent, eingabeLesen, euro, euroSpanne, hinweise, paket,
  preisBerechnen, unterlagen, unterlagenText, zuschlaegeFuer, zuschlaegeFuerFlaeche,
} from "../werkzeuge/kaufbegutachtung/kaufbegutachtung.js";

const e = (roh) => eingabeLesen(roh).eingabe;
const ids = (h) => [...h.ids].sort();

test("Bruttopreise: netto × 1,19, auf Cent gerundet", () => {
  assert.equal(brutto(890), 1059.1);
  assert.equal(brutto(1490), 1773.1);
  assert.equal(brutto(290), 345.1);
  assert.equal(brutto(120), 142.8);
  assert.equal(brutto(75), 89.25);
  assert.equal(brutto(225), 267.75);
  assert.equal(brutto(10.01), 11.91);        // 11,9119 → 11,91
  assert.equal(brutto(10.05), 11.96);        // 11,9595 → 11,96
  // Keine Gleitkomma-Reste bei allen Preisen aus den Daten.
  const netto = [...Object.values(DATEN.pakete).flatMap((p) => [p.grund.netto, ...p.zuschlaege.map((z) => z.netto)]),
    ...Object.values(DATEN.optionen).flatMap((o) => (o.netto !== undefined ? [o.netto] : [o.netto_von, o.netto_bis]))];
  for (const n of netto) assert.equal(bruttoCent(n), n * 119, `netto ${n}`);
});

test("Betragsformat Deutsch und Englisch", () => {
  assert.equal(euro(1059.1, "de"), "1.059,10 €");
  assert.equal(euro(1059.1, "en"), "€1,059.10");
  assert.equal(euro(89.25, "de"), "89,25 €");
  assert.equal(euro(12345678.5, "de"), "12.345.678,50 €");
  assert.equal(euroSpanne(267.75, 357, "de"), "267,75 – 357,00 €");
  assert.equal(euroSpanne(267.75, 357, "en"), "€267.75 – €357.00");
  assert.equal(euroSpanne(5, 5, "de"), "5,00 €");
});

test("Grundpreis ohne Angaben", () => {
  const w = preisBerechnen({ objekt: "etw" });
  assert.deepEqual(w.positionen.map((p) => p.id), ["grund_etw"]);
  assert.equal(w.bruttoVon, 1059.1);
  assert.equal(w.nettoVon, 890);
  assert.equal(w.ustVon, 169.1);
  assert.equal(preisBerechnen({ objekt: "efh" }).bruttoVon, 1773.1);
});

test("Flächenzuschlag fällt automatisch an (ab flaeche_ab)", () => {
  assert.deepEqual(zuschlaegeFuerFlaeche("etw", 100), []);
  assert.deepEqual(zuschlaegeFuerFlaeche("etw", 100.5), ["gross_etw"]);
  assert.deepEqual(zuschlaegeFuerFlaeche("etw", null), []);
  assert.deepEqual(zuschlaegeFuerFlaeche("efh", 200), []);
  assert.deepEqual(zuschlaegeFuerFlaeche("efh", 201), ["gross_efh"]);
  const w = preisBerechnen(e({ objekt: "etw", flaeche: "120" }));
  assert.deepEqual(w.positionen.map((p) => p.id), ["grund_etw", "gross_etw"]);
  assert.equal(w.bruttoVon, 1297.1);
  // Unter der Grenze nur mit Schalter: Maisonette/Dachgeschoss löst denselben Zuschlag aus.
  assert.deepEqual(preisBerechnen(e({ objekt: "etw", flaeche: "80" })).positionen.map((p) => p.id), ["grund_etw"]);
  const maisonette = e({ objekt: "etw", flaeche: "80", maisonette: true });
  assert.deepEqual(zuschlaegeFuer(maisonette).filter((z) => z.trifftZu), [{ id: "gross_etw", trifftZu: true, gruende: ["schalter"] }]);
  assert.equal(preisBerechnen(maisonette).bruttoVon, 1297.1);
  // Zuschlag nur einmal, auch wenn Fläche und Schalter zutreffen.
  const beides = e({ objekt: "etw", flaeche: "130", maisonette: true });
  assert.deepEqual(zuschlaegeFuer(beides)[0].gruende, ["flaeche", "schalter"]);
  assert.equal(preisBerechnen(beides).positionen.length, 2);
});

test("Zuschläge beim Haus: Vollkeller, über 200 m² oder Einliegerwohnung; keine freie Wahl", () => {
  const haus = e({ objekt: "efh", flaeche: "250", vollkeller: true });
  assert.deepEqual(preisBerechnen(haus).positionen.map((p) => p.id), ["grund_efh", "keller", "gross_efh"]);
  assert.equal(preisBerechnen(haus).bruttoVon, 1773.1 + 178.5 + 238);
  assert.deepEqual(preisBerechnen(e({ objekt: "efh", einlieger: true })).positionen.map((p) => p.id), ["grund_efh", "gross_efh"]);
  // Ein Zuschlag in der Auswahl zählt nicht – er fällt nur an, wenn er zutrifft.
  assert.deepEqual(preisBerechnen({ ...e({ objekt: "efh" }), auswahl: ["keller", "gross_efh"] }).positionen.map((p) => p.id), ["grund_efh"]);
  // Schalter gelten nur für ihre Objektart.
  assert.equal(e({ objekt: "efh", maisonette: true }).maisonette, false);
  assert.equal(e({ objekt: "etw", vollkeller: true }).vollkeller, false);
});

test("Bauakte als Spanne: Summe von – bis", () => {
  const w = preisBerechnen({ objekt: "etw", auswahl: ["bauakte"] });
  assert.equal(w.spanne, true);
  assert.equal(w.bruttoVon, 1326.85);
  assert.equal(w.bruttoBis, 1416.1);
  assert.equal(w.nettoVon, 1115);
  assert.equal(w.nettoBis, 1190);
  assert.equal(euroSpanne(w.bruttoVon, w.bruttoBis, "de"), "1.326,85 – 1.416,10 €");
  const alle = preisBerechnen({ objekt: "efh", auswahl: paket("efh").optionen.map((o) => o.id) });
  const summe = alle.positionen.reduce((s, p) => s + p.bruttoVon * 100, 0) / 100;
  assert.equal(Math.round(summe * 100), Math.round(alle.bruttoVon * 100));
  // Optionen, die es bei der Objektart nicht gibt, zählen nicht (Vermietungs-Check nur bei Wohnungen).
  assert.equal(preisBerechnen({ objekt: "efh", auswahl: ["vermietung"] }).positionen.length, 1);
});

test("Regeln: Wohnung, Baujahr 1905, vermieten, Gasetagenheizung, Milieuschutz", () => {
  const h = hinweise(e({ objekt: "etw", baujahr: "1905", nutzung: "vermieten", heizung: "gasetage", milieuschutz: true }));
  assert.deepEqual(ids(h), [
    "asbest", "blei", "daemmpflicht_etw", "elektro_alt", "flaeche", "gasetage", "gruenderzeit", "heizung_fossil",
    "heizungsfoerderung", "kfw308", "mietpreisbremse", "mietspiegel", "milieuschutz", "schimmel", "thermo_saison",
    "vermieterpflichten",
  ].sort());
  assert.deepEqual([...h.empfohlen].sort(), ["schadstoff", "vermietung"]);
  assert.deepEqual(h.gruppen.map((g) => g.kategorie), ["pflicht", "miete", "pruefen", "foerderung"]);
  // Nicht dabei: Hausregeln, Lage-Regeln ohne gewählte Lage, andere Nutzung, andere Heizung.
  for (const id of ["daemmpflicht_efh", "rauchmelder", "ddr", "sperrfrist", "heizkosten_fern", "heizungspruefung", "oeltank"]) {
    assert.ok(!h.ids.includes(id), id);
  }
  // Mit 6 oder mehr Wohnungen und Gas-Zentralheizung kommt die Heizungsprüfung dazu.
  assert.ok(hinweise(e({ objekt: "etw", heizung: "gas", mfh6: true })).ids.includes("heizungspruefung"));
});

test("Regeln: Haus, Baujahr 1975, Fertighaus, Öl, Brandenburg", () => {
  const h = hinweise(e({ objekt: "efh", baujahr: "1975", fertighaus: true, heizung: "oel", region: "brandenburg" }));
  assert.deepEqual(ids(h), [
    "asbest", "beratung_ea", "daemmpflicht_efh", "ddr", "elektro_35", "fertighaus", "flachdach", "heizung_fossil",
    "heizungsfoerderung", "kfw308", "mineralwolle", "oeltank", "pcb_pak", "schimmel", "thermo_saison",
  ].sort());
  assert.deepEqual(h.empfohlen, ["schadstoff"]);
  for (const id of ["blei", "rauchmelder", "solarpflicht", "elektro_alt", "strang", "platte"]) assert.ok(!h.ids.includes(id), id);
});

test("Regeln: Haus, Baujahr 2015, Wärmepumpe", () => {
  const h = hinweise(e({ objekt: "efh", baujahr: "2015", heizung: "waermepumpe" }));
  assert.deepEqual(ids(h), ["beratung_ea", "neubau", "thermo_saison", "waermepumpe"]);
  assert.deepEqual(h.empfohlen, []);
});

test("Regeln mit Baujahr oder Feld erscheinen erst nach der Eingabe", () => {
  assert.deepEqual(ids(hinweise(e({ objekt: "etw" }))), ["thermo_saison"]);
  assert.deepEqual(ids(hinweise(e({ objekt: "efh" }))), ["beratung_ea", "thermo_saison"]);
  assert.ok(hinweise(e({ objekt: "efh", region: "west" })).ids.includes("rauchmelder"));
  assert.ok(!hinweise(e({ objekt: "efh", region: "unbekannt" })).ids.includes("rauchmelder"));
  // Grenzen sind inklusive.
  assert.ok(hinweise(e({ objekt: "etw", baujahr: "1918" })).ids.includes("gruenderzeit"));
  assert.ok(!hinweise(e({ objekt: "etw", baujahr: "1919" })).ids.includes("gruenderzeit"));
  assert.ok(hinweise(e({ objekt: "etw", baujahr: "1919" })).ids.includes("zwischenkrieg"));
  // Ungültiges Baujahr zählt wie ein leeres Feld und wird gemeldet.
  const ungueltig = eingabeLesen({ objekt: "etw", baujahr: "19x5" });
  assert.equal(ungueltig.eingabe.baujahr, null);
  assert.ok(ungueltig.fehler.baujahr);
  assert.ok(eingabeLesen({ objekt: "etw", flaeche: "5" }).fehler.flaeche);
});

test("Unterlagen: Filter nach Bedingungen, sortiert nach Priorität", () => {
  const ohne = unterlagen(e({ objekt: "etw" })).map((u) => u.id);
  assert.deepEqual(ohne, ["expose", "ea", "teilung", "protokolle", "finanzen", "grundbuch", "verwalterbest",
    "pruefberichte", "modernisierung", "gutachten"]);
  const mit = unterlagen(e({ objekt: "etw", baujahr: "1905", nutzung: "vermieten", heizung: "gasetage" }));
  for (const id of ["mietvertrag", "therme", "blei"]) assert.ok(mit.some((u) => u.id === id), id);
  assert.ok(!mit.some((u) => u.id === "abnahme"));
  const prio = mit.map((u) => u.prio);
  assert.deepEqual(prio, [...prio].sort((a, b) => a - b));
  assert.equal(mit.find((u) => u.id === "mietvertrag").prio, 1);
  assert.ok(unterlagen(e({ objekt: "etw", baujahr: "2022" })).some((u) => u.id === "abnahme"));
  const haus = unterlagen(e({ objekt: "efh", baujahr: "1975", heizung: "oel", fertighaus: true })).map((u) => u.id);
  for (const id of ["oeltank", "fertighaus", "genehmigung", "behoerden"]) assert.ok(haus.includes(id), id);
  for (const id of ["blei", "mietvertrag"]) assert.ok(!haus.includes(id), id);
  assert.ok(unterlagen(e({ objekt: "efh", nutzung: "vermietet_selbst" })).some((u) => u.id === "mietvertrag"));
  assert.ok(!unterlagen(e({ objekt: "efh", nutzung: "selbst" })).some((u) => u.id === "mietvertrag"));
  const text = unterlagenText(e({ objekt: "etw" }), ["expose"]);
  assert.match(text, /\[x\] Exposé/);
  assert.match(text, /\[ \] Energieausweis/);
  assert.match(text, /#wohnung$/);
  assert.match(unterlagenText(e({ objekt: "efh" }), [], "en"), /pre-purchase-inspection-berlin\/#house$/);
});

test("Anfrage per E-Mail: Inhalt und Länge unter 1.800 Zeichen", () => {
  const eingabe = e({ objekt: "etw", flaeche: "85", baujahr: "1905", heizung: "gasetage", nutzung: "vermieten",
    region: "ost", milieuschutz: true, mfh6: true, maisonette: true });
  const a = anfrage({ eingabe, auswahl: ["vermietung", "englisch"], vorhanden: ["expose"],
    adresse: "Musterstraße 1, 10115 Berlin", termin: "ab 10. November" });
  assert.ok(a.href.startsWith("mailto:info@ing-bassam.de?subject="));
  assert.ok(a.href.includes("%0D%0A"), "Zeilenumbrüche als CRLF");
  for (const teil of ["Eigentumswohnung", "Musterstraße 1", "ab 10. November", "Baujahr: 1905", "Vermietungs-Check: 345,10 €",
    "Gesamt: 1.785,00 € inkl. 19 % USt (netto 1.500,00 €)", "Maisonette oder Dachgeschoss",
    "Noch fehlende unverzichtbare Unterlagen", "Namen und Bankdaten von Mietern bitte schwärzen"]) {
    assert.ok(a.text.includes(teil), teil);
  }
  assert.ok(a.text.includes("- Exposé"));
  assert.ok(!a.text.split("Noch fehlende")[1].includes("Exposé"), "Vorhandenes steht nicht bei den fehlenden");
  assert.equal(decodeURIComponent(a.href.split("&body=")[1]).replace(/\r\n/g, "\n"), a.text);
  assert.ok(a.laenge <= MAIL_GRENZE);

  // Schlimmster Fall: alle Optionen, alle Unterlagen vorhanden, lange Adresse.
  const haus = e({ objekt: "efh", flaeche: "250", baujahr: "1960", heizung: "oel", nutzung: "vermietet_selbst",
    region: "brandenburg", fertighaus: true, vollkeller: true, einlieger: true });
  const alle = unterlagen(haus).map((u) => u.id);
  const voll = anfrage({ eingabe: haus, auswahl: paket("efh").optionen.map((o) => o.id), vorhanden: alle,
    adresse: "x".repeat(400), termin: "y".repeat(300) });
  assert.ok(voll.laenge <= MAIL_GRENZE, `Länge ${voll.laenge}`);
  // Mit enger Grenze wird die Unterlagenliste gekürzt, die Pflichtangaben bleiben.
  const eng = anfrage({ eingabe: haus, auswahl: ["englisch"], vorhanden: [], grenze: 1100 });
  assert.ok(eng.laenge <= 1100, `Länge ${eng.laenge}`);
  assert.ok(eng.text.includes("Gesamt:"));
  assert.ok(eng.text.includes("Namen und Bankdaten"));
  assert.match(eng.text, /… und \d+ weitere|Exposé/);

  const englisch = anfrage({ eingabe: e({ objekt: "efh" }), sprache: "en" });
  assert.ok(englisch.text.includes("Total: €1,773.10 incl. 19% VAT (net €1,490.00)"));
  assert.ok(englisch.betreff.startsWith("Enquiry: pre-purchase inspection"));
});

test("Anteil an Gemeinschaftskosten", () => {
  assert.equal(anteil(100000, 45, 1000), 4500);
  assert.equal(anteil("85000", "123", "10000"), 1045.5);
  assert.equal(anteil("", 45, 1000), null);
  assert.equal(anteil(1000, 45, 0), null);
  assert.equal(anteil(1000, 2000, 1000), null);
});
