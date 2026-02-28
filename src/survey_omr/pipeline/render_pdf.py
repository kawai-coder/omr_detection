from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image
from tqdm import tqdm

from survey_omr.pipeline.cache import render_cache_dir


def render_pdf_to_images(pdf_path: Path, dpi: int, cache_root: Path) -> list[Path]:
    """Render each page from PDF into cached PNG files."""
    page_paths: list[Path] = []
    out_dir = render_cache_dir(pdf_path, cache_root)

    with fitz.open(pdf_path) as doc:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for i in tqdm(range(doc.page_count), desc="render", unit="page"):
            out_path = out_dir / f"page_{i+1:03d}.png"
            if not out_path.exists():
                page = doc[i]
                pix = page.get_pixmap(matrix=mat, alpha=False)
                mode = "RGB"
                img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                img.save(out_path)
            page_paths.append(out_path)
    return page_paths
