/**
 * Kaufbegutachtung – Kern des Hinweis-Assistenten ohne Browser-Abhängigkeiten.
 *
 * Alle Regeln, Unterlagen und Texte kommen aus daten.js (einzige Quelle). Preise
 * stehen bewusst nirgends auf der Website: Preise und Leistungsübersicht verschickt
 * das Büro nur auf Anfrage per E-Mail. Diese Datei ermittelt nur:
 *   - Hinweise: Regeln, deren Bedingungen alle erfüllt sind (UND-Verknüpfung).
 *     Eine Regel mit Baujahr-Grenze erscheint erst, wenn ein Baujahr eingegeben
 *     ist; eine Regel mit Heizung, Nutzung oder Lage erst, wenn das Feld gewählt ist.
 *   - Unterlagen: dieselben Bedingungen, sortiert nach Priorität.
 *   - Anfrage: Text und mailto-Adresse für die E-Mail an das Büro, mit der Bitte um
 *     ein Angebot mit Preisen und Leistungsübersicht (unter 1.800 Zeichen).
 *   - Anteil an Gemeinschaftskosten: rechnet nur mit den Eingaben der Nutzerin oder
 *     des Nutzers (Kosten × Miteigentumsanteil).
 *
 * Sprachen: "de" und "en". Eingaben werden geprüft, nichts wird gesendet oder gespeichert.
 */
import { DATEN } from "./daten.js";

export { DATEN };
export const KATEGORIEN = ["pflicht", "miete", "pruefen", "foerderung"];
export const OBJEKTE = ["etw", "efh"];
export const MAIL_GRENZE = 1800;
// Merkmale des Objekts (Kästchen); jedes gilt nur für seine Objektart.
export const SCHALTER = Object.keys(DATEN.eingaben.schalter);

const sprachen = (sprache) => (sprache === "en" ? "en" : "de");
const ui = (sprache) => DATEN.seite[sprachen(sprache)].ui;

function ersetzen(vorlage, werte) {
  return vorlage.replace(/\{(\w+)\}/g, (_, name) => (name in werte ? String(werte[name]) : `{${name}}`));
}

/** Betrag der Nutzereingabe mit zwei Nachkommastellen, Deutsch oder Englisch (nur für den Anteil). */
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

/** Leistungsumfang einer Objektart als Liste (ohne Preise). */
export function leistungsumfang(objekt, sprache = "de") {
  const eintrag = DATEN.leistungen[objekt === "efh" ? "efh" : "etw"];
  return [...eintrag[sprachen(sprache)]];
}

// ------------------------------------------------------- Eingaben prüfen

function zahlLesen(wert) {
  if (wert === "" || wert === null || wert === undefined) return null;
  const zahl = Number(String(wert).trim().replace(",", "."));
  return Number.isFinite(zahl) ? zahl : NaN;
}

/**
 * Formularwerte → geprüfte Eingabe. Ungültige Zahlen werden wie leere Felder
 * behandelt und als Fehler gemeldet; Merkmale gelten nur für ihre Objektart.
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
  };
}

/** Passende Hinweise, nach Kategorien in fester Reihenfolge gruppiert. */
export function hinweise(e, sprache = "de") {
  const passend = DATEN.regeln.filter((r) => bedingungErfuellt(r, e));
  const titel = DATEN.seite[sprachen(sprache)].kategorien;
  const gruppen = KATEGORIEN.map((kategorie) => ({
    kategorie,
    titel: titel[kategorie],
    regeln: passend.filter((r) => r.kategorie === kategorie).map((r) => regelText(r, sprache)),
  })).filter((g) => g.regeln.length);
  return { gruppen, anzahl: passend.length, ids: passend.map((r) => r.id) };
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
 * Text und mailto-Adresse der Anfrage („Angebot anfordern“). Enthält Objektart,
 * Eckdaten, vorhandene und fehlende unverzichtbare Unterlagen und die Bitte um ein
 * Angebot mit Preisen und Leistungsübersicht. Hält den Text (Betreff + Inhalt) unter
 * grenze Zeichen: Zuerst werden lange Unterlagen-Namen gekürzt, dann die Liste der
 * vorhandenen Unterlagen durch ihre Anzahl ersetzt, zuletzt die Liste der fehlenden
 * Unterlagen abgeschnitten („… und 3 weitere“).
 */
export function anfrage({ eingabe: e, vorhanden = [], adresse = "", termin = "", sprache = "de", grenze = MAIL_GRENZE }) {
  const s = sprachen(sprache);
  const t = ui(s);
  const liste = unterlagen(e, s);
  const da = new Set(vorhanden);
  const vorhandenListe = liste.filter((u) => da.has(u.id)).map((u) => u.text);
  const fehlenListe = liste.filter((u) => u.prio === 1 && !da.has(u.id)).map((u) => u.text);
  const objektName = DATEN.text[s][e.objekt === "efh" ? "objekt_efh" : "objekt_etw"];
  const adresseKurz = kuerzen(String(adresse || "").replace(/\s+/g, " ").trim(), 160);
  const terminKurz = kuerzen(String(termin || "").replace(/\s+/g, " ").trim(), 120);
  const betreff = adresseKurz ? `${t.betreff}: ${objektName}, ${kuerzen(adresseKurz, 80)}` : `${t.betreff}: ${objektName}`;

  const kopf = [t.anhang, "", t.anrede, "", t.einleitung, t.angebot_bitte, "", `${t.objekt}: ${objektName}`];
  if (adresseKurz) kopf.push(`${t.adresse}: ${adresseKurz}`);
  if (terminKurz) kopf.push(`${t.termin}: ${terminKurz}`);
  if (e.flaeche) kopf.push(`${t.flaeche}: ${String(e.flaeche).replace(".", s === "de" ? "," : ".")} m²`);
  if (e.baujahr) kopf.push(`${t.baujahr}: ${e.baujahr}`);
  if (e.heizung) kopf.push(`${t.heizung}: ${label(DATEN.eingaben.heizung, e.heizung, s)}`);
  if (e.nutzung) kopf.push(`${t.nutzung}: ${label(DATEN.eingaben.nutzung, e.nutzung, s)}`);
  if (e.region) kopf.push(`${t.region}: ${label(DATEN.eingaben.region, e.region, s)}`);
  const besonders = SCHALTER.filter((n) => e[n]).map((n) => DATEN.eingaben.schalter[n][s]);
  if (besonders.length) kopf.push(`${t.besonderheiten}: ${besonders.join("; ")}`);
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
  return { betreff, text, href, laenge: betreff.length + text.length };
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
