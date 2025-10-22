.PHONY: help sync install test lint format clean docker-build docker-up docker-down run-api run-worker

help:
	@echo "Available commands:"
	@echo "  sync          Sync dependencies with uv"
	@echo "  install       Alias for sync (for compatibility)"
	@echo "  test          Run tests with coverage"
	@echo "  lint          Run linters (ruff, mypy)"
	@echo "  format        Format code with black and isort"
	@echo "  clean         Clean build artifacts and cache"
	@echo "  run-api       Run the API server (development)"
	@echo "  run-worker    Run the worker (development)"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-up     Start services with docker-compose"
	@echo "  docker-down   Stop services"

sync:
	uv sync

install: sync

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run black src/ tests/
	uv run isort src/ tests/
	uv run ruff check --fix src/ tests/

run-api:
	uv run uvicorn simple_ocr.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	uv run python -m simple_ocr.workers.nats_worker

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .venv/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t simple-ocr:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
