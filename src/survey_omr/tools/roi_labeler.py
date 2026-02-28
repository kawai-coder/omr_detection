from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from survey_omr.utils.io import dump_yaml, load_yaml


@dataclass
class DragState:
    drawing: bool = False
    start: tuple[int, int] = (0, 0)
    end: tuple[int, int] = (0, 0)


def run_labeler(schema_path: Path) -> None:
    """OpenCV-based ROI labeler for answer_box and option boxes."""
    schema = load_yaml(schema_path)
    questions = schema.get("questions", [])
    if not questions:
        raise ValueError("schema.questions is empty")

    page_templates = {
        1: schema["pages"]["page1"]["template_path"],
        2: schema["pages"]["page2"]["template_path"],
    }

    idx = 0
    mode = "answer_box"
    state = DragState()

    def mouse_cb(event, x, y, *_):
        nonlocal state
        if event == cv2.EVENT_LBUTTONDOWN:
            state.drawing = True
            state.start = (x, y)
            state.end = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and state.drawing:
            state.end = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            state.drawing = False
            state.end = (x, y)

    while True:
        q = questions[idx]
        page = int(q["page"])
        img = cv2.imread(page_templates[page])
        show = img.copy()
        cv2.putText(show, f"Q:{q['id']} mode:{mode} [n/p next] [a answer] [o option] [c copy prev] [s save]", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 200), 1)

        if state.start != state.end:
            cv2.rectangle(show, state.start, state.end, (0, 255, 0), 2)

        win = "ROI Labeler"
        cv2.namedWindow(win)
        cv2.setMouseCallback(win, mouse_cb)
        cv2.imshow(win, show)
        key = cv2.waitKey(50) & 0xFF

        if key == ord("q"):
            break
        if key == ord("a"):
            mode = "answer_box"
        if key == ord("o"):
            mode = "option"
        if key == ord("n"):
            idx = min(len(questions) - 1, idx + 1)
            state = DragState()
        if key == ord("p"):
            idx = max(0, idx - 1)
            state = DragState()
        if key == ord("c") and idx > 0:
            questions[idx]["rois"] = questions[idx - 1].get("rois", {}).copy()
        if key == ord("1") and mode == "option":
            _set_option(q, "A", state)
        if key == ord("2") and mode == "option":
            _set_option(q, "B", state)
        if key == ord("3") and mode == "option":
            _set_option(q, "C", state)
        if key == ord("4") and mode == "option":
            _set_option(q, "D", state)
        if key == ord("5") and mode == "option":
            _set_option(q, "E", state)
        if key == ord("6") and mode == "option":
            _set_option(q, "F", state)
        if key == 13:
            _set_answer(q, state)
        if key == ord("s"):
            schema["questions"] = questions
            dump_yaml(schema_path, schema)
            print(f"Saved schema to {schema_path}")

    cv2.destroyAllWindows()


def _box(state: DragState) -> list[int]:
    x1, y1 = state.start
    x2, y2 = state.end
    return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]


def _set_answer(q: dict[str, Any], state: DragState) -> None:
    q.setdefault("rois", {})["answer_box"] = _box(state)


def _set_option(q: dict[str, Any], opt: str, state: DragState) -> None:
    q.setdefault("rois", {}).setdefault("option_boxes", {})[opt] = _box(state)
