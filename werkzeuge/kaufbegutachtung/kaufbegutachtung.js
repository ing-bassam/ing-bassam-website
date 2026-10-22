/**
 * Kaufbegutachtung – Rechenkern ohne Browser-Abhängigkeiten.
 *
 * Alle Preise, Regeln, Unterlagen und Texte kommen aus daten.js (einzige Quelle).
 * Diese Datei rechnet nur:
 *   - Preise: brutto = netto × (1 + mwst), auf Cent gerundet; Spannen (Bauakte)
 *     werden als „von – bis“ summiert. Zuschläge sind keine Wahl, sondern fallen
 *     an, wenn sie zutreffen: ab der Wohnfläche zuschlaege[].auto.flaeche_ab oder
 *     wenn der Schalter zuschlaege[].auto.schalter an ist (z. B. Maisonette).
 *   - Hinweise: Regeln, deren Bedingungen alle erfüllt sind (UND-Verknüpfung).
 *     Eine Regel mit Baujahr-Grenze erscheint erst, wenn ein Baujahr eingegeben
 *     ist; eine Regel mit Heizung, Nutzung oder Lage erst, wenn das Feld gewählt ist.
 *   - Unterlagen: dieselben Bedingungen, sortiert nach Priorität.
 *   - Anfrage: Text und mailto-Adresse für die E-Mail an das Büro (unter 1.800 Zeichen).
 *
 * Sprachen: "de" und "en". Eingaben werden geprüft, nichts wird gesendet oder gespeichert.
 */
import { DATEN } from "./daten.js";

export { DATEN };
export const KATEGORIEN = ["pflicht", "miete", "pruefen", "foerderung"];
export const OBJEKTE = ["etw", "efh"];
export const MAIL_GRENZE = 1800;
export const SCHALTER = ["fertighaus", "mfh6", "milieuschutz"];       // Schritt 2: Hinweise
export const PREIS_SCHALTER = ["maisonette", "vollkeller", "einlieger"]; // Schritt 1: Zuschläge

const sprachen = (sprache) => (sprache === "en" ? "en" : "de");
const ui = (sprache) => DATEN.seite[sprachen(sprache)].ui;

function ersetzen(vorlage, werte) {
  return vorlage.replace(/\{(\w+)\}/g, (_, name) => (name in werte ? String(werte[name]) : `{${name}}`));
}

// ------------------------------------------------------------------ Preise

/** Bruttobetrag in Cent (ganzzahlig) – vermeidet Rundungsfehler beim Summieren. */
export function bruttoCent(netto, mwst = DATEN.mwst) {
  return Math.round(netto * 100 * (1 + mwst));
}

/** Bruttobetrag in Euro, auf Cent gerundet. */
export function brutto(netto, mwst = DATEN.mwst) {
  return bruttoCent(netto, mwst) / 100;
}

/** Betrag mit zwei Nachkommastellen: „1.059,10 €“ (de) oder „€1,059.10“ (en). */
export function euro(betrag, sprache = "de") {
  const cent = Math.round(Math.abs(betrag) * 100);
  const ganz = String(Math.floor(cent / 100));
  const rest = String(cent % 100).padStart(2, "0");
  const minus = betrag < 0 ? "−" : "";
  if (sprachen(sprache) === "en") {
    return `${minus}€${ganz.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${rest}`;
  }
  return `${minus}${ganz.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${rest} €`;
}

/** Betrag oder Spanne: „267,75 – 357,00 €“ bzw. „€267.75 – €357.00“. */
export function euroSpanne(von, bis, sprache = "de") {
  if (von === bis) return euro(von, sprache);
  if (sprachen(sprache) === "en") return `${euro(von, "en")} – ${euro(bis, "en")}`;
  return `${euro(von, "de").replace(" €", "")} – ${euro(bis, "de")}`;
}

function posten(eintrag, art, id, sprache) {
  const nettoVon = eintrag.netto ?? eintrag.netto_von;
  const nettoBis = eintrag.netto ?? eintrag.netto_bis;
  const text = eintrag[sprachen(sprache)];
  return {
    id,
    art,
    name: text.name,
    kurz: text.kurz || "",
    text: text.text || "",
    nettoVon,
    nettoBis,
    bruttoVon: brutto(nettoVon),
    bruttoBis: brutto(nettoBis),
    spanne: nettoVon !== nettoBis,
    autoAb: eintrag.auto && eintrag.auto.flaeche_ab ? eintrag.auto.flaeche_ab : null,
    schalter: eintrag.auto && eintrag.auto.schalter ? eintrag.auto.schalter : null,
  };
}

/** Grundpaket, Zuschläge und Optionen einer Objektart mit Netto- und Bruttopreisen. */
export function paket(objekt, sprache = "de") {
  const p = DATEN.pakete[objekt];
  if (!p) throw new Error(`Unbekannte Objektart: ${objekt}`);
  return {
    objekt,
    grund: posten(p.grund, "grund", p.grund.id, sprache),
    zuschlaege: p.zuschlaege.map((z) => posten(z, "zuschlag", z.id, sprache)),
    optionen: p.optionen.map((id) => posten(DATEN.optionen[id], "option", id, sprache)),
  };
}

function flaecheErreicht(z, flaeche) {
  const zahl = Number(flaeche);
  return Boolean(z.auto && z.auto.flaeche_ab) && flaeche !== null && Number.isFinite(zahl) && zahl >= z.auto.flaeche_ab;
}

/** Zuschläge, die schon wegen der Wohnfläche anfallen (flaeche ≥ auto.flaeche_ab). */
export function zuschlaegeFuerFlaeche(objekt, flaeche) {
  return DATEN.pakete[objekt].zuschlaege.filter((z) => flaecheErreicht(z, flaeche)).map((z) => z.id);
}

/**
 * Zuschläge, die für dieses Objekt zutreffen: wegen der Wohnfläche oder weil der
 * zugehörige Schalter an ist (Maisonette/Dachgeschoss, Vollkeller, Einliegerwohnung).
 * grund: "flaeche", "schalter" oder beides – für die Anzeige „fällt an, weil …“.
 */
export function zuschlaegeFuer(e) {
  return DATEN.pakete[e.objekt].zuschlaege.map((z) => {
    const gruende = [];
    if (flaecheErreicht(z, e.flaeche)) gruende.push("flaeche");
    if (z.auto && z.auto.schalter && e[z.auto.schalter]) gruende.push("schalter");
    return { id: z.id, trifftZu: gruende.length > 0, gruende };
  });
}

/**
 * Preis für ein Objekt: Grundpreis + zutreffende Zuschläge + gewählte Optionen.
 * e: Objektart, Wohnfläche und Schalter (wie aus eingabeLesen); auswahl: IDs der
 * gewählten Optionen (Zuschläge in auswahl werden ignoriert – sie sind keine Wahl).
 */
export function preisBerechnen({ auswahl = [], sprache = "de", ...e }) {
  const objekt = e.objekt === "efh" ? "efh" : "etw";
  const p = paket(objekt, sprache);
  const zutreffend = new Set(zuschlaegeFuer({ ...e, objekt, flaeche: e.flaeche ?? null }).filter((z) => z.trifftZu).map((z) => z.id));
  const gewaehlt = new Set(auswahl);
  const positionen = [p.grund, ...p.zuschlaege.filter((z) => zutreffend.has(z.id)),
    ...p.optionen.filter((o) => gewaehlt.has(o.id))];
  const summe = (feld) => positionen.reduce((s, x) => s + x[feld], 0);
  const centSumme = (feld) => positionen.reduce((s, x) => s + bruttoCent(x[feld]), 0);
  const nettoVon = summe("nettoVon");
  const nettoBis = summe("nettoBis");
  const bruttoVon = centSumme("nettoVon") / 100;
  const bruttoBis = centSumme("nettoBis") / 100;
  return {
    objekt,
    positionen,
    nettoVon,
    nettoBis,
    bruttoVon,
    bruttoBis,
    ustVon: Math.round((bruttoVon - nettoVon) * 100) / 100,
    ustBis: Math.round((bruttoBis - nettoBis) * 100) / 100,
    spanne: nettoVon !== nettoBis,
  };
}

// ------------------------------------------------------- Eingaben prüfen

function zahlLesen(wert) {
  if (wert === "" || wert === null || wert === undefined) return null;
  const zahl = Number(String(wert).trim().replace(",", "."));
  return Number.isFinite(zahl) ? zahl : NaN;
}

/**
 * Formularwerte → geprüfte Eingabe. Ungültige Zahlen werden wie leere Felder
 * behandelt und als Fehler gemeldet; Schalter gelten nur für ihre Objektart.
 */
export function eingabeLesen(roh = {}, sprache = "de") {
  const t = ui(sprache);
  const fehler = {};
  const objekt = roh.objekt === "efh" ? "efh" : "etw";
  let flaeche = zahlLesen(roh.flaeche);
  if (flaeche !== null && (Number.isNaN(flaeche) || flaeche < 10 || flaeche > 2000)) {
    fehler.flaeche = t.fehler_flaeche;
    flaeche = null;
  }
  let baujahr = zahlLesen(roh.baujahr);
  if (baujahr !== null && (Number.isNaN(baujahr) || !Number.isInteger(baujahr) || baujahr < 1800 || baujahr > 2030)) {
    fehler.baujahr = t.fehler_baujahr;
    baujahr = null;
  }
  const auswahl = (id, liste) => (liste.some((e) => e.id === id) ? id : "");
  const e = {
    objekt,
    flaeche,
    baujahr,
    heizung: auswahl(roh.heizung, DATEN.eingaben.heizung),
    nutzung: auswahl(roh.nutzung, DATEN.eingaben.nutzung),
    region: auswahl(roh.region, DATEN.eingaben.region),
  };
  for (const name of SCHALTER) {
    e[name] = Boolean(roh[name]) && DATEN.eingaben.schalter[name].objekt === objekt;
  }
  for (const name of PREIS_SCHALTER) {
    e[name] = Boolean(roh[name]) && DATEN.eingaben.preis_schalter[name].objekt === objekt;
  }
  return { eingabe: e, fehler };
}

// ------------------------------------------------- Regeln und Unterlagen

/** Sind alle Bedingungen eines Eintrags (Regel oder Unterlage) erfüllt? */
export function bedingungErfuellt(eintrag, e) {
  if (eintrag.objekt && eintrag.objekt !== "beide" && eintrag.objekt !== e.objekt) return false;
  if (eintrag.von !== undefined || eintrag.bis !== undefined) {
    if (e.baujahr === null || e.baujahr === undefined) return false;
    if (eintrag.von !== undefined && e.baujahr < eintrag.von) return false;
    if (eintrag.bis !== undefined && e.baujahr > eintrag.bis) return false;
  }
  for (const feld of ["heizung", "nutzung", "region"]) {
    if (eintrag[feld] && !(e[feld] && eintrag[feld].includes(e[feld]))) return false;
  }
  for (const name of SCHALTER) {
    if (eintrag[name] === true && !e[name]) return false;
  }
  return true;
}

function regelText(regel, sprache) {
  const t = regel[sprachen(sprache)];
  return {
    id: regel.id,
    kategorie: regel.kategorie,
    titel: t.titel,
    text: t.text,
    quelle: { titel: regel.quelle.titel, url: regel.quelle.url || "" },
    empfiehlt: regel.empfiehlt || [],
  };
}

/**
 * Passende Hinweise, nach Kategorien in fester Reihenfolge gruppiert.
 * empfohlen: Optionen der gewählten Objektart, die eine passende Regel empfiehlt.
 */
export function hinweise(e, sprache = "de") {
  const passend = DATEN.regeln.filter((r) => bedingungErfuellt(r, e));
  const titel = DATEN.seite[sprachen(sprache)].kategorien;
  const gruppen = KATEGORIEN.map((kategorie) => ({
    kategorie,
    titel: titel[kategorie],
    regeln: passend.filter((r) => r.kategorie === kategorie).map((r) => regelText(r, sprache)),
  })).filter((g) => g.regeln.length);
  const verfuegbar = new Set(DATEN.pakete[e.objekt].optionen);
  const empfohlen = [...new Set(passend.flatMap((r) => r.empfiehlt || []))].filter((id) => verfuegbar.has(id));
  return { gruppen, empfohlen, anzahl: passend.length, ids: passend.map((r) => r.id) };
}

/** Unterlagen für die Objektart und die Eingaben, nach Priorität sortiert (1 vor 2 vor 3). */
export function unterlagen(e, sprache = "de") {
  const s = sprachen(sprache);
  return DATEN.unterlagen[e.objekt]
    .filter((u) => bedingungErfuellt(u, e))
    .map((u, i) => ({ id: u.id, prio: u.prio, text: u[s], wo: u[`wo_${s}`], reihenfolge: i }))
    .sort((a, b) => a.prio - b.prio || a.reihenfolge - b.reihenfolge)
    .map(({ reihenfolge, ...rest }) => rest);
}

/** Checkliste als Text zum Kopieren und Weiterleiten. */
export function unterlagenText(e, vorhanden = [], sprache = "de") {
  const s = sprachen(sprache);
  const t = ui(s);
  const liste = unterlagen(e, s);
  const da = new Set(vorhanden);
  const objektName = DATEN.text[s][e.objekt === "efh" ? "objekt_efh" : "objekt_etw"];
  const zeilen = [`${t.unterlagen_kopf} – ${objektName}`];
  for (const prio of [1, 2, 3]) {
    const teil = liste.filter((u) => u.prio === prio);
    if (!teil.length) continue;
    zeilen.push("", `${DATEN.text[s].prio[String(prio)]}:`);
    for (const u of teil) zeilen.push(`[${da.has(u.id) ? "x" : " "}] ${u.text} – ${t.wo_kurz}: ${u.wo}`);
  }
  zeilen.push("", `${DATEN.urls[s]}#${DATEN.anker[s][e.objekt]}`);
  return zeilen.join("\n");
}

// ------------------------------------------------------------ Anfrage

function label(liste, id, sprache) {
  const eintrag = liste.find((x) => x.id === id);
  return eintrag ? eintrag[sprachen(sprache)] : "";
}

function kuerzen(text, laenge) {
  return text.length <= laenge ? text : `${text.slice(0, laenge - 1).trimEnd()}…`;
}

/**
 * Text und mailto-Adresse der Anfrage. Hält den Text (Betreff + Inhalt) unter
 * grenze Zeichen: Zuerst werden lange Unterlagen-Namen gekürzt, dann die Liste
 * der vorhandenen Unterlagen durch ihre Anzahl ersetzt, zuletzt die Liste der
 * fehlenden Unterlagen abgeschnitten („… und 3 weitere“).
 */
export function anfrage({ eingabe: e, auswahl = [], vorhanden = [], adresse = "", termin = "",
  sprache = "de", grenze = MAIL_GRENZE }) {
  const s = sprachen(sprache);
  const t = ui(s);
  const preis = preisBerechnen({ ...e, auswahl, sprache: s });
  const liste = unterlagen(e, s);
  const da = new Set(vorhanden);
  const vorhandenListe = liste.filter((u) => da.has(u.id)).map((u) => u.text);
  const fehlenListe = liste.filter((u) => u.prio === 1 && !da.has(u.id)).map((u) => u.text);
  const objektName = DATEN.text[s][e.objekt === "efh" ? "objekt_efh" : "objekt_etw"];
  const adresseKurz = kuerzen(String(adresse || "").replace(/\s+/g, " ").trim(), 160);
  const terminKurz = kuerzen(String(termin || "").replace(/\s+/g, " ").trim(), 120);
  const betreff = adresseKurz ? `${t.betreff}: ${objektName}, ${kuerzen(adresseKurz, 80)}` : `${t.betreff}: ${objektName}`;

  const kopf = [t.anhang, "", t.anrede, "", t.einleitung, "", `${t.objekt}: ${objektName}`];
  if (adresseKurz) kopf.push(`${t.adresse}: ${adresseKurz}`);
  if (terminKurz) kopf.push(`${t.termin}: ${terminKurz}`);
  if (e.flaeche) kopf.push(`${t.flaeche}: ${String(e.flaeche).replace(".", s === "de" ? "," : ".")} m²`);
  if (e.baujahr) kopf.push(`${t.baujahr}: ${e.baujahr}`);
  if (e.heizung) kopf.push(`${t.heizung}: ${label(DATEN.eingaben.heizung, e.heizung, s)}`);
  if (e.nutzung) kopf.push(`${t.nutzung}: ${label(DATEN.eingaben.nutzung, e.nutzung, s)}`);
  if (e.region) kopf.push(`${t.region}: ${label(DATEN.eingaben.region, e.region, s)}`);
  const besonders = [...PREIS_SCHALTER.filter((n) => e[n]).map((n) => DATEN.eingaben.preis_schalter[n][s]),
    ...SCHALTER.filter((n) => e[n]).map((n) => DATEN.eingaben.schalter[n][s])];
  if (besonders.length) kopf.push(`${t.besonderheiten}: ${besonders.join("; ")}`);

  kopf.push("", `${t.leistungen}:`);
  for (const pos of preis.positionen) {
    kopf.push(`- ${pos.name}: ${euroSpanne(pos.bruttoVon, pos.bruttoBis, s)}`);
  }
  kopf.push(`${t.gesamt}: ${euroSpanne(preis.bruttoVon, preis.bruttoBis, s)} ${t.inkl} (${t.netto} ${euroSpanne(preis.nettoVon, preis.nettoBis, s)})`);
  const fuss = ["", t.gruss];

  const bauen = ({ laenge = Infinity, nurAnzahl = false, fehlenHoechstens = Infinity }) => {
    const teil = [];
    if (vorhandenListe.length) {
      if (nurAnzahl) teil.push("", ersetzen(t.vorhanden_anzahl, { n: vorhandenListe.length }));
      else teil.push("", `${t.vorhanden}:`, ...vorhandenListe.map((x) => `- ${kuerzen(x, laenge)}`));
    }
    teil.push("", `${t.fehlen}:`);
    if (!fehlenListe.length) teil.push(`- ${t.keine}`);
    const gezeigt = fehlenListe.slice(0, fehlenHoechstens);
    teil.push(...gezeigt.map((x) => `- ${kuerzen(x, laenge)}`));
    if (gezeigt.length < fehlenListe.length) teil.push(ersetzen(t.weitere, { n: fehlenListe.length - gezeigt.length }));
    return [...kopf, ...teil, ...fuss].join("\n");
  };
  const passt = (text) => betreff.length + text.length <= grenze;

  let text = bauen({});
  const stufen = [{ laenge: 70 }, { laenge: 70, nurAnzahl: true }, { laenge: 50, nurAnzahl: true }];
  for (const stufe of stufen) {
    if (passt(text)) break;
    text = bauen(stufe);
  }
  for (let n = fehlenListe.length - 1; !passt(text) && n >= 0; n -= 1) {
    text = bauen({ laenge: 50, nurAnzahl: true, fehlenHoechstens: n });
  }
  const crlf = text.replace(/\n/g, "\r\n");
  const href = `mailto:${DATEN.kontakt.email}?subject=${encodeURIComponent(betreff)}&body=${encodeURIComponent(crlf)}`;
  return { betreff, text, href, laenge: betreff.length + text.length, preis };
}

// -------------------------------------------------- Gemeinschaftskosten

/** Anteil an Kosten der Gemeinschaft: Kosten × Zähler / Nenner (z. B. 45/1.000). */
export function anteil(kosten, zaehler, nenner) {
  const k = zahlLesen(kosten);
  const z = zahlLesen(zaehler);
  const n = zahlLesen(nenner);
  if ([k, z, n].some((x) => x === null || Number.isNaN(x)) || k < 0 || z < 0 || n <= 0 || z > n) return null;
  return Math.round((k * z / n) * 100) / 100;
}
