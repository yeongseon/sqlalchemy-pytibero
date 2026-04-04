# pyright: reportIncompatibleMethodOverride=false, reportAssignmentType=false, reportMissingImports=false, reportCallIssue=false
from __future__ import annotations

import re

from sqlalchemy import types as sqltypes
from sqlalchemy import util
from sqlalchemy.engine import default, reflection
from sqlalchemy.sql import text

from sqlalchemy_pytibero.base import TiberoExecutionContext, TiberoIdentifierPreparer
from sqlalchemy_pytibero.compiler import TiberoCompiler, TiberoDDLCompiler, TiberoTypeCompiler
from sqlalchemy_pytibero.types import (
    BIGINT,
    BINARY_DOUBLE,
    BINARY_FLOAT,
    BLOB,
    CHAR,
    CLOB,
    DATE,
    DECIMAL,
    FLOAT,
    INTEGER,
    INTERVAL_DAY_TO_SECOND,
    INTERVAL_YEAR_TO_MONTH,
    LONG,
    LONG_RAW,
    NCHAR,
    NCLOB,
    NUMBER,
    NUMERIC,
    NVARCHAR2,
    RAW,
    ROWID,
    SMALLINT,
    TIMESTAMP,
    VARCHAR2,
)

_RE_TYPE_BASE = re.compile(r"^([A-Z ]+)")
_RE_LENGTH = re.compile(r"\((\d+)\)")
_RE_PRECISION_SCALE = re.compile(r"\((\d+)(?:\s*,\s*(\d+))?\)")
_RE_VERSION = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?")

colspecs = {
    sqltypes.Numeric: NUMERIC,
    sqltypes.Float: FLOAT,
    sqltypes.Integer: INTEGER,
}

ischema_names = {
    "NUMBER": NUMBER,
    "NUMERIC": NUMERIC,
    "DECIMAL": DECIMAL,
    "FLOAT": FLOAT,
    "BINARY_FLOAT": BINARY_FLOAT,
    "BINARY_DOUBLE": BINARY_DOUBLE,
    "SMALLINT": SMALLINT,
    "INTEGER": INTEGER,
    "INT": INTEGER,
    "BIGINT": BIGINT,
    "VARCHAR2": VARCHAR2,
    "VARCHAR": VARCHAR2,
    "CHAR": CHAR,
    "NCHAR": NCHAR,
    "NVARCHAR2": NVARCHAR2,
    "CLOB": CLOB,
    "NCLOB": NCLOB,
    "BLOB": BLOB,
    "DATE": DATE,
    "TIMESTAMP": TIMESTAMP,
    "RAW": RAW,
    "LONG RAW": LONG_RAW,
    "LONG": LONG,
    "ROWID": ROWID,
    "INTERVAL YEAR TO MONTH": INTERVAL_YEAR_TO_MONTH,
    "INTERVAL DAY TO SECOND": INTERVAL_DAY_TO_SECOND,
}


class TiberoDialect(default.DefaultDialect):
    name = "tibero"
    driver = "pytibero"
    supports_statement_cache = True

    statement_compiler = TiberoCompiler
    ddl_compiler = TiberoDDLCompiler
    type_compiler = TiberoTypeCompiler
    preparer = TiberoIdentifierPreparer
    execution_ctx_cls = TiberoExecutionContext

    default_paramstyle = "qmark"

    colspecs = colspecs
    ischema_names = ischema_names

    max_identifier_length = 128
    max_index_name_length = 128
    max_constraint_name_length = 128
    requires_name_normalize = True

    supports_native_enum = False
    supports_native_boolean = False
    supports_native_decimal = True

    supports_sequences = True
    sequences_optional = True

    supports_alter = True
    supports_comments = True
    inline_comments = False

    supports_default_values = False
    supports_default_metavalue = False
    supports_empty_insert = False
    supports_multivalues_insert = True
    supports_is_distinct_from = False

    insert_returning = False
    update_returning = False
    delete_returning = False

    postfetch_lastrowid = True

    _disconnect_messages = (
        "connection is closed",
        "lost connection",
        "server has gone away",
        "connection reset",
        "broken pipe",
        "connection timed out",
        "connection refused",
        "failed to connect",
        "not connected",
        "socket error",
    )

    def __init__(self, isolation_level=None, **kwargs):
        super().__init__(**kwargs)
        self.isolation_level = isolation_level

    @classmethod
    def import_dbapi(cls):
        import pytibero

        return pytibero

    @classmethod
    def dbapi(cls):
        return cls.import_dbapi()

    def create_connect_args(self, url):
        if url is None:
            raise ValueError("Unexpected database URL format")
        opts = url.translate_connect_args(username="user", database="database")
        kwargs = {
            "host": opts.get("host", "localhost"),
            "port": opts.get("port", 8629),
            "database": opts.get("database", ""),
            "user": opts.get("user", "tibero"),
            "password": opts.get("password", ""),
        }
        return (), kwargs

    def on_connect(self):
        isolation_level = self.isolation_level

        def connect(conn):
            conn.autocommit = False
            if isolation_level is not None:
                self.set_isolation_level(conn, isolation_level)

        return connect

    def get_isolation_level(self, dbapi_conn):
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("SELECT SYS_CONTEXT('USERENV', 'ISOLATION_LEVEL') FROM DUAL")
            row = cursor.fetchone()
            if not row or not row[0]:
                return "READ COMMITTED"
            return str(row[0]).upper()
        finally:
            cursor.close()

    def get_isolation_level_values(self):
        return ["READ COMMITTED", "SERIALIZABLE"]

    def set_isolation_level(self, dbapi_conn, level):
        normalized = str(level).upper()
        if normalized not in self.get_isolation_level_values():
            raise ValueError(f"Invalid isolation level: {level!r}")
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute(f"ALTER SESSION SET ISOLATION_LEVEL = {normalized}")
        finally:
            cursor.close()

    def reset_isolation_level(self, dbapi_conn):
        self.set_isolation_level(dbapi_conn, "READ COMMITTED")

    def _get_server_version_info(self, connection):
        version = connection.execute(text("SELECT BANNER FROM V$VERSION")).scalar()
        if version is None:
            return None
        match = _RE_VERSION.search(str(version))
        if not match:
            return None
        nums = [int(p) for p in match.groups() if p is not None]
        return tuple(nums)

    def _get_default_schema_name(self, connection):
        return connection.execute(
            text("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
        ).scalar()

    def _effective_schema(self, connection, schema):
        if schema:
            return schema.upper()
        default_schema = self._get_default_schema_name(connection)
        if default_schema:
            return str(default_schema).upper()
        return None

    def _row_get(self, row, key, index, default=None):
        if isinstance(row, dict):
            return row.get(key, default)
        mapping = getattr(row, "_mapping", None)
        if mapping is not None and key in mapping:
            return mapping[key]
        try:
            return row[index]
        except Exception:
            return default

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        if effective:
            result = connection.execute(
                text("SELECT table_name FROM all_tables WHERE owner = :schema ORDER BY table_name"),
                {"schema": effective},
            )
        else:
            result = connection.execute(
                text("SELECT table_name FROM user_tables ORDER BY table_name")
            )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text("SELECT view_name FROM all_views WHERE owner = :schema ORDER BY view_name"),
            {"schema": effective},
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text("SELECT text FROM all_views WHERE owner = :schema AND view_name = :name"),
            {"schema": effective, "name": view_name.upper()},
        )
        row = result.fetchone()
        return row[0] if row else None

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT column_name, data_type, data_length, data_precision, data_scale, "
                "nullable, data_default, column_id "
                "FROM all_tab_columns "
                "WHERE owner = :schema AND table_name = :table "
                "ORDER BY column_id"
            ),
            {"schema": effective, "table": table_name.upper()},
        )

        columns = []
        for row in result:
            col_name = self._row_get(row, "COLUMN_NAME", 0)
            data_type = str(self._row_get(row, "DATA_TYPE", 1, "")).upper()
            data_length = self._row_get(row, "DATA_LENGTH", 2)
            data_precision = self._row_get(row, "DATA_PRECISION", 3)
            data_scale = self._row_get(row, "DATA_SCALE", 4)
            nullable = self._row_get(row, "NULLABLE", 5) == "Y"
            data_default = self._row_get(row, "DATA_DEFAULT", 6)

            coltype = self._resolve_column_type(
                data_type=data_type,
                data_length=data_length,
                data_precision=data_precision,
                data_scale=data_scale,
            )

            columns.append(
                {
                    "name": col_name,
                    "type": coltype,
                    "nullable": nullable,
                    "default": data_default,
                    "autoincrement": False,
                }
            )
        return columns

    def _resolve_column_type(self, data_type, data_length, data_precision, data_scale):
        type_cls = self.ischema_names.get(data_type)
        if type_cls is None:
            util.warn(f"Did not recognize type '{data_type}'")
            return sqltypes.NULLTYPE

        if data_type in {"VARCHAR2", "NVARCHAR2", "CHAR", "NCHAR", "RAW"}:
            return type_cls(length=data_length) if data_length is not None else type_cls()

        if data_type in {"NUMBER", "NUMERIC", "DECIMAL", "FLOAT"}:
            if data_precision is not None and data_scale is not None:
                return type_cls(precision=int(data_precision), scale=int(data_scale))
            if data_precision is not None:
                return type_cls(precision=int(data_precision))
            return type_cls()

        return type_cls() if callable(type_cls) else type_cls

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT c.constraint_name, cc.column_name "
                "FROM all_constraints c "
                "JOIN all_cons_columns cc "
                "ON c.owner = cc.owner AND c.constraint_name = cc.constraint_name "
                "WHERE c.owner = :schema AND c.table_name = :table AND c.constraint_type = 'P' "
                "ORDER BY cc.position"
            ),
            {"schema": effective, "table": table_name.upper()},
        )
        rows = list(result)
        if not rows:
            return {"name": None, "constrained_columns": []}
        return {
            "name": rows[0][0],
            "constrained_columns": [r[1] for r in rows],
        }

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT c.constraint_name, cc.column_name, rc.table_name AS ref_table, "
                "rcc.column_name AS ref_column, rc.owner AS ref_owner "
                "FROM all_constraints c "
                "JOIN all_cons_columns cc "
                "ON c.owner = cc.owner AND c.constraint_name = cc.constraint_name "
                "JOIN all_constraints rc "
                "ON c.r_owner = rc.owner AND c.r_constraint_name = rc.constraint_name "
                "JOIN all_cons_columns rcc "
                "ON rc.owner = rcc.owner AND rc.constraint_name = rcc.constraint_name "
                "AND cc.position = rcc.position "
                "WHERE c.owner = :schema AND c.table_name = :table AND c.constraint_type = 'R' "
                "ORDER BY c.constraint_name, cc.position"
            ),
            {"schema": effective, "table": table_name.upper()},
        )
        by_name = {}
        for row in result:
            name = row[0]
            item = by_name.setdefault(
                name,
                {
                    "name": name,
                    "constrained_columns": [],
                    "referred_schema": row[4],
                    "referred_table": row[2],
                    "referred_columns": [],
                },
            )
            item["constrained_columns"].append(row[1])
            item["referred_columns"].append(row[3])
        return list(by_name.values())

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT i.index_name, i.uniqueness, ic.column_name, ic.column_position "
                "FROM all_indexes i "
                "JOIN all_ind_columns ic "
                "ON i.owner = ic.index_owner AND i.index_name = ic.index_name "
                "WHERE i.owner = :schema AND i.table_name = :table "
                "ORDER BY i.index_name, ic.column_position"
            ),
            {"schema": effective, "table": table_name.upper()},
        )
        idict = {}
        for row in result:
            name = row[0]
            item = idict.setdefault(
                name,
                {
                    "name": name,
                    "column_names": [],
                    "unique": row[1] == "UNIQUE",
                },
            )
            item["column_names"].append(row[2])
        return list(idict.values())

    @reflection.cache
    def get_unique_constraints(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT c.constraint_name, cc.column_name "
                "FROM all_constraints c "
                "JOIN all_cons_columns cc "
                "ON c.owner = cc.owner AND c.constraint_name = cc.constraint_name "
                "WHERE c.owner = :schema AND c.table_name = :table AND c.constraint_type = 'U' "
                "ORDER BY c.constraint_name, cc.position"
            ),
            {"schema": effective, "table": table_name.upper()},
        )
        by_name = {}
        for row in result:
            by_name.setdefault(row[0], {"name": row[0], "column_names": []})["column_names"].append(
                row[1]
            )
        return list(by_name.values())

    @reflection.cache
    def get_check_constraints(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT constraint_name, search_condition "
                "FROM all_constraints "
                "WHERE owner = :schema AND table_name = :table AND constraint_type = 'C'"
            ),
            {"schema": effective, "table": table_name.upper()},
        )
        return [{"name": row[0], "sqltext": row[1]} for row in result if row[1] is not None]

    @reflection.cache
    def get_table_comment(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        result = connection.execute(
            text(
                "SELECT comments FROM all_tab_comments "
                "WHERE owner = :schema AND table_name = :table"
            ),
            {"schema": effective, "table": table_name.upper()},
        )
        row = result.fetchone()
        return {"text": row[0] if row and row[0] else None}

    def get_schema_names(self, connection, **kw):
        result = connection.execute(text("SELECT username FROM all_users ORDER BY username"))
        return [row[0] for row in result]

    def has_table(self, connection, table_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        table_count = connection.execute(
            text("SELECT COUNT(*) FROM all_tables WHERE owner = :schema AND table_name = :name"),
            {"schema": effective, "name": table_name.upper()},
        ).scalar()
        if table_count and table_count > 0:
            return True
        view_count = connection.execute(
            text("SELECT COUNT(*) FROM all_views WHERE owner = :schema AND view_name = :name"),
            {"schema": effective, "name": table_name.upper()},
        ).scalar()
        return bool(view_count and view_count > 0)

    def has_index(self, connection, table_name, index_name, schema=None):
        effective = self._effective_schema(connection, schema)
        count = connection.execute(
            text(
                "SELECT COUNT(*) FROM all_indexes "
                "WHERE owner = :schema AND table_name = :table AND index_name = :name"
            ),
            {"schema": effective, "table": table_name.upper(), "name": index_name.upper()},
        ).scalar()
        return bool(count and count > 0)

    def has_sequence(self, connection, sequence_name, schema=None, **kw):
        effective = self._effective_schema(connection, schema)
        count = connection.execute(
            text(
                "SELECT COUNT(*) FROM all_sequences WHERE sequence_owner = :schema AND sequence_name = :name"
            ),
            {"schema": effective, "name": sequence_name.upper()},
        ).scalar()
        return bool(count and count > 0)

    def is_disconnect(self, e, connection, cursor):
        msg = str(e).lower()
        for pattern in self._disconnect_messages:
            if pattern in msg:
                return True
        code = self._extract_error_code(e)
        if code in {-3113, -3114, -3135, -12537, -12541, -12547, -12170, 3113, 3114}:
            return True
        return False

    @staticmethod
    def _extract_error_code(exception):
        if not getattr(exception, "args", None):
            return None
        first = exception.args[0]
        if isinstance(first, int):
            return first
        if isinstance(first, str):
            match = re.match(r"\s*(-?\d+)", first)
            if match:
                return int(match.group(1))
        return None

    def do_ping(self, dbapi_connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT 1 FROM DUAL")
            return True
        finally:
            cursor.close()


dialect = TiberoDialect
