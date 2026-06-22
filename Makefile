VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: setup run test lint guards docker-up

setup:
	./scripts/setup.sh

run: setup
	./scripts/run.sh

test: setup
	$(PYTHON) -m pytest tests/ -v

lint: setup
	$(VENV)/bin/ruff check cdss app tests && $(VENV)/bin/black --check cdss app tests

guards: setup
	$(PYTHON) scripts/check_file_size.py cdss app
	$(PYTHON) scripts/check_import_direction.py cdss
	$(PYTHON) scripts/check_comment_length.py cdss app

docker-up:
	docker compose up --build
