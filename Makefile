.PHONY: run test lint guards docker-up

run:
	python -m streamlit run app/main.py

test:
	pytest tests/ -v

lint:
	ruff check cdss app tests && black --check cdss app tests

guards:
	python scripts/check_file_size.py cdss app
	python scripts/check_import_direction.py cdss
	python scripts/check_comment_length.py cdss app

docker-up:
	docker compose up --build
