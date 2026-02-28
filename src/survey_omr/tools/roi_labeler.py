from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2

from survey_omr.utils.io import read_yaml, write_yaml


def run_roi_labeler(schema_path: Path) -> None:
    schema = read_yaml(schema_path)
    questions = schema.get("questions", [])
    idx = 0
    mode = "answer_box"
    drag = {"start": None, "end": None}

    def current_image() -> tuple[str, Any]:
        q = questions[idx]
        page = f"page{q['page']}"
        img = cv2.imread(schema["pages"][page]["template_path"])
        return page, img

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            drag["start"] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and drag["start"] is not None:
            drag["end"] = (x, y)
            x1, y1 = drag["start"]
            x2, y2 = drag["end"]
            box = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
            q = questions[idx]
            q.setdefault("rois", {}).setdefault("option_boxes", {})
            if mode == "answer_box":
                q["rois"]["answer_box"] = box
            else:
                q["rois"]["option_boxes"][mode] = box
            drag["start"] = None

    cv2.namedWindow("roi")
    cv2.setMouseCallback("roi", on_mouse)

    while True:
        _, img = current_image()
        q = questions[idx]
        cv2.putText(img, f"{q['id']} mode={mode}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        for name, b in q.get("rois", {}).get("option_boxes", {}).items():
            cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (255, 0, 0), 2)
            cv2.putText(img, name, (b[0], b[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        ab = q.get("rois", {}).get("answer_box")
        if ab:
            cv2.rectangle(img, (ab[0], ab[1]), (ab[2], ab[3]), (0, 255, 0), 2)

        cv2.imshow("roi", img)
        k = cv2.waitKey(30) & 0xFF
        if k == ord("q"):
            break
        if k == ord("s"):
            write_yaml(schema_path, schema)
        if k == ord("n"):
            idx = min(len(questions) - 1, idx + 1)
        if k == ord("p"):
            idx = max(0, idx - 1)
        if k == ord("c") and idx > 0:
            questions[idx]["rois"] = questions[idx - 1].get("rois", {}).copy()
        if k == 9:  # tab
            opts = ["answer_box"] + questions[idx].get("options", ["A", "B", "C", "D"])
            mode = opts[(opts.index(mode) + 1) % len(opts)] if mode in opts else opts[0]

    write_yaml(schema_path, schema)
    cv2.destroyAllWindows()
