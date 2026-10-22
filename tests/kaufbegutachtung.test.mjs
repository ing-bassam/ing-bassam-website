// Tests für den Kern des Hinweis-Assistenten der Kaufbegutachtung
// (werkzeuge/kaufbegutachtung/kaufbegutachtung.js). Preise gibt es dort bewusst nicht:
// Sie kommen nur auf Anfrage per E-Mail.
import test from "node:test";
import assert from "node:assert/strict";
import {
  DATEN, MAIL_GRENZE, SCHALTER, anfrage, anteil, eingabeLesen, euro, hinweise, leistungsumfang, unterlagen,
  unterlagenText,
} from "../werkzeuge/kaufbegutachtung/kaufbegutachtung.js";
import * as kern from "../werkzeuge/kaufbegutachtung/kaufbegutachtung.js";

const e = (roh) => eingabeLesen(roh).eingabe;
const ids = (h) => [...h.ids].sort();
// Eurobetrag wie „1.059,10 €“, „150 €“, „€1,059.10“ oder „EUR 150“.
const EUROBETRAG = /\d[\d.,]*\s?(?:€|EUR\b)|(?:€|\bEUR)\s?\d/;

test("Keine Preise im Kern und in den Daten", () => {
  for (const name of ["preisBerechnen", "paket", "brutto", "bruttoCent", "euroSpanne", "zuschlaegeFuer"]) {
    assert.equal(kern[name], undefined, name);
  }
  for (const feld of ["mwst", "stundensatz_netto", "pakete", "optionen"]) assert.equal(DATEN[feld], undefined, feld);
  assert.equal(DATEN.eingaben.preis_schalter, undefined);
  const json = JSON.stringify(DATEN);
  for (const feld of ["\"netto\"", "\"netto_von\"", "\"netto_bis\"", "\"zuschlaege\"", "\"empfiehlt\""]) {
    assert.ok(!json.includes(feld), feld);
  }
});

test("Leistungsumfang je Objektart, ohne Beträge", () => {
  for (const objekt of ["etw", "efh"]) {
    for (const sprache of ["de", "en"]) {
      const liste = leistungsumfang(objekt, sprache);
      assert.ok(liste.length >= 5, `${objekt}/${sprache}`);
      for (const punkt of liste) assert.doesNotMatch(punkt, EUROBETRAG, punkt);
    }
  }
  assert.ok(leistungsumfang("etw").some((x) => x.includes("WEG-Unterlagen")));
  assert.ok(leistungsumfang("efh", "en").some((x) => x.includes("roof to basement")));
});

test("Merkmale gelten nur für ihre Objektart", () => {
  assert.deepEqual([...SCHALTER].sort(), ["einlieger", "fertighaus", "maisonette", "mfh6", "milieuschutz", "vollkeller"]);
  assert.equal(e({ objekt: "efh", maisonette: true }).maisonette, false);
  assert.equal(e({ objekt: "etw", maisonette: true }).maisonette, true);
  assert.equal(e({ objekt: "etw", vollkeller: true }).vollkeller, false);
  assert.equal(e({ objekt: "efh", vollkeller: true, einlieger: true }).einlieger, true);
});

test("Betragsformat für den Anteil an Gemeinschaftskosten", () => {
  assert.equal(euro(4500, "de"), "4.500,00 €");
  assert.equal(euro(4500, "en"), "€4,500.00");
  assert.equal(euro(1045.5, "de"), "1.045,50 €");
});

test("Regeln: Wohnung, Baujahr 1905, vermieten, Gasetagenheizung, Milieuschutz", () => {
  const h = hinweise(e({ objekt: "etw", baujahr: "1905", nutzung: "vermieten", heizung: "gasetage", milieuschutz: true }));
  assert.deepEqual(ids(h), [
    "asbest", "blei", "daemmpflicht_etw", "elektro_alt", "flaeche", "gasetage", "gruenderzeit", "heizung_fossil",
    "mietpreisbremse", "mietspiegel", "milieuschutz", "schimmel", "thermo_saison", "vermieterpflichten",
  ].sort());
  assert.equal(h.empfohlen, undefined, "keine Empfehlung von Optionen mehr");
  assert.deepEqual(h.gruppen.map((g) => g.kategorie), ["pflicht", "miete", "pruefen", "foerderung"]);
  // Nicht dabei: Hausregeln, Lage-Regeln ohne gewählte Lage, andere Nutzung, andere Heizung –
  // und die Förderhinweise, die Selbstnutzung voraussetzen (KfW 308, Heizungstausch-Bonus).
  for (const id of ["daemmpflicht_efh", "rauchmelder", "ddr", "sperrfrist", "heizkosten_fern", "heizungspruefung", "oeltank",
    "kfw308", "heizungsfoerderung"]) {
    assert.ok(!h.ids.includes(id), id);
  }
  // Mit 6 oder mehr Wohnungen und Gas-Zentralheizung kommt die Heizungsprüfung dazu.
  assert.ok(hinweise(e({ objekt: "etw", heizung: "gas", mfh6: true })).ids.includes("heizungspruefung"));
});

test("Regeln: Haus, Baujahr 1975, Fertighaus, Öl, Brandenburg, selbst nutzen", () => {
  const h = hinweise(e({ objekt: "efh", baujahr: "1975", fertighaus: true, heizung: "oel", region: "brandenburg", nutzung: "selbst" }));
  assert.deepEqual(ids(h), [
    "asbest", "beratung_ea", "daemmpflicht_efh", "ddr", "elektro_35", "fertighaus", "flachdach", "heizung_fossil",
    "heizungsfoerderung", "kfw308", "mineralwolle", "oeltank", "pcb_pak", "schimmel", "thermo_saison",
  ].sort());
  for (const id of ["blei", "rauchmelder", "solarpflicht", "elektro_alt", "strang", "platte"]) assert.ok(!h.ids.includes(id), id);
});

test("Regeln: Haus, Baujahr 2015, Wärmepumpe", () => {
  const h = hinweise(e({ objekt: "efh", baujahr: "2015", heizung: "waermepumpe" }));
  assert.deepEqual(ids(h), ["beratung_ea", "neubau", "thermo_saison", "waermepumpe"]);
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

test("Angebot anfordern: Inhalt der E-Mail ohne Preise, Länge unter 1.800 Zeichen", () => {
  const eingabe = e({ objekt: "etw", flaeche: "85", baujahr: "1905", heizung: "gasetage", nutzung: "vermieten",
    region: "ost", milieuschutz: true, mfh6: true, maisonette: true });
  const a = anfrage({ eingabe, vorhanden: ["expose"], adresse: "Musterstraße 1, 10115 Berlin", termin: "ab 10. November" });
  assert.ok(a.href.startsWith("mailto:info@ing-bassam.de?subject="));
  assert.ok(a.href.includes("%0D%0A"), "Zeilenumbrüche als CRLF");
  for (const teil of ["Objekt: Eigentumswohnung", "Adresse: Musterstraße 1", "Wunschtermin: ab 10. November",
    "Wohnfläche: 85 m²", "Baujahr: 1905", "Heizung: Gasetagenheizung", "Nutzung: Vermieten", "Lage: Berlin (Ost)",
    "Maisonette oder Dachgeschoss", "Bitte senden Sie mir Ihr Angebot mit Preisen und der Leistungsübersicht.",
    "Noch fehlende unverzichtbare Unterlagen", "Namen und Bankdaten von Mietern bitte schwärzen"]) {
    assert.ok(a.text.includes(teil), teil);
  }
  assert.ok(a.text.includes("- Exposé"));
  assert.ok(!a.text.split("Noch fehlende")[1].includes("Exposé"), "Vorhandenes steht nicht bei den fehlenden");
  assert.doesNotMatch(`${a.betreff}\n${a.text}`, EUROBETRAG);
  assert.doesNotMatch(a.text, /Gesamt|Preisrechner|inkl\. 19/);
  assert.equal(decodeURIComponent(a.href.split("&body=")[1]).replace(/\r\n/g, "\n"), a.text);
  assert.ok(a.laenge <= MAIL_GRENZE);

  // Schlimmster Fall: alle Unterlagen vorhanden, alle Merkmale, lange Adresse.
  const haus = e({ objekt: "efh", flaeche: "250", baujahr: "1960", heizung: "oel", nutzung: "vermietet_selbst",
    region: "brandenburg", fertighaus: true, vollkeller: true, einlieger: true });
  const alle = unterlagen(haus).map((u) => u.id);
  const voll = anfrage({ eingabe: haus, vorhanden: alle, adresse: "x".repeat(400), termin: "y".repeat(300) });
  assert.ok(voll.laenge <= MAIL_GRENZE, `Länge ${voll.laenge}`);
  assert.ok(voll.text.includes("Voll unterkellert; Mit Einliegerwohnung; Fertighaus / Holztafelbau"));
  // Mit enger Grenze wird die Unterlagenliste gekürzt, die Pflichtangaben bleiben.
  const eng = anfrage({ eingabe: haus, vorhanden: [], grenze: 800 });
  assert.ok(eng.laenge <= 800, `Länge ${eng.laenge}`);
  assert.ok(eng.text.includes("Bitte senden Sie mir Ihr Angebot"));
  assert.ok(eng.text.includes("Namen und Bankdaten"));
  assert.match(eng.text, /… und \d+ weitere|Exposé/);

  const englisch = anfrage({ eingabe: e({ objekt: "efh" }), sprache: "en" });
  assert.ok(englisch.text.includes("Please send me your quote with prices and the list of services."));
  assert.ok(englisch.text.includes("Property: House"));
  assert.ok(englisch.betreff.startsWith("Enquiry: pre-purchase inspection"));
  assert.doesNotMatch(englisch.text, EUROBETRAG);
});

test("Anteil an Gemeinschaftskosten", () => {
  assert.equal(anteil(100000, 45, 1000), 4500);
  assert.equal(anteil("85000", "123", "10000"), 1045.5);
  assert.equal(anteil("", 45, 1000), null);
  assert.equal(anteil(1000, 45, 0), null);
  assert.equal(anteil(1000, 2000, 1000), null);
});
