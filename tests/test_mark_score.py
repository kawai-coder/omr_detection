import numpy as np

from survey_omr.pipeline.detect_marks import score_mark


def test_mark_score_detects_fill():
    img = np.full((50, 50), 255, dtype=np.uint8)
    img[10:40, 10:40] = 0
    out = score_mark(img, threshold=0.18)
    assert out.marked is True
    assert out.score > 0.18
