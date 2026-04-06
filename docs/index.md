# sqlalchemy-pytibero

[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-pytibero)](https://pypi.org/project/sqlalchemy-pytibero/)
[![Python](https://img.shields.io/pypi/pyversions/sqlalchemy-pytibero)](https://pypi.org/project/sqlalchemy-pytibero/)
[![License](https://img.shields.io/pypi/l/sqlalchemy-pytibero)](https://github.com/yeongseon/sqlalchemy-pytibero/blob/main/LICENSE)

`sqlalchemy-pytibero` is a SQLAlchemy 2.0 dialect for Tibero built on top of the `pytibero` DB-API driver. It provides SQL compilation, schema reflection, Tibero-specific type handling, and dialect integration for both Core and ORM usage.

## Why this project

- Registers the `tibero` SQLAlchemy dialect and `tibero.pytibero` driver name.
- Provides Tibero-aware SQL and DDL compilers.
- Maps Tibero column metadata to SQLAlchemy types for reflection.
- Supports Tibero-compatible schema comments and identity columns.
- Keeps the integration lightweight while following SQLAlchemy conventions.

## Quick install

```bash
pip install sqlalchemy-pytibero
pip install "sqlalchemy-pytibero[pytibero]"
```

## Quick usage

```python
from sqlalchemy import create_engine, text

engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB")
with engine.connect() as conn:
    print(conn.execute(text("SELECT 1 FROM DUAL")).scalar())
```

## Architecture

```mermaid
flowchart TD
    app["Application"] --> sa["SQLAlchemy Core/ORM"]
    sa --> dialect["TiberoDialect"]
    dialect --> compiler["SQL/DDL/Type Compilers"]
    dialect --> dbapi["pytibero"]
    compiler --> sql["Tibero SQL"]
    dbapi --> server["Tibero Server"]
    sql --> server
```

## Documentation map

### Getting Started

- [Quick Start](quickstart.md)
- [Connection Guide](connection.md)

### User Guide

- [Dialect Features](dialect-features.md)
- [Type Mapping](types.md)
- [Schema Reflection](reflection.md)
- [DDL Generation](ddl.md)
- [Limitations](limitations.md)

### Reference and Development

- [API Reference](api-reference.md)
- [Development Guide](development.md)

## Project links

- GitHub: https://github.com/yeongseon/sqlalchemy-pytibero
- PyPI: https://pypi.org/project/sqlalchemy-pytibero/
