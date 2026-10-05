/**
 * Gewährleistungsfristen-Rechner – Rechenkern ohne Browser-Abhängigkeiten.
 *
 * Rechnet mit UTC-Kalendertagen (keine Zeitzonen- oder Sommerzeiteffekte).
 * Alle Daten sind ISO-Zeichenketten "JJJJ-MM-TT"; intern werden Date-Objekte
 * auf UTC-Mitternacht verwendet.
 *
 * Rechtsgrundlagen (jeweils in der am 2026-10-05 geltenden Fassung):
 *   § 634a Abs. 1 BGB   Verjährung der Mängelansprüche (5 Jahre Bauwerk, 2 Jahre sonst)
 *   § 13 Abs. 4 VOB/B   4 Jahre Bauwerke, 2 Jahre andere Werke / Anlagen ohne Wartung
 *   § 13 Abs. 5 VOB/B   2 Jahre ab schriftlicher Mängelrüge bzw. ab Abnahme der Mängelbeseitigung,
 *                       nicht vor Ablauf der Regelfrist
 *   §§ 187, 188 BGB     Fristbeginn und Fristende
 *   § 193 BGB           Fristende an Sonnabend, Sonntag oder Feiertag
 *   §§ 203, 204, 209 BGB Hemmung (Verhandlungen, gerichtliche Verfahren)
 *   § 212 BGB           Neubeginn durch Anerkenntnis
 *
 * Das Werkzeug ersetzt keine Rechtsberatung; es rechnet die Regelfälle nach
 * und benennt, was es nicht prüfen kann.
 */

export const FRISTEN = {
  bgb_bauwerk: { bezeichnung: "Bauwerk, BGB-Werkvertrag", jahre: 5, monate: 0, grundlage: "§ 634a Abs. 1 Nr. 2 BGB" },
  bgb_sonstig: { bezeichnung: "Andere Werkleistung, BGB (Herstellung, Wartung, Veränderung einer Sache)", jahre: 2, monate: 0, grundlage: "§ 634a Abs. 1 Nr. 1 BGB" },
  vob_bauwerk: { bezeichnung: "Bauwerk, VOB/B vereinbart", jahre: 4, monate: 0, grundlage: "§ 13 Abs. 4 Nr. 1 VOB/B" },
  vob_sonstig: { bezeichnung: "Andere Werke und vom Feuer berührte Teile von Feuerungsanlagen, VOB/B", jahre: 2, monate: 0, grundlage: "§ 13 Abs. 4 Nr. 1 VOB/B" },
  vob_anlage: { bezeichnung: "Maschinelle und elektrotechnische Anlagen ohne Wartungsauftrag, VOB/B", jahre: 2, monate: 0, grundlage: "§ 13 Abs. 4 Nr. 2 VOB/B" },
  vereinbart: { bezeichnung: "Vertraglich vereinbarte Frist", jahre: null, monate: null, grundlage: "Vertrag" },
};

export const HEMMUNGSARTEN = {
  verhandlung: { bezeichnung: "Verhandlungen über den Anspruch", grundlage: "§ 203 BGB", nachlauf: { monate: 3 } },
  verfahren: { bezeichnung: "Selbständiges Beweisverfahren, Klage oder Mahnverfahren", grundlage: "§ 204 BGB", nachlauf: { monate: 6, hemmung: true } },
  sonstig: { bezeichnung: "Sonstige Hemmung (z. B. vereinbarter Verjährungsverzicht)", grundlage: "§ 209 BGB", nachlauf: null },
};

const TAG = 86_400_000;

// ---------------------------------------------------------------- Datum

export function parseDatum(text) {
  const treffer = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text || "").trim());
  if (!treffer) return null;
  const [jahr, monat, tag] = treffer.slice(1).map(Number);
  const d = new Date(Date.UTC(jahr, monat - 1, tag));
  if (d.getUTCFullYear() !== jahr || d.getUTCMonth() !== monat - 1 || d.getUTCDate() !== tag) return null;
  return d;
}

export function iso(d) {
  return d.toISOString().slice(0, 10);
}

export function tageImMonat(jahr, monat0) {
  return new Date(Date.UTC(jahr, monat0 + 1, 0)).getUTCDate();
}

export function plusTage(d, n) {
  return new Date(d.getTime() + n * TAG);
}

/** § 188 Abs. 2 und 3 BGB: gleicher Kalendertag; fehlt er, der letzte Tag des Monats. */
export function plusMonate(d, n) {
  const gesamt = d.getUTCMonth() + n;
  const jahr = d.getUTCFullYear() + Math.floor(gesamt / 12);
  const monat = ((gesamt % 12) + 12) % 12;
  const tag = Math.min(d.getUTCDate(), tageImMonat(jahr, monat));
  return new Date(Date.UTC(jahr, monat, tag));
}

export function plusJahre(d, n) {
  return plusMonate(d, 12 * n);
}

export function tageZwischen(a, b) {
  return Math.round((b.getTime() - a.getTime()) / TAG);
}

// ------------------------------------------------------------ Feiertage

/** Ostersonntag nach der Gaußschen Osterformel (Fassung von Lichtenberg). */
export function ostersonntag(jahr) {
  const k = Math.floor(jahr / 100);
  const m = 15 + Math.floor((3 * k + 3) / 4) - Math.floor((8 * k + 13) / 25);
  const s = 2 - Math.floor((3 * k + 3) / 4);
  const a = jahr % 19;
  const d = (19 * a + m) % 30;
  const r = Math.floor((d + Math.floor(a / 11)) / 29);
  const og = 21 + d - r;
  const sz = 7 - ((jahr + Math.floor(jahr / 4) + s) % 7);
  const oe = 7 - ((og - sz) % 7);
  const os = og + oe; // Tag im März (32 = 1. April)
  return new Date(Date.UTC(jahr, 2, 1) + (os - 1) * TAG);
}

/** Gesetzliche Feiertage in Berlin (bundesweite und der 8. März). */
export function feiertage(jahr) {
  const ostern = ostersonntag(jahr);
  const liste = new Map([
    [iso(new Date(Date.UTC(jahr, 0, 1))), "Neujahr"],
    [iso(new Date(Date.UTC(jahr, 2, 8))), "Internationaler Frauentag (Berlin)"],
    [iso(plusTage(ostern, -2)), "Karfreitag"],
    [iso(plusTage(ostern, 1)), "Ostermontag"],
    [iso(new Date(Date.UTC(jahr, 4, 1))), "Tag der Arbeit"],
    [iso(plusTage(ostern, 39)), "Christi Himmelfahrt"],
    [iso(plusTage(ostern, 50)), "Pfingstmontag"],
    [iso(new Date(Date.UTC(jahr, 9, 3))), "Tag der Deutschen Einheit"],
    [iso(new Date(Date.UTC(jahr, 11, 25))), "1. Weihnachtstag"],
    [iso(new Date(Date.UTC(jahr, 11, 26))), "2. Weihnachtstag"],
  ]);
  if (jahr < 2019) liste.delete(iso(new Date(Date.UTC(jahr, 2, 8))));
  return liste;
}

export function feiertagsname(d) {
  return feiertage(d.getUTCFullYear()).get(iso(d)) || null;
}

/** § 193 BGB: Sonnabend, Sonntag und Feiertage zählen nicht als Werktag. */
export function istWerktag(d) {
  const wochentag = d.getUTCDay();
  return wochentag !== 0 && wochentag !== 6 && !feiertagsname(d);
}

export function naechsterWerktag(d) {
  let t = d;
  while (!istWerktag(t)) t = plusTage(t, 1);
  return t;
}

// ------------------------------------------------------------- Rechnung

function spaeter(a, b) {
  return a.getTime() >= b.getTime() ? a : b;
}

function frueher(a, b) {
  return a.getTime() <= b.getTime() ? a : b;
}

/**
 * Berechnet das Ende der Verjährungsfrist für Mängelansprüche.
 *
 * eingabe = {
 *   abnahme: "JJJJ-MM-TT",            Tag der Abnahme (Pflicht)
 *   frist: Schlüssel aus FRISTEN,     Standard "bgb_bauwerk"
 *   vereinbartJahre, vereinbartMonate bei frist === "vereinbart"
 *   anerkenntnis: "JJJJ-MM-TT",       Neubeginn nach § 212 BGB (optional)
 *   ruege: "JJJJ-MM-TT",              schriftliche Mängelrüge, nur VOB/B (optional)
 *   beseitigungAbnahme: "JJJJ-MM-TT", Abnahme der Mängelbeseitigung, nur VOB/B (optional)
 *   hemmungen: [{ von, bis, art }],   art aus HEMMUNGSARTEN (optional)
 *   heute: "JJJJ-MM-TT",              Stichtag für die Restlaufzeit (Standard: heute)
 * }
 */
export function berechne(eingabe) {
  const fehler = [];
  const hinweise = [];
  const schritte = [];
  const abnahme = parseDatum(eingabe.abnahme);
  if (!abnahme) fehler.push("Bitte das Datum der Abnahme eingeben.");

  const schluessel = FRISTEN[eingabe.frist] ? eingabe.frist : "bgb_bauwerk";
  const vorgabe = FRISTEN[schluessel];
  let jahre = vorgabe.jahre;
  let monate = vorgabe.monate;
  if (schluessel === "vereinbart") {
    jahre = Number(eingabe.vereinbartJahre) || 0;
    monate = Number(eingabe.vereinbartMonate) || 0;
    if (jahre < 0 || monate < 0 || jahre * 12 + monate < 1) fehler.push("Bitte die vereinbarte Frist in Jahren und Monaten eingeben.");
  }
  if (fehler.length) return { ok: false, fehler };

  const istVob = schluessel.startsWith("vob");
  const gesamtMonate = jahre * 12 + monate;
  const fristText = `${jahre ? `${jahre} Jahr${jahre === 1 ? "" : "e"}` : ""}${jahre && monate ? " und " : ""}${monate ? `${monate} Monat${monate === 1 ? "" : "e"}` : ""}`;
  let nr = 0;
  const schritt = (bezeichnung, wert, grundlage, erklaerung = "") => schritte.push({ nr: ++nr, bezeichnung, wert, grundlage, erklaerung });

  const fristbeginn = plusTage(abnahme, 1);
  schritt("Abnahme", iso(abnahme), "§ 634a Abs. 2 BGB / § 13 Abs. 4 Nr. 3 VOB/B", "Die Verjährung beginnt mit der Abnahme der Leistung.");
  schritt("Erster Tag der Frist", iso(fristbeginn), "§ 187 Abs. 1 BGB", "Der Tag der Abnahme wird nicht mitgerechnet.");

  const regelende = plusMonate(abnahme, gesamtMonate);
  schritt(`Regelfrist ${fristText}`, iso(regelende), `${vorgabe.grundlage}; § 188 Abs. 2 BGB`,
    "Die Frist endet mit Ablauf des Tages, der dem Abnahmetag nach seiner Zahl entspricht."
    + (regelende.getUTCDate() !== abnahme.getUTCDate() ? " Fehlt dieser Tag im Zielmonat, gilt der letzte Tag des Monats (§ 188 Abs. 3 BGB)." : ""));

  let ende = regelende;

  // Neubeginn durch Anerkenntnis (§ 212 Abs. 1 Nr. 1 BGB): die volle Frist läuft erneut.
  const anerkenntnis = parseDatum(eingabe.anerkenntnis);
  if (eingabe.anerkenntnis && !anerkenntnis) fehler.push("Das Datum des Anerkenntnisses ist ungültig.");
  if (anerkenntnis) {
    if (anerkenntnis.getTime() > ende.getTime()) {
      hinweise.push("Das Anerkenntnis liegt nach dem errechneten Fristende. Ob ein Anerkenntnis nach Ablauf der Verjährung Wirkungen hat, ist eine Rechtsfrage – das Werkzeug berücksichtigt es nicht.");
    } else if (anerkenntnis.getTime() < abnahme.getTime()) {
      hinweise.push("Das Anerkenntnis liegt vor der Abnahme und bleibt unberücksichtigt.");
    } else {
      ende = plusMonate(anerkenntnis, gesamtMonate);
      schritt("Neubeginn durch Anerkenntnis", iso(ende), "§ 212 Abs. 1 Nr. 1 BGB",
        `Mit dem Anerkenntnis vom ${iso(anerkenntnis)} beginnt die Frist von ${fristText} neu. Ob eine Nachbesserung ein Anerkenntnis ist, beurteilt ein Rechtsanwalt.`);
    }
  }

  // VOB/B § 13 Abs. 5 Nr. 1: schriftliche Mängelrüge und Abnahme der Mängelbeseitigung.
  const ruege = parseDatum(eingabe.ruege);
  if (eingabe.ruege && !ruege) fehler.push("Das Datum der Mängelrüge ist ungültig.");
  if (ruege && istVob) {
    if (ruege.getTime() > regelende.getTime()) {
      hinweise.push("Die schriftliche Mängelrüge ging erst nach Ablauf der Regelfrist zu; § 13 Abs. 5 Nr. 1 VOB/B verlangt den Zugang vor Ablauf. Sie bleibt unberücksichtigt.");
    } else {
      const endeRuege = plusJahre(ruege, 2);
      ende = spaeter(ende, endeRuege);
      schritt("Zwei Jahre ab schriftlicher Mängelrüge", iso(endeRuege), "§ 13 Abs. 5 Nr. 1 Satz 2 VOB/B",
        "Gilt nur für den gerügten Mangel und endet nicht vor Ablauf der Regelfrist.");
    }
  } else if (ruege && !istVob) {
    hinweise.push("Die Zwei-Jahres-Frist ab Mängelrüge gibt es nur bei vereinbarter VOB/B. Beim BGB-Werkvertrag verlängert eine Mängelanzeige die Verjährung nicht; dort hemmen nur Verhandlungen oder ein gerichtliches Verfahren.");
  }

  const beseitigung = parseDatum(eingabe.beseitigungAbnahme);
  if (eingabe.beseitigungAbnahme && !beseitigung) fehler.push("Das Datum der Abnahme der Mängelbeseitigung ist ungültig.");
  if (beseitigung && istVob) {
    const endeBeseitigung = plusJahre(beseitigung, 2);
    ende = spaeter(ende, endeBeseitigung);
    schritt("Zwei Jahre ab Abnahme der Mängelbeseitigung", iso(endeBeseitigung), "§ 13 Abs. 5 Nr. 1 Satz 3 VOB/B",
      "Gilt nur für die nachgebesserte Leistung und endet nicht vor Ablauf der Regelfrist.");
  } else if (beseitigung && !istVob) {
    hinweise.push("Eine neue Zwei-Jahres-Frist nach Abnahme der Mängelbeseitigung kennt nur die VOB/B. Beim BGB-Werkvertrag kann die Nachbesserung ein Anerkenntnis sein (§ 212 BGB) – tragen Sie das Datum dann oben als Anerkenntnis ein.");
  }

  // Hemmung (§ 209 BGB): die Zeit der Hemmung wird nicht eingerechnet.
  const hemmungen = (eingabe.hemmungen || [])
    .map((h) => ({ von: parseDatum(h.von), bis: parseDatum(h.bis), art: HEMMUNGSARTEN[h.art] ? h.art : "sonstig" }))
    .filter((h) => h.von && h.bis)
    .sort((a, b) => a.von.getTime() - b.von.getTime());
  for (const h of hemmungen) {
    if (h.bis.getTime() < h.von.getTime()) {
      hinweise.push(`Eine Hemmung endet vor ihrem Beginn (${iso(h.von)} bis ${iso(h.bis)}) und bleibt unberücksichtigt.`);
      continue;
    }
    const art = HEMMUNGSARTEN[h.art];
    let bisWirksam = h.bis;
    if (art.nachlauf && art.nachlauf.hemmung) {
      bisWirksam = plusMonate(h.bis, art.nachlauf.monate);
      schritt("Ende der Hemmung durch das Verfahren", iso(bisWirksam), "§ 204 Abs. 2 Satz 1 BGB",
        `Die Hemmung endet sechs Monate nach der rechtskräftigen Entscheidung oder anderweitigen Beendigung (${iso(h.bis)}).`);
    }
    const anfang = spaeter(h.von, fristbeginn);
    const schluss = frueher(bisWirksam, ende);
    if (anfang.getTime() > schluss.getTime()) {
      hinweise.push(`Die Hemmung ab ${iso(h.von)} liegt außerhalb der laufenden Frist und verlängert sie nicht.`);
      continue;
    }
    const tage = tageZwischen(anfang, schluss) + 1;
    ende = plusTage(ende, tage);
    schritt(`Hemmung: ${art.bezeichnung}`, iso(ende), `${art.grundlage}; § 209 BGB`,
      `${tage} Tage (${iso(anfang)} bis ${iso(schluss)}, Beginn und Ende mitgezählt) werden nicht eingerechnet; das Fristende verschiebt sich entsprechend.`);
    if (art.nachlauf && !art.nachlauf.hemmung) {
      const fruehestens = plusMonate(bisWirksam, art.nachlauf.monate);
      if (fruehestens.getTime() > ende.getTime()) {
        ende = fruehestens;
        schritt("Frühestens drei Monate nach Ende der Verhandlungen", iso(ende), "§ 203 Satz 2 BGB",
          "Nach dem Ende von Verhandlungen tritt die Verjährung frühestens drei Monate später ein.");
      }
    }
  }
  if (fehler.length) return { ok: false, fehler };

  // § 193 BGB: Fristende an Sonnabend, Sonntag oder Feiertag.
  const endeWerktag = naechsterWerktag(ende);
  const verschoben = endeWerktag.getTime() !== ende.getTime();
  if (verschoben) {
    const grund = feiertagsname(ende) || (ende.getUTCDay() === 0 ? "Sonntag" : "Sonnabend");
    schritt("Fristende an einem " + grund, iso(endeWerktag), "§ 193 BGB",
      "Fällt das Fristende auf einen Sonnabend, Sonntag oder gesetzlichen Feiertag, tritt an seine Stelle der nächste Werktag. Verlassen Sie sich darauf nicht – handeln Sie vorher.");
  }

  const heute = parseDatum(eingabe.heute) || new Date(Date.UTC(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()));
  const tageBis = tageZwischen(heute, endeWerktag);
  const status = tageBis < 0 ? "abgelaufen" : tageBis <= 180 ? "knapp" : "laeuft";

  if (ende.getTime() !== regelende.getTime()) {
    hinweise.push("Verlängerungen durch Mängelrüge, Mängelbeseitigung oder Anerkenntnis gelten nur für den jeweils betroffenen Mangel; für alle anderen Mängel bleibt es bei der Regelfrist.");
  }
  if (istVob) {
    hinweise.push("Die VOB/B gilt nur, wenn sie wirksam in den Vertrag einbezogen ist. Ist das zweifelhaft oder wurde sie gegenüber einem Verbraucher verwendet, rechnen Sie zur Sicherheit auch mit der BGB-Frist.");
  }
  hinweise.push("Bei arglistig verschwiegenen Mängeln gilt die regelmäßige Verjährung (§ 634a Abs. 3 BGB), bei einem Bauwerk aber nicht vor Ablauf von fünf Jahren ab Abnahme. Teilabnahmen, Verjährungsverzicht und Vertragsklauseln kann das Werkzeug nicht prüfen.");

  return {
    ok: true,
    fehler: [],
    frist: { schluessel, bezeichnung: vorgabe.bezeichnung, jahre, monate, text: fristText, grundlage: vorgabe.grundlage, vob: istVob },
    abnahme: iso(abnahme),
    fristbeginn: iso(fristbeginn),
    regelende: iso(regelende),
    ende: iso(ende),
    endeWerktag: iso(endeWerktag),
    verschoben,
    heute: iso(heute),
    tageBis,
    status,
    schritte,
    hinweise,
  };
}

/** Datum für die Anzeige: "15.03.2026". */
export function datumDeutsch(isoText) {
  const d = parseDatum(isoText);
  if (!d) return "";
  return `${String(d.getUTCDate()).padStart(2, "0")}.${String(d.getUTCMonth() + 1).padStart(2, "0")}.${d.getUTCFullYear()}`;
}

/** Wochentag für die Anzeige. */
export function wochentag(isoText) {
  const d = parseDatum(isoText);
  if (!d) return "";
  return ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Sonnabend"][d.getUTCDay()];
}
