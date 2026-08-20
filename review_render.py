"""Erzeugt pro konvertiertem PDF eine review.html mit gerenderten Bildern/Tabellen.

Jeder Abschnitt (Überschrift + zugehöriger Text/Bilder/Tabellen) bekommt einen
Button "Element verwerfen". Der Klick ruft den lokalen review_server auf, der
die Elemente aus der .md- und .json-Datei löscht.

Bilder werden content-hash-benannt in review_images/ abgelegt, damit die
Referenzen auch nach Löschungen (bei denen sich docling-interne Indizes
verschieben) stabil bleiben.
"""

import hashlib
import html
import io
import json
from pathlib import Path

from docling_core.types.doc import PictureItem, TableItem
from docling_core.types.doc.document import SectionHeaderItem, TitleItem

STYLE = """
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0;
       background: #f0f0f3; color: #1a1a1a; }
.wrap { max-width: 860px; margin: 0 auto; padding: 24px 16px 80px; }
h1.doc-title { font-size: 1.3rem; color: #444; }
section { background: #fff; border: 1px solid #ddd; border-radius: 10px;
          padding: 18px 22px; margin: 18px 0; transition: opacity .35s, transform .35s; }
section.discarded { opacity: 0; transform: translateX(40px); }
section h1 { font-size: 1.5rem; margin: .3em 0; }
section h2 { font-size: 1.2rem; margin: .3em 0; }
p { line-height: 1.55; }
img { max-width: 100%; height: auto; border: 1px solid #eee; border-radius: 4px;
      display: block; margin: 10px 0; }
figcaption { font-size: .85rem; color: #666; margin: -6px 0 12px; }
table { border-collapse: collapse; margin: 12px 0; font-size: .9rem; max-width: 100%;
        display: block; overflow-x: auto; }
th, td { border: 1px solid #ccc; padding: 5px 9px; text-align: left; }
th { background: #f5f5f5; }
button.discard { background: #c62828; color: #fff; border: none; border-radius: 6px;
                 padding: 7px 14px; font-size: .85rem; cursor: pointer; float: right;
                 margin-left: 12px; }
button.discard:hover { background: #a31f1f; }
button.discard:disabled { background: #999; cursor: wait; }
.err { color: #c62828; font-size: .85rem; margin-top: 6px; }
.hint { background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px;
        padding: 10px 14px; font-size: .9rem; }
"""

SCRIPT = """
async function discard(btn) {
  const section = btn.closest('section');
  const refs = JSON.parse(section.dataset.refs);
  btn.disabled = true; btn.textContent = 'wird verworfen…';
  try {
    const res = await fetch('/discard', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({doc: DOC, refs: refs})
    });
    const j = await res.json();
    if (!j.ok) throw new Error(j.error || 'Unbekannter Fehler');
    section.classList.add('discarded');
    setTimeout(() => section.remove(), 400);
  } catch (e) {
    btn.disabled = false; btn.textContent = 'Element verwerfen';
    let err = section.querySelector('.err');
    if (!err) { err = document.createElement('div'); err.className = 'err';
                btn.insertAdjacentElement('afterend', err); }
    err.textContent = 'Löschen fehlgeschlagen: ' + e.message +
      ' — läuft review_server.py und ist die Seite über http://localhost geöffnet?';
  }
}
"""


def normalize_slashes(md_path: Path, json_path: Path, artifacts_name: str) -> None:
    """Backslashes in den Artefakt-Verweisen durch '/' ersetzen (portabler)."""
    for path in (md_path, json_path):
        text = path.read_text(encoding="utf-8")
        fixed = text.replace(f"{artifacts_name}\\\\", f"{artifacts_name}/") \
                    .replace(f"{artifacts_name}\\", f"{artifacts_name}/")
        if fixed != text:
            path.write_text(fixed, encoding="utf-8")


def _save_review_image(pil_image, img_dir: Path) -> str:
    buf = io.BytesIO()
    pil_image.save(buf, "PNG")
    data = buf.getvalue()
    name = "img_" + hashlib.sha1(data).hexdigest()[:16] + ".png"
    path = img_dir / name
    if not path.exists():
        img_dir.mkdir(exist_ok=True)
        path.write_bytes(data)
    return f"review_images/{name}"


def render_review_html(doc, out_dir: Path, stem: str) -> Path:
    """Schreibt out_dir/review.html und gibt den Pfad zurück."""
    img_dir = out_dir / "review_images"

    sections = []  # Liste von {"refs": [...], "parts": [...]}
    current = {"refs": [], "parts": []}
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            current["parts"].append("</ul>")
            in_list = False

    def flush():
        nonlocal current
        close_list()
        if current["parts"]:
            sections.append(current)
        current = {"refs": [], "parts": []}

    for element, _level in doc.iterate_items():
        if isinstance(element, (TitleItem, SectionHeaderItem)):
            # Neue Überschrift eröffnet einen neuen Abschnitt
            flush()
            tag = "h1" if isinstance(element, TitleItem) else "h2"
            current["refs"].append(element.self_ref)
            current["parts"].append(f"<{tag}>{html.escape(element.text)}</{tag}>")
        elif isinstance(element, TableItem):
            close_list()
            current["refs"].append(element.self_ref)
            try:
                table_html = element.export_to_html(doc)
            except Exception:
                table_html = "<p><em>[Tabelle nicht darstellbar]</em></p>"
            current["parts"].append(table_html)
        elif isinstance(element, PictureItem):
            close_list()
            current["refs"].append(element.self_ref)
            img = element.get_image(doc)
            if img is not None:
                src = _save_review_image(img, img_dir)
                caption = element.caption_text(doc)
                cap_html = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
                current["parts"].append(f'<img src="{src}" alt="">{cap_html}')
            else:
                current["parts"].append("<p><em>[Bild ohne Daten]</em></p>")
        elif hasattr(element, "text"):
            text = (element.text or "").strip()
            if not text:
                continue
            current["refs"].append(element.self_ref)
            if element.label == "list_item":
                if not in_list:
                    current["parts"].append("<ul>")
                    in_list = True
                current["parts"].append(f"<li>{html.escape(text)}</li>")
            else:
                close_list()
                current["parts"].append(f"<p>{html.escape(text)}</p>")
    flush()

    body_parts = []
    for sec in sections:
        refs_attr = html.escape(json.dumps(sec["refs"]), quote=True)
        body_parts.append(
            f'<section data-refs="{refs_attr}">'
            f'<button class="discard" onclick="discard(this)">Element verwerfen</button>'
            + "".join(sec["parts"])
            + "</section>"
        )

    page = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review: {html.escape(stem)}</title>
<style>{STYLE}</style>
<script>const DOC = {json.dumps(stem)};{SCRIPT}</script>
</head>
<body>
<div class="wrap">
<h1 class="doc-title">Review: {html.escape(stem)}</h1>
<p class="hint">Diese Seite über <code>review_server.py</code> öffnen
(http://localhost:8765), sonst können die Verwerfen-Buttons nicht in die
.md/.json-Dateien schreiben.</p>
{"".join(body_parts)}
</div>
</body>
</html>"""

    out_path = out_dir / "review.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path
