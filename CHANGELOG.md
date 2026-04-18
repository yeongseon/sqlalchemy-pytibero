# Changelog

## Unreleased

- Added `aioodbc` async dialect (`tibero+aioodbc://`) using SQLAlchemy's built-in `aiodbcConnector` (#14)

## 0.2.0

- Improved `_resolve_column_type` to use regex-based type parsing for parameterized types
- Added `_normalize_default` to strip vendor quoting from column defaults
- Added Alembic migration support (`alembic_impl.py` + entry point registration)
- Extended type mapping: `TIMESTAMP WITH TIME ZONE`, `TIMESTAMP WITH LOCAL TIME ZONE`, `LONG VARCHAR`

## 0.1.0

- Initial SQLAlchemy 2.0 dialect for Tibero backed by `pytibero`
