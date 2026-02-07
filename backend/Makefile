.PHONY: install dev test lint typecheck run clean

# ─── Setup ──────────────────────────────────────────────────
install:
	pip install -e .

dev:
	pip install -e ".[dev,db,ml]"

# ─── Quality ────────────────────────────────────────────────
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck:
	mypy src/medai/

# ─── Test ───────────────────────────────────────────────────
test:
	pytest -m unit -v --tb=short

test-all:
	pytest -v --tb=short

test-cov:
	pytest -m unit --cov=src/medai --cov-report=term-missing -v

# ─── Run ────────────────────────────────────────────────────
run:
	uvicorn medai.main:app --host 0.0.0.0 --port 8000 --reload

# ─── Clean ──────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf .coverage htmlcov/ dist/ *.egg-info
