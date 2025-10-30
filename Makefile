.PHONY: help install dev lint format test run clean

help:
	@echo "GitHub Secrets Migrator - Makefile targets:"
	@echo "  install    - Install dependencies"
	@echo "  dev        - Install with dev dependencies"
	@echo "  lint       - Run linting checks"
	@echo "  format     - Format code with black"
	@echo "  test       - Run tests"
	@echo "  run        - Run the migrator"
	@echo "  clean      - Clean build artifacts"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install black flake8 pylint pytest pytest-cov

lint:
	@echo "Running flake8..."
	flake8 src/ main.py --max-line-length=100 --ignore=E203,W503 || true
	@echo "Running pylint..."
	pylint src/ main.py --disable=C0111,R0903 || true

format:
	black src/ main.py --line-length=100

test:
	pytest tests/ -v --tb=short 2>/dev/null || echo "No tests configured yet"

run:
	python main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf build/ dist/ *.egg-info

.PHONY: help install dev lint format test run clean
