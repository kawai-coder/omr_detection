from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class MarkResult:
    score: float
    ink_ratio: float
    largest_cc_ratio: float
    marked: bool


def score_mark(img: np.ndarray, threshold: float = 0.18) -> MarkResult:
    """Score filled/marked status using ink ratio and connected component strength."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    th = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

    ink_ratio = float(np.mean(th > 0))
    nlabels, labels, stats, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    largest = 0
    if nlabels > 1:
        largest = int(stats[1:, cv2.CC_STAT_AREA].max())
    largest_cc_ratio = largest / max(1, th.shape[0] * th.shape[1])

    score = float(0.65 * ink_ratio + 0.35 * min(1.0, largest_cc_ratio * 4.0))
    return MarkResult(score=score, ink_ratio=ink_ratio, largest_cc_ratio=largest_cc_ratio, marked=score >= threshold)
