.PHONY: test lint type format install clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

test-cov:
	pytest --cov --cov-report=term-missing

lint:
	ruff check .

type:
	mypy services data

format:
	ruff format .
	ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov

all: lint type test
