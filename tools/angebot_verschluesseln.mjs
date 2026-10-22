#!/usr/bin/env node
/*
 * Verschlüsselt die Inhalte der privaten Angebotsseite Kaufbegutachtung.
 *
 * Warum: Preise, Optionen, Zuschläge, Hinweise nach Baujahr, Pflichten nach dem
 * Kauf, Unterlagen und Texte sollen nicht öffentlich auf ing-bassam.de stehen.
 * Der Inhaber verschickt sie nach einer Anfrage als privaten Link. Die Seite
 * angebot/kaufbegutachtung/ ist zwar abrufbar, ihr Inhalt liegt aber nur
 * verschlüsselt in paket.js (AES-GCM, 256 Bit). Den Schlüssel enthält allein der
 * Link – im Teil nach „#“, den der Browser nie an den Server sendet.
 *
 * Die Klartext-Quelle (inhalte.json) und der Schlüssel liegen NIE im Repository.
 * Das Werkzeug verweigert Pfade innerhalb des Repositorys und gibt den Schlüssel
 * nie aus (die Ausgaben der Workflows sind öffentlich).
 *
 * Aufruf (im Hauptordner des Repositorys, Node 22 oder neuer, ohne Zusatzpakete):
 *
 *   Neuen Schlüssel anlegen (einmalig oder beim Schlüsselwechsel):
 *     node tools/angebot_verschluesseln.mjs --schluessel-erzeugen <schluessel.txt> [--ueberschreiben]
 *
 *   Inhalte verschlüsseln (nach jeder Änderung an inhalte.json):
 *     node tools/angebot_verschluesseln.mjs --daten <inhalte.json> --schluessel <schluessel.txt>
 *         [--ausgabe angebot/kaufbegutachtung/paket.js] [--links <Private_Links.md>]
 *
 *   --links schreibt zusätzlich die vier fertigen Links (Deutsch/Englisch,
 *   Wohnung/Haus) mit einer kurzen Anleitung in eine Datei außerhalb des Repositorys.
 *
 * Neu verschlüsseln mit demselben Schlüssel: Die Links bleiben gültig.
 * Neuer Schlüssel: Alle bisher verschickten Links funktionieren nicht mehr.
 *
 * tests/angebot.test.mjs prüft Paketbau, Ver- und Entschlüsselung mit Beispieldaten.
 */
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  KATEGORIEN, OBJEKTE, PAKET_VERSION, base64ZuBytes, linkBauen, schluesselErzeugen, verschluesseln,
} from "../angebot/kaufbegutachtung/angebot.js";

export const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const STANDARD_AUSGABE = resolve(WURZEL, "angebot", "kaufbegutachtung", "paket.js");
export const ADRESSE = "https://ing-bassam.de/angebot/kaufbegutachtung/";

// Zuschläge, die (auch) über ein Merkmal des Objekts zutreffen. Die Merkmale
// erscheinen auf der Seite als Kästchen beim Zuschlag.
export const PREIS_SCHALTER = {
  gross_etw: { name: "maisonette", objekt: "etw", de: "Maisonette oder Dachgeschoss", en: "Maisonette or attic flat" },
  keller: { name: "vollkeller", objekt: "efh", de: "Voll unterkellert", en: "Full basement" },
  gross_efh: { name: "einlieger", objekt: "efh", de: "Mit Einliegerwohnung", en: "With a granny flat (Einliegerwohnung)" },
};
// Texte, die die Seite aus inhalte.json braucht.
const TEXTE = ["objekt_etw", "objekt_efh", "objekt_etw_unter", "objekt_efh_unter", "pauschal", "ausserhalb", "ablauf",
  "grenzen", "beauftragen", "rechtsstand", "prio"];

const kopie = (wert) => JSON.parse(JSON.stringify(wert));
const zahl = (x) => typeof x === "number" && Number.isFinite(x);

/** Liegt der Pfad im Repository? (Dort dürfen Schlüssel und Klartext nie liegen.) */
export function imRepository(pfad, wurzel = WURZEL) {
  const teil = relative(wurzel, resolve(pfad));
  return teil === "" || (!teil.startsWith("..") && !isAbsolute(teil));
}

/**
 * inhalte.json → Inhalt des Pakets. Übernimmt Preise, Optionen, Zuschläge,
 * Eingaben, Regeln, Unterlagen und Texte, ergänzt die Merkmale der Zuschläge
 * und prüft alle Verweise. Wirft einen Fehler mit allen Befunden.
 */
export function paketBauen(inhalte) {
  const d = kopie(inhalte);
  const fehler = [];
  const pruefe = (bedingung, text) => { if (!bedingung) fehler.push(text); };

  pruefe(zahl(d.mwst) && d.mwst > 0 && d.mwst < 1, "mwst muss eine Zahl zwischen 0 und 1 sein (z. B. 0.19)");
  pruefe(zahl(d.stundensatz_netto) && d.stundensatz_netto > 0, "stundensatz_netto fehlt");
  pruefe(d.kontakt && /@/.test(d.kontakt.email || ""), "kontakt.email fehlt");
  for (const s of ["de", "en"]) pruefe(d.stand && d.stand[s], `stand.${s} fehlt`);

  const optionen = d.optionen || {};
  for (const [id, o] of Object.entries(optionen)) {
    const fest = zahl(o.netto) && o.netto > 0;
    const spanne = zahl(o.netto_von) && zahl(o.netto_bis) && o.netto_von > 0 && o.netto_bis >= o.netto_von;
    // Kostenlose Extras: "kostenlos": true und/oder "netto": 0 – die Seite zeigt dann „kostenlos“.
    const frei = (o.kostenlos === true && o.netto === undefined) || (o.netto === 0 && o.netto_von === undefined);
    pruefe(fest || spanne || frei, `Option ${id}: netto oder netto_von/netto_bis fehlt`);
    pruefe(o.kostenlos === undefined || typeof o.kostenlos === "boolean", `Option ${id}: kostenlos muss true oder false sein`);
    pruefe(o.kostenlos !== true || (!fest && !spanne), `Option ${id}: kostenlos, aber mit Preis`);
    for (const s of ["de", "en"]) pruefe(o[s] && o[s].name && o[s].text, `Option ${id}: Name/Text ${s} fehlt`);
  }

  const eingaben = d.eingaben || {};
  const schalter = { ...(eingaben.schalter || {}) };
  for (const objekt of OBJEKTE) {
    const p = d.pakete && d.pakete[objekt];
    if (!p) { fehler.push(`pakete.${objekt} fehlt`); continue; }
    pruefe(p.grund && zahl(p.grund.netto) && p.grund.netto > 0, `pakete.${objekt}.grund.netto fehlt`);
    for (const s of ["de", "en"]) pruefe(p.grund && p.grund[s] && p.grund[s].name && p.grund[s].text, `pakete.${objekt}.grund.${s} fehlt`);
    for (const z of p.zuschlaege || []) {
      const ps = PREIS_SCHALTER[z.id];
      if (!z.schalter && ps) z.schalter = ps.name;
      if (z.schalter && !schalter[z.schalter] && ps) schalter[z.schalter] = { objekt: ps.objekt, de: ps.de, en: ps.en };
      if (z.schalter && schalter[z.schalter]) schalter[z.schalter].preis = true;
      pruefe(zahl(z.netto) && z.netto > 0, `Zuschlag ${z.id}: netto fehlt`);
      pruefe(Boolean(z.schalter) || (z.auto && zahl(z.auto.flaeche_ab)), `Zuschlag ${z.id}: weder Wohnfläche noch Merkmal`);
      pruefe(!z.schalter || Boolean(schalter[z.schalter]), `Zuschlag ${z.id}: Merkmal ${z.schalter} unbekannt`);
      for (const s of ["de", "en"]) pruefe(z[s] && z[s].name, `Zuschlag ${z.id}: Name ${s} fehlt`);
    }
    p.zuschlaege = p.zuschlaege || [];
    for (const id of p.optionen || []) pruefe(Boolean(optionen[id]), `pakete.${objekt}: Option ${id} unbekannt`);
  }
  eingaben.schalter = schalter;
  for (const [name, x] of Object.entries(schalter)) {
    pruefe(OBJEKTE.includes(x.objekt) && x.de && x.en, `Merkmal ${name}: objekt/de/en fehlt`);
  }

  const ids = (feld) => new Set((eingaben[feld] || []).map((x) => x.id));
  const auswahl = { heizung: ids("heizung"), nutzung: ids("nutzung"), region: ids("region") };
  for (const feld of Object.keys(auswahl)) pruefe(auswahl[feld].size > 0, `eingaben.${feld} fehlt`);
  const regelIds = new Set();
  for (const r of d.regeln || []) {
    const ort = `Regel ${r.id}`;
    pruefe(r.id && !regelIds.has(r.id), `${ort}: ID fehlt oder doppelt`);
    regelIds.add(r.id);
    pruefe(KATEGORIEN.includes(r.kategorie), `${ort}: Kategorie ${r.kategorie} unbekannt`);
    pruefe(["etw", "efh", "beide"].includes(r.objekt), `${ort}: objekt ${r.objekt} unbekannt`);
    for (const feld of Object.keys(auswahl)) {
      for (const wert of r[feld] || []) pruefe(auswahl[feld].has(wert), `${ort}: ${feld} ${wert} unbekannt`);
    }
    for (const id of r.empfiehlt || []) pruefe(Boolean(optionen[id]), `${ort}: empfiehlt unbekannte Option ${id}`);
    if (r.von !== undefined && r.bis !== undefined) pruefe(r.von <= r.bis, `${ort}: von > bis`);
    for (const s of ["de", "en"]) pruefe(r[s] && r[s].titel && r[s].text, `${ort}: Titel/Text ${s} fehlt`);
    pruefe(r.quelle && r.quelle.titel, `${ort}: Quelle fehlt`);
    pruefe(!r.quelle || !r.quelle.url || r.quelle.url.startsWith("https://"), `${ort}: Quelle muss mit https:// beginnen`);
  }
  pruefe(regelIds.size > 0, "regeln fehlen");
  for (const objekt of OBJEKTE) {
    const liste = (d.unterlagen && d.unterlagen[objekt]) || [];
    pruefe(liste.length > 0, `unterlagen.${objekt} fehlt`);
    const gesehen = new Set();
    for (const u of liste) {
      pruefe(u.id && !gesehen.has(u.id), `Unterlage ${objekt}/${u.id}: ID fehlt oder doppelt`);
      gesehen.add(u.id);
      pruefe([1, 2, 3].includes(u.prio), `Unterlage ${objekt}/${u.id}: prio 1–3`);
      pruefe(u.de && u.en && u.wo_de && u.wo_en, `Unterlage ${objekt}/${u.id}: Texte fehlen`);
    }
  }
  for (const s of ["de", "en"]) {
    for (const k of TEXTE) pruefe(d.text && d.text[s] && d.text[s][k] !== undefined, `text.${s}.${k} fehlt`);
  }
  pruefe(d.text && Array.isArray(d.text.de.ablauf) && d.text.de.ablauf.length >= 4, "text.de.ablauf braucht 4 Schritte");

  if (fehler.length) throw new Error(`inhalte.json ist nicht vollständig:\n- ${fehler.join("\n- ")}`);

  const text = {};
  for (const s of ["de", "en"]) text[s] = Object.fromEntries(TEXTE.map((k) => [k, d.text[s][k]]));
  return {
    format: PAKET_VERSION,
    stand: d.stand,
    mwst: d.mwst,
    stundensatz_netto: d.stundensatz_netto,
    kontakt: { email: d.kontakt.email, telefon: d.kontakt.telefon || "" },
    pakete: d.pakete,
    optionen,
    eingaben,
    regeln: d.regeln,
    unterlagen: d.unterlagen,
    text,
  };
}

/** Inhalt von paket.js (LF, ohne Klartext). */
export function paketDatei(paket) {
  return [
    "// Kaufbegutachtung – verschlüsseltes Inhaltspaket der privaten Angebotsseite.",
    "// AES-GCM mit 256-Bit-Schlüssel; iv und daten sind Base64. Ohne den Schlüssel aus",
    "// dem privaten Link ist der Inhalt nicht lesbar.",
    "// Erzeugt mit tools/angebot_verschluesseln.mjs – nicht von Hand ändern.",
    `export const PAKET = ${JSON.stringify({ v: paket.v, iv: paket.iv, daten: paket.daten }, null, 2)};`,
    "",
  ].join("\n");
}

/** Die vier privaten Links. */
export function links(schluessel, basis = ADRESSE) {
  return [
    { sprache: "Deutsch", objekt: "Wohnung", link: linkBauen({ basis, schluessel, objekt: "etw", sprache: "de" }) },
    { sprache: "Deutsch", objekt: "Haus", link: linkBauen({ basis, schluessel, objekt: "efh", sprache: "de" }) },
    { sprache: "Englisch", objekt: "Wohnung (flat)", link: linkBauen({ basis, schluessel, objekt: "etw", sprache: "en" }) },
    { sprache: "Englisch", objekt: "Haus (house)", link: linkBauen({ basis, schluessel, objekt: "efh", sprache: "en" }) },
  ];
}

/** Private_Links.md: Links und Anleitung (enthält den Schlüssel – nur außerhalb des Repositorys). */
export function linksDatei({ schluessel, datenPfad, schluesselPfad, linksPfad }) {
  const zeilen = links(schluessel).map((x) => `| ${x.sprache} | ${x.objekt} | ${x.link} |`);
  return `# Private Links – Kaufbegutachtung: Preise und Optionen

**Vertraulich.** Jeder Link enthält den Schlüssel (der Teil nach \`#k=\`). Wer den Link hat, sieht
Preise, Optionen, Hinweise und Unterlagenliste. Nur an Interessenten nach einer Anfrage schicken,
nie öffentlich posten und diese Datei nie ins Repository legen.

Die Links funktionieren erst, wenn der Pull Request mit der Angebotsseite gemergt und die Website
ausgeliefert ist (Workflow „Website ausliefern“).

| Sprache | Objekt | Link |
|---|---|---|
${zeilen.join("\n")}

Der Teil \`&o=wohnung\` oder \`&o=haus\` wählt nur vor, welches Objekt beim Öffnen gezeigt wird;
\`&l=de\` oder \`&l=en\` die Sprache. Beides lässt sich auf der Seite umschalten.

## Preise oder Texte geändert – neu verschlüsseln

1. \`inhalte.json\` ändern (Preise netto, Optionen, Regeln, Unterlagen, Texte).
2. Im Hauptordner des Repositorys ausführen:

   \`\`\`
   node tools/angebot_verschluesseln.mjs --daten "${datenPfad}" --schluessel "${schluesselPfad}"
   \`\`\`

3. Die geänderte Datei \`angebot/kaufbegutachtung/paket.js\` per Pull Request einreichen und mergen.
   Der Schlüssel bleibt gleich – alle verschickten Links funktionieren weiter und zeigen die neuen Preise.

## Schlüssel wechseln (z. B. wenn ein Link in falsche Hände geraten ist)

1. Neuen Schlüssel erzeugen (der alte wird überschrieben):

   \`\`\`
   node tools/angebot_verschluesseln.mjs --schluessel-erzeugen "${schluesselPfad}" --ueberschreiben
   \`\`\`

2. Neu verschlüsseln und diese Datei mit den neuen Links neu schreiben:

   \`\`\`
   node tools/angebot_verschluesseln.mjs --daten "${datenPfad}" --schluessel "${schluesselPfad}" --links "${linksPfad}"
   \`\`\`

3. \`paket.js\` per Pull Request einreichen und mergen. Danach funktionieren **alle alten Links nicht mehr**;
   wer noch einen alten Link hat, sieht nur den Hinweis „Dieser Link ist nicht vollständig“.
`;
}

function schreiben(pfad, inhalt) {
  mkdirSync(dirname(pfad), { recursive: true });
  writeFileSync(pfad, inhalt, { encoding: "utf8" });
}

function argumente(liste) {
  const a = { ueberschreiben: false };
  for (let i = 0; i < liste.length; i += 1) {
    const name = liste[i];
    if (name === "--ueberschreiben") a.ueberschreiben = true;
    else if (["--daten", "--schluessel", "--ausgabe", "--links", "--schluessel-erzeugen"].includes(name)) {
      const wert = liste[i + 1];
      if (!wert || wert.startsWith("--")) throw new Error(`${name} braucht einen Pfad`);
      a[name.slice(2).replace(/-(\w)/g, (_, x) => x.toUpperCase())] = resolve(wert);
      i += 1;
    } else throw new Error(`Unbekannte Angabe: ${name}`);
  }
  return a;
}

function schluesselLesen(pfad) {
  if (!existsSync(pfad)) throw new Error(`Schlüsseldatei fehlt: ${pfad} (erst --schluessel-erzeugen ausführen)`);
  const text = readFileSync(pfad, "utf8").trim();
  const bytes = base64ZuBytes(text);
  if (!bytes || bytes.length !== 32 || !/^[A-Za-z0-9_-]{43}$/.test(text)) {
    throw new Error("Schlüsseldatei ungültig: erwartet werden 32 Bytes als Base64url (43 Zeichen).");
  }
  return text;
}

export async function main(liste = process.argv.slice(2)) {
  const a = argumente(liste);
  for (const [name, pfad] of [["--schluessel", a.schluessel], ["--schluessel-erzeugen", a.schluesselErzeugen],
    ["--daten", a.daten], ["--links", a.links]]) {
    if (pfad && imRepository(pfad)) {
      throw new Error(`${name}: ${pfad} liegt im Repository. Schlüssel, Klartext und Links gehören nach außerhalb.`);
    }
  }

  if (a.schluesselErzeugen) {
    if (existsSync(a.schluesselErzeugen) && !a.ueberschreiben) {
      throw new Error(`${a.schluesselErzeugen} gibt es schon. Mit --ueberschreiben ersetzen (alte Links werden ungültig).`);
    }
    schreiben(a.schluesselErzeugen, `${schluesselErzeugen()}\n`);
    console.log(`Neuer Schlüssel gespeichert: ${a.schluesselErzeugen} (Inhalt wird nicht angezeigt).`);
    if (!a.daten) return 0;
  }

  if (!a.daten || !a.schluessel) {
    throw new Error("Aufruf: --daten <inhalte.json> --schluessel <schluessel.txt> [--ausgabe <paket.js>] [--links <Private_Links.md>]");
  }
  const schluessel = schluesselLesen(a.schluessel);
  const inhalt = paketBauen(JSON.parse(readFileSync(a.daten, "utf8")));
  const paket = await verschluesseln(inhalt, schluessel);
  const ausgabe = a.ausgabe || STANDARD_AUSGABE;
  schreiben(ausgabe, paketDatei(paket));
  const optionen = Object.keys(inhalt.optionen).length;
  console.log(`Paket geschrieben: ${imRepository(ausgabe) ? relative(WURZEL, ausgabe) : ausgabe} (${inhalt.regeln.length} Regeln, ${optionen} Optionen, `
    + `${Math.round(paket.daten.length / 1024)} KB verschlüsselt).`);
  if (a.links) {
    schreiben(a.links, linksDatei({ schluessel, datenPfad: a.daten, schluesselPfad: a.schluessel, linksPfad: a.links }));
    console.log(`Links geschrieben: ${a.links} (Inhalt wird nicht angezeigt).`);
  }
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().then((code) => process.exit(code)).catch((fehler) => {
    console.error(`FEHLER: ${fehler.message}`);
    process.exit(1);
  });
}
