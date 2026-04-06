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

!!! warning "Isolation level validation"
    `set_isolation_level()` only accepts `READ COMMITTED` and `SERIALIZABLE`. Any other value raises `ValueError`.

!!! note "Disconnect detection"
    `is_disconnect()` checks known message fragments and common Tibero/Oracle-like connection error codes for pool invalidation.

!!! tip "Use pool_pre_ping"
    For long-lived applications, `pool_pre_ping=True` helps recover stale connections by issuing a lightweight `SELECT 1 FROM DUAL` check.
