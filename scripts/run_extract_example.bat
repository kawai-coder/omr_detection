@echo off
python -m survey_omr.cli extract --pdf data/all_students.pdf --schema outputs/schema.yaml --out outputs/问卷识别结果.xlsx --workers 4 --ocr paddle --ocr-threshold 0.6 --mark-threshold 0.18
