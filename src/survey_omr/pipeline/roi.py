from __future__ import annotations

from typing import Any

import numpy as np

from survey_omr.utils.geometry import clip_box


def crop_roi(img: np.ndarray, box: list[int]) -> np.ndarray:
    x1, y1, x2, y2 = clip_box(box, img.shape[1], img.shape[0])
    return img[y1:y2, x1:x2].copy()


def iter_questions(schema: dict[str, Any], page_no: int) -> list[dict[str, Any]]:
    return [q for q in schema.get("questions", []) if int(q["page"]) == page_no]
