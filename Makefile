.PHONY: install test build-template extract review-ui

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest -q

build-template:
	python -m survey_omr.cli build-template --pdf data/all_students.pdf --out-dir outputs/templates --schema-out outputs/schema.yaml

extract:
	python -m survey_omr.cli extract --pdf data/all_students.pdf --schema outputs/schema.yaml --out outputs/result.xlsx

review-ui:
	python -m survey_omr.cli review-ui --run-dir $${RUN_DIR}
