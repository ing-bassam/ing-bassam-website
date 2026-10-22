// Kaufbegutachtung – Oberfläche des Hinweis-Assistenten für die deutsche und die
// englische Seite (Sprache aus <html lang>). Läuft ausschließlich im Browser
// (Kern: kaufbegutachtung.js, Daten: daten.js). Nichts wird gesendet oder
// gespeichert – keine Cookies, kein localStorage. Die Anfrage entsteht als E-Mail
// im eigenen E-Mail-Programm; Unterlagen hängt man dort an. Preise zeigt die Seite
// nicht: Sie kommen mit dem Angebot per E-Mail.
//
// Anker: #wohnung / #haus (deutsch) und #flat / #house (englisch) wählen die
// Objektart vor – das sind die Ziele der QR-Codes in den Broschüren.
import {
  DATEN, SCHALTER, anfrage, anteil, eingabeLesen, euro, hinweise, unterlagen, unterlagenText,
} from "./kaufbegutachtung.js";

const sprache = document.documentElement.lang === "en" ? "en" : "de";
const t = DATEN.seite[sprache].ui;
const form = document.getElementById("kauf-form");
const $ = (id) => document.getElementById(id);

// Zustand, der nicht im Formular steht.
const zustand = {
  objekt: "etw",
  vorhanden: { etw: new Set(), efh: new Set() },
  unterlagenSchluessel: "",
};

function esc(text) {
  return String(text).replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[z]));
}

function ersetzen(vorlage, werte) {
  return vorlage.replace(/\{(\w+)\}/g, (_, name) => (name in werte ? String(werte[name]) : `{${name}}`));
}

// ------------------------------------------------------------ Aufbau

function auswahlFuellen(id, liste) {
  $(id).innerHTML = `<option value="">${esc(t.bitte_waehlen)}</option>`
    + liste.map((x) => `<option value="${esc(x.id)}">${esc(x[sprache])}</option>`).join("");
}

function schalterAufbauen(ziel, namen, quelle) {
  $(ziel).innerHTML = namen.map((name) => {
    const s = quelle[name];
    return `<label class="haken" data-schalter-objekt="${s.objekt}"><input type="checkbox" name="${name}" value="1"><span>${esc(s[sprache])}</span></label>`;
  }).join("");
}

function objektSetzen(objekt, { anker = true } = {}) {
  zustand.objekt = objekt === "efh" ? "efh" : "etw";
  const radio = form.querySelector(`input[name=objekt][value="${zustand.objekt}"]`);
  if (radio) radio.checked = true;
  document.querySelectorAll("[data-objekt-nur]").forEach((el) => { el.hidden = el.dataset.objektNur !== zustand.objekt; });
  document.querySelectorAll("[data-schalter-objekt]").forEach((el) => { el.hidden = el.dataset.schalterObjekt !== zustand.objekt; });
  if (anker) {
    const ziel = `#${DATEN.anker[sprache][zustand.objekt]}`;
    if (location.hash !== ziel) history.replaceState(null, "", ziel);
  }
}

// ------------------------------------------------------------ Lesen

function formularLesen() {
  const d = new FormData(form);
  const roh = {
    objekt: zustand.objekt,
    flaeche: d.get("flaeche"),
    baujahr: d.get("baujahr"),
    heizung: d.get("heizung"),
    nutzung: d.get("nutzung"),
    region: d.get("region"),
  };
  for (const name of SCHALTER) roh[name] = d.get(name) === "1";
  return eingabeLesen(roh, sprache);
}

// ------------------------------------------------------------ Ausgabe

function hinweiseZeigen(e) {
  const h = hinweise(e, sprache);
  const mitAngaben = e.baujahr !== null || e.heizung || e.nutzung || e.region || SCHALTER.some((n) => e[n]);
  $("hinweise-status").textContent = h.anzahl === 1 ? t.hinweise_eins : ersetzen(t.hinweise_anzahl, { n: h.anzahl });
  const sprachAttr = sprache === "en" ? ' lang="de"' : "";
  const quelle = (q) => (q.url
    ? `${esc(t.quelle)}: <a href="${esc(q.url)}" rel="noopener"${sprachAttr}>${esc(q.titel)}</a>`
    : `${esc(t.quelle)}: <span${sprachAttr}>${esc(q.titel)}</span>`);
  const gruppen = h.gruppen.map((g) => `
      <section class="hinweis-gruppe" data-kategorie="${g.kategorie}">
        <h4>${esc(g.titel)}</h4>
        <ul class="hinweis-karten">${g.regeln.map((r) => `
          <li class="hinweis-karte">
            <p class="hinweis-titel">${esc(r.titel)}</p>
            <p>${esc(r.text)}</p>
            <p class="quelle">${quelle(r.quelle)}</p>
          </li>`).join("")}
        </ul>
      </section>`).join("");
  $("hinweise-ergebnis").innerHTML = `
      ${mitAngaben ? "" : `<p class="meldung info">${esc(t.hinweise_leer)}</p>`}
      ${gruppen}
      <p class="rechtsstand">${esc(DATEN.text[sprache].rechtsstand)}</p>`;
}

function unterlagenZeigen(e) {
  const liste = unterlagen(e, sprache);
  const schluessel = `${e.objekt}:${liste.map((u) => u.id).join(",")}`;
  if (schluessel === zustand.unterlagenSchluessel) return;
  zustand.unterlagenSchluessel = schluessel;
  const da = zustand.vorhanden[e.objekt];
  const teile = [];
  for (const prio of [1, 2, 3]) {
    const teil = liste.filter((u) => u.prio === prio);
    if (!teil.length) continue;
    teile.push(`
      <h4 class="prio prio-${prio}">${esc(DATEN.text[sprache].prio[String(prio)])}</h4>
      <ul class="unterlagen-haken">${teil.map((u) => `
        <li>
          <label class="haken"><input type="checkbox" name="vorhanden" value="${esc(u.id)}"${da.has(u.id) ? " checked" : ""}><span>${esc(u.text)} <span class="liegt-vor">(${esc(t.liegt_vor)})</span></span></label>
          <details class="erklaerung"><summary>${esc(t.wo)}</summary><p>${esc(u.wo)}</p></details>
        </li>`).join("")}
      </ul>`);
  }
  $("unterlagen-ergebnis").innerHTML = teile.join("");
}

function anfrageZeigen(e) {
  const a = anfrage({
    eingabe: e, vorhanden: [...zustand.vorhanden[e.objekt]],
    adresse: $("adresse").value, termin: $("termin").value, sprache,
  });
  $("anfrage-link").href = a.href;
  $("mail-vorschau").textContent = `${a.betreff}\n\n${a.text}`;
  return a;
}

function anteilZeigen() {
  const betrag = anteil($("anteil-kosten").value, $("anteil-zaehler").value, $("anteil-nenner").value);
  $("anteil-ergebnis").textContent = betrag === null ? t.anteil_fehlt : ersetzen(t.anteil_ergebnis, { betrag: euro(betrag, sprache) });
}

function fehlerZeigen(fehler) {
  for (const feld of ["flaeche", "baujahr"]) {
    $(`${feld}-fehler`).textContent = fehler[feld] || "";
    $(feld).setAttribute("aria-invalid", fehler[feld] ? "true" : "false");
  }
}

function aktualisieren() {
  const { eingabe, fehler } = formularLesen();
  fehlerZeigen(fehler);
  hinweiseZeigen(eingabe);
  unterlagenZeigen(eingabe);
  anfrageZeigen(eingabe);
  anteilZeigen();
}

// ------------------------------------------------------------ Kopieren

async function kopieren(text, status, ersatz, okText) {
  try {
    await navigator.clipboard.writeText(text);
    ersatz.hidden = true;
    status.textContent = okText;
  } catch {
    ersatz.value = text;
    ersatz.hidden = false;
    ersatz.focus();
    ersatz.select();
    status.textContent = t.kopieren_fehler;
  }
}

// ------------------------------------------------------------ Ereignisse

const objektAusAnker = () => Object.entries(DATEN.anker[sprache])
  .find(([, anker]) => anker === decodeURIComponent(location.hash.slice(1)).toLowerCase())?.[0];

function ausAnker() {
  const objekt = objektAusAnker();
  if (!objekt) return;
  if (objekt !== zustand.objekt) {
    objektSetzen(objekt, { anker: false });
    aktualisieren();
  }
  $(DATEN.anker[sprache][objekt]).scrollIntoView({ block: "start" });
}

form.addEventListener("change", (ev) => {
  const ziel = ev.target;
  if (ziel.name === "objekt") {
    objektSetzen(ziel.value);
  } else if (ziel.name === "vorhanden") {
    if (ziel.checked) zustand.vorhanden[zustand.objekt].add(ziel.value); else zustand.vorhanden[zustand.objekt].delete(ziel.value);
  }
  aktualisieren();
});
form.addEventListener("input", (ev) => {
  if (["flaeche", "baujahr", "adresse", "termin"].includes(ev.target.name) || ev.target.id.startsWith("anteil-")) aktualisieren();
});
form.addEventListener("submit", (ev) => ev.preventDefault());

$("liste-kopieren").addEventListener("click", () => {
  const { eingabe } = formularLesen();
  kopieren(unterlagenText(eingabe, [...zustand.vorhanden[eingabe.objekt]], sprache), $("liste-status"), $("liste-text"), t.kopiert);
});
$("mail-kopieren").addEventListener("click", () => {
  const a = anfrageZeigen(formularLesen().eingabe);
  kopieren(`${a.betreff}\n\n${a.text}`, $("mail-status"), $("mail-text"), t.mail_kopiert);
});
window.addEventListener("hashchange", ausAnker);

// ------------------------------------------------------------ Start

auswahlFuellen("heizung", DATEN.eingaben.heizung);
auswahlFuellen("nutzung", DATEN.eingaben.nutzung);
auswahlFuellen("region", DATEN.eingaben.region);
schalterAufbauen("schalter", SCHALTER, DATEN.eingaben.schalter);
const start = objektAusAnker();
objektSetzen(start || form.querySelector("input[name=objekt]:checked")?.value || "etw", { anker: Boolean(start) });
form.hidden = false;
aktualisieren();
// Der Browser springt beim Laden zum Anker, bevor das Formular sichtbar ist; danach
// verschiebt das eingeblendete Formular die Seite. Deshalb den Anker erneut anspringen.
if (start) {
  const springen = () => $(DATEN.anker[sprache][start]).scrollIntoView({ block: "start", behavior: "instant" });
  requestAnimationFrame(springen);
  if (document.readyState !== "complete") window.addEventListener("load", springen, { once: true });
}
