# sqlalchemy-pytibero

[![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-pytibero)](https://pypi.org/project/sqlalchemy-pytibero)
[![CI](https://github.com/yeongseon/sqlalchemy-pytibero/actions/workflows/ci.yml/badge.svg)](https://github.com/yeongseon/sqlalchemy-pytibero/actions/workflows/ci.yml)
[![license](https://img.shields.io/github/license/yeongseon/sqlalchemy-pytibero)](https://github.com/yeongseon/sqlalchemy-pytibero/blob/main/LICENSE)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://yeongseon.github.io/sqlalchemy-pytibero/)

SQLAlchemy 2.0 dialect for the Tibero database, backed by `pytibero`.

## Installation

```bash
pip install sqlalchemy-pytibero
```

With DB-API dependency:

```bash
pip install "sqlalchemy-pytibero[pytibero]"
```

## Quick Start

```python
from sqlalchemy import create_engine, text

engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB")

with engine.connect() as conn:
    value = conn.execute(text("SELECT 1 FROM DUAL")).scalar()
    print(value)
```

## Alembic Support

This dialect includes an Alembic implementation. After installing, Alembic
migrations work out of the box:

```ini
# alembic.ini
sqlalchemy.url = tibero://tibero:password@localhost:8629/TESTDB
```

```bash
alembic upgrade head
```

Note: Tibero DDL is auto-committed, so `transactional_ddl = False`.

## Architecture

```mermaid
flowchart TD
    app["Application"] --> sa["SQLAlchemy Core/ORM"]
    sa --> dialect["TiberoDialect"]
    dialect --> dbapi["pytibero"]
    dbapi --> server["Tibero Server"]
```

## Development

```bash
make lint
make test
```

## License

MIT
