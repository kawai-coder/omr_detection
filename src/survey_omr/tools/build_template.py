from __future__ import annotations

from pathlib import Path

import cv2

from survey_omr.pipeline.render_pdf import render_pdf_pages
from survey_omr.utils.io import read_yaml, write_yaml


def build_template(pdf_path: Path, out_dir: Path, schema_out: Path, dpi: int, cache_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = render_pdf_pages(pdf_path, dpi=dpi, cache_root=cache_dir)
    if len(pages) < 2:
        raise ValueError("PDF must contain at least 2 pages.")

    p1 = cv2.imread(str(pages[0]))
    p2 = cv2.imread(str(pages[1]))
    t1 = out_dir / "template_page1.png"
    t2 = out_dir / "template_page2.png"
    cv2.imwrite(str(t1), p1)
    cv2.imwrite(str(t2), p2)

    example = Path(__file__).resolve().parents[1] / "config" / "schema.example.yaml"
    schema = read_yaml(example)
    schema.setdefault("meta", {})["dpi"] = dpi
    schema["meta"]["page_size"] = [int(p1.shape[1]), int(p1.shape[0])]
    schema["pages"]["page1"]["template_path"] = str(t1)
    schema["pages"]["page2"]["template_path"] = str(t2)
    write_yaml(schema_out, schema)
