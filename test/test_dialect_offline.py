# pyright: reportArgumentType=false
from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import url

from sqlalchemy_pytibero.base import TiberoExecutionContext
from sqlalchemy_pytibero.dialect import TiberoDialect, _normalize_default


def _invoke_reflection(dialect, method_name, connection, *args, **kwargs):
    method = getattr(dialect, method_name)
    if hasattr(method, "__wrapped__"):
        return method.__wrapped__(dialect, connection, *args, **kwargs)
    return method(connection, *args, **kwargs)


class TestDialectBasics:
    def test_init_and_flags(self):
        d = TiberoDialect()
        assert d.name == "tibero"
        assert d.driver == "pytibero"
        assert d.postfetch_lastrowid is True

    def test_import_dbapi_success(self):
        fake = types.ModuleType("pytibero")
        with patch.dict(sys.modules, {"pytibero": fake}):
            assert TiberoDialect.import_dbapi() is fake
            assert TiberoDialect.dbapi() is fake

    def test_import_dbapi_import_error(self):
        import builtins

        real_import = builtins.__import__

        def _fake(name, *args, **kwargs):
            if name == "pytibero":
                raise ImportError("driver missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake):
            with pytest.raises(ImportError, match="driver missing"):
                TiberoDialect.import_dbapi()

    def test_create_connect_args(self):
        d = TiberoDialect()
        parsed = url.make_url("tibero://u:p@dbhost:8630/d1")
        args, kwargs = d.create_connect_args(parsed)
        assert args == ()
        assert kwargs == {
            "host": "dbhost",
            "port": 8630,
            "database": "d1",
            "user": "u",
            "password": "p",
        }

    def test_create_connect_args_defaults_and_none(self):
        d = TiberoDialect()
        args, kwargs = d.create_connect_args(url.make_url("tibero://"))
        assert args == ()
        assert kwargs == {
            "host": "localhost",
            "port": 8629,
            "database": "",
            "user": "tibero",
            "password": "",
        }
        with pytest.raises(ValueError, match="Unexpected database URL format"):
            d.create_connect_args(cast(Any, None))

    def test_on_connect(self):
        d = TiberoDialect(isolation_level="SERIALIZABLE")
        d.set_isolation_level = MagicMock()
        conn = MagicMock()
        d.on_connect()(conn)
        assert conn.autocommit is False
        d.set_isolation_level.assert_called_once_with(conn, "SERIALIZABLE")


class TestIsolationLevelMethods:
    def test_get_set_reset_isolation_levels(self):
        d = TiberoDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("read committed",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        assert d.get_isolation_level(dbapi_conn) == "READ COMMITTED"
        assert d.get_isolation_level_values() == ["READ COMMITTED", "SERIALIZABLE"]

        d.set_isolation_level(dbapi_conn, "SERIALIZABLE")
        cursor.execute.assert_any_call("ALTER SESSION SET ISOLATION_LEVEL = SERIALIZABLE")

        d.reset_isolation_level(dbapi_conn)
        cursor.execute.assert_any_call("ALTER SESSION SET ISOLATION_LEVEL = READ COMMITTED")
        assert cursor.close.call_count >= 3

    def test_set_isolation_level_invalid(self):
        d = TiberoDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = MagicMock()
        with pytest.raises(ValueError, match="Invalid isolation level"):
            d.set_isolation_level(dbapi_conn, "READ UNCOMMITTED")

    def test_get_isolation_level_default_when_empty(self):
        d = TiberoDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = (None,)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor
        assert d.get_isolation_level(dbapi_conn) == "READ COMMITTED"


class TestExistenceChecks:
    def test_has_table_and_sequence_and_index(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.execute.return_value = MagicMock(scalar=lambda: 1)
        assert d.has_table(conn, "users", schema="APP") is True

        conn2 = MagicMock()
        conn2.execute.side_effect = [MagicMock(scalar=lambda: 0), MagicMock(scalar=lambda: 1)]
        assert d.has_table(conn2, "users", schema="APP") is True

        conn2b = MagicMock()
        conn2b.execute.side_effect = [MagicMock(scalar=lambda: 0), MagicMock(scalar=lambda: 0)]
        assert d.has_table(conn2b, "users", schema="APP") is False

        conn3 = MagicMock()
        conn3.execute.return_value = MagicMock(scalar=lambda: 1)
        assert d.has_sequence(conn3, "seq_users", schema="APP") is True
        assert d.has_index(conn3, "users", "ix_users_name", schema="APP") is True

        conn4 = MagicMock()
        conn4.execute.return_value = MagicMock(scalar=lambda: 0)
        assert d.has_sequence(conn4, "seq_users", schema="APP") is False
        assert d.has_index(conn4, "users", "ix_users_name", schema="APP") is False


class TestReflectionMethods:
    def test_get_columns(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.return_value = [
            ("ID", "NUMBER", None, 10, 0, "N", None, 1),
            ("NAME", "VARCHAR2(100)", 100, None, None, "Y", "'x'", 2),
            ("FLAG", "MYSTERY", None, None, None, "Y", None, 3),
        ]
        with patch("sqlalchemy.util.warn", create=True) as warn:
            cols = _invoke_reflection(d, "get_columns", conn, "USERS", schema="APP")
        assert cols[0]["name"] == "ID"
        assert cols[0]["nullable"] is False
        assert cols[0]["default"] is None
        assert cols[1]["type"].__class__.__name__ == "VARCHAR2"
        assert cols[1]["default"] == "x"
        assert cols[2]["type"].__class__.__name__ == "NullType"
        warn.assert_called_once()

    @pytest.mark.parametrize(
        ("raw_default", "expected"),
        [
            (None, None),
            ("", None),
            ("NULL", None),
            (" SYSDATE ", "SYSDATE"),
            ("(1)", "1"),
            ("'hello'", "hello"),
            ("0", "0"),
            ("USER", "USER"),
            ("SYS_GUID()", "SYS_GUID()"),
            ("seq_users.NEXTVAL", "seq_users.NEXTVAL"),
        ],
    )
    def test_normalize_default(self, raw_default, expected):
        assert _normalize_default(raw_default) == expected

    def test_get_columns_normalizes_defaults(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.return_value = [
            ("C1", "DATE", None, None, None, "Y", " SYSDATE \n", 1),
            ("C2", "NUMBER", None, 10, 0, "Y", "(1)", 2),
            ("C3", "VARCHAR2", 20, None, None, "Y", "'hello'", 3),
            ("C4", "VARCHAR2", 20, None, None, "Y", "NULL", 4),
            ("C5", "VARCHAR2", 20, None, None, "Y", "USER", 5),
        ]

        cols = _invoke_reflection(d, "get_columns", conn, "USERS", schema="APP")

        assert [col["default"] for col in cols] == ["SYSDATE", "1", "hello", None, "USER"]

    def test_row_get_and_effective_schema_and_type_resolution_helpers(self):
        d = TiberoDialect()
        assert d._row_get({"A": 1}, "A", 0) == 1

        mapping_row = MagicMock()
        mapping_row._mapping = {"A": 2}
        assert d._row_get(mapping_row, "A", 0) == 2

        class BadRow:
            def __getitem__(self, idx):
                raise IndexError()

        assert d._row_get(BadRow(), "A", 0, default=9) == 9

        conn = MagicMock()
        conn.execute.return_value = MagicMock(scalar=lambda: "app")
        assert d._effective_schema(conn, "x") == "X"
        assert d._effective_schema(conn, None) == "APP"
        conn.execute.return_value = MagicMock(scalar=lambda: None)
        assert d._effective_schema(conn, None) is None

        assert d._resolve_column_type("NUMBER", None, 5, None).__class__.__name__ == "NUMBER"
        assert d._resolve_column_type("DATE", None, None, None).__class__.__name__ == "DATE"

    def test_get_pk_constraint(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.return_value = [("PK_USERS", "ID")]
        pk = _invoke_reflection(d, "get_pk_constraint", conn, "USERS", schema="APP")
        assert pk == {"name": "PK_USERS", "constrained_columns": ["ID"]}

    def test_get_foreign_keys(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.return_value = [
            ("FK_ORDERS_USERS", "USER_ID", "USERS", "ID", "APP"),
            ("FK_ORDERS_USERS", "TENANT_ID", "USERS", "TENANT_ID", "APP"),
        ]
        fks = _invoke_reflection(d, "get_foreign_keys", conn, "ORDERS", schema="APP")
        assert fks[0]["name"] == "FK_ORDERS_USERS"
        assert fks[0]["constrained_columns"] == ["USER_ID", "TENANT_ID"]
        assert fks[0]["referred_columns"] == ["ID", "TENANT_ID"]

    def test_get_table_names_and_views_and_definition(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.side_effect = [
            [("USERS",), ("ORDERS",)],
            [("ACTIVE_USERS",)],
            MagicMock(fetchone=lambda: ("SELECT * FROM USERS",)),
        ]
        assert _invoke_reflection(d, "get_table_names", conn, schema="APP") == ["USERS", "ORDERS"]
        assert _invoke_reflection(d, "get_view_names", conn, schema="APP") == ["ACTIVE_USERS"]
        assert (
            _invoke_reflection(d, "get_view_definition", conn, "ACTIVE_USERS", schema="APP")
            == "SELECT * FROM USERS"
        )

    def test_get_table_names_without_schema_uses_user_tables(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        with patch.object(d, "_get_default_schema_name", return_value=None):
            conn.execute.return_value = [("T1",), ("T2",)]
            assert _invoke_reflection(d, "get_table_names", conn, schema=None) == ["T1", "T2"]

    def test_get_view_definition_none_and_empty_pk(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.return_value = MagicMock(fetchone=lambda: None)
        assert _invoke_reflection(d, "get_view_definition", conn, "V1", schema="APP") is None

        conn2 = MagicMock()
        conn2.info_cache = {}
        conn2.dialect_options = {}
        conn2.execute.return_value = []
        assert _invoke_reflection(d, "get_pk_constraint", conn2, "T1", schema="APP") == {
            "name": None,
            "constrained_columns": [],
        }

    def test_get_indexes_unique_checks_comments_schemas(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.info_cache = {}
        conn.dialect_options = {}
        conn.execute.side_effect = [
            [
                ("IX_USERS_NAME", "NONUNIQUE", "NAME", 1),
                ("UX_USERS_EMAIL", "UNIQUE", "EMAIL", 1),
            ],
            [("UX_USERS_EMAIL", "EMAIL")],
            [("CK_USERS_NAME", "NAME IS NOT NULL")],
            MagicMock(fetchone=lambda: ("User table",)),
            [("APP",), ("SYS",)],
        ]
        idx = _invoke_reflection(d, "get_indexes", conn, "USERS", schema="APP")
        uq = _invoke_reflection(d, "get_unique_constraints", conn, "USERS", schema="APP")
        ck = _invoke_reflection(d, "get_check_constraints", conn, "USERS", schema="APP")
        comment = _invoke_reflection(d, "get_table_comment", conn, "USERS", schema="APP")
        schemas = d.get_schema_names(conn)
        assert idx[0]["name"] == "IX_USERS_NAME"
        assert any(item["name"] == "UX_USERS_EMAIL" for item in uq)
        assert ck[0]["name"] == "CK_USERS_NAME"
        assert comment == {"text": "User table"}
        assert schemas == ["APP", "SYS"]


class TestIsDisconnect:
    def test_disconnect_message_patterns(self):
        d = TiberoDialect()
        assert d.is_disconnect(Exception("connection is closed"), None, None) is True
        assert d.is_disconnect(Exception("Socket Error happened"), None, None) is True

    def test_disconnect_by_error_code(self):
        d = TiberoDialect()
        assert d.is_disconnect(Exception(-3113, "x"), None, None) is True
        assert d.is_disconnect(Exception("3114 lost"), None, None) is True

    def test_non_disconnect(self):
        d = TiberoDialect()
        assert d.is_disconnect(Exception("syntax error"), None, None) is False

    def test_extract_error_code_cases(self):
        d = TiberoDialect()
        assert d._extract_error_code(Exception()) is None
        assert d._extract_error_code(Exception(-1, "x")) == -1
        assert d._extract_error_code(Exception("  -3113 closed")) == -3113
        assert d._extract_error_code(Exception("oops")) is None


class TestDoPing:
    def test_do_ping_success_and_exception(self):
        d = TiberoDialect()
        cursor = MagicMock()
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor
        assert d.do_ping(dbapi_conn) is True
        cursor.execute.assert_called_once_with("SELECT 1 FROM DUAL")
        cursor.close.assert_called_once()

        bad_cursor = MagicMock()
        bad_cursor.execute.side_effect = RuntimeError("boom")
        bad_conn = MagicMock()
        bad_conn.cursor.return_value = bad_cursor
        with pytest.raises(RuntimeError, match="boom"):
            d.do_ping(bad_conn)


class TestPostfetchLastRowId:
    def test_postfetch_flag_and_execution_context(self):
        assert TiberoDialect.postfetch_lastrowid is True
        ctx = object.__new__(TiberoExecutionContext)
        ctx.cursor = MagicMock(lastrowid=55)
        assert ctx.get_lastrowid() == 55


class TestDisconnectMessages:
    def test_disconnect_message_tuple(self):
        msgs = TiberoDialect._disconnect_messages
        assert isinstance(msgs, tuple)
        assert len(msgs) > 0
        assert all(m == m.lower() for m in msgs)


class TestVersionAndSchemaQueries:
    def test_version_and_default_schema_methods(self):
        d = TiberoDialect()
        conn = MagicMock()
        conn.execute.return_value = MagicMock(scalar=lambda: "Tibero Database 7.2.1")
        assert d._get_server_version_info(conn) == (7, 2, 1)
        conn.execute.return_value = MagicMock(scalar=lambda: "unknown")
        assert d._get_server_version_info(conn) is None
        conn.execute.return_value = MagicMock(scalar=lambda: None)
        assert d._get_server_version_info(conn) is None

        conn.execute.return_value = MagicMock(scalar=lambda: "APP")
        assert d._get_default_schema_name(conn) == "APP"
