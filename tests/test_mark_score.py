import numpy as np

from survey_omr.pipeline.detect_marks import score_mark


def test_mark_score_higher_when_filled() -> None:
    blank = np.full((60, 60, 3), 255, dtype=np.uint8)
    filled = blank.copy()
    filled[10:50, 10:50, :] = 0
    assert score_mark(filled) > score_mark(blank)
