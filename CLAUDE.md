# PDF-Konvertierung mit docling (Citavi-Anhänge)

## Zweck

Die PDF-Dateien im Unterordner `input/` (Citavi-7-Projektanhänge, Dateinamen sind GUIDs)
werden mit **docling** nach Markdown + JSON konvertiert (Text, Bilder, Tabellen).
Anschließend prüft der Nutzer die Ergebnisse in einer HTML-Review-Ansicht und
verwirft unerwünschte Abschnitte per Button — die Löschung wird direkt in die
.md- und .json-Dateien zurückgeschrieben.

## Umgebung

- Windows 11, PowerShell; Python 3.12 (Windows-Store-Installation)
- Installiert: `docling` 2.120.3 (inkl. `docling-core` mit `delete_items`-API), pandas
- OCR: RapidOCR (torch, CPU) — Modelle sind bereits lokal gecacht

## Dateien

| Datei | Zweck |
|---|---|
| `input/` | Eingabeordner: hier liegen die zu konvertierenden `*.pdf`. |
| `convert_pdfs.py` | Batch-Konvertierung aller `input/*.pdf` → `output/<stem>/`. Aufruf: `python convert_pdfs.py [N]` (N = max. Anzahl, ohne N = alle). Überspringt Ordner mit `.done`-Marker. |
| `review_render.py` | Erzeugt `review.html` pro Dokument (von Konverter UND Server genutzt). Enthält auch `normalize_slashes()`. |
| `review_server.py` | Lokaler Server, Port **8765** (`python review_server.py`, dann http://localhost:8765). Index-Seite + statische Auslieferung + `POST /discard`. |

## Ausgabestruktur pro PDF (`output/<stem>/`)

- `<stem>.md` — Markdown, Bildverweise **relativ** (`<stem>_artifacts/...`, Forward-Slashes)
- `<stem>.json` — DoclingDocument-JSON, ebenfalls relative Bildverweise
- `<stem>_artifacts/` — von docling ausgelagerte Bilder (in md+json referenziert)
- `review.html` — Review-Ansicht; `review_images/` — content-hash-benannte Bilder dafür
- `picture_<i>.png`, `table_<i>.png`, `table_<i>.csv` — Einzelexporte (nur bei Konvertierung erzeugt, werden bei Discards NICHT aktualisiert)
- `.done` — Marker „fertig konvertiert" (löschen = Neukonvertierung erzwingen)

## Review-/Verwerfen-Mechanismus

- `review.html` gruppiert Elemente in Abschnitte: jede Überschrift (`TitleItem`/
  `SectionHeaderItem`) beginnt einen neuen Abschnitt; Texte/Bilder/Tabellen bis zur
  nächsten Überschrift gehören dazu. Jeder Abschnitt trägt `data-refs` (Liste der
  docling `self_ref`s, z. B. `#/texts/12`) und einen Button „Element verwerfen".
- Klick → `POST /discard {doc, refs}` → Server lädt die JSON via
  `DoclingDocument.load_from_json`, löst **erst alle** Refs auf (Löschen verschiebt
  Indizes!), ruft `doc.delete_items(node_items=...)` auf, speichert md+json neu
  (`ImageRefMode.REFERENCED`, relatives `artifacts_dir`) und rendert `review.html` neu.
- **Kein Undo.** Verworfene Elemente sind aus md+json endgültig entfernt
  (Original-PDF bleibt natürlich unberührt).
- Buttons funktionieren nur über den Server (http://localhost:8765), nicht via `file://`.

## Wichtige Stolperfallen

- **`artifacts_dir` muss als relativer `Path` übergeben werden**, sonst schreibt
  docling absolute Windows-Pfade in md/json. Nach jedem Speichern
  `normalize_slashes()` aufrufen (docling nutzt Backslashes).
- **`self_ref`s sind indexbasiert und verschieben sich nach jedem Löschen.** Deshalb:
  niemals Refs über einen Discard hinweg cachen; `review.html` wird nach jedem
  Discard serverseitig neu erzeugt. Bilder für die HTML-Ansicht sind deshalb
  content-hash-benannt (`review_images/img_<sha1>.png`) statt indexbasiert.
- **`discard_elements()` wechselt per `os.chdir` ins Dokumentverzeichnis** (mit Lock
  serialisiert), damit relative Bild-URIs aus der JSON beim Neu-Speichern/Rendern
  auflösbar sind.
- Output-Ordner können durch Explorer/andere Prozesse **gesperrt** sein
  (Remove-Item schlägt fehl). Inhalt löschen reicht; der Konverter schreibt in
  existierende Ordner hinein.
- OCR (`do_ocr=True`) macht bildreiche PDFs langsam (~2 min); Warnungen
  „RapidOCR returned empty result" sind harmlos (Bildbereiche ohne Text).
- Tests für den Discard-Flow an einer **Kopie** durchführen (Ordner
  `output/_testdoc`, Dateien auf `_testdoc.*` umbenennen), nie an echten Daten.

## Stand (2026-08-20)

- 34 PDFs im Ordner `input/`; **2 konvertiert** und vom Nutzer zu beurteilen:
  `039dd06f-…` (Zeitschrift, 179 Bilder, 5 Tabellen) und `0bad208e-…` (Artikel).
- Discard-Flow ist end-to-end getestet (direkt + via HTTP).
- **Nächster Schritt:** Nach Freigabe durch den Nutzer `python convert_pdfs.py`
  (ohne Argument) für die restlichen 32 PDFs laufen lassen; dauert mit OCR
  potenziell >30 min, daher im Hintergrund starten.
- Offene Ideen (nicht beauftragt): Backup vor jedem Discard, Undo-Funktion,
  OCR abschaltbar machen falls alle PDFs echten Text enthalten.
