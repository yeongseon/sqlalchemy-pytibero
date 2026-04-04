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

.PHONY: lint format test clean check-e2e-env test-e2e-docker test-oracle-compat clean-oracle-compat

check-e2e-env:
	@if [ -z "$$TIBERO_LICENSE_FILE" ]; then \
		echo "TIBERO_LICENSE_FILE is required."; \
		echo "Example: export TIBERO_LICENSE_FILE=/abs/path/to/license.xml"; \
		exit 1; \
	fi
	@if [ ! -f "$$TIBERO_LICENSE_FILE" ]; then \
		echo "TIBERO_LICENSE_FILE does not point to an existing file: $$TIBERO_LICENSE_FILE"; \
		exit 1; \
	fi

test-e2e-docker: check-e2e-env
	docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from e2e

test-oracle-compat:
	docker compose -f docker-compose.oracle-compat.yml up --build --abort-on-container-exit --exit-code-from oracle-compat

clean-oracle-compat:
	docker compose -f docker-compose.oracle-compat.yml down -v --remove-orphans

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
