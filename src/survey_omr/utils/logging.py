from __future__ import annotations

import logging
from pathlib import Path

from .io import ensure_dir


def setup_logging(log_path: Path, verbose: bool = True) -> logging.Logger:
    """Setup root logger writing to file + console."""
    ensure_dir(log_path.parent)
    logger = logging.getLogger("survey_omr")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    logger.addHandler(file_handler)

    if verbose:
        stream = logging.StreamHandler()
        stream.setLevel(logging.INFO)
        stream.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
        logger.addHandler(stream)

    return logger
