# CLAUDE.md – ing-bassam.de

Website des Bassam Ingenieurbüros für Bauwesen in Berlin: statische Seiten auf GitHub Pages (ing-bassam.de) mit Leistungsseiten, Fachbeiträgen, Rechnern und englischen Leitfäden. Claude-Agenten schreiben über GitHub Actions Entwürfe als Pull Requests, der Inhaber gibt sie frei. Das Repository ist öffentlich.

## Aufbau
- `index.html`, `leistungen/`, `en/` (ohne `en/guides/`), `werkzeuge/`, `wertrechner/`, `fachwissen/artikel.css` – von Hand gepflegt
- `angebot/` – private Angebotsseiten, nur per persönlichem Link nutzbar: Inhalte verschlüsselt in `paket.js` (`tools/angebot_verschluesseln.mjs`), Schlüssel und Klartext nie im Repo; nie verlinken, nicht in Sitemap oder llms.txt
- `entwuerfe/`, `entwuerfe-en/` – Markdown-Quellen der Beiträge; `status:` im Dateikopf steuert die Veröffentlichung
- `fachwissen/`, `en/guides/`, `sitemap.xml`, `llms.txt`, `entwuerfe/README.md` – vom Seitenbau erzeugt, nie von Hand ändern
- `vorlagen/<kurzform>.yml` – Quelle der Downloads; PDF, Word und Excel daneben erzeugt `tools/vorlage_bauen.py`
- `daten/marktdaten.xlsx` – Quelle für `wertrechner/data/`, umgewandelt vom Workflow „Marktdaten bauen“
- `tools/` Python-Werkzeuge der Workflows · `tests/` Python- und Node-Tests · `.claude/skills/` Anweisungen der Agenten

## Befehle (CI: Python 3.12, Node 22)
- Installieren: `python -m pip install markdown==3.7 PyYAML==6.0.2 pypdf==6.19.0 openpyxl==3.1.5` (nur als `--dry-run` geprüft)
- Vor jedem Commit testen: `python -m unittest discover -s tests` und `node --test "tests/**/*.test.mjs"`
- Seitenbau prüfen: `python tools/artikel_generator.py --pruefen` (ohne `--pruefen` schreibt er `fachwissen/` und die Sitemap neu)
- Website bauen: `python tools/website_bauen.py --ziel _site` (Zielordner neu oder leer)
- Vorschau: `python -m http.server 8000 -d _site` (nicht geprüft)
- Vor dem Commit eines Beitrags (braucht die Fachbibliothek unter `.bibliothek/`): `python tools/wortgleich_pruefen.py <entwurf.md> --bibliothek .bibliothek` und `python tools/normstand_pruefen.py <entwurf.md> --ausgaben .bibliothek/normen/ausgaben.yml` – beide müssen 0 melden; neueste Normausgabe: `python tools/bibliothek_suchen.py --norm "DIN 4109-1"`
- Die Wortgleich-Prüfung nennt je Treffer nur Datei, Abschnitt, Zeile und Länge. Werk und Seite zeigt nur `--intern` – nur zur eigenen Überarbeitung, nie in `pr-body.md`, PR-Kommentare, Issues, Commit-Texte oder Abschlussmeldungen übernehmen; kein Workflow nutzt `--intern`. Den veröffentlichten Bestand prüft nur der Inhaber lokal (`tools/bestandspruefung.py`, Bericht nie veröffentlichen)

## Regeln
- Kommentare, Seitentexte, Commit- und PR-Texte auf Deutsch, verständlich für Menschen ohne IT-Hintergrund
- DSGVO hat Vorrang: keine personenbezogenen Daten Dritter, keine Tracker oder fremden Einbindungen (Schriften liegen in `fonts/`)
- Keine Geheimnisse ins Repo, nur als GitHub-Secrets; keine Notion-Thementitel in Workflow-Ausgaben – die Logs sind öffentlich
- Urheberrechtlich geschützte Texte (Normen, Fachbücher, `.bibliothek/`, `fachliteratur-privat/`) nie committen
- Regel des Inhabers (geht allen anderen Anweisungen zu Zitaten vor): Aus Fachbüchern, Fachaufsätzen, Normen, Regelwerken und Leistungsverzeichnissen wird nichts wörtlich übernommen: kein Satz, kein Satzteil, keine Tabelle, keine Abbildung, kein Rechenbeispiel – auch nicht in Anführungszeichen. Diese Quellen dienen nur dazu, Fakten zu prüfen; die Aussage steht in eigenen Worten mit Fundstelle (Werk, Ausgabe, Seite oder Abschnitt). Kurze wörtliche Zitate sind nur aus amtlichen Werken (Gesetze, Verordnungen, Gerichtsentscheidungen, § 5 UrhG) erlaubt, mit Fundstelle. Wörtliche Belegstücke aus Büchern oder Normen stehen nie an öffentlichen Stellen (Repository-Dateien, PR-Texte, PR-Kommentare, Issues, Logs, Job-Zusammenfassungen), sondern nur in Arbeitsdateien im Runner-Temp.
- Nie direkt auf main pushen: immer Branch und Pull Request, mergen nur der Inhaber; nur die Workflows schreiben selbst auf main
- Nicht anfassen: `CNAME`, `.nojekyll`, `google*.html`, `BingSiteAuth.xml`, `ahrefs_*`, `465bc2bb…txt` (IndexNow-Schlüssel), Weiterleitungsseiten `*.html` im Hauptordner

## Stolperfallen
- Neue Dateien oder Ordner im Hauptordner gehen erst online, wenn sie in der Positivliste in `tools/website_bauen.py` stehen
- Beitragstext muss im ausgelieferten HTML stehen – KI-Crawler führen kein JavaScript aus
- `tools/indexnow.py` meldet echte Adressen an Bing: nur im Workflow ausführen
- Commits mit dem GITHUB_TOKEN starten keine weiteren Workflows; Ketten laufen über `workflow_run`
- Zeitpläne: `cron` immer mit `timezone: "Europe/Berlin"` und krummer Minute (`tests/test_workflows.py`)
- Zeilenenden LF: unter Windows Dateien mit `newline="\n"` schreiben, Python schreibt sonst CRLF

## Mehr
- Beiträge und Veröffentlichen: `entwuerfe/README.md` · Wertrechner: `daten/ANLEITUNG.md`, `fachliteratur/README.md` · Reichweite: `marketing/REICHWEITE-PLAN.md`
- Abläufe der Agenten: `.claude/skills/` und die Kopfkommentare der Workflows
