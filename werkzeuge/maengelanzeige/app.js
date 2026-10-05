// Mängelanzeige-Generator – Oberfläche. Der Brief entsteht ausschließlich im
// Browser (Rechenkern: brief.js). Bewusst ohne Adresszeilen-Speicher und ohne
// localStorage: Die Angaben enthalten Namen und Adressen und bleiben nur so
// lange im Formular, wie die Seite offen ist.
import { ANLAGEN, PRUEFLISTE, briefErzeugen, briefText } from "./brief.js";

const form = document.getElementById("anzeige-form");
const ausgabe = document.getElementById("ergebnis");
const liste = document.getElementById("maengel");
const vorlage = document.getElementById("mangel-vorlage");

function isoHeute(plusTage = 0) {
  const d = new Date();
  d.setDate(d.getDate() + plusTage);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function esc(text) {
  return String(text).replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[z]));
}

// --------------------------------------------------------------- Mängel

function mangelHinzufuegen(werte = {}) {
  const zeile = vorlage.content.firstElementChild.cloneNode(true);
  const nr = liste.children.length + 1;
  zeile.querySelector(".mangel-nr").textContent = `Mangel ${nr}`;
  zeile.querySelectorAll("label").forEach((label) => {
    const feld = label.querySelector("input, textarea");
    const id = `mangel-${nr}-${feld.name}`;
    feld.id = id;
    label.setAttribute("for", id);
  });
  if (werte.datum === undefined) zeile.querySelector("input[name=datum]").value = isoHeute();
  zeile.querySelector(".entfernen").addEventListener("click", () => {
    if (liste.children.length === 1) return;
    zeile.remove();
    [...liste.children].forEach((z, i) => { z.querySelector(".mangel-nr").textContent = `Mangel ${i + 1}`; });
    aktualisieren();
  });
  liste.append(zeile);
  return zeile;
}

function maengelLesen() {
  return [...liste.children].map((zeile) => ({
    ort: zeile.querySelector("input[name=ort]").value,
    erscheinung: zeile.querySelector("textarea[name=erscheinung]").value,
    datum: zeile.querySelector("input[name=datum]").value,
  }));
}

// -------------------------------------------------------------- Eingabe

function eingabeLesen() {
  const d = new FormData(form);
  const wert = (name) => (d.get(name) ?? "").toString();
  return {
    einzelperson: d.get("einzelperson") === "ja",
    absender: { name: wert("abs-name"), strasse: wert("abs-strasse"), plzOrt: wert("abs-plzort"), telefon: wert("abs-telefon"), email: wert("abs-email") },
    empfaenger: { firma: wert("emp-firma"), zusatz: wert("emp-zusatz"), strasse: wert("emp-strasse"), plzOrt: wert("emp-plzort") },
    ort: wert("ort"),
    datum: wert("datum"),
    bauvorhaben: wert("bauvorhaben"),
    leistung: wert("leistung"),
    vertragsdatum: wert("vertragsdatum"),
    vertragsart: wert("vertragsart") || "bgb",
    abnahme: wert("abnahme") || "nein",
    abnahmeDatum: wert("abnahmeDatum"),
    vorbehaltNr: wert("vorbehaltNr"),
    maengel: maengelLesen(),
    frist: wert("frist"),
    rueckmeldung: wert("rueckmeldung"),
    zeiten: wert("zeiten"),
    zugang: wert("zugang"),
    ansprechpartner: wert("ansprechpartner"),
    gefahr: d.get("gefahr") === "ja",
    sicherung: wert("sicherung"),
    anlagen: d.getAll("anlagen").map(String),
    anlagenWeitere: wert("anlagenWeitere"),
  };
}

function felderUmschalten(eingabe) {
  document.querySelectorAll("[data-nur-abnahme]").forEach((el) => { el.hidden = eingabe.abnahme === "nein"; });
  document.querySelectorAll("[data-nur-vorbehalt]").forEach((el) => { el.hidden = eingabe.abnahme !== "vorbehalt"; });
  document.querySelectorAll("[data-nur-gefahr]").forEach((el) => { el.hidden = !eingabe.gefahr; });
}

// -------------------------------------------------------------- Ausgabe

function briefHtml(brief) {
  const absaetze = brief.absaetze.map((a) => (typeof a === "string"
    ? `<p>${esc(a)}</p>`
    : `<ol>${a.liste.map((z) => `<li>${esc(z)}</li>`).join("")}</ol>`)).join("");
  return `
      <article class="brief" id="brief" lang="de">
        <div class="brief-kopf">
          <address class="absender">${brief.absender.map(esc).join("<br>")}</address>
          <p class="brief-datum">${esc(brief.ortDatum)}</p>
        </div>
        <address class="empfaenger">${brief.empfaenger.map(esc).join("<br>")}</address>
        <p class="betreff">${esc(brief.betreff)}</p>
        <p>${esc(brief.anrede)}</p>
        ${absaetze}
        <p class="gruss">${esc(brief.gruss)}</p>
        <p class="unterschrift">${esc(brief.unterschrift)}</p>
        ${brief.anlagen.length ? `<div class="anlagen"><b>Anlagen</b><ul>${brief.anlagen.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : ""}
      </article>`;
}

function rendern(e) {
  ausgabe.hidden = false;
  const hinweise = e.hinweise.length
    ? `<details class="abschnitt" ${e.ok ? "" : "open"}><summary>Hinweise zu Ihren Angaben (${e.hinweise.length})</summary><div class="abschnitt-inhalt"><ul class="hinweise">${e.hinweise.map((h) => `<li>${esc(h)}</li>`).join("")}</ul></div></details>`
    : "";
  if (!e.ok) {
    ausgabe.innerHTML = `
      <div class="ergebnis-kopf"><span class="verfahren">Vorschau</span><h2>Noch nicht vollständig</h2></div>
      <div class="meldung warnung"><strong>Damit das Schreiben entsteht, fehlt noch:</strong><ul class="hinweise">${e.fehler.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></div>
      ${hinweise}`;
    return;
  }
  const pruefliste = PRUEFLISTE.map((p, i) => `<li><label class="haken"><input type="checkbox" id="pruef-${i}"><span>${esc(p)}</span></label></li>`).join("");
  ausgabe.innerHTML = `
      <div class="ergebnis-kopf">
        <span class="verfahren">Vorschau · aktualisiert sich mit jeder Eingabe</span>
        <h2>Ihre Mängelanzeige</h2>
      </div>
      ${briefHtml(e.brief)}
      <div class="aktionen-zeile">
        <button type="button" class="btn btn-primary" data-drucken>Drucken oder als PDF speichern</button>
        <button type="button" class="btn btn-outline" data-kopieren>Text kopieren</button>
        <a class="btn btn-leer" href="/vorlagen/maengelanzeige-mit-fristsetzung/maengelanzeige-mit-fristsetzung.docx" download>Word-Vorlage herunterladen</a>
      </div>
      ${hinweise}
      <details class="abschnitt" open>
        <summary>Vor dem Absenden prüfen</summary>
        <div class="abschnitt-inhalt"><ul class="pruefliste-haken">${pruefliste}</ul></div>
      </details>
      <div class="cta">
        <h3>Streit über den Mangel? Dann zählt die Feststellung vor der Beseitigung</h3>
        <p>Bestreitet das Unternehmen den Mangel oder bessert es nach, ohne dass die Ursache geklärt ist, geht der Befund verloren. Eine technische Beweissicherung hält den Zustand fest; eine gutachterliche Stellungnahme liefert Ihrem Anwalt Ort, Erscheinungsbild, Ursache und Kosten.</p>
        <div class="aktionen">
          <a class="btn btn-primary" href="/leistungen/technische-beweissicherung/">Beweissicherung ab 690 €</a>
          <a class="btn btn-ghost" href="/leistungen/privatgutachten-bauprozess/">Stellungnahme für den Streitfall</a>
        </div>
        <p class="klein">Rückmeldung innerhalb eines Werktags · Berlin und Brandenburg</p>
      </div>
      <p class="rechtlich"><strong>Keine Rechtsberatung.</strong> Der Generator setzt das Musterschreiben des Büros mit Ihren Angaben zusammen. Welche Mängelrechte Ihnen zustehen, ob die Frist angemessen ist und ob die VOB/B wirksam vereinbart wurde, beurteilt ein Rechtsanwalt – spätestens vor Kündigung, Rücktritt oder Klage. Ihre Angaben verlassen diese Seite nicht und werden beim Schließen gelöscht.</p>`;
  ausgabe.querySelector("[data-drucken]").addEventListener("click", () => window.print());
  ausgabe.querySelector("[data-kopieren]").addEventListener("click", async (ev) => {
    try {
      await navigator.clipboard.writeText(briefText(e.brief));
      ev.currentTarget.textContent = "Text kopiert";
    } catch {
      ev.currentTarget.textContent = "Kopieren nicht möglich – bitte markieren und kopieren";
    }
  });
}

function aktualisieren() {
  const eingabe = eingabeLesen();
  felderUmschalten(eingabe);
  rendern(briefErzeugen(eingabe));
}

// ---------------------------------------------------------------- Start

form.elements.datum.value = isoHeute();
form.elements.frist.value = isoHeute(21);
form.elements.rueckmeldung.value = isoHeute(7);
for (const [schluessel, bezeichnung] of Object.entries(ANLAGEN)) {
  const label = document.createElement("label");
  label.className = "haken";
  label.innerHTML = `<input type="checkbox" name="anlagen" value="${schluessel}"${schluessel === "fotos" ? " checked" : ""}><span>${esc(bezeichnung)}</span>`;
  document.getElementById("anlagen").append(label);
}
mangelHinzufuegen();
document.getElementById("mangel-neu").addEventListener("click", () => { mangelHinzufuegen().querySelector("input[name=ort]").focus(); aktualisieren(); });
form.addEventListener("input", aktualisieren);
form.addEventListener("change", aktualisieren);
form.addEventListener("submit", (ev) => { ev.preventDefault(); aktualisieren(); ausgabe.scrollIntoView({ behavior: "smooth", block: "start" }); });
aktualisieren();
