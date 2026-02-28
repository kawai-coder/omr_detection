from __future__ import annotations

from pathlib import Path

from survey_omr.utils.io import ensure_dir, file_sha1


def render_cache_dir(pdf_path: Path, cache_root: Path) -> Path:
    """Return deterministic cache dir based on PDF hash."""
    pdf_hash = file_sha1(pdf_path)
    return ensure_dir(cache_root / "render" / pdf_hash)
