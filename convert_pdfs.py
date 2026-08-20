"""Konvertiert alle PDFs in diesem Ordner mit docling nach Markdown + JSON.

Pro PDF wird ein Unterordner in ./output angelegt:
    output/<name>/<name>.md            Markdown mit referenzierten Bildern (relative Pfade)
    output/<name>/<name>.json          DoclingDocument als JSON (relative Pfade)
    output/<name>/<name>_artifacts/    ausgelagerte Bilder (Seiten/Abbildungen)
    output/<name>/review.html          HTML-Ansicht mit "Element verwerfen"-Buttons
    output/<name>/review_images/       Bilder für die HTML-Ansicht
    output/<name>/picture_<i>.png      Abbildungen einzeln
    output/<name>/table_<i>.png        Tabellen als Bild
    output/<name>/table_<i>.csv        Tabellen als Daten

Aufruf:
    python convert_pdfs.py           # alle PDFs
    python convert_pdfs.py 2         # nur die ersten 2 (noch nicht konvertierten)
"""

import sys
import time
import traceback
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem

from review_render import normalize_slashes, render_review_html

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


def build_converter() -> DocumentConverter:
    opts = PdfPipelineOptions()
    opts.images_scale = 2.0          # scale=1 entspricht 72 DPI -> 2.0 = 144 DPI
    opts.generate_page_images = True
    opts.generate_picture_images = True
    opts.do_table_structure = True
    opts.do_ocr = True               # nötig für gescannte PDFs
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )


def convert_one(converter: DocumentConverter, pdf_path: Path) -> None:
    out_dir = OUTPUT_DIR / pdf_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    result = converter.convert(pdf_path)
    doc = result.document

    # Markdown und JSON, Bilder ausgelagert in <name>_artifacts.
    # artifacts_dir als RELATIVER Pfad -> relative Bildverweise in md/json
    artifacts = Path(f"{pdf_path.stem}_artifacts")
    md_path = out_dir / f"{pdf_path.stem}.md"
    json_path = out_dir / f"{pdf_path.stem}.json"
    doc.save_as_markdown(md_path, image_mode=ImageRefMode.REFERENCED, artifacts_dir=artifacts)
    doc.save_as_json(json_path, image_mode=ImageRefMode.REFERENCED, artifacts_dir=artifacts)
    normalize_slashes(md_path, json_path, artifacts.name)

    # HTML-Ansicht mit Verwerfen-Buttons
    render_review_html(doc, out_dir, pdf_path.stem)

    # Abbildungen und Tabellen zusätzlich einzeln als PNG
    for i, (element, _level) in enumerate(doc.iterate_items()):
        if isinstance(element, PictureItem):
            img = element.get_image(doc)
            if img:
                img.save(out_dir / f"picture_{i}.png", "PNG")
        elif isinstance(element, TableItem):
            img = element.get_image(doc)
            if img:
                img.save(out_dir / f"table_{i}.png", "PNG")

    # Tabellen als Daten (CSV)
    for i, table in enumerate(doc.tables):
        try:
            df = table.export_to_dataframe(doc)
            df.to_csv(out_dir / f"table_{i}.csv", index=False)
        except Exception as e:
            print(f"    Warnung: Tabelle {i} nicht als CSV exportierbar: {e}")

    # Erfolgsmarker, damit ein erneuter Lauf diese Datei überspringt
    (out_dir / ".done").touch()


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    pdfs = sorted(BASE_DIR.glob("*.pdf"))
    # Bereits fertig konvertierte überspringen
    todo = [p for p in pdfs if not (OUTPUT_DIR / p.stem / ".done").exists()]
    skipped = len(pdfs) - len(todo)
    if skipped:
        print(f"{skipped} PDF(s) bereits konvertiert, werden übersprungen.")
    if limit is not None:
        todo = todo[:limit]

    print(f"{len(todo)} PDF(s) zu konvertieren.")
    if not todo:
        return

    converter = build_converter()
    failed = []
    for n, pdf in enumerate(todo, 1):
        print(f"[{n}/{len(todo)}] {pdf.name} ...", flush=True)
        t0 = time.time()
        try:
            convert_one(converter, pdf)
            print(f"    fertig in {time.time() - t0:.1f}s")
        except Exception:
            failed.append(pdf.name)
            print(f"    FEHLER bei {pdf.name}:")
            traceback.print_exc()

    print(f"\nFertig: {len(todo) - len(failed)} ok, {len(failed)} Fehler.")
    if failed:
        print("Fehlgeschlagen:", ", ".join(failed))


if __name__ == "__main__":
    main()
