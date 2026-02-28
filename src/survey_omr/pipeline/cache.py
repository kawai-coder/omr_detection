from __future__ import annotations

from pathlib import Path

from survey_omr.utils.io import ensure_dir, file_sha1


def render_cache_dir(pdf_path: Path, cache_root: Path) -> Path:
    return ensure_dir(cache_root / "render" / file_sha1(pdf_path))
