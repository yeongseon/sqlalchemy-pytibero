# Quick Start

This guide gets `sqlalchemy-pytibero` running quickly with both SQLAlchemy Core and ORM.

## Install

```bash
pip install sqlalchemy-pytibero
```

Optional: install with driver extra.

```bash
pip install "sqlalchemy-pytibero[pytibero]"
```

## Connection URL

Use the Tibero dialect name:

```text
tibero://user:pass@host:port/db
```

Defaults from `TiberoDialect.create_connect_args()`:

- `host`: `localhost`
- `port`: `8629`
- `user`: `tibero`
- `password`: empty string
- `database`: empty string

## SQLAlchemy Core example

```python
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select

engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB", echo=True)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), nullable=False),
)

metadata.create_all(engine)

with engine.begin() as conn:
    conn.execute(users.insert(), [{"name": "alice"}, {"name": "bob"}])

with engine.connect() as conn:
    rows = conn.execute(select(users.c.id, users.c.name)).all()
    for row in rows:
        print(row)
```

## SQLAlchemy ORM example

```python
from sqlalchemy import Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB")
Base.metadata.create_all(engine)

with Session(engine) as session:
    session.add(Account(name="first"))
    session.commit()

    account = session.scalar(select(Account).where(Account.name == "first"))
    account.name = "updated"
    session.commit()

    session.delete(account)
    session.commit()
```

## Async example

Install with async support:

```bash
pip install "sqlalchemy-pytibero[aioodbc]"
```

```python
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine("tibero+aioodbc://tibero:password@localhost:8629/TESTDB")
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1 FROM DUAL"))
        print(result.scalar())
    await engine.dispose()

asyncio.run(main())
```

## Architecture

```mermaid
flowchart LR
    app[Application Code] --> sa[SQLAlchemy Core / ORM]
    sa --> dialect[sqlalchemy-pytibero\nTiberoDialect]
    dialect --> dbapi[pytibero DB-API]
    dbapi --> tibero[Tibero Database]
```

!!! warning "Driver import error"
    `TiberoDialect.import_dbapi()` imports `pytibero` directly. If `pytibero` is missing, engine creation fails immediately.

!!! tip "Start simple"
    Validate connectivity first with `SELECT 1 FROM DUAL` before creating metadata and running migrations.

!!! note "No RETURNING support"
    `insert_returning`, `update_returning`, and `delete_returning` are disabled in this dialect. See [Limitations](limitations.md).
