from __future__ import annotations

import re
from typing import Any

import cv2
import numpy as np

ALLOWED = {"A", "B", "C", "D", "E", "F", "OTH"}


def _clean_letters(text: str) -> set[str]:
    tokens = re.split(r"[\s,，、/;；]+", text.upper())
    out: set[str] = set()
    for t in tokens:
        if t in ALLOWED:
            out.add(t)
        elif len(t) > 1:
            out.update(ch for ch in t if ch in ALLOWED)
    return out


def recognize_letters(roi: np.ndarray, engine: str = "off") -> dict[str, Any]:
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    proc = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 5)

    if engine == "off":
        return {"letters_pred": set(), "ocr_text_raw": "", "ocr_conf": 0.0}

    text = ""
    conf = 0.0
    if engine == "paddle":
        try:
            from paddleocr import PaddleOCR

            ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            result = ocr.ocr(proc, cls=False)
            chunks = []
            confs = []
            for line in result or []:
                for _, (t, c) in line:
                    chunks.append(t)
                    confs.append(float(c))
            text = " ".join(chunks)
            conf = float(np.mean(confs)) if confs else 0.0
        except Exception:
            text, conf = "", 0.0
    elif engine == "tesseract":
        try:
            import pytesseract

            cfg = "--psm 7 -c tessedit_char_whitelist=ABCDEF,/;，、 "
            text = pytesseract.image_to_string(proc, config=cfg)
            conf = 0.55 if text.strip() else 0.0
        except Exception:
            text, conf = "", 0.0

    return {"letters_pred": _clean_letters(text), "ocr_text_raw": text, "ocr_conf": conf}
