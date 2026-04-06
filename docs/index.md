# sqlalchemy-pytibero

SQLAlchemy 2.0 dialect for the Tibero database, backed by `pytibero`.

## Key features

- Native SQLAlchemy 2.0 dialect integration for Tibero.
- DB-API connectivity powered by `pytibero`.
- Lightweight base installation for flexible dependency management.
- Optional extras install for bundled DB-API setup.

## Quick install

```bash
pip install sqlalchemy-pytibero
pip install "sqlalchemy-pytibero[pytibero]"
```

## Minimal example

```python
from sqlalchemy import create_engine, text
engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB")
with engine.connect() as conn:
    value = conn.execute(text("SELECT 1 FROM DUAL")).scalar()
    print(value)
```

## Architecture

```mermaid
flowchart TD
    app["Application"] --> sa["SQLAlchemy Core/ORM"]
    sa --> dialect["TiberoDialect"]
    dialect --> dbapi["pytibero"]
    dbapi --> server["Tibero Server"]
```

## Project links

- GitHub: https://github.com/yeongseon/sqlalchemy-pytibero
- PyPI: https://pypi.org/project/sqlalchemy-pytibero/
