# Schema Reflection

`TiberoDialect` implements a broad set of SQLAlchemy reflection hooks against Tibero system views.

## Schema normalization

- Effective schema is derived by `_effective_schema(connection, schema)`.
- If `schema` is provided, uppercase is used.
- If omitted, current schema is read with:

```sql
SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL
```

The dialect also enables SQLAlchemy name normalization (`requires_name_normalize = True`).

## Table and view reflection

### `get_table_names(connection, schema=None, **kw)`

- With schema: reads `all_tables`
- Without schema: reads `user_tables`

### `get_view_names(connection, schema=None, **kw)`

Reads `all_views` for the effective schema.

### `get_view_definition(connection, view_name, schema=None, **kw)`

Returns `text` from `all_views` for one view, or `None`.

### `get_table_comment(connection, table_name, schema=None, **kw)`

Returns `{ "text": <comment-or-None> }` from `all_tab_comments`.

## Column reflection

### `get_columns(connection, table_name, schema=None, **kw)`

Reads:

- `column_name`
- `data_type`
- `data_length`
- `data_precision`
- `data_scale`
- `nullable`
- `data_default`

Type resolution is delegated to `_resolve_column_type(...)` using `ischema_names`. Parameterized types
like `VARCHAR2(100)` or `NUMBER(10,2)` are parsed via regex to extract base type and precision/scale.

Column defaults are normalized by `_normalize_default()` which strips vendor-specific quoting
(e.g., `'value'` → `value`, `NULL` → `None`).

Example:

```python
from sqlalchemy import create_engine, inspect

engine = create_engine("tibero://tibero:password@localhost:8629/TESTDB")
insp = inspect(engine)
print(insp.get_columns("USERS"))
```

## Constraint and index reflection

### Primary key

`get_pk_constraint(connection, table_name, schema=None, **kw)` returns:

```python
{"name": "PK_USERS", "constrained_columns": ["ID"]}
```

### Foreign keys

`get_foreign_keys(connection, table_name, schema=None, **kw)` groups rows by constraint name and returns constrained/referred columns in order.

### Indexes

`get_indexes(connection, table_name, schema=None, **kw)` returns dictionaries with:

- `name`
- `column_names`
- `unique`

### Unique constraints

`get_unique_constraints(connection, table_name, schema=None, **kw)` returns named column groups.

### Check constraints

`get_check_constraints(connection, table_name, schema=None, **kw)` returns non-null check SQL text.

## Sequence reflection

### `has_sequence(connection, sequence_name, schema=None, **kw)`

Implemented via `all_sequences` count lookup.

### `get_sequence_names()` and `get_sequence_range()`

These methods are not overridden in this dialect module. If your workflow depends on them, use explicit SQL against Tibero metadata or test SQLAlchemy default behavior in your version.

## Additional object existence checks

- `has_table(connection, table_name, schema=None, **kw)` checks both tables and views.
- `has_index(connection, table_name, index_name, schema=None)` checks `all_indexes`.

## Reflection flow

```mermaid
flowchart TD
    i[Inspector call] --> s[_effective_schema]
    s --> q[Run metadata query on ALL_* or USER_* views]
    q --> r[_row_get extracts row values]
    r --> t[_resolve_column_type / group constraints]
    t --> out[SQLAlchemy reflection dictionaries]
```

!!! note "Uppercase object matching"
    Reflection SQL uppercases table/view/sequence names before filtering.

!!! warning "Unknown type fallback"
    Unmapped `DATA_TYPE` values become `NULLTYPE`, which can impact autogeneration and comparisons.
