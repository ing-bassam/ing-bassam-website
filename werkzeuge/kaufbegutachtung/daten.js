// Kaufbegutachtung – Preise, Optionen, Hinweisregeln, Unterlagen und Texte (Deutsch und Englisch).
//
// EINZIGE QUELLE für die Seiten leistungen/kaufbegutachtung/ und
// en/pre-purchase-inspection-berlin/ sowie für den Rechner (kaufbegutachtung.js, app.js).
//
// Ändern: Werte und Texte hier anpassen, dann
//     python tools/kaufbegutachtung_bauen.py
// ausführen – das schreibt die festen Abschnitte beider Seiten (Preistabellen,
// Hinweise, Unterlagen, FAQ, Strukturdaten) neu. tests/test_kaufbegutachtung.py
// prüft, dass Seiten und Daten übereinstimmen.
//
// Zwischen den Markierungen steht reines JSON (doppelte Anführungszeichen, keine
// Kommentare, kein Komma am Ende), damit auch Python die Daten lesen kann.
//
// Bedeutung: Preise netto in Euro; brutto = netto × (1 + mwst), auf Cent gerundet.
// zuschlaege[].auto: fällt an ab der Wohnfläche flaeche_ab und/oder wenn der Schalter
// (eingaben.preis_schalter) an ist – Zuschläge sind keine frei wählbaren Optionen.
// regeln[]: Bedingungen sind UND-verknüpft (objekt, von/bis = Baujahr inklusive,
// heizung/nutzung/region = Liste, fertighaus/mfh6/milieuschutz = Schalter an);
// empfiehlt = Optionen, die bei dieser Regel als „empfohlen“ markiert werden.
// unterlagen.*[].prio: 1 unverzichtbar, 2 wichtig, 3 wenn vorhanden.
// seite: Texte nur für die Website (Oberfläche, FAQ, Kategorien); in seite.*.faq
// und sprach_hinweis stehen Platzhalter {brutto:ID}, {netto:ID} und {text:SCHLUESSEL}.

export const DATEN = /* DATEN-ANFANG */ {
  "stand": {
    "de": "Oktober 2026",
    "en": "October 2026"
  },
  "mwst": 0.19,
  "stundensatz_netto": 75,
  "urls": {
    "de": "https://ing-bassam.de/leistungen/kaufbegutachtung/",
    "en": "https://ing-bassam.de/en/pre-purchase-inspection-berlin/"
  },
  "anker": {
    "de": {
      "efh": "haus",
      "etw": "wohnung"
    },
    "en": {
      "efh": "house",
      "etw": "flat"
    }
  },
  "kontakt": {
    "firma": "Bassam Ingenieurbüro für Bauwesen GmbH",
    "adresse": "Straße am Flugplatz 6a · 12487 Berlin",
    "telefon": "+49 176 23581339",
    "email": "info@ing-bassam.de",
    "web": "www.ing-bassam.de",
    "gf": "M. Sc. Abdel Karim Abu Elkheir",
    "register": "HRB 274183 B (AG Charlottenburg) · USt-ID DE455794705"
  },
  "pakete": {
    "etw": {
      "grund": {
        "id": "grund_etw",
        "netto": 890,
        "de": {
          "name": "Kaufbegutachtung Eigentumswohnung",
          "kurz": "bis ca. 100 m², keine Maisonette oder Dachgeschosswohnung",
          "text": "Auswertung der WEG-Unterlagen, Begehung der Wohnung und des zugänglichen Gemeinschaftseigentums (ca. 2–3 Std.), mündliches Fazit vor Ort, schriftlicher Zustandsbericht mit Mängelliste, Kostenrahmen für 10–15 Jahre, Rücklagen-Einschätzung und Ihr Kostenanteil, Pflichten nach dem Kauf."
        },
        "en": {
          "name": "Pre-purchase inspection, flat",
          "kurz": "up to approx. 100 m², not a maisonette or attic flat",
          "text": "Review of the owners’ association (WEG) records, inspection of the flat and the accessible common property (approx. 2–3 h), verbal summary on site, written condition report with defect list, 10–15-year cost outlook, assessment of the maintenance reserve and your cost share, duties after purchase."
        }
      },
      "zuschlaege": [
        {
          "id": "gross_etw",
          "netto": 200,
          "auto": {
            "flaeche_ab": 100.01,
            "schalter": "maisonette"
          },
          "de": {
            "name": "Über 100 m², Maisonette oder Dachgeschoss",
            "text": "Mehraufwand bei Begehung und Bericht."
          },
          "en": {
            "name": "Above 100 m², maisonette or attic flat",
            "text": "Additional inspection and reporting effort."
          }
        }
      ],
      "optionen": ["vermietung", "thermo_etw", "schadstoff", "bauakte", "englisch", "express", "zweit"]
    },
    "efh": {
      "grund": {
        "id": "grund_efh",
        "netto": 1490,
        "de": {
          "name": "Kaufbegutachtung Einfamilienhaus",
          "kurz": "bis ca. 200 m² Wohnfläche, ohne Vollkeller",
          "text": "Vorbereitung und Unterlagenauswertung, Begehung vom Dach bis zum Keller, soweit zugänglich (ca. 4–5 Std.), mündliches Fazit vor Ort, schriftlicher Zustandsbericht mit Mängelliste, Kostenrahmen für 10–15 Jahre, Lage-Check aus amtlichen Karten, Pflichten nach dem Kauf."
        },
        "en": {
          "name": "Pre-purchase inspection, house",
          "kurz": "up to approx. 200 m² living area, without full basement",
          "text": "Preparation and document review, inspection from roof to basement as far as accessible (approx. 4–5 h), verbal summary on site, written condition report with defect list, 10–15-year cost outlook, location check from official maps, duties after purchase."
        }
      },
      "zuschlaege": [
        {
          "id": "keller",
          "netto": 150,
          "de": {
            "name": "Vollunterkellerung",
            "text": "Erweiterte Begehung und Feuchtemessung im Keller."
          },
          "en": {
            "name": "Full basement",
            "text": "Extended inspection and moisture readings in the basement."
          },
          "auto": {
            "schalter": "vollkeller"
          }
        },
        {
          "id": "gross_efh",
          "netto": 200,
          "auto": {
            "flaeche_ab": 200.01,
            "schalter": "einlieger"
          },
          "de": {
            "name": "Über 200 m² Wohnfläche oder Einliegerwohnung",
            "text": "Mehraufwand bei Begehung und Bericht."
          },
          "en": {
            "name": "Above 200 m² living area or granny flat",
            "text": "Additional inspection and reporting effort."
          }
        }
      ],
      "optionen": ["thermo_efh", "drohne", "schadstoff", "bauakte", "englisch", "express", "zweit"]
    }
  },
  "optionen": {
    "vermietung": {
      "netto": 290,
      "de": {
        "name": "Vermietungs-Check",
        "text": "Alle Merkmale der Mietspiegel-Orientierungshilfe vor Ort aufgenommen, Mietspiegel-Einordnung (Ist-Zustand und Verbesserungen), Wohnflächen-Plausibilität, Vermieterpflichten technisch geprüft. Keine Rechtsberatung."
      },
      "en": {
        "name": "Rental check",
        "text": "All features of Berlin’s rent-index guidance recorded on site, rent-index classification (as is and with upgrades), living-area plausibility, landlord duties checked technically. No legal advice."
      }
    },
    "thermo_etw": {
      "netto": 190,
      "de": {
        "name": "Thermografie der Wohnung",
        "text": "Wärmebilder nach DIN EN ISO 6781-1, nur bei ausreichendem Temperaturunterschied innen/außen (Faustregel mind. 10 K; meist November bis März, frühmorgens); ggf. Kurztermin ohne Mehrkosten."
      },
      "en": {
        "name": "Thermal imaging of the flat",
        "text": "Thermography to DIN EN ISO 6781-1, only with a sufficient indoor/outdoor temperature difference (rule of thumb at least 10 K; usually November to March, early morning); a short separate visit at no extra cost if needed."
      }
    },
    "thermo_efh": {
      "netto": 290,
      "de": {
        "name": "Thermografie der Gebäudehülle",
        "text": "Wärmebilder außen und innen nach DIN EN ISO 6781-1, nur bei ausreichendem Temperaturunterschied innen/außen (Faustregel mind. 10 K; meist November bis März, frühmorgens); ggf. Kurztermin ohne Mehrkosten."
      },
      "en": {
        "name": "Thermal imaging of the building envelope",
        "text": "External and internal thermography to DIN EN ISO 6781-1, only with a sufficient indoor/outdoor temperature difference (rule of thumb at least 10 K; usually November to March, early morning); a short separate visit at no extra cost if needed."
      }
    },
    "drohne": {
      "netto": 250,
      "de": {
        "name": "Drohnenaufnahmen von Dach und Fassade",
        "text": "Nur wenn der Flug zulässig ist (Geozonen, Zustimmung der überflogenen Eigentümer). Ist er es nicht, entfällt die Option ohne Kosten."
      },
      "en": {
        "name": "Drone images of roof and façade",
        "text": "Only where the flight is permitted (geo-zones, consent of the owners overflown). If it is not, the option is dropped at no cost."
      }
    },
    "schadstoff": {
      "netto": 240,
      "de": {
        "name": "Schadstoffproben mit Laboranalyse",
        "text": "Bis zu 3 Materialproben (z. B. Asbest, alte Mineralwolle, PAK) im akkreditierten Labor, jede weitere 71,40 € (60 € netto). Nur mit Zustimmung des Eigentümers."
      },
      "en": {
        "name": "Pollutant samples with lab analysis",
        "text": "Up to 3 material samples (e.g. asbestos, old mineral wool, PAH) analysed by an accredited lab, each further sample €71.40 (€60 net). Only with the owner’s consent."
      }
    },
    "bauakte": {
      "netto_von": 225,
      "netto_bis": 300,
      "de": {
        "name": "Einsicht in die Bauakte",
        "text": "Beim Bauaktenarchiv des Bezirks mit Vollmacht des Eigentümers; 89,25 € je Stunde (75 € netto), meist 3–4 Std. Amtsgebühren (ab ca. 36 €) reichen wir ohne Aufschlag weiter."
      },
      "en": {
        "name": "Building-file review",
        "text": "At the district building-file archive with the owner’s power of attorney; €89.25 per hour (€75 net), usually 3–4 h. Office fees (from approx. €36) passed on without mark-up."
      }
    },
    "englisch": {
      "netto": 120,
      "de": {
        "name": "Bericht auf Englisch",
        "text": "Zustandsbericht auf Englisch, mit Glossar der deutschen Fachbegriffe (Hausgeld, Erhaltungsrücklage, Teilungserklärung)."
      },
      "en": {
        "name": "Report in English",
        "text": "Condition report in English, with a glossary of the German terms (Hausgeld, maintenance reserve, declaration of division)."
      }
    },
    "express": {
      "netto": 190,
      "de": {
        "name": "Express-Bericht",
        "text": "Schriftlicher Bericht innerhalb von 3 Werktagen statt 7–10."
      },
      "en": {
        "name": "Express report",
        "text": "Written report within 3 working days instead of 7–10."
      }
    },
    "zweit": {
      "netto": 290,
      "de": {
        "name": "Zweittermin",
        "text": "Z. B. nach dem Öffnen von Bauteilen, zur Nachverhandlung oder vor der Übergabe."
      },
      "en": {
        "name": "Second visit",
        "text": "E.g. after building parts have been opened, for renegotiation or before handover."
      }
    }
  },
  "eingaben": {
    "heizung": [
      {
        "id": "gas",
        "de": "Gas-Zentralheizung",
        "en": "Gas central heating"
      },
      {
        "id": "gasetage",
        "de": "Gasetagenheizung (Therme in der Wohnung)",
        "en": "Gas boiler in the flat"
      },
      {
        "id": "oel",
        "de": "Ölheizung",
        "en": "Oil heating"
      },
      {
        "id": "fernwaerme",
        "de": "Fernwärme",
        "en": "District heating"
      },
      {
        "id": "waermepumpe",
        "de": "Wärmepumpe",
        "en": "Heat pump"
      },
      {
        "id": "holz",
        "de": "Kamin-, Kachel- oder Pelletofen",
        "en": "Wood, pellet or tiled stove"
      },
      {
        "id": "nachtspeicher",
        "de": "Nachtspeicher / Strom",
        "en": "Night-storage / electric"
      },
      {
        "id": "unbekannt",
        "de": "Weiß ich nicht",
        "en": "Don’t know"
      }
    ],
    "nutzung": [
      {
        "id": "selbst",
        "de": "Selbst einziehen",
        "en": "Live in it myself"
      },
      {
        "id": "vermieten",
        "de": "Vermieten",
        "en": "Let it out"
      },
      {
        "id": "vermietet_selbst",
        "de": "Ist vermietet – ich will später selbst einziehen",
        "en": "It is let – I want to move in later"
      }
    ],
    "region": [
      {
        "id": "west",
        "de": "Berlin (West)",
        "en": "Berlin (former West)"
      },
      {
        "id": "ost",
        "de": "Berlin (Ost)",
        "en": "Berlin (former East)"
      },
      {
        "id": "brandenburg",
        "de": "Brandenburg",
        "en": "Brandenburg"
      },
      {
        "id": "unbekannt",
        "de": "Weiß ich nicht",
        "en": "Don’t know"
      }
    ],
    "schalter": {
      "fertighaus": {
        "objekt": "efh",
        "de": "Fertighaus / Holztafelbau",
        "en": "Prefabricated / timber-frame house"
      },
      "mfh6": {
        "objekt": "etw",
        "de": "Haus mit 6 oder mehr Wohnungen",
        "en": "Building with 6 or more flats"
      },
      "milieuschutz": {
        "objekt": "etw",
        "de": "Lage im Milieuschutzgebiet (soziales Erhaltungsgebiet)",
        "en": "In a social preservation area (Milieuschutz)"
      }
    },
    "preis_schalter": {
      "maisonette": {
        "objekt": "etw",
        "de": "Maisonette oder Dachgeschoss",
        "en": "Maisonette or attic flat"
      },
      "vollkeller": {
        "objekt": "efh",
        "de": "Voll unterkellert",
        "en": "Full basement"
      },
      "einlieger": {
        "objekt": "efh",
        "de": "Mit Einliegerwohnung",
        "en": "With a granny flat (Einliegerwohnung)"
      }
    }
  },
  "regeln": [
    {
      "id": "daemmpflicht_efh",
      "kategorie": "pflicht",
      "objekt": "efh",
      "bis": 2001,
      "empfiehlt": [],
      "de": {
        "titel": "Dämmpflicht nach dem Kauf",
        "text": "Erfüllt die Decke zum unbeheizten Dachboden den Mindestwärmeschutz nicht und ist das Dach ungedämmt, muss sie gedämmt werden (U ≤ 0,24) – binnen 2 Jahren nach dem Kauf, wenn der Verkäufer seit 2002 selbst darin wohnte, sonst sofort. Gleiches gilt für offene Heizungsrohre in unbeheizten Räumen. Wir prüfen beides."
      },
      "en": {
        "titel": "Insulation duty after purchase",
        "text": "If the floor to the unheated loft lacks minimum insulation and the roof is uninsulated, it must be insulated (U ≤ 0.24) – within 2 years of purchase if the seller had lived there since 2002, otherwise immediately. The same applies to exposed heating pipes in unheated rooms. We check both."
      },
      "quelle": {
        "titel": "§§ 35, 69 GModG (vormals §§ 47, 69 GEG)",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "daemmpflicht_etw",
      "kategorie": "pflicht",
      "objekt": "etw",
      "bis": 1994,
      "empfiehlt": [],
      "de": {
        "titel": "Dämmpflicht der Gemeinschaft",
        "text": "Im Mehrfamilienhaus muss eine ungedämmte oberste Geschossdecke gedämmt sein – das ist Sache der Eigentümergemeinschaft. Ist das offen, kommt ein Kostenanteil auf Sie zu."
      },
      "en": {
        "titel": "Insulation duty of the association",
        "text": "In a block of flats, an uninsulated top floor slab must be insulated – this is the owners’ association’s job. If it is still open, you will pay a share."
      },
      "quelle": {
        "titel": "§ 35 GModG",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "heizung_fossil",
      "kategorie": "pflicht",
      "objekt": "beide",
      "heizung": ["gas", "gasetage", "oel"],
      "empfiehlt": [],
      "de": {
        "titel": "Gas oder Öl: kein Austauschzwang",
        "text": "Vorhandene Heizungen dürfen weiterlaufen; die frühere Austauschpflicht für alte Kessel ist entfallen. Wer nach dem 29.07.2026 eine neue Gas- oder Ölheizung einbaut, braucht ab 2029 einen Anteil aus Biomethan, Bioöl oder Wasserstoff: 10 % (2029), 15 % (2030), 30 % (2035), 60 % (2040). Solarthermie oder eine Wärmepumpen-Hybridheizung zählen mit."
      },
      "en": {
        "titel": "Gas or oil: no forced replacement",
        "text": "Existing heating may keep running; the former duty to replace old boilers has gone. Anyone installing a new gas or oil heating after 29 July 2026 needs a share of biomethane, bio-oil or hydrogen from 2029: 10% (2029), 15% (2030), 30% (2035), 60% (2040). Solar thermal or a hybrid heat pump count towards it."
      },
      "quelle": {
        "titel": "§ 43 GModG, Stand Oktober 2026",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "gasetage",
      "kategorie": "pruefen",
      "objekt": "etw",
      "heizung": ["gasetage"],
      "empfiehlt": [],
      "de": {
        "titel": "Gasetagenheizung",
        "text": "Die früheren Sonderfristen für Eigentümergemeinschaften mit Gasetagenheizungen sind entfallen. Wir klären Alter, Abgasanlage und ob die Therme zu Ihrem Sondereigentum gehört."
      },
      "en": {
        "titel": "Gas boiler in the flat",
        "text": "The former special deadlines for owners’ associations with per-flat gas boilers no longer apply. We check age, flue and whether the boiler is part of your unit."
      },
      "quelle": {
        "titel": "GModG, §§ 71l, 71n aufgehoben",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "heizungspruefung",
      "kategorie": "pflicht",
      "objekt": "etw",
      "heizung": ["gas", "oel", "fernwaerme", "unbekannt"],
      "mfh6": true,
      "empfiehlt": [],
      "de": {
        "titel": "Heizungsprüfung bis 30.09.2027",
        "text": "In Häusern ab 6 Wohnungen muss eine wasserführende Heizung mit Einbau vor Oktober 2009 bis 30.09.2027 geprüft und optimiert werden – Pflicht der Gemeinschaft. Wir sehen nach, ob es dazu einen Beschluss gibt."
      },
      "en": {
        "titel": "Heating check by 30 Sept 2027",
        "text": "In buildings with 6 or more flats, water-based heating installed before October 2009 must be checked and optimised by 30 Sept 2027 – the association’s duty. We look for a resolution on it."
      },
      "quelle": {
        "titel": "§ 60b GModG",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "heizkosten_fern",
      "kategorie": "pflicht",
      "objekt": "etw",
      "heizung": ["gas", "oel", "fernwaerme", "unbekannt"],
      "empfiehlt": [],
      "de": {
        "titel": "Fernablesbare Zähler bis 31.12.2026",
        "text": "Heizkostenverteiler und Wasserzähler müssen bis Ende 2026 fernablesbar sein. Sonst dürfen Mieter die Heizkosten um 3 % kürzen."
      },
      "en": {
        "titel": "Remote-read meters by 31 Dec 2026",
        "text": "Heat-cost allocators and water meters must be remotely readable by the end of 2026. Otherwise tenants may cut their heating costs by 3%."
      },
      "quelle": {
        "titel": "§§ 5, 12 HeizkostenV",
        "url": "https://www.gesetze-im-internet.de/heizkostenv/__5.html"
      }
    },
    {
      "id": "blei",
      "kategorie": "pflicht",
      "objekt": "beide",
      "bis": 1973,
      "empfiehlt": [],
      "de": {
        "titel": "Bleileitungen möglich",
        "text": "Bis in die 1970er wurden Trinkwasserleitungen aus Blei verlegt. Die Frist zum Entfernen oder Stilllegen ist am 12.01.2026 abgelaufen; noch vorhandene Leitungen müssen sofort ersetzt werden, außer das Gesundheitsamt hat die Frist verlängert. Wir prüfen sichtbare Leitungen; Gewissheit gibt eine Wasseranalyse."
      },
      "en": {
        "titel": "Lead pipes possible",
        "text": "Lead water pipes were installed until the 1970s. The deadline for removing or disconnecting them passed on 12 Jan 2026; remaining pipes must be replaced immediately unless the health authority has extended the deadline. We inspect visible pipes; a water analysis gives certainty."
      },
      "quelle": {
        "titel": "§ 17 TrinkwV",
        "url": "https://www.gesetze-im-internet.de/trinkwv_2023/__17.html"
      }
    },
    {
      "id": "kaminofen",
      "kategorie": "pflicht",
      "objekt": "beide",
      "heizung": ["holz"],
      "empfiehlt": [],
      "de": {
        "titel": "Kamin- oder Kachelofen",
        "text": "Kamin- oder Kachelofen, errichtet vor dem 22.03.2010: ohne Nachweis der Grenzwerte seit 2025 nicht mehr zulässig – außer z. B. Grundofen, offener Kamin oder Ofen als einzige Heizung. Bitte die Bescheinigung des Schornsteinfegers anfordern."
      },
      "en": {
        "titel": "Wood or tiled stove",
        "text": "Wood or tiled stove installed before 22 March 2010: without proof of emission limits no longer permitted since 2025 – except e.g. masonry heaters, open fireplaces or a stove that is the only heating. Please ask for the chimney sweep’s certificate."
      },
      "quelle": {
        "titel": "§ 26 1. BImSchV",
        "url": "https://www.gesetze-im-internet.de/bimschv_1_2010/__26.html"
      }
    },
    {
      "id": "oeltank",
      "kategorie": "pflicht",
      "objekt": "efh",
      "heizung": ["oel"],
      "empfiehlt": [],
      "de": {
        "titel": "Öltank",
        "text": "Mit dem Kauf werden Sie Betreiber des Tanks; je nach Größe und Lage sind Sachverständigenprüfungen Pflicht. Letzten Prüfbericht anfordern – eine spätere Stilllegung kostet Geld."
      },
      "en": {
        "titel": "Oil tank",
        "text": "With the purchase you become the tank operator; depending on size and location, expert inspections are mandatory. Ask for the last inspection report – decommissioning later costs money."
      },
      "quelle": {
        "titel": "§ 46 AwSV",
        "url": "https://www.gesetze-im-internet.de/awsv/__46.html"
      }
    },
    {
      "id": "nachtspeicher",
      "kategorie": "pruefen",
      "objekt": "beide",
      "bis": 1984,
      "heizung": ["nachtspeicher"],
      "empfiehlt": [],
      "de": {
        "titel": "Nachtspeicheröfen",
        "text": "Geräte aus der Zeit bis etwa 1984 können Asbest enthalten. Nicht öffnen; der Ausbau gehört in die Hand einer Fachfirma. Der Tausch gegen eine Wärmepumpe wird gefördert."
      },
      "en": {
        "titel": "Night-storage heaters",
        "text": "Units from before about 1984 may contain asbestos. Do not open them; removal is a job for a specialist firm. Replacing them with a heat pump is subsidised."
      },
      "quelle": {
        "titel": "Berliner Mieterverein, MieterMagazin 06/2011",
        "url": "https://www.berliner-mieterverein.de/magazin/online/mm1106/110628.htm"
      }
    },
    {
      "id": "fernwaerme",
      "kategorie": "pruefen",
      "objekt": "beide",
      "heizung": ["fernwaerme"],
      "empfiehlt": [],
      "de": {
        "titel": "Fernwärme",
        "text": "Wir sehen uns Übergabestation und Alter an; Liefervertrag und Preisklausel bitte mitschicken. Der Berliner Wärmeplan zeigt Netzgebiete, schreibt aber nichts vor."
      },
      "en": {
        "titel": "District heating",
        "text": "We look at the substation and its age; please send the supply contract and price clause. Berlin’s heat plan shows network areas but imposes no obligations."
      },
      "quelle": {
        "titel": "Berliner Wärmeplan (Senat, 16.06.2026)",
        "url": "https://www.berlin.de/sen/uvk/klimaschutz/waermewende/waermeplan/"
      }
    },
    {
      "id": "waermepumpe",
      "kategorie": "pruefen",
      "objekt": "beide",
      "heizung": ["waermepumpe"],
      "empfiehlt": [],
      "de": {
        "titel": "Wärmepumpe",
        "text": "Wir prüfen Typ, Alter, Vorlauftemperatur und Wartung. Wichtig für die Kosten ist die Jahresarbeitszahl – Stromabrechnungen bitte mitschicken."
      },
      "en": {
        "titel": "Heat pump",
        "text": "We check type, age, flow temperature and maintenance. What matters for running costs is the seasonal performance factor – please send the electricity bills."
      },
      "quelle": {
        "titel": "GModG § 60a",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "gruenderzeit",
      "kategorie": "pruefen",
      "objekt": "beide",
      "bis": 1918,
      "empfiehlt": [],
      "de": {
        "titel": "Altbau bis 1918",
        "text": "Holzbalkendecken mit verdeckten Balkenköpfen in Außenwänden und unter Bädern können faulen; auch Echter Hausschwamm ist möglich. Im Keller fehlt oft eine Horizontalsperre. Darauf achten wir gezielt."
      },
      "en": {
        "titel": "Period building up to 1918",
        "text": "Timber-beam floors with hidden beam ends in external walls and under bathrooms can rot; dry rot is possible too. Basements often lack a damp-proof course. We look for this specifically."
      },
      "quelle": {
        "titel": "Fachliteratur: Stahr, Bausanierung (2022); DIN 68800-4",
        "url": ""
      }
    },
    {
      "id": "zwischenkrieg",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1919,
      "bis": 1948,
      "empfiehlt": [],
      "de": {
        "titel": "Bauzeit 1919–1948",
        "text": "Kaum Wärmeschutz, oft noch Holzbalkendecken. Rechnen Sie mit höheren Heizkosten und Schimmelrisiko an kalten Ecken."
      },
      "en": {
        "titel": "Built 1919–1948",
        "text": "Hardly any insulation, often timber-beam floors. Expect higher heating costs and a mould risk at cold corners."
      },
      "quelle": {
        "titel": "Fachliteratur: Stahr, Bausanierung (2022)",
        "url": ""
      }
    },
    {
      "id": "nachkrieg",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1945,
      "bis": 1965,
      "empfiehlt": [],
      "de": {
        "titel": "Nachkriegsbau",
        "text": "Teils Trümmerziegel oder Ziegelsplittbeton mit schwankender Festigkeit. Vor Wanddurchbrüchen oder einem Ausbau die Tragfähigkeit prüfen lassen."
      },
      "en": {
        "titel": "Post-war building",
        "text": "Partly rubble bricks or brick-aggregate concrete with variable strength. Have the load capacity checked before opening walls or extending."
      },
      "quelle": {
        "titel": "Deutscher Bundestag, Drucksache 11/179",
        "url": "https://dserver.bundestag.de/btd/11/001/1100179.pdf"
      }
    },
    {
      "id": "asbest",
      "kategorie": "pruefen",
      "objekt": "beide",
      "bis": 1993,
      "empfiehlt": ["schadstoff"],
      "de": {
        "titel": "Asbest möglich",
        "text": "Bis 1993 (vereinzelt noch kurz danach) wurde Asbest verbaut, z. B. in Fliesenkleber, Spachtel, Floor-Flex-Platten, Dach- und Fassadenplatten. Intakt meist unkritisch – wichtig wird es beim Umbau. Dann müssen Sie der Firma das Baujahr und bekannte Hinweise auf Schadstoffe geben (Pflicht)."
      },
      "en": {
        "titel": "Asbestos possible",
        "text": "Asbestos was used until 1993 (occasionally slightly later), e.g. in tile adhesive, filler, vinyl floor tiles, roof and façade panels. Usually harmless when intact – it matters when you renovate. You must then give the contractor the year of construction and any known indications of pollutants (legal duty)."
      },
      "quelle": {
        "titel": "Verbraucherzentrale; § 5a GefStoffV",
        "url": "https://www.verbraucherzentrale.de/wissen/umwelt-haushalt/wohnen/asbest-gefaehrlich-und-immer-noch-aktuell-48383"
      }
    },
    {
      "id": "pcb_pak",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1950,
      "bis": 1978,
      "empfiehlt": ["schadstoff"],
      "de": {
        "titel": "PCB und PAK möglich",
        "text": "Dauerelastische Fugen können PCB enthalten, schwarzer Parkettkleber und Teerpappe PAK. Altparkett nicht abschleifen, bevor der Kleber geprüft ist."
      },
      "en": {
        "titel": "PCBs and PAHs possible",
        "text": "Flexible joint sealants may contain PCBs; black parquet adhesive and tar felt may contain PAHs. Do not sand old parquet before the adhesive has been tested."
      },
      "quelle": {
        "titel": "Fachliteratur: Kaub, Schadstoffe im Bauwesen (2024)",
        "url": ""
      }
    },
    {
      "id": "mineralwolle",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1930,
      "bis": 2000,
      "empfiehlt": [],
      "de": {
        "titel": "Alte Mineralwolle",
        "text": "Dämmwolle, die vor 1996 eingebaut wurde, gilt als krebserzeugend; bis 2000 kann noch alte Ware verbaut worden sein. Nicht selbst ausbauen – nur durch einen Fachbetrieb mit Schutzmaßnahmen."
      },
      "en": {
        "titel": "Old mineral wool",
        "text": "Insulation wool installed before 1996 is classed as carcinogenic; old material may still have been used until 2000. Do not remove it yourself – only via a specialist firm with protective measures."
      },
      "quelle": {
        "titel": "TRGS 521 (Ausgabe Mai 2026)",
        "url": "https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS-521.html"
      }
    },
    {
      "id": "elektro_alt",
      "kategorie": "pruefen",
      "objekt": "beide",
      "bis": 1972,
      "empfiehlt": [],
      "de": {
        "titel": "Alte Elektroanlage",
        "text": "Anlagen von vor 1973 haben oft keinen Schutzleiter. Bestandsschutz heißt nicht sicher – ein Elektro-Check durch einen Fachbetrieb ist ratsam."
      },
      "en": {
        "titel": "Old electrical installation",
        "text": "Installations from before 1973 often lack an earth conductor. Grandfathered does not mean safe – a check by an electrician is advisable."
      },
      "quelle": {
        "titel": "ZVEI, Elektro-Altanlagen (2020)",
        "url": ""
      }
    },
    {
      "id": "elektro_35",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1973,
      "bis": 1991,
      "empfiehlt": [],
      "de": {
        "titel": "Elektroanlage über 35 Jahre",
        "text": "Leitungen und Klemmen gelten nach etwa 35 Jahren als verbraucht; ein FI-Schutzschalter fehlt oft. Prüfung durch einen Fachbetrieb empfohlen."
      },
      "en": {
        "titel": "Wiring over 35 years old",
        "text": "Wiring and terminals are regarded as worn after about 35 years; a residual-current device is often missing. A check by an electrician is recommended."
      },
      "quelle": {
        "titel": "ZVEI, Elektro-Altanlagen (2020)",
        "url": ""
      }
    },
    {
      "id": "ddr",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1949,
      "bis": 1990,
      "region": ["ost", "brandenburg"],
      "empfiehlt": [],
      "de": {
        "titel": "DDR-Bauzeit",
        "text": "Möglich sind Aluminiumleitungen (Brandrisiko an Klemmen), Asbestzement und Sokalit-Platten sowie mit Hylotox behandelte Dachstühle. Wir achten darauf; Klarheit bringt nur eine Analyse."
      },
      "en": {
        "titel": "GDR-era building",
        "text": "Possible are aluminium wiring (fire risk at terminals), asbestos cement and Sokalit boards, and roof timbers treated with Hylotox. We look out for these; only an analysis gives certainty."
      },
      "quelle": {
        "titel": "Umweltbundesamt, Asbest in der DDR; WD Bundestag 2002",
        "url": ""
      }
    },
    {
      "id": "fertighaus",
      "kategorie": "pruefen",
      "objekt": "efh",
      "von": 1956,
      "bis": 1991,
      "fertighaus": true,
      "empfiehlt": [],
      "de": {
        "titel": "Fertighaus dieser Zeit",
        "text": "Holzschutzmittel (PCP, Lindan), Formaldehyd und muffiger Geruch durch Chloranisole sind möglich. Vor dem Kauf eine Raumluftanalyse erwägen – auf Wunsch organisieren wir sie über ein Partnerlabor."
      },
      "en": {
        "titel": "Prefab house of this era",
        "text": "Wood preservatives (PCP, lindane), formaldehyde and a musty smell from chloroanisoles are possible. Consider an indoor-air analysis before buying – we can arrange it via a partner lab."
      },
      "quelle": {
        "titel": "Verbraucherzentrale NRW, Fertighaus aus den 70er-Jahren",
        "url": "https://www.verbraucherzentrale.nrw/schadstoffe/gebaeude/fertighaus-aus-den-70er-jahren-50146"
      }
    },
    {
      "id": "flachdach",
      "kategorie": "pruefen",
      "objekt": "efh",
      "von": 1960,
      "bis": 1990,
      "empfiehlt": [],
      "de": {
        "titel": "Flachdächer dieser Zeit",
        "text": "Abdichtungen halten etwa 30–35 Jahre und sind meist erneuert oder fällig. Nachweise zur letzten Sanierung bitte mitschicken."
      },
      "en": {
        "titel": "Flat roofs of this era",
        "text": "Membranes last about 30–35 years and have usually been renewed or are due. Please send records of the last renewal."
      },
      "quelle": {
        "titel": "BBSR, Nutzungsdauern von Bauteilen (Stand 2025)",
        "url": ""
      }
    },
    {
      "id": "strang",
      "kategorie": "pruefen",
      "objekt": "etw",
      "von": 1950,
      "bis": 1980,
      "empfiehlt": [],
      "de": {
        "titel": "Leitungsstränge",
        "text": "Wasser- und Abwasserstränge stammen oft noch aus der Bauzeit. Eine Strangsanierung ist häufig der größte Einzelposten der Gemeinschaft – wir suchen in den Protokollen danach."
      },
      "en": {
        "titel": "Riser pipes",
        "text": "Water and waste risers are often original. Riser replacement is frequently the association’s largest single cost – we look for it in the minutes."
      },
      "quelle": {
        "titel": "Fachliteratur; § 5 Abs. 2 WEG",
        "url": ""
      }
    },
    {
      "id": "balkone",
      "kategorie": "pruefen",
      "objekt": "etw",
      "von": 1950,
      "bis": 1995,
      "empfiehlt": [],
      "de": {
        "titel": "Betonbalkone",
        "text": "Auskragende Balkone ohne Wärmetrennung zeigen oft Rost und Abplatzungen. Eine Sanierung je Balkon ist schnell fünfstellig; wer zahlt, regelt die Teilungserklärung."
      },
      "en": {
        "titel": "Concrete balconies",
        "text": "Cantilevered balconies without thermal breaks often show rust and spalling. Repair can easily reach five figures per balcony; the declaration of division says who pays."
      },
      "quelle": {
        "titel": "Fachliteratur: Stahr, Bausanierung (2022)",
        "url": ""
      }
    },
    {
      "id": "platte",
      "kategorie": "pruefen",
      "objekt": "etw",
      "von": 1965,
      "bis": 1990,
      "region": ["ost"],
      "empfiehlt": [],
      "de": {
        "titel": "Plattenbau",
        "text": "Fugen, Balkonplatten und Außenwände prüfen wir gezielt. Viele Sanierungen der 1990er (Dämmung, Fenster, Stränge) stehen vor dem zweiten Zyklus – das kann Sonderumlagen bedeuten."
      },
      "en": {
        "titel": "Prefabricated concrete block",
        "text": "We check joints, balcony slabs and external walls specifically. Many 1990s renovations (insulation, windows, risers) are approaching their second cycle – this can mean special levies."
      },
      "quelle": {
        "titel": "BBSR, Nutzungsdauern von Bauteilen (Stand 2025)",
        "url": ""
      }
    },
    {
      "id": "erneuerung",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 1995,
      "bis": 2009,
      "empfiehlt": [],
      "de": {
        "titel": "Erste Erneuerungen fällig",
        "text": "Heizkessel (ca. 18–20 Jahre), Fensterdichtungen und Fugen sind in diesem Alter oft fällig. Wartungs- und Austauschbelege bitte mitschicken."
      },
      "en": {
        "titel": "First renewals due",
        "text": "Boilers (approx. 18–20 years), window seals and joints are often due at this age. Please send maintenance and replacement records."
      },
      "quelle": {
        "titel": "BBSR, Nutzungsdauern von Bauteilen (Stand 2025)",
        "url": ""
      }
    },
    {
      "id": "neubau",
      "kategorie": "pruefen",
      "objekt": "beide",
      "von": 2010,
      "empfiehlt": [],
      "de": {
        "titel": "Jüngerer Bau",
        "text": "Häufig sind Abdichtungsmängel an Duschen, Balkonen und Flachdächern. Mängelansprüche verjähren meist 5 Jahre nach der Abnahme – Abnahmeprotokolle und Mängellisten bitte mitschicken."
      },
      "en": {
        "titel": "Recent building",
        "text": "Waterproofing defects in showers, balconies and flat roofs are common. Defect claims usually expire 5 years after acceptance – please send acceptance records and defect lists."
      },
      "quelle": {
        "titel": "§ 634a BGB",
        "url": "https://www.gesetze-im-internet.de/bgb/__634a.html"
      }
    },
    {
      "id": "schimmel",
      "kategorie": "pruefen",
      "objekt": "beide",
      "bis": 2000,
      "empfiehlt": [],
      "de": {
        "titel": "Wärmebrücken und Schimmel",
        "text": "Vor 2001 gab es keine einheitlichen Anforderungen an Wärmebrücken. Schimmel droht an Ecken, Laibungen und hinter Möbeln, besonders nach einem Fenstertausch. Wir messen an kritischen Stellen."
      },
      "en": {
        "titel": "Thermal bridges and mould",
        "text": "Before 2001 there were no uniform requirements for thermal bridges. Mould can form at corners, reveals and behind furniture, especially after new windows. We take readings at critical points."
      },
      "quelle": {
        "titel": "UBA-Schimmelleitfaden (2017, präzisiert 2024)",
        "url": "https://www.umweltbundesamt.de/themen/gesundheit/umwelteinfluesse-auf-den-menschen/schimmel/aktueller-uba-schimmelleitfaden"
      }
    },
    {
      "id": "mietspiegel",
      "kategorie": "miete",
      "objekt": "etw",
      "bis": 2024,
      "nutzung": ["vermieten"],
      "empfiehlt": ["vermietung"],
      "de": {
        "titel": "Was Ausstattung an Miete bringt",
        "text": "Laut Orientierungshilfe zum Berliner Mietspiegel 2026 verschiebt jede Merkmalgruppe die Miete um 20 % des Abstands zwischen Mittel- und Ober- bzw. Unterwert. Beispiel 57 m² Altbau in Neukölln: Wird die Gruppe „Gebäude“ positiv, etwa durch eine Video-Gegensprechanlage, und gleichen sich die übrigen aus, sind rund 40–47 € mehr im Monat möglich."
      },
      "en": {
        "titel": "What fittings add to the rent",
        "text": "According to the guidance for Berlin’s 2026 rent index, each feature group shifts the rent by 20% of the gap between the mean and the upper (or lower) value. Example 57 m² period flat in Neukölln: if the “building” group turns positive, e.g. via a video intercom, and the other groups balance out, about €40–47 more per month is possible."
      },
      "quelle": {
        "titel": "Berliner Mietspiegel 2026, Orientierungshilfe",
        "url": "https://mietspiegel.berlin.de/"
      }
    },
    {
      "id": "mietspiegel_neu",
      "kategorie": "miete",
      "objekt": "etw",
      "von": 2025,
      "nutzung": ["vermieten"],
      "empfiehlt": [],
      "de": {
        "titel": "Neubau ab 2025",
        "text": "Für Wohnungen, die ab 2025 bezugsfertig wurden, gilt der Mietspiegel 2026 nicht. Die Vergleichsmiete lässt sich nur über Vergleichswohnungen oder ein Gutachten bestimmen."
      },
      "en": {
        "titel": "New build from 2025",
        "text": "The 2026 rent index does not apply to flats completed from 2025. The comparative rent can only be determined via comparable flats or an expert opinion."
      },
      "quelle": {
        "titel": "Berliner Mietspiegel 2026, Nr. 3",
        "url": "https://mietspiegel.berlin.de/"
      }
    },
    {
      "id": "mietpreisbremse",
      "kategorie": "miete",
      "objekt": "beide",
      "nutzung": ["vermieten"],
      "empfiehlt": [],
      "de": {
        "titel": "Mietpreisbremse bis 2029",
        "text": "Bei Neuvermietung höchstens 10 % über der Vergleichsmiete (Berlin, bis 31.12.2029); Mieterhöhungen höchstens 15 % in 3 Jahren. Ausnahme: Erstvermietung nach dem 01.10.2014. Rechtliche Details klärt ein Mieterverein oder Anwalt."
      },
      "en": {
        "titel": "Rent brake until 2029",
        "text": "On re-letting, at most 10% above the comparative rent (Berlin, until 31 Dec 2029); rent increases at most 15% in 3 years. Exception: first letting after 1 Oct 2014. Legal details: ask a landlord association or lawyer."
      },
      "quelle": {
        "titel": "§§ 556d ff., 558 BGB; Berliner Verordnungen",
        "url": "https://www.gesetze-im-internet.de/bgb/__556d.html"
      }
    },
    {
      "id": "flaeche",
      "kategorie": "miete",
      "objekt": "beide",
      "nutzung": ["vermieten", "vermietet_selbst"],
      "empfiehlt": [],
      "de": {
        "titel": "Wohnfläche nachmessen",
        "text": "Ist die Fläche mehr als 10 % kleiner als im Mietvertrag, ist die Miete gemindert. Wir plausibilisieren die angegebene Fläche."
      },
      "en": {
        "titel": "Check the living area",
        "text": "If the area is more than 10% smaller than in the tenancy agreement, the rent is reduced. We check the stated area for plausibility."
      },
      "quelle": {
        "titel": "BGH, VIII ZR 295/03",
        "url": ""
      }
    },
    {
      "id": "milieuschutz",
      "kategorie": "miete",
      "objekt": "etw",
      "milieuschutz": true,
      "empfiehlt": [],
      "de": {
        "titel": "Milieuschutzgebiet",
        "text": "Modernisierungen brauchen hier eine Genehmigung. Video-Gegensprechanlage, Fußbodenheizung oder ein zweites Bad sind meist nicht genehmigungsfähig – das begrenzt Aufwertung und Mietpotenzial."
      },
      "en": {
        "titel": "Social preservation area",
        "text": "Upgrades need a permit here. Video intercom, underfloor heating or a second bathroom are usually not permitted – this limits upgrades and rental potential."
      },
      "quelle": {
        "titel": "Berliner Genehmigungskriterien soziale Erhaltungsgebiete (2026)",
        "url": "https://www.berlin.de/ba-neukoelln/politik-und-verwaltung/aemter/stadtentwicklungsamt/stadtplanung/soziale-erhaltungsverordnung/"
      }
    },
    {
      "id": "sperrfrist",
      "kategorie": "miete",
      "objekt": "etw",
      "nutzung": ["vermietet_selbst"],
      "empfiehlt": [],
      "de": {
        "titel": "Eigenbedarf kann gesperrt sein",
        "text": "Wurde die Wohnung erst nach Mietbeginn in Eigentum umgewandelt, ist eine Eigenbedarfskündigung in Berlin 10 Jahre gesperrt. Kauf bricht nicht Miete. Bitte vor dem Notartermin rechtlich prüfen lassen."
      },
      "en": {
        "titel": "Own-use notice may be barred",
        "text": "If the flat was converted into a condominium after the tenancy began, an own-use notice is barred for 10 years in Berlin. A sale does not end a tenancy. Have this checked legally before the notary appointment."
      },
      "quelle": {
        "titel": "§ 577a BGB; Berliner Kündigungsschutzklausel-Verordnung",
        "url": "https://www.gesetze-im-internet.de/bgb/__577a.html"
      }
    },
    {
      "id": "vermieterpflichten",
      "kategorie": "miete",
      "objekt": "beide",
      "nutzung": ["vermieten"],
      "empfiehlt": [],
      "de": {
        "titel": "Pflichten als Vermieter",
        "text": "Energieausweis bei der Besichtigung vorlegen, CO2-Kosten nach Stufenmodell aufteilen, Rauchwarnmelder in Aufenthaltsräumen und Fluren. Bei neuer Gas- oder Ölheizung tragen Sie ab 2028 zusätzlich Kosten anteilig."
      },
      "en": {
        "titel": "Duties as a landlord",
        "text": "Show the energy certificate at viewings, split CO2 costs by the tiered model, smoke alarms in living rooms and hallways. With a new gas or oil heating you will also share costs from 2028."
      },
      "quelle": {
        "titel": "§ 80 GModG; CO2KostAufG; § 48 BauO Bln",
        "url": "https://www.gesetze-im-internet.de/co2kostaufg/"
      }
    },
    {
      "id": "beratung_ea",
      "kategorie": "foerderung",
      "objekt": "efh",
      "empfiehlt": [],
      "de": {
        "titel": "Beratung zum Energieausweis",
        "text": "Beim Kauf eines Hauses mit höchstens 2 Wohnungen müssen Sie bis Ende 2026 ein kostenloses Beratungsgespräch zum Energieausweis führen, wenn es angeboten wird."
      },
      "en": {
        "titel": "Energy-certificate consultation",
        "text": "When buying a house with at most 2 dwellings, until the end of 2026 you must hold a free consultation on the energy certificate if one is offered."
      },
      "quelle": {
        "titel": "§ 80 Abs. 4 GModG",
        "url": "https://www.gesetze-im-internet.de/geg/"
      }
    },
    {
      "id": "kfw308",
      "kategorie": "foerderung",
      "objekt": "beide",
      "bis": 1994,
      "empfiehlt": [],
      "de": {
        "titel": "Förderkredit „Jung kauft Alt“",
        "text": "Familien mit Kind unter 18 und Einkommen bis 90.000 € (plus 10.000 € je weiteres Kind) bekommen für Häuser und Wohnungen der Energieklassen F, G oder H einen zinsverbilligten KfW-Kredit, wenn sie binnen 4,5 Jahren sanieren. Wichtig: Antrag vor dem Kaufvertrag."
      },
      "en": {
        "titel": "“Jung kauft Alt” loan",
        "text": "Families with a child under 18 and income up to €90,000 (plus €10,000 per further child) can get a reduced-interest KfW loan for houses and flats in energy classes F, G or H if they renovate within 4.5 years. Important: apply before the purchase contract."
      },
      "quelle": {
        "titel": "KfW-Programm 308 (Wohneigentum für Familien – Bestandserwerb)",
        "url": "https://www.kfw.de/308"
      }
    },
    {
      "id": "heizungsfoerderung",
      "kategorie": "foerderung",
      "objekt": "beide",
      "heizung": ["oel", "gasetage", "nachtspeicher", "gas"],
      "empfiehlt": [],
      "de": {
        "titel": "Heizungstausch: Bonus befristet",
        "text": "Wer selbst einzieht und die Heizung tauscht, bekommt Zuschüsse. Der Bonus von 16 % gilt nur bei Antrag bis 31.01.2027 und sinkt danach schrittweise; dazu kann ein Einkommensbonus kommen."
      },
      "en": {
        "titel": "Heating replacement: bonus limited",
        "text": "Owner-occupiers replacing their heating receive grants. The 16% bonus applies only to applications by 31 Jan 2027 and then decreases step by step; an income-related bonus may be added."
      },
      "quelle": {
        "titel": "BEG Einzelmaßnahmen (Richtlinie vom 17.08.2026, gültig seit 21.07.2026)",
        "url": ""
      }
    },
    {
      "id": "solarpflicht",
      "kategorie": "foerderung",
      "objekt": "efh",
      "bis": 1995,
      "region": ["west", "ost"],
      "empfiehlt": [],
      "de": {
        "titel": "Dach sanieren in Berlin",
        "text": "Wer in Berlin das Dach grundlegend saniert, muss eine Photovoltaikanlage installieren (Solargesetz Berlin). Bei der Kostenplanung berücksichtigen."
      },
      "en": {
        "titel": "Roof renovation in Berlin",
        "text": "Anyone in Berlin who substantially renovates the roof must install a PV system (Berlin Solar Act). Include this in your budget."
      },
      "quelle": {
        "titel": "Solargesetz Berlin",
        "url": "https://www.ihk.de/berlin/service-und-beratung/energie-und-umwelt/energie-und-umweltrecht/energie2/solargesetz-berlin-5314064"
      }
    },
    {
      "id": "thermo_saison",
      "kategorie": "foerderung",
      "objekt": "beide",
      "empfiehlt": [],
      "de": {
        "titel": "Thermografie nur im Winter",
        "text": "Wärmebilder sind nur bei ausreichendem Unterschied zwischen innen und außen aussagekräftig (Faustregel mind. 10 K, keine Sonne) – meist von November bis März, frühmorgens."
      },
      "en": {
        "titel": "Thermal imaging in winter only",
        "text": "Thermal images are only meaningful with a sufficient difference between inside and outside (rule of thumb at least 10 K, no sun) – usually November to March, early morning."
      },
      "quelle": {
        "titel": "DIN EN ISO 6781-1 (2023)",
        "url": ""
      }
    },
    {
      "id": "rauchmelder",
      "kategorie": "pflicht",
      "objekt": "beide",
      "region": ["west", "ost"],
      "empfiehlt": [],
      "de": {
        "titel": "Rauchwarnmelder",
        "text": "In Berlin sind Rauchwarnmelder in Aufenthaltsräumen (außer Küche) und Fluren Pflicht, auch im Bestand."
      },
      "en": {
        "titel": "Smoke alarms",
        "text": "In Berlin, smoke alarms are required in living rooms and bedrooms (not kitchens) and hallways, including existing homes."
      },
      "quelle": {
        "titel": "§ 48 Abs. 4 BauO Bln",
        "url": ""
      }
    }
  ],
  "unterlagen": {
    "etw": [
      {
        "id": "expose",
        "prio": 1,
        "de": "Exposé, bemaßter Grundriss und Wohnflächenberechnung",
        "en": "Property listing (exposé), dimensioned floor plan and living-area calculation",
        "wo_de": "Makler, Verkäufer",
        "wo_en": "Agent, seller"
      },
      {
        "id": "ea",
        "prio": 1,
        "de": "Energieausweis des Gebäudes",
        "en": "Energy performance certificate (Energieausweis) of the building",
        "wo_de": "Makler (Pflichtvorlage)",
        "wo_en": "Agent (must be shown)"
      },
      {
        "id": "teilung",
        "prio": 1,
        "de": "Teilungserklärung mit Gemeinschaftsordnung, Aufteilungsplan und Nachträgen",
        "en": "Declaration of division (Teilungserklärung) with community rules, division plan and amendments",
        "wo_de": "Verkäufer, Notar",
        "wo_en": "Seller, notary"
      },
      {
        "id": "protokolle",
        "prio": 1,
        "de": "Protokolle der letzten 3 Eigentümerversammlungen und Beschluss-Sammlung",
        "en": "Minutes of the last 3 owners’ meetings and register of resolutions (Beschluss-Sammlung)",
        "wo_de": "Verwalter, mit Ermächtigung des Verkäufers",
        "wo_en": "Property manager, with the seller’s authorisation"
      },
      {
        "id": "finanzen",
        "prio": 1,
        "de": "Wirtschaftsplan, Jahresabrechnungen (3 Jahre) und Vermögensbericht mit Stand der Erhaltungsrücklage",
        "en": "Budget, annual accounts (3 years) and financial report incl. maintenance reserve (Erhaltungsrücklage)",
        "wo_de": "Verwalter, Verkäufer",
        "wo_en": "Property manager, seller"
      },
      {
        "id": "grundbuch",
        "prio": 1,
        "de": "Aktueller Auszug aus dem Wohnungsgrundbuch",
        "en": "Current extract from the condominium land register",
        "wo_de": "Notar, Verkäufer",
        "wo_en": "Notary, seller"
      },
      {
        "id": "mietvertrag",
        "prio": 1,
        "nutzung": ["vermieten", "vermietet_selbst"],
        "nur_vermietet": true,
        "de": "Mietvertrag (Namen und Bankdaten geschwärzt), Mieterhöhungen, letzte Betriebs- und Heizkostenabrechnung",
        "en": "Tenancy agreement (names and bank details blacked out), rent increases, last service and heating cost statement",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "verwalterbest",
        "prio": 2,
        "de": "Verwalterbestätigung: Hausgeldrückstände, beschlossene Sonderumlagen, Darlehen der Gemeinschaft",
        "en": "Manager’s confirmation (Verwalterbestätigung): service-charge arrears, resolved special levies, loans of the association",
        "wo_de": "Verwalter",
        "wo_en": "Property manager"
      },
      {
        "id": "pruefberichte",
        "prio": 2,
        "de": "Prüfberichte: Heizung, Aufzug, Legionellen (bei zentralem Warmwasser)",
        "en": "Inspection reports: heating, lift, Legionella (with central hot water)",
        "wo_de": "Verwalter",
        "wo_en": "Property manager"
      },
      {
        "id": "modernisierung",
        "prio": 2,
        "de": "Rechnungen zu Modernisierungen in der Wohnung (mit Jahr)",
        "en": "Invoices for upgrades inside the flat (with year)",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "therme",
        "prio": 2,
        "heizung": ["gasetage"],
        "de": "Gastherme: Wartungsprotokolle und Bescheinigungen des Schornsteinfegers",
        "en": "Gas boiler: maintenance records and chimney sweep certificates",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "blei",
        "prio": 2,
        "bis": 1973,
        "de": "Nachweis, dass keine Bleileitungen mehr vorhanden sind",
        "en": "Proof that no lead pipes remain",
        "wo_de": "Verwalter, Verkäufer",
        "wo_en": "Property manager, seller"
      },
      {
        "id": "gutachten",
        "prio": 3,
        "de": "Gutachten oder Zustandsberichte zum Gemeinschaftseigentum (Dach, Fassade, Balkone, Tiefgarage)",
        "en": "Reports on the common property (roof, façade, balconies, garage)",
        "wo_de": "Verwalter",
        "wo_en": "Property manager"
      },
      {
        "id": "abnahme",
        "prio": 3,
        "von": 2021,
        "de": "Abnahmeprotokolle und Mängellisten (Neubau unter 5 Jahre)",
        "en": "Acceptance records and defect lists (new build under 5 years)",
        "wo_de": "Verwalter, Verkäufer",
        "wo_en": "Property manager, seller"
      }
    ],
    "efh": [
      {
        "id": "expose",
        "prio": 1,
        "de": "Exposé, bemaßte Grundrisse und Schnitte, Wohnflächenberechnung",
        "en": "Property listing (exposé), dimensioned floor plans and sections, living-area calculation",
        "wo_de": "Makler, Verkäufer",
        "wo_en": "Agent, seller"
      },
      {
        "id": "ea",
        "prio": 1,
        "de": "Energieausweis",
        "en": "Energy performance certificate (Energieausweis)",
        "wo_de": "Makler (Pflichtvorlage)",
        "wo_en": "Agent (must be shown)"
      },
      {
        "id": "genehmigung",
        "prio": 1,
        "de": "Baugenehmigung mit genehmigten Plänen, auch für Anbauten, Dachausbau und Garage; Schlussabnahme",
        "en": "Building permit with approved drawings, also for extensions, loft conversion and garage; final acceptance",
        "wo_de": "Verkäufer, sonst Bauaktenarchiv",
        "wo_en": "Seller, otherwise building-file archive"
      },
      {
        "id": "grundbuch",
        "prio": 1,
        "de": "Aktueller Grundbuchauszug (alle Abteilungen)",
        "en": "Current land register extract (all sections)",
        "wo_de": "Notar, Verkäufer",
        "wo_en": "Notary, seller"
      },
      {
        "id": "lageplan",
        "prio": 1,
        "de": "Lageplan bzw. Flurkarte",
        "en": "Site plan or cadastral map",
        "wo_de": "Verkäufer, Vermessungsamt",
        "wo_en": "Seller, surveying office"
      },
      {
        "id": "mietvertrag",
        "prio": 1,
        "nutzung": ["vermieten", "vermietet_selbst"],
        "nur_vermietet": true,
        "de": "Mietverträge (Namen und Bankdaten geschwärzt), falls vermietet",
        "en": "Tenancy agreements (names and bank details blacked out), if let",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "modernisierung",
        "prio": 2,
        "de": "Rechnungen zu Modernisierungen mit Jahr (Dach, Fenster, Heizung, Leitungen, Dämmung, Bäder)",
        "en": "Invoices for upgrades with year (roof, windows, heating, pipes, insulation, bathrooms)",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "heizung",
        "prio": 2,
        "de": "Heizung: Wartungsprotokolle, Feuerstättenbescheid, Schornsteinfeger-Protokolle",
        "en": "Heating: maintenance records, chimney sweep notice and reports",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "verbrauch",
        "prio": 2,
        "de": "Verbrauchsabrechnungen der letzten 3 Jahre (Gas, Öl, Strom, Fernwärme)",
        "en": "Energy bills for the last 3 years (gas, oil, electricity, district heating)",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "versicherung",
        "prio": 2,
        "de": "Wohngebäudeversicherung mit Schadenhistorie",
        "en": "Buildings insurance with claims history",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "abwasser",
        "prio": 2,
        "de": "Abwasser: Kanalanschluss oder Genehmigung und Dichtheitsnachweis der Grube bzw. Kleinkläranlage",
        "en": "Waste water: sewer connection, or permit and tightness test of the cesspit / small treatment plant",
        "wo_de": "Verkäufer, Wasserbehörde",
        "wo_en": "Seller, water authority"
      },
      {
        "id": "oeltank",
        "prio": 2,
        "heizung": ["oel"],
        "de": "Öltank: letzter Prüfbericht",
        "en": "Oil tank: last inspection report",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "blei",
        "prio": 2,
        "bis": 1973,
        "de": "Nachweis, dass keine Bleileitungen mehr vorhanden sind",
        "en": "Proof that no lead pipes remain",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "fertighaus",
        "prio": 2,
        "fertighaus": true,
        "de": "Fertighaus: Hersteller, Haustyp, frühere Raumluftmessungen",
        "en": "Prefab house: manufacturer, model, earlier indoor-air tests",
        "wo_de": "Verkäufer",
        "wo_en": "Seller"
      },
      {
        "id": "behoerden",
        "prio": 3,
        "de": "Auskünfte zu Baulasten, Altlasten und Denkmalschutz",
        "en": "Information on public building encumbrances (Baulasten), contaminated land and listed status",
        "wo_de": "Bezirksamt, mit Vollmacht des Eigentümers",
        "wo_en": "District office, with the owner’s power of attorney"
      }
    ]
  },
  "text": {
    "de": {
      "kopf_unter": "Kaufbegutachtung von Wohnimmobilien · Berlin",
      "titel": "Wissen, was Sie kaufen – bevor Sie zum Notar gehen.",
      "objekt_efh": "Einfamilienhaus",
      "objekt_efh_unter": "auch Doppelhaushälfte und Reihenhaus",
      "objekt_etw": "Eigentumswohnung",
      "objekt_etw_unter": "inklusive WEG-Unterlagen",
      "nutzen": [
        {
          "t": "Mängel erkennen",
          "d": "Feuchte, Dach, Heizung, Schadstoffverdacht – bevor Sie unterschreiben."
        },
        {
          "t": "Kosten kennen",
          "d": "Was in den nächsten 10–15 Jahren auf Sie zukommt, mit Kostenrahmen."
        },
        {
          "t": "Besser verhandeln",
          "d": "Sachliche Argumente für Preis und Kaufvertrag."
        }
      ],
      "nutzen_etw_extra": {
        "t": "WEG durchleuchten",
        "d": "Rücklage, Beschlüsse, Sonderumlagen – und Ihr Anteil daran."
      },
      "vertrauen": "In diesem Auftrag arbeiten wir ausschließlich für Sie. Provisionen von Maklern, Verkäufern oder Handwerksbetrieben schließt die Berufsordnung der Baukammer Berlin aus.",
      "pauschal": "Festpreis inkl. 19 % USt und Anfahrt in Berlin. Zuschläge richten sich nach dem Objekt, Optionen wählen Sie selbst; Amtsgebühren reichen wir ohne Aufschlag weiter.",
      "ausserhalb": "Außerhalb Berlins nennen wir Ihnen die Anfahrtspauschale vorab im Angebot.",
      "ablauf": [
        {
          "t": "Anfrage",
          "w": "heute",
          "d": "Adresse, Exposé und vorhandene Unterlagen per E-Mail."
        },
        {
          "t": "Termin",
          "w": "meist in 1–2 Wochen",
          "d": "Zugang stimmen Sie mit dem Makler ab – oder wir."
        },
        {
          "t": "Begehung",
          "w": "2–5 Std.",
          "d": "Mündliches Fazit direkt vor Ort."
        },
        {
          "t": "Bericht",
          "w": "7–10 Werktage",
          "d": "Express in 3 Werktagen – rechtzeitig vor dem Notar."
        }
      ],
      "bekommen": ["Mündliches Fazit direkt nach der Begehung", "Zustandsbericht als PDF mit Fotos", "Mängelliste mit Ampel: akut · mittelfristig · beobachten", "Kostenrahmen je Position und für 10–15 Jahre", "Pflichten nach dem Kauf mit Fristen", "Hinweise zu Förderung und nächsten Schritten"],
      "grenzen": ["Zerstörungsfrei und soweit zugänglich: keine Bauteilöffnungen; Proben nur als Option und mit Zustimmung des Eigentümers", "Nicht zugängliche oder verdeckte Bauteile (z. B. Dach ohne sicheren Zugang, Leitungen in Wänden) bewerten wir nur nach Indizien", "Keine Funktionsprüfung von Heizung, Elektro und Leitungen (das machen Fachbetriebe) und keine Standsicherheitsprüfung", "Feuchtemessungen sind Vergleichsmessungen; Kosten sind Schätzspannen, keine Angebote", "Keine Wertermittlung und keine Rechtsberatung – rechtliche Fragen, etwa zum Kaufvertrag, klärt bei Bedarf Ihr Anwalt"],
      "beauftragen": "Sie erhalten zuerst unser Angebot mit Bedingungen und Widerrufsbelehrung. Dann beauftragen Sie uns per E-Mail; soll die Begehung innerhalb der 14-tägigen Widerrufsfrist stattfinden, bestätigen Sie das bitte ausdrücklich.",
      "rechtsstand": "Rechtsstand Oktober 2026 · allgemeine Hinweise, keine Rechtsberatung",
      "qualifikation": ["Begutachtung durch den Geschäftsführer M. Sc. Abdel Karim Abu Elkheir persönlich", "B. Eng. Bauingenieurwesen, M. Sc. Wirtschaftsingenieurwesen (Bautechnik)", "Mitglied der Baukammer Berlin", "Berufshaftpflicht: 3 Mio. € Personen-, 300.000 € Vermögensschäden"],
      "unterlagen_titel": "Diese Unterlagen helfen uns",
      "unterlagen_unter": "Bitte beim Makler, Verkäufer oder Verwalter anfordern – diese Seite können Sie direkt weiterleiten. Nicht alles muss vorliegen.",
      "prio": {
        "1": "Unverzichtbar",
        "2": "Wichtig",
        "3": "Wenn vorhanden"
      },
      "qr_titel": "Preis berechnen und Hinweise zu Ihrem Baujahr",
      "qr_text": "Baujahr, Heizung und Nutzung eingeben – der Rechner zeigt Ihren Preis, passende Hinweise und die Unterlagen für Ihr Objekt."
    },
    "en": {
      "kopf_unter": "Pre-purchase inspections · Berlin",
      "titel": "Know what you’re buying – before you sign at the notary.",
      "objekt_efh": "House",
      "objekt_efh_unter": "detached, semi-detached or terraced",
      "objekt_etw": "Flat (condominium)",
      "objekt_etw_unter": "including the owners’ association records",
      "nutzen": [
        {
          "t": "Spot defects",
          "d": "Damp, roof, heating, suspected pollutants – before you sign."
        },
        {
          "t": "Know the costs",
          "d": "What the next 10–15 years will cost you, with cost ranges."
        },
        {
          "t": "Negotiate better",
          "d": "Factual arguments for the price and the contract."
        }
      ],
      "nutzen_etw_extra": {
        "t": "Check the WEG",
        "d": "Owners’ association: reserve, resolutions, special levies – and your share."
      },
      "vertrauen": "On this job we work solely for you. The Berlin Chamber of Engineers’ code of conduct rules out commissions from agents, sellers or contractors.",
      "pauschal": "Fixed price incl. 19% VAT and travel within Berlin. Surcharges depend on the property, options are your choice; office fees are passed on without mark-up.",
      "ausserhalb": "Outside Berlin we state the travel fee in advance in our quote.",
      "ablauf": [
        {
          "t": "Enquiry",
          "w": "today",
          "d": "Address, property listing (exposé) and any documents by email."
        },
        {
          "t": "Appointment",
          "w": "usually within 1–2 weeks",
          "d": "You arrange access with the agent – or we do."
        },
        {
          "t": "Inspection",
          "w": "2–5 h",
          "d": "Verbal summary right on site."
        },
        {
          "t": "Report",
          "w": "7–10 working days",
          "d": "Express in 3 working days – in time for the notary."
        }
      ],
      "bekommen": ["Verbal summary right after the inspection", "Condition report as PDF with photos", "Defect list with traffic lights: urgent · medium-term · monitor", "Cost ranges per item and for 10–15 years", "Duties after purchase, with deadlines", "Notes on subsidies and next steps"],
      "grenzen": ["Non-destructive and as far as accessible: no opening-up; samples only as an option and with the owner’s consent", "Inaccessible or concealed parts (e.g. a roof without safe access, pipes inside walls) are assessed from indications only", "No function test of heating, electrics or pipes (done by specialist firms) and no structural assessment", "Moisture readings are comparative; costs are estimate ranges, not quotes", "No valuation and no legal advice – legal questions, e.g. on the purchase contract, are for your lawyer"],
      "beauftragen": "You first receive our quote with our terms and information on your right of withdrawal. You then instruct us by email; if the inspection is to take place within the 14-day withdrawal period, please confirm this expressly.",
      "rechtsstand": "Legal position October 2026 · general information, not legal advice",
      "qualifikation": ["Inspection by the managing director, M. Sc. Abdel Karim Abu Elkheir, in person", "B. Eng. Civil Engineering, M. Sc. Industrial Engineering (construction)", "Member of the Berlin Chamber of Engineers (Baukammer Berlin)", "Professional indemnity: €3m personal injury, €300,000 financial loss"],
      "unterlagen_titel": "Documents that help us",
      "unterlagen_unter": "Please request them from the agent, seller or property manager – you can forward this page directly. Not everything needs to be available.",
      "prio": {
        "1": "Essential",
        "2": "Important",
        "3": "If available"
      },
      "qr_titel": "Calculate your price and get notes for your building’s age",
      "qr_text": "Enter year of construction, heating and use – the calculator shows your price, relevant notes and the documents for your property."
    }
  },
  "seite": {
    "de": {
      "unterzeile": "Begehung, Auswertung der Unterlagen und ein schriftlicher Zustandsbericht mit Mängelliste und Kostenrahmen für 10–15 Jahre – für Eigentumswohnung und Einfamilienhaus, zum Festpreis.",
      "dienst": "Kaufbegutachtung von Eigentumswohnungen und Einfamilienhäusern in Berlin: Auswertung der Unterlagen, Begehung soweit zugänglich, mündliches Fazit vor Ort, schriftlicher Zustandsbericht mit Mängelliste, Kostenrahmen für 10–15 Jahre und Pflichten nach dem Kauf.",
      "kategorien": {
        "pflicht": "Pflichten nach dem Kauf",
        "miete": "Vermietung",
        "pruefen": "Darauf achten wir besonders",
        "foerderung": "Gut zu wissen"
      },
      "hinweise_titel": "Hinweise nach Baujahr, Heizung und Nutzung",
      "hinweise_unter": "Allgemeine Prüfhinweise: worauf wir bei Objekten dieser Art achten. Sie sind kein Befund zu Ihrem Objekt.",
      "stundensatz": "Zusatzleistungen außerhalb der beschriebenen Leistungen: {brutto} je Stunde ({netto} netto).",
      "sprach_hinweis": "",
      "anteil": {
        "titel": "Ihr Anteil an Gemeinschaftskosten",
        "text": "Kosten einer Maßnahme der Gemeinschaft × Ihr Miteigentumsanteil = Ihr Anteil.",
        "beispiel": "Beispiel: 100.000 € × 45/1.000 = 4.500 €",
        "hinweis": "Reine Rechnung nach Miteigentumsanteil – keine Bewertung und keine Auskunft dazu, wer welche Kosten trägt."
      },
      "faq": [
        {
          "f": "Wie lange dauert die Kaufbegutachtung?",
          "a": "Die Begehung dauert bei einer Wohnung ca. 2–3 Stunden, bei einem Haus ca. 4–5 Stunden; das mündliche Fazit bekommen Sie direkt vor Ort. Der schriftliche Bericht folgt nach 7–10 Werktagen, als Express-Bericht innerhalb von 3 Werktagen. Einen Termin gibt es meist in 1–2 Wochen."
        },
        {
          "f": "Muss ich bei der Begehung dabei sein?",
          "a": "Nein. Den Zugang stimmen Sie mit dem Makler ab – oder wir. Sind Sie nicht vor Ort, besprechen wir das Fazit anschließend per Telefon oder Video mit Ihnen; den Zustandsbericht erhalten Sie als PDF mit Fotos."
        },
        {
          "f": "Bekomme ich den Bericht auf Englisch?",
          "a": "Ja. Der Bericht ist standardmäßig auf Deutsch. Mit der Option „Bericht auf Englisch“ für {brutto:englisch} inkl. USt ({netto:englisch} netto) erhalten Sie ihn auf Englisch, mit Glossar der deutschen Fachbegriffe (Hausgeld, Erhaltungsrücklage, Teilungserklärung)."
        },
        {
          "f": "Arbeiten Sie auch außerhalb Berlins?",
          "a": "Ja. In Berlin ist die Anfahrt im Festpreis enthalten. {text:ausserhalb}"
        },
        {
          "f": "Wie beauftrage ich Sie – und kann ich widerrufen?",
          "a": "{text:beauftragen}"
        },
        {
          "f": "Ersetzt die Kaufbegutachtung ein Wertgutachten oder eine Rechtsberatung?",
          "a": "Nein. Wir ermitteln keinen Verkehrswert und beraten nicht rechtlich – rechtliche Fragen, etwa zum Kaufvertrag, klärt bei Bedarf Ihr Anwalt. Die Begutachtung ist zerstörungsfrei und erfasst, was zugänglich ist; Kosten nennen wir als Schätzspannen, nicht als Angebote."
        }
      ],
      "ui": {
        "nur_wohnung": "Bei Eigentumswohnungen",
        "bekommen_titel": "Das bekommen Sie",
        "grenzen_titel": "Was nicht enthalten ist",
        "u_baujahr_bis": "nur bei Baujahr bis {bis}",
        "u_baujahr_ab": "nur bei Baujahr ab {von}",
        "u_baujahr_von_bis": "nur bei Baujahr {von}–{bis}",
        "u_heizung": "nur bei {liste}",
        "u_vermietet": "nur falls vermietet",
        "u_schalter": "nur bei {name}",
        "anteil_kurz": "Ihr Anteil an Gemeinschaftskosten",
        "grund": "Im Grundpreis enthalten",
        "zuschlaege": "Zuschläge – falls zutreffend",
        "zuschlag_ja": "fällt an",
        "zuschlag_nein": "entfällt",
        "zuschlag_flaeche": "Wohnfläche über {n} m²",
        "optionen": "Optionen – nach Wahl",
        "empfohlen": "Empfohlen für Ihr Objekt",
        "summe": "Ihr Preis",
        "inkl": "inkl. 19 % USt",
        "netto": "netto",
        "ust": "darin 19 % USt",
        "hinweise_leer": "Geben Sie Baujahr, Heizung und Nutzung ein – dann erscheinen die passenden Hinweise.",
        "hinweise_anzahl": "{n} Hinweise für Ihr Objekt",
        "hinweise_eins": "1 Hinweis für Ihr Objekt",
        "quelle": "Quelle",
        "passende_option": "Passende Option",
        "liegt_vor": "liegt vor",
        "wo": "Wo bekomme ich das?",
        "wo_kurz": "Erhältlich bei",
        "nur_bei": "nur bei",
        "kopiert": "Liste kopiert. Sie können sie jetzt einfügen und an Makler, Verkäufer oder Verwalter weiterleiten.",
        "mail_kopiert": "E-Mail-Text kopiert. Bitte an info@ing-bassam.de senden.",
        "kopieren_fehler": "Kopieren war nicht möglich. Bitte markieren Sie den Text unten und kopieren Sie ihn selbst.",
        "unterlagen_kopf": "Unterlagen für die Kaufbegutachtung",
        "objekt": "Objekt",
        "adresse": "Adresse",
        "termin": "Wunschtermin",
        "flaeche": "Wohnfläche",
        "baujahr": "Baujahr",
        "heizung": "Heizung",
        "nutzung": "Nutzung",
        "region": "Lage",
        "besonderheiten": "Besonderheiten",
        "leistungen": "Leistungen laut Preisrechner",
        "gesamt": "Gesamt",
        "vorhanden": "Diese Unterlagen liegen vor (im Anhang)",
        "vorhanden_anzahl": "{n} Unterlagen liegen vor (im Anhang).",
        "fehlen": "Noch fehlende unverzichtbare Unterlagen",
        "weitere": "… und {n} weitere",
        "anhang": "Hinweis: Unterlagen bitte an diese E-Mail anhängen; Namen und Bankdaten von Mietern bitte schwärzen.",
        "anrede": "Guten Tag,",
        "einleitung": "ich interessiere mich für eine Kaufbegutachtung und bitte um Ihr Angebot.",
        "gruss": "Mit freundlichen Grüßen",
        "betreff": "Anfrage Kaufbegutachtung",
        "keine": "keine",
        "objekt_kurz": {
          "efh": "Haus",
          "etw": "Wohnung",
          "beide": "Haus und Wohnung"
        },
        "baujahr_von_bis": "Baujahr {von}–{bis}",
        "baujahr_bis": "Baujahr bis {bis}",
        "baujahr_ab": "Baujahr ab {von}",
        "heizung_bed": "Heizung: {liste}",
        "nutzung_bed": "Nutzung: {liste}",
        "region_bed": "Lage: {liste}",
        "oder": "oder",
        "unbekannt": "unbekannt",
        "bitte_waehlen": "Bitte wählen",
        "leistung": "Leistung",
        "preis": "Preis inkl. 19 % USt",
        "fehler_flaeche": "Bitte eine Wohnfläche zwischen 10 und 2.000 m² eingeben.",
        "fehler_baujahr": "Bitte ein Baujahr zwischen 1800 und 2030 eingeben.",
        "anteil_ergebnis": "Ihr Anteil: {betrag}",
        "anteil_fehlt": "Kosten und Miteigentumsanteil eingeben – dann erscheint Ihr Anteil."
      }
    },
    "en": {
      "unterzeile": "Inspection, document review and a written condition report with defect list and a 10–15-year cost outlook – for flats and houses, at a fixed price.",
      "dienst": "Pre-purchase inspection of flats and houses in Berlin: document review, inspection as far as accessible, verbal summary on site, written condition report with defect list, 10–15-year cost outlook and duties after purchase.",
      "kategorien": {
        "pflicht": "Duties after purchase",
        "miete": "Letting",
        "pruefen": "What we look at closely",
        "foerderung": "Good to know"
      },
      "hinweise_titel": "Notes by year of construction, heating and use",
      "hinweise_unter": "General inspection notes: what we look out for in properties of this kind. They are not a finding about your property.",
      "stundensatz": "Additional work outside the described services: {brutto} per hour ({netto} net).",
      "sprach_hinweis": "Our reports are written in German as standard. A report in English is an option for {brutto:englisch} incl. VAT ({netto:englisch} net) – the inspection itself and all calls can be in English.",
      "anteil": {
        "titel": "Your share of common costs",
        "text": "Cost of a measure taken by the owners’ association × your co-ownership share = your share.",
        "beispiel": "Example: €100,000 × 45/1,000 = €4,500",
        "hinweis": "A plain calculation by co-ownership share – no assessment and no statement on who bears which costs."
      },
      "faq": [
        {
          "f": "How long does the pre-purchase inspection take?",
          "a": "The inspection takes approx. 2–3 hours for a flat and approx. 4–5 hours for a house; you get the verbal summary right on site. The written report follows within 7–10 working days, as an express report within 3 working days. An appointment is usually available within 1–2 weeks."
        },
        {
          "f": "Do I have to be there for the inspection?",
          "a": "No. You arrange access with the agent – or we do. If you are not on site, we go through the summary with you afterwards by phone or video; you receive the condition report as a PDF with photos."
        },
        {
          "f": "Is the report in English?",
          "a": "Not as standard – our reports are written in German. With the option “Report in English” for {brutto:englisch} incl. VAT ({netto:englisch} net) you receive the condition report in English, with a glossary of the German terms (Hausgeld, maintenance reserve, declaration of division). The inspection itself and all calls can be in English."
        },
        {
          "f": "Do you work outside Berlin?",
          "a": "Yes. Within Berlin, travel is included in the fixed price. {text:ausserhalb}"
        },
        {
          "f": "How do I instruct you – and can I withdraw?",
          "a": "{text:beauftragen}"
        },
        {
          "f": "Does the inspection replace a valuation or legal advice?",
          "a": "No. We do not determine the market value and do not give legal advice – legal questions, e.g. on the purchase contract, are for your lawyer. The inspection is non-destructive and covers what is accessible; costs are estimate ranges, not quotes."
        }
      ],
      "ui": {
        "nur_wohnung": "For flats",
        "bekommen_titel": "What you receive",
        "grenzen_titel": "What is not included",
        "u_baujahr_bis": "only for buildings up to {bis}",
        "u_baujahr_ab": "only for buildings from {von}",
        "u_baujahr_von_bis": "only for buildings from {von}–{bis}",
        "u_heizung": "only with {liste}",
        "u_vermietet": "only if let",
        "u_schalter": "only for {name}",
        "anteil_kurz": "Your share of common costs",
        "grund": "Included in the base price",
        "zuschlaege": "Surcharges – where applicable",
        "zuschlag_ja": "applies",
        "zuschlag_nein": "does not apply",
        "zuschlag_flaeche": "living area above {n} m²",
        "optionen": "Options – your choice",
        "empfohlen": "Recommended for your property",
        "summe": "Your price",
        "inkl": "incl. 19% VAT",
        "netto": "net",
        "ust": "of which 19% VAT",
        "hinweise_leer": "Enter year of construction, heating and use – the relevant notes will then appear.",
        "hinweise_anzahl": "{n} notes for your property",
        "hinweise_eins": "1 note for your property",
        "quelle": "Source",
        "passende_option": "Matching option",
        "liegt_vor": "available",
        "wo": "Where do I get it?",
        "wo_kurz": "Available from",
        "nur_bei": "only if",
        "kopiert": "List copied. You can now paste it and forward it to the agent, seller or property manager.",
        "mail_kopiert": "Email text copied. Please send it to info@ing-bassam.de.",
        "kopieren_fehler": "Copying was not possible. Please select the text below and copy it yourself.",
        "unterlagen_kopf": "Documents for the pre-purchase inspection",
        "objekt": "Property",
        "adresse": "Address",
        "termin": "Preferred date",
        "flaeche": "Living area",
        "baujahr": "Year of construction",
        "heizung": "Heating",
        "nutzung": "Use",
        "region": "Location",
        "besonderheiten": "Particulars",
        "leistungen": "Services according to the price calculator",
        "gesamt": "Total",
        "vorhanden": "These documents are available (attached)",
        "vorhanden_anzahl": "{n} documents are available (attached).",
        "fehlen": "Essential documents still missing",
        "weitere": "… and {n} more",
        "anhang": "Note: please attach the documents to this email; black out tenants’ names and bank details.",
        "anrede": "Hello,",
        "einleitung": "I am interested in a pre-purchase inspection and would like to receive your quote.",
        "gruss": "Kind regards",
        "betreff": "Enquiry: pre-purchase inspection",
        "keine": "none",
        "objekt_kurz": {
          "efh": "House",
          "etw": "Flat",
          "beide": "House and flat"
        },
        "baujahr_von_bis": "Built {von}–{bis}",
        "baujahr_bis": "Built up to {bis}",
        "baujahr_ab": "Built from {von}",
        "heizung_bed": "Heating: {liste}",
        "nutzung_bed": "Use: {liste}",
        "region_bed": "Location: {liste}",
        "oder": "or",
        "unbekannt": "unknown",
        "bitte_waehlen": "Please choose",
        "leistung": "Service",
        "preis": "Price incl. 19% VAT",
        "fehler_flaeche": "Please enter a living area between 10 and 2,000 m².",
        "fehler_baujahr": "Please enter a year of construction between 1800 and 2030.",
        "anteil_ergebnis": "Your share: {betrag}",
        "anteil_fehlt": "Enter the cost and your co-ownership share – your share will then appear."
      }
    }
  }
} /* DATEN-ENDE */;

export default DATEN;
