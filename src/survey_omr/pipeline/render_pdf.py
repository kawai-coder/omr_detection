from __future__ import annotations

from pathlib import Path

import fitz
import cv2
import numpy as np

from survey_omr.pipeline.cache import render_cache_dir


def render_pdf_pages(pdf_path: Path, dpi: int, cache_root: Path) -> list[Path]:
    """Render PDF pages to cached PNG files and return path list."""
    cache_dir = render_cache_dir(pdf_path, cache_root)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    paths: list[Path] = []
    for i, page in enumerate(doc, start=1):
        out_path = cache_dir / f"page_{i:03d}.png"
        paths.append(out_path)
        if out_path.exists():
            continue
        pix = page.get_pixmap(matrix=mat, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else arr
        cv2.imwrite(str(out_path), bgr)
    return paths
