PYTHON ?= python

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e .[dev]

build-template:
	$(PYTHON) -m survey_omr.cli build-template --pdf data/all_students.pdf --out-dir outputs/templates

label-roi:
	$(PYTHON) -m survey_omr.cli label-roi --schema outputs/schema.yaml

extract:
	$(PYTHON) -m survey_omr.cli extract --pdf data/all_students.pdf --schema outputs/schema.yaml --out outputs/问卷识别结果.xlsx

review-ui:
	$(PYTHON) -m survey_omr.cli review-ui --run-dir $$(ls -dt outputs/run_* | head -1)

test:
	pytest -q
