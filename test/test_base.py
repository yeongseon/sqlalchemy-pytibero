from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sqlalchemy_pytibero.base import (
    AUTOCOMMIT_REGEXP,
    RESERVED_WORDS,
    TiberoExecutionContext,
    TiberoIdentifierPreparer,
)
from sqlalchemy_pytibero.dialect import TiberoDialect


class TestAutocommitRegexp:
    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE t SET a=1",
            "insert into t values (1)",
            "CREATE TABLE t (id int)",
            "DELETE FROM t",
            "drop table t",
            "ALTER TABLE t ADD c int",
            "MERGE INTO t u USING s ON (u.id=s.id)",
            "TRUNCATE TABLE t",
        ],
    )
    def test_matches_writes(self, statement):
        assert AUTOCOMMIT_REGEXP.match(statement)

    @pytest.mark.parametrize("statement", ["SELECT 1", "WITH c AS (SELECT 1) SELECT * FROM c"])
    def test_does_not_match_reads(self, statement):
        assert AUTOCOMMIT_REGEXP.match(statement) is None


class TestReservedWords:
    def test_reserved_words(self):
        assert isinstance(RESERVED_WORDS, frozenset)
        assert "select" in RESERVED_WORDS
        assert "insert" in RESERVED_WORDS
        assert "table" in RESERVED_WORDS


class TestIdentifierPreparer:
    def test_constructor_defaults_and_quote_free_identifiers(self):
        p = TiberoIdentifierPreparer(TiberoDialect())
        assert p.initial_quote == '"'
        assert p.final_quote == '"'
        assert p.escape_quote == '"'
        assert p._quote_free_identifiers("users", None, "order") == ('"users"', '"order"')


class TestExecutionContext:
    def test_should_autocommit_text(self):
        ctx = object.__new__(TiberoExecutionContext)
        assert ctx.should_autocommit_text("DELETE FROM t")
        assert ctx.should_autocommit_text("SELECT 1") is None

    def test_get_lastrowid_and_fallback_none(self):
        ctx = object.__new__(TiberoExecutionContext)
        ctx.cursor = MagicMock(lastrowid=77)
        assert ctx.get_lastrowid() == 77

        ctx.cursor = MagicMock()
        del ctx.cursor.lastrowid
        assert ctx.get_lastrowid() is None
