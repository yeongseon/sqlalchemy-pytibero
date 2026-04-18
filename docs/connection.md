# Connection Guide

This page documents how SQLAlchemy URLs are interpreted by `TiberoDialect.create_connect_args()` and how to configure engine/pool behavior.

## URL format

```text
tibero://user:password@host:port/database
```

Examples:

```python
from sqlalchemy import create_engine

engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB")
engine_defaulted = create_engine("tibero://@localhost/")  # user/port/database defaulting applied
```

## URL default values

When fields are omitted, the dialect applies:

| Field | Default |
|---|---|
| host | `localhost` |
| port | `8629` |
| user | `tibero` |
| password | `""` |
| database | `""` |

## `create_engine()` options

Common SQLAlchemy options for Tibero workloads:

```python
engine = create_engine(
    "tibero://tibero:password@db-host:8629/TESTDB",
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    isolation_level="READ COMMITTED",  # supported: READ COMMITTED, SERIALIZABLE
)
```

`TiberoDialect.on_connect()` sets `autocommit=False` for each new DB-API connection.

## Query parameters

`create_connect_args()` uses translated URL parts (`host`, `port`, `database`, `user`, `password`) and does not consume custom query-string parameters itself. SQLAlchemy-level options should usually be passed directly to `create_engine(...)`.

## Connection flow

```mermaid
flowchart TD
    u[SQLAlchemy URL] --> p[translate_connect_args]
    p --> d[TiberoDialect.create_connect_args]
    d --> k[kwargs: host/port/database/user/password]
    k --> drv[pytibero.connect(...)]
    drv --> c[on_connect: autocommit=False]
    c --> db[Tibero Session]
```

## Async connection (aioodbc)

Install the async extra:

```bash
pip install "sqlalchemy-pytibero[aioodbc]"
```

Use `create_async_engine` with the `tibero+aioodbc://` URL scheme:

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "tibero+aioodbc://tibero:password@localhost:8629/TESTDB",
    echo=True,
)

async with engine.begin() as conn:
    result = await conn.execute(text("SELECT 1 FROM DUAL"))
    print(result.scalar())
```

The async dialect builds an ODBC DSN string internally. You can override the ODBC driver name via the `driver` query parameter:

```text
tibero+aioodbc://user:pass@host:port/db?driver=Tibero%207%20ODBC%20Driver
```

!!! warning "Isolation level validation"
    `set_isolation_level()` only accepts `READ COMMITTED` and `SERIALIZABLE`. Any other value raises `ValueError`.

!!! note "Disconnect detection"
    `is_disconnect()` checks known message fragments and common Tibero/Oracle-like connection error codes for pool invalidation.

!!! tip "Use pool_pre_ping"
    For long-lived applications, `pool_pre_ping=True` helps recover stale connections by issuing a lightweight `SELECT 1 FROM DUAL` check.
