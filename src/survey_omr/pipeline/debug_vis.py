from __future__ import annotations

from pathlib import Path

import cv2


def save_alignment_debug(path: Path, img) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])


def save_roi_overlay(path: Path, img, questions: list[dict]) -> None:
    vis = img.copy()
    for q in questions:
        box = q.get("rois", {}).get("answer_box")
        if box:
            x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(vis, q["id"], (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), vis)
