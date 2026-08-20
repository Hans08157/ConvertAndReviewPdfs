Zum Ausprobieren: Der Review-Server läuft bereits. Öffne im Browser:
http://localhost:8765 — dort siehst du die Übersicht beider Dokumente und kommst zu den Review-Seiten.

Was gebaut wurde:

1. convert_pdfs.py (aktualisiert): Bildverweise in .md und .json sind jetzt relativ (<name>_artifacts/... mit Forward-Slashes) — die Ordner sind damit verschiebbar. Zusätzlich wird pro PDF eine review.html erzeugt.
2. review.html pro Dokument: Alle Abschnitte als Karten — eine Überschrift plus der zugehörige Text, Bilder (gerendert) und Tabellen (als echte HTML-Tabellen). Jeder Abschnitt hat oben rechts einen roten Button „Element verwerfen".
3. review_server.py: Kleiner lokaler Server (Port 8765). Beim Klick auf „Element verwerfen" löscht er den kompletten Abschnitt (Überschrift + Texte + Bilder + Tabellen) aus der .md- und .json-Datei und erzeugt die review.html neu. Der Abschnitt verschwindet direkt aus der Seite. Das ist nötig, weil eine im Browser geöffnete HTML-Datei allein keine lokalen Dateien ändern darf — daher der Server als Vermittler. Getestet habe ich das an einer Wegwerf-Kopie: Löschen über HTTP entfernt die Elemente korrekt aus beiden Dateien.

Wichtig zu wissen:
- Der Server läuft gerade in dieser Session. Wenn du ihn später selbst starten willst: python review_server.py im Ordner, dann http://localhost:8765 öffnen. Die Seite direkt per Doppelklick (als file://) zu öffnen funktioniert für die Ansicht, aber die Verwerfen-Buttons brauchen den Server.
- Verworfen ist endgültig — es gibt keinen Undo-Button. Falls gewünscht, kann ich vor jeder Löschung ein Backup der md/json anlegen lassen.
- Die separaten picture_<i>.png/table_<i>.csv-Exporte bleiben beim Verwerfen unangetastet (nur md/json/html werden aktualisiert).

Schau dir die Review-Ansicht an — wenn Abschnittsaufteilung und Verhalten passen, lasse ich die restlichen 32 PDFs durchlaufen.