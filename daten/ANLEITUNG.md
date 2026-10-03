# Marktdaten pflegen – Anleitung

Der Wertrechner rechnet mit den Zahlen aus `daten/marktdaten.xlsx`. Diese Datei pflegt
das Büro selbst. Der Browser der Besucher liest sie nie; er bekommt nur die daraus
erzeugte Datei `wertrechner/data/marktdaten.json`.

## Der Ablauf in drei Schritten

1. **Neue Werte eintragen.** `daten/marktdaten.xlsx` öffnen, Zahlen ändern, in der
   Spalte „Quelle/Stand“ die neue Veröffentlichung mit Seitenzahl eintragen, speichern.
2. **Umwandeln.** Entweder lokal `python tools/marktdaten_bauen.py` ausführen – oder
   auf GitHub unter *Actions → „Marktdaten bauen“ → Run workflow* klicken. Die Action
   erzeugt die JSON-Datei und öffnet einen Pull Request mit den Änderungen.
3. **Hochladen bzw. Pull Request mergen.** Danach ist der Rechner in wenigen Minuten
   aktuell.

Das Skript prüft vor dem Schreiben: Pflichtblätter vorhanden? Pflichtschlüssel
belegt? Jede Zeile mit „Quelle/Stand“? Fehlt etwas, bricht es mit einer klaren
Meldung ab und schreibt nichts.

## Regeln für die Excel-Datei

- Erste Zeile = Spaltennamen, jede weitere Zeile ein Datensatz. Spaltennamen nicht
  umbenennen; der Rechner sucht nach ihnen.
- In den Blättern `Modellparameter`, `Sachwertfaktoren` und `Liegenschaftszinssaetze`
  gilt: Spalte „Schlüssel“ nicht ändern, nur „Wert“.
- Zahlen als Zahlen eintragen (kein Text wie „13,80 €“). Prozentwerte als Zahl ohne
  Prozentzeichen (2 statt 2 %). Datumswerte als Datum.
- Neue Zeilen sind erlaubt (z. B. ein weiterer Baupreisindex), gelöschte Zeilen
  nur, wenn der Rechner sie nicht braucht.
- Blätter, deren Name mit `_` beginnt, werden ignoriert – geeignet für Notizen.
- `tools/marktdaten_anlegen.py` kann die Datei im Ausgangszustand neu erzeugen
  (`--erzwingen`). Eigene Änderungen gehen dabei verloren.

## Was jedes Jahr zu aktualisieren ist

| Wann | Was | Wo in der Excel-Datei | Quelle |
|---|---|---|---|
| Sommer (Juli–Sept.) | **Sachwertfaktoren** (neue Formelkonstanten, Gruppen, Korrekturen, Gültigkeitsbereich, RND-Tabellen, Baupreisindex, BRW-Stichtag) | `Sachwertfaktoren`, `SWF_Korrekturen`, `RND` (Verfahren sachwert), `Gueltigkeit`, `Baupreisindex`, `Modellparameter` (`bpi_*`, `brw_stichtag_modell`, `stichtag_faktoren`) | berlin.de/gutachterausschuss → Daten zur Wertermittlung → Sachwertfaktoren |
| Herbst (Sept.–Okt.) | **Liegenschaftszinssätze** (Formel, Zuschläge, Korrekturen, Bewirtschaftungskosten, RND-Tabellen, Gültigkeitsbereich, ggf. Ortsteiltabelle) | `Liegenschaftszinssaetze`, `Bewirtschaftungskosten`, `RND` (Verfahren ertragswert), `Gueltigkeit`, `Ortsteile` | ebenda → Liegenschaftszinssätze |
| Frühjahr (ab Februar) | **Bodenrichtwerte** zum 01.01. – nur zur Anzeige; für die Berechnung erst, wenn die neuen Faktoren diesen Stichtag vorschreiben | `Modellparameter` (`brw_stichtag_aktuell`) **und** `tools/adressdaten_bauen.py` (Konstanten `BRW_MODELL`, `BRW_AKTUELL`), danach Skript neu laufen lassen | Geoportal Berlin, WFS brw20xx |
| mit neuem Mietspiegel (alle 2 Jahre) | **Wohnlagen** | `tools/adressdaten_bauen.py` (Konstanten `WOHNLAGEN`, `WOHNLAGEN_STAND`) | Geoportal Berlin, WFS wohnlagenadr20xx |
| bei Bedarf | **GFZ-Umrechnungskoeffizienten** (zuletzt 2004, selten) | `GFZ_Koeffizienten` | ebenda → GFZ-Umrechnungskoeffizienten |

Wichtig: Baupreisindex und Bodenrichtwert-Stichtag gehören zum Modell. Beide
**immer zusammen mit den Sachwertfaktoren** umstellen – nie einzeln „aktualisieren“,
sonst stimmt das Modell nicht mehr (§ 10 ImmoWertV, siehe `fachliteratur/MODELL-BERLIN.md`).

## Adressen und Bodenrichtwerte neu bauen

```bash
python tools/adressdaten_bauen.py
```

Lädt die offenen Daten des Landes Berlin (einmalig ca. 300 MB in `.wertrechner-cache/`)
und schreibt `wertrechner/data/adressen/<PLZ>.json`. Dauer: einige Minuten. Auf GitHub
geht das ebenfalls über *Actions → „Marktdaten bauen“* mit dem Haken „Adressen neu bauen“.
