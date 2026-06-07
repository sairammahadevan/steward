.PHONY: dev run test lint clean

dev:
	pip install -e ".[dev]" --break-system-packages

run:
	bash run.sh

test:
	pytest -v

lint:
	ruff check src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f steward.db
