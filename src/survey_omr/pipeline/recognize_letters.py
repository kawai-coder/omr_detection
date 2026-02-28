from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

_ALLOWED = {"A", "B", "C", "D", "E", "F", "OTH"}


@dataclass
class OCRResult:
    letters_pred: set[str]
    ocr_text_raw: str
    ocr_conf: float


def _normalize_letters(text: str) -> set[str]:
    tokens = re.split(r"[\s,，、/;；|]+", text.upper())
    out = set()
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in _ALLOWED:
            out.add(t)
        elif len(t) > 1 and all(ch in _ALLOWED for ch in t):
            out.update(list(t))
    return out


def _prep(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    g = cv2.GaussianBlur(g, (3, 3), 0)
    return cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def recognize_letters(img: np.ndarray, backend: str = "paddle") -> OCRResult:
    """Recognize handwritten letters from answer box with optional OCR backend."""
    proc = _prep(img)
    if backend == "off":
        return OCRResult(set(), "", 0.0)

    if backend == "paddle":
        try:
            from paddleocr import PaddleOCR

            ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            result = ocr.ocr(proc, cls=False)
            texts, confs = [], []
            for line in result or []:
                for seg in line:
                    texts.append(seg[1][0])
                    confs.append(float(seg[1][1]))
            raw = " ".join(texts).strip()
            conf = float(np.mean(confs)) if confs else 0.0
            return OCRResult(_normalize_letters(raw), raw, conf)
        except Exception:
            backend = "tesseract"

    if backend == "tesseract":
        try:
            import pytesseract

            cfg = "--psm 7 -c tessedit_char_whitelist=ABCDEFabcdef,;/，、 "
            raw = pytesseract.image_to_string(proc, config=cfg)
            return OCRResult(_normalize_letters(raw), raw.strip(), 0.55 if raw.strip() else 0.0)
        except Exception:
            pass

    return OCRResult(set(), "", 0.0)
