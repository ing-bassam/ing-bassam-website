/**
 * Private Angebotsseite Kaufbegutachtung – Oberfläche im Browser.
 *
 * Ablauf: Schlüssel aus dem Link lesen (Teil nach „#“), paket.js entschlüsseln,
 * Seite aufbauen. Ohne gültigen Schlüssel bleibt nur der Hinweis „Dieser Link ist
 * nicht vollständig“ stehen. Alles läuft im Browser; nichts wird gesendet oder
 * gespeichert. Die E-Mail „Auswahl senden“ öffnet das eigene E-Mail-Programm.
 *
 * Wichtig: Der Schlüssel steht im Teil nach „#“. Sprünge innerhalb der Seite
 * („Auswahl senden“, „Zum Inhalt springen“) dürfen diesen Teil deshalb nie
 * ersetzen – sie werden abgefangen und scrollen nur zum Ziel.
 */
import { PAKET } from "./paket.js";
import { UI } from "./oberflaeche.js";
import {
  OBJEKTE, anfrage, aufzaehlung, bruttoCent, cent, eingabeLesen, entschluesseln, ersetzen, euro, euroSpanne, fragmentAktion,
  hinweise, kostenlos, linkBauen, linkLesen, optionBrutto, optionenFuer, preisBerechnen, schalterListe, sprungZiel, unterlagen,
  zuschlaegeFuer,
} from "./angebot.js";

const wurzel = document.getElementById("angebot");
const status = document.querySelector(".angebot-status");
const oeffnen = document.getElementById("oeffnen");
const linkFehlt = document.getElementById("link-fehlt");
const sprachwahl = document.getElementById("sprachwahl");

let daten = null;
let schluessel = "";
const zustand = {
  sprache: "de", objekt: "etw", flaeche: "", baujahr: "", heizung: "", nutzung: "", region: "",
  schalter: {}, gewaehlt: new Set(), vorhanden: new Set(), adresse: "", termin: "", notar: "", alleHinweise: false,
};
let r = {}; // Verweise auf Elemente, die sich bei Eingaben ändern

const SVG_NS = "http://www.w3.org/2000/svg";
const ICONS = {
  etw: ["M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z", "M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2",
    "M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2", "M10 6h4", "M10 10h4", "M10 14h4", "M10 18h4"],
  efh: ["M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8",
    "M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"],
  haken: ["M20 6 9 17l-5-5"],
};

// ------------------------------------------------------------ Bausteine

function el(tag, attrs = {}, ...kinder) {
  const knoten = document.createElement(tag);
  for (const [name, wert] of Object.entries(attrs)) {
    if (wert === null || wert === undefined || wert === false) continue;
    if (name === "class") knoten.className = wert;
    else if (name === "text") knoten.textContent = wert;
    else if (name.startsWith("on") && typeof wert === "function") knoten.addEventListener(name.slice(2), wert);
    else if (wert === true) knoten.setAttribute(name, "");
    else knoten.setAttribute(name, String(wert));
  }
  for (const kind of kinder.flat(Infinity)) {
    if (kind === null || kind === undefined || kind === false) continue;
    knoten.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
  }
  return knoten;
}

function icon(name) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  for (const d of ICONS[name]) {
    const pfad = document.createElementNS(SVG_NS, "path");
    pfad.setAttribute("d", d);
    svg.append(pfad);
  }
  return svg;
}

const t = () => UI[zustand.sprache];
const s = () => zustand.sprache;
const txt = () => daten.text[zustand.sprache];

/** Quelle eines Hinweises: externe Links ohne Referrer, Titel auf Deutsch. */
function quelle(q) {
  const titel = q.url
    ? el("a", { href: q.url, rel: "noreferrer noopener", lang: s() === "en" ? "de" : null, text: q.titel })
    : el("span", { lang: s() === "en" ? "de" : null, text: q.titel });
  return el("p", { class: "quelle" }, `${t().quelle}: `, titel);
}

function abschnitt(id, nummer, titel, text, ...inhalt) {
  return el("section", { class: "angebot-abschnitt", id, "aria-labelledby": `${id}-titel` },
    el("h2", { class: "schritt-titel", id: `${id}-titel` }, el("span", { class: "schritt-nr", "aria-hidden": "true" }, nummer), titel),
    text ? el("p", { class: "schritt-text", text }) : null,
    ...inhalt);
}

function feld({ id, label, hilfe, kinder, fehlerId }) {
  return el("div", { class: "block" },
    el("label", { for: id }, label, hilfe ? el("span", { class: "optional" }, ` (${hilfe})`) : null),
    kinder,
    fehlerId ? el("p", { class: "fehler", id: fehlerId }) : null);
}

function auswahlFeld(id, label, liste) {
  const select = el("select", { id, name: id },
    el("option", { value: "", text: t().bitte_waehlen }),
    liste.map((x) => el("option", { value: x.id, text: x[s()] })));
  select.value = zustand[id];
  select.addEventListener("change", () => { zustand[id] = select.value; aktualisieren({ unterlagen: true }); });
  return feld({ id, label, kinder: el("div", { class: "eingabe" }, select) });
}

function zahlFeld({ id, label, hilfe, einheit, min, max, step, inputmode }) {
  const input = el("input", {
    id, name: id, type: "number", inputmode, min, max, step, value: zustand[id], "aria-describedby": `${id}-fehler`,
  });
  input.addEventListener("input", () => { zustand[id] = input.value; aktualisieren({ unterlagen: id === "baujahr" }); });
  return feld({
    id, label, hilfe, fehlerId: `${id}-fehler`,
    kinder: el("div", { class: "eingabe kurz" }, input, einheit ? el("span", { class: "einheit", text: einheit }) : null),
  });
}

function schalterKaestchen(name, beschriftung) {
  const input = el("input", { type: "checkbox", id: `schalter-${name}` });
  input.checked = Boolean(zustand.schalter[name]);
  input.addEventListener("change", () => { zustand.schalter[name] = input.checked; aktualisieren({ unterlagen: true }); });
  return el("label", { class: "haken", for: `schalter-${name}` }, input, el("span", { text: beschriftung }));
}

// ------------------------------------------------------------ Abschnitte

function kopfBauen() {
  const umschalter = el("div", { class: "umschalter" }, OBJEKTE.map((objekt) => {
    const input = el("input", { type: "radio", name: "objekt", value: objekt, id: `objekt-${objekt}` });
    input.checked = zustand.objekt === objekt;
    input.addEventListener("change", () => objektWechseln(objekt));
    return el("label", { for: `objekt-${objekt}` }, input, icon(objekt),
      el("span", { class: "titel", text: txt()[`objekt_${objekt}`] }),
      el("span", { class: "text", text: txt()[`objekt_${objekt}_unter`] }));
  }));
  return el("section", { class: "hero hero-leistung hero-angebot", "aria-labelledby": "titel" },
    el("div", { class: "wrap" },
      el("span", { class: "eyebrow", text: `${t().eyebrow} · ${ersetzen(t().stand, { stand: daten.stand[s()] })}` }),
      el("h1", { id: "titel", tabindex: "-1" }, `${t().titel} `, el("span", { class: "accent", text: t().titel_akzent })),
      el("p", { class: "hero-lead", text: t().unterzeile }),
      el("fieldset", { class: "objektwahl" }, el("legend", { text: t().objekt_frage }), umschalter)));
}

function preisBauen() {
  const paket = daten.pakete[zustand.objekt];
  const g = paket.grund[s()];
  const grundBrutto = bruttoCent(paket.grund.netto, daten.mwst);
  const grundpaket = el("article", { class: "grundpaket", "aria-labelledby": "grund-name" },
    el("p", { class: "klein-titel", text: t().grund_titel }),
    el("div", { class: "posten-kopf" },
      el("h3", { class: "posten-name", id: "grund-name", text: g.name }),
      el("span", { class: "posten-preis", text: euro(grundBrutto, s()) })),
    g.kurz ? el("p", { class: "kurz", text: g.kurz }) : null,
    el("ul", { class: "liste-haken" }, aufzaehlung(g.text).map((punkt) => el("li", { text: punkt }))));

  // Zuschläge: Fläche und Merkmale, Status je Zuschlag
  const flaeche = zahlFeld({ id: "flaeche", label: t().flaeche, hilfe: t().flaeche_hilfe, einheit: "m²", min: 10, max: 2000, step: "any", inputmode: "decimal" });
  r.zuschlaege = {};
  const zuschlagListe = el("ul", { class: "zuschlag-liste" }, paket.zuschlaege.map((z) => {
    const statusText = el("span", { class: "status-chip" });
    const zeile = el("li", { class: "zuschlag" },
      el("div", { class: "posten-kopf" },
        el("span", { class: "zuschlag-name", text: z[s()].name }),
        el("span", { class: "posten-preis", text: `+ ${euro(bruttoCent(z.netto, daten.mwst), s())}` })),
      el("p", { class: "zuschlag-text", text: z[s()].text }),
      el("div", { class: "zuschlag-fuss" },
        z.schalter && daten.eingaben.schalter[z.schalter]
          ? schalterKaestchen(z.schalter, daten.eingaben.schalter[z.schalter][s()]) : null,
        statusText));
    r.zuschlaege[z.id] = { zeile, statusText };
    return zeile;
  }));
  const zuschlaege = el("section", { class: "zuschlaege", "aria-labelledby": "zuschlaege-titel" },
    el("h3", { id: "zuschlaege-titel", text: t().zuschlaege_titel }),
    el("p", { class: "hilfe-text", text: t().zuschlaege_text }),
    flaeche, zuschlagListe);

  // Extras als Karten zum Ankreuzen
  r.extras = {};
  const extrasListe = el("ul", { class: "extras-liste" }, optionenFuer(daten, zustand.objekt).map((o) => {
    const [von, bis] = optionBrutto(o, daten.mwst);
    const frei = kostenlos(o);
    const input = el("input", { type: "checkbox", id: `extra-${o.id}` });
    input.checked = zustand.gewaehlt.has(o.id);
    input.addEventListener("change", () => {
      if (input.checked) zustand.gewaehlt.add(o.id); else zustand.gewaehlt.delete(o.id);
      aktualisieren();
    });
    const empfohlen = el("span", { class: "extra-empfohlen", text: t().empfohlen, hidden: true });
    r.extras[o.id] = { empfohlen };
    return el("li", {}, el("label", { class: "extra", for: `extra-${o.id}` }, input,
      el("span", { class: "extra-inhalt" },
        el("span", { class: "extra-kopf" },
          el("span", { class: "extra-name", text: o[s()].name }),
          frei
            ? el("span", { class: "extra-preis extra-kostenlos", text: t().kostenlos })
            : el("span", { class: "extra-preis", text: euroSpanne(von, bis, s()) })),
        el("span", { class: "extra-text", text: o[s()].text }),
        empfohlen)));
  }));
  const extras = el("section", { class: "extras", "aria-labelledby": "extras-titel" },
    el("h3", { id: "extras-titel", text: t().extras_titel }),
    el("p", { class: "hilfe-text", text: t().extras_text }),
    extrasListe);

  // Summe (dunkler Kasten, auf breiten Bildschirmen mitlaufend)
  r.summeBrutto = el("p", { class: "summe-brutto" });
  r.summeMwst = el("p", { class: "summe-mwst" });
  r.balken = { grund: el("span", { class: "b-grund" }), zuschlag: el("span", { class: "b-zuschlag" }), option: el("span", { class: "b-option" }) };
  r.legende = el("ul", { class: "balken-legende" });
  r.posten = el("ul", { class: "posten-liste" });
  r.summeNetto = el("p", { class: "summe-netto" });
  r.summeSpanne = el("p", { class: "summe-hinweis", text: t().summe_spanne, hidden: true });
  r.ansage = el("p", { class: "sr-only", "aria-live": "polite" });
  const stunde = { brutto: bruttoCent(daten.stundensatz_netto, daten.mwst), netto: cent(daten.stundensatz_netto) };
  const summe = el("aside", { class: "preis-summe", id: "summe", "aria-labelledby": "summe-titel" },
    el("p", { class: "label", id: "summe-titel", text: t().summe_titel }),
    r.summeBrutto, r.summeMwst,
    el("div", { class: "balken", "aria-hidden": "true" }, r.balken.grund, r.balken.zuschlag, r.balken.option),
    r.legende, r.posten, r.summeNetto, r.summeSpanne,
    el("p", { class: "summe-hinweis", text: txt().pauschal }),
    el("p", { class: "summe-hinweis", text: txt().ausserhalb }),
    el("p", { class: "summe-hinweis", text: ersetzen(t().stundensatz, { brutto: euro(stunde.brutto, s()), netto: euro(stunde.netto, s()) }) }),
    el("a", { class: "btn btn-primary", href: "#senden", text: t().zur_auswahl }),
    r.ansage);

  return abschnitt("preis", "1", t().preis_titel, t().preis_text,
    el("div", { class: "preis-raster" }, el("div", { class: "preis-auswahl" }, grundpaket, zuschlaege, extras), summe));
}

function objektBauen() {
  const merkmale = schalterListe(daten).filter((x) => x.objekt === zustand.objekt && !x.preis);
  r.hinweisStatus = el("p", { class: "kauf-status" });
  r.hinweisLeer = el("p", { class: "meldung info", text: t().hinweise_leer, hidden: true });
  r.hinweisListe = el("ul", { class: "hinweis-liste" });
  r.hinweisKnopf = el("button", { type: "button", class: "btn btn-outline btn-klein", "aria-expanded": "false", "aria-controls": "hinweis-liste", hidden: true });
  r.hinweisListe.id = "hinweis-liste";
  r.hinweisKnopf.addEventListener("click", () => {
    zustand.alleHinweise = !zustand.alleHinweise;
    aktualisieren();
  });
  return abschnitt("objekt", "2", t().objekt_titel, t().objekt_text,
    el("div", { class: "zeile" },
      zahlFeld({ id: "baujahr", label: t().baujahr, min: 1800, max: 2030, step: 1, inputmode: "numeric" }),
      auswahlFeld("heizung", t().heizung, daten.eingaben.heizung),
      auswahlFeld("nutzung", t().nutzung, daten.eingaben.nutzung),
      auswahlFeld("region", t().region, daten.eingaben.region)),
    merkmale.length ? el("fieldset", { class: "block" }, el("legend", { class: "legende", text: t().merkmale }),
      el("div", { class: "schalter-liste" }, merkmale.map((m) => schalterKaestchen(m.name, m[s()])))) : null,
    el("section", { class: "hinweise-block", "aria-labelledby": "hinweise-titel" },
      el("h3", { id: "hinweise-titel", text: t().hinweise_titel }),
      r.hinweisLeer, r.hinweisListe, r.hinweisStatus,
      el("div", { class: "aktionen-zeile" }, r.hinweisKnopf),
      el("p", { class: "rechtsstand", text: txt().rechtsstand })));
}

function unterlagenBauen() {
  r.fortschrittBalken = el("span");
  r.fortschrittText = el("p", { class: "fortschritt-text" });
  r.unterlagen = el("div", { class: "unterlagen-gruppen" });
  return abschnitt("unterlagen", "3", t().unterlagen_titel, t().unterlagen_text,
    el("div", { class: "unterlagen-fortschritt" }, el("div", { class: "schiene", "aria-hidden": "true" }, r.fortschrittBalken), r.fortschrittText),
    r.unterlagen);
}

function ablaufBauen() {
  const a = txt().ablauf;
  const schritte = [
    { ...a[0], zustand: "erledigt" },
    { ...t().schritt_angebot, zustand: "aktuell" },
    ...a.slice(1),
    t().schritt_notar,
  ];
  const liste = el("ol", { class: "schritte" }, schritte.map((x, i) => el("li", { class: x.zustand || null },
    el("span", { class: "punkt", "aria-hidden": "true" }, x.zustand === "erledigt" ? icon("haken") : String(i + 1)),
    el("span", { class: "s-titel" }, x.t, x.zustand ? el("span", { class: "sr-only", text: ` (${x.zustand === "erledigt" ? t().erledigt : t().naechstes})` }) : null),
    x.w ? el("span", { class: "s-wann", text: x.w }) : null,
    el("span", { class: "s-text", text: x.d }))));
  return abschnitt("ablauf", "4", t().ablauf_titel, "",
    liste,
    el("h3", { text: t().grenzen_titel }),
    el("ul", { class: "liste-grenzen" }, txt().grenzen.map((g) => el("li", { text: g }))));
}

function sendenBauen() {
  const textfeld = (id, label, hilfe) => {
    const input = el("input", { class: "feld", id, name: id, type: "text", autocomplete: "off", value: zustand[id], "aria-describedby": hilfe ? `${id}-hilfe` : null });
    input.addEventListener("input", () => { zustand[id] = input.value; mailAktualisieren(); });
    return el("div", { class: "block" },
      el("label", { for: id }, label, " ", el("span", { class: "optional", text: t().optional })),
      input,
      hilfe ? el("p", { class: "hilfe", id: `${id}-hilfe`, text: hilfe }) : null);
  };
  r.mailLink = el("a", { class: "btn btn-primary", href: "mailto:" + daten.kontakt.email, text: t().senden_knopf });
  r.mailText = el("textarea", { class: "kopiertext", readonly: true, hidden: true, "aria-label": t().vorschau });
  r.mailStatus = el("p", { class: "kauf-status", "aria-live": "polite" });
  r.mailVorschau = el("pre");
  const kopieren = el("button", { type: "button", class: "btn btn-outline btn-klein", text: t().kopieren_knopf });
  kopieren.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(r.aktuelleMail.text);
      r.mailStatus.textContent = ersetzen(t().kopiert, { email: daten.kontakt.email });
      r.mailText.hidden = true;
    } catch {
      r.mailText.value = r.aktuelleMail.text;
      r.mailText.hidden = false;
      r.mailStatus.textContent = t().kopieren_fehler;
      r.mailText.focus();
      r.mailText.select();
    }
  });
  return abschnitt("senden", "5", t().senden_titel, t().senden_text,
    el("div", { class: "senden-felder" },
      textfeld("adresse", t().feld_adresse),
      textfeld("termin", t().feld_termin, t().feld_termin_hilfe),
      textfeld("notar", t().feld_notar)),
    el("div", { class: "aktionen-zeile" }, r.mailLink, kopieren),
    r.mailStatus, r.mailText,
    el("details", { class: "erklaerung mail-vorschau" }, el("summary", { text: t().vorschau }), r.mailVorschau),
    el("p", { class: "beauftragen-hinweis", text: txt().beauftragen }));
}

function leisteBauen() {
  r.leisteBetrag = el("span", { class: "betrag" });
  return el("div", { class: "preis-leiste" },
    el("p", {}, el("small", { text: t().leiste_titel }), r.leisteBetrag),
    el("a", { class: "btn btn-primary", href: "#senden", text: t().zur_auswahl }));
}

// ------------------------------------------------------------ Anzeigen

function roh() {
  return {
    objekt: zustand.objekt, flaeche: zustand.flaeche, baujahr: zustand.baujahr, heizung: zustand.heizung,
    nutzung: zustand.nutzung, region: zustand.region, schalter: zustand.schalter,
  };
}

function fehlerZeigen(id, fehler, text) {
  const ausgabe = document.getElementById(`${id}-fehler`);
  const input = document.getElementById(id);
  if (!ausgabe || !input) return;
  ausgabe.textContent = fehler ? text : "";
  if (fehler) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
}

function preisZeigen(e) {
  const p = preisBerechnen(daten, e, zustand.gewaehlt);
  const betrag = euroSpanne(p.brutto_von, p.brutto_bis, s());
  r.summeBrutto.textContent = betrag;
  r.summeMwst.textContent = ersetzen(t().summe_brutto, { mwst: p.mwst_prozent });
  r.summeNetto.textContent = ersetzen(t().summe_netto, {
    netto: euroSpanne(p.netto_von, p.netto_bis, s()), ust: euroSpanne(p.ust_von, p.ust_bis, s()), mwst: p.mwst_prozent,
  });
  r.summeSpanne.hidden = !p.spanne;
  const gesamt = p.anteile.grund + p.anteile.zuschlag + p.anteile.option || 1;
  const legende = [];
  for (const art of ["grund", "zuschlag", "option"]) {
    r.balken[art].style.width = `${(100 * p.anteile[art]) / gesamt}%`;
    if (p.anteile[art]) {
      legende.push(el("li", { class: `l-${art}` }, el("span", { class: "punkt", "aria-hidden": "true" }),
        t()[`anteil_${art}`], el("b", { text: euroSpanne(p.anteile_von[art], p.anteile[art], s()) })));
    }
  }
  // Nur Grundpaket: die Legende würde die Postenliste wiederholen.
  r.legende.replaceChildren(...(legende.length > 1 ? legende : []));
  r.posten.replaceChildren(...p.posten.map((x) => el("li", {},
    el("span", { text: x.art === "zuschlag" ? `${t().posten_zuschlag}: ${x.eintrag[s()].name}` : x.eintrag[s()].name }),
    el("b", { text: x.kostenlos ? t().kostenlos : euroSpanne(x.brutto_von, x.brutto_bis, s()) }))));
  r.leisteBetrag.textContent = betrag;
  r.ansage.textContent = `${t().summe_titel}: ${betrag} ${r.summeMwst.textContent}`;

  for (const z of zuschlaegeFuer(daten, e)) {
    const ref = r.zuschlaege[z.id];
    if (!ref) continue;
    ref.zeile.dataset.aktiv = String(z.aktiv);
    ref.statusText.textContent = z.aktiv
      ? (z.grund === "flaeche" ? `${t().trifft_zu} – ${t().grund_flaeche}` : t().trifft_zu)
      : t().trifft_nicht_zu;
  }
}

function hinweiseZeigen(e) {
  const h = hinweise(daten, e, s());
  const liste = zustand.alleHinweise ? h.alle : h.kompakt;
  r.hinweisListe.replaceChildren(...liste.map((x) => el("li", { class: "hinweis-eintrag", "data-kategorie": x.kategorie },
    el("span", { class: "hinweis-kat", text: t().kategorien[x.kategorie] }),
    el("h4", { class: "hinweis-name", text: x.titel }),
    el("p", { text: zustand.alleHinweise ? x.text : x.kurz }),
    quelle(x.quelle))));
  const ohneAngaben = e.baujahr === null && !e.heizung && !e.nutzung;
  r.hinweisLeer.hidden = !ohneAngaben;
  const mehr = h.anzahl > h.kompakt.length;
  r.hinweisKnopf.hidden = !mehr && !zustand.alleHinweise;
  r.hinweisKnopf.textContent = zustand.alleHinweise ? t().weniger_anzeigen : ersetzen(t().alle_anzeigen, { n: h.anzahl });
  r.hinweisKnopf.setAttribute("aria-expanded", String(zustand.alleHinweise));
  r.hinweisStatus.textContent = mehr && !zustand.alleHinweise
    ? ersetzen(t().hinweise_anzahl, { n: h.kompakt.length, m: h.anzahl }) : "";
  for (const [id, ref] of Object.entries(r.extras)) ref.empfohlen.hidden = !h.empfohlen.has(id);
}

function unterlagenZeigen(e) {
  const liste = unterlagen(daten, e, s());
  const gruppen = [];
  for (const prio of [1, 2, 3]) {
    const teil = liste.filter((u) => u.prio === prio);
    if (!teil.length) continue;
    gruppen.push(el("h3", { class: `prio-titel prio-${prio}`, text: txt().prio[String(prio)] }));
    gruppen.push(el("ul", { class: "unterlagen-zeilen" }, teil.map((u) => {
      const input = el("input", { type: "checkbox", id: `u-${u.id}` });
      input.checked = zustand.vorhanden.has(u.id);
      input.addEventListener("change", () => {
        if (input.checked) zustand.vorhanden.add(u.id); else zustand.vorhanden.delete(u.id);
        fortschrittZeigen(e);
        mailAktualisieren();
      });
      return el("li", { class: "unterlage" },
        el("div", { class: "unterlage-text" }, el("span", { class: "unterlage-name", text: u.text }), el("small", { text: `${t().wo}: ${u.wo}` })),
        el("label", { class: "haken", for: `u-${u.id}` }, input, el("span", { text: t().liegt_vor }), el("span", { class: "sr-only", text: `: ${u.text}` })));
    })));
  }
  r.unterlagen.replaceChildren(...gruppen);
  fortschrittZeigen(e);
}

function fortschrittZeigen(e) {
  const wichtig = unterlagen(daten, e, s()).filter((u) => u.prio === 1);
  const da = wichtig.filter((u) => zustand.vorhanden.has(u.id)).length;
  r.fortschrittBalken.style.width = wichtig.length ? `${(100 * da) / wichtig.length}%` : "0%";
  r.fortschrittText.textContent = ersetzen(t().fortschritt, { n: da, m: wichtig.length });
}

function mailAktualisieren() {
  const { eingabe } = eingabeLesen(roh(), daten);
  r.aktuelleMail = anfrage({
    daten, t: t().mail, eingabe, gewaehlt: zustand.gewaehlt, vorhanden: [...zustand.vorhanden],
    felder: { adresse: zustand.adresse, termin: zustand.termin, notar: zustand.notar }, sprache: s(),
  });
  r.mailLink.href = r.aktuelleMail.href;
  r.mailVorschau.textContent = r.aktuelleMail.text;
  if (!r.mailText.hidden) r.mailText.value = r.aktuelleMail.text;
}

function aktualisieren({ unterlagen: liste = false } = {}) {
  const { eingabe, fehler } = eingabeLesen(roh(), daten);
  fehlerZeigen("flaeche", fehler.flaeche, t().fehler_flaeche);
  fehlerZeigen("baujahr", fehler.baujahr, t().fehler_baujahr);
  preisZeigen(eingabe);
  hinweiseZeigen(eingabe);
  if (liste) unterlagenZeigen(eingabe);
  mailAktualisieren();
}

// ------------------------------------------------------------ Wechsel

function adresseMerken() {
  // Nur der Teil nach „#“ ändert sich; der Browser sendet ihn nie an den Server.
  // Objektart (o) und Sprache (l) werden ersetzt, der Schlüssel (k) bleibt immer stehen.
  // replaceState löst kein „hashchange“ aus und legt keinen neuen Verlaufseintrag an.
  if (!schluessel) return;
  history.replaceState(null, "", linkBauen({ schluessel, objekt: zustand.objekt, sprache: zustand.sprache }));
}

/** Zu einem Abschnitt der Seite scrollen und ihn fokussieren, ohne den Teil nach „#“ zu ändern. */
function springen(id) {
  const ziel = id ? document.getElementById(id) : null;
  if (!ziel) return;
  if (!ziel.hasAttribute("tabindex")) ziel.setAttribute("tabindex", "-1");
  ziel.scrollIntoView({ block: "start" });
  ziel.focus({ preventScroll: true });
}

function objektWechseln(objekt) {
  if (objekt === zustand.objekt) return;
  const neu = optionenFuer(daten, objekt).map((o) => o.id);
  const gewaehlt = new Set();
  for (const id of zustand.gewaehlt) {
    if (neu.includes(id)) gewaehlt.add(id);
    else {
      // gleichartige Option der anderen Objektart, z. B. Thermografie Wohnung → Haus
      const ersatz = neu.find((x) => x.split("_")[0] === id.split("_")[0]);
      if (ersatz) gewaehlt.add(ersatz);
    }
  }
  zustand.gewaehlt = gewaehlt;
  zustand.objekt = objekt;
  adresseMerken();
  aufbauen(`objekt-${objekt}`);
}

function spracheWechseln() {
  zustand.sprache = zustand.sprache === "de" ? "en" : "de";
  adresseMerken();
  aufbauen("sprache-knopf");
}

function aufbauen(fokusId) {
  const ui = t();
  document.documentElement.lang = s();
  document.title = ui.titel_seite;
  document.getElementById("fuss-text").textContent = ui.fuss;
  document.getElementById("fuss-impressum").textContent = ui.impressum;
  document.getElementById("fuss-datenschutz").textContent = ui.datenschutz;
  const knopf = el("button", {
    type: "button", class: "sprache-knopf", id: "sprache-knopf", lang: s() === "de" ? "en" : "de", "aria-label": ui.sprache_label, text: ui.sprache_knopf,
  });
  knopf.addEventListener("click", spracheWechseln);
  sprachwahl.replaceChildren(knopf);
  sprachwahl.hidden = false;
  r = {};
  wurzel.replaceChildren(kopfBauen(),
    el("div", { class: "wrap angebot-inhalt" }, preisBauen(), objektBauen(), unterlagenBauen(), ablaufBauen(), sendenBauen()),
    leisteBauen());
  wurzel.hidden = false;
  document.body.classList.add("bereit");
  aktualisieren({ unterlagen: true });
  if (fokusId) document.getElementById(fokusId)?.focus();
}

function gueltig(d) {
  return Boolean(d && d.pakete && d.pakete.etw && d.pakete.efh && d.optionen && d.eingaben && d.regeln
    && d.unterlagen && d.text && d.text.de && d.text.en && d.kontakt && typeof d.mwst === "number");
}

async function starten() {
  const link = linkLesen(location.hash);
  zustand.sprache = link.sprache || ((navigator.language || "de").toLowerCase().startsWith("de") ? "de" : "en");
  if (link.objekt) zustand.objekt = link.objekt;
  const versuchen = async (paket) => {
    try {
      return link.schluessel && paket ? await entschluesseln(paket, link.schluessel) : null;
    } catch {
      return null;
    }
  };
  let entschluesselt = await versuchen(PAKET);
  if (!gueltig(entschluesselt) && link.schluessel) {
    // Nach einem Schlüsselwechsel kann der Browser noch das alte paket.js im Zwischenspeicher
    // haben: einmal frisch laden (andere Adresse, gleiche Datei) und erneut versuchen.
    try {
      entschluesselt = await versuchen((await import(`./paket.js?frisch=${Date.now()}`)).PAKET);
    } catch {
      entschluesselt = null;
    }
  }
  if (!gueltig(entschluesselt)) {
    daten = null;
    schluessel = "";
    oeffnen.hidden = true;
    linkFehlt.hidden = false;
    status.hidden = false;
    wurzel.hidden = true;
    wurzel.replaceChildren();
    sprachwahl.hidden = true;
    document.body.classList.remove("bereit");
    return;
  }
  daten = entschluesselt;
  schluessel = link.schluessel;
  linkFehlt.hidden = true;
  status.hidden = true;
  aufbauen();
}

// Seiteninterne Links (href="#…", z. B. „Auswahl senden“ und „Zum Inhalt springen“) würden
// den Teil nach „#“ und damit den Schlüssel ersetzen. Deshalb: Klick abfangen, Ziel ansteuern.
document.addEventListener("click", (ereignis) => {
  if (ereignis.defaultPrevented || ereignis.button !== 0) return;
  const link = ereignis.target instanceof Element ? ereignis.target.closest('a[href^="#"]') : null;
  if (!link) return;
  ereignis.preventDefault();
  springen(sprungZiel(link.getAttribute("href")));
});

// Ändert sich der Teil nach „#“ doch einmal (z. B. von Hand oder durch den Browser), entscheidet
// fragmentAktion: Ohne Schlüssel wird der alte Teil wiederhergestellt, nur ein anderer gültiger
// Schlüssel öffnet die Seite neu.
window.addEventListener("hashchange", () => {
  const { aktion, ziel } = fragmentAktion(location.hash, { schluessel, geoeffnet: Boolean(daten) });
  if (aktion === "starten") {
    starten();
  } else if (aktion === "wiederherstellen") {
    adresseMerken();
    springen(ziel);
  }
});

starten();
