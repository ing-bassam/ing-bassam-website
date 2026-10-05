// Tests für den Rechenkern des Taupunkt- und Schimmelrisiko-Rechners.
// Prüfwerte: DIN 4108-2:2013-02, Abschnitt 6.2 (20 °C / 50 % innen, −5 °C außen →
// θ_si,min = 12,6 °C, f_Rsi ≥ 0,70) und Tabellenwerte der Magnus-Formel.
import test from "node:test";
import assert from "node:assert/strict";
import {
  absoluteFeuchte, bewerten, erforderlicherTemperaturfaktor, kritischeTemperatur, oberflaechenfeuchte,
  oberflaechentemperatur, partialdruck, saettigungsdruck, taupunkt, zulaessigeRaumfeuchte,
} from "../werkzeuge/taupunkt/taupunkt.js";

const nahe = (ist, soll, toleranz, text = "") => assert.ok(Math.abs(ist - soll) <= toleranz, `${text} ist ${ist}, erwartet ${soll} ± ${toleranz}`);

test("Magnus-Formel: Sättigungsdampfdruck und Partialdruck", () => {
  nahe(saettigungsdruck(20), 2333, 5, "p_s(20 °C)");
  nahe(saettigungsdruck(0), 611.2, 0.1, "p_s(0 °C)");
  nahe(saettigungsdruck(10), 1228, 5, "p_s(10 °C)");
  nahe(partialdruck(20, 0.5), 1166, 3, "p_v(20 °C, 50 %)");
});

test("Taupunkt und absolute Feuchte bei 20 °C / 50 %", () => {
  nahe(taupunkt(20, 0.5), 9.26, 0.05, "Taupunkt");
  nahe(absoluteFeuchte(20, 0.5), 8.62, 0.05, "absolute Feuchte g/m³");
  nahe(taupunkt(22, 0.6), 13.9, 0.1, "Taupunkt 22 °C / 60 %");
});

test("DIN 4108-2: kritische Oberflächentemperatur 12,6 °C und Temperaturfaktor 0,70", () => {
  nahe(kritischeTemperatur(20, 0.5), 12.6, 0.05, "θ_s,80");
  nahe(oberflaechenfeuchte(20, 0.5, 12.6), 0.80, 0.005, "φ_si bei 12,6 °C");
  nahe(zulaessigeRaumfeuchte(20, 12.6), 0.50, 0.005, "zulässige Raumfeuchte");
  nahe(oberflaechentemperatur(20, -5, 0.7), 12.5, 1e-9, "θ_si aus f_Rsi");
  nahe(erforderlicherTemperaturfaktor(20, 0.5, -5), 0.70, 0.01, "f_Rsi,min");
  assert.equal(erforderlicherTemperaturfaktor(20, 0.5, 20), null);
});

test("Bewertung mit gemessener Oberflächentemperatur", () => {
  const schimmel = bewerten({ innen: 20, feuchte: 50, modus: "gemessen", oberflaeche: 12.5 });
  assert.equal(schimmel.ok, true);
  assert.equal(schimmel.status, "schimmel");
  assert.equal(schimmel.oberflaechenfeuchte, 81);
  assert.equal(schimmel.kritisch80, 12.6);
  assert.equal(schimmel.schritte.length, 7);
  assert.equal(bewerten({ innen: 20, feuchte: 50, modus: "gemessen", oberflaeche: 15 }).status, "unkritisch");
  assert.equal(bewerten({ innen: 20, feuchte: 50, modus: "gemessen", oberflaeche: 13.5 }).status, "grenzbereich");
  const tau = bewerten({ innen: 20, feuchte: 50, modus: "gemessen", oberflaeche: 9 });
  assert.equal(tau.status, "tauwasser");
  assert.ok(tau.hinweise[0].includes("kondensiert"));
});

test("Bewertung mit Außentemperatur und Temperaturfaktor", () => {
  const e = bewerten({ innen: 20, feuchte: 50, modus: "geschaetzt", aussen: -5, fRsi: 0.7 });
  assert.equal(e.ok, true);
  assert.equal(e.oberflaeche, 12.5);
  assert.equal(e.fRsiMin, 0.7);
  assert.equal(e.status, "schimmel");
  assert.equal(e.schritte.length, 9);
  assert.equal(bewerten({ innen: 20, feuchte: 50, modus: "geschaetzt", aussen: -5, fRsi: 0.75 }).status, "grenzbereich");
  assert.equal(bewerten({ innen: 20, feuchte: 40, modus: "geschaetzt", aussen: -5, fRsi: 0.75 }).status, "unkritisch");
});

test("Ungültige Eingaben werden benannt", () => {
  assert.equal(bewerten({ innen: 20, feuchte: 0, modus: "gemessen", oberflaeche: 12 }).ok, false);
  assert.equal(bewerten({ innen: 20, feuchte: 50, modus: "geschaetzt", aussen: 25, fRsi: 0.7 }).ok, false);
  assert.equal(bewerten({ innen: 20, feuchte: 50, modus: "geschaetzt", aussen: -5, fRsi: 1.2 }).ok, false);
  assert.equal(bewerten({ innen: "", feuchte: 50, modus: "gemessen", oberflaeche: 12 }).ok, false);
  const f = bewerten({ innen: 20, feuchte: 50, modus: "gemessen", oberflaeche: "" });
  assert.equal(f.ok, false);
  assert.match(f.fehler[0], /Oberflächentemperatur/);
});
