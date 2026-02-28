from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    image: np.ndarray
    angle: float
    crop_box: tuple[int, int, int, int]


def _estimate_skew(binary: np.ndarray) -> float:
    lines = cv2.HoughLinesP(binary, 1, np.pi / 180, threshold=150, minLineLength=150, maxLineGap=20)
    if lines is None:
        return 0.0
    angles = []
    for line in lines[:200]:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -20 < angle < 20:
            angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def preprocess_page(img: np.ndarray) -> PreprocessResult:
    """Basic denoise, threshold, deskew and border crop pipeline."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()
    den = cv2.medianBlur(gray, 3)
    thr = cv2.adaptiveThreshold(den, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
    inv = 255 - thr
    angle = _estimate_skew(inv)

    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rot = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    _, b = cv2.threshold(rot, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    b_inv = 255 - b
    coords = cv2.findNonZero(b_inv)
    if coords is None:
        return PreprocessResult(image=rot, angle=angle, crop_box=(0, 0, w, h))
    x, y, cw, ch = cv2.boundingRect(coords)
    pad = 8
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(w, x + cw + pad), min(h, y + ch + pad)
    cropped = rot[y1:y2, x1:x2]
    return PreprocessResult(image=cropped, angle=angle, crop_box=(x1, y1, x2, y2))
