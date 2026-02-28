from survey_omr.pipeline.fuse import fuse_prediction


def test_fuse_ocr_priority() -> None:
    out = fuse_prediction(
        "single",
        ["A", "B", "C", "D"],
        {"letters_pred": {"B"}, "ocr_conf": 0.9},
        {"marks_pred": {"A"}, "mark_scores": {"A": 0.8, "B": 0.1, "C": 0.0, "D": 0.0}},
        0.65,
        0.18,
    )
    assert out["pred"] == ["B"]
    assert out["flags"]["conflict"] == 1
