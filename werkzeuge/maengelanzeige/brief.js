/**
 * Mängelanzeige-Generator – Rechenkern ohne Browser-Abhängigkeiten.
 *
 * Erzeugt aus strukturierten Angaben den Text einer Mängelanzeige mit
 * Fristsetzung. Die Formulierungen folgen dem Musterschreiben des Büros
 * (vorlagen/maengelanzeige-mit-fristsetzung.yml, Stand 2026-09-29): Ort und
 * Erscheinungsbild je Mangel, keine Ursachenbehauptung, konkretes Fristdatum,
 * Vorbehalt weiterer Rechte, Bitte um Eingangsbestätigung.
 *
 * Rechtsgrundlagen: §§ 634, 635, 637 BGB; § 4 Abs. 7 und § 13 Abs. 5 VOB/B.
 * Das Werkzeug ersetzt keine Rechtsberatung.
 */

export const ANLAGEN = {
  fotos: "Lichtbilder mit Datum und Maßangabe",
  liste: "Nummerierte Mängelliste mit Ort und Erscheinungsbild",
  vertrag: "Kopie des Bauvertrags oder des Abnahmeprotokolls",
  gutachten: "Gutachterliche Stellungnahme",
};

/** Prüfpunkte vor dem Absenden, aus dem Musterschreiben des Büros. */
export const PRUEFLISTE = [
  "Das Schreiben ist an das Unternehmen gerichtet, mit dem der Vertrag besteht, nicht an Architekt, Bauleitung oder Nachunternehmer.",
  "Bestehen mehrere Verträge, geht je Vertrag ein eigenes Schreiben hinaus.",
  "Bei Wohnungseigentum ist geklärt, ob der Mangel am Sondereigentum oder am Gemeinschaftseigentum auftritt.",
  "Bauvorhaben, Vertragsdatum und betroffene Leistung sind eindeutig bezeichnet.",
  "Die Vertragsgrundlage ist angegeben: Werkvertragsrecht des Bürgerlichen Gesetzbuchs oder einbezogene VOB/B.",
  "Im Schreiben steht, ob die Leistung schon abgenommen ist.",
  "Jeder Mangel ist einzeln aufgeführt.",
  "Zu jedem Mangel ist der Ort genau bezeichnet: Gebäude, Geschoss, Raum oder Bauteil.",
  "Zu jedem Mangel ist das Erscheinungsbild beschrieben, nicht nur das Wort mangelhaft.",
  "Eine Ursache wird nicht behauptet.",
  "Das Datum der Feststellung ist eingetragen.",
  "Die Lichtbilder tragen Datum, eine Maßangabe und eine erkennbare Lage im Raum.",
  "Die Anlagen sind vollständig und im Schreiben genannt.",
  "Die Frist nennt ein konkretes Kalenderdatum.",
  "Die Frist gilt für den Abschluss der Arbeiten.",
  "Die Frist ist so bemessen, dass die Arbeiten in dieser Zeit tatsächlich abgeschlossen werden können.",
  "Der Vorbehalt weiterer Rechte steht im Schreiben.",
  "Das Schreiben geht vor Ablauf der Verjährungsfrist hinaus.",
  "Der Zugang ist nachweisbar, etwa durch Boten mit Empfangsbestätigung oder Einschreiben mit Rückschein.",
  "Eine Kopie mit Absendedatum liegt in der Bauakte, und eine Wiedervorlage nach Fristablauf ist notiert.",
];

const TAG = 86_400_000;

export function parseDatum(text) {
  const t = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text || "").trim());
  if (!t) return null;
  const [j, m, d] = t.slice(1).map(Number);
  const datum = new Date(Date.UTC(j, m - 1, d));
  return datum.getUTCFullYear() === j && datum.getUTCMonth() === m - 1 && datum.getUTCDate() === d ? datum : null;
}

export function datumDeutsch(iso) {
  const d = parseDatum(iso);
  return d ? `${String(d.getUTCDate()).padStart(2, "0")}.${String(d.getUTCMonth() + 1).padStart(2, "0")}.${d.getUTCFullYear()}` : "";
}

function text(wert) {
  return String(wert ?? "").replace(/\s+/g, " ").trim();
}

function aufzaehlung(teile) {
  if (teile.length <= 1) return teile.join("");
  return `${teile.slice(0, -1).join(", ")} und ${teile[teile.length - 1]}`;
}

/** Prüft die Angaben; Fehler verhindern den Brief, Hinweise begleiten ihn. */
export function pruefen(eingabe) {
  const fehler = [];
  const hinweise = [];
  const heute = parseDatum(eingabe.datum);
  if (!heute) fehler.push("Bitte das Datum des Schreibens eintragen.");
  if (!text(eingabe.empfaenger?.firma)) fehler.push("Bitte das Unternehmen eintragen, mit dem der Vertrag besteht.");
  if (!text(eingabe.absender?.name)) fehler.push("Bitte Ihren Namen als Absender eintragen.");
  if (!text(eingabe.bauvorhaben)) fehler.push("Bitte das Bauvorhaben bezeichnen (z. B. Adresse oder Projektname).");
  if (!text(eingabe.leistung)) fehler.push("Bitte die beauftragte Leistung benennen (z. B. Fliesenarbeiten im Erdgeschoss).");
  if (!parseDatum(eingabe.vertragsdatum)) fehler.push("Bitte das Datum des Bauvertrags eintragen.");
  if (eingabe.abnahme !== "nein" && !parseDatum(eingabe.abnahmeDatum)) fehler.push("Bitte das Datum der Abnahme eintragen.");
  if (eingabe.abnahme === "vorbehalt" && !text(eingabe.vorbehaltNr)) fehler.push("Bitte die Nummer des Vorbehalts im Abnahmeprotokoll eintragen.");

  const maengel = (eingabe.maengel || []).filter((m) => text(m.ort) || text(m.erscheinung) || text(m.datum));
  if (!maengel.length) fehler.push("Bitte mindestens einen Mangel mit Ort und Erscheinungsbild eintragen.");
  maengel.forEach((m, i) => {
    if (!text(m.ort)) fehler.push(`Mangel ${i + 1}: Bitte den Ort genau bezeichnen (Gebäude, Geschoss, Raum, Bauteil).`);
    if (!text(m.erscheinung)) fehler.push(`Mangel ${i + 1}: Bitte das Erscheinungsbild beschreiben.`);
    if (!parseDatum(m.datum)) fehler.push(`Mangel ${i + 1}: Bitte das Datum der Feststellung eintragen.`);
    if (/\b(verursacht|ursache|weil|aufgrund|wegen|pfusch|fehlerhaft ausgeführt)\b/i.test(text(m.erscheinung))) {
      hinweise.push(`Mangel ${i + 1}: Die Beschreibung klingt nach einer Ursachenbehauptung. Beschreiben Sie nur, was zu sehen ist – die Ursache muss das Unternehmen untersuchen.`);
    }
  });
  if (maengel.length > 3) hinweise.push("Bei mehr als drei Mängeln empfiehlt das Musterschreiben zusätzlich eine nummerierte Mängelliste als Anlage.");

  const frist = parseDatum(eingabe.frist);
  if (!frist) fehler.push("Bitte ein konkretes Datum für das Ende der Frist eintragen.");
  else if (heute) {
    const tage = Math.round((frist - heute) / TAG);
    if (tage <= 0) fehler.push("Die Frist muss nach dem Datum des Schreibens liegen.");
    else if (tage < 10) hinweise.push(`Die Frist beträgt nur ${tage} Tage. Maßgebend ist die Zeit, die für die Arbeiten objektiv nötig ist; eine zu kurze Frist setzt eine angemessene in Gang, aber wer vor deren Ablauf selbst handelt, riskiert seine Ansprüche.`);
  }
  const rueck = parseDatum(eingabe.rueckmeldung);
  if (eingabe.rueckmeldung && !rueck) fehler.push("Das Datum für die Rückmeldung ist ungültig.");
  if (rueck && frist && rueck >= frist) hinweise.push("Die Rückmeldefrist sollte deutlich vor dem Fristende liegen.");
  if (eingabe.vertragsart === "vob" && eingabe.abnahme === "nein") {
    hinweise.push("Vor der Abnahme hat das Unternehmen erkannte Mängel nach § 4 Abs. 7 VOB/B auf eigene Kosten zu beseitigen; die Anzeige mit Frist ist trotzdem sinnvoll, schon aus Beweisgründen.");
  }
  if (eingabe.gefahr && !text(eingabe.sicherung)) hinweise.push("Sie haben eine Gefahr angegeben – tragen Sie ein, welche Sicherungsmaßnahme Sie veranlasst haben.");
  hinweise.push("Der Zugang zählt, nicht die Absendung: Bote mit Empfangsbestätigung oder Einschreiben mit Rückschein; eine einfache E-Mail belegt den Zugang in der Regel nicht.");
  return { fehler, hinweise };
}

/** Baut den Brief als Struktur: Adressblöcke, Betreff, Absätze, Grußformel, Anlagen. */
export function briefErzeugen(eingabe) {
  const { fehler, hinweise } = pruefen(eingabe);
  if (fehler.length) return { ok: false, fehler, hinweise, brief: null };

  const ich = Boolean(eingabe.einzelperson);
  const f = (wir, ichForm) => (ich ? ichForm : wir);
  const maengel = (eingabe.maengel || []).filter((m) => text(m.ort) || text(m.erscheinung));
  const mehrere = maengel.length > 1;
  const vob = eingabe.vertragsart === "vob";
  const a = eingabe.absender || {};
  const e = eingabe.empfaenger || {};

  const absaetze = [];
  absaetze.push(
    `zwischen Ihnen als Auftragnehmer und ${f("uns", "mir")} als Auftraggeber besteht der Bauvertrag vom ${datumDeutsch(eingabe.vertragsdatum)} über ${text(eingabe.leistung)}. `
    + (vob ? "In diesen Vertrag ist die VOB/B einbezogen. " : "Für diesen Vertrag gilt das Werkvertragsrecht des Bürgerlichen Gesetzbuchs. ")
    + `Hiermit ${f("zeigen wir", "zeige ich")} ${mehrere ? "Mängel" : "einen Mangel"} an und ${f("fordern", "fordere")} Sie zu ${mehrere ? "deren" : "dessen"} Beseitigung auf.`,
  );

  if (eingabe.abnahme === "ja") {
    absaetze.push(`Die Abnahme erfolgte am ${datumDeutsch(eingabe.abnahmeDatum)}.`);
  } else if (eingabe.abnahme === "vorbehalt") {
    absaetze.push(`Die Abnahme erfolgte am ${datumDeutsch(eingabe.abnahmeDatum)}; ${mehrere ? "die nachstehenden Mängel sind" : "der nachstehende Mangel ist"} im Abnahmeprotokoll unter Nummer ${text(eingabe.vorbehaltNr)} vorbehalten.`);
  } else {
    absaetze.push("Die Leistung ist bisher nicht abgenommen.");
  }

  if (mehrere) {
    absaetze.push(`${f("Wir haben", "Ich habe")} folgende Mängel festgestellt:`);
    absaetze.push({ liste: maengel.map((m) => `${text(m.ort)} – ${text(m.erscheinung)} (festgestellt am ${datumDeutsch(m.datum)})`) });
  } else {
    const m = maengel[0];
    absaetze.push(`Am ${datumDeutsch(m.datum)} ${f("haben wir", "habe ich")} Folgendes festgestellt: ${text(m.ort)} – ${text(m.erscheinung)}.`);
  }

  absaetze.push(
    `Die Ursache der beschriebenen ${mehrere ? "Erscheinungen" : "Erscheinung"} ${f("benennen wir", "benenne ich")} nicht. `
    + `${f("Wir beschreiben", "Ich beschreibe")} das Erscheinungsbild und seine Lage; die Untersuchung der Ursache liegt bei Ihnen.`,
  );

  const anlagen = (eingabe.anlagen || []).filter((k) => ANLAGEN[k]).map((k) => ANLAGEN[k]);
  text(eingabe.anlagenWeitere).split(/\s*;\s*/).filter(Boolean).forEach((z) => anlagen.push(z));
  if (anlagen.length) {
    absaetze.push(`${aufzaehlung(anlagen)} ${anlagen.length > 1 ? "sind" : "ist"} diesem Schreiben als Anlage beigefügt.`);
  }

  absaetze.push(
    `${f("Wir fordern", "Ich fordere")} Sie auf, ${mehrere ? "die vorstehend beschriebenen Mängel" : "den vorstehend beschriebenen Mangel"} bis zum ${datumDeutsch(eingabe.frist)} vollständig zu beseitigen. `
    + "Die Frist bezieht sich auf den Abschluss der Arbeiten, nicht auf deren Beginn.",
  );

  if (text(eingabe.zeiten)) {
    const ansprech = text(eingabe.ansprechpartner) || [text(a.name), text(a.telefon), text(a.email)].filter(Boolean).join(", ");
    let satz = `Für die Ausführung stehen folgende Zeiten zur Verfügung: ${text(eingabe.zeiten)}. Bitte stimmen Sie den Termin vorher mit ${ansprech} ab.`;
    if (text(eingabe.zugang)) satz += ` Den Zugang zu ${text(eingabe.zugang)} ${f("stellen wir", "stelle ich")} sicher.`;
    absaetze.push(satz);
  }

  absaetze.push(`Auf welche Weise Sie ${mehrere ? "die Mängel" : "den Mangel"} beseitigen, entscheiden Sie. Das Ergebnis muss der vertraglich vereinbarten Beschaffenheit entsprechen.`);
  absaetze.push(`Weitere Rechte ${f("behalten wir uns", "behalte ich mir")} ausdrücklich vor. Nach Ablauf der Frist ${f("prüfen wir", "prüfe ich")}, welche Mängelrechte ${f("uns", "mir")} zustehen.`);

  const rueck = parseDatum(eingabe.rueckmeldung) ? datumDeutsch(eingabe.rueckmeldung) : null;
  if (rueck) {
    absaetze.push(`Bitte bestätigen Sie ${f("uns", "mir")} den Erhalt dieses Schreibens und teilen ${f("uns", "mir")} bis zum ${rueck} mit, wann Sie die Arbeiten ausführen.`);
  } else {
    absaetze.push(`Bitte bestätigen Sie ${f("uns", "mir")} den Erhalt dieses Schreibens und teilen ${f("uns", "mir")} mit, wann Sie die Arbeiten ausführen.`);
  }

  if (eingabe.gefahr) {
    const sicherung = text(eingabe.sicherung) || "Sicherungsmaßnahmen";
    absaetze.push(`Der beschriebene Zustand kann zu weiteren Schäden führen. ${f("Wir haben", "Ich habe")} ${sicherung} veranlasst und ${f("bitten", "bitte")} um Rückmeldung bis zum ${rueck || datumDeutsch(eingabe.frist)}.`);
  }

  const brief = {
    absender: [text(a.name), text(a.strasse), text(a.plzOrt), [text(a.telefon), text(a.email)].filter(Boolean).join(" · ")].filter(Boolean),
    empfaenger: [text(e.firma), text(e.zusatz), text(e.strasse), text(e.plzOrt)].filter(Boolean),
    ortDatum: `${text(eingabe.ort) ? text(eingabe.ort) + ", den " : ""}${datumDeutsch(eingabe.datum)}`,
    betreff: `Mängelanzeige mit Fristsetzung – Bauvorhaben ${text(eingabe.bauvorhaben)}, ${text(eingabe.leistung)}`,
    anrede: text(eingabe.anrede) || "Sehr geehrte Damen und Herren,",
    absaetze,
    gruss: "Mit freundlichen Grüßen",
    unterschrift: text(a.name),
    anlagen,
  };
  return { ok: true, fehler: [], hinweise, brief };
}

/** Der Brief als reiner Text, etwa zum Kopieren in ein Schreibprogramm. */
export function briefText(brief) {
  const zeilen = [];
  zeilen.push(...brief.absender, "");
  zeilen.push(...brief.empfaenger, "");
  zeilen.push(brief.ortDatum, "");
  zeilen.push(brief.betreff, "");
  zeilen.push(brief.anrede, "");
  for (const absatz of brief.absaetze) {
    if (typeof absatz === "string") {
      zeilen.push(absatz, "");
    } else {
      absatz.liste.forEach((eintrag, i) => zeilen.push(`${i + 1}. ${eintrag}`));
      zeilen.push("");
    }
  }
  zeilen.push(brief.gruss, "", "", brief.unterschrift);
  if (brief.anlagen.length) {
    zeilen.push("", "Anlagen:");
    brief.anlagen.forEach((eintrag) => zeilen.push(`– ${eintrag}`));
  }
  return zeilen.join("\n");
}
