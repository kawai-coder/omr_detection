from __future__ import annotations

from typing import Any


def fuse_prediction(
    qtype: str,
    options: list[str],
    ocr_result: dict[str, Any],
    mark_result: dict[str, Any],
    ocr_threshold: float,
    mark_threshold: float,
    margin: float = 0.03,
) -> dict[str, Any]:
    letters = set(ocr_result.get("letters_pred", set())) & set(options)
    ocr_conf = float(ocr_result.get("ocr_conf", 0.0))
    marks = set(mark_result.get("marks_pred", set())) & set(options)
    scores = {k: float(v) for k, v in mark_result.get("mark_scores", {}).items()}

    pred_source = "mark"
    pred = marks
    conflict = 0
    low_conf = 0
    ambiguous = 0
    missing = 0

    if ocr_conf >= ocr_threshold and letters:
        pred = letters
        pred_source = "OCR"
        if marks and marks != letters:
            conflict = 1

    if not pred:
        missing = 1
        low_conf = 1

    if qtype == "single" and len(pred) > 1:
        ambiguous = 1

    near = [abs(scores.get(o, 0.0) - mark_threshold) for o in options]
    if near and min(near) < margin:
        low_conf = 1

    option_conf = {}
    for o in options:
        if pred_source == "OCR":
            option_conf[o] = ocr_conf if o in pred else 1 - ocr_conf
        else:
            option_conf[o] = scores.get(o, 0.0)

    q_conf = sum(option_conf.values()) / max(1, len(option_conf))
    penalty = 0.0
    penalty += 0.2 if conflict else 0.0
    penalty += 0.2 if ambiguous else 0.0
    penalty += 0.2 if missing else 0.0
    penalty += 0.15 if low_conf else 0.0
    question_conf = max(0.0, min(1.0, q_conf - penalty))

    return {
        "pred": sorted(pred),
        "pred_source": pred_source,
        "option_conf": option_conf,
        "question_conf": question_conf,
        "flags": {
            "conflict": conflict,
            "ambiguous": ambiguous,
            "missing": missing,
            "low_conf": low_conf,
        },
    }
