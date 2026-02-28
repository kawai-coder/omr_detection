from survey_omr.pipeline.fuse import fuse_predictions


def test_fuse_prefers_ocr_when_confident():
    out = fuse_predictions(
        options=["A", "B", "C", "D"],
        qtype="single",
        ocr_letters={"B"},
        ocr_conf=0.95,
        mark_scores={"A": 0.2, "B": 0.1, "C": 0.05, "D": 0.02},
        ocr_threshold=0.6,
        mark_threshold=0.18,
    )
    assert out.selected == {"B"}


def test_single_ambiguous_flag():
    out = fuse_predictions(
        options=["A", "B", "C", "D"],
        qtype="single",
        ocr_letters=set(),
        ocr_conf=0.0,
        mark_scores={"A": 0.3, "B": 0.4, "C": 0.01, "D": 0.02},
        ocr_threshold=0.6,
        mark_threshold=0.18,
    )
    assert out.flags["ambiguous"] == 1
