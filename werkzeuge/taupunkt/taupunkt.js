/**
 * Taupunkt- und Schimmelrisiko-Rechner – Rechenkern ohne Browser-Abhängigkeiten.
 *
 * Grundlagen:
 *   Sättigungsdampfdruck nach der Magnus-Formel (Sonntag 1990, über Wasser):
 *     p_s(θ) = 611,2 Pa · exp(17,62 · θ / (243,12 °C + θ))
 *   Taupunkt: Umkehrung der Magnus-Formel für den Wasserdampfpartialdruck p_v = φ · p_s(θ_i).
 *   Schimmelkriterium: DIN 4108-2:2013-02, Abschnitt 6.2 – an der raumseitigen Oberfläche
 *     darf die relative Luftfeuchte 80 % nicht überschreiten; unter den Randbedingungen
 *     20 °C / 50 % innen und −5 °C außen entspricht das einer Oberflächentemperatur von
 *     mindestens 12,6 °C bzw. einem Temperaturfaktor f_Rsi ≥ 0,70.
 *   Temperaturfaktor: f_Rsi = (θ_si − θ_e) / (θ_i − θ_e)  →  θ_si = θ_e + f_Rsi · (θ_i − θ_e)
 *   Absolute Feuchte: ρ_v = p_v / (R_v · T) mit R_v = 461,5 J/(kg·K)
 *
 * Alle Temperaturen in °C, Feuchten als Anteil (0,5 = 50 %), Drücke in Pa.
 * Stationäre Betrachtung ohne Sorption, Luftbewegung und Wärmespeicherung –
 * das Werkzeug ordnet ein, es ersetzt keine Messung über Zeit und kein Gutachten.
 */

export const MAGNUS = { a: 17.62, b: 243.12, p0: 611.2 };
export const R_V = 461.5;
export const KRITISCH = 0.8;          // DIN 4108-2: 80 % relative Feuchte an der Oberfläche
export const F_RSI_MINDEST = 0.7;     // DIN 4108-2: Mindestwert des Temperaturfaktors
export const RANDBEDINGUNG = { innen: 20, feuchte: 0.5, aussen: -5 };  // DIN 4108-2, Abschnitt 6.2

/** Sättigungsdampfdruck über Wasser in Pa. */
export function saettigungsdruck(theta) {
  return MAGNUS.p0 * Math.exp((MAGNUS.a * theta) / (MAGNUS.b + theta));
}

/** Temperatur in °C, bei der der Dampfdruck p (Pa) gesättigt ist (Umkehrung der Magnus-Formel). */
export function taupunktAusDruck(p) {
  const l = Math.log(p / MAGNUS.p0);
  return (MAGNUS.b * l) / (MAGNUS.a - l);
}

/** Wasserdampfpartialdruck in Pa aus Lufttemperatur und relativer Feuchte (Anteil). */
export function partialdruck(theta, phi) {
  return phi * saettigungsdruck(theta);
}

/** Taupunkttemperatur in °C. */
export function taupunkt(theta, phi) {
  return taupunktAusDruck(partialdruck(theta, phi));
}

/** Absolute Feuchte in g/m³. */
export function absoluteFeuchte(theta, phi) {
  return (partialdruck(theta, phi) / (R_V * (theta + 273.15))) * 1000;
}

/** Relative Feuchte (Anteil) an einer Oberfläche mit der Temperatur thetaSi. */
export function oberflaechenfeuchte(theta, phi, thetaSi) {
  return partialdruck(theta, phi) / saettigungsdruck(thetaSi);
}

/** Oberflächentemperatur, bei der die relative Feuchte an der Oberfläche den Wert grenze erreicht. */
export function kritischeTemperatur(theta, phi, grenze = KRITISCH) {
  return taupunktAusDruck(partialdruck(theta, phi) / grenze);
}

/** Höchste Raumluftfeuchte (Anteil), bei der eine Oberfläche mit thetaSi unter der Grenze bleibt. */
export function zulaessigeRaumfeuchte(theta, thetaSi, grenze = KRITISCH) {
  return (grenze * saettigungsdruck(thetaSi)) / saettigungsdruck(theta);
}

/** Oberflächentemperatur aus Temperaturfaktor und Außentemperatur. */
export function oberflaechentemperatur(thetaInnen, thetaAussen, fRsi) {
  return thetaAussen + fRsi * (thetaInnen - thetaAussen);
}

/** Temperaturfaktor, der nötig ist, damit die Oberfläche die kritische Temperatur erreicht. */
export function erforderlicherTemperaturfaktor(thetaInnen, phi, thetaAussen, grenze = KRITISCH) {
  if (thetaInnen <= thetaAussen) return null;
  return (kritischeTemperatur(thetaInnen, phi, grenze) - thetaAussen) / (thetaInnen - thetaAussen);
}

function runde(x, stellen = 1) {
  const f = 10 ** stellen;
  return Math.round(x * f) / f;
}

/** Zahl aus einem Formularfeld; leere Felder sind keine Null, sondern fehlen. */
function lesen(wert) {
  if (wert === "" || wert === null || wert === undefined) return NaN;
  return Number(String(wert).replace(",", "."));
}

/**
 * Vollständige Bewertung.
 *
 * eingabe = {
 *   innen: Raumlufttemperatur °C, feuchte: relative Feuchte in % (0–100),
 *   modus: "gemessen" | "geschaetzt",
 *   oberflaeche: gemessene Oberflächentemperatur °C (modus gemessen),
 *   aussen: Außentemperatur °C, fRsi: Temperaturfaktor 0–1 (modus geschaetzt)
 * }
 */
export function bewerten(eingabe) {
  const fehler = [];
  const innen = lesen(eingabe.innen);
  const feuchteProzent = lesen(eingabe.feuchte);
  if (!Number.isFinite(innen) || innen < -20 || innen > 50) fehler.push("Bitte eine Raumlufttemperatur zwischen −20 und 50 °C eingeben.");
  if (!Number.isFinite(feuchteProzent) || feuchteProzent <= 0 || feuchteProzent > 100) fehler.push("Bitte eine relative Luftfeuchte zwischen 1 und 100 % eingeben.");
  const modus = eingabe.modus === "geschaetzt" ? "geschaetzt" : "gemessen";
  let thetaSi;
  let aussen = null;
  let fRsi = null;
  if (modus === "gemessen") {
    thetaSi = lesen(eingabe.oberflaeche);
    if (!Number.isFinite(thetaSi) || thetaSi < -30 || thetaSi > 50) fehler.push("Bitte die gemessene Oberflächentemperatur eingeben (−30 bis 50 °C).");
  } else {
    aussen = lesen(eingabe.aussen);
    fRsi = lesen(eingabe.fRsi);
    if (!Number.isFinite(aussen) || aussen < -40 || aussen > 40) fehler.push("Bitte eine Außentemperatur zwischen −40 und 40 °C eingeben.");
    if (!Number.isFinite(fRsi) || fRsi < 0 || fRsi > 1) fehler.push("Bitte einen Temperaturfaktor zwischen 0 und 1 eingeben (DIN 4108-2: mindestens 0,70).");
    if (Number.isFinite(aussen) && Number.isFinite(innen) && aussen >= innen) fehler.push("Die Außentemperatur muss unter der Raumlufttemperatur liegen, sonst gibt es keine kalte Oberfläche zu bewerten.");
    if (!fehler.length) thetaSi = oberflaechentemperatur(innen, aussen, fRsi);
  }
  if (fehler.length) return { ok: false, fehler };

  const phi = feuchteProzent / 100;
  const pv = partialdruck(innen, phi);
  const td = taupunkt(innen, phi);
  const ts80 = kritischeTemperatur(innen, phi);
  const phiSi = oberflaechenfeuchte(innen, phi, thetaSi);
  const phiMax = zulaessigeRaumfeuchte(innen, thetaSi);
  const reserve = thetaSi - ts80;
  const fRsiMin = aussen === null ? null : erforderlicherTemperaturfaktor(innen, phi, aussen);

  let status;
  if (phiSi >= 1) status = "tauwasser";
  else if (phiSi >= KRITISCH) status = "schimmel";
  else if (phiSi >= 0.7) status = "grenzbereich";
  else status = "unkritisch";

  const schritte = [];
  let nr = 0;
  const schritt = (bezeichnung, wert, einheit, formel, grundlage) => schritte.push({ nr: ++nr, bezeichnung, wert, einheit, formel, grundlage });
  schritt("Sättigungsdampfdruck der Raumluft", runde(saettigungsdruck(innen), 0), "Pa",
    `611,2 Pa · exp(17,62 · ${runde(innen)} / (243,12 + ${runde(innen)}))`, "Magnus-Formel (Sonntag 1990)");
  schritt("Wasserdampfpartialdruck", runde(pv, 0), "Pa", `${runde(feuchteProzent)} % · Sättigungsdampfdruck`, "Definition der relativen Feuchte");
  schritt("Absolute Feuchte der Raumluft", runde(absoluteFeuchte(innen, phi), 1), "g/m³", "p_v / (461,5 J/(kg·K) · T)", "Zustandsgleichung des Wasserdampfs");
  schritt("Taupunkttemperatur", runde(td, 1), "°C", "Temperatur, bei der p_v gesättigt ist", "Umkehrung der Magnus-Formel");
  schritt("Kritische Oberflächentemperatur (80 %)", runde(ts80, 1), "°C", "Temperatur, bei der p_v / p_s = 0,80", "DIN 4108-2:2013-02, Abschnitt 6.2");
  if (modus === "geschaetzt") {
    schritt("Oberflächentemperatur aus Temperaturfaktor", runde(thetaSi, 1), "°C",
      `${runde(aussen)} + ${runde(fRsi, 2)} · (${runde(innen)} − ${runde(aussen)})`, "f_Rsi = (θ_si − θ_e) / (θ_i − θ_e)");
    schritt("Erforderlicher Temperaturfaktor", runde(fRsiMin, 2), "", `(${runde(ts80, 1)} − ${runde(aussen)}) / (${runde(innen)} − ${runde(aussen)})`, "DIN 4108-2: mindestens 0,70 unter Normbedingungen");
  }
  schritt("Relative Feuchte an der Oberfläche", runde(phiSi * 100, 0), "%", "p_v / p_s(θ_si)", "DIN 4108-2: höchstens 80 %");
  schritt("Zulässige Raumluftfeuchte bei dieser Oberfläche", runde(Math.min(phiMax, 1) * 100, 0), "%", "0,80 · p_s(θ_si) / p_s(θ_i)", "Umstellung des 80-%-Kriteriums");

  const hinweise = [
    "Stationäre Betrachtung: Kurze Feuchtespitzen beim Duschen oder Kochen werden von Oberflächen gepuffert; entscheidend ist der Mittelwert über Tage. Ein Raumklima-Protokoll über zwei bis vier Wochen zeigt das.",
    "Die Oberflächentemperatur hängt von der Stelle ab: Raumecken, Fensterlaibungen, Rollladenkästen und Flächen hinter Möbeln sind kälter als die freie Wand. Messen Sie dort, wo der Befall ist oder droht.",
    "Der Temperaturfaktor 0,70 der DIN 4108-2 ist ein Mindestwert für die Planung; Bestandsgebäude vor 1995 erreichen ihn an Wärmebrücken oft nicht. Das ist dann eine Eigenschaft des Bauteils, nicht des Nutzers.",
  ];
  if (status === "tauwasser") hinweise.unshift("An dieser Oberfläche kondensiert Wasser. Prüfen Sie zuerst, ob Feuchte aus dem Bauteil kommt (Leckage, aufsteigende Feuchte); Lüften allein löst das selten.");
  if (status === "schimmel") hinweise.unshift("Über 80 % relative Feuchte an der Oberfläche reicht für Schimmelwachstum, auch ohne sichtbares Tauwasser. Entweder die Oberfläche wärmer machen (Dämmung, Beheizen, Möbel abrücken) oder die Raumluft trockener halten.");
  if (status === "grenzbereich") hinweise.unshift("Noch unter dem Kriterium, aber ohne Reserve. Bei kälterer Witterung oder höherer Feuchte kippt die Bewertung.");

  return {
    ok: true,
    fehler: [],
    modus,
    status,
    innen: runde(innen, 1),
    feuchte: runde(feuchteProzent, 0),
    oberflaeche: runde(thetaSi, 1),
    aussen: aussen === null ? null : runde(aussen, 1),
    fRsi: fRsi === null ? null : runde(fRsi, 2),
    fRsiMin: fRsiMin === null ? null : runde(fRsiMin, 2),
    taupunkt: runde(td, 1),
    kritisch80: runde(ts80, 1),
    oberflaechenfeuchte: runde(phiSi * 100, 0),
    zulaessigeRaumfeuchte: runde(Math.min(phiMax, 1) * 100, 0),
    absoluteFeuchte: runde(absoluteFeuchte(innen, phi), 1),
    partialdruck: runde(pv, 0),
    reserve: runde(reserve, 1),
    schritte,
    hinweise,
  };
}
