// Gewährleistungsfristen-Rechner – Oberfläche. Rechnet ausschließlich im Browser
// (Rechenkern: frist.js). Eingaben wandern in die Adresszeile (#…), damit ein
// Ergebnis als Lesezeichen oder Link weitergegeben werden kann; nichts wird gesendet.
import { berechne, FRISTEN, HEMMUNGSARTEN, datumDeutsch, wochentag } from "./frist.js";

const form = document.getElementById("frist-form");
const ausgabe = document.getElementById("ergebnis");
const liste = document.getElementById("hemmungen");
const vorlage = document.getElementById("hemmung-vorlage");
const vobFelder = document.querySelectorAll("[data-nur-vob]");
const vereinbartFelder = document.querySelectorAll("[data-nur-vereinbart]");

function heuteIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function esc(text) {
  return String(text).replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[z]));
}

// ------------------------------------------------------------ Hemmungen

function hemmungHinzufuegen(werte = {}) {
  const zeile = vorlage.content.firstElementChild.cloneNode(true);
  const nr = liste.children.length + 1;
  zeile.querySelectorAll("label").forEach((label) => {
    const feld = label.querySelector("input, select");
    const id = `hemmung-${nr}-${feld.name}`;
    feld.id = id;
    label.setAttribute("for", id);
  });
  const artFeld = zeile.querySelector("select[name=art]");
  for (const [schluessel, art] of Object.entries(HEMMUNGSARTEN)) {
    const option = document.createElement("option");
    option.value = schluessel;
    option.textContent = art.bezeichnung;
    artFeld.append(option);
  }
  if (werte.von) zeile.querySelector("input[name=von]").value = werte.von;
  if (werte.bis) zeile.querySelector("input[name=bis]").value = werte.bis;
  if (werte.art) artFeld.value = werte.art;
  zeile.querySelector(".entfernen").addEventListener("click", () => { zeile.remove(); aktualisieren(); });
  liste.append(zeile);
  zeile.querySelector("input[name=von]").focus();
}

function hemmungenLesen() {
  return [...liste.children].map((zeile) => ({
    von: zeile.querySelector("input[name=von]").value,
    bis: zeile.querySelector("input[name=bis]").value,
    art: zeile.querySelector("select[name=art]").value,
  }));
}

// -------------------------------------------------------------- Eingabe

function eingabeLesen() {
  const daten = new FormData(form);
  return {
    abnahme: daten.get("abnahme") || "",
    frist: daten.get("frist") || "bgb_bauwerk",
    vereinbartJahre: daten.get("vereinbartJahre"),
    vereinbartMonate: daten.get("vereinbartMonate"),
    anerkenntnis: daten.get("anerkenntnis") || "",
    ruege: daten.get("ruege") || "",
    beseitigungAbnahme: daten.get("beseitigungAbnahme") || "",
    heute: daten.get("heute") || heuteIso(),
    hemmungen: hemmungenLesen(),
  };
}

function felderUmschalten() {
  const frist = form.elements.frist.value;
  const vob = frist.startsWith("vob");
  vobFelder.forEach((el) => { el.hidden = !vob; });
  vereinbartFelder.forEach((el) => { el.hidden = frist !== "vereinbart"; });
}

function inAdresse(eingabe) {
  // Erst wenn ein Abnahmedatum steht, gibt es etwas zu merken; vorher bleibt die Adresse sauber.
  const p = new URLSearchParams();
  if (eingabe.abnahme) {
    p.set("abnahme", eingabe.abnahme);
    p.set("frist", eingabe.frist);
    if (eingabe.frist === "vereinbart") {
      p.set("vereinbartJahre", eingabe.vereinbartJahre || "0");
      p.set("vereinbartMonate", eingabe.vereinbartMonate || "0");
    }
    for (const k of ["anerkenntnis", "ruege", "beseitigungAbnahme"]) {
      if (eingabe[k]) p.set(k, eingabe[k]);
    }
    eingabe.hemmungen.filter((h) => h.von && h.bis).forEach((h) => p.append("h", `${h.von}_${h.bis}_${h.art}`));
  }
  const neu = p.toString();
  if (neu !== location.hash.slice(1)) history.replaceState(null, "", neu ? `#${neu}` : location.pathname);
}

function ausAdresse() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (![...p.keys()].length) return;
  for (const name of ["abnahme", "frist", "vereinbartJahre", "vereinbartMonate", "anerkenntnis", "ruege", "beseitigungAbnahme"]) {
    if (p.has(name) && form.elements[name]) form.elements[name].value = p.get(name);
  }
  p.getAll("h").forEach((wert) => {
    const [von, bis, art] = wert.split("_");
    hemmungHinzufuegen({ von, bis, art });
  });
}

// -------------------------------------------------------------- Ausgabe

function tageText(e) {
  if (e.status === "abgelaufen") return `Abgelaufen seit ${Math.abs(e.tageBis)} Tagen (Stichtag ${datumDeutsch(e.heute)})`;
  if (e.tageBis === 0) return "Läuft heute ab";
  return `Noch ${e.tageBis} Tage ab Stichtag ${datumDeutsch(e.heute)}`;
}

function rendern(e) {
  if (!e.ok) {
    ausgabe.hidden = false;
    ausgabe.innerHTML = `<p class="meldung info">${e.fehler.map(esc).join(" ")}</p>`;
    return;
  }
  const schritte = e.schritte.map((s) => `
        <tr>
          <td class="nr">${s.nr}</td>
          <td class="formel"><b>${esc(s.bezeichnung)}</b>${s.erklaerung ? `<br><small>${esc(s.erklaerung)}</small>` : ""}</td>
          <td class="wert">${esc(datumDeutsch(s.wert))}</td>
          <td class="grundlage">${esc(s.grundlage)}</td>
        </tr>`).join("");
  const hinweise = e.hinweise.map((h) => `<li>${esc(h)}</li>`).join("");
  const knapp = e.status === "knapp";
  ausgabe.hidden = false;
  ausgabe.innerHTML = `
      <div class="ergebnis-kopf">
        <span class="verfahren">${esc(e.frist.bezeichnung)} · ${esc(e.frist.grundlage)}</span>
        <h2>Ende der Verjährungsfrist</h2>
      </div>
      <div class="spanne status-${e.status}">
        <span class="label">${e.verschoben ? "Letzter Tag (nach § 193 BGB verschoben)" : "Letzter Tag der Frist"}</span>
        <div class="zahlen">${esc(datumDeutsch(e.endeWerktag))} <span class="wochentag">${esc(wochentag(e.endeWerktag))}</span></div>
        <p class="mitte"><b>${esc(tageText(e))}</b>${e.verschoben ? ` · rechnerisch ${esc(datumDeutsch(e.ende))} (${esc(wochentag(e.ende))})` : ""}</p>
        <p class="stand">Regelfrist ${esc(e.frist.text)} ab Abnahme am ${esc(datumDeutsch(e.abnahme))}. Hemmende Maßnahmen wie Klage oder selbständiges Beweisverfahren müssen vor Ablauf dieses Tages bei Gericht eingehen; eine Mängelanzeige allein hemmt beim BGB-Vertrag nicht.</p>
      </div>
      <ul class="eckdaten">
        <li><span class="k">Erster Tag der Frist</span><span class="v">${esc(datumDeutsch(e.fristbeginn))}</span></li>
        <li><span class="k">Ende der Regelfrist</span><span class="v">${esc(datumDeutsch(e.regelende))}</span></li>
        <li><span class="k">Rechnerisches Ende</span><span class="v">${esc(datumDeutsch(e.ende))}<small>${e.ende === e.regelende ? "keine Verlängerung" : "nach Hemmung, Rüge oder Neubeginn"}</small></span></li>
        <li><span class="k">Verschiebung § 193 BGB</span><span class="v">${e.verschoben ? esc(datumDeutsch(e.endeWerktag)) : "keine"}<small>${e.verschoben ? esc(wochentag(e.ende)) + " → nächster Werktag" : "Fristende ist ein Werktag"}</small></span></li>
      </ul>
      <details class="abschnitt" open>
        <summary>Rechenweg Schritt für Schritt</summary>
        <div class="abschnitt-inhalt">
          <div class="tabelle-huelle">
            <table class="rechenweg">
              <thead><tr><th>Nr.</th><th>Schritt</th><th>Datum</th><th>Grundlage</th></tr></thead>
              <tbody>${schritte}</tbody>
            </table>
          </div>
        </div>
      </details>
      <details class="abschnitt">
        <summary>Was das Werkzeug nicht prüfen kann</summary>
        <div class="abschnitt-inhalt"><ul class="hinweise">${hinweise}</ul></div>
      </details>
      <div class="cta">
        <h3>${knapp ? "Die Frist läuft bald ab – jetzt noch prüfen lassen" : e.status === "abgelaufen" ? "Frist abgelaufen? Trotzdem lohnt der Blick auf Arglist und Vertrag" : "Vor Fristablauf das Gebäude durchsehen lassen"}</h3>
        <p>${knapp || e.status === "laeuft"
          ? "Eine Begehung einige Monate vor dem Fristende findet die Mängel, die Sie noch rügen können. Wir prüfen Dach, Fassade, Keller, Fenster und Haustechnik und liefern das Mängelprotokoll für die Anzeige an den Vertragspartner."
          : "Ob Ansprüche trotz Ablauf bestehen – etwa bei arglistig verschwiegenen Mängeln oder abweichenden Vertragsfristen – beurteilt ein Rechtsanwalt. Wir liefern dafür die technische Feststellung."}</p>
        <div class="aktionen">
          <a class="btn btn-primary" href="/leistungen/baubegleitung-bauabnahme/">Gewährleistungsbegehung ab 490 €</a>
          <a class="btn btn-ghost" href="/werkzeuge/maengelanzeige/">Mängelanzeige erstellen</a>
        </div>
        <p class="klein">Rückmeldung innerhalb eines Werktags · Berlin und Brandenburg</p>
      </div>
      <p class="rechtlich"><strong>Keine Rechtsberatung.</strong> Das Werkzeug rechnet die gesetzlichen Regelfristen nach §§ 187, 188, 193, 203, 204, 209, 212 und 634a BGB sowie § 13 VOB/B nach dem Stand vom 5. Oktober 2026 nach. Ob eine Hemmung oder ein Anerkenntnis vorliegt, ob die VOB/B wirksam vereinbart ist und welche Frist in Ihrem Vertrag gilt, muss ein Rechtsanwalt beurteilen. Handeln Sie nie am letzten Tag.</p>
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
  felderUmschalten();
  const eingabe = eingabeLesen();
  inAdresse(eingabe);
  if (!eingabe.abnahme) {
    ausgabe.hidden = true;
    return;
  }
  rendern(berechne(eingabe));
}

// ---------------------------------------------------------------- Start

form.elements.heute.value = heuteIso();
ausAdresse();
// Ein neuer Link in derselben Registerkarte lädt die Seite nicht neu, sondern ändert nur den Anker.
window.addEventListener("hashchange", () => {
  form.reset();
  form.elements.heute.value = heuteIso();
  liste.replaceChildren();
  ausAdresse();
  aktualisieren();
});
document.getElementById("hemmung-neu").addEventListener("click", () => hemmungHinzufuegen());
form.addEventListener("input", aktualisieren);
form.addEventListener("change", aktualisieren);
form.addEventListener("submit", (ev) => { ev.preventDefault(); aktualisieren(); ausgabe.scrollIntoView({ behavior: "smooth", block: "start" }); });
aktualisieren();
