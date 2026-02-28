from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from survey_omr.pipeline.render_pdf import render_pdf_to_images
from survey_omr.utils.io import dump_yaml, ensure_dir, load_yaml


def build_template(pdf_path: Path, out_dir: Path, schema_example: Path, schema_out: Path, dpi: int = 300) -> dict[str, Any]:
    """Render first two pages as templates and initialize schema.yaml."""
    ensure_dir(out_dir)
    pages = render_pdf_to_images(pdf_path, dpi=dpi, cache_root=Path(".cache"))
    if len(pages) < 2:
        raise ValueError("PDF must contain at least 2 pages.")

    t1 = out_dir / "template_page1.png"
    t2 = out_dir / "template_page2.png"
    cv2.imwrite(str(t1), cv2.imread(str(pages[0])))
    cv2.imwrite(str(t2), cv2.imread(str(pages[1])))

    schema = load_yaml(schema_example)
    img = cv2.imread(str(t1))
    h, w = img.shape[:2]
    schema.setdefault("meta", {})
    schema["meta"].update({"dpi": dpi, "page_size": [w, h]})
    schema.setdefault("pages", {})
    schema["pages"]["page1"] = {"template_path": str(t1)}
    schema["pages"]["page2"] = {"template_path": str(t2)}
    dump_yaml(schema_out, schema)
    return schema
