// Tests für den Rechenkern des Gewährleistungsfristen-Rechners.
// Aufruf: node --test "tests/**/*.test.mjs"
import test from "node:test";
import assert from "node:assert/strict";
import {
  berechne, feiertage, iso, naechsterWerktag, ostersonntag, parseDatum, plusJahre, plusMonate, datumDeutsch, wochentag,
} from "../werkzeuge/gewaehrleistungsfrist/frist.js";

const d = (text) => parseDatum(text);

test("Datum: parsen, ungültige Daten, Ausgabe", () => {
  assert.equal(iso(d("2026-03-15")), "2026-03-15");
  assert.equal(d("2026-02-30"), null);
  assert.equal(d("15.03.2026"), null);
  assert.equal(datumDeutsch("2026-03-15"), "15.03.2026");
  assert.equal(wochentag("2026-03-15"), "Sonntag");
});

test("§ 188 Abs. 3 BGB: fehlt der Tag im Zielmonat, gilt der letzte Tag des Monats", () => {
  assert.equal(iso(plusMonate(d("2024-01-31"), 1)), "2024-02-29");
  assert.equal(iso(plusMonate(d("2023-01-31"), 1)), "2023-02-28");
  assert.equal(iso(plusJahre(d("2024-02-29"), 5)), "2029-02-28");
  assert.equal(iso(plusMonate(d("2023-08-31"), 42)), "2027-02-28");
});

test("Feiertage: Osterformel und Berliner Feiertage", () => {
  assert.equal(iso(ostersonntag(2026)), "2026-04-05");
  assert.equal(iso(ostersonntag(2027)), "2027-03-28");
  const f = feiertage(2026);
  assert.equal(f.get("2026-04-03"), "Karfreitag");
  assert.equal(f.get("2026-04-06"), "Ostermontag");
  assert.equal(f.get("2026-05-14"), "Christi Himmelfahrt");
  assert.equal(f.get("2026-05-25"), "Pfingstmontag");
  assert.equal(f.get("2026-03-08"), "Internationaler Frauentag (Berlin)");
  assert.equal(feiertage(2018).has("2018-03-08"), false);
});

test("§ 193 BGB: Sonnabend, Sonntag und Feiertag verschieben auf den nächsten Werktag", () => {
  assert.equal(iso(naechsterWerktag(d("2026-03-14"))), "2026-03-16"); // Sonnabend
  assert.equal(iso(naechsterWerktag(d("2026-03-15"))), "2026-03-16"); // Sonntag
  assert.equal(iso(naechsterWerktag(d("2027-03-08"))), "2027-03-09"); // Frauentag, Montag
  assert.equal(iso(naechsterWerktag(d("2026-04-03"))), "2026-04-07"); // Karfreitag bis Dienstag nach Ostern
  assert.equal(iso(naechsterWerktag(d("2026-06-10"))), "2026-06-10"); // Mittwoch bleibt
});

test("Regelfrist BGB Bauwerk: fünf Jahre ab Abnahme, Sonntag verschiebt", () => {
  const e = berechne({ abnahme: "2021-03-15", frist: "bgb_bauwerk", heute: "2026-01-01" });
  assert.equal(e.ok, true);
  assert.equal(e.fristbeginn, "2021-03-16");
  assert.equal(e.regelende, "2026-03-15");
  assert.equal(e.ende, "2026-03-15");
  assert.equal(e.verschoben, true);
  assert.equal(e.endeWerktag, "2026-03-16");
  assert.equal(e.tageBis, 74);
  assert.equal(e.status, "knapp");
  assert.equal(e.schritte[0].bezeichnung, "Abnahme");
  assert.ok(e.schritte.some((s) => s.grundlage === "§ 193 BGB"));
});

test("Regelfrist VOB/B Bauwerk: vier Jahre, Werktag bleibt", () => {
  const e = berechne({ abnahme: "2022-06-10", frist: "vob_bauwerk", heute: "2025-06-01" });
  assert.equal(e.regelende, "2026-06-10");
  assert.equal(e.endeWerktag, "2026-06-10");
  assert.equal(e.verschoben, false);
  assert.equal(e.tageBis, 374);
  assert.equal(e.status, "laeuft");
  assert.equal(e.frist.vob, true);
  // Innerhalb von sechs Monaten vor dem Ende gilt die Frist als knapp.
  assert.equal(berechne({ abnahme: "2022-06-10", frist: "vob_bauwerk", heute: "2026-01-01" }).status, "knapp");
});

test("Vereinbarte Frist in Jahren und Monaten", () => {
  const e = berechne({ abnahme: "2023-08-31", frist: "vereinbart", vereinbartJahre: 3, vereinbartMonate: 6, heute: "2026-01-01" });
  assert.equal(e.regelende, "2027-02-28");
  assert.equal(e.frist.text, "3 Jahre und 6 Monate");
  const leer = berechne({ abnahme: "2023-08-31", frist: "vereinbart", vereinbartJahre: 0, vereinbartMonate: 0 });
  assert.equal(leer.ok, false);
});

test("Ohne Abnahmedatum keine Rechnung", () => {
  const e = berechne({ abnahme: "", frist: "bgb_bauwerk" });
  assert.equal(e.ok, false);
  assert.match(e.fehler[0], /Abnahme/);
});

test("Hemmung § 209 BGB: die gehemmten Tage verschieben das Ende", () => {
  const e = berechne({
    abnahme: "2022-06-10", frist: "vob_bauwerk", heute: "2026-01-01",
    hemmungen: [{ von: "2024-01-01", bis: "2024-01-30", art: "sonstig" }],
  });
  assert.equal(e.ende, "2026-07-10");
  assert.equal(e.endeWerktag, "2026-07-10");
});

test("Verhandlungen § 203 BGB: frühestens drei Monate nach ihrem Ende", () => {
  const e = berechne({
    abnahme: "2021-03-15", frist: "bgb_bauwerk", heute: "2026-01-01",
    hemmungen: [{ von: "2026-02-01", bis: "2026-03-10", art: "verhandlung" }],
  });
  assert.equal(e.ende, "2026-06-10");
  assert.ok(e.schritte.some((s) => s.grundlage === "§ 203 Satz 2 BGB"));
});

test("Gerichtliches Verfahren § 204 BGB: Hemmung endet sechs Monate nach Beendigung", () => {
  const e = berechne({
    abnahme: "2021-03-15", frist: "bgb_bauwerk", heute: "2026-01-01",
    hemmungen: [{ von: "2025-01-10", bis: "2025-03-10", art: "verfahren" }],
  });
  assert.equal(e.ende, "2026-11-14");
  assert.equal(e.endeWerktag, "2026-11-16");
});

test("Hemmung außerhalb der laufenden Frist verlängert nicht", () => {
  const e = berechne({
    abnahme: "2021-03-15", frist: "bgb_bauwerk", heute: "2026-01-01",
    hemmungen: [{ von: "2019-01-01", bis: "2019-06-01", art: "sonstig" }],
  });
  assert.equal(e.ende, "2026-03-15");
  assert.ok(e.hinweise.some((h) => /außerhalb/.test(h)));
});

test("VOB/B § 13 Abs. 5: schriftliche Mängelrüge und Abnahme der Mängelbeseitigung", () => {
  const ruege = berechne({ abnahme: "2022-06-10", frist: "vob_bauwerk", ruege: "2025-12-01", heute: "2026-01-01" });
  assert.equal(ruege.ende, "2027-12-01");
  assert.equal(ruege.endeWerktag, "2027-12-01");
  const spaet = berechne({ abnahme: "2022-06-10", frist: "vob_bauwerk", ruege: "2026-07-01", heute: "2026-01-01" });
  assert.equal(spaet.ende, "2026-06-10");
  assert.ok(spaet.hinweise.some((h) => /nach Ablauf der Regelfrist/.test(h)));
  const beseitigung = berechne({ abnahme: "2022-06-10", frist: "vob_bauwerk", beseitigungAbnahme: "2026-01-20", heute: "2026-01-01" });
  assert.equal(beseitigung.ende, "2028-01-20");
  const bgb = berechne({ abnahme: "2021-03-15", frist: "bgb_bauwerk", ruege: "2025-12-01", heute: "2026-01-01" });
  assert.equal(bgb.ende, "2026-03-15");
  assert.ok(bgb.hinweise.some((h) => /nur bei vereinbarter VOB\/B/.test(h)));
});

test("Anerkenntnis § 212 BGB: die volle Frist beginnt neu", () => {
  const e = berechne({ abnahme: "2021-03-15", frist: "bgb_bauwerk", anerkenntnis: "2024-05-02", heute: "2026-01-01" });
  assert.equal(e.ende, "2029-05-02");
  assert.equal(e.endeWerktag, "2029-05-02");
  const zuSpaet = berechne({ abnahme: "2021-03-15", frist: "bgb_bauwerk", anerkenntnis: "2026-04-01", heute: "2026-01-01" });
  assert.equal(zuSpaet.ende, "2026-03-15");
  assert.ok(zuSpaet.hinweise.some((h) => /nach dem errechneten Fristende/.test(h)));
});

test("Abgelaufene Frist wird als solche gemeldet", () => {
  const e = berechne({ abnahme: "2018-01-10", frist: "bgb_bauwerk", heute: "2026-01-01" });
  assert.equal(e.regelende, "2023-01-10");
  assert.equal(e.status, "abgelaufen");
  assert.ok(e.tageBis < 0);
});
