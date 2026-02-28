from __future__ import annotations

from typing import Any


def build_audit_row(
    student_id: str,
    question_id: str,
    fused: dict[str, Any],
    ocr_result: dict[str, Any],
    mark_result: dict[str, Any],
    align_failed: int,
    roi_version: str,
    preprocess_version: str,
) -> dict[str, Any]:
    flags = dict(fused.get("flags", {}))
    flags["align_failed"] = int(align_failed)
    return {
        "student_id": student_id,
        "question_id": question_id,
        "pred_source": fused.get("pred_source", "fused"),
        "ocr_text_raw": ocr_result.get("ocr_text_raw", ""),
        "ocr_conf": float(ocr_result.get("ocr_conf", 0.0)),
        "mark_scores_json": str(mark_result.get("mark_scores", {})),
        "question_conf": float(fused.get("question_conf", 0.0)),
        "flags": str(flags),
        "roi_version": roi_version,
        "preprocess_version": preprocess_version,
    }
