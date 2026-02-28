from __future__ import annotations

from typing import Any


def make_audit_row(
    student_id: str,
    question_id: str,
    pred_source: str,
    ocr_text_raw: str,
    ocr_conf: float,
    mark_scores: dict[str, float],
    question_conf: float,
    flags: dict[str, int],
    roi_version: str,
    preprocess_version: str,
) -> dict[str, Any]:
    """Build normalized audit row."""
    return {
        "student_id": student_id,
        "question_id": question_id,
        "pred_source": pred_source,
        "ocr_text_raw": ocr_text_raw,
        "ocr_conf": round(float(ocr_conf), 4),
        "mark_scores_json": {k: round(float(v), 4) for k, v in mark_scores.items()},
        "question_conf": round(float(question_conf), 4),
        "flags": flags,
        "roi_version": roi_version,
        "preprocess_version": preprocess_version,
    }
