/*
 * Assistent des Wertrechners: führt durch die Eingabe, sucht die Adresse in
 * den PLZ-Dateien, ruft die Berliner Modellschicht auf und zeigt das Ergebnis.
 *
 * Alles bleibt im Browser: keine Cookies, kein localStorage, keine Aufrufe
 * fremder Dienste. Geladen werden nur /wertrechner/data/marktdaten.json und
 * die jeweils eine Datei /wertrechner/data/adressen/<PLZ>.json.
 */
import { modell, berlinSachwert, berlinErtragswert } from './berlin.js';
import { uebersetzer } from './texte.js';

const SPRACHE = document.documentElement.lang === 'en' ? 'en' : 'de';
const t = uebersetzer(SPRACHE);
const DATEN = new URL('./data/', import.meta.url);
const KONTAKT = 'info@ing-bassam.de';
const app = document.getElementById('app');

const SCHRITTE = {
  sachwert: ['objektart', 'adresse', 'grundstueck', 'gebaeude', 'besonderheiten', 'ergebnis'],
  ertragswert: ['objektart', 'adresse', 'grundstueck', 'mietobjekt', 'besonderheiten', 'ergebnis'],
};
const BESONDERHEITEN = ['bauschaeden', 'altlasten', 'baulasten', 'denkmal', 'rechte'];

let m = null;                     // Berliner Modell (aus marktdaten.json)
let daten = null;
const plzCache = new Map();
const zustand = {
  schritt: 0,
  objektart: null,
  adresse: null,                  // { plz, strasse, hnr, eintrag, zone, wohnlage, ortsteil, datei }
  grundstueck: { flaeche: '', flurstueck: '' },
  gebaeude: { gebaeudestellung: 'freistehend', unterkellert: 'ja', geschosse: '1', dachgeschoss: 'voll_ausgebaut', baujahr: '', bauzustand: 'normal', konstruktion: 'massiv', flaechenart: 'grundflaeche', flaeche: '', nebenanlagen: '' },
  mietobjekt: { baujahr: '', bauzustand: 'normal', zentralheizung: true, baeder: true, wohnflaeche: '', wohneinheiten: '', mieteWohnen: '', gewerbe: false, gewerbeflaeche: '', mieteGewerbe: '', gewerbeart: 'buero_laden', garagen: '', stellplaetze: '', mieteSonstiges: '', geschossflaeche: '' },
  besonderheiten: Object.fromEntries(BESONDERHEITEN.map((b) => [b, 'weissNicht'])),
  ergebnis: null,
};

/* ------------------------------------------------------------------------
 * Hilfen
 * ---------------------------------------------------------------------- */

const h = (text) => String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const geld = (n) => new Intl.NumberFormat(t('sprache'), { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
const geldCent = (n) => new Intl.NumberFormat(t('sprache'), { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
const zahl = (n, stellen = 2) => new Intl.NumberFormat(t('sprache'), { maximumFractionDigits: stellen }).format(n);
const datum = (iso) => (iso ? new Intl.DateTimeFormat(t('sprache'), { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(iso)) : '–');

/** Liest eine Zahl aus der Eingabe (deutsch „1.234,5“ oder englisch „1,234.5“). */
function zahlLesen(text) {
  let s = String(text ?? '').trim().replace(/\s/g, '');
  if (!s) return null;
  if (SPRACHE === 'de') s = s.replace(/\./g, '').replace(',', '.');
  else s = s.replace(/,/g, '');
  const n = Number(s);
  return Number.isFinite(n) ? n : NaN;
}

function schritte() {
  return SCHRITTE[zustand.objektart === 'mfh' ? 'ertragswert' : 'sachwert'];
}

function aktuellerSchritt() {
  return schritte()[zustand.schritt];
}

function wahl(name, optionen, ausgewaehlt, kompakt = false) {
  return `<ul class="wahl${kompakt ? ' kompakt' : ''}">${optionen.map((o) => `
    <li><label><input type="radio" name="${name}" value="${h(o.wert)}"${o.wert === ausgewaehlt ? ' checked' : ''}>
      <span class="titel">${h(o.titel)}</span>${o.text ? `<span class="text">${h(o.text)}</span>` : ''}</label></li>`).join('')}</ul>`;
}

function erklaerung(text) {
  return `<details class="erklaerung"><summary>${h(t('wasIstDas'))}</summary><p>${h(text)}</p></details>`;
}

function feld({ name, label, wert, einheit, hilfe, optional, inputmode = 'decimal', max = 420 }) {
  // Breite über Klassen statt style-Attribut – die CSP erlaubt keine Inline-Styles.
  const breite = max <= 220 ? ' kurz' : max <= 260 ? ' mittel' : max >= 500 ? ' breit' : '';
  return `<div class="block" data-feld="${name}">
    <label for="f-${name}">${h(label)}${optional ? ` <span class="optional">(${h(t('optional'))})</span>` : ''}</label>
    <div class="eingabe${breite}"><input id="f-${name}" name="${name}" type="text" inputmode="${inputmode}" autocomplete="off" value="${h(wert)}"${optional ? '' : ' required'} aria-describedby="e-${name}">${einheit ? `<span class="einheit">${h(einheit)}</span>` : ''}</div>
    ${hilfe ? `<p class="hilfe">${h(hilfe)}</p>` : ''}
    <p class="fehler" id="e-${name}" aria-live="polite"></p>
  </div>`;
}

const pfeil = '<svg class="pfeil" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>';

/* ------------------------------------------------------------------------
 * Rahmen: Fortschritt, Inhalt, Navigation
 * ---------------------------------------------------------------------- */

function render() {
  const liste = schritte();
  const name = aktuellerSchritt();
  const nr = zustand.schritt + 1;
  const prozent = Math.round((zustand.schritt / (liste.length - 1)) * 100);
  const inhalt = ANSICHTEN[name]();
  const letzterEingabeschritt = name === 'besonderheiten';
  const istErgebnis = name === 'ergebnis';

  app.innerHTML = `
    <div class="fortschritt" aria-hidden="${istErgebnis}">
      <div class="fortschritt-zeile"><b>${h(t(`label_${name}`))}</b><span>${h(t('schritt', { n: nr, gesamt: liste.length }))}</span></div>
      <div class="fortschritt-schiene"><div class="fortschritt-balken"></div></div>
      <ol class="fortschritt-punkte">${liste.map((s, i) => `<li${i === zustand.schritt ? ' aria-current="step"' : ''}${i < zustand.schritt ? ' class="erledigt"' : ''}>${h(t(`label_${s}`))}</li>`).join('')}</ol>
    </div>
    <form class="karte-inhalt einblenden" id="schrittform" novalidate>
      <div class="schritt-kopf"><h2 id="schritt-titel" tabindex="-1">${h(inhalt.titel)}</h2>${inhalt.text ? `<p>${h(inhalt.text)}</p>` : ''}</div>
      ${inhalt.html}
      <div class="navigation">
        ${zustand.schritt > 0 && !istErgebnis ? `<button type="button" class="btn btn-outline zurueck" data-zurueck>${pfeil}${h(t('zurueck'))}</button>` : '<span></span>'}
        ${istErgebnis ? `<button type="button" class="btn btn-outline" data-neu>${h(t('neu'))}</button><button type="button" class="btn btn-outline" data-drucken>${h(t('drucken'))}</button>`
      : inhalt.ohneWeiter ? '' : `<button type="submit" class="btn btn-primary">${h(letzterEingabeschritt ? t('berechnen') : t('weiter'))}${pfeil}</button>`}
      </div>
    </form>`;

  app.querySelector('.fortschritt-balken').style.width = `${prozent}%`;   // CSSOM statt style-Attribut (CSP)
  const form = document.getElementById('schrittform');
  form.addEventListener('submit', (e) => { e.preventDefault(); weiter(); });
  form.querySelector('[data-zurueck]')?.addEventListener('click', zurueck);
  form.querySelector('[data-neu]')?.addEventListener('click', neuStarten);
  form.querySelector('[data-drucken]')?.addEventListener('click', () => window.print());
  inhalt.nachher?.(form);
  document.getElementById('schritt-titel').focus({ preventScroll: zustand.schritt === 0 });
  if (zustand.schritt > 0) app.scrollIntoView({ block: 'start', behavior: 'smooth' });
}

function weiter() {
  const name = aktuellerSchritt();
  const form = document.getElementById('schrittform');
  const ok = PRUEFEN[name] ? PRUEFEN[name](form) : true;
  if (!ok) return;
  if (name === 'objektart' && zustand.objektart === 'etw') { zustand.schritt = 0; renderEtw(); return; }
  if (name === 'besonderheiten') zustand.ergebnis = berechnen();
  zustand.schritt = Math.min(zustand.schritt + 1, schritte().length - 1);
  render();
}

function zurueck() {
  zustand.schritt = Math.max(zustand.schritt - 1, 0);
  render();
}

function neuStarten() {
  zustand.schritt = 0;
  zustand.ergebnis = null;
  render();
}

/* ------------------------------------------------------------------------
 * Ansichten der Schritte
 * ---------------------------------------------------------------------- */

const ANSICHTEN = {
  objektart() {
    return {
      titel: t('objektartTitel'), text: t('objektartText'),
      html: `<fieldset class="block"><legend class="sr-only">${h(t('objektartTitel'))}</legend>
        ${wahl('objektart', ['efh', 'zfh', 'mfh', 'etw'].map((a) => ({ wert: a, titel: t(`objektart_${a}`), text: t(`objektart_${a}_text`) })), zustand.objektart)}
        <p class="fehler" id="e-objektart" aria-live="polite"></p></fieldset>`,
    };
  },

  adresse() {
    const a = zustand.adresse;
    return {
      titel: t('adresseTitel'), text: t('adresseText'),
      html: `
        <div class="zeile">
          ${feld({ name: 'plz', label: t('plz'), wert: a?.plz || '', hilfe: t('plzHilfe'), inputmode: 'numeric', max: 220 })}
        </div>
        <div class="block vorschlaege" data-feld="strasse" ${a?.datei ? '' : 'hidden'}>
          <label for="f-strasse">${h(t('strasse'))}</label>
          <div class="eingabe breit"><input id="f-strasse" type="text" autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list" aria-controls="strassen-liste" value="${h(a?.strasse || '')}" aria-describedby="e-strasse"></div>
          <ul id="strassen-liste" role="listbox" hidden></ul>
          <p class="hilfe">${h(t('strasseHilfe'))}</p>
          <p class="fehler" id="e-strasse" aria-live="polite"></p>
        </div>
        <div class="block" data-feld="hnr" ${a?.strasse ? '' : 'hidden'}>
          <label for="f-hnr">${h(t('hausnummer'))}</label>
          <div class="eingabe kurz"><select id="f-hnr" aria-describedby="e-hnr"></select></div>
          <p class="hilfe">${h(t('hausnummerHilfe'))}</p>
          <p class="fehler" id="e-hnr" aria-live="polite"></p>
        </div>
        <div id="fund"></div>`,
      nachher: adresseVerdrahten,
    };
  },

  grundstueck() {
    const maxFlaeche = m.pruefung(zustand.objektart === 'mfh' ? 'ertragswert' : 'sachwert', 'grundstuecksflaeche', 1)?.max;
    return {
      titel: t('grundstueckTitel'), text: t('grundstueckText'),
      html: `<div class="zeile">
          ${feld({ name: 'grundstuecksflaeche', label: t('grundstuecksflaeche'), wert: zustand.grundstueck.flaeche, einheit: t('m2') })}
          ${feld({ name: 'flurstueck', label: t('flurstueck'), wert: zustand.grundstueck.flurstueck, hilfe: t('flurstueckHilfe'), optional: true, inputmode: 'text' })}
        </div>
        <p class="meldung info">${h(t('grossesGrundstueck', { max: zahl(maxFlaeche || 0, 0) }))}</p>`,
    };
  },

  gebaeude() {
    const g = zustand.gebaeude;
    const flaechenHilfe = { bgf: t('flaeche_bgf_hilfe'), grundflaeche: t('flaeche_grundflaeche_hilfe'), wohnflaeche: t('flaeche_wohnflaeche_hilfe') };
    return {
      titel: t('gebaeudeTitel'), text: t('gebaeudeText'),
      html: `
        <fieldset class="block"><legend class="legende">${h(t('gebaeudestellung'))}</legend>
          ${wahl('gebaeudestellung', ['freistehend', 'doppelhaushaelfte', 'reihenendhaus', 'reihenmittelhaus'].map((s) => ({ wert: s, titel: t(`stellung_${s}`) })), g.gebaeudestellung, true)}</fieldset>
        <div class="zeile">
          <fieldset class="block"><legend class="legende">${h(t('keller'))}</legend>
            ${wahl('unterkellert', [{ wert: 'ja', titel: t('keller_ja') }, { wert: 'nein', titel: t('keller_nein') }], g.unterkellert, true)}
            ${erklaerung(t('kellerErklaerung'))}</fieldset>
          <fieldset class="block"><legend class="legende">${h(t('geschosse'))}</legend>
            ${wahl('geschosse', ['1', '2', '3'].map((n) => ({ wert: n, titel: t(`geschosse_${n}`) })), g.geschosse, true)}</fieldset>
        </div>
        <fieldset class="block"><legend class="legende">${h(t('dachgeschoss'))}</legend>
          ${wahl('dachgeschoss', ['voll_ausgebaut', 'nicht_ausgebaut', 'flachdach'].map((d) => ({ wert: d, titel: t(`dach_${d}`), text: t(`dach_${d}_text`) })), g.dachgeschoss, true)}</fieldset>
        <div class="zeile">
          <div>${feld({ name: 'baujahr', label: t('baujahr'), wert: g.baujahr, inputmode: 'numeric', max: 220 })}${erklaerung(t('baujahrErklaerung'))}</div>
          <fieldset class="block"><legend class="legende">${h(t('konstruktion'))}</legend>
            ${wahl('konstruktion', ['massiv', 'fertighaus_massiv', 'fertighaus_holz'].map((k) => ({ wert: k, titel: t(`konstruktion_${k}`) })), g.konstruktion, true)}</fieldset>
        </div>
        <fieldset class="block"><legend class="legende">${h(t('bauzustand'))}</legend>
          ${wahl('bauzustand', ['gut', 'normal', 'schlecht'].map((z) => ({ wert: z, titel: t(`zustand_${z}`), text: t(`zustand_${z}_text`) })), g.bauzustand)}
          ${erklaerung(t('zustandErklaerung'))}</fieldset>
        <fieldset class="block"><legend class="legende">${h(t('flaecheTitel'))}</legend>
          <p class="hilfe">${h(t('flaecheText'))}</p>
          ${wahl('flaechenart', ['grundflaeche', 'bgf', 'wohnflaeche'].map((f) => ({ wert: f, titel: t(`flaeche_${f}`) })), g.flaechenart, true)}
          ${feld({ name: 'flaeche', label: t(`flaeche_${g.flaechenart}`), wert: g.flaeche, einheit: t('m2'), hilfe: flaechenHilfe[g.flaechenart], max: 260 })}
        </fieldset>
        ${feld({ name: 'nebenanlagen', label: t('nebenanlagen'), wert: g.nebenanlagen, einheit: t('euro'), hilfe: t('nebenanlagenHilfe'), optional: true, max: 260 })}
        ${zustand.objektart === 'zfh' ? `<p class="meldung info">${h(t('zweifamilienhausHinweis'))}</p>` : ''}`,
      nachher(form) {
        form.querySelectorAll('input[name="flaechenart"]').forEach((r) => r.addEventListener('change', () => {
          zustand.gebaeude.flaechenart = r.value;
          const block = form.querySelector('[data-feld="flaeche"]');
          block.querySelector('label').textContent = t(`flaeche_${r.value}`);
          block.querySelector('.hilfe').textContent = flaechenHilfe[r.value];
        }));
      },
    };
  },

  mietobjekt() {
    const o = zustand.mietobjekt;
    const altbau = Number(o.baujahr) > 0 && Number(o.baujahr) <= 1948;
    return {
      titel: t('mietobjektTitel'), text: t('mietobjektText'),
      html: `
        <div class="zeile">
          <div>${feld({ name: 'baujahr', label: t('baujahr'), wert: o.baujahr, inputmode: 'numeric', max: 220 })}${erklaerung(t('baujahrErklaerung'))}</div>
          <fieldset class="block"><legend class="legende">${h(t('bauzustand'))}</legend>
            ${wahl('bauzustand', ['gut', 'normal', 'schlecht'].map((z) => ({ wert: z, titel: t(`zustand_${z}`), text: t(`zustand_${z}_text`) })), o.bauzustand, true)}
            ${erklaerung(t('zustandErklaerung'))}</fieldset>
        </div>
        <fieldset class="block" id="ausstattung" ${altbau ? '' : 'hidden'}><legend class="legende">${h(t('ausstattungTitel'))}</legend>
          <label class="haken"><input type="checkbox" name="zentralheizung"${o.zentralheizung ? ' checked' : ''}> ${h(t('zentralheizung'))}</label>
          <label class="haken"><input type="checkbox" name="baeder"${o.baeder ? ' checked' : ''}> ${h(t('baeder'))}</label></fieldset>
        <h3 class="gruppe-titel">${h(t('wohnen'))}</h3>
        <div class="zeile">
          ${feld({ name: 'wohnflaeche', label: t('wohnflaecheGesamt'), wert: o.wohnflaeche, einheit: t('m2') })}
          ${feld({ name: 'wohneinheiten', label: t('wohneinheiten'), wert: o.wohneinheiten, inputmode: 'numeric' })}
          ${feld({ name: 'mieteWohnen', label: t('mieteWohnen'), wert: o.mieteWohnen, einheit: t('euro') })}
        </div>
        <h3 class="gruppe-titel">${h(t('gewerbe'))}</h3>
        <label class="haken"><input type="checkbox" name="gewerbe"${o.gewerbe ? ' checked' : ''}> ${h(t('gewerbeVorhanden'))}</label>
        <div id="gewerbe-felder" ${o.gewerbe ? '' : 'hidden'}>
          <div class="zeile">
            ${feld({ name: 'gewerbeflaeche', label: t('gewerbeflaeche'), wert: o.gewerbeflaeche, einheit: t('m2') })}
            ${feld({ name: 'mieteGewerbe', label: t('mieteGewerbe'), wert: o.mieteGewerbe, einheit: t('euro') })}
          </div>
          <fieldset class="block"><legend class="legende">${h(t('gewerbeart'))}</legend>
            ${wahl('gewerbeart', ['buero_laden', 'nebennutzung'].map((a) => ({ wert: a, titel: t(`gewerbe_${a}`) })), o.gewerbeart, true)}</fieldset>
        </div>
        <h3 class="gruppe-titel">${h(t('sonstiges'))} <span class="optional">(${h(t('optional'))})</span></h3>
        <div class="zeile">
          ${feld({ name: 'garagen', label: t('garagen'), wert: o.garagen, optional: true, inputmode: 'numeric' })}
          ${feld({ name: 'stellplaetze', label: t('stellplaetze'), wert: o.stellplaetze, optional: true, inputmode: 'numeric' })}
          ${feld({ name: 'mieteSonstiges', label: t('mieteSonstiges'), wert: o.mieteSonstiges, einheit: t('euro'), optional: true })}
        </div>
        ${feld({ name: 'geschossflaeche', label: t('geschossflaeche'), wert: o.geschossflaeche, einheit: t('m2'), hilfe: t('geschossflaecheHilfe') })}`,
      nachher(form) {
        form.querySelector('input[name="gewerbe"]').addEventListener('change', (e) => { form.querySelector('#gewerbe-felder').hidden = !e.target.checked; });
        form.querySelector('input[name="baujahr"]').addEventListener('input', (e) => { const j = Number(e.target.value); form.querySelector('#ausstattung').hidden = !(j > 0 && j <= 1948); });
      },
    };
  },

  besonderheiten() {
    return {
      titel: t('besonderheitenTitel'), text: t('besonderheitenText'),
      html: `<div>${BESONDERHEITEN.map((b) => `
        <div class="frage"><span id="q-${b}">${h(t(`besonderheit_${b}`))}</span>
          <div class="dreier" role="radiogroup" aria-labelledby="q-${b}">
            ${['ja', 'nein', 'weissNicht'].map((w) => `<label><input type="radio" name="b-${b}" value="${w}"${zustand.besonderheiten[b] === w ? ' checked' : ''}>${h(t(w))}</label>`).join('')}
          </div></div>`).join('')}</div>`,
    };
  },

  ergebnis() {
    const e = zustand.ergebnis;
    if (!e || e.status !== 'ok') return keinWert(e);
    return ergebnisAnsicht(e);
  },
};

/* ------------------------------------------------------------------------
 * Prüfungen je Schritt (lesen die Eingaben in den Zustand)
 * ---------------------------------------------------------------------- */

function fehlerSetzen(form, name, text) {
  const ziel = form.querySelector(`#e-${name}`);
  if (ziel) ziel.textContent = text || '';
  const input = form.querySelector(`#f-${name}`);
  if (input) input.setAttribute('aria-invalid', text ? 'true' : 'false');
  return !text;
}

function zahlPruefen(form, name, { optional = false, min = 0, max = Infinity, ganz = false } = {}) {
  const roh = form.querySelector(`#f-${name}`)?.value ?? '';
  const n = zahlLesen(roh);
  if (n === null) {
    fehlerSetzen(form, name, optional ? '' : t('fehlerPflicht'));
    return optional ? { ok: true, wert: null } : { ok: false };
  }
  if (Number.isNaN(n) || (ganz && !Number.isInteger(n))) { fehlerSetzen(form, name, t('fehlerZahl')); return { ok: false }; }
  if (n < min || n > max) { fehlerSetzen(form, name, t('fehlerBereich', { min: zahl(min, 0), max: zahl(max, 0) })); return { ok: false }; }
  fehlerSetzen(form, name, '');
  return { ok: true, wert: n };
}

const radio = (form, name) => form.querySelector(`input[name="${name}"]:checked`)?.value;

const PRUEFEN = {
  objektart(form) {
    zustand.objektart = radio(form, 'objektart') || null;
    const ok = Boolean(zustand.objektart);
    form.querySelector('#e-objektart').textContent = ok ? '' : t('fehlerPflicht');
    return ok;
  },
  adresse(form) {
    const a = zustand.adresse;
    if (!a?.datei) return fehlerSetzen(form, 'plz', t('plzFehlt'));
    if (!a.strasse) return fehlerSetzen(form, 'strasse', t('strasseFehlt'));
    if (!a.eintrag) return fehlerSetzen(form, 'hnr', t('hausnummerFehlt'));
    return true;
  },
  grundstueck(form) {
    const f = zahlPruefen(form, 'grundstuecksflaeche', { min: 1, max: 100000 });
    zustand.grundstueck.flaeche = form.querySelector('#f-grundstuecksflaeche').value;
    zustand.grundstueck.flurstueck = form.querySelector('#f-flurstueck').value.trim();
    return f.ok;
  },
  gebaeude(form) {
    const g = zustand.gebaeude;
    for (const n of ['gebaeudestellung', 'unterkellert', 'geschosse', 'dachgeschoss', 'bauzustand', 'konstruktion', 'flaechenart']) g[n] = radio(form, n) || g[n];
    const jahr = new Date().getFullYear();
    const b = zahlPruefen(form, 'baujahr', { min: 1800, max: jahr, ganz: true });
    const f = zahlPruefen(form, 'flaeche', { min: 10, max: 5000 });
    const n = zahlPruefen(form, 'nebenanlagen', { optional: true, min: 0, max: 500000 });
    g.baujahr = form.querySelector('#f-baujahr').value;
    g.flaeche = form.querySelector('#f-flaeche').value;
    g.nebenanlagen = form.querySelector('#f-nebenanlagen').value;
    return b.ok && f.ok && n.ok;
  },
  mietobjekt(form) {
    const o = zustand.mietobjekt;
    o.bauzustand = radio(form, 'bauzustand') || o.bauzustand;
    o.gewerbeart = radio(form, 'gewerbeart') || o.gewerbeart;
    o.zentralheizung = form.querySelector('input[name="zentralheizung"]').checked;
    o.baeder = form.querySelector('input[name="baeder"]').checked;
    o.gewerbe = form.querySelector('input[name="gewerbe"]').checked;
    const jahr = new Date().getFullYear();
    const pruefungen = [
      zahlPruefen(form, 'baujahr', { min: 1800, max: jahr, ganz: true }),
      zahlPruefen(form, 'wohnflaeche', { min: 20, max: 50000 }),
      zahlPruefen(form, 'wohneinheiten', { min: 1, max: 1000, ganz: true }),
      zahlPruefen(form, 'mieteWohnen', { min: 0, max: 10000000 }),
      zahlPruefen(form, 'garagen', { optional: true, min: 0, max: 1000, ganz: true }),
      zahlPruefen(form, 'stellplaetze', { optional: true, min: 0, max: 1000, ganz: true }),
      zahlPruefen(form, 'mieteSonstiges', { optional: true, min: 0, max: 1000000 }),
      zahlPruefen(form, 'geschossflaeche', { min: 20, max: 100000 }),
    ];
    if (o.gewerbe) {
      pruefungen.push(zahlPruefen(form, 'gewerbeflaeche', { min: 1, max: 50000 }), zahlPruefen(form, 'mieteGewerbe', { min: 0, max: 10000000 }));
    } else {
      fehlerSetzen(form, 'gewerbeflaeche', ''); fehlerSetzen(form, 'mieteGewerbe', '');
    }
    for (const n of ['baujahr', 'wohnflaeche', 'wohneinheiten', 'mieteWohnen', 'gewerbeflaeche', 'mieteGewerbe', 'garagen', 'stellplaetze', 'mieteSonstiges', 'geschossflaeche']) {
      o[n] = form.querySelector(`#f-${n}`).value;
    }
    return pruefungen.every((p) => p.ok);
  },
  besonderheiten(form) {
    for (const b of BESONDERHEITEN) zustand.besonderheiten[b] = radio(form, `b-${b}`) || 'weissNicht';
    return true;
  },
};

/* ------------------------------------------------------------------------
 * Adresssuche
 * ---------------------------------------------------------------------- */

async function plzLaden(plz) {
  if (plzCache.has(plz)) return plzCache.get(plz);
  const antwort = await fetch(new URL(`adressen/${plz}.json`, DATEN), { cache: 'force-cache' });
  if (!antwort.ok) { plzCache.set(plz, null); return null; }
  const datei = await antwort.json();
  plzCache.set(plz, datei);
  return datei;
}

function adresseVerdrahten(form) {
  const plzInput = form.querySelector('#f-plz');
  const strasseBlock = form.querySelector('[data-feld="strasse"]');
  const strasseInput = form.querySelector('#f-strasse');
  const liste = form.querySelector('#strassen-liste');
  const hnrBlock = form.querySelector('[data-feld="hnr"]');
  const hnrSelect = form.querySelector('#f-hnr');
  let treffer = [];
  let markiert = -1;

  const zeigeFund = () => { form.querySelector('#fund').innerHTML = zustand.adresse?.eintrag ? fundAnsicht(zustand.adresse) : ''; };

  const hausnummernFuellen = () => {
    const a = zustand.adresse;
    const idx = a.datei.strassen.indexOf(a.strasse);
    const eintraege = a.datei.adressen.filter((e) => e[0] === idx);
    hnrSelect.innerHTML = `<option value="">–</option>${eintraege.map((e) => `<option value="${h(e[1])}"${e[1] === a.hnr ? ' selected' : ''}>${h(e[1])}</option>`).join('')}`;
    hnrBlock.hidden = false;
  };

  const eintragWaehlen = (hnr) => {
    const a = zustand.adresse;
    const idx = a.datei.strassen.indexOf(a.strasse);
    const e = a.datei.adressen.find((x) => x[0] === idx && x[1] === hnr);
    a.hnr = hnr;
    a.eintrag = e || null;
    if (e) {
      a.zone = { modell: a.datei.zonen[e[2]]?.modell || null, aktuell: a.datei.zonen[e[3]]?.aktuell || null };
      a.wohnlage = e[4];
      a.ortsteil = a.datei.ortsteile[e[5]];
      fehlerSetzen(form, 'hnr', '');
    }
    zeigeFund();
  };

  const strasseWaehlen = (name) => {
    zustand.adresse.strasse = name;
    zustand.adresse.hnr = null;
    zustand.adresse.eintrag = null;
    strasseInput.value = name;
    liste.hidden = true;
    strasseInput.setAttribute('aria-expanded', 'false');
    fehlerSetzen(form, 'strasse', '');
    hausnummernFuellen();
    zeigeFund();
    hnrSelect.focus();
  };

  const vorschlaegeZeigen = () => {
    const q = strasseInput.value.trim().toLowerCase();
    const strassen = zustand.adresse?.datei?.strassen || [];
    treffer = q ? strassen.filter((s) => s.toLowerCase().includes(q)).sort((x, y) => Number(y.toLowerCase().startsWith(q)) - Number(x.toLowerCase().startsWith(q))).slice(0, 12) : [];
    markiert = -1;
    liste.innerHTML = treffer.map((s, i) => `<li role="option" id="str-${i}" data-i="${i}">${h(s)}</li>`).join('');
    liste.hidden = treffer.length === 0;
    strasseInput.setAttribute('aria-expanded', String(treffer.length > 0));
  };

  plzInput.addEventListener('input', async () => {
    const plz = plzInput.value.replace(/\D/g, '').slice(0, 5);
    plzInput.value = plz;
    if (plz.length < 5) { strasseBlock.hidden = true; hnrBlock.hidden = true; zustand.adresse = null; zeigeFund(); return; }
    fehlerSetzen(form, 'plz', '');
    const datei = await plzLaden(plz);
    if (plzInput.value !== plz) return;
    if (!datei) { zustand.adresse = null; strasseBlock.hidden = true; hnrBlock.hidden = true; zeigeFund(); fehlerSetzen(form, 'plz', t('plzFehlt')); return; }
    zustand.adresse = { plz, datei, strasse: null, hnr: null, eintrag: null };
    strasseInput.value = '';
    strasseBlock.hidden = false;
    hnrBlock.hidden = true;
    zeigeFund();
    strasseInput.focus();
  });

  strasseInput.addEventListener('input', () => { zustand.adresse.strasse = null; zustand.adresse.eintrag = null; hnrBlock.hidden = true; zeigeFund(); vorschlaegeZeigen(); });
  strasseInput.addEventListener('focus', vorschlaegeZeigen);
  strasseInput.addEventListener('keydown', (e) => {
    if (liste.hidden) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); markiert = Math.min(markiert + 1, treffer.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); markiert = Math.max(markiert - 1, 0); }
    else if (e.key === 'Enter') { e.preventDefault(); if (markiert >= 0) strasseWaehlen(treffer[markiert]); else if (treffer.length === 1) strasseWaehlen(treffer[0]); return; }
    else if (e.key === 'Escape') { liste.hidden = true; return; }
    else return;
    liste.querySelectorAll('li').forEach((li, i) => li.setAttribute('aria-selected', String(i === markiert)));
    strasseInput.setAttribute('aria-activedescendant', markiert >= 0 ? `str-${markiert}` : '');
  });
  // pointerdown ohne Fokuswechsel, damit das Eingabefeld kein blur auslöst und
  // die Liste beim Klick noch da ist; die Auswahl selbst passiert beim click.
  liste.addEventListener('pointerdown', (e) => e.preventDefault());
  liste.addEventListener('click', (e) => { const li = e.target.closest('li'); if (li) strasseWaehlen(treffer[Number(li.dataset.i)]); });
  strasseInput.addEventListener('blur', () => { setTimeout(() => { liste.hidden = true; }, 200); });
  hnrSelect.addEventListener('change', () => eintragWaehlen(hnrSelect.value));

  if (zustand.adresse?.datei) {
    strasseBlock.hidden = false;
    if (zustand.adresse.strasse) hausnummernFuellen();
    zeigeFund();
  }
}

function fundAnsicht(a) {
  const z = a.zone?.modell;
  // Für Eigenheime zählt nur Wohnbauland, für Mietshäuser auch Gewerbezonen (LZ 2025 S. 2)
  const erlaubt = zustand.objektart === 'mfh' ? ['W', 'W-EFH', 'M1', 'M2', 'G', 'Gp'] : ['W', 'W-EFH', 'M1', 'M2'];
  const bauland = z && erlaubt.includes(z.nutzung);
  const ort = m.ortsteil(a.ortsteil);
  return `<div class="fund einblenden" aria-live="polite">
    <div class="fund-kopf">${h(t('adressfundTitel'))} · ${h(a.strasse)} ${h(a.hnr)}, ${h(a.plz)} Berlin</div>
    ${z ? `<div class="fund-brw">
      <span class="zahl">${zahl(z.brw, 0)}<small>${h(t('einheit_euro_m2'))}</small></span>
      <span class="label">${h(t('brwModell', { datum: datum(a.datei.stichtage.modell) }))}</span>
      ${a.zone.aktuell ? `<span class="aktuell">${h(t('brwAktuell', { datum: datum(a.datei.stichtage.aktuell) }))}: <b>${zahl(a.zone.aktuell.brw, 0)} ${h(t('einheit_euro_m2'))}</b></span>` : ''}
    </div>
    ${erklaerung(t('brwErklaerung'))}` : `<p class="meldung warnung">${h(t('keinBauland', { nutzung: '–' }))}</p>`}
    <dl class="fund-raster">
      <div><dt>${h(t('nutzungZone'))}</dt><dd>${h(z?.nutzung || '–')}</dd></div>
      <div><dt>${h(t('gfzZone'))}</dt><dd>${z?.gfz != null ? zahl(z.gfz, 2) : '–'}</dd></div>
      <div><dt>${h(t('wohnlage'))}</dt><dd>${h(t(`wohnlage_${a.wohnlage ?? 0}`))}</dd></div>
      <div><dt>${h(t('ortsteil'))}</dt><dd>${h(a.ortsteil)}${ort ? ` <small>(${h(t('altbezirk'))} ${h(ort.Altbezirk)})</small>` : ''}</dd></div>
    </dl>
    ${z && !bauland ? `<p class="meldung warnung">${h(t('keinBauland', { nutzung: z.nutzung }))}</p>` : ''}
    ${erklaerung(t('wohnlageErklaerung'))}
    <p class="fund-quelle">${h(t('quelleBrw'))}</p>
  </div>`;
}

/* ------------------------------------------------------------------------
 * Berechnung
 * ---------------------------------------------------------------------- */

function adresseFuerModell() {
  const a = zustand.adresse;
  return { zone: a.zone, wohnlage: a.wohnlage, ortsteil: a.ortsteil, plz: a.plz, strasse: a.strasse, hnr: a.hnr };
}

function berechnen() {
  const jahr = new Date().getFullYear();
  try {
    if (zustand.objektart === 'mfh') {
      const o = zustand.mietobjekt;
      return berlinErtragswert({
        baujahr: zahlLesen(o.baujahr), bauzustand: o.bauzustand,
        ausstattung: { zentralheizung: o.zentralheizung, baeder: o.baeder },
        wohnen: { flaeche: zahlLesen(o.wohnflaeche), einheiten: zahlLesen(o.wohneinheiten), mieteMonat: zahlLesen(o.mieteWohnen) },
        gewerbe: o.gewerbe ? { flaeche: zahlLesen(o.gewerbeflaeche), mieteMonat: zahlLesen(o.mieteGewerbe), art: o.gewerbeart } : null,
        sonstiges: { garagen: zahlLesen(o.garagen) || 0, stellplaetze: zahlLesen(o.stellplaetze) || 0, mieteMonat: zahlLesen(o.mieteSonstiges) || 0 },
        grundstuecksflaeche: zahlLesen(zustand.grundstueck.flaeche), geschossflaeche: zahlLesen(o.geschossflaeche),
      }, adresseFuerModell(), m, { jahr });
    }
    const g = zustand.gebaeude;
    const flaeche = zahlLesen(g.flaeche);
    return berlinSachwert({
      gebaeudestellung: g.gebaeudestellung, unterkellert: g.unterkellert === 'ja', geschosse: Number(g.geschosse), dachgeschoss: g.dachgeschoss,
      baujahr: zahlLesen(g.baujahr), bauzustand: g.bauzustand, konstruktion: g.konstruktion,
      bgf: g.flaechenart === 'bgf' ? flaeche : undefined, grundflaeche: g.flaechenart === 'grundflaeche' ? flaeche : undefined, wohnflaeche: g.flaechenart === 'wohnflaeche' ? flaeche : undefined,
      grundstuecksflaeche: zahlLesen(zustand.grundstueck.flaeche), nebenanlagen: zahlLesen(g.nebenanlagen) || 0,
    }, adresseFuerModell(), m, { jahr });
  } catch (fehler) {
    console.error(fehler);
    return { status: 'nicht_anwendbar', gruende: [fehler.message], hinweise: [] };
  }
}

/* ------------------------------------------------------------------------
 * Ergebnisseite
 * ---------------------------------------------------------------------- */

function besonderheitenListe() {
  return BESONDERHEITEN.filter((b) => zustand.besonderheiten[b] !== 'nein').map((b) => `${t(`besonderheit_${b}`)} (${t(zustand.besonderheiten[b])})`);
}

function eckdatenSachwert(e) {
  const g = zustand.gebaeude;
  const mo = e.modell;
  return [
    [t('ek_objekt'), t(`objektart_${zustand.objektart}`), `${t(`stellung_${g.gebaeudestellung}`)}, ${t(`geschosse_${g.geschosse}`)}, ${t(`dach_${g.dachgeschoss}`)}`],
    [t('ek_adresse'), `${zustand.adresse.strasse} ${zustand.adresse.hnr}`, `${zustand.adresse.plz} Berlin, ${zustand.adresse.ortsteil}`],
    [t('ek_grundstueck'), `${zahl(zahlLesen(zustand.grundstueck.flaeche), 0)} ${t('m2')}`, `${t('ek_bodenwert')} ${geld(e.ergebnis.bodenwert)} · ${zahl(mo.bodenrichtwert, 0)} ${t('einheit_euro_m2')}`],
    [t('ek_flaeche'), `${t('mp_bgf')} ${zahl(mo.bgf, 0)} ${t('m2')}`, mo.bgfGeschaetzt ? t(`mp_bgf_${mo.bgfGeschaetzt.art}`) : ''],
    [t('ek_baujahr'), `${g.baujahr} · ${t(`zustand_${g.bauzustand}`)}`, `${t('mp_rnd')} ${mo.rnd.rnd} ${t('jahre')}`],
    [t('ek_gebaeudesachwert'), geld(e.ergebnis.summeGebaeude), `${t('mp_swf')} ${zahl(mo.sachwertfaktor.gerundet, 2)}`],
  ];
}

function eckdatenErtragswert(e) {
  const o = zustand.mietobjekt;
  const mo = e.modell;
  return [
    [t('ek_objekt'), t(`objektart_${zustand.objektart}`), `${t('ek_mieteinheiten')}: ${o.wohneinheiten}${o.gewerbe ? ' + ' + t('gewerbe') : ''}`],
    [t('ek_adresse'), `${zustand.adresse.strasse} ${zustand.adresse.hnr}`, `${zustand.adresse.plz} Berlin, ${zustand.adresse.ortsteil} · ${mo.gebietsgruppe}`],
    [t('ek_grundstueck'), `${zahl(zahlLesen(zustand.grundstueck.flaeche), 0)} ${t('m2')}`, `${t('ek_bodenwert')} ${geld(e.ergebnis.bodenwert)} · ${zahl(mo.bodenrichtwert, 0)} ${t('einheit_euro_m2')}`],
    [t('ek_rohertrag'), geld(e.ergebnis.rohertrag), `${t('mp_objektmiete')}: ${zahl(mo.objektmiete, 2)} ${t('einheit_euro_m2')}`],
    [t('ek_reinertrag'), geld(e.ergebnis.reinertrag), `${t('mp_lz')} ${zahl(mo.liegenschaftszins.gerundet, 1)} %`],
    [t('ek_baujahr'), `${o.baujahr} · ${t(`zustand_${o.bauzustand}`)}`, `${t('mp_rnd')} ${mo.rnd.rnd} ${t('jahre')}`],
  ];
}

function rechenwegTabelle(e) {
  const letzte = e.ergebnis.schritte.length;
  const summen = new Set(['Vorläufiger Sachwert des Grundstücks', 'Marktangepasster vorläufiger Sachwert', 'Vorläufiger Ertragswert', 'Marktangepasster vorläufiger Ertragswert', 'Jahresreinertrag', 'Jahresrohertrag gesamt']);
  return `<div class="tabelle-huelle"><table class="rechenweg">
    <thead><tr><th>#</th><th>${h(t('spalteSchritt'))}</th><th>${h(t('spalteFormel'))}</th><th>${h(t('spalteWert'))}</th><th>${h(t('spalteGrundlage'))}</th></tr></thead>
    <tbody>${e.ergebnis.schritte.map((s) => `<tr class="${s.nr >= letzte - 1 ? 'ergebnis' : summen.has(s.bezeichnung) ? 'summe' : ''}">
      <td class="nr">${s.nr}</td><td>${h(s.bezeichnung)}</td><td class="formel">${h(s.formel)}</td>
      <td class="wert">${s.einheit === '€' ? geldCent(s.wert) : s.einheit ? `${zahl(s.wert, 4)} ${h(s.einheit)}` : zahl(s.wert, 4)}</td>
      <td class="grundlage">${h(s.grundlage)}</td></tr>`).join('')}</tbody></table></div>`;
}

function bestandteileListe(f, einheit) {
  return `<ul class="bestandteile">${f.bestandteile.map((b) => `<li><span>${h(b.text)}</span><b>${b.wert >= 0 ? '+' : '−'} ${zahl(Math.abs(b.wert), 4)}</b></li>`).join('')}
    <li class="summe"><span>= ${zahl(f.ungerundet, 4)}${einheit} → ${zahl(f.gerundet, f.stellen)}${einheit}</span></li></ul>`;
}

function parameterListe(e) {
  const mo = e.modell;
  const zeilen = [];
  if (e.verfahren === 'sachwert') {
    zeilen.push([t('mp_nhkTyp'), mo.nhkTyp], [t('mp_nhk', { stufe: mo.standardstufe }), `${zahl(mo.nhk, 0)} ${t('einheit_euro_m2')}`],
      [t('mp_bgf'), `${zahl(mo.bgf, 0)} ${t('m2')}${mo.bgfGeschaetzt ? ` (${t(`mp_bgf_${mo.bgfGeschaetzt.art}`)})` : ''}`],
      [t('mp_bpi'), zahl(mo.baupreisindex, 1)], [t('mp_regionalfaktor'), zahl(mo.regionalfaktor, 2)],
      [t('mp_gnd'), `${mo.gnd} ${t('jahre')}`], [t('mp_alter'), `${mo.alter} ${t('jahre')}`], [t('mp_rnd'), `${mo.rnd.rnd} ${t('jahre')}`],
      [t('mp_brw', { datum: datum(mo.bodenrichtwertStichtag) }), `${zahl(mo.bodenrichtwert, 0)} ${t('einheit_euro_m2')}`],
      [t('mp_brwAktuell'), mo.bodenrichtwertAktuell != null ? `${zahl(mo.bodenrichtwertAktuell, 0)} ${t('einheit_euro_m2')}` : '–'],
      [t('mp_wohnlage'), mo.wohnlage], [t('mp_altbezirk'), `${mo.altbezirk} / ${mo.swfGruppe}`],
      [t('mp_swf'), `${zahl(mo.sachwertfaktor.gerundet, 2)} (${zahl(mo.sachwertfaktor.ungerundet, 4)})`], [t('mp_stichtag'), datum(mo.stichtagFaktoren)]);
  } else {
    zeilen.push([t('mp_objektmiete'), `${zahl(mo.objektmiete, 2)} ${t('einheit_euro_m2')}`], [t('mp_gewerbeanteil'), `${zahl(mo.gewerbeanteilProzent, 1)} %`],
      [t('mp_gebietsgruppe'), `${mo.gebietsgruppe} / ${mo.stadtlage}`], [t('mp_altbezirk'), mo.altbezirk],
      [t('mp_lz'), `${zahl(mo.liegenschaftszins.gerundet, 1)} % (${zahl(mo.liegenschaftszins.ungerundet, 3)} %)`],
      [t('mp_alter'), `${mo.alter} ${t('jahre')}`], [t('mp_rnd'), `${mo.rnd.rnd} ${t('jahre')}`],
      [t('mp_brw', { datum: datum(mo.bodenrichtwertStichtag) }), `${zahl(mo.bodenrichtwert, 0)} ${t('einheit_euro_m2')}`],
      [t('mp_brwAktuell'), mo.bodenrichtwertAktuell != null ? `${zahl(mo.bodenrichtwertAktuell, 0)} ${t('einheit_euro_m2')}` : '–'],
      [t('mp_gfz'), `${mo.gfzZone != null ? zahl(mo.gfzZone, 2) : '–'} / ${mo.gfzTatsaechlich != null ? zahl(mo.gfzTatsaechlich, 2) : '–'}`],
      [t('mp_gfzFaktor'), zahl(mo.gfzAnpassung.faktor, 4)], [t('mp_stichtag'), datum(mo.stichtagFaktoren)]);
  }
  return `<dl class="parameter">${zeilen.map(([k, v]) => `<div><dt>${h(k)}</dt><dd>${h(v)}</dd></div>`).join('')}</dl>`;
}

function quellenListe() {
  return `<ul>${daten.blaetter.Quellen.map((q) => `<li><a href="${h(q.Link)}" rel="noopener noreferrer" target="_blank">${h(q.Dokument)}</a> – ${h(q['Quelle/Stand'])}</li>`).join('')}<li>${h(t('quelleBrw'))}</li></ul>`;
}

function ergebnisAnsicht(e) {
  const besonderheiten = besonderheitenListe();
  const faktor = e.verfahren === 'sachwert' ? e.modell.sachwertfaktor : e.modell.liegenschaftszins;
  const einheit = e.verfahren === 'sachwert' ? '' : ' %';
  const eck = e.verfahren === 'sachwert' ? eckdatenSachwert(e) : eckdatenErtragswert(e);
  return {
    titel: t('ergebnisTitel'), text: '',
    html: `
      <p class="ergebnis-verfahren">${h(t(`ergebnisVerfahren_${e.verfahren}`))}</p>
      <div class="spanne" role="region" aria-label="${h(t('ergebnisSpanne'))}">
        <div class="label">${h(t('ergebnisSpanne'))}</div>
        <div class="zahlen"><span>${geld(e.spanne.von)}</span><span class="bis">–</span><span>${geld(e.spanne.bis)}</span></div>
        <p class="mitte">${h(t('ergebnisMitte'))}: <b>${geld(e.wert)}</b></p>
        <div class="balken" aria-hidden="true"><i></i><b></b></div>
        <div class="skala" aria-hidden="true"><span>−${e.spanne.prozent} %</span><span>+${e.spanne.prozent} %</span></div>
        <p class="stand">${h(t('ergebnisStand', { stichtag: datum(e.modell.stichtagFaktoren), brwdatum: datum(e.modell.bodenrichtwertStichtag), heute: datum(new Date().toISOString()) }))}</p>
      </div>
      <p class="hilfe abstand">${h(t('ergebnisStreuung', { prozent: e.spanne.prozent }))}</p>
      <ul class="eckdaten">${eck.map(([k, v, s]) => `<li><span class="k">${h(k)}</span><span class="v">${h(v)}${s ? `<small>${h(s)}</small>` : ''}</span></li>`).join('')}</ul>

      <details class="abschnitt"><summary>${h(t('rechenweg'))}</summary><div class="abschnitt-inhalt">
        <p>${h(t('rechenwegText'))}</p>${rechenwegTabelle(e)}
        <p><strong>${h(t('faktorBestandteile'))} – ${h(e.verfahren === 'sachwert' ? t('mp_swf') : t('mp_lz'))}</strong></p>${bestandteileListe(faktor, einheit)}
      </div></details>
      <details class="abschnitt"><summary>${h(t('modellparameter'))}</summary><div class="abschnitt-inhalt">${parameterListe(e)}</div></details>
      ${e.hinweise.length ? `<details class="abschnitt" open><summary>${h(t('hinweise'))}</summary><div class="abschnitt-inhalt"><ul>${e.hinweise.map((x) => `<li>${h(x)}</li>`).join('')}</ul></div></details>` : ''}
      <details class="abschnitt"><summary>${h(t('nichtBeruecksichtigt'))}</summary><div class="abschnitt-inhalt">
        <ul>${t('nichtBeruecksichtigtListe').map((x) => `<li>${h(x)}</li>`).join('')}</ul>
        <p>${besonderheiten.length ? h(t('besonderheitenAngegeben', { liste: besonderheiten.join('; ') })) : h(t('keineBesonderheiten'))}</p>
      </div></details>
      <details class="abschnitt"><summary>${h(t('quellen'))}</summary><div class="abschnitt-inhalt">${quellenListe()}</div></details>
      <p class="rechtlich"><strong>${h(t('ergebnisTitel'))}.</strong> ${h(t('rechtlich'))}</p>
      ${ctaAnsicht(besonderheiten.length > 0)}`,
    nachher(form) { form.querySelector('[data-anfrage]').addEventListener('click', anfrageSenden); },
  };
}

function ctaAnsicht(mitBesonderheiten, knopf = t('ctaKnopf')) {
  return `<div class="cta"><h3>${h(t('ctaTitel'))}</h3><p>${h(mitBesonderheiten ? t('ctaTextBesonderheiten') : t('ctaText'))}</p>
    <div class="aktionen"><button type="button" class="btn btn-primary" data-anfrage>${h(knopf)}${pfeil}</button><a class="btn btn-ghost" href="/#kontakt">${h(t('zurStartseite'))}</a></div>
    <p class="klein">${h(t('ctaHinweis'))}</p></div>`;
}

function keinWert(e) {
  const gruende = e?.gruende || [];
  const titelGrund = e?.status === 'ausserhalb' ? t('grund_ausserhalb') : e?.status === 'liquidation' ? t('grund_liquidation') : t('grund_nicht_anwendbar');
  return {
    titel: t('keinWertTitel'), text: t('keinWertText'),
    html: `<div class="kein-wert">
      <p><strong>${h(titelGrund)}</strong></p>
      <ul class="gruende">${gruende.map((g) => `<li>${h(g)}</li>`).join('')}</ul>
      ${e?.hinweise?.length ? `<ul class="gruende neutral">${e.hinweise.map((x) => `<li>${h(x)}</li>`).join('')}</ul>` : ''}
      ${ctaAnsicht(false, t('anfrageKnopf'))}
    </div>`,
    nachher(form) { form.querySelector('[data-anfrage]').addEventListener('click', anfrageSenden); },
  };
}

function renderEtw() {
  app.innerHTML = `<div class="karte-inhalt einblenden">
    <div class="schritt-kopf"><h2 tabindex="-1" id="schritt-titel">${h(t('etwTitel'))}</h2><p>${h(t('etwText'))}</p></div>
    ${ctaAnsicht(false, t('anfrageKnopf'))}
    <div class="navigation"><button type="button" class="btn btn-outline zurueck" data-zurueck>${pfeil}${h(t('zurueck'))}</button></div></div>`;
  app.querySelector('[data-zurueck]').addEventListener('click', render);
  app.querySelector('[data-anfrage]').addEventListener('click', anfrageSenden);
  document.getElementById('schritt-titel').focus();
}

/** Baut die Anfrage-E-Mail erst beim Klick – vorher verlässt nichts den Browser. */
function anfrageSenden() {
  const a = zustand.adresse;
  const adresse = a?.eintrag ? `${a.strasse} ${a.hnr}, ${a.plz} Berlin` : (SPRACHE === 'de' ? 'Adresse folgt' : 'address to follow');
  const zeilen = [`${t('ek_objekt')}: ${zustand.objektart ? t(`objektart_${zustand.objektart}`) : '–'}`, `${t('ek_adresse')}: ${adresse}`];
  if (zustand.grundstueck.flaeche) zeilen.push(`${t('grundstuecksflaeche')}: ${zustand.grundstueck.flaeche} m²${zustand.grundstueck.flurstueck ? ` (${t('flurstueck')} ${zustand.grundstueck.flurstueck})` : ''}`);
  if (zustand.objektart === 'mfh') {
    const o = zustand.mietobjekt;
    zeilen.push(`${t('baujahr')}: ${o.baujahr} · ${t('bauzustand')}: ${t(`zustand_${o.bauzustand}`)}`, `${t('wohnflaecheGesamt')}: ${o.wohnflaeche} m² · ${t('wohneinheiten')}: ${o.wohneinheiten} · ${t('mieteWohnen')}: ${o.mieteWohnen} €`);
    if (o.gewerbe) zeilen.push(`${t('gewerbeflaeche')}: ${o.gewerbeflaeche} m² · ${t('mieteGewerbe')}: ${o.mieteGewerbe} €`);
  } else if (zustand.objektart && zustand.objektart !== 'etw') {
    const g = zustand.gebaeude;
    if (g.baujahr) zeilen.push(`${t('baujahr')}: ${g.baujahr} · ${t('bauzustand')}: ${t(`zustand_${g.bauzustand}`)}`, `${t('gebaeudestellung')}: ${t(`stellung_${g.gebaeudestellung}`)}, ${t(`geschosse_${g.geschosse}`)}, ${t(`dach_${g.dachgeschoss}`)}, ${g.unterkellert === 'ja' ? t('keller_ja') : t('keller_nein')}`, `${t(`flaeche_${g.flaechenart}`)}: ${g.flaeche} m²`);
  }
  const bes = besonderheitenListe();
  if (bes.length) zeilen.push(`${t('besonderheitenTitel')}: ${bes.join('; ')}`);
  const e = zustand.ergebnis;
  if (e?.status === 'ok') zeilen.push(`${t('ergebnisTitel')}: ${geld(e.spanne.von)} – ${geld(e.spanne.bis)} (${t('ergebnisMitte')} ${geld(e.wert)})`);
  else if (e) zeilen.push(`${t('keinWertTitel')}: ${(e.gruende || []).join(' ')}`);
  zeilen.push(`${datum(new Date().toISOString())} · ${location.href}`);
  const body = t('mailAnrede') + zeilen.map((z) => `- ${z}`).join('\n') + '\n' + t('mailSchluss');
  window.location.href = `mailto:${KONTAKT}?subject=${encodeURIComponent(t('mailBetreff', { adresse }))}&body=${encodeURIComponent(body)}`;
}

/* ------------------------------------------------------------------------
 * Start
 * ---------------------------------------------------------------------- */

async function start() {
  try {
    const antwort = await fetch(new URL('marktdaten.json', DATEN), { cache: 'force-cache' });
    if (!antwort.ok) throw new Error(`HTTP ${antwort.status}`);
    daten = await antwort.json();
    m = modell(daten);
    render();
  } catch (fehler) {
    console.error(fehler);
    app.innerHTML = `<div class="karte-inhalt"><p class="meldung fehler">${h(t('fehlerLaden'))}</p></div>`;
  }
}

start();
