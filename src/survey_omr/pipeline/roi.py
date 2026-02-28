from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from survey_omr.utils.geometry import clip_roi


@dataclass
class QuestionROI:
    question_id: str
    page: int
    qtype: str
    options: list[str]
    answer_box: tuple[int, int, int, int]
    option_boxes: dict[str, tuple[int, int, int, int]]


def parse_questions(schema: dict[str, Any]) -> list[QuestionROI]:
    """Parse question definitions from schema dict."""
    questions: list[QuestionROI] = []
    for q in schema.get("questions", []):
        questions.append(
            QuestionROI(
                question_id=q["id"],
                page=int(q["page"]),
                qtype=q.get("type", "single"),
                options=list(q.get("options", ["A", "B", "C", "D"])),
                answer_box=tuple(q["rois"]["answer_box"]),
                option_boxes={k: tuple(v) for k, v in q["rois"]["option_boxes"].items()},
            )
        )
    return questions


def crop_roi(image: np.ndarray, roi: tuple[int, int, int, int]) -> np.ndarray:
    """Crop clipped ROI image."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = clip_roi(roi, w, h)
    return image[y1:y2, x1:x2]


def draw_rois(image: np.ndarray, questions: list[QuestionROI], page: int) -> np.ndarray:
    """Draw all question ROI rectangles for a page."""
    vis = image.copy()
    for q in questions:
        if q.page != page:
            continue
        x1, y1, x2, y2 = q.answer_box
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 180, 0), 2)
        cv2.putText(vis, q.question_id, (x1, max(10, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 0), 1)
        for opt, ob in q.option_boxes.items():
            ox1, oy1, ox2, oy2 = ob
            cv2.rectangle(vis, (ox1, oy1), (ox2, oy2), (180, 0, 0), 1)
            cv2.putText(vis, opt, (ox1, oy1 + 10), cv2.FONT_HERSHEY_PLAIN, 0.8, (180, 0, 0), 1)
    return vis
