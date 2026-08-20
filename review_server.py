"""Lokaler Review-Server für die konvertierten PDFs.

Start:  python review_server.py
Dann im Browser öffnen: http://localhost:8765

- Zeigt eine Übersicht aller konvertierten Dokumente
- Serviert die review.html-Seiten samt Bildern
- POST /discard löscht die übergebenen Elemente aus der .md- und .json-Datei
  des Dokuments und erzeugt die review.html neu
"""

import html
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from docling_core.types.doc import ImageRefMode
from docling_core.types.doc.document import DoclingDocument, RefItem

from review_render import normalize_slashes, render_review_html

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
PORT = 8765

# Löschungen pro Dokument serialisieren
_lock = threading.Lock()


def discard_elements(stem: str, refs: list[str]) -> int:
    """Löscht die Elemente mit den gegebenen self_refs aus md + json.

    Gibt die Anzahl der gelöschten Elemente zurück.
    """
    out_dir = OUTPUT_DIR / stem
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    if not json_path.exists():
        raise FileNotFoundError(f"{json_path} nicht gefunden")

    # Ins Dokumentverzeichnis wechseln, damit die relativen Bildpfade aus der
    # JSON-Datei beim erneuten Speichern/Rendern korrekt aufgelöst werden.
    old_cwd = os.getcwd()
    os.chdir(out_dir)
    try:
        doc = DoclingDocument.load_from_json(json_path)

        # Erst ALLE Referenzen auflösen, dann löschen (Löschen verschiebt Indizes)
        items = []
        for ref in refs:
            try:
                items.append(RefItem(cref=ref).resolve(doc))
            except Exception:
                pass  # bereits gelöscht oder unbekannt -> ignorieren

        if items:
            doc.delete_items(node_items=items)

        artifacts = Path(f"{stem}_artifacts")
        doc.save_as_json(json_path, image_mode=ImageRefMode.REFERENCED, artifacts_dir=artifacts)
        doc.save_as_markdown(md_path, image_mode=ImageRefMode.REFERENCED, artifacts_dir=artifacts)
        normalize_slashes(md_path, json_path, artifacts.name)
        render_review_html(doc, out_dir, stem)
    finally:
        os.chdir(old_cwd)
    return len(items)


class ReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_index()
        else:
            super().do_GET()

    def _send_index(self):
        rows = []
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir() and (d / "review.html").exists():
                rows.append(
                    f'<li><a href="/{html.escape(d.name)}/review.html">{html.escape(d.name)}</a></li>'
                )
        page = (
            '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            "<title>PDF-Review</title>"
            '<style>body{font-family:sans-serif;max-width:700px;margin:40px auto}'
            "li{margin:6px 0}</style></head><body>"
            f"<h1>Konvertierte Dokumente ({len(rows)})</h1><ul>{''.join(rows)}</ul>"
            "</body></html>"
        )
        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/discard":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            stem = payload["doc"]
            refs = payload["refs"]
            # Pfad-Traversal verhindern
            if "/" in stem or "\\" in stem or ".." in stem:
                raise ValueError("Ungültiger Dokumentname")
            with _lock:
                deleted = discard_elements(stem, refs)
            body = {"ok": True, "deleted": deleted}
            status = 200
        except Exception as e:
            body = {"ok": False, "error": str(e)}
            status = 500
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        # Nur Fehler und Discards loggen, kein Request-Spam
        if "discard" in (args[0] if args else "") or "POST" in fmt % args:
            super().log_message(fmt, *args)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ReviewHandler)
    print(f"Review-Server läuft: http://localhost:{PORT}")
    print("Beenden mit Strg+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
