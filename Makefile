.PHONY: setup test lint format

BACKEND := cd backend &&

setup:
	$(BACKEND) uv sync

test:
	$(BACKEND) uv run pytest -m "not perf" --cov=antegraph --cov-report=term-missing

lint:
	$(BACKEND) uv run ruff check . && uv run ruff format --check . && uv run mypy

format:
	$(BACKEND) uv run ruff format . && uv run ruff check --fix .
