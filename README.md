# ConvertAndReviewPdfs

Konvertiert PDF-Dateien (Citavi-7-Projektanhänge) mit **docling** nach Markdown + JSON
und bietet eine lokale HTML-Review-Ansicht, in der unerwünschte Abschnitte per Button
verworfen werden können.

## Ablauf

1. Zu konvertierende PDFs in den Ordner **`input/`** legen.
2. Konvertierung starten:
   ```powershell
   python convert_pdfs.py        # alle PDFs aus input/
   python convert_pdfs.py 2      # nur die ersten 2 (noch nicht konvertierten)
   ```
   Pro PDF entsteht `output/<name>/` mit `.md`, `.json`, ausgelagerten Bildern,
   Einzelexporten (`picture_<i>.png`, `table_<i>.png/.csv`) und einer `review.html`.
   Bereits konvertierte PDFs (Marker `output/<name>/.done`) werden übersprungen.
3. Review-Server starten und Ergebnisse prüfen:
   ```powershell
   python review_server.py
   ```
   Dann http://localhost:8765 öffnen. Die Übersichtsseite verlinkt alle Dokumente.

## Review / Verwerfen

- Jede `review.html` zeigt das Dokument als Abschnitts-Karten (Überschrift + zugehörige
  Texte, Bilder, Tabellen). Jeder Abschnitt hat einen Button „Element verwerfen".
- Ein Klick löscht den kompletten Abschnitt endgültig aus der `.md`- und `.json`-Datei
  und rendert die `review.html` neu. **Es gibt keinen Undo** — das Original-PDF in
  `input/` bleibt aber unberührt.
- Die Verwerfen-Buttons funktionieren nur über den Server (http://localhost:8765),
  nicht wenn die HTML-Datei direkt per `file://` geöffnet wird.
- Die separaten `picture_<i>.png`/`table_<i>.csv`-Exporte werden beim Verwerfen
  nicht aktualisiert (nur md/json/html).

## Voraussetzungen

- Windows 11, Python 3.12
- `docling` ≥ 2.120 (inkl. `docling-core` mit `delete_items`-API), `pandas`
- OCR: RapidOCR (torch, CPU); OCR ist aktiviert, gescannte PDFs dauern dadurch länger.
