from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _estimate_skew_angle(bin_img: np.ndarray) -> float:
    lines = cv2.HoughLinesP(bin_img, 1, np.pi / 180, threshold=80, minLineLength=80, maxLineGap=10)
    if lines is None:
        return 0.0
    angles = []
    for line in lines[:, 0]:
        x1, y1, x2, y2 = line
        angle = np.degrees(np.arctan2((y2 - y1), (x2 - x1)))
        if abs(angle) < 20:
            angles.append(angle)
    if not angles:
        return 0.0
    return float(np.median(angles))


def preprocess_page(img: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoise = cv2.medianBlur(gray, 3)
    bin_img = cv2.adaptiveThreshold(denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 8)

    angle = _estimate_skew_angle(bin_img)
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)

    _, inv = cv2.threshold(rotated, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(inv)
    if coords is not None:
        x, y, bw, bh = cv2.boundingRect(coords)
        cropped = rotated[y : y + bh, x : x + bw]
        crop_box = [x, y, x + bw, y + bh]
    else:
        cropped = rotated
        crop_box = [0, 0, w, h]

    proc = cv2.cvtColor(cropped, cv2.COLOR_GRAY2BGR)
    return proc, {"deskew_angle": angle, "crop_box": crop_box}
