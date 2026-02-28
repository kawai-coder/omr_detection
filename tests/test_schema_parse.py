from pathlib import Path

from survey_omr.utils.io import read_yaml


def test_schema_parse() -> None:
    schema = read_yaml(Path("src/survey_omr/config/schema.example.yaml"))
    assert schema["meta"]["pages_per_student"] == 2
    assert len(schema["questions"]) >= 1
