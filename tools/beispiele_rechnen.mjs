#!/usr/bin/env node
/*
 * Rechnet Berliner Beispielobjekte mit dem Rechenkern durch und schreibt die
 * Rechenwege als Markdown-Tabellen nach fachliteratur/BEISPIELE-PHASE-4.md.
 * Zweck: Abgleich mit einer professionellen Bewertungssoftware (Phase 4).
 *
 *     node tools/beispiele_rechnen.mjs
 *
 * Die Adressen stammen aus wertrechner/data/adressen/<PLZ>.json, damit der
 * Bodenrichtwert dem entspricht, was der Rechner auf der Website verwendet.
 * Das Stichtagsjahr ist fest 2026, damit die Datei reproduzierbar bleibt.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { modell, berlinSachwert, berlinErtragswert } from '../wertrechner/berlin.js';

const WURZEL = new URL('../', import.meta.url);
const JAHR = 2026;
const daten = JSON.parse(readFileSync(new URL('wertrechner/data/marktdaten.json', WURZEL), 'utf8'));
const m = modell(daten);

const geld = (n) => new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(n);
const zahl = (n, st = 4) => new Intl.NumberFormat('de-DE', { maximumFractionDigits: st }).format(n);

function adresse(plz, strasse, hnr) {
  const datei = JSON.parse(readFileSync(new URL(`wertrechner/data/adressen/${plz}.json`, WURZEL), 'utf8'));
  const idx = datei.strassen.indexOf(strasse);
  const e = datei.adressen.find((x) => x[0] === idx && x[1] === hnr);
  if (!e) throw new Error(`Adresse nicht gefunden: ${strasse} ${hnr}, ${plz}`);
  return {
    text: `${strasse} ${hnr}, ${plz} Berlin (${datei.ortsteile[e[5]]})`,
    zone: { modell: datei.zonen[e[2]]?.modell || null, aktuell: datei.zonen[e[3]]?.aktuell || null },
    wohnlage: e[4], ortsteil: datei.ortsteile[e[5]],
  };
}

const BEISPIELE = [
  {
    titel: 'Beispiel 1 – freistehendes Einfamilienhaus, Johannisthal (Sachwertverfahren)',
    verfahren: 'sachwert',
    adresse: adresse('12487', 'Akeleiweg', '1'),
    objekt: { gebaeudestellung: 'freistehend', unterkellert: true, geschosse: 1, dachgeschoss: 'voll_ausgebaut', baujahr: 1965, bauzustand: 'normal', konstruktion: 'massiv', bgf: 220, grundstuecksflaeche: 600, nebenanlagen: 0 },
    eingaben: ['freistehend, unterkellert, 1 Vollgeschoss, Dachgeschoss ausgebaut (NHK-Typ 1.01)', 'Baujahr 1965, baulicher Zustand normal, Massivbau', 'Brutto-Grundfläche 220 m² (angegeben)', 'Grundstück 600 m²', 'keine besonderen Nebenanlagen'],
  },
  {
    titel: 'Beispiel 2 – Reihenmittelhaus, Mahlsdorf (Sachwertverfahren)',
    verfahren: 'sachwert',
    adresse: adresse('12623', 'Akazienallee', '1'),
    objekt: { gebaeudestellung: 'reihenmittelhaus', unterkellert: false, geschosse: 2, dachgeschoss: 'nicht_ausgebaut', baujahr: 1998, bauzustand: 'gut', konstruktion: 'massiv', grundflaeche: 65, grundstuecksflaeche: 300, nebenanlagen: 8000 },
    eingaben: ['Reihenmittelhaus, nicht unterkellert, 2 Vollgeschosse, Dachgeschoss nicht ausgebaut (NHK-Typ 3.32)', 'Baujahr 1998, baulicher Zustand gut, Massivbau', 'Grundfläche nach Außenmaßen 65 m² → BGF abgeleitet', 'Grundstück 300 m²', 'besondere Nebenanlagen (Carport) 8.000 € Zeitwert'],
  },
  {
    titel: 'Beispiel 3 – Altbau-Mietwohnhaus mit Laden, Neukölln (Ertragswertverfahren)',
    verfahren: 'ertragswert',
    adresse: adresse('12043', 'Anzengruberstraße', '1'),
    objekt: {
      baujahr: 1905, bauzustand: 'normal', ausstattung: { zentralheizung: true, baeder: true },
      wohnen: { flaeche: 1200, einheiten: 16, mieteMonat: 9000 },
      gewerbe: { flaeche: 200, mieteMonat: 2400, art: 'buero_laden' },
      sonstiges: { garagen: 0, stellplaetze: 4, mieteMonat: 200 },
      grundstuecksflaeche: 800, geschossflaeche: 1750,
    },
    eingaben: ['Baujahr 1905, baulicher Zustand normal, vollständig mit Zentralheizung und Bädern', 'Wohnen: 1.200 m², 16 Wohnungen, 9.000 €/Monat nettokalt (7,50 €/m²)', 'Gewerbe (Laden): 200 m², 2.400 €/Monat nettokalt (12,00 €/m²)', '4 offene Stellplätze, 200 €/Monat', 'Grundstück 800 m², Geschossfläche oberirdisch 1.750 m² (GFZ 2,19)'],
  },
  {
    titel: 'Beispiel 4 – Mietwohnhaus der 1960er, Köpenick (Ertragswertverfahren)',
    verfahren: 'ertragswert',
    adresse: adresse('12555', 'Alt-Köpenick', '1'),
    objekt: {
      baujahr: 1964, bauzustand: 'normal',
      wohnen: { flaeche: 800, einheiten: 12, mieteMonat: 5600 },
      sonstiges: { garagen: 0, stellplaetze: 6, mieteMonat: 240 },
      grundstuecksflaeche: 700, geschossflaeche: 1050,
    },
    eingaben: ['Baujahr 1964, baulicher Zustand normal', 'Wohnen: 800 m², 12 Wohnungen, 5.600 €/Monat nettokalt (7,00 €/m²)', '6 offene Stellplätze, 240 €/Monat', 'Grundstück 700 m², Geschossfläche oberirdisch 1.050 m² (GFZ 1,50)'],
  },
  {
    titel: 'Beispiel 5 – Altbau in Prenzlauer Berg bei 9 €/m²: Liquidationsfall (zur Demonstration)',
    verfahren: 'ertragswert',
    adresse: adresse('10405', 'Christburger Straße', '1'),
    objekt: {
      baujahr: 1905, bauzustand: 'normal', ausstattung: { zentralheizung: true, baeder: true },
      wohnen: { flaeche: 1200, einheiten: 16, mieteMonat: 10800 },
      gewerbe: { flaeche: 150, mieteMonat: 2100, art: 'buero_laden' },
      sonstiges: { garagen: 0, stellplaetze: 0, mieteMonat: 0 },
      grundstuecksflaeche: 900, geschossflaeche: 2100,
    },
    eingaben: ['Baujahr 1905, baulicher Zustand normal, vollständig mit Zentralheizung und Bädern', 'Wohnen: 1.200 m², 16 Wohnungen, 10.800 €/Monat nettokalt (9,00 €/m²)', 'Gewerbe (Laden): 150 m², 2.100 €/Monat nettokalt (14,00 €/m²)', 'Grundstück 900 m², Geschossfläche oberirdisch 2.100 m² (GFZ 2,33)', 'Bodenrichtwert 5.000 €/m²: Die Bodenwertverzinsung übersteigt den Reinertrag – der Rechner gibt bewusst keinen Wert aus, sondern den Hinweis auf eine Liquidationsbetrachtung.'],
  },
];

function tabelle(kopf, zeilen) {
  const esc = (s) => String(s ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
  return [`| ${kopf.join(' | ')} |`, `| ${kopf.map(() => '---').join(' | ')} |`, ...zeilen.map((z) => `| ${z.map(esc).join(' | ')} |`)].join('\n');
}

function parameterZeilen(e) {
  const mo = e.modell;
  if (e.verfahren === 'sachwert') {
    return [
      ['NHK-2010-Typ / Kostenkennwert Stufe 4', `${mo.nhkTyp} / ${zahl(mo.nhk, 0)} €/m²`],
      ['Brutto-Grundfläche', `${zahl(mo.bgf, 0)} m²${mo.bgfGeschaetzt ? ` (${mo.bgfGeschaetzt.art === 'grundflaeche' ? `aus Grundfläche ${zahl(mo.bgfGeschaetzt.grundflaeche, 0)} m² × ${zahl(mo.bgfGeschaetzt.ebenen, 2)} Ebenen` : `aus Wohnfläche × ${zahl(mo.bgfGeschaetzt.faktor, 2)}`})` : ' (angegeben)'}`],
      ['Baupreisindex (2010 = 100) / Regionalfaktor', `${zahl(mo.baupreisindex, 1)} / ${zahl(mo.regionalfaktor, 2)}`],
      ['Gesamtnutzungsdauer / Alter / Restnutzungsdauer', `${mo.gnd} / ${mo.alter} / ${mo.rnd.rnd} Jahre (${mo.rnd.quelle})`],
      ['Bodenrichtwert 01.01.2024 (Modell) / 01.01.2026 (aktuell)', `${zahl(mo.bodenrichtwert, 0)} / ${mo.bodenrichtwertAktuell != null ? zahl(mo.bodenrichtwertAktuell, 0) : '–'} €/m²`],
      ['Wohnlage / Altbezirk / SWF-Gruppe', `${mo.wohnlage} / ${mo.altbezirk} / ${mo.swfGruppe}`],
      ['Sachwertfaktor Formel → angewendet', `${zahl(mo.sachwertfaktor.ungerundet, 4)} → ${zahl(mo.sachwertfaktor.gerundet, 2)}`],
    ];
  }
  return [
    ['Ø Objektkaltmiete / gewerblicher Anteil', `${zahl(mo.objektmiete, 2)} €/m² / ${zahl(mo.gewerbeanteilProzent, 2)} %`],
    ['Gebietsgruppe / Stadtlage / Altbezirk', `${mo.gebietsgruppe} / ${mo.stadtlage} / ${mo.altbezirk}`],
    ['Liegenschaftszinssatz Formel → angewendet', `${zahl(mo.liegenschaftszins.ungerundet, 3)} % → ${zahl(mo.liegenschaftszins.gerundet, 1)} %`],
    ['Alter / Restnutzungsdauer', `${mo.alter} / ${mo.rnd.rnd} Jahre${mo.rnd.abschlag ? ` (Ausstattungsabschlag ${mo.rnd.abschlag})` : ''} (${mo.rnd.quelle})`],
    ['Bodenrichtwert 01.01.2024 (Modell) / 01.01.2026 (aktuell)', `${zahl(mo.bodenrichtwert, 0)} / ${mo.bodenrichtwertAktuell != null ? zahl(mo.bodenrichtwertAktuell, 0) : '–'} €/m²`],
    ['GFZ Richtwertzone / Grundstück → Anpassungsfaktor', `${mo.gfzZone != null ? zahl(mo.gfzZone, 2) : '–'} / ${mo.gfzTatsaechlich != null ? zahl(mo.gfzTatsaechlich, 2) : '–'} → ${zahl(mo.gfzAnpassung.faktor, 4)}${mo.gfzAnpassung.hinweis ? ' (' + mo.gfzAnpassung.hinweis + ')' : ''}`],
  ];
}

const teile = [
  '# Beispielobjekte für den Abgleich mit der Bewertungssoftware (Phase 4)',
  '',
  'Automatisch erzeugt von `tools/beispiele_rechnen.mjs` aus dem Rechenkern und den Marktdaten des Repositories. ' +
  `Stichtagsjahr für das Alter: ${JAHR}. Faktoren zum Stichtag ${daten.parameter.stichtag_faktoren}; Bodenrichtwert ${daten.parameter.brw_stichtag_modell}. ` +
  'Die Adressen sind echte Berliner Adressen aus den offenen Daten; die Gebäudeangaben sind angenommen.',
  '',
  'Zum Abgleich: Jede Zeile des Rechenwegs nennt Formel, Ergebnis und Rechtsgrundlage. Abweichungen zur Software deuten auf unterschiedliche Modellannahmen hin (siehe `MODELL-BERLIN.md`), nicht auf Rechenfehler – die Arithmetik ist über den Referenzfall A abgesichert.',
  '',
];

for (const b of BEISPIELE) {
  const e = b.verfahren === 'sachwert'
    ? berlinSachwert(b.objekt, b.adresse, m, { jahr: JAHR })
    : berlinErtragswert(b.objekt, b.adresse, m, { jahr: JAHR });
  teile.push(`## ${b.titel}`, '', `**Adresse:** ${b.adresse.text}`, '', '**Eingaben**', '', ...b.eingaben.map((x) => `- ${x}`), '');
  if (e.status !== 'ok') {
    teile.push(`**Ergebnis: kein Wert (${e.status})**`, '', ...(e.gruende || []).map((g) => `- ${g}`), '', ...(e.hinweise || []).map((h) => `- Hinweis: ${h}`), '');
    continue;
  }
  teile.push('**Modellparameter**', '', tabelle(['Parameter', 'Wert'], parameterZeilen(e)), '');
  teile.push('**Rechenweg**', '', tabelle(['#', 'Schritt', 'Rechnung', 'Ergebnis', 'Grundlage'],
    e.ergebnis.schritte.map((s) => [s.nr, s.bezeichnung, s.formel, s.einheit === '€' ? geld(s.wert) : s.einheit ? `${zahl(s.wert)} ${s.einheit}` : zahl(s.wert), s.grundlage])), '');
  const f = e.verfahren === 'sachwert' ? e.modell.sachwertfaktor : e.modell.liegenschaftszins;
  teile.push(`**Zusammensetzung ${e.verfahren === 'sachwert' ? 'Sachwertfaktor' : 'Liegenschaftszinssatz'}**`, '',
    tabelle(['Bestandteil', 'Wert'], [...f.bestandteile.map((x) => [x.text, zahl(x.wert, 6)]), ['Summe (ungerundet)', zahl(f.ungerundet, 6)], ['angewendet (gerundet)', zahl(f.gerundet, f.stellen)]]), '');
  teile.push('**Gültigkeitsprüfung**', '', tabelle(['Größe', 'Wert', 'Bereich', 'Ergebnis'],
    e.pruefungen.map((p) => [p.groesse, `${zahl(p.wert)} ${p.einheit}`, `${zahl(p.min)} – ${zahl(p.max)} ${p.einheit}`, p.ok ? 'innerhalb' : (p.sperrend ? 'AUSSERHALB (sperrend)' : 'außerhalb (Hinweis)')])), '');
  if (e.hinweise.length) teile.push('**Hinweise**', '', ...e.hinweise.map((h) => `- ${h}`), '');
  teile.push(`**Ergebnis: ${geld(e.wert).replace(',00', '')} – Spanne ${geld(e.spanne.von).replace(',00', '')} bis ${geld(e.spanne.bis).replace(',00', '')} (±${e.spanne.prozent} %)**`, '');
}

const ziel = new URL('fachliteratur/BEISPIELE-PHASE-4.md', WURZEL);
writeFileSync(ziel, teile.join('\n') + '\n', 'utf8');
console.log(`Geschrieben: fachliteratur/BEISPIELE-PHASE-4.md (${BEISPIELE.length} Beispiele)`);
