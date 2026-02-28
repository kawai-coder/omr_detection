from __future__ import annotations

from typing import Any

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


def score_mark(roi: np.ndarray) -> float:
    """Return a 0~1 mark score using ink ratio + connected component proxy."""
    gray = roi.mean(axis=2) if roi.ndim == 3 else roi.astype(np.float32)
    if cv2 is None:
        th = (gray < 200).astype(np.uint8)
        ink_ratio = float(th.mean())
        return min(1.0, ink_ratio * 2.0)

    gray_u8 = gray.astype(np.uint8)
    _, th = cv2.threshold(gray_u8, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
    ink_ratio = float((th > 0).mean())

    n, _, stats, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    max_cc = int(stats[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0
    area = th.shape[0] * th.shape[1]
    cc_ratio = max_cc / max(1, area)
    return float(min(1.0, 0.7 * ink_ratio + 0.3 * cc_ratio * 5))


def detect_option_marks(option_rois: dict[str, np.ndarray], threshold: float = 0.18) -> dict[str, Any]:
    scores = {opt: score_mark(img) for opt, img in option_rois.items()}
    pred = {opt for opt, s in scores.items() if s >= threshold}
    return {"mark_scores": scores, "marks_pred": pred}
