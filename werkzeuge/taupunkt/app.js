// Taupunkt- und Schimmelrisiko-Rechner – Oberfläche. Rechnet ausschließlich im
// Browser (Rechenkern: taupunkt.js). Eingaben wandern in die Adresszeile, damit
// ein Ergebnis als Link weitergegeben werden kann; nichts wird gesendet.
import { bewerten } from "./taupunkt.js";

const form = document.getElementById("taupunkt-form");
const ausgabe = document.getElementById("ergebnis");
const gemessenFelder = document.querySelectorAll("[data-nur-gemessen]");
const geschaetztFelder = document.querySelectorAll("[data-nur-geschaetzt]");

const STATUS = {
  tauwasser: { titel: "Tauwasser", text: "An dieser Oberfläche kondensiert Wasser." },
  schimmel: { titel: "Schimmelrisiko", text: "Das 80-Prozent-Kriterium der DIN 4108-2 ist überschritten." },
  grenzbereich: { titel: "Grenzbereich", text: "Das Kriterium ist eingehalten, aber ohne Reserve." },
  unkritisch: { titel: "Unkritisch", text: "Die Oberfläche bleibt unter diesen Bedingungen trocken." },
};

function esc(text) {
  return String(text).replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[z]));
}

function zahl(x, stellen = 1) {
  return Number(x).toLocaleString("de-DE", { minimumFractionDigits: stellen, maximumFractionDigits: stellen });
}

function eingabeLesen() {
  const d = new FormData(form);
  return {
    innen: d.get("innen"),
    feuchte: d.get("feuchte"),
    modus: d.get("modus") || "gemessen",
    oberflaeche: d.get("oberflaeche"),
    aussen: d.get("aussen"),
    fRsi: d.get("fRsi"),
  };
}

function felderUmschalten(modus) {
  gemessenFelder.forEach((el) => { el.hidden = modus !== "gemessen"; });
  geschaetztFelder.forEach((el) => { el.hidden = modus !== "geschaetzt"; });
}

function inAdresse(e) {
  const p = new URLSearchParams();
  p.set("innen", e.innen);
  p.set("feuchte", e.feuchte);
  p.set("modus", e.modus);
  if (e.modus === "gemessen") p.set("oberflaeche", e.oberflaeche);
  else { p.set("aussen", e.aussen); p.set("fRsi", e.fRsi); }
  const neu = p.toString();
  if (neu !== location.hash.slice(1)) history.replaceState(null, "", `#${neu}`);
}

function ausAdresse() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (!p.has("innen")) return;
  for (const name of ["innen", "feuchte", "oberflaeche", "aussen", "fRsi"]) {
    if (p.has(name) && form.elements[name]) form.elements[name].value = p.get(name);
  }
  if (p.has("modus")) {
    const radio = form.querySelector(`input[name=modus][value="${p.get("modus") === "geschaetzt" ? "geschaetzt" : "gemessen"}"]`);
    if (radio) radio.checked = true;
  }
}

function rendern(e) {
  ausgabe.hidden = false;
  if (!e.ok) {
    ausgabe.innerHTML = `<p class="meldung info">${e.fehler.map(esc).join(" ")}</p>`;
    return;
  }
  const status = STATUS[e.status];
  const schritte = e.schritte.map((s) => `
        <tr>
          <td class="nr">${s.nr}</td>
          <td class="formel"><b>${esc(s.bezeichnung)}</b><br><small>${esc(s.formel)}</small></td>
          <td class="wert">${esc(zahl(s.wert, s.einheit === "Pa" || s.einheit === "%" ? 0 : s.einheit === "" ? 2 : 1))}${s.einheit ? " " + esc(s.einheit) : ""}</td>
          <td class="grundlage">${esc(s.grundlage)}</td>
        </tr>`).join("");
  const reserveText = e.reserve >= 0
    ? `Die Oberfläche liegt ${zahl(e.reserve)} K über der kritischen Temperatur von ${zahl(e.kritisch80)} °C.`
    : `Die Oberfläche liegt ${zahl(-e.reserve)} K unter der kritischen Temperatur von ${zahl(e.kritisch80)} °C.`;
  const empfehlung = e.status === "unkritisch"
    ? "Unter diesen Bedingungen ist kein Schimmel zu erwarten. Treten trotzdem Flecken auf, kommt die Feuchte eher aus dem Bauteil als aus der Luft – dann hilft ein Blick auf Leckagen und Abdichtung."
    : e.status === "grenzbereich"
      ? "Halten Sie die Raumluftfeuchte im Winter unter dem errechneten Höchstwert und prüfen Sie, ob die kalte Stelle wärmer werden kann: Möbel von der Außenwand abrücken, gleichmäßig heizen, Lüftungsgewohnheiten mit einem Raumklima-Protokoll überprüfen."
      : "Zwei Wege: die Oberfläche wärmer machen (Wärmebrücke dämmen, Raum beheizen, Möbel abrücken) oder die Raumluft trockener halten. Welcher Weg der richtige ist, entscheidet sich an der Frage, ob die Oberflächentemperatur dem Bauteil oder der Nutzung geschuldet ist – das klärt ein Schimmelgutachten mit Messung und Berechnung.";
  ausgabe.innerHTML = `
      <div class="ergebnis-kopf">
        <span class="verfahren">${e.modus === "gemessen" ? "Gemessene Oberflächentemperatur" : "Oberflächentemperatur aus Temperaturfaktor"} · DIN 4108-2, 80-%-Kriterium</span>
        <h2>${esc(status.titel)}</h2>
      </div>
      <div class="spanne status-${e.status}">
        <span class="label">Relative Feuchte an der Oberfläche</span>
        <div class="zahlen">${zahl(e.oberflaechenfeuchte, 0)} % <span class="wochentag">bei ${zahl(e.oberflaeche)} °C Oberfläche</span></div>
        <p class="mitte"><b>${esc(status.text)}</b> ${esc(reserveText)}</p>
        <p class="stand">Raumluft ${zahl(e.innen)} °C / ${zahl(e.feuchte, 0)} % → Taupunkt ${zahl(e.taupunkt)} °C, ${zahl(e.absoluteFeuchte)} g Wasser je m³ Luft.${e.fRsiMin !== null ? ` Erforderlicher Temperaturfaktor f<sub>Rsi</sub> = ${zahl(e.fRsiMin, 2)}, vorhanden ${zahl(e.fRsi, 2)}.` : ""}</p>
      </div>
      <ul class="eckdaten">
        <li><span class="k">Taupunkt</span><span class="v">${zahl(e.taupunkt)} °C<small>Tauwasser ab dieser Oberflächentemperatur</small></span></li>
        <li><span class="k">Kritische Temperatur (80 %)</span><span class="v">${zahl(e.kritisch80)} °C<small>Schimmelkriterium DIN 4108-2</small></span></li>
        <li><span class="k">Oberflächentemperatur</span><span class="v">${zahl(e.oberflaeche)} °C<small>${e.modus === "gemessen" ? "gemessen" : `aus f<sub>Rsi</sub> ${zahl(e.fRsi, 2)} bei ${zahl(e.aussen)} °C außen`}</small></span></li>
        <li><span class="k">Zulässige Raumluftfeuchte</span><span class="v">${zahl(e.zulaessigeRaumfeuchte, 0)} %<small>damit diese Oberfläche unter 80 % bleibt</small></span></li>
      </ul>
      <details class="abschnitt" open>
        <summary>Rechenweg Schritt für Schritt</summary>
        <div class="abschnitt-inhalt">
          <div class="tabelle-huelle">
            <table class="rechenweg">
              <thead><tr><th>Nr.</th><th>Größe</th><th>Wert</th><th>Grundlage</th></tr></thead>
              <tbody>${schritte}</tbody>
            </table>
          </div>
        </div>
      </details>
      <details class="abschnitt">
        <summary>Einordnung und Grenzen</summary>
        <div class="abschnitt-inhalt"><ul class="hinweise">${e.hinweise.map((h) => `<li>${esc(h)}</li>`).join("")}</ul></div>
      </details>
      <div class="cta">
        <h3>${e.status === "unkritisch" ? "Trotzdem Schimmel? Dann steckt meist das Bauteil dahinter" : "Bauteil oder Nutzung – wir klären die Ursache"}</h3>
        <p>${esc(empfehlung)}</p>
        <div class="aktionen">
          <a class="btn btn-primary" href="/leistungen/schimmelgutachten/">Schimmel-Check ab 350 €</a>
          <a class="btn btn-ghost" href="/fachwissen/raumklima-protokoll-schimmelverdacht/">Raumklima-Protokoll zum Selbstführen</a>
        </div>
        <p class="klein">Rückmeldung innerhalb eines Werktags · Berlin und Brandenburg</p>
      </div>
      <p class="rechtlich"><strong>Einordnung, kein Gutachten.</strong> Der Rechner wertet eine Momentaufnahme stationär nach der Magnus-Formel und dem 80-%-Kriterium der DIN 4108-2:2013-02 aus. Ob ein Bauteil den Mindestwärmeschutz einhält, ob eine Wärmebrücke, eine Leckage oder die Nutzung ursächlich ist und wer die Kosten trägt, lässt sich nur mit Messung über Zeit, Bauteilaufbau und Ortstermin beurteilen.</p>
      <div class="aktionen-zeile">
        <button type="button" class="btn btn-outline btn-klein" data-drucken>Ergebnis drucken oder als PDF speichern</button>
        <button type="button" class="btn btn-leer btn-klein" data-link>Link zu dieser Berechnung kopieren</button>
      </div>`;
  ausgabe.querySelector("[data-drucken]").addEventListener("click", () => window.print());
  ausgabe.querySelector("[data-link]").addEventListener("click", async (ev) => {
    try {
      await navigator.clipboard.writeText(location.href);
      ev.currentTarget.textContent = "Link kopiert";
    } catch {
      ev.currentTarget.textContent = location.href;
    }
  });
}

function aktualisieren() {
  const e = eingabeLesen();
  felderUmschalten(e.modus);
  inAdresse(e);
  rendern(bewerten(e));
}

ausAdresse();
form.addEventListener("input", aktualisieren);
form.addEventListener("change", aktualisieren);
form.addEventListener("submit", (ev) => { ev.preventDefault(); aktualisieren(); ausgabe.scrollIntoView({ behavior: "smooth", block: "start" }); });
aktualisieren();
