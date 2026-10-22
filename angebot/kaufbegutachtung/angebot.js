/**
 * Private Angebotsseite Kaufbegutachtung – Rechenlogik ohne Inhalte.
 *
 * Preise, Optionen, Zuschläge, Hinweisregeln, Pflichten, Unterlagen und Texte
 * stehen NICHT hier, sondern nur verschlüsselt in paket.js (AES-GCM, 256 Bit).
 * Den Schlüssel enthält allein der private Link, den das Büro nach einer Anfrage
 * per E-Mail verschickt – im Teil nach „#“, den der Browser nie an den Server
 * sendet: …/angebot/kaufbegutachtung/#k=<Schlüssel>&o=wohnung|haus&l=de|en
 *
 * Diese Datei enthält nur, was öffentlich sein darf:
 *   - Link lesen und Paket entschlüsseln (WebCrypto, im Browser und in Node),
 *   - Eingaben prüfen,
 *   - Preis berechnen: Grundpaket + zutreffende Zuschläge + gewählte Extras,
 *     alles in Cent, Bruttopreis aus dem Nettopreis (Umsatzsteuer aus dem Paket),
 *   - passende Hinweise und Unterlagen auswählen (Bedingungen UND-verknüpft),
 *   - den Text der E-Mail „Auswahl senden“ bauen.
 *
 * Das Werkzeug tools/angebot_verschluesseln.mjs nutzt dieselben Funktionen zum
 * Verschlüsseln; tests/angebot.test.mjs prüft beides mit Beispieldaten.
 */

export const PAKET_VERSION = 1;
export const KATEGORIEN = ["pflicht", "miete", "pruefen", "foerderung"];
export const OBJEKTE = ["etw", "efh"];
export const HOECHSTENS_HINWEISE = 6;
export const MAIL_GRENZE = 1800;
const SCHLUESSEL_BYTES = 32;
const IV_BYTES = 12;

const sprachen = (sprache) => (sprache === "en" ? "en" : "de");

function ersetzen(vorlage, werte) {
  return String(vorlage).replace(/\{(\w+)\}/g, (_, name) => (name in werte ? String(werte[name]) : `{${name}}`));
}
export { ersetzen };

// ------------------------------------------------------------- Base64

/** Bytes → Base64 (Standardalphabet, mit „=“). */
export function bytesZuBase64(bytes) {
  let binaer = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binaer += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binaer);
}

/** Bytes → Base64url (für Links: „-“ und „_“, ohne „=“). */
export function bytesZuBase64url(bytes) {
  return bytesZuBase64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Base64 oder Base64url → Bytes; null bei ungültigem Text. */
export function base64ZuBytes(text) {
  const sauber = String(text || "").trim().replace(/-/g, "+").replace(/_/g, "/");
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(sauber)) return null;
  const aufgefuellt = sauber + "=".repeat((4 - (sauber.length % 4)) % 4);
  try {
    const binaer = atob(aufgefuellt);
    const bytes = new Uint8Array(binaer.length);
    for (let i = 0; i < binaer.length; i += 1) bytes[i] = binaer.charCodeAt(i);
    return bytes;
  } catch {
    return null;
  }
}

// --------------------------------------------------------------- Link

const OBJEKT_NAMEN = { wohnung: "etw", flat: "etw", etw: "etw", haus: "efh", house: "efh", efh: "efh" };

/**
 * Liest den Teil nach „#“: k = Schlüssel, o = wohnung|haus, l = de|en.
 * Fehlt etwas, ist der Wert null bzw. "" (Schlüssel).
 */
export function linkLesen(fragment) {
  const text = String(fragment || "").replace(/^#/, "");
  const werte = new URLSearchParams(text);
  const objekt = OBJEKT_NAMEN[(werte.get("o") || "").toLowerCase()] || null;
  const l = (werte.get("l") || "").toLowerCase();
  return { schluessel: (werte.get("k") || "").trim(), objekt, sprache: l === "de" || l === "en" ? l : null };
}

/** Baut den Teil nach „#“ (oder mit basis den ganzen Link) für Schlüssel, Objektart und Sprache. */
export function linkBauen({ basis = "", schluessel, objekt = "etw", sprache = "de" }) {
  const o = objekt === "efh" ? "haus" : "wohnung";
  return `${basis}#k=${schluessel}&o=${o}&l=${sprachen(sprache)}`;
}

// ------------------------------------------------------------ Krypto

function subtle() {
  const krypto = globalThis.crypto;
  if (!krypto || !krypto.subtle) throw new Error("WebCrypto fehlt");
  return krypto.subtle;
}

/** Schlüssel aus dem Link (Base64url, 32 Bytes) → CryptoKey; null, wenn er nicht passt. */
export async function schluesselImportieren(text, verwendung = ["decrypt"]) {
  const bytes = typeof text === "string" ? base64ZuBytes(text) : text;
  if (!bytes || bytes.length !== SCHLUESSEL_BYTES) return null;
  return subtle().importKey("raw", bytes, { name: "AES-GCM" }, false, verwendung);
}

/** Neuer zufälliger Schlüssel (32 Bytes) als Base64url-Text. */
export function schluesselErzeugen() {
  return bytesZuBase64url(globalThis.crypto.getRandomValues(new Uint8Array(SCHLUESSEL_BYTES)));
}

/** Daten (JSON-fähig) → Paket {v, iv, daten} mit frischem Zufalls-IV. */
export async function verschluesseln(daten, schluesselText) {
  const schluessel = await schluesselImportieren(schluesselText, ["encrypt"]);
  if (!schluessel) throw new Error("Schlüssel ungültig: erwartet werden 32 Bytes als Base64url.");
  const iv = globalThis.crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const klartext = new TextEncoder().encode(JSON.stringify(daten));
  const chiffrat = new Uint8Array(await subtle().encrypt({ name: "AES-GCM", iv }, schluessel, klartext));
  return { v: PAKET_VERSION, iv: bytesZuBase64(iv), daten: bytesZuBase64(chiffrat) };
}

/** Paket + Schlüssel aus dem Link → Inhalte; null bei fehlendem oder falschem Schlüssel. */
export async function entschluesseln(paket, schluesselText) {
  if (!paket || paket.v !== PAKET_VERSION) return null;
  const iv = base64ZuBytes(paket.iv);
  const chiffrat = base64ZuBytes(paket.daten);
  if (!iv || iv.length !== IV_BYTES || !chiffrat || !chiffrat.length) return null;
  const schluessel = await schluesselImportieren(schluesselText);
  if (!schluessel) return null;
  try {
    const klartext = await subtle().decrypt({ name: "AES-GCM", iv }, schluessel, chiffrat);
    return JSON.parse(new TextDecoder().decode(klartext));
  } catch {
    return null;
  }
}

// ----------------------------------------------------------- Beträge

const mwstProzent = (mwst) => Math.round(Number(mwst) * 100);

/** Euro → Cent (ganzzahlig). */
export const cent = (euroBetrag) => Math.round(Number(euroBetrag) * 100);

/** Bruttobetrag in Cent aus dem Nettobetrag in Cent. */
export function brutto(nettoCent, mwst) {
  return Math.round((nettoCent * (100 + mwstProzent(mwst))) / 100);
}

/** Cent → Betrag als Text: deutsch mit Komma und Eurozeichen hinten, englisch mit Punkt und Eurozeichen vorn. */
export function euro(betragCent, sprache = "de") {
  const minus = betragCent < 0 ? "−" : "";
  const c = Math.abs(Math.round(betragCent));
  const ganz = String(Math.floor(c / 100));
  const rest = String(c % 100).padStart(2, "0");
  if (sprachen(sprache) === "en") return `${minus}€${ganz.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${rest}`;
  return `${minus}${ganz.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${rest} €`;
}

/** Betrag oder Spanne (von – bis), wenn eine Leistung nach Aufwand abgerechnet wird. */
export function euroSpanne(von, bis, sprache = "de") {
  if (von === bis) return euro(von, sprache);
  if (sprachen(sprache) === "en") return `${euro(von, "en")} – ${euro(bis, "en")}`;
  return `${euro(von, "de").replace(/ €$/, "")} – ${euro(bis, "de")}`;
}

// ---------------------------------------------------------- Eingaben

function zahlLesen(wert) {
  if (wert === "" || wert === null || wert === undefined) return null;
  const zahl = Number(String(wert).trim().replace(",", "."));
  return Number.isFinite(zahl) ? zahl : NaN;
}

/** Alle Merkmale (Kästchen) des Pakets mit der Objektart, für die sie gelten. */
export function schalterListe(daten) {
  return Object.entries(daten.eingaben.schalter).map(([name, s]) => ({ name, ...s }));
}

/**
 * Formularwerte → geprüfte Eingabe. Ungültige Zahlen gelten als leer und kommen
 * als Fehlercode zurück; Merkmale zählen nur für ihre Objektart.
 */
export function eingabeLesen(roh = {}, daten) {
  const fehler = {};
  const objekt = roh.objekt === "efh" ? "efh" : "etw";
  let flaeche = zahlLesen(roh.flaeche);
  if (flaeche !== null && (Number.isNaN(flaeche) || flaeche < 10 || flaeche > 2000)) {
    fehler.flaeche = true;
    flaeche = null;
  }
  let baujahr = zahlLesen(roh.baujahr);
  if (baujahr !== null && (Number.isNaN(baujahr) || !Number.isInteger(baujahr) || baujahr < 1800 || baujahr > 2030)) {
    fehler.baujahr = true;
    baujahr = null;
  }
  const auswahl = (id, liste) => (liste.some((x) => x.id === id) ? id : "");
  const schalter = {};
  for (const s of schalterListe(daten)) schalter[s.name] = Boolean(roh.schalter && roh.schalter[s.name]) && s.objekt === objekt;
  return {
    eingabe: {
      objekt,
      flaeche,
      baujahr,
      heizung: auswahl(roh.heizung, daten.eingaben.heizung),
      nutzung: auswahl(roh.nutzung, daten.eingaben.nutzung),
      region: auswahl(roh.region, daten.eingaben.region),
      schalter,
    },
    fehler,
  };
}

// ------------------------------------------------------------- Preis

/** Zuschläge der Objektart mit Angabe, ob und warum sie zutreffen (Fläche oder Merkmal). */
export function zuschlaegeFuer(daten, e) {
  return daten.pakete[e.objekt].zuschlaege.map((z) => {
    const abFlaeche = z.auto && z.auto.flaeche_ab !== undefined ? z.auto.flaeche_ab : null;
    const durchFlaeche = abFlaeche !== null && e.flaeche !== null && e.flaeche !== undefined && e.flaeche >= abFlaeche;
    const durchSchalter = Boolean(z.schalter && e.schalter && e.schalter[z.schalter]);
    return { id: z.id, eintrag: z, aktiv: durchFlaeche || durchSchalter, grund: durchFlaeche ? "flaeche" : durchSchalter ? "schalter" : null };
  });
}

/** Extras der Objektart in der Reihenfolge des Pakets. */
export function optionenFuer(daten, objekt) {
  return daten.pakete[objekt === "efh" ? "efh" : "etw"].optionen.map((id) => ({ id, ...daten.optionen[id] }));
}

/** Netto-Spanne einer Option in Cent (fester Preis: von = bis). */
export function optionNetto(option) {
  if (option.netto_von !== undefined) return [cent(option.netto_von), cent(option.netto_bis)];
  return [cent(option.netto), cent(option.netto)];
}

/**
 * Preis aus Grundpaket, zutreffenden Zuschlägen und gewählten Extras.
 * Alle Beträge in Cent. Der Gesamtbruttopreis wird aus der Nettosumme berechnet,
 * die Umsatzsteuer ist die Differenz.
 */
export function preisBerechnen(daten, e, gewaehlt = []) {
  const wahl = new Set(gewaehlt);
  const paket = daten.pakete[e.objekt];
  const posten = [];
  const dazu = (art, id, eintrag, von, bis, extra = {}) => posten.push({
    art, id, eintrag, netto_von: von, netto_bis: bis, brutto_von: brutto(von, daten.mwst), brutto_bis: brutto(bis, daten.mwst), ...extra,
  });
  const grund = cent(paket.grund.netto);
  dazu("grund", paket.grund.id, paket.grund, grund, grund);
  for (const z of zuschlaegeFuer(daten, e)) {
    if (z.aktiv) dazu("zuschlag", z.id, z.eintrag, cent(z.eintrag.netto), cent(z.eintrag.netto), { grund: z.grund });
  }
  for (const o of optionenFuer(daten, e.objekt)) {
    if (wahl.has(o.id)) {
      const [von, bis] = optionNetto(o);
      dazu("option", o.id, o, von, bis);
    }
  }
  const summe = (feld, art) => posten.filter((p) => !art || p.art === art).reduce((s, p) => s + p[feld], 0);
  const nettoVon = summe("netto_von");
  const nettoBis = summe("netto_bis");
  const bruttoVon = brutto(nettoVon, daten.mwst);
  const bruttoBis = brutto(nettoBis, daten.mwst);
  return {
    posten,
    mwst_prozent: mwstProzent(daten.mwst),
    netto_von: nettoVon,
    netto_bis: nettoBis,
    brutto_von: bruttoVon,
    brutto_bis: bruttoBis,
    ust_von: bruttoVon - nettoVon,
    ust_bis: bruttoBis - nettoBis,
    spanne: nettoVon !== nettoBis,
    // Anteile für die Balkengrafik (brutto): obere Grenze und – bei Spannen – untere Grenze
    anteile: { grund: summe("brutto_bis", "grund"), zuschlag: summe("brutto_bis", "zuschlag"), option: summe("brutto_bis", "option") },
    anteile_von: { grund: summe("brutto_von", "grund"), zuschlag: summe("brutto_von", "zuschlag"), option: summe("brutto_von", "option") },
  };
}

// --------------------------------------------- Hinweise und Unterlagen

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
  for (const [name, an] of Object.entries(e.schalter || {})) {
    if (eintrag[name] === true && !an) return false;
  }
  return true;
}

// Abkürzungen, nach denen ein Punkt keinen Satz beendet.
const ABKUERZUNG = /(?:^|[\s(])(?:z|B|d|h|u|a|o|g|e|i|ca|bzw|Nr|Abs|inkl|Std|max|min|ggf|evtl|vgl|bspw|usw|etc|approx|incl|no|St|Dr|Mio|Tsd|ff|S)\.$/i;

/** Die ersten saetze Sätze eines Textes (für die kompakte Ansicht). */
export function kurzfassung(text, saetze = 2) {
  const t = String(text || "").trim();
  const ende = /[.!?](?=\s+[A-ZÄÖÜ„"(0-9])/g;
  let gezaehlt = 0;
  let treffer;
  while ((treffer = ende.exec(t)) !== null) {
    if (ABKUERZUNG.test(t.slice(0, treffer.index + 1))) continue;
    gezaehlt += 1;
    if (gezaehlt === saetze) return t.slice(0, treffer.index + 1);
  }
  return t;
}

function regelText(regel, sprache) {
  const t = regel[sprachen(sprache)];
  return {
    id: regel.id,
    kategorie: regel.kategorie,
    titel: t.titel,
    text: t.text,
    kurz: kurzfassung(t.text, 2),
    quelle: { titel: regel.quelle.titel, url: regel.quelle.url || "" },
  };
}

/**
 * Passende Hinweise: alle, nach Kategorie sortiert (Pflichten, Vermietung,
 * Prüfschwerpunkte, Gut zu wissen), dazu die ersten höchstens sechs für die
 * kompakte Ansicht und die Extras, die passende Regeln empfehlen.
 */
export function hinweise(daten, e, sprache = "de") {
  const passend = daten.regeln
    .map((regel, reihenfolge) => ({ regel, reihenfolge }))
    .filter(({ regel }) => bedingungErfuellt(regel, e))
    .sort((a, b) => KATEGORIEN.indexOf(a.regel.kategorie) - KATEGORIEN.indexOf(b.regel.kategorie) || a.reihenfolge - b.reihenfolge)
    .map(({ regel }) => regel);
  const alle = passend.map((r) => regelText(r, sprache));
  const empfohlen = new Set(passend.flatMap((r) => r.empfiehlt || []));
  return { alle, kompakt: alle.slice(0, HOECHSTENS_HINWEISE), anzahl: alle.length, empfohlen };
}

/** Unterlagen für Objektart und Eingaben, nach Priorität sortiert (1 vor 2 vor 3). */
export function unterlagen(daten, e, sprache = "de") {
  const s = sprachen(sprache);
  return daten.unterlagen[e.objekt]
    .map((u, reihenfolge) => ({ u, reihenfolge }))
    .filter(({ u }) => bedingungErfuellt(u, e))
    .sort((a, b) => a.u.prio - b.u.prio || a.reihenfolge - b.reihenfolge)
    .map(({ u }) => ({ id: u.id, prio: u.prio, text: u[s], wo: u[`wo_${s}`] }));
}

/** Kommaliste (außerhalb von Klammern) → Aufzählungspunkte, erster Buchstabe groß. */
export function aufzaehlung(text) {
  const teile = [];
  let tiefe = 0;
  let aktuell = "";
  const t = String(text || "").trim().replace(/\.$/, "");
  for (let i = 0; i < t.length; i += 1) {
    const z = t[i];
    if (z === "(") tiefe += 1;
    if (z === ")") tiefe = Math.max(0, tiefe - 1);
    if (z === "," && tiefe === 0 && t[i + 1] === " ") {
      teile.push(aktuell);
      aktuell = "";
      i += 1;
      continue;
    }
    aktuell += z;
  }
  teile.push(aktuell);
  return teile.map((x) => x.trim()).filter(Boolean).map((x) => x[0].toUpperCase() + x.slice(1));
}

// ------------------------------------------------------------ E-Mail

function label(liste, id, sprache) {
  const eintrag = liste.find((x) => x.id === id);
  return eintrag ? eintrag[sprachen(sprache)] : "";
}

function kuerzen(text, laenge) {
  return text.length <= laenge ? text : `${text.slice(0, laenge - 1).trimEnd()}…`;
}

const einzeilig = (text, laenge) => kuerzen(String(text || "").replace(/\s+/g, " ").trim(), laenge);

/**
 * Text und mailto-Adresse für „Auswahl senden“: Objekt, Eckdaten, gewählte
 * Leistungen mit Bruttopreisen, Gesamtpreis brutto, Termine, vorhandene und
 * fehlende unverzichtbare Unterlagen und die Bitte um das verbindliche Angebot.
 * t sind die Texte der Oberfläche (oberflaeche.js, Abschnitt mail).
 *
 * Damit E-Mail-Programme den Link sicher öffnen, bleibt der Text (Betreff +
 * Inhalt) unter grenze Zeichen: Zuerst werden lange Unterlagen-Namen gekürzt,
 * dann die Liste der vorhandenen Unterlagen durch ihre Anzahl ersetzt, zuletzt
 * die Liste der fehlenden Unterlagen abgeschnitten („… und 3 weitere“).
 */
export function anfrage({ daten, t, eingabe: e, gewaehlt = [], vorhanden = [], felder = {}, sprache = "de", grenze = MAIL_GRENZE }) {
  const s = sprachen(sprache);
  const preis = preisBerechnen(daten, e, gewaehlt);
  const liste = unterlagen(daten, e, s);
  const da = new Set(vorhanden);
  const vorhandenListe = liste.filter((u) => da.has(u.id)).map((u) => u.text);
  const fehlenListe = liste.filter((u) => u.prio === 1 && !da.has(u.id)).map((u) => u.text);
  const objektName = daten.text[s][e.objekt === "efh" ? "objekt_efh" : "objekt_etw"];
  const adresse = einzeilig(felder.adresse, 160);
  const termin = einzeilig(felder.termin, 120);
  const notar = einzeilig(felder.notar, 120);
  const betreff = adresse ? `${t.betreff}: ${objektName}, ${kuerzen(adresse, 80)}` : `${t.betreff}: ${objektName}`;

  const kopf = [t.anhang, "", t.anrede, "", t.einleitung, "", `${t.objekt}: ${objektName}`];
  if (adresse) kopf.push(`${t.adresse}: ${adresse}`);
  if (e.flaeche) kopf.push(`${t.flaeche}: ${String(e.flaeche).replace(".", s === "de" ? "," : ".")} m²`);
  if (e.baujahr) kopf.push(`${t.baujahr}: ${e.baujahr}`);
  if (e.heizung) kopf.push(`${t.heizung}: ${label(daten.eingaben.heizung, e.heizung, s)}`);
  if (e.nutzung) kopf.push(`${t.nutzung}: ${label(daten.eingaben.nutzung, e.nutzung, s)}`);
  if (e.region) kopf.push(`${t.region}: ${label(daten.eingaben.region, e.region, s)}`);
  const besonders = schalterListe(daten).filter((x) => e.schalter && e.schalter[x.name]).map((x) => x[s]);
  if (besonders.length) kopf.push(`${t.besonderheiten}: ${besonders.join("; ")}`);
  kopf.push("", `${t.leistungen}:`);
  for (const p of preis.posten) {
    const vorsatz = p.art === "zuschlag" ? `${t.zuschlag}: ` : "";
    kopf.push(`- ${vorsatz}${p.eintrag[s].name}: ${euroSpanne(p.brutto_von, p.brutto_bis, s)}`);
  }
  kopf.push(`${ersetzen(t.gesamt, { mwst: preis.mwst_prozent })}: ${euroSpanne(preis.brutto_von, preis.brutto_bis, s)}`);
  if (termin || notar) kopf.push("");
  if (termin) kopf.push(`${t.termin}: ${termin}`);
  if (notar) kopf.push(`${t.notar}: ${notar}`);
  const fuss = ["", t.bitte, "", t.gruss];

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
  for (const stufe of [{ laenge: 70 }, { laenge: 70, nurAnzahl: true }, { laenge: 50, nurAnzahl: true }]) {
    if (passt(text)) break;
    text = bauen(stufe);
  }
  for (let n = fehlenListe.length - 1; !passt(text) && n >= 0; n -= 1) {
    text = bauen({ laenge: 50, nurAnzahl: true, fehlenHoechstens: n });
  }
  const crlf = text.replace(/\n/g, "\r\n");
  const href = `mailto:${daten.kontakt.email}?subject=${encodeURIComponent(betreff)}&body=${encodeURIComponent(crlf)}`;
  return { betreff, text, href, laenge: betreff.length + text.length, preis };
}
