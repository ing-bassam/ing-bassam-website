// Tests für die private Angebotsseite Kaufbegutachtung (angebot/kaufbegutachtung/)
// und das Werkzeug tools/angebot_verschluesseln.mjs.
//
// Alle Daten hier sind erfundene Beispiele mit einem Testschlüssel – der echte
// Schlüssel und die echten Inhalte (inhalte.json) liegen nie im Repository.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import {
  HOECHSTENS_HINWEISE, anfrage, aufzaehlung, bytesZuBase64url, brutto, cent, eingabeLesen, entschluesseln, euro, euroSpanne,
  hinweise, kurzfassung, linkBauen, linkLesen, preisBerechnen, schluesselErzeugen, unterlagen, verschluesseln, zuschlaegeFuer,
} from "../angebot/kaufbegutachtung/angebot.js";
import { UI } from "../angebot/kaufbegutachtung/oberflaeche.js";
import { PAKET } from "../angebot/kaufbegutachtung/paket.js";
import { WURZEL, imRepository, linksDatei, main, paketBauen, paketDatei } from "../tools/angebot_verschluesseln.mjs";

// Testschlüssel: die Bytes 0, 1, 2, … 31 – nur für diese Tests.
const TESTSCHLUESSEL = bytesZuBase64url(Uint8Array.from({ length: 32 }, (_, i) => i));
const EUROBETRAG = /\d[\d.,]*\s?(?:€|EUR\b)|(?:€|\bEUR)\s?\d/;

const zweisprachig = (de, en = `${de} (EN)`) => ({ de, en });
const nameText = (name, text) => ({ de: { name, text }, en: { name: `${name} EN`, text: `${text} EN` } });
const regel = (id, kategorie, objekt, extra = {}) => ({
  id, kategorie, objekt, ...extra,
  de: { titel: `Titel ${id}`, text: `Erster Satz zu ${id}. Zweiter Satz, z. B. mit Abkürzung. Dritter Satz.` },
  en: { titel: `Title ${id}`, text: `First sentence on ${id}. Second sentence. Third sentence.` },
  quelle: { titel: `Quelle ${id}`, url: `https://example.org/${id}` },
});
const unterlage = (id, prio, extra = {}) => ({ id, prio, ...extra, de: `Unterlage ${id}`, en: `Document ${id}`, wo_de: "Verkäufer", wo_en: "Seller" });

const BEISPIEL = {
  stand: zweisprachig("Januar 2030", "January 2030"),
  mwst: 0.19,
  stundensatz_netto: 55,
  kontakt: { email: "test@example.org", telefon: "+49 30 000000" },
  pakete: {
    etw: {
      grund: { id: "grund_etw", netto: 600, ...nameText("Grundpaket Wohnung", "Begehung (ca. 2 Std., innen), Bericht mit Mängelliste, Fazit vor Ort.") },
      zuschlaege: [{ id: "gross_etw", netto: 110, auto: { flaeche_ab: 80.01 }, ...nameText("Groß", "Mehr Aufwand.") }],
      optionen: ["foto", "akte", "check"],
    },
    efh: {
      grund: { id: "grund_efh", netto: 1100, ...nameText("Grundpaket Haus", "Begehung, Bericht.") },
      zuschlaege: [
        { id: "keller", netto: 170, ...nameText("Keller", "Mehr Keller.") },
        { id: "gross_efh", netto: 210, auto: { flaeche_ab: 150.01 }, ...nameText("Groß", "Mehr Haus.") },
      ],
      optionen: ["foto_efh", "akte"],
    },
  },
  optionen: {
    foto: { netto: 130, ...nameText("Fotos Wohnung", "Bilder.") },
    foto_efh: { netto: 160, ...nameText("Fotos Haus", "Bilder.") },
    akte: { netto_von: 140, netto_bis: 210, ...nameText("Akte", "Nach Aufwand.") },
    check: { netto: 70, ...nameText("Check", "Prüfung.") },
  },
  eingaben: {
    heizung: [{ id: "gas", ...zweisprachig("Gas") }, { id: "oel", ...zweisprachig("Öl") }],
    nutzung: [{ id: "selbst", ...zweisprachig("Selbst") }, { id: "vermieten", ...zweisprachig("Vermieten") }],
    region: [{ id: "ost", ...zweisprachig("Ost") }, { id: "west", ...zweisprachig("West") }],
    schalter: { fertig: { objekt: "efh", ...zweisprachig("Fertighaus") } },
  },
  regeln: [
    regel("f1", "foerderung", "beide"),
    regel("r1", "pruefen", "beide", { bis: 2000 }),
    regel("r2", "pruefen", "beide", { bis: 2000 }),
    regel("r3", "pruefen", "beide", { bis: 2000, empfiehlt: ["akte"] }),
    regel("r4", "pruefen", "beide", { bis: 2000 }),
    regel("m1", "miete", "etw", { nutzung: ["vermieten"], empfiehlt: ["check"] }),
    regel("h1", "pruefen", "efh", { fertig: true }),
    regel("g1", "pruefen", "beide", { heizung: ["oel"] }),
    regel("p1", "pflicht", "beide", { bis: 1970 }),
  ],
  unterlagen: {
    etw: [unterlage("a", 2), unterlage("b", 1), unterlage("c", 1, { nutzung: ["vermieten"] }), unterlage("d", 3, { bis: 1970 })],
    efh: [unterlage("e", 1), unterlage("f", 2, { fertig: true })],
  },
  text: {
    de: {
      objekt_etw: "Eigentumswohnung", objekt_efh: "Einfamilienhaus", objekt_etw_unter: "mit WEG", objekt_efh_unter: "auch DHH",
      pauschal: "Pauschal.", ausserhalb: "Außerhalb.", ablauf: [1, 2, 3, 4].map((n) => ({ t: `Schritt ${n}`, w: "bald", d: "Text." })),
      grenzen: ["Keine Öffnung."], beauftragen: "Erst Angebot, dann Auftrag.", rechtsstand: "Stand 2030", prio: { 1: "Muss", 2: "Soll", 3: "Kann" },
      qr_titel: "nicht gebraucht",
    },
    en: {
      objekt_etw: "Flat", objekt_efh: "House", objekt_etw_unter: "with WEG", objekt_efh_unter: "also semi",
      pauschal: "Fixed.", ausserhalb: "Outside.", ablauf: [1, 2, 3, 4].map((n) => ({ t: `Step ${n}`, w: "soon", d: "Text." })),
      grenzen: ["No opening."], beauftragen: "Quote first.", rechtsstand: "As of 2030", prio: { 1: "Must", 2: "Should", 3: "Could" },
    },
  },
};

const DATEN = paketBauen(BEISPIEL);
const e = (roh) => eingabeLesen(roh, DATEN).eingabe;

// ------------------------------------------------------------ Paketbau

test("Paketbau ergänzt die Merkmale der Zuschläge und lässt Unnötiges weg", () => {
  assert.equal(DATEN.pakete.etw.zuschlaege[0].schalter, "maisonette");
  assert.equal(DATEN.pakete.efh.zuschlaege[0].schalter, "vollkeller");
  assert.equal(DATEN.pakete.efh.zuschlaege[1].schalter, "einlieger");
  assert.deepEqual(DATEN.eingaben.schalter.maisonette, { objekt: "etw", de: "Maisonette oder Dachgeschoss", en: "Maisonette or attic flat", preis: true });
  assert.equal(DATEN.eingaben.schalter.fertig.preis, undefined, "Merkmal ohne Preisbezug");
  assert.equal(DATEN.text.de.qr_titel, undefined);
  assert.deepEqual(DATEN.kontakt, { email: "test@example.org", telefon: "+49 30 000000" });
  // Die Quelle selbst bleibt unverändert.
  assert.equal(BEISPIEL.pakete.etw.zuschlaege[0].schalter, undefined);
});

test("Paketbau meldet alle Lücken auf einmal", () => {
  const kaputt = structuredClone(BEISPIEL);
  kaputt.mwst = 19;
  kaputt.regeln[0].kategorie = "werbung";
  kaputt.regeln[1].empfiehlt = ["gibtsnicht"];
  kaputt.pakete.etw.optionen.push("fehlt");
  kaputt.pakete.etw.zuschlaege.push({ id: "raetsel", netto: 10, ...nameText("X", "Y") });
  kaputt.regeln[2].quelle.url = "http://unsicher.example";
  assert.throws(() => paketBauen(kaputt), (fehler) => {
    for (const teil of ["mwst", "Kategorie werbung", "unbekannte Option gibtsnicht", "Option fehlt unbekannt",
      "Zuschlag raetsel: weder Wohnfläche noch Merkmal", "https://"]) {
      assert.ok(fehler.message.includes(teil), teil);
    }
    return true;
  });
});

// ------------------------------------------------- Ver- und Entschlüsselung

test("Verschlüsseln und über die Seitenlogik entschlüsseln", async () => {
  const paket = await verschluesseln(DATEN, TESTSCHLUESSEL);
  assert.equal(paket.v, 1);
  assert.ok(!paket.daten.includes("Grundpaket"), "kein Klartext im Chiffrat");
  assert.deepEqual(await entschluesseln(paket, TESTSCHLUESSEL), DATEN);
  // Jede Verschlüsselung bekommt einen neuen Zufallswert (IV).
  const nochmal = await verschluesseln(DATEN, TESTSCHLUESSEL);
  assert.notEqual(nochmal.iv, paket.iv);
  assert.notEqual(nochmal.daten, paket.daten);
});

test("Falscher, fehlender oder kaputter Schlüssel ergibt nichts", async () => {
  const paket = await verschluesseln(DATEN, TESTSCHLUESSEL);
  assert.equal(await entschluesseln(paket, schluesselErzeugen()), null);
  assert.equal(await entschluesseln(paket, ""), null);
  assert.equal(await entschluesseln(paket, TESTSCHLUESSEL.slice(0, 20)), null);
  assert.equal(await entschluesseln(paket, "nicht base64 !!"), null);
  const veraendert = { ...paket, daten: (paket.daten[0] === "A" ? "B" : "A") + paket.daten.slice(1) };
  assert.equal(await entschluesseln(veraendert, TESTSCHLUESSEL), null, "manipuliertes Chiffrat");
  assert.equal(await entschluesseln({ ...paket, v: 2 }, TESTSCHLUESSEL), null);
  await assert.rejects(() => verschluesseln(DATEN, "zu-kurz"));
});

test("Ausgeliefertes paket.js hat das erwartete Format und ist ohne Schlüssel nicht lesbar", async () => {
  assert.deepEqual(Object.keys(PAKET).sort(), ["daten", "iv", "v"]);
  assert.equal(PAKET.v, 1);
  assert.match(PAKET.iv, /^[A-Za-z0-9+/]{16}$/);
  assert.match(PAKET.daten, /^[A-Za-z0-9+/]+={0,2}$/);
  assert.equal(await entschluesseln(PAKET, TESTSCHLUESSEL), null);
});

test("Schlüssel ist zufällig, 32 Bytes, Base64url", () => {
  const a = schluesselErzeugen();
  assert.match(a, /^[A-Za-z0-9_-]{43}$/);
  assert.notEqual(a, schluesselErzeugen());
});

// ------------------------------------------------------------------ Link

test("Link: Schlüssel, Objektart und Sprache aus dem Teil nach #", () => {
  assert.deepEqual(linkLesen(`#k=${TESTSCHLUESSEL}&o=haus&l=en`), { schluessel: TESTSCHLUESSEL, objekt: "efh", sprache: "en" });
  assert.deepEqual(linkLesen("#k=abc&o=wohnung&l=de"), { schluessel: "abc", objekt: "etw", sprache: "de" });
  assert.deepEqual(linkLesen("#k=abc&o=house"), { schluessel: "abc", objekt: "efh", sprache: null });
  assert.deepEqual(linkLesen("#o=flat&l=fr"), { schluessel: "", objekt: "etw", sprache: null });
  assert.deepEqual(linkLesen(""), { schluessel: "", objekt: null, sprache: null });
  const link = linkBauen({ basis: "https://ing-bassam.de/angebot/kaufbegutachtung/", schluessel: TESTSCHLUESSEL, objekt: "efh", sprache: "en" });
  assert.equal(link, `https://ing-bassam.de/angebot/kaufbegutachtung/#k=${TESTSCHLUESSEL}&o=haus&l=en`);
  assert.deepEqual(linkLesen(new URL(link).hash), { schluessel: TESTSCHLUESSEL, objekt: "efh", sprache: "en" });
});

// ------------------------------------------------------------------ Preis

test("Beträge: Brutto aus Netto in Cent, deutsches und englisches Format", () => {
  assert.equal(brutto(cent(1000), 0.19), 119000);
  assert.equal(brutto(cent(55), 0.19), 6545);
  assert.equal(brutto(cent(12.34), 0.19), 1468, "auf Cent gerundet");
  assert.equal(euro(119000, "de"), "1.190,00 €");
  assert.equal(euro(119000, "en"), "€1,190.00");
  assert.equal(euroSpanne(16660, 24990, "de"), "166,60 – 249,90 €");
  assert.equal(euroSpanne(16660, 24990, "en"), "€166.60 – €249.90");
  assert.equal(euroSpanne(100, 100, "de"), "1,00 €");
});

test("Preis Wohnung: Grundpaket, Zuschlag über Fläche, Extras mit Spanne", () => {
  const nur = preisBerechnen(DATEN, e({ objekt: "etw" }));
  assert.equal(nur.brutto_von, 71400);
  assert.equal(nur.spanne, false);
  assert.deepEqual(nur.posten.map((p) => p.id), ["grund_etw"]);

  const ein = e({ objekt: "etw", flaeche: "90" });
  const p = preisBerechnen(DATEN, ein, ["foto", "akte", "foto_efh"]);
  assert.deepEqual(p.posten.map((x) => x.id), ["grund_etw", "gross_etw", "foto", "akte"], "foto_efh gehört zum Haus");
  assert.equal(p.netto_von, 98000);
  assert.equal(p.netto_bis, 105000);
  assert.equal(p.brutto_von, 116620);
  assert.equal(p.brutto_bis, 124950);
  assert.equal(p.ust_von, 18620);
  assert.equal(p.spanne, true);
  assert.equal(p.mwst_prozent, 19);
  assert.equal(p.posten.reduce((s, x) => s + x.brutto_bis, 0), p.brutto_bis, "Summe der Posten = Gesamtbrutto");
  assert.deepEqual(p.anteile, { grund: 71400, zuschlag: 13090, option: 40460 });
  assert.deepEqual(p.anteile_von, { grund: 71400, zuschlag: 13090, option: 32130 });
  assert.equal(zuschlaegeFuer(DATEN, ein)[0].grund, "flaeche");
  // Genau an der Grenze (80 m²) noch kein Zuschlag; Merkmal Maisonette löst ihn aus.
  assert.equal(zuschlaegeFuer(DATEN, e({ objekt: "etw", flaeche: "80" }))[0].aktiv, false);
  const maisonette = zuschlaegeFuer(DATEN, e({ objekt: "etw", schalter: { maisonette: true } }))[0];
  assert.deepEqual([maisonette.aktiv, maisonette.grund], [true, "schalter"]);
});

test("Preis Haus: Merkmale Vollkeller und Einliegerwohnung, Merkmale nur für ihre Objektart", () => {
  const haus = e({ objekt: "efh", schalter: { vollkeller: true, einlieger: true, maisonette: true } });
  assert.equal(haus.schalter.maisonette, false, "Maisonette gibt es nur bei Wohnungen");
  const p = preisBerechnen(DATEN, haus, []);
  assert.deepEqual(p.posten.map((x) => x.id), ["grund_efh", "keller", "gross_efh"]);
  assert.equal(p.brutto_von, 176120);
  assert.equal(euro(p.brutto_von, "de"), "1.761,20 €");
});

test("Eingaben: ungültige Zahlen werden als Fehler gemeldet und nicht verwendet", () => {
  const { eingabe, fehler } = eingabeLesen({ objekt: "etw", flaeche: "5", baujahr: "19,5", heizung: "kohle" }, DATEN);
  assert.deepEqual(fehler, { flaeche: true, baujahr: true });
  assert.equal(eingabe.flaeche, null);
  assert.equal(eingabe.baujahr, null);
  assert.equal(eingabe.heizung, "");
  assert.equal(eingabeLesen({ flaeche: "85,5" }, DATEN).eingabe.flaeche, 85.5);
});

// ------------------------------------------------- Hinweise und Unterlagen

test("Hinweise: höchstens sechs, Pflichten zuerst, dann Vermietung, dann Prüfschwerpunkte", () => {
  const h = hinweise(DATEN, e({ objekt: "etw", baujahr: "1960", nutzung: "vermieten", heizung: "oel" }), "de");
  assert.deepEqual(h.alle.map((x) => x.id), ["p1", "m1", "r1", "r2", "r3", "r4", "g1", "f1"]);
  assert.equal(h.kompakt.length, HOECHSTENS_HINWEISE);
  assert.deepEqual(h.kompakt.map((x) => x.id), ["p1", "m1", "r1", "r2", "r3", "r4"]);
  assert.equal(h.anzahl, 8);
  assert.deepEqual([...h.empfohlen].sort(), ["akte", "check"]);
  assert.equal(h.alle[0].kurz, "Erster Satz zu p1. Zweiter Satz, z. B. mit Abkürzung.");
  assert.deepEqual(h.alle[0].quelle, { titel: "Quelle p1", url: "https://example.org/p1" });
  // Ohne Baujahr: keine Regeln mit Baujahr-Grenze; Hausregel nur mit Merkmal.
  assert.deepEqual(hinweise(DATEN, e({ objekt: "efh" })).alle.map((x) => x.id), ["f1"]);
  assert.deepEqual(hinweise(DATEN, e({ objekt: "efh", schalter: { fertig: true } })).alle.map((x) => x.id), ["h1", "f1"]);
  assert.equal(hinweise(DATEN, e({ objekt: "etw" }), "en").alle[0].titel, "Title f1");
});

test("Kurzfassung: zwei Sätze, Abkürzungen beenden keinen Satz", () => {
  assert.equal(kurzfassung("Eins. Zwei. Drei."), "Eins. Zwei.");
  assert.equal(kurzfassung("Bis 01.02.2030 gilt es, z. B. für Öfen. Danach nicht. Rest."), "Bis 01.02.2030 gilt es, z. B. für Öfen. Danach nicht.");
  assert.equal(kurzfassung("Ca. 2 Std. Arbeit, ca. 10 € Gebühr. Zweiter. Dritter."), "Ca. 2 Std. Arbeit, ca. 10 € Gebühr. Zweiter.");
  assert.equal(kurzfassung("Nur ein Satz."), "Nur ein Satz.");
  assert.equal(kurzfassung("First, e.g. this. Second. Third.", 1), "First, e.g. this.");
});

test("Unterlagen nach Priorität, Bedingungen wie bei den Hinweisen", () => {
  assert.deepEqual(unterlagen(DATEN, e({ objekt: "etw" })).map((u) => u.id), ["b", "a"]);
  assert.deepEqual(unterlagen(DATEN, e({ objekt: "etw", baujahr: "1960", nutzung: "vermieten" })).map((u) => u.id), ["b", "c", "a", "d"]);
  assert.deepEqual(unterlagen(DATEN, e({ objekt: "efh", schalter: { fertig: true } }), "en")[1], { id: "f", prio: 2, text: "Document f", wo: "Seller" });
});

test("Leistungsumfang als Aufzählung, Kommas in Klammern bleiben zusammen", () => {
  assert.deepEqual(aufzaehlung("Begehung (ca. 2 Std., innen), Bericht mit Mängelliste, fazit vor Ort."),
    ["Begehung (ca. 2 Std., innen)", "Bericht mit Mängelliste", "Fazit vor Ort"]);
});

// ---------------------------------------------------------------- E-Mail

test("E-Mail „Auswahl senden“: Auswahl, Gesamtpreis brutto, Unterlagen, Bitte um verbindliches Angebot", () => {
  const ein = e({ objekt: "etw", flaeche: "90", baujahr: "1960", nutzung: "vermieten" });
  const m = anfrage({
    daten: DATEN, t: UI.de.mail, eingabe: ein, gewaehlt: ["foto", "akte"], vorhanden: ["b"],
    felder: { adresse: "Musterstraße 1, Berlin", termin: "ab Montag", notar: "15. Dezember" }, sprache: "de",
  });
  assert.equal(m.betreff, "Kaufbegutachtung – meine Auswahl: Eigentumswohnung, Musterstraße 1, Berlin");
  for (const teil of [
    "Objekt: Eigentumswohnung", "Wohnfläche: 90 m²", "Baujahr: 1960", "Nutzung: Vermieten",
    "- Grundpaket Wohnung: 714,00 €", "- Zuschlag: Groß: 130,90 €", "- Akte: 166,60 – 249,90 €",
    "Gesamtpreis inkl. 19 % USt: 1.166,20 – 1.249,50 €", "Wunschtermin: ab Montag", "Notartermin: 15. Dezember",
    "Diese Unterlagen liegen vor (im Anhang):\n- Unterlage b", "Noch fehlende unverzichtbare Unterlagen:\n- Unterlage c",
    "Bitte senden Sie mir das verbindliche Angebot mit Bedingungen und Widerrufsbelehrung.",
  ]) {
    assert.ok(m.text.includes(teil), teil);
  }
  assert.ok(m.href.startsWith("mailto:test@example.org?subject="));
  assert.ok(m.href.includes("%0D%0A"), "Zeilenumbrüche als CRLF");
  assert.equal(decodeURIComponent(m.href.split("&body=")[1]), m.text.replace(/\n/g, "\r\n"));

  const en = anfrage({ daten: DATEN, t: UI.en.mail, eingabe: e({ objekt: "efh" }), sprache: "en" });
  assert.ok(en.text.includes("Total price incl. 19% VAT: €1,309.00"));
  assert.ok(en.text.includes("Please send me the binding quote with your terms and information on the right of withdrawal."));
});

test("E-Mail bleibt unter der Längengrenze", () => {
  const lang = structuredClone(DATEN);
  lang.unterlagen.etw = Array.from({ length: 30 }, (_, i) => unterlage(`x${i}`, 1));
  for (const u of lang.unterlagen.etw) u.de = `Sehr lange Unterlage ${u.id} `.repeat(8);
  const m = anfrage({
    daten: lang, t: UI.de.mail, eingabe: eingabeLesen({ objekt: "etw" }, lang).eingabe, gewaehlt: ["foto", "akte", "check"],
    vorhanden: ["x1", "x2", "x3"], felder: { adresse: "A".repeat(500), termin: "B".repeat(500) }, sprache: "de", grenze: 1800,
  });
  assert.ok(m.laenge <= 1800, `Länge ${m.laenge}`);
  assert.match(m.text, /… und \d+ weitere/);
  assert.ok(m.text.includes("Bitte senden Sie mir das verbindliche Angebot"));
});

// ------------------------------------------------------------ Oberfläche

function schluesselPfade(knoten, pfad = "") {
  if (typeof knoten !== "object" || knoten === null) return [pfad];
  return Object.entries(knoten).flatMap(([k, v]) => schluesselPfade(v, `${pfad}.${k}`));
}

test("Oberflächentexte: Deutsch und Englisch vollständig, ohne Beträge", () => {
  assert.deepEqual(schluesselPfade(UI.en).sort(), schluesselPfade(UI.de).sort());
  const alle = JSON.stringify(UI);
  assert.doesNotMatch(alle, EUROBETRAG);
  assert.ok(UI.de.mail.bitte === "Bitte senden Sie mir das verbindliche Angebot mit Bedingungen und Widerrufsbelehrung.");
});

// --------------------------------------------------------------- Werkzeug

test("Werkzeug: Pfade im Repository werden abgelehnt", () => {
  assert.equal(imRepository(join(WURZEL, "angebot", "schluessel.txt")), true);
  assert.equal(imRepository(WURZEL), true);
  assert.equal(imRepository(join(WURZEL, "..", "privat", "schluessel.txt")), false);
});

test("Werkzeug: paket.js und Links-Datei", () => {
  const datei = paketDatei({ v: 1, iv: "AAAA", daten: "BBBB" });
  assert.match(datei, /^\/\/ Kaufbegutachtung/);
  assert.ok(datei.includes('export const PAKET = {\n  "v": 1,\n  "iv": "AAAA",\n  "daten": "BBBB"\n};\n'));
  assert.ok(!datei.includes("\r"));
  const md = linksDatei({ schluessel: TESTSCHLUESSEL, datenPfad: "D:/q/inhalte.json", schluesselPfad: "D:/p/s.txt", linksPfad: "D:/p/l.md" });
  for (const teil of [`#k=${TESTSCHLUESSEL}&o=wohnung&l=de`, `#k=${TESTSCHLUESSEL}&o=haus&l=de`, `#k=${TESTSCHLUESSEL}&o=wohnung&l=en`,
    `#k=${TESTSCHLUESSEL}&o=haus&l=en`, "funktionieren erst", "--schluessel-erzeugen", "--ueberschreiben", "alle alten Links"]) {
    assert.ok(md.includes(teil), teil);
  }
});

test("Werkzeug von Anfang bis Ende: Schlüssel anlegen, verschlüsseln, Seite entschlüsselt", async () => {
  const ordner = mkdtempSync(join(tmpdir(), "angebot-test-"));
  const ausgaben = [];
  const original = console.log;
  console.log = (...teile) => ausgaben.push(teile.join(" "));
  try {
    const schluesselPfad = join(ordner, "privat", "schluessel.txt");
    const datenPfad = join(ordner, "inhalte.json");
    const ausgabe = join(ordner, "paket.js");
    const linksPfad = join(ordner, "privat", "Private_Links.md");
    writeFileSync(datenPfad, JSON.stringify(BEISPIEL));
    await main(["--schluessel-erzeugen", schluesselPfad]);
    await assert.rejects(() => main(["--schluessel-erzeugen", schluesselPfad]), /--ueberschreiben/);
    await main(["--daten", datenPfad, "--schluessel", schluesselPfad, "--ausgabe", ausgabe, "--links", linksPfad]);
    const schluessel = readFileSync(schluesselPfad, "utf8").trim();
    const { PAKET: neu } = await import(pathToFileURL(ausgabe).href);
    assert.deepEqual(await entschluesseln(neu, schluessel), DATEN);
    assert.ok(readFileSync(linksPfad, "utf8").includes(`#k=${schluessel}&o=haus&l=en`));
    for (const zeile of ausgaben) assert.ok(!zeile.includes(schluessel), "Schlüssel nie in der Ausgabe");
    assert.ok(!readFileSync(ausgabe, "utf8").includes(schluessel), "Schlüssel nie in paket.js");
  } finally {
    console.log = original;
    rmSync(ordner, { recursive: true, force: true });
  }
});
