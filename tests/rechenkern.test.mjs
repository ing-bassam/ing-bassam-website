// Tests des Rechenkerns: node --test tests/
// Pflichtfall ist der Referenzfall A, der mit einer professionellen
// Bewertungssoftware gegengerechnet wurde. Jede Zahl muss exakt stimmen.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  runde, rundeAuf, alterswertminderungsfaktor, barwertfaktor, bodenwert, bewirtschaftungsbetrag, sachwert, ertragswert,
} from '../wertrechner/rechenkern.js';

const BOG = [
  { bezeichnung: 'Abschlag Bauschaden', betrag: -2500 },
  { bezeichnung: 'Abschlag Baulast', betrag: -5100 },
  { bezeichnung: 'Bodenwert zusätzlicher Flächen', betrag: 20000 },
];

test('Runden: kaufmännisch, ohne Gleitkommafehler', () => {
  assert.equal(runde(1.005, 2), 1.01);
  assert.equal(runde(252923.2634, 2), 252923.26);
  assert.equal(runde(-0.0625, 3), -0.063);
  assert.equal(rundeAuf(691976.72, 1000), 692000);
  assert.equal(rundeAuf(686826.08, 1000), 687000);
  assert.equal(rundeAuf(500, 1000), 1000);
});

test('Alterswertminderungsfaktor nach § 38 ImmoWertV', () => {
  assert.equal(alterswertminderungsfaktor(54, 80), 0.675);
  assert.equal(alterswertminderungsfaktor(44, 70), 0.6286);
  assert.equal(alterswertminderungsfaktor(0, 80), 0);
  assert.equal(alterswertminderungsfaktor(90, 80), 1);
  assert.throws(() => alterswertminderungsfaktor(-1, 80));
  assert.throws(() => alterswertminderungsfaktor(10, 0));
});

test('Barwertfaktor nach § 34 Abs. 2 ImmoWertV', () => {
  assert.equal(barwertfaktor(5.5, 46.356), 16.6622);
  assert.equal(barwertfaktor(0, 25), 25);
  assert.equal(barwertfaktor(5, 0), 0);
  assert.throws(() => barwertfaktor(-1, 10));
});

test('Bodenwert und Bewirtschaftungsbetrag', () => {
  assert.equal(bodenwert({ flaeche: 500, bodenrichtwert: 300 }), 150000);
  // Beispiel GFZ-W S. 3: 700 €/m² (GFZ 2,5) → GFZ 3,0 = 700 / 1,2003 × 1,3756 ≈ 802 €/m²
  assert.equal(bodenwert({ flaeche: 1000, bodenrichtwert: 700, faktor: 1.3756 / 1.2003 }), 802232.78);
  assert.equal(bewirtschaftungsbetrag({ jeM2: 14 }, { flaeche: 150 }), 2100);
  assert.equal(bewirtschaftungsbetrag({ prozent: 3 }, { rohertragJahr: 39900 }), 1197);
  assert.equal(bewirtschaftungsbetrag({ jeEinheit: 359, prozent: 1 }, { einheiten: 1, rohertragJahr: 100 }), 360);
  assert.equal(bewirtschaftungsbetrag(undefined, {}), 0);
});

test('Referenzfall A – Sachwertverfahren, zwei Gebäude', () => {
  const e = sachwert({
    gebaeude: [
      { bezeichnung: 'Wohnhaus', bgf: 260, nhk: 878, zuschlag2010: 4100, baupreisindex: 189.7, regionalfaktor: 0.85, gnd: 80, rnd: 54 },
      { bezeichnung: 'Geschäftshaus', bgf: 500, nhk: 720, zuschlag2010: 2500, baupreisindex: 193.6, regionalfaktor: 0.85, gnd: 70, rnd: 44 },
    ],
    aussenanlagen: 21600,
    bodenwert: 150000,
    sachwertfaktor: 0.85,
    bog: BOG,
  });
  assert.equal(e.gebaeude[0].herstellungskosten2010, 232380);
  assert.equal(e.gebaeude[1].herstellungskosten2010, 362500);
  assert.equal(e.gebaeude[0].alterswertminderungsfaktor, 0.675);
  assert.equal(e.gebaeude[1].alterswertminderungsfaktor, 0.6286);
  assert.equal(e.gebaeude[0].wert, 252923.26);
  assert.equal(e.gebaeude[1].wert, 374978.76);
  assert.equal(e.vorlaeufigerSachwert, 799502.02);
  assert.equal(e.marktangepasst, 679576.72);
  assert.equal(e.bogSumme, 12400);
  assert.equal(e.sachwert, 691976.72);
  assert.equal(e.sachwertGerundet, 692000);
  assert.ok(e.schritte.length > 10);
  assert.ok(e.schritte.every((s) => s.grundlage && s.bezeichnung && typeof s.wert === 'number'));
  assert.equal(e.hinweise.length, 0);
});

test('Referenzfall A – allgemeines Ertragswertverfahren', () => {
  const w = ertragswert({
    nutzungen: [
      { art: 'wohnen', bezeichnung: 'Wohnen', flaeche: 150, einheiten: 1, mieteMonat: 975, gebaeudeteil: 'G1',
        bewirtschaftung: { verwaltung: { jeEinheit: 359 }, instandhaltung: { jeM2: 14 }, betriebskosten: { jeM2: 2.5 }, mietausfallwagnis: { prozent: 2 } } },
      { art: 'gewerbe', bezeichnung: 'Verbrauchermarkt', flaeche: 350, mieteMonat: 3325, gebaeudeteil: 'G2',
        bewirtschaftung: { verwaltung: { prozent: 3 }, instandhaltung: { jeM2: 7 }, betriebskosten: { prozent: 10 }, mietausfallwagnis: { prozent: 4 } } },
      { art: 'sonstiges', bezeichnung: 'Sonstiges', einheiten: 1, mieteMonat: 50, gebaeudeteil: 'G1',
        bewirtschaftung: { verwaltung: { jeEinheit: 47 }, instandhaltung: { jeEinheit: 106 }, betriebskosten: { jeEinheit: 10 }, mietausfallwagnis: { prozent: 2 } } },
    ],
    gebaeudeteile: [{ id: 'G1', bezeichnung: 'Wohnhaus', rnd: 54 }, { id: 'G2', bezeichnung: 'Geschäftshaus', rnd: 44 }],
    liegenschaftszins: 5.5,
    bodenwert: 150000,
    marktanpassungsfaktor: 1.0,
    bog: BOG,
  });
  assert.equal(w.status, 'ok');
  assert.equal(w.rohertrag, 52200);
  assert.equal(w.bewirtschaftung.verwaltung, 1603);
  assert.equal(w.bewirtschaftung.instandhaltung, 4656);
  assert.equal(w.bewirtschaftung.betriebskosten, 4375);
  assert.equal(w.bewirtschaftung.mietausfallwagnis, 1842);
  assert.equal(w.bewirtschaftungskosten, 12476);
  assert.equal(w.reinertrag, 39724);
  assert.equal(w.bodenwertverzinsung, 8250);
  assert.equal(w.gebaeudereinertrag, 31474);
  assert.equal(w.rnd, 46.356);
  assert.equal(w.barwertfaktor, 16.6622);
  assert.equal(w.gebaeudeertragswert, 524426.08);
  assert.equal(w.vorlaeufigerErtragswert, 674426.08);
  assert.equal(w.ertragswert, 686826.08);
  assert.equal(w.ertragswertGerundet, 687000);
});

test('Randfall: Restnutzungsdauer 0 – Gebäude ohne Sachwert, Hinweis', () => {
  const e = sachwert({
    gebaeude: [{ bgf: 200, nhk: 1000, baupreisindex: 184.7, regionalfaktor: 1, gnd: 80, rnd: 0 }],
    bodenwert: { flaeche: 600, bodenrichtwert: 800 },
    sachwertfaktor: 1.0,
  });
  assert.equal(e.gebaeude[0].wert, 0);
  assert.equal(e.vorlaeufigerSachwert, 480000);
  assert.equal(e.hinweise.length, 1);
});

test('Randfall: sehr hoher Bodenwert – Liquidationsfall statt negativem Wert', () => {
  const w = ertragswert({
    nutzungen: [{ art: 'wohnen', flaeche: 400, einheiten: 6, mieteMonat: 2400,
      bewirtschaftung: { verwaltung: { jeEinheit: 351 }, instandhaltung: { jeM2: 13.8 }, mietausfallwagnis: { prozent: 2 } } }],
    rnd: 40,
    liegenschaftszins: 3.0,
    bodenwert: { flaeche: 1000, bodenrichtwert: 3000 },
  });
  assert.equal(w.status, 'liquidation');
  assert.equal(w.ertragswert, null);
  assert.ok(w.gebaeudereinertrag < 0);
  assert.equal(w.hinweise.length, 1);
});

test('Randfall: fehlende oder ungültige Eingaben werden abgewiesen', () => {
  assert.throws(() => sachwert({}), /mindestens ein Gebäude/);
  assert.throws(() => sachwert({ gebaeude: [{ bgf: 100, nhk: 900, baupreisindex: 184.7, gnd: 80 }], bodenwert: 1, sachwertfaktor: 1 }), /Restnutzungsdauer/);
  assert.throws(() => sachwert({ gebaeude: [{ bgf: 100, nhk: 900, baupreisindex: 184.7, gnd: 80, rnd: 40 }], bodenwert: 1 }), /Sachwertfaktor/);
  assert.throws(() => ertragswert({ nutzungen: [] }), /mindestens eine Nutzung/);
  assert.throws(() => ertragswert({ nutzungen: [{ mieteMonat: 100 }], rnd: 40, bodenwert: 1 }), /Liegenschaftszinssatz/);
  assert.throws(() => ertragswert({ nutzungen: [{ mieteMonat: 100, gebaeudeteil: 'X' }], gebaeudeteile: [{ id: 'Y', rnd: 40 }], liegenschaftszins: 4, bodenwert: 1 }),
    /keinem Gebäudeteil/);
});

test('Liegenschaftszins 0 % – Barwertfaktor gleich Restnutzungsdauer', () => {
  const w = ertragswert({
    nutzungen: [{ art: 'wohnen', flaeche: 100, einheiten: 1, mieteMonat: 1000, bewirtschaftung: {} }],
    rnd: 30, liegenschaftszins: 0, bodenwert: 100000,
  });
  assert.equal(w.barwertfaktor, 30);
  assert.equal(w.gebaeudeertragswert, 360000);
});
