from survey_omr.pipeline.roi import parse_questions


def test_schema_parse_basic():
    schema = {
        "questions": [
            {
                "id": "Q1",
                "page": 1,
                "type": "single",
                "options": ["A", "B", "C", "D"],
                "rois": {
                    "answer_box": [1, 2, 3, 4],
                    "option_boxes": {"A": [1, 1, 2, 2], "B": [2, 2, 3, 3], "C": [3, 3, 4, 4], "D": [4, 4, 5, 5]},
                },
            }
        ]
    }
    qs = parse_questions(schema)
    assert len(qs) == 1
    assert qs[0].question_id == "Q1"
    assert qs[0].option_boxes["A"] == (1, 1, 2, 2)
