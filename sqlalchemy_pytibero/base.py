# pyright: reportIncompatibleMethodOverride=false
from __future__ import annotations

import re

from sqlalchemy.engine import default
from sqlalchemy.sql import compiler


AUTOCOMMIT_REGEXP = re.compile(
    r"\s*(?:UPDATE|INSERT|CREATE|DELETE|DROP|ALTER|MERGE|TRUNCATE)", re.I | re.UNICODE
)

RESERVED_WORDS = frozenset(
    {
        "access",
        "add",
        "all",
        "alter",
        "and",
        "any",
        "as",
        "asc",
        "audit",
        "between",
        "by",
        "char",
        "check",
        "cluster",
        "column",
        "comment",
        "compress",
        "connect",
        "create",
        "current",
        "date",
        "decimal",
        "default",
        "delete",
        "desc",
        "distinct",
        "drop",
        "else",
        "exclusive",
        "exists",
        "file",
        "float",
        "for",
        "from",
        "grant",
        "group",
        "having",
        "identified",
        "if",
        "immediate",
        "in",
        "increment",
        "index",
        "initial",
        "insert",
        "integer",
        "intersect",
        "into",
        "is",
        "level",
        "like",
        "lock",
        "long",
        "maxextents",
        "minus",
        "mlslabel",
        "mode",
        "modify",
        "noaudit",
        "nocompress",
        "not",
        "nowait",
        "null",
        "number",
        "of",
        "offline",
        "on",
        "online",
        "option",
        "or",
        "order",
        "pctfree",
        "prior",
        "privileges",
        "public",
        "raw",
        "rename",
        "resource",
        "revoke",
        "row",
        "rowid",
        "rownum",
        "rows",
        "select",
        "session",
        "set",
        "share",
        "size",
        "smallint",
        "start",
        "successful",
        "synonym",
        "sysdate",
        "table",
        "then",
        "to",
        "trigger",
        "uid",
        "union",
        "unique",
        "update",
        "user",
        "validate",
        "values",
        "varchar",
        "varchar2",
        "view",
        "whenever",
        "where",
        "with",
    }
)


class TiberoIdentifierPreparer(compiler.IdentifierPreparer):
    reserved_words = RESERVED_WORDS

    def __init__(
        self,
        dialect,
        initial_quote='"',
        final_quote=None,
        escape_quote='"',
        omit_schema=False,
    ):
        super().__init__(dialect, initial_quote, final_quote, escape_quote, omit_schema)

    def _quote_free_identifiers(self, *ids):
        return tuple(self.quote_identifier(i) for i in ids if i is not None)


class TiberoExecutionContext(default.DefaultExecutionContext):
    def should_autocommit_text(self, statement):
        return AUTOCOMMIT_REGEXP.match(statement)

    def get_lastrowid(self):
        try:
            return self.cursor.lastrowid
        except Exception:
            return None
