/*
 * Modellschicht „Berlin“: setzt die Angaben des Besuchers und die Adressdaten
 * nach dem Modell des Gutachterausschusses für Grundstückswerte in Berlin in
 * Eingaben für den Rechenkern um (fachliteratur/MODELL-BERLIN.md).
 *
 * Alle Zahlen kommen aus wertrechner/data/marktdaten.json (erzeugt aus
 * daten/marktdaten.xlsx). Hier steht nur Logik: Nachschlagen, Formeln,
 * Gültigkeitsprüfungen. Nichts wird geschätzt oder erfunden – fehlt ein Wert,
 * gibt es keinen Wert, sondern einen Grund.
 */
import { sachwert, ertragswert, runde, rundeAuf, fmt } from './rechenkern.js';

const WOHNLAGE = { 0: null, 1: 'einfach', 2: 'mittel', 3: 'gut' };
const BAULAND_SACHWERT = new Set(['W', 'W-EFH', 'M1', 'M2']);
const BAULAND_ERTRAGSWERT = new Set(['W', 'W-EFH', 'M1', 'M2', 'G', 'Gp']);

// Prüfgrößen, bei denen außerhalb des Gültigkeitsbereichs KEIN Wert erscheint.
// Alle anderen Größen der Blätter „Gueltigkeit“ führen nur zu einem Hinweis.
const SPERREN = {
  sachwert: new Set(['vorlaeufiger_sachwert', 'grundstuecksflaeche', 'bgf', 'brw']),
  ertragswert: new Set(['objektmiete_tabelle', 'grundstuecksflaeche', 'wohn_nutzflaeche', 'brw', 'alter']),
};

/* ------------------------------------------------------------------------
 * Zugriff auf die Marktdaten
 * ---------------------------------------------------------------------- */

export function modell(daten) {
  if (!daten || !daten.parameter || !daten.blaetter) throw new Error('Marktdaten fehlen oder sind unvollständig');
  const b = daten.blaetter;
  const parameter = daten.parameter;

  const ortsteile = new Map(b.Ortsteile.map((z) => [normName(z.Ortsteil), z]));
  const nhkZeilen = b.NHK2010;
  const gfz = {};
  for (const z of b.GFZ_Koeffizienten) (gfz[z.Tabelle] ||= []).push({ gfz: z.GFZ, k: z.Koeffizient });
  for (const t of Object.values(gfz)) t.sort((a, c) => a.gfz - c.gfz);
  const korrekturen = b.SWF_Korrekturen;
  const bewk = b.Bewirtschaftungskosten;
  const rnd = b.RND;
  const gueltigkeit = b.Gueltigkeit;

  function bewkWert(position, nutzung) {
    const z = bewk.find((x) => x.Position === position && x.Nutzung === nutzung);
    if (!z) throw new Error(`Bewirtschaftungskosten fehlen: ${position} / ${nutzung}`);
    return z.Wert;
  }

  return {
    parameter,
    quellen: b.Quellen,
    marktanpassungsfaktor: daten.liegenschaftszins.marktanpassungsfaktor ?? 1,

    ortsteil(name) {
      return ortsteile.get(normName(name)) || null;
    },

    /** NHK-2010-Zeile für Gebäudestellung, Unterkellerung, Geschosse und Dach (SWF 2025 S. 3). */
    nhkTyp({ gebaeudestellung, unterkellert, geschosse, dachgeschoss }) {
      const stellung = gebaeudestellung === 'freistehend' ? 'freistehend'
        : gebaeudestellung === 'reihenmittelhaus' ? 'reihenmittel' : 'doppelhaus_reihenend';
      const keller = unterkellert ? 'unterkellert' : 'nicht_unterkellert';
      // Berlin: 3-geschossige Gebäude wie 2-geschossige behandeln (SWF 2025 S. 3)
      const ebenen = geschosse >= 2 ? (unterkellert ? 'KG+EG+OG' : 'EG+OG') : (unterkellert ? 'KG+EG' : 'EG');
      const zeile = nhkZeilen.find((z) => z.Gebäudestellung === stellung && z.Keller === keller
        && z.Geschosse === ebenen && z.Dachgeschoss === dachgeschoss);
      if (!zeile) throw new Error(`NHK-Typ nicht gefunden: ${stellung}, ${keller}, ${ebenen}, ${dachgeschoss}`);
      return zeile;
    },

    nhkWert(zeile) {
      return zeile[`Stufe_${parameter.nhk_standardstufe}`];
    },

    /**
     * Restnutzungsdauer nach den Berliner Tabellen.
     * verfahren 'sachwert' (SWF 2025 S. 3–4) oder 'ertragswert' (LZ 2025 S. 10–11).
     * ausstattung = { zentralheizung, baeder } (nur Ertragswert, Baujahre bis 1948).
     */
    restnutzungsdauer(verfahren, { baujahr, alter, bauzustand, ausstattung }) {
      const zeilen = rnd.filter((z) => z.Verfahren === verfahren);
      const altbau = zeilen.find((z) => z.Regel === 'baujahr' && baujahr <= z.bis);
      let wert;
      let abschlag = 0;
      let quelle;
      if (altbau) {
        wert = altbau[bauzustand];
        quelle = altbau['Quelle/Stand'];
        if (verfahren === 'ertragswert' && ausstattung) {
          const bis1918 = baujahr <= 1918;
          if (bis1918 && !(ausstattung.zentralheizung && ausstattung.baeder)) {
            const regel = ausstattung.zentralheizung || ausstattung.baeder ? 'abschlag_altbau_teilweise' : 'abschlag_altbau_ohne';
            abschlag = zeilen.find((z) => z.Regel === regel)?.[bauzustand] || 0;
          } else if (!bis1918 && !ausstattung.zentralheizung) {
            abschlag = zeilen.find((z) => z.Regel === 'abschlag_zwischenkrieg_ohne_zh')?.[bauzustand] || 0;
          }
        }
      } else {
        const z = zeilen.find((x) => x.Regel === 'baualter' && (x.von == null || alter >= x.von) && (x.bis == null || alter <= x.bis));
        if (!z) throw new Error(`Restnutzungsdauer: kein Tabellenwert für Baualter ${alter}`);
        wert = z[bauzustand];
        quelle = z['Quelle/Stand'];
      }
      if (wert == null) return { rnd: null, quelle, grund: `Für Baualter ${alter} Jahre und Bauzustand „${bauzustand}“ sieht das Berliner Modell keine Restnutzungsdauer vor.` };
      return { rnd: Math.max(wert + abschlag, 0), tabellenwert: wert, abschlag, quelle };
    },

    /** Korrektur eines Merkmals aus dem Blatt SWF_Korrekturen. */
    swfKorrektur(merkmal, auspraegung, baujahr) {
      if (merkmal === 'baujahresgruppe') {
        const z = korrekturen.find((k) => k.Merkmal === merkmal && (k.von == null || baujahr >= k.von) && (k.bis == null || baujahr <= k.bis));
        return z ? { wert: z.Korrektur, text: z.Ausprägung, quelle: z['Quelle/Stand'] } : null;
      }
      const z = korrekturen.find((k) => k.Merkmal === merkmal && k.Ausprägung === auspraegung);
      return z ? { wert: z.Korrektur, text: z.Ausprägung, quelle: z['Quelle/Stand'] } : null;
    },

    /**
     * Sachwertfaktor zum Stichtag (SWF 2025 S. 8–10):
     * SWF = konstante + koeff_sachwert × vorläufiger Sachwert + koeff_tag × tage + Gruppe + Korrekturen.
     */
    sachwertfaktor({ vorlaeufigerSachwert, swfGruppe, baujahr, gebaeudeart, bauzustand, konstruktion, wohnlage, bauerrichtungsvertrag }) {
      const f = daten.sachwertfaktor;
      const bestandteile = [
        { text: 'Konstante', wert: f.konstante },
        { text: `${fmt(f.koeff_sachwert)} × vorläufiger Sachwert ${fmt(vorlaeufigerSachwert)} €`, wert: f.koeff_sachwert * vorlaeufigerSachwert },
        { text: `${fmt(f.koeff_tag)} × ${fmt(f.tage)} Tage (31.12.2021 bis 31.12.2024)`, wert: f.koeff_tag * f.tage },
        { text: `Altbezirksgruppe ${swfGruppe}`, wert: f[`gruppe_${swfGruppe}`] },
      ];
      const merkmale = [
        ['baujahresgruppe', null, 'Baujahresgruppe'],
        ['gebaeudeart', gebaeudeart, 'Gebäudeart'],
        ['bauzustand', bauzustand, 'Bauzustand'],
        ['konstruktion', konstruktion, 'Gebäudekonstruktion'],
        ['wohnlage', wohnlage, 'Stadträumliche Wohnlage'],
        ['bauerrichtungsvertrag', bauerrichtungsvertrag || f.bauerrichtungsvertrag_standard, 'Bauerrichtungsvertrag'],
      ];
      for (const [merkmal, auspraegung, titel] of merkmale) {
        const k = this.swfKorrektur(merkmal, auspraegung, baujahr);
        if (!k) throw new Error(`Sachwertfaktor: keine Korrektur für ${titel} „${auspraegung}“`);
        bestandteile.push({ text: `${titel} ${k.text}`, wert: k.wert });
      }
      const ungerundet = bestandteile.reduce((s, t) => s + t.wert, 0);
      const stellen = parameter.swf_rundung_nachkommastellen;
      return { ungerundet: runde(ungerundet, 6), gerundet: runde(ungerundet, stellen), stellen, bestandteile };
    },

    /**
     * Liegenschaftszinssatz in Prozent (LZ 2025 S. 12–15):
     * LZ = konstante + koeff_miete × Objektmiete + koeff_tag × tage + Gebietsgruppe + Altbezirk + Baujahr + Gewerbe.
     */
    liegenschaftszins({ objektmiete, gebietsgruppe, altbezirk, baujahr, stadtlage, gewerbeanteilProzent }) {
      const f = daten.liegenschaftszins;
      const gruppe = normName(gebietsgruppe).replace('ü', 'ue');
      const bestandteile = [
        { text: 'Konstante', wert: f.konstante },
        { text: `${fmt(f.koeff_miete)} × Objektkaltmiete ${fmt(objektmiete)} €/m²`, wert: f.koeff_miete * objektmiete },
        { text: `${fmt(f.koeff_tag)} × ${fmt(f.tage)} Tage (01.01.2022 bis 31.12.2024)`, wert: f.koeff_tag * f.tage },
        { text: `Gebietsgruppe ${gebietsgruppe}`, wert: f[`zuschlag_${gruppe}`] ?? 0 },
      ];
      const alt = f[`altbezirk_${normName(altbezirk)}`];
      if (alt) bestandteile.push({ text: `Altbezirk ${altbezirk}`, wert: alt });
      if (baujahr >= 1973 && baujahr <= 1990 && stadtlage === 'West') {
        bestandteile.push({ text: 'Baujahre 1973–1990 im Westteil', wert: f.baujahr_1973_1990_west });
      }
      if (gewerbeanteilProzent > 0) {
        bestandteile.push({ text: `Gewerblicher Anteil ${fmt(runde(gewerbeanteilProzent, 1))} % × ${fmt(f.gewerbe_je_prozentpunkt)}`,
          wert: f.gewerbe_je_prozentpunkt * gewerbeanteilProzent });
      }
      const ungerundet = bestandteile.reduce((s, t) => s + t.wert, 0);
      const stellen = parameter.lz_rundung_nachkommastellen;
      return { ungerundet: runde(ungerundet, 6), gerundet: runde(ungerundet, stellen), stellen, bestandteile };
    },

    /** GFZ-Umrechnungskoeffizient mit linearer Zwischenwertbildung; null außerhalb der Tabelle. */
    gfzKoeffizient(tabelle, wert) {
      const t = gfz[tabelle];
      if (!t || wert == null || wert < t[0].gfz || wert > t[t.length - 1].gfz) return null;
      for (let i = 1; i < t.length; i += 1) {
        if (wert <= t[i].gfz) {
          const a = t[i - 1];
          const c = t[i];
          return runde(a.k + (c.k - a.k) * (wert - a.gfz) / (c.gfz - a.gfz), 4);
        }
      }
      return t[t.length - 1].k;
    },

    /**
     * Anpassungsfaktor des Bodenrichtwerts an die tatsächliche wertrelevante GFZ
     * (LZ 2025 S. 4; GFZ-W S. 3; GFZ-D S. 2). Zonen W: Tabelle Wohn-04; gemischte
     * Zonen: nach Nutzflächenanteil gewichtetes Mittel aus Wohn-04 und Dienst-04.
     */
    gfzAnpassung({ nutzungZone, gfzZone, gfzTatsaechlich, gewerbeflaechenanteil = 0 }) {
      if (gfzZone == null || gfzTatsaechlich == null) {
        return { faktor: 1, hinweis: 'Für die GFZ-Anpassung des Bodenwerts fehlt die GFZ der Richtwertzone oder des Grundstücks; der Bodenrichtwert wurde unangepasst übernommen.' };
      }
      if (runde(gfzZone, 2) === runde(gfzTatsaechlich, 2)) return { faktor: 1 };
      const tabellen = nutzungZone === 'W' || nutzungZone === 'W-EFH' || gewerbeflaechenanteil <= 0
        ? [['wohn04', 1]]
        : [['wohn04', 1 - gewerbeflaechenanteil], ['dienst04', gewerbeflaechenanteil]];
      let faktor = 0;
      const teile = [];
      for (const [tabelle, gewicht] of tabellen) {
        const kZone = this.gfzKoeffizient(tabelle, gfzZone);
        const kObjekt = this.gfzKoeffizient(tabelle, gfzTatsaechlich);
        if (kZone == null || kObjekt == null) {
          return { faktor: 1, hinweis: `GFZ ${fmt(gfzTatsaechlich)} bzw. ${fmt(gfzZone)} liegt außerhalb der Tabelle ${tabelle === 'wohn04' ? 'Wohn-04 (0,8–5,0)' : 'Dienst-04 (2,0–7,0)'}; der Bodenrichtwert wurde ohne GFZ-Anpassung übernommen.` };
        }
        faktor += gewicht * kObjekt / kZone;
        teile.push({ tabelle, gewicht, kZone, kObjekt });
      }
      return { faktor: runde(faktor, 4), teile };
    },

    /** Berliner Bewirtschaftungskostenansätze als Sätze für den Rechenkern (LZ 2025 S. 9). */
    bewirtschaftung(art, variante) {
      const ihWohnen = bewkWert('instandhaltung', 'wohnen');
      if (art === 'wohnen') {
        return {
          verwaltung: { jeEinheit: bewkWert('verwaltung', 'wohnen') },
          instandhaltung: { jeM2: ihWohnen },
          mietausfallwagnis: { prozent: bewkWert('mietausfallwagnis', 'wohnen') },
        };
      }
      if (art === 'gewerbe') {
        const anteil = bewkWert('instandhaltung', variante === 'nebennutzung' ? 'nebennutzung' : 'gewerbe') / 100;
        return {
          verwaltung: { prozent: bewkWert('verwaltung', 'gewerbe') },
          instandhaltung: { jeM2: runde(ihWohnen * anteil, 2) },
          mietausfallwagnis: { prozent: bewkWert('mietausfallwagnis', 'gewerbe') },
        };
      }
      return {  // sonstiges: Garagen oder Stellplätze
        verwaltung: { prozent: bewkWert('verwaltung', 'sonstiges') },
        instandhaltung: { jeEinheit: bewkWert('instandhaltung', variante === 'garage' ? 'garage' : 'stellplatz') },
        mietausfallwagnis: { prozent: bewkWert('mietausfallwagnis', 'sonstiges') },
      };
    },

    /** Prüft einen Wert gegen das Blatt Gueltigkeit. */
    pruefung(verfahren, schluessel, wert) {
      const z = gueltigkeit.find((g) => g.Verfahren === verfahren && g.Schlüssel === schluessel);
      if (!z || wert == null) return null;
      const ok = wert >= z.Min && wert <= z.Max;
      return { schluessel, groesse: z.Größe, wert, min: z.Min, max: z.Max, einheit: z.Einheit, ok, sperrend: SPERREN[verfahren].has(schluessel), quelle: z['Quelle/Stand'] };
    },

    spanne(wert) {
      const prozent = parameter.spanne_prozent;
      const schritt = parameter.ergebnis_rundung_euro;
      return { prozent, von: rundeAuf(wert * (1 - prozent / 100), schritt), bis: rundeAuf(wert * (1 + prozent / 100), schritt) };
    },
  };
}

function normName(text) {
  return String(text || '').trim().toLowerCase();
}

function stichtagsjahr(optionen) {
  return optionen?.jahr ?? new Date().getFullYear();
}

function zoneAusAdresse(adresse) {
  const z = adresse?.zone?.modell;
  return z && typeof z.brw === 'number' ? z : null;
}

/* ------------------------------------------------------------------------
 * Sachwertverfahren für Ein- und Zweifamilienhäuser nach dem Berliner Modell
 * ---------------------------------------------------------------------- */

/**
 * objekt = {
 *   gebaeudestellung: 'freistehend'|'doppelhaushaelfte'|'reihenendhaus'|'reihenmittelhaus',
 *   unterkellert: true|false, geschosse: 1|2|3 (Vollgeschosse oberirdisch),
 *   dachgeschoss: 'voll_ausgebaut'|'nicht_ausgebaut'|'flachdach',
 *   baujahr, bauzustand: 'gut'|'normal'|'schlecht',
 *   konstruktion: 'massiv'|'fertighaus_massiv'|'fertighaus_holz',
 *   bgf | wohnflaeche, grundstuecksflaeche, nebenanlagen (€, optional), bog (optional)
 * }
 * adresse = { zone: { modell: { brw, nutzung, gfz }, aktuell: {...} }, wohnlage: 0–3, ortsteil }
 */
export function berlinSachwert(objekt, adresse, m, optionen = {}) {
  const gruende = [];
  const hinweise = [];
  const jahr = stichtagsjahr(optionen);
  const p = m.parameter;

  const ort = m.ortsteil(adresse?.ortsteil);
  if (!ort) gruende.push(`Der Ortsteil „${adresse?.ortsteil || '–'}“ ist im Berliner Modell nicht zugeordnet.`);
  const swfGruppe = ort?.SWF_Gruppe;
  if (ort && !swfGruppe) {
    gruende.push(`Für den Altbezirk ${ort.Altbezirk} veröffentlicht der Gutachterausschuss keine Sachwertfaktoren (zu wenige Verkäufe von Ein- und Zweifamilienhäusern).`);
  }
  const zone = zoneAusAdresse(adresse);
  if (!zone) gruende.push('Für diese Adresse liegt kein Bodenrichtwert zum Modellstichtag vor.');
  else if (!BAULAND_SACHWERT.has(zone.nutzung)) {
    gruende.push(`Die Bodenrichtwertzone ist als „${zone.nutzung}“ ausgewiesen, nicht als Wohnbauland. Das Sachwertverfahren für Eigenheime ist hier nicht anwendbar.`);
  }
  if (zone?.entwicklung) hinweise.push('Das Grundstück liegt in einem städtebaulichen Entwicklungsbereich; der Bodenrichtwert gilt dort nur eingeschränkt.');
  if (zone?.beitrag) hinweise.push(`Beitragszustand der Richtwertzone: ${zone.beitrag}.`);

  const alter = jahr - objekt.baujahr;
  if (!(objekt.baujahr > 1800 && alter >= 0)) gruende.push('Das Baujahr ist nicht plausibel.');

  const wohnlageText = WOHNLAGE[adresse?.wohnlage ?? 0] || 'mittel';
  if (!WOHNLAGE[adresse?.wohnlage ?? 0]) hinweise.push('Für diese Adresse ist keine Wohnlage im Mietspiegel-Datensatz hinterlegt; es wurde „mittel“ angenommen.');

  if (gruende.length) return { status: 'nicht_anwendbar', gruende, hinweise };

  // Gebäudeart und NHK
  const nhkTyp = m.nhkTyp(objekt);
  const nhk = m.nhkWert(nhkTyp);
  const gebaeudeart = objekt.gebaeudestellung;

  // BGF – angegeben, aus der Grundfläche (Außenmaße) abgeleitet oder aus der
  // Wohnfläche geschätzt. Die Anteile stehen als Annahmen im Blatt Modellparameter.
  // Anrechenbare Ebenen: alle Vollgeschosse (auch das dritte, obwohl der NHK-Typ
  // wie 2-geschossig gewählt wird), der Keller und das nutzbare Dachgeschoss.
  let bgf = objekt.bgf;
  let bgfGeschaetzt = null;
  const dgBgf = objekt.dachgeschoss === 'flachdach' ? 0 : p.bgf_anteil_dachgeschoss;
  const ebenen = runde(objekt.geschosse + (objekt.unterkellert ? 1 : 0) + dgBgf, 2);
  if (!(bgf > 0) && objekt.grundflaeche > 0) {
    bgf = runde(objekt.grundflaeche * ebenen, 0);
    bgfGeschaetzt = { art: 'grundflaeche', grundflaeche: objekt.grundflaeche, ebenen };
    hinweise.push(`Die Brutto-Grundfläche wurde aus der Grundfläche abgeleitet (${fmt(objekt.grundflaeche)} m² × ${fmt(ebenen)} anrechenbare Ebenen ≈ ${fmt(bgf)} m²).`);
  } else if (!(bgf > 0) && objekt.wohnflaeche > 0) {
    const dgWf = objekt.dachgeschoss === 'voll_ausgebaut' ? p.wohnflaeche_anteil_dachgeschoss : 0;
    const faktor = runde(ebenen / (objekt.geschosse * p.wohnflaeche_anteil_vollgeschoss + dgWf), 2);
    bgf = runde(objekt.wohnflaeche * faktor, 0);
    bgfGeschaetzt = { art: 'wohnflaeche', faktor, wohnflaeche: objekt.wohnflaeche };
    hinweise.push(`Die Brutto-Grundfläche wurde aus der Wohnfläche geschätzt (${fmt(objekt.wohnflaeche)} m² × ${fmt(faktor)} ≈ ${fmt(bgf)} m²). Eine gemessene BGF oder die Grundfläche nach Außenmaßen macht das Ergebnis genauer.`);
  } else if (!(bgf > 0)) {
    return { status: 'nicht_anwendbar', gruende: ['Brutto-Grundfläche, Grundfläche oder Wohnfläche fehlt.'], hinweise };
  }

  // Restnutzungsdauer
  const rnd = m.restnutzungsdauer('sachwert', { baujahr: objekt.baujahr, alter, bauzustand: objekt.bauzustand });
  if (rnd.rnd == null) return { status: 'nicht_anwendbar', gruende: [rnd.grund], hinweise };

  // Erster Durchlauf ohne Marktanpassung, um den vorläufigen Sachwert für die SWF-Formel zu erhalten
  const kernEingabe = {
    gebaeude: [{ bezeichnung: 'Wohngebäude', bgf, nhk, zuschlag2010: 0, baupreisindex: p.bpi_2010, regionalfaktor: p.regionalfaktor, gnd: p.gnd_wohnen, rnd: rnd.rnd }],
    aussenanlagen: objekt.nebenanlagen || 0,
    bodenwert: { flaeche: objekt.grundstuecksflaeche, bodenrichtwert: zone.brw },
    sachwertfaktor: 1,
    bog: objekt.bog || [],
    rundung: { alterswertminderung: p.alterswertminderung_nachkommastellen, ergebnis: p.ergebnis_rundung_euro },
  };
  const vorlauf = sachwert(kernEingabe);
  const swf = m.sachwertfaktor({
    vorlaeufigerSachwert: vorlauf.vorlaeufigerSachwert, swfGruppe, baujahr: objekt.baujahr, gebaeudeart,
    bauzustand: objekt.bauzustand, konstruktion: objekt.konstruktion, wohnlage: wohnlageText === 'sehr gut' ? 'sehr_gut' : wohnlageText,
  });
  const ergebnis = sachwert({ ...kernEingabe, sachwertfaktor: swf.gerundet });

  // Gültigkeitsprüfungen
  const pruefungen = [
    m.pruefung('sachwert', 'vorlaeufiger_sachwert', ergebnis.vorlaeufigerSachwert),
    m.pruefung('sachwert', 'grundstuecksflaeche', objekt.grundstuecksflaeche),
    m.pruefung('sachwert', 'bgf', bgf),
    m.pruefung('sachwert', 'brw', zone.brw),
    m.pruefung('sachwert', 'nhk', nhk),
  ].filter(Boolean);
  const verletzt = pruefungen.filter((x) => !x.ok);
  for (const v of verletzt.filter((x) => !x.sperrend)) {
    hinweise.push(`${v.groesse} (${fmt(v.wert)} ${v.einheit}) liegt außerhalb des Bereichs, in dem die Sachwertfaktoren statistisch gesichert sind (${fmt(v.min)}–${fmt(v.max)} ${v.einheit}).`);
  }
  const sperrend = verletzt.filter((x) => x.sperrend);
  if (sperrend.length) {
    return {
      status: 'ausserhalb',
      gruende: sperrend.map((v) => `${v.groesse}: ${fmt(v.wert)} ${v.einheit} liegt außerhalb des Gültigkeitsbereichs der Berliner Sachwertfaktoren (${fmt(v.min)}–${fmt(v.max)} ${v.einheit}).`),
      hinweise, pruefungen,
    };
  }

  return {
    status: 'ok',
    verfahren: 'sachwert',
    ergebnis,
    wert: ergebnis.sachwertGerundet,
    spanne: m.spanne(ergebnis.sachwertGerundet),
    modell: {
      nhkTyp: nhkTyp.Typ, nhk, standardstufe: p.nhk_standardstufe, bgf, bgfGeschaetzt,
      baupreisindex: p.bpi_2010, regionalfaktor: p.regionalfaktor, gnd: p.gnd_wohnen, alter, rnd,
      bodenrichtwert: zone.brw, bodenrichtwertStichtag: p.brw_stichtag_modell, bodenrichtwertAktuell: adresse?.zone?.aktuell?.brw ?? null,
      wohnlage: wohnlageText, altbezirk: ort.Altbezirk, swfGruppe, sachwertfaktor: swf,
      stichtagFaktoren: p.stichtag_faktoren,
    },
    pruefungen,
    hinweise,
  };
}

/* ------------------------------------------------------------------------
 * Allgemeines Ertragswertverfahren für Mietwohn- und Wohn-/Geschäftshäuser
 * ---------------------------------------------------------------------- */

/**
 * objekt = {
 *   baujahr, bauzustand, ausstattung: { zentralheizung, baeder } (Altbauten),
 *   wohnen:   { flaeche, einheiten, mieteMonat },
 *   gewerbe:  { flaeche, mieteMonat, art: 'buero_laden'|'nebennutzung' } (optional),
 *   sonstiges:{ garagen, stellplaetze, mieteMonat } (optional),
 *   grundstuecksflaeche, geschossflaeche (oberirdisch, Außenmaße) oder gfz,
 *   bog (optional)
 * }
 */
export function berlinErtragswert(objekt, adresse, m, optionen = {}) {
  const gruende = [];
  const hinweise = [];
  const jahr = stichtagsjahr(optionen);
  const p = m.parameter;

  const ort = m.ortsteil(adresse?.ortsteil);
  if (!ort) gruende.push(`Der Ortsteil „${adresse?.ortsteil || '–'}“ ist im Berliner Modell nicht zugeordnet.`);
  const zone = zoneAusAdresse(adresse);
  if (!zone) gruende.push('Für diese Adresse liegt kein Bodenrichtwert zum Modellstichtag vor.');
  else if (!BAULAND_ERTRAGSWERT.has(zone.nutzung)) {
    gruende.push(`Die Bodenrichtwertzone ist als „${zone.nutzung}“ ausgewiesen; die Berliner Liegenschaftszinssätze gelten nur für Bauland (W, M1, M2, G, Gp).`);
  }
  if (zone?.entwicklung) hinweise.push('Das Grundstück liegt in einem städtebaulichen Entwicklungsbereich; der Bodenrichtwert gilt dort nur eingeschränkt.');

  const wohnen = objekt.wohnen || {};
  const gewerbe = objekt.gewerbe || {};
  const sonstiges = objekt.sonstiges || {};
  const einheiten = (wohnen.einheiten || 0) + (gewerbe.einheiten || (gewerbe.flaeche > 0 ? 1 : 0));
  if (einheiten < p.ertragswert_mindest_mieteinheiten) {
    gruende.push(`Die Liegenschaftszinssätze gelten erst ab ${p.ertragswert_mindest_mieteinheiten} Mieteinheiten (angegeben: ${einheiten}).`);
  }
  if (objekt.baujahr < p.ertragswert_baujahr_min) gruende.push(`Baujahre vor ${p.ertragswert_baujahr_min} sind im Berliner Modell nicht enthalten.`);
  const alter = jahr - objekt.baujahr;
  if (!(objekt.baujahr > 1800 && alter >= 0)) gruende.push('Das Baujahr ist nicht plausibel.');
  if (!(wohnen.flaeche > 0 && wohnen.mieteMonat >= 0)) gruende.push('Wohnfläche und Wohnungsmiete fehlen.');
  if (gruende.length) return { status: 'nicht_anwendbar', gruende, hinweise };

  // Nutzungen mit Berliner Bewirtschaftungsansätzen
  const nutzungen = [{
    art: 'wohnen', bezeichnung: 'Wohnen', flaeche: wohnen.flaeche, einheiten: wohnen.einheiten, mieteMonat: wohnen.mieteMonat,
    bewirtschaftung: m.bewirtschaftung('wohnen'),
  }];
  if (gewerbe.flaeche > 0) {
    nutzungen.push({
      art: 'gewerbe', bezeichnung: gewerbe.art === 'nebennutzung' ? 'Gewerbe (Nebennutzung, z. B. Lager)' : 'Gewerbe (Büro, Praxis, Laden)',
      flaeche: gewerbe.flaeche, einheiten: gewerbe.einheiten || 1, mieteMonat: gewerbe.mieteMonat || 0,
      bewirtschaftung: m.bewirtschaftung('gewerbe', gewerbe.art),
    });
  }
  const garagen = sonstiges.garagen || 0;
  const stellplaetze = sonstiges.stellplaetze || 0;
  if (garagen + stellplaetze > 0 && sonstiges.mieteMonat > 0) {
    // Miete anteilig nach Plätzen auf Garagen und Stellplätze verteilen (unterschiedliche Instandhaltung)
    const je = sonstiges.mieteMonat / (garagen + stellplaetze);
    if (garagen > 0) nutzungen.push({ art: 'sonstiges', bezeichnung: 'Garagen', einheiten: garagen, mieteMonat: runde(je * garagen, 2), bewirtschaftung: m.bewirtschaftung('sonstiges', 'garage') });
    if (stellplaetze > 0) nutzungen.push({ art: 'sonstiges', bezeichnung: 'Stellplätze', einheiten: stellplaetze, mieteMonat: runde(je * stellplaetze, 2), bewirtschaftung: m.bewirtschaftung('sonstiges', 'stellplatz') });
  }

  const mieteMonatGesamt = nutzungen.reduce((s, n) => s + n.mieteMonat, 0);
  const wohnNutzflaeche = wohnen.flaeche + (gewerbe.flaeche || 0);
  const objektmiete = runde(mieteMonatGesamt / wohnNutzflaeche, 2);
  const rohertragJahr = mieteMonatGesamt * 12;
  const gewerbeanteilProzent = rohertragJahr > 0 ? runde(((gewerbe.mieteMonat || 0) * 12) / rohertragJahr * 100, 2) : 0;
  if (gewerbeanteilProzent > p.ertragswert_max_gewerbeanteil_prozent) {
    return { status: 'nicht_anwendbar', gruende: [`Der gewerbliche Mietanteil (${fmt(gewerbeanteilProzent)} %) übersteigt ${p.ertragswert_max_gewerbeanteil_prozent} %; dafür gelten die Berliner Liegenschaftszinssätze nicht.`], hinweise };
  }

  // Restnutzungsdauer
  const rnd = m.restnutzungsdauer('ertragswert', { baujahr: objekt.baujahr, alter, bauzustand: objekt.bauzustand, ausstattung: objekt.ausstattung });
  if (rnd.rnd == null) return { status: 'nicht_anwendbar', gruende: [rnd.grund], hinweise };
  if (rnd.abschlag) hinweise.push(`Wegen der Ausstattung wurde die Restnutzungsdauer um ${fmt(Math.abs(rnd.abschlag))} Jahre gekürzt (Berliner Modell für Baujahre bis 1948).`);

  // Liegenschaftszinssatz
  const lz = m.liegenschaftszins({ objektmiete, gebietsgruppe: ort.Gebietsgruppe, altbezirk: ort.Altbezirk, baujahr: objekt.baujahr, stadtlage: ort.Stadtlage, gewerbeanteilProzent });

  // Bodenwert mit GFZ-Anpassung
  const gfzTatsaechlich = objekt.gfz ?? (objekt.geschossflaeche > 0 && objekt.grundstuecksflaeche > 0 ? runde(objekt.geschossflaeche / objekt.grundstuecksflaeche, 2) : null);
  const gewerbeflaechenanteil = wohnNutzflaeche > 0 ? (gewerbe.flaeche || 0) / wohnNutzflaeche : 0;
  const anpassung = m.gfzAnpassung({ nutzungZone: zone.nutzung, gfzZone: zone.gfz, gfzTatsaechlich, gewerbeflaechenanteil });
  if (anpassung.hinweis) hinweise.push(anpassung.hinweis);

  const ergebnis = ertragswert({
    nutzungen,
    rnd: rnd.rnd,
    liegenschaftszins: lz.gerundet,
    bodenwert: { flaeche: objekt.grundstuecksflaeche, bodenrichtwert: zone.brw, faktor: anpassung.faktor },
    marktanpassungsfaktor: m.marktanpassungsfaktor,
    bog: objekt.bog || [],
    rundung: { barwertfaktor: p.barwertfaktor_nachkommastellen, ergebnis: p.ergebnis_rundung_euro },
  });

  // Gültigkeitsprüfungen
  const bodenwertJeM2 = objekt.grundstuecksflaeche > 0 ? runde(ergebnis.bodenwert / objekt.grundstuecksflaeche, 0) : null;
  const pruefungen = [
    m.pruefung('ertragswert', 'objektmiete_tabelle', objektmiete),
    m.pruefung('ertragswert', 'objektmiete', objektmiete),
    m.pruefung('ertragswert', 'gewerbeanteil', gewerbeanteilProzent),
    m.pruefung('ertragswert', 'grundstuecksflaeche', objekt.grundstuecksflaeche),
    m.pruefung('ertragswert', 'wohn_nutzflaeche', wohnNutzflaeche),
    m.pruefung('ertragswert', 'gfz', gfzTatsaechlich),
    m.pruefung('ertragswert', 'brw', zone.brw),
    m.pruefung('ertragswert', 'bodenwert_m2', bodenwertJeM2),
    m.pruefung('ertragswert', 'alter', alter),
    m.pruefung('ertragswert', 'rnd', rnd.rnd),
  ].filter(Boolean);
  const verletzt = pruefungen.filter((x) => !x.ok);
  for (const v of verletzt.filter((x) => !x.sperrend)) {
    hinweise.push(`${v.groesse} (${fmt(v.wert)} ${v.einheit}) liegt außerhalb des Bereichs, in dem die Liegenschaftszinssätze statistisch gesichert sind (${fmt(v.min)}–${fmt(v.max)} ${v.einheit}).`);
  }
  const sperrend = verletzt.filter((x) => x.sperrend);
  if (sperrend.length) {
    return {
      status: 'ausserhalb',
      gruende: sperrend.map((v) => `${v.groesse}: ${fmt(v.wert)} ${v.einheit} liegt außerhalb des Gültigkeitsbereichs der Berliner Liegenschaftszinssätze (${fmt(v.min)}–${fmt(v.max)} ${v.einheit}).`),
      hinweise, pruefungen,
    };
  }
  if (ergebnis.status === 'liquidation') {
    return { status: 'liquidation', gruende: ergebnis.hinweise, hinweise, pruefungen, ergebnis };
  }

  return {
    status: 'ok',
    verfahren: 'ertragswert',
    ergebnis,
    wert: ergebnis.ertragswertGerundet,
    spanne: m.spanne(ergebnis.ertragswertGerundet),
    modell: {
      objektmiete, gewerbeanteilProzent, wohnNutzflaeche, alter, rnd, liegenschaftszins: lz,
      gebietsgruppe: ort.Gebietsgruppe, altbezirk: ort.Altbezirk, stadtlage: ort.Stadtlage,
      bodenrichtwert: zone.brw, bodenrichtwertStichtag: p.brw_stichtag_modell, bodenrichtwertAktuell: adresse?.zone?.aktuell?.brw ?? null,
      gfzZone: zone.gfz, gfzTatsaechlich, gfzAnpassung: anpassung, stichtagFaktoren: p.stichtag_faktoren,
    },
    pruefungen,
    hinweise,
  };
}
