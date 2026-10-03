/*
 * Rechenkern des Wertrechners – reine Rechenlogik nach der ImmoWertV 2021.
 *
 * Keine Abhängigkeiten, keine Zufallselemente, keine KI: gleiche Eingabe heißt
 * immer gleiches Ergebnis. Läuft unverändert im Browser und in Node (Tests).
 *
 * Jede Funktion nennt den Paragrafen bzw. die Anlage der ImmoWertV und die
 * Fundstelle in der ImmoWertA (Muster-Anwendungshinweise, Stand 20.09.2023;
 * Seitenzahlen beziehen sich auf fachliteratur/ImmoWertA-2023.pdf).
 *
 * Dieser Kern kennt keine Berliner Modellwerte. Welche Normalherstellungskosten,
 * Restnutzungsdauern, Sachwertfaktoren oder Liegenschaftszinssätze gelten,
 * entscheidet die Modellschicht (berlin.js) und übergibt sie hier als Zahlen.
 *
 * Jeder Rechenschritt wird protokolliert ({nr, bezeichnung, formel, wert,
 * einheit, grundlage}), damit die Oberfläche den Rechenweg zeigen kann.
 */

let zahlFormat = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 4 });
let koeffFormat = new Intl.NumberFormat('de-DE', { maximumSignificantDigits: 6 });

/** Stellt das Zahlenformat der Formeltexte um (z. B. 'en-GB' für die englische Seite). */
export function setzeZahlenformat(sprache) {
  zahlFormat = new Intl.NumberFormat(sprache, { maximumFractionDigits: 4 });
  koeffFormat = new Intl.NumberFormat(sprache, { maximumSignificantDigits: 6 });
}

/** Zahl für die Formeltexte (bis 4 Nachkommastellen). */
export function fmt(wert) {
  return Number.isFinite(wert) ? zahlFormat.format(wert) : String(wert);
}

/** Regressionskoeffizienten mit allen signifikanten Stellen (z. B. −0,00000028). */
export function fmtKoeff(wert) {
  return Number.isFinite(wert) ? koeffFormat.format(wert) : String(wert);
}

/** Kaufmännisches Runden auf `stellen` Nachkommastellen, ohne Gleitkommafehler (1,005 → 1,01). */
export function runde(wert, stellen = 2) {
  if (!Number.isFinite(wert)) return wert;
  const vorzeichen = wert < 0 ? -1 : 1;
  const betrag = Math.abs(wert);
  const gerundet = Number(`${Math.round(Number(`${betrag}e${stellen}`))}e-${stellen}`);
  return vorzeichen * gerundet;
}

/** Runden auf volle Schritte, z. B. 1.000 €: rundeAuf(691976.72, 1000) = 692000. */
export function rundeAuf(wert, schritt = 1000) {
  return Math.round(wert / schritt) * schritt;
}

function zahl(wert, name) {
  if (typeof wert !== 'number' || !Number.isFinite(wert)) {
    throw new Error(`Eingabe fehlt oder ist keine Zahl: ${name}`);
  }
  return wert;
}

function nichtNegativ(wert, name) {
  if (zahl(wert, name) < 0) throw new Error(`Eingabe darf nicht negativ sein: ${name}`);
  return wert;
}

/** Sammelt die Rechenschritte in der Reihenfolge der Berechnung. */
function protokoll() {
  const schritte = [];
  const hinweise = [];
  return {
    schritte,
    hinweise,
    schritt(bezeichnung, formel, wert, einheit, grundlage) {
      schritte.push({ nr: schritte.length + 1, bezeichnung, formel, wert, einheit, grundlage });
      return wert;
    },
    hinweis(text) {
      hinweise.push(text);
    },
  };
}

/* ========================================================================
 * Gemeinsame Bausteine
 * ====================================================================== */

/**
 * Alterswertminderungsfaktor = Restnutzungsdauer / Gesamtnutzungsdauer
 * (lineare Alterswertminderung).
 * § 38 ImmoWertV; ImmoWertA zu § 38, S. 37.
 */
export function alterswertminderungsfaktor(rnd, gnd, stellen = 4) {
  nichtNegativ(rnd, 'Restnutzungsdauer');
  if (zahl(gnd, 'Gesamtnutzungsdauer') <= 0) throw new Error('Gesamtnutzungsdauer muss größer als 0 sein');
  return runde(Math.min(rnd / gnd, 1), stellen);
}

/**
 * Jährlich nachschüssiger Rentenbarwertfaktor (Kapitalisierungsfaktor):
 *   (qⁿ − 1) / (qⁿ · (q − 1)),  q = 1 + p/100, n = Restnutzungsdauer.
 * § 34 Abs. 2 ImmoWertV; ImmoWertA zu § 34, S. 34.
 */
export function barwertfaktor(zinssatzProzent, jahre, stellen = 4) {
  nichtNegativ(zinssatzProzent, 'Liegenschaftszinssatz');
  nichtNegativ(jahre, 'Restnutzungsdauer');
  if (zinssatzProzent === 0) return runde(jahre, stellen);
  const q = 1 + zinssatzProzent / 100;
  const qn = q ** jahre;
  return runde((qn - 1) / (qn * (q - 1)), stellen);
}

/**
 * Bodenwert = Grundstücksfläche × (ggf. angepasster) Bodenrichtwert.
 * §§ 40 Abs. 2, 16 ImmoWertV; ImmoWertA zu § 40, S. 37.
 * `faktor` nimmt eine Anpassung des Bodenrichtwerts auf (z. B. GFZ-Umrechnung).
 */
export function bodenwert({ flaeche, bodenrichtwert, faktor = 1 }) {
  nichtNegativ(flaeche, 'Grundstücksfläche');
  nichtNegativ(bodenrichtwert, 'Bodenrichtwert');
  return runde(flaeche * bodenrichtwert * zahl(faktor, 'Anpassungsfaktor Bodenwert'), 2);
}

function bodenwertAusEingabe(p, eingabe) {
  if (typeof eingabe === 'number') {
    return p.schritt('Bodenwert', 'vorgegeben', runde(eingabe, 2), '€', '§§ 40, 16 ImmoWertV; ImmoWertA zu § 40, S. 37');
  }
  const wert = bodenwert(eingabe);
  const faktorText = eingabe.faktor && eingabe.faktor !== 1 ? ` × ${fmt(eingabe.faktor)}` : '';
  return p.schritt('Bodenwert', `${fmt(eingabe.flaeche)} m² × ${fmt(eingabe.bodenrichtwert)} €/m²${faktorText}`, wert, '€',
    '§§ 40 Abs. 2, 16 ImmoWertV; ImmoWertA zu § 40, S. 37');
}

function bogSumme(p, bog, grundlage) {
  let summe = 0;
  for (const posten of bog || []) {
    zahl(posten.betrag, `besonderes objektspezifisches Grundstücksmerkmal „${posten.bezeichnung}“`);
    summe += posten.betrag;
    p.schritt(`Besonderes objektspezifisches Grundstücksmerkmal: ${posten.bezeichnung}`, posten.betrag >= 0 ? 'Zuschlag' : 'Abschlag',
      runde(posten.betrag, 2), '€', grundlage);
  }
  return runde(summe, 2);
}

/* ========================================================================
 * Sachwertverfahren (§§ 35 bis 39 ImmoWertV)
 * ====================================================================== */

/**
 * Sachwertverfahren nach §§ 35–39 ImmoWertV.
 *
 * eingabe = {
 *   gebaeude: [{ bezeichnung, bgf, nhk, zuschlag2010, baupreisindex, regionalfaktor, gnd, rnd }],
 *   aussenanlagen,                       // Zeitwert besonderer Außen- und Nebenanlagen (§ 37)
 *   bodenwert,                           // Zahl in € oder { flaeche, bodenrichtwert, faktor }
 *   sachwertfaktor,                      // objektspezifisch angepasster Sachwertfaktor (§ 39)
 *   bog: [{ bezeichnung, betrag }],      // besondere objektspezifische Grundstücksmerkmale (§ 8 Abs. 3)
 *   rundung: { alterswertminderung: 4, ergebnis: 1000 }
 * }
 */
export function sachwert(eingabe) {
  if (!eingabe || !Array.isArray(eingabe.gebaeude) || eingabe.gebaeude.length === 0) {
    throw new Error('Eingabe fehlt: mindestens ein Gebäude');
  }
  const p = protokoll();
  const r = { alterswertminderung: 4, ergebnis: 1000, ...(eingabe.rundung || {}) };

  // 1. Vorläufiger Sachwert der baulichen Anlagen je Gebäude (§ 36)
  const gebaeude = eingabe.gebaeude.map((g, i) => {
    const name = g.bezeichnung || `Gebäude ${i + 1}`;
    nichtNegativ(g.bgf, `${name}: Brutto-Grundfläche`);
    nichtNegativ(g.nhk, `${name}: Normalherstellungskosten`);
    zahl(g.baupreisindex, `${name}: Baupreisindex`);
    const regionalfaktor = g.regionalfaktor ?? 1;
    const zuschlag = g.zuschlag2010 || 0;

    const hk2010 = p.schritt(`${name}: Herstellungskosten 2010`,
      `${fmt(g.bgf)} m² × ${fmt(g.nhk)} €/m²${zuschlag ? ` ${zuschlag > 0 ? '+' : '−'} ${fmt(Math.abs(zuschlag))} €` : ''}`,
      runde(g.bgf * g.nhk + zuschlag, 2), '€',
      '§ 36 Abs. 2 ImmoWertV (NHK × BGF, Zuschläge für nicht erfasste Bauteile), Anlage 4; ImmoWertA zu § 36, S. 36');

    const hk = p.schritt(`${name}: Herstellungskosten zum Stichtag`,
      `${fmt(hk2010)} € × ${fmt(g.baupreisindex)} / 100 × Regionalfaktor ${fmt(regionalfaktor)}`,
      runde(hk2010 * g.baupreisindex / 100 * regionalfaktor, 2), '€',
      '§ 36 Abs. 2 Satz 4 und Abs. 3 ImmoWertV (Baupreisindex, Regionalfaktor); ImmoWertA zu § 36, S. 36');

    const awm = p.schritt(`${name}: Alterswertminderungsfaktor`,
      `Restnutzungsdauer ${fmt(g.rnd)} Jahre / Gesamtnutzungsdauer ${fmt(g.gnd)} Jahre`,
      alterswertminderungsfaktor(g.rnd, g.gnd, r.alterswertminderung), '',
      '§ 38 ImmoWertV (linear); ImmoWertA zu § 38, S. 37');
    if (g.rnd > g.gnd) p.hinweis(`${name}: Die Restnutzungsdauer übersteigt die Gesamtnutzungsdauer; der Faktor wurde auf 1,0 begrenzt.`);
    if (g.rnd === 0) p.hinweis(`${name}: Restnutzungsdauer 0 Jahre – das Gebäude trägt keinen Sachwert mehr bei.`);

    const wert = p.schritt(`${name}: vorläufiger Sachwert der baulichen Anlage`,
      `${fmt(hk)} € × ${fmt(awm)}`, runde(hk * awm, 2), '€', '§ 36 Abs. 1 ImmoWertV');

    return { bezeichnung: name, herstellungskosten2010: hk2010, herstellungskosten: hk, alterswertminderungsfaktor: awm, wert };
  });

  const summeGebaeude = p.schritt('Summe vorläufige Sachwerte der baulichen Anlagen',
    gebaeude.map((g) => fmt(g.wert) + ' €').join(' + '), runde(gebaeude.reduce((s, g) => s + g.wert, 0), 2), '€', '§ 35 Abs. 2 Nr. 1 ImmoWertV');

  // 2. Bauliche Außenanlagen und sonstige Anlagen (§ 37)
  const aussenanlagen = p.schritt('Vorläufiger Sachwert der baulichen Außenanlagen und sonstigen Anlagen',
    'Zeitwert nach Erfahrungssätzen', runde(nichtNegativ(eingabe.aussenanlagen ?? 0, 'Außenanlagen'), 2), '€',
    '§ 37 ImmoWertV; ImmoWertA zu § 37, S. 36');

  // 3. Bodenwert (§§ 40 ff.)
  const boden = bodenwertAusEingabe(p, eingabe.bodenwert);

  // 4. Vorläufiger Sachwert des Grundstücks (§ 35 Abs. 2)
  const vorlaeufig = p.schritt('Vorläufiger Sachwert des Grundstücks',
    `${fmt(summeGebaeude)} € + ${fmt(aussenanlagen)} € + ${fmt(boden)} €`, runde(summeGebaeude + aussenanlagen + boden, 2), '€',
    '§ 35 Abs. 2 ImmoWertV; ImmoWertA zu § 35, S. 35');

  // 5. Marktanpassung mit dem Sachwertfaktor (§ 35 Abs. 3, § 39)
  const swf = nichtNegativ(eingabe.sachwertfaktor, 'Sachwertfaktor');
  const marktangepasst = p.schritt('Marktangepasster vorläufiger Sachwert',
    `${fmt(vorlaeufig)} € × Sachwertfaktor ${fmt(swf)}`, runde(vorlaeufig * swf, 2), '€',
    '§ 35 Abs. 3, § 39, § 21 Abs. 3 ImmoWertV; ImmoWertA zu § 39, S. 37');

  // 6. Besondere objektspezifische Grundstücksmerkmale (§ 35 Abs. 4, § 8 Abs. 3)
  const bog = bogSumme(p, eingabe.bog, '§ 35 Abs. 4, § 8 Abs. 3 ImmoWertV; ImmoWertA zu § 8, S. 16');
  const ergebnis = p.schritt('Sachwert des Grundstücks',
    `${fmt(marktangepasst)} € ${bog >= 0 ? '+' : '−'} ${fmt(Math.abs(bog))} €`, runde(marktangepasst + bog, 2), '€', '§ 35 Abs. 4 ImmoWertV');
  const gerundet = p.schritt('Sachwert, gerundet', `auf volle ${fmt(r.ergebnis)} €`, rundeAuf(ergebnis, r.ergebnis), '€', 'Wertermittlungspraxis');

  return {
    verfahren: 'sachwert',
    schritte: p.schritte,
    hinweise: p.hinweise,
    gebaeude,
    summeGebaeude,
    aussenanlagen,
    bodenwert: boden,
    vorlaeufigerSachwert: vorlaeufig,
    sachwertfaktor: swf,
    marktangepasst,
    bogSumme: bog,
    sachwert: ergebnis,
    sachwertGerundet: gerundet,
  };
}

/* ========================================================================
 * Allgemeines Ertragswertverfahren (§§ 27 bis 34 ImmoWertV)
 * ====================================================================== */

/**
 * Betrag eines Bewirtschaftungskostenansatzes.
 * satz = { jeM2, jeEinheit, prozent, betrag } – die Teile addieren sich:
 *   jeM2 × Fläche + jeEinheit × Einheiten + prozent % vom Jahresrohertrag + fester Betrag.
 * § 32 ImmoWertV, Anlage 3; ImmoWertA zu § 32, S. 34.
 */
export function bewirtschaftungsbetrag(satz, { flaeche = 0, einheiten = 0, rohertragJahr = 0 }) {
  if (!satz) return 0;
  const teile = [
    (satz.jeM2 || 0) * flaeche,
    (satz.jeEinheit || 0) * einheiten,
    (satz.prozent || 0) / 100 * rohertragJahr,
    satz.betrag || 0,
  ];
  return runde(teile.reduce((s, t) => s + t, 0), 2);
}

function satzText(satz, nutzung) {
  const teile = [];
  if (satz?.jeM2) teile.push(`${fmt(satz.jeM2)} €/m² × ${fmt(nutzung.flaeche || 0)} m²`);
  if (satz?.jeEinheit) teile.push(`${fmt(satz.jeEinheit)} € × ${fmt(nutzung.einheiten || 0)} Einheit(en)`);
  if (satz?.prozent) teile.push(`${fmt(satz.prozent)} % vom Rohertrag`);
  if (satz?.betrag) teile.push(`${fmt(satz.betrag)} € pauschal`);
  return teile.join(' + ') || 'kein Ansatz';
}

const POSITIONEN = [
  ['verwaltung', 'Verwaltungskosten', '§ 32 Abs. 1 Nr. 1, Abs. 2 ImmoWertV, Anlage 3'],
  ['instandhaltung', 'Instandhaltungskosten', '§ 32 Abs. 1 Nr. 2, Abs. 3 ImmoWertV, Anlage 3'],
  ['mietausfallwagnis', 'Mietausfallwagnis', '§ 32 Abs. 1 Nr. 3, Abs. 4 ImmoWertV, Anlage 3'],
  ['betriebskosten', 'Nicht umlagefähige Betriebskosten', '§ 32 Abs. 1 Nr. 4 ImmoWertV'],
];

/**
 * Allgemeines Ertragswertverfahren nach §§ 27–34 ImmoWertV.
 *
 * eingabe = {
 *   nutzungen: [{ art: 'wohnen'|'gewerbe'|'sonstiges', bezeichnung, flaeche, einheiten,
 *                 mieteMonat,                         // Nettokaltmiete der Nutzung je Monat in €
 *                 gebaeudeteil,                       // Kennung des Gebäudeteils (optional)
 *                 bewirtschaftung: { verwaltung, instandhaltung, mietausfallwagnis, betriebskosten } }],
 *   gebaeudeteile: [{ id, bezeichnung, rnd }],       // optional; sonst `rnd`
 *   rnd,
 *   liegenschaftszins,                               // in Prozent
 *   bodenwert,                                       // Zahl in € oder { flaeche, bodenrichtwert, faktor }
 *   marktanpassungsfaktor,                           // Standard 1,0
 *   bog: [{ bezeichnung, betrag }],
 *   rundung: { barwertfaktor: 4, mittlereRnd: 3, ergebnis: 1000 }
 * }
 */
export function ertragswert(eingabe) {
  if (!eingabe || !Array.isArray(eingabe.nutzungen) || eingabe.nutzungen.length === 0) {
    throw new Error('Eingabe fehlt: mindestens eine Nutzung');
  }
  const p = protokoll();
  const r = { barwertfaktor: 4, mittlereRnd: 3, ergebnis: 1000, ...(eingabe.rundung || {}) };

  // 1. Rohertrag (§ 31 Abs. 2)
  const nutzungen = eingabe.nutzungen.map((n, i) => {
    const name = n.bezeichnung || `Nutzung ${i + 1}`;
    nichtNegativ(n.mieteMonat, `${name}: Miete je Monat`);
    const rohertragJahr = p.schritt(`${name}: Jahresrohertrag`, `${fmt(n.mieteMonat)} €/Monat × 12`, runde(n.mieteMonat * 12, 2), '€',
      '§ 31 Abs. 2 ImmoWertV (marktüblich erzielbare, hier tatsächliche Nettokaltmiete); ImmoWertA zu § 31, S. 33');
    return { ...n, bezeichnung: name, rohertragJahr };
  });
  const rohertrag = p.schritt('Jahresrohertrag gesamt', nutzungen.map((n) => fmt(n.rohertragJahr) + ' €').join(' + '),
    runde(nutzungen.reduce((s, n) => s + n.rohertragJahr, 0), 2), '€', '§ 31 Abs. 2 ImmoWertV');

  // 2. Bewirtschaftungskosten (§ 32, Anlage 3)
  const bewirtschaftung = {};
  let summeBewk = 0;
  for (const [schluessel, titel, grundlage] of POSITIONEN) {
    let summePosition = 0;
    for (const n of nutzungen) {
      const satz = n.bewirtschaftung?.[schluessel];
      const betrag = bewirtschaftungsbetrag(satz, { flaeche: n.flaeche, einheiten: n.einheiten, rohertragJahr: n.rohertragJahr });
      if (satz) p.schritt(`${titel} ${n.bezeichnung}`, satzText(satz, n), betrag, '€', `${grundlage}; ImmoWertA zu § 32, S. 34`);
      summePosition += betrag;
    }
    bewirtschaftung[schluessel] = runde(summePosition, 2);
    summeBewk += summePosition;
  }
  const bewk = p.schritt('Bewirtschaftungskosten gesamt',
    POSITIONEN.map(([k, titel]) => `${titel} ${fmt(bewirtschaftung[k])} €`).join(' + '), runde(summeBewk, 2), '€', '§ 32 Abs. 1 ImmoWertV');

  // 3. Reinertrag (§ 31 Abs. 1)
  const reinertrag = p.schritt('Jahresreinertrag', `${fmt(rohertrag)} € − ${fmt(bewk)} €`, runde(rohertrag - bewk, 2), '€',
    '§ 31 Abs. 1 ImmoWertV; ImmoWertA zu § 31, S. 33');

  // 4. Bodenwert und Bodenwertverzinsung (§ 28 Satz 1 Nr. 1)
  const boden = bodenwertAusEingabe(p, eingabe.bodenwert);
  const lz = nichtNegativ(eingabe.liegenschaftszins, 'Liegenschaftszinssatz');
  const verzinsung = p.schritt('Bodenwertverzinsungsbetrag', `${fmt(boden)} € × ${fmt(lz)} %`, runde(boden * lz / 100, 2), '€',
    '§ 28 Satz 1 Nr. 1 und Satz 2 ImmoWertV; ImmoWertA zu § 28, S. 31');
  const gebaeudereinertrag = p.schritt('Reinertragsanteil der baulichen Anlagen', `${fmt(reinertrag)} € − ${fmt(verzinsung)} €`,
    runde(reinertrag - verzinsung, 2), '€', '§ 28 Satz 1 Nr. 1 ImmoWertV');

  // 5. Restnutzungsdauer – bei mehreren Gebäudeteilen nach Rohertragsanteilen gewichtet
  let rnd;
  if (Array.isArray(eingabe.gebaeudeteile) && eingabe.gebaeudeteile.length > 0) {
    const teile = eingabe.gebaeudeteile.map((t) => {
      nichtNegativ(t.rnd, `Gebäudeteil ${t.id}: Restnutzungsdauer`);
      const anteil = nutzungen.filter((n) => n.gebaeudeteil === t.id).reduce((s, n) => s + n.rohertragJahr, 0);
      return { ...t, anteil };
    });
    const summeAnteile = teile.reduce((s, t) => s + t.anteil, 0);
    if (summeAnteile <= 0) throw new Error('Die Nutzungen sind keinem Gebäudeteil zugeordnet');
    rnd = p.schritt('Mittlere Restnutzungsdauer (gewichtet nach Rohertragsanteilen)',
      teile.map((t) => `${fmt(t.rnd)} Jahre × ${fmt(t.anteil)} €`).join(' + ') + ` / ${fmt(summeAnteile)} €`,
      runde(teile.reduce((s, t) => s + t.rnd * t.anteil, 0) / summeAnteile, r.mittlereRnd), 'Jahre',
      '§ 28 Satz 3 ImmoWertV (Kapitalisierungsdauer = Restnutzungsdauer); Gewichtung bei mehreren Gebäudeteilen nach Wertermittlungspraxis');
  } else {
    rnd = p.schritt('Restnutzungsdauer', 'vorgegeben', nichtNegativ(eingabe.rnd, 'Restnutzungsdauer'), 'Jahre', '§ 28 Satz 3 ImmoWertV');
  }

  const basis = {
    verfahren: 'ertragswert', schritte: p.schritte, hinweise: p.hinweise, nutzungen, rohertrag, bewirtschaftung,
    bewirtschaftungskosten: bewk, reinertrag, bodenwert: boden, liegenschaftszins: lz, bodenwertverzinsung: verzinsung,
    gebaeudereinertrag, rnd,
  };

  if (gebaeudereinertrag <= 0) {
    p.hinweis('Der Reinertrag deckt die Bodenwertverzinsung nicht. Das Gebäude trägt wirtschaftlich nicht mehr zum Wert bei; '
      + 'in solchen Fällen ist eine Liquidationsbetrachtung erforderlich (ImmoWertA zu § 28). Es wird kein Ertragswert ausgegeben.');
    return { ...basis, status: 'liquidation', barwertfaktor: null, gebaeudeertragswert: null, vorlaeufigerErtragswert: null,
      marktangepasst: null, bogSumme: null, ertragswert: null, ertragswertGerundet: null };
  }

  // 6. Kapitalisierung (§ 34) und vorläufiger Ertragswert (§ 28)
  const bwf = p.schritt('Barwertfaktor (Kapitalisierungsfaktor)', `(qⁿ − 1) / (qⁿ · (q − 1)) mit q = ${fmt(1 + lz / 100)}, n = ${fmt(rnd)}`,
    barwertfaktor(lz, rnd, r.barwertfaktor), '', '§ 34 Abs. 2 ImmoWertV; ImmoWertA zu § 34, S. 34');
  const gebaeudeertragswert = p.schritt('Vorläufiger Ertragswert der baulichen Anlagen', `${fmt(gebaeudereinertrag)} € × ${fmt(bwf)}`,
    runde(gebaeudereinertrag * bwf, 2), '€', '§ 28 Satz 1 Nr. 1 ImmoWertV');
  const vorlaeufig = p.schritt('Vorläufiger Ertragswert', `${fmt(gebaeudeertragswert)} € + ${fmt(boden)} €`,
    runde(gebaeudeertragswert + boden, 2), '€', '§ 28 Satz 1 ImmoWertV; ImmoWertA zu § 28, S. 31');

  // 7. Marktanpassung (§ 7 Abs. 2) und besondere objektspezifische Grundstücksmerkmale (§ 27 Abs. 4, § 8 Abs. 3)
  const maf = nichtNegativ(eingabe.marktanpassungsfaktor ?? 1, 'Marktanpassungsfaktor');
  const marktangepasst = p.schritt('Marktangepasster vorläufiger Ertragswert', `${fmt(vorlaeufig)} € × ${fmt(maf)}`,
    runde(vorlaeufig * maf, 2), '€', '§ 7 Abs. 2 ImmoWertV; ImmoWertA zu § 7');
  const bog = bogSumme(p, eingabe.bog, '§ 27 Abs. 4, § 8 Abs. 3 ImmoWertV; ImmoWertA zu § 8, S. 16');
  const ergebnis = p.schritt('Ertragswert des Grundstücks', `${fmt(marktangepasst)} € ${bog >= 0 ? '+' : '−'} ${fmt(Math.abs(bog))} €`,
    runde(marktangepasst + bog, 2), '€', '§ 27 Abs. 4 ImmoWertV');
  const gerundet = p.schritt('Ertragswert, gerundet', `auf volle ${fmt(r.ergebnis)} €`, rundeAuf(ergebnis, r.ergebnis), '€', 'Wertermittlungspraxis');

  return { ...basis, status: 'ok', barwertfaktor: bwf, gebaeudeertragswert, vorlaeufigerErtragswert: vorlaeufig, marktanpassungsfaktor: maf,
    marktangepasst, bogSumme: bog, ertragswert: ergebnis, ertragswertGerundet: gerundet };
}
