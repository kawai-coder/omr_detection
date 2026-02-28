from __future__ import annotations

from pathlib import Path

import cv2

from survey_omr.pipeline.roi import QuestionROI, draw_rois
from survey_omr.utils.io import ensure_dir


def save_aligned_debug(path: Path, image) -> None:
    ensure_dir(path.parent)
    cv2.imwrite(str(path), image)


def save_roi_overlay(path: Path, image, questions: list[QuestionROI], page: int) -> None:
    ensure_dir(path.parent)
    vis = draw_rois(image, questions, page)
    cv2.imwrite(str(path), vis)
