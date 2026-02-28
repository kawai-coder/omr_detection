from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FusedQuestion:
    selected: set[str]
    pred_source: str
    option_conf: dict[str, float]
    question_conf: float
    flags: dict[str, int]


def fuse_predictions(
    options: list[str],
    qtype: str,
    ocr_letters: set[str],
    ocr_conf: float,
    mark_scores: dict[str, float],
    ocr_threshold: float,
    mark_threshold: float,
    margin: float = 0.03,
    align_failed: bool = False,
) -> FusedQuestion:
    """Fuse OCR + mark predictions with conflict-aware confidence scoring."""
    marks_pred = {k for k, v in mark_scores.items() if v >= mark_threshold}
    use_ocr = ocr_conf >= ocr_threshold and len(ocr_letters) > 0
    selected = set(o for o in (ocr_letters if use_ocr else marks_pred) if o in options)
    pred_source = "OCR" if use_ocr else "mark"

    flags = {"conflict": 0, "ambiguous": 0, "missing": 0, "align_failed": int(align_failed), "low_conf": 0}
    if use_ocr and marks_pred and selected.symmetric_difference(marks_pred):
        flags["conflict"] = 1

    if qtype == "single" and len(selected) > 1:
        flags["ambiguous"] = 1
    if not selected:
        flags["missing"] = 1

    near = any(abs(v - mark_threshold) <= margin for v in mark_scores.values())
    if near or (use_ocr and ocr_conf < min(0.9, ocr_threshold + 0.1)):
        flags["low_conf"] = 1

    option_conf = {o: float(mark_scores.get(o, 0.0)) for o in options}
    if use_ocr:
        for o in options:
            if o in ocr_letters:
                option_conf[o] = max(option_conf[o], ocr_conf)

    q_conf = float(sum(option_conf.values()) / max(1, len(option_conf)))
    penalties = 0.15 * flags["conflict"] + 0.2 * flags["ambiguous"] + 0.15 * flags["missing"] + 0.35 * flags["align_failed"] + 0.1 * flags["low_conf"]
    q_conf = max(0.0, min(1.0, q_conf - penalties))
    return FusedQuestion(selected=selected, pred_source="fused" if use_ocr and marks_pred else pred_source, option_conf=option_conf, question_conf=q_conf, flags=flags)
