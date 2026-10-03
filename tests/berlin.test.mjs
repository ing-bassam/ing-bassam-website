// Tests der Berliner Modellschicht gegen die veröffentlichten Tabellen des
// Gutachterausschusses (fachliteratur/MODELL-BERLIN.md). node --test tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { modell, berlinSachwert, berlinErtragswert } from '../wertrechner/berlin.js';

const daten = JSON.parse(readFileSync(new URL('../wertrechner/data/marktdaten.json', import.meta.url), 'utf8'));
const m = modell(daten);
const JAHR = 2026;

const ZONE_W = { modell: { brw: 600, nutzung: 'W', gfz: 0.4 }, aktuell: { brw: 540, nutzung: 'W', gfz: 0.4 } };
const ADRESSE_JOHANNISTHAL = { zone: ZONE_W, wohnlage: 2, ortsteil: 'Johannisthal' };

const EFH = {
  gebaeudestellung: 'freistehend', unterkellert: true, geschosse: 1, dachgeschoss: 'voll_ausgebaut',
  baujahr: 1965, bauzustand: 'normal', konstruktion: 'massiv', bgf: 220, grundstuecksflaeche: 600,
};

test('Ortsteile: Altbezirk, Gebietsgruppe, Stadtlage, Sachwertfaktor-Gruppe (LZ 2025 Tabelle 1)', () => {
  const j = m.ortsteil('Johannisthal');
  assert.equal(j.Altbezirk, 'Treptow');
  assert.equal(j.Gebietsgruppe, 'Südost');
  assert.equal(j.Stadtlage, 'Ost');
  assert.equal(j.SWF_Gruppe, 1);
  assert.equal(m.ortsteil('Mitte').SWF_Gruppe, null);
  assert.equal(m.ortsteil('Frohnau').Gebietsgruppe, 'Nord');
  assert.equal(m.ortsteil('Westend').Gebietsgruppe, 'Südwest');
  assert.equal(m.ortsteil('Gropiusstadt').Stadtlage, 'West');
  assert.equal(m.ortsteil('Nirgendwo'), null);
  assert.equal(daten.blaetter.Ortsteile.length, 97);
});

test('NHK 2010: Typauswahl nach Berliner Regeln (Stufe 4)', () => {
  const t1 = m.nhkTyp({ gebaeudestellung: 'freistehend', unterkellert: true, geschosse: 1, dachgeschoss: 'voll_ausgebaut' });
  assert.equal(t1.Typ, '1.01');
  assert.equal(m.nhkWert(t1), 1005);
  const t2 = m.nhkTyp({ gebaeudestellung: 'reihenmittelhaus', unterkellert: false, geschosse: 2, dachgeschoss: 'flachdach' });
  assert.equal(t2.Typ, '3.33');
  assert.equal(m.nhkWert(t2), 1060);
  // 3-geschossig wie 2-geschossig; Doppelhaushälfte und Reihenendhaus teilen sich die Spalte
  assert.equal(m.nhkTyp({ gebaeudestellung: 'doppelhaushaelfte', unterkellert: true, geschosse: 3, dachgeschoss: 'nicht_ausgebaut' }).Typ, '2.12');
  assert.equal(m.nhkTyp({ gebaeudestellung: 'reihenendhaus', unterkellert: true, geschosse: 2, dachgeschoss: 'nicht_ausgebaut' }).Typ, '2.12');
  assert.equal(daten.blaetter.NHK2010.length, 36);
});

test('Restnutzungsdauer nach den Berliner Tabellen', () => {
  assert.equal(m.restnutzungsdauer('sachwert', { baujahr: 1935, alter: 91, bauzustand: 'gut' }).rnd, 55);
  assert.equal(m.restnutzungsdauer('sachwert', { baujahr: 1990, alter: 36, bauzustand: 'normal' }).rnd, 40);
  assert.equal(m.restnutzungsdauer('sachwert', { baujahr: 2024, alter: 2, bauzustand: 'schlecht' }).rnd, 70);
  assert.equal(m.restnutzungsdauer('sachwert', { baujahr: 1965, alter: 61, bauzustand: 'normal' }).rnd, 40);
  // Ertragswert: Leerstellen der Tabelle 5 und Ausstattungsabschläge der Tabellen 3/4
  assert.equal(m.restnutzungsdauer('ertragswert', { baujahr: 2024, alter: 2, bauzustand: 'normal' }).rnd, null);
  assert.equal(m.restnutzungsdauer('ertragswert', { baujahr: 1900, alter: 126, bauzustand: 'normal', ausstattung: { zentralheizung: false, baeder: false } }).rnd, 30);
  assert.equal(m.restnutzungsdauer('ertragswert', { baujahr: 1900, alter: 126, bauzustand: 'normal', ausstattung: { zentralheizung: true, baeder: false } }).rnd, 35);
  assert.equal(m.restnutzungsdauer('ertragswert', { baujahr: 1900, alter: 126, bauzustand: 'gut', ausstattung: { zentralheizung: true, baeder: true } }).rnd, 55);
  assert.equal(m.restnutzungsdauer('ertragswert', { baujahr: 1930, alter: 96, bauzustand: 'gut', ausstattung: { zentralheizung: false, baeder: true } }).rnd, 50);
  assert.equal(m.restnutzungsdauer('ertragswert', { baujahr: 1975, alter: 51, bauzustand: 'schlecht' }).rnd, 25);
});

test('Sachwertfaktor reproduziert die Tabellen 4–6 (SWF 2025 S. 8–9)', () => {
  const basis = { baujahr: 1980, gebaeudeart: 'freistehend', bauzustand: 'normal', konstruktion: 'massiv', wohnlage: 'mittel' };
  assert.equal(m.sachwertfaktor({ ...basis, vorlaeufigerSachwert: 300000, swfGruppe: 1 }).gerundet, 1.01);
  assert.equal(m.sachwertfaktor({ ...basis, vorlaeufigerSachwert: 1100000, swfGruppe: 1 }).gerundet, 0.79);
  assert.equal(m.sachwertfaktor({ ...basis, vorlaeufigerSachwert: 500000, swfGruppe: 2 }).gerundet, 0.89);
  assert.equal(m.sachwertfaktor({ ...basis, vorlaeufigerSachwert: 700000, swfGruppe: 3 }).gerundet, 0.79);
  // Korrekturen: Reihenmittelhaus +0,341, guter Zustand +0,179, Baujahr 1949–1970 −0,123, Holz-Fertighaus −0,072
  const k = m.sachwertfaktor({ vorlaeufigerSachwert: 500000, swfGruppe: 1, baujahr: 1960, gebaeudeart: 'reihenmittelhaus', bauzustand: 'gut', konstruktion: 'fertighaus_holz', wohnlage: 'gut' });
  assert.equal(k.gerundet, Math.round((1.398 - 0.14 - 0.30239 + 0.341 + 0.179 - 0.123 - 0.072 + 0.075) * 100) / 100);
  assert.equal(m.sachwertfaktor({ ...basis, vorlaeufigerSachwert: 500000, swfGruppe: 1, wohnlage: 'sehr_gut' }).gerundet,
    m.sachwertfaktor({ ...basis, vorlaeufigerSachwert: 500000, swfGruppe: 1, wohnlage: 'gut' }).gerundet);
});

test('Liegenschaftszinssatz reproduziert die Tabellen 6–11 (LZ 2025 S. 12–15)', () => {
  const basis = { altbezirk: 'Treptow', baujahr: 1905, stadtlage: 'Ost', gewerbeanteilProzent: 0 };
  assert.equal(m.liegenschaftszins({ ...basis, objektmiete: 6, gebietsgruppe: 'Südost' }).gerundet, 2.9);
  assert.equal(m.liegenschaftszins({ ...basis, objektmiete: 12, gebietsgruppe: 'Südost' }).gerundet, 3.7);
  assert.equal(m.liegenschaftszins({ ...basis, objektmiete: 12, gebietsgruppe: 'City', altbezirk: 'Neukölln' }).gerundet, 3.9);
  assert.equal(m.liegenschaftszins({ ...basis, objektmiete: 8, gebietsgruppe: 'Nord', altbezirk: 'Reinickendorf' }).gerundet, 3.4);
  assert.equal(m.liegenschaftszins({ ...basis, objektmiete: 10, gebietsgruppe: 'City', altbezirk: 'Mitte' }).gerundet, 3.0);
  assert.equal(m.liegenschaftszins({ ...basis, objektmiete: 7, gebietsgruppe: 'West', altbezirk: 'Spandau', baujahr: 1980, stadtlage: 'West' }).gerundet, 3.5);
  const mitGewerbe = m.liegenschaftszins({ ...basis, objektmiete: 7, gebietsgruppe: 'Südost', gewerbeanteilProzent: 20 });
  const ohneGewerbe = m.liegenschaftszins({ ...basis, objektmiete: 7, gebietsgruppe: 'Südost' });
  assert.equal(Math.round((mitGewerbe.ungerundet - ohneGewerbe.ungerundet) * 1000) / 1000, 0.16);
});

test('GFZ-Umrechnungskoeffizienten und Bodenwertanpassung', () => {
  assert.equal(m.gfzKoeffizient('wohn04', 2.5), 1.2003);
  assert.equal(m.gfzKoeffizient('wohn04', 3.0), 1.3756);
  assert.equal(m.gfzKoeffizient('wohn04', 2.55), 1.2188);
  assert.equal(m.gfzKoeffizient('wohn04', 0.5), null);
  assert.equal(m.gfzKoeffizient('dienst04', 4.0), 1.0);
  assert.equal(m.gfzKoeffizient('dienst04', 7.0), 1.614);
  // Beispiel GFZ-W S. 3: 700 €/m² bei GFZ 2,5 → GFZ 3,0 ≈ 802 €/m²
  const a = m.gfzAnpassung({ nutzungZone: 'W', gfzZone: 2.5, gfzTatsaechlich: 3.0 });
  assert.equal(Math.round(700 * a.faktor), 802);
  assert.equal(m.gfzAnpassung({ nutzungZone: 'W', gfzZone: 0.4, gfzTatsaechlich: 0.6 }).faktor, 1);
  assert.ok(m.gfzAnpassung({ nutzungZone: 'W', gfzZone: 0.4, gfzTatsaechlich: 0.6 }).hinweis);
  assert.equal(m.gfzAnpassung({ nutzungZone: 'W', gfzZone: 2.5, gfzTatsaechlich: 2.5 }).faktor, 1);
  // Beispiel GFZ-D S. 3: 2.000 €/m² bei GFZ 2,5 → GFZ 3,0 ≈ 2.295 €/m² (reine Büronutzung)
  const d = m.gfzAnpassung({ nutzungZone: 'M1', gfzZone: 2.5, gfzTatsaechlich: 3.0, gewerbeflaechenanteil: 1 });
  assert.equal(Math.round(2000 * d.faktor), 2295);
});

test('Berliner Bewirtschaftungskosten als Ansätze', () => {
  assert.deepEqual(m.bewirtschaftung('wohnen'), { verwaltung: { jeEinheit: 351 }, instandhaltung: { jeM2: 13.8 }, mietausfallwagnis: { prozent: 2 } });
  assert.deepEqual(m.bewirtschaftung('gewerbe', 'buero_laden'), { verwaltung: { prozent: 3 }, instandhaltung: { jeM2: 13.8 }, mietausfallwagnis: { prozent: 4 } });
  assert.deepEqual(m.bewirtschaftung('gewerbe', 'nebennutzung').instandhaltung, { jeM2: 4.14 });
  assert.deepEqual(m.bewirtschaftung('sonstiges', 'garage').instandhaltung, { jeEinheit: 104 });
  assert.deepEqual(m.bewirtschaftung('sonstiges', 'stellplatz').instandhaltung, { jeEinheit: 52 });
});

test('Sachwert Berlin: Einfamilienhaus in Johannisthal, von Hand nachgerechnet', () => {
  const e = berlinSachwert(EFH, ADRESSE_JOHANNISTHAL, m, { jahr: JAHR });
  assert.equal(e.status, 'ok', JSON.stringify(e.gruende));
  // 220 m² × 1.005 €/m² = 221.100 € × 1,847 = 408.371,70 €; Alter 61 → RND 40 → 0,5 → 204.185,85 €
  assert.equal(e.ergebnis.gebaeude[0].herstellungskosten2010, 221100);
  assert.equal(e.ergebnis.gebaeude[0].herstellungskosten, 408371.7);
  assert.equal(e.modell.rnd.rnd, 40);
  assert.equal(e.ergebnis.gebaeude[0].wert, 204185.85);
  assert.equal(e.ergebnis.bodenwert, 360000);
  assert.equal(e.ergebnis.vorlaeufigerSachwert, 564185.85);
  // SWF = 1,398 − 0,00000028 × 564.185,85 − 0,30239 − 0,123 (Baujahr 1949–1970) = 0,8146 → 0,81
  assert.equal(e.modell.sachwertfaktor.gerundet, 0.81);
  assert.equal(e.ergebnis.marktangepasst, 456990.54);
  assert.equal(e.wert, 457000);
  assert.ok(e.spanne.von < e.wert && e.wert < e.spanne.bis);
  assert.equal(e.spanne.prozent, 15);
  assert.ok(e.pruefungen.every((p) => p.ok));
  assert.equal(e.modell.nhkTyp, '1.01');
  assert.equal(e.modell.bodenrichtwertAktuell, 540);
  assert.equal(e.modell.wohnlage, 'mittel');
});

test('Sachwert Berlin: BGF aus Grundfläche oder Wohnfläche, Schätzung gekennzeichnet', () => {
  const aus = berlinSachwert({ ...EFH, bgf: undefined, grundflaeche: 80 }, ADRESSE_JOHANNISTHAL, m, { jahr: JAHR });
  assert.equal(aus.status, 'ok');
  assert.equal(aus.modell.bgf, 224);                // 80 × (1 + 1 + 0,8)
  assert.equal(aus.modell.bgfGeschaetzt.art, 'grundflaeche');
  const wf = berlinSachwert({ ...EFH, bgf: undefined, wohnflaeche: 120 }, ADRESSE_JOHANNISTHAL, m, { jahr: JAHR });
  assert.equal(wf.status, 'ok');
  assert.equal(wf.modell.bgfGeschaetzt.art, 'wohnflaeche');
  assert.equal(wf.modell.bgfGeschaetzt.faktor, 2.07); // 2,8 / (0,8 + 0,55)
  assert.ok(wf.hinweise.some((h) => h.includes('geschätzt')));
  const nichts = berlinSachwert({ ...EFH, bgf: undefined }, ADRESSE_JOHANNISTHAL, m, { jahr: JAHR });
  assert.equal(nichts.status, 'nicht_anwendbar');
});

test('Sachwert Berlin: nicht anwendbar ohne Sachwertfaktoren, ohne Wohnbauland, außerhalb des Gültigkeitsbereichs', () => {
  const mitte = berlinSachwert(EFH, { ...ADRESSE_JOHANNISTHAL, ortsteil: 'Mitte' }, m, { jahr: JAHR });
  assert.equal(mitte.status, 'nicht_anwendbar');
  assert.ok(mitte.gruende[0].includes('keine Sachwertfaktoren'));
  const gewerbe = berlinSachwert(EFH, { ...ADRESSE_JOHANNISTHAL, zone: { modell: { brw: 300, nutzung: 'G', gfz: null } } }, m, { jahr: JAHR });
  assert.equal(gewerbe.status, 'nicht_anwendbar');
  // 3.000 m² Grundstück: Grundstücksfläche und (wegen des Bodenwerts) vorläufiger Sachwert liegen außerhalb
  const gross = berlinSachwert({ ...EFH, grundstuecksflaeche: 3000 }, ADRESSE_JOHANNISTHAL, m, { jahr: JAHR });
  assert.equal(gross.status, 'ausserhalb');
  assert.ok(gross.gruende.some((g) => g.includes('Grundstücksfläche')));
  assert.ok(gross.gruende.some((g) => g.includes('vorläufiger Sachwert')));
  const teuer = berlinSachwert({ ...EFH, bgf: 420, grundstuecksflaeche: 900 }, { ...ADRESSE_JOHANNISTHAL, zone: { modell: { brw: 1200, nutzung: 'W', gfz: 0.4 } } }, m, { jahr: JAHR });
  assert.equal(teuer.status, 'ausserhalb');
  assert.equal(teuer.gruende.length, 1);
  assert.ok(teuer.gruende[0].includes('vorläufiger Sachwert'));
});

test('Ertragswert Berlin: Altbau-Mietshaus in Neukölln', () => {
  const objekt = {
    baujahr: 1905, bauzustand: 'normal', ausstattung: { zentralheizung: true, baeder: true },
    wohnen: { flaeche: 1200, einheiten: 16, mieteMonat: 9000 },
    gewerbe: { flaeche: 200, mieteMonat: 2400, art: 'buero_laden' },
    sonstiges: { garagen: 0, stellplaetze: 4, mieteMonat: 200 },
    grundstuecksflaeche: 800, geschossflaeche: 1750,
  };
  const adresse = { zone: { modell: { brw: 2000, nutzung: 'W', gfz: 2.5 }, aktuell: { brw: 2000, nutzung: 'W', gfz: 2.5 } }, wohnlage: 1, ortsteil: 'Neukölln' };
  const w = berlinErtragswert(objekt, adresse, m, { jahr: JAHR });
  assert.equal(w.status, 'ok', JSON.stringify(w.gruende));
  assert.equal(w.modell.gebietsgruppe, 'City');
  assert.equal(w.modell.objektmiete, 8.29);            // 11.600 € / 1.400 m²
  assert.equal(w.modell.gewerbeanteilProzent, 20.69);  // 28.800 / 139.200
  assert.equal(w.modell.rnd.rnd, 40);
  // LZ = 0,644 + 0,132 × 8,29 + 1,45812 + 0,167 + 0,008 × 20,69 = 3,529 → 3,5
  assert.equal(w.modell.liegenschaftszins.gerundet, 3.5);
  assert.equal(w.ergebnis.rohertrag, 139200);
  assert.equal(w.ergebnis.bewirtschaftung.verwaltung, 16 * 351 + 0.03 * 28800 + 0.03 * 2400);
  assert.equal(w.ergebnis.bewirtschaftung.instandhaltung, 1200 * 13.8 + 200 * 13.8 + 4 * 52);
  assert.equal(w.ergebnis.bewirtschaftung.mietausfallwagnis, 0.02 * 108000 + 0.04 * 28800 + 0.04 * 2400);
  assert.equal(w.ergebnis.bewirtschaftung.betriebskosten, 0);
  assert.ok(w.modell.gfzAnpassung.faktor < 1 && w.modell.gfzAnpassung.faktor > 0.85);
  assert.equal(w.ergebnis.liegenschaftszins, 3.5);
  assert.equal(w.wert % 1000, 0);
  assert.ok(w.spanne.von < w.wert && w.wert < w.spanne.bis);
  assert.ok(w.pruefungen.every((p) => p.ok), JSON.stringify(w.pruefungen.filter((p) => !p.ok)));
});

test('Ertragswert Berlin: Ausschlussgründe', () => {
  const adresse = { zone: { modell: { brw: 2000, nutzung: 'W', gfz: 2.5 } }, wohnlage: 2, ortsteil: 'Neukölln' };
  const basis = { baujahr: 1905, bauzustand: 'normal', wohnen: { flaeche: 1200, einheiten: 16, mieteMonat: 9000 }, grundstuecksflaeche: 800, geschossflaeche: 1750 };
  assert.equal(berlinErtragswert({ ...basis, wohnen: { flaeche: 300, einheiten: 3, mieteMonat: 2500 } }, adresse, m, { jahr: JAHR }).status, 'nicht_anwendbar');
  assert.equal(berlinErtragswert({ ...basis, gewerbe: { flaeche: 2000, mieteMonat: 50000, art: 'buero_laden' } }, adresse, m, { jahr: JAHR }).status, 'nicht_anwendbar');
  assert.equal(berlinErtragswert({ ...basis, baujahr: 2015 }, adresse, m, { jahr: JAHR }).status, 'ausserhalb');  // Alter 11 < 30
  assert.equal(berlinErtragswert({ ...basis, wohnen: { flaeche: 1200, einheiten: 16, mieteMonat: 3600 } }, adresse, m, { jahr: JAHR }).status, 'ausserhalb'); // 3,00 €/m²
  const liq = berlinErtragswert({ ...basis, wohnen: { flaeche: 1200, einheiten: 16, mieteMonat: 5000 } }, { ...adresse, zone: { modell: { brw: 6000, nutzung: 'W', gfz: 2.2 } } }, m, { jahr: JAHR });
  assert.ok(['liquidation', 'ausserhalb'].includes(liq.status));
});
