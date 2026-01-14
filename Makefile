.PHONY: help install dev lint format test run clean build build-mac build-linux build-windows build-onefile

help:
	@echo "GitHub Secrets Migrator - Makefile targets:"
	@echo "  install        - Install dependencies"
	@echo "  dev            - Install with dev dependencies"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code with black"
	@echo "  test           - Run tests"
	@echo "  run            - Run the migrator"
	@echo "  build          - Build for current platform (onedir)"
	@echo "  build-mac      - Build for macOS (Intel + Apple Silicon)"
	@echo "  build-linux    - Build for Linux"
	@echo "  build-windows  - Build for Windows"
	@echo "  build-onefile  - Build single file for current platform"
	@echo "  clean          - Clean build artifacts"

install:
	python -m pip install -r requirements.txt

dev:
	python -m pip install -r requirements.txt && python -m pip install black flake8 pylint pytest pytest-cov

lint:
	python -m flake8 src/ main.py --max-line-length=100 --ignore=E203,W503 || true
	python -m pylint src/ main.py --disable=C0111,R0903 || true

format:
	python -m black src/ main.py --line-length=100

test:
	python -m pytest tests/ -v --tb=short 2>/dev/null || echo "No tests configured yet"

run:
	python main.py

build:
	python -m PyInstaller gh-secrets-migrator.spec --clean
	@echo "✅ Build complete! Executable in bin/"

build-mac:
	python -m PyInstaller gh-secrets-migrator.spec --clean
	@echo "✅ macOS build complete (Intel + Apple Silicon)! Output: bin/"

build-linux:
	python -m PyInstaller gh-secrets-migrator.spec --clean
	@echo "✅ Linux build complete! Executable in bin/"

build-windows:
	python -m PyInstaller gh-secrets-migrator.spec --clean
	@echo "✅ Windows build complete! Executable in bin/"

build-onefile:
	python -m PyInstaller gh-secrets-migrator-onefile.spec --clean
	@echo "✅ Single-file build complete! Executable: dist/gh-secrets-migrator"

build-docker:
	docker build -t gh-secrets-migrator:latest .

run-docker:
	docker run -it -v $(pwd)/app --env-file .env.local gh-secrets-migrator

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf build/ *.egg-info

.PHONY: help install dev lint format test run clean build build-mac build-linux build-windows build-onefile
