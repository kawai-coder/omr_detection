@echo off
python -m survey_omr.cli extract --pdf data/all_students.pdf --schema outputs/schema.yaml --out outputs/result.xlsx --workers 4 --ocr off
