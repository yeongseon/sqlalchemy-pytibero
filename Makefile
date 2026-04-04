PYTEST = python3 -m pytest
RUFF = ruff
SRC = sqlalchemy_pytibero
TESTS = test

lint:
	$(RUFF) check $(SRC)/ $(TESTS)/
	$(RUFF) format --check $(SRC)/ $(TESTS)/

format:
	$(RUFF) check --fix $(SRC)/ $(TESTS)/
	$(RUFF) format $(SRC)/ $(TESTS)/

test:
	$(PYTEST) $(TESTS)/ -v \
		--cov=$(SRC) \
		--cov-report=term-missing \
		--cov-fail-under=95

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
