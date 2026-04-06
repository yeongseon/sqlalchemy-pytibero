# Development Guide

## Clone and setup

```bash
git clone https://github.com/yeongseon/sqlalchemy-pytibero.git
cd sqlalchemy-pytibero
python -m venv .venv
source .venv/bin/activate
```

## Install development dependencies

Defined in `pyproject.toml` under `[project.optional-dependencies].dev`:

- `pytest>=7.0`
- `pytest-cov`
- `ruff==0.15.6`

Install:

```bash
pip install -e .
pip install -e ".[dev,pytibero]"
```

## Run tests

```bash
pytest
```

Current test configuration:

- `testpaths = ["test"]`
- `collect_ignore_glob = ["test/oracle_compat/*"]`

There are currently no dedicated dialect-integration tests in this repository; `oracle_compat` tests are excluded.

## Lint and style

Ruff is configured with:

- line length: `100`
- target version: `py310`

Run lint checks:

```bash
ruff check .
```

## Contributing workflow

1. Create a feature branch.
2. Implement changes with focused commits.
3. Run `ruff check .` and `pytest`.
4. Update documentation when behavior changes.
5. Push branch and open a pull request.

## Development workflow diagram

```mermaid
flowchart LR
    fork[Branch from main/docs branch] --> code[Implement changes]
    code --> lint[ruff check .]
    lint --> test[pytest]
    test --> docs[Update docs]
    docs --> push[git push]
    push --> pr[Open PR]
```

!!! note "Target compatibility"
    Package metadata declares Python `>=3.10`.

!!! warning "Driver dependency"
    If you run integration-style checks, ensure `pytibero` is installed and a Tibero instance is reachable.
