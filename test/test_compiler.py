from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.schema import (
    CreateTable,
    DropTableComment,
    SetColumnComment,
    SetTableComment,
)

from sqlalchemy_pytibero.dialect import TiberoDialect
from sqlalchemy_pytibero.types import (
    BIGINT,
    BINARY_DOUBLE,
    BINARY_FLOAT,
    CHAR,
    CLOB,
    DATE,
    DECIMAL,
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
    VARCHAR2,
)


def _compile(stmt, dialect=None):
    dialect = dialect or TiberoDialect()
    return stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}).string


metadata = MetaData()
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100)),
    Column("email", String(200)),
)
orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
)


class TestSelectCompilation:
    def test_basic_distinct_limit_offset_for_update(self):
        assert "SELECT" in _compile(select(users))
        assert "DISTINCT" in _compile(select(users.c.name).distinct())
        assert "FETCH FIRST 10 ROWS ONLY" in _compile(select(users).limit(10))
        assert "OFFSET 5 ROWS" in _compile(select(users).offset(5))
        assert "OFFSET 5 ROWS FETCH FIRST 10 ROWS ONLY" in _compile(
            select(users).offset(5).limit(10)
        )
        assert _compile(select(users).with_for_update()).strip().endswith("FOR UPDATE")
        assert "FOR UPDATE OF" in _compile(select(users).with_for_update(of=[users.c.id]))

    def test_for_update_nowait(self):
        sql = _compile(select(users).with_for_update(nowait=True))
        assert sql.strip().endswith("FOR UPDATE NOWAIT")


class TestInsertCompilation:
    def test_insert_with_values(self):
        sql = _compile(sa.insert(users).values(name="a", email="a@example.com"))
        assert "INSERT INTO users" in sql


class TestJoinCompilation:
    def test_join_and_outerjoin(self):
        inner = _compile(select(users).join(orders, users.c.id == orders.c.user_id))
        left = _compile(select(users).outerjoin(orders, users.c.id == orders.c.user_id))
        assert "INNER JOIN" in inner and " ON " in inner
        assert "LEFT OUTER JOIN" in left and " ON " in left


class TestCastCompilation:
    def test_cast(self):
        assert "CAST" in _compile(select(sa.cast(users.c.name, Integer)))
        assert "CAST" in _compile(select(sa.cast(users.c.id, String(20))))


class TestLiteralValueCompilation:
    def test_backslash_escaping(self):
        sql = _compile(select(sa.literal("a\\b")))
        assert "\\\\" in sql


class TestFunctionCompilation:
    def test_sysdate_and_systimestamp(self):
        assert "SYSDATE" in _compile(select(sa.func.sysdate()))
        assert "SYSTIMESTAMP" in _compile(select(sa.func.systimestamp()))

    def test_nvl_dual_and_default_from(self):
        assert "NVL(" in _compile(select(sa.func.nvl(users.c.name, "x")))
        assert "DUAL" in _compile(select(sa.literal(1)))
        assert "DUAL" in _compile(select(sa.func.dual()))


class TestTypeCompilation:
    def test_type_compiler_methods(self):
        tc = TiberoDialect().type_compiler_instance
        assert tc.process(sa.Boolean()) == "NUMBER(1)"
        assert tc.process(NUMERIC()) == "NUMERIC"
        assert tc.process(NUMERIC(precision=10)) == "NUMERIC(10)"
        assert tc.process(NUMERIC(precision=10, scale=2)) == "NUMERIC(10, 2)"
        assert tc.process(NUMBER()) == "NUMBER"
        assert tc.process(NUMBER(precision=8)) == "NUMBER(8)"
        assert tc.process(NUMBER(precision=8, scale=3)) == "NUMBER(8, 3)"
        assert tc.process(DECIMAL()) == "DECIMAL"
        assert tc.process(DECIMAL(precision=9)) == "DECIMAL(9)"
        assert tc.process(DECIMAL(precision=9, scale=3)) == "DECIMAL(9, 3)"
        assert tc.process(sa.Float()) == "FLOAT"
        assert tc.process(sa.Float(precision=7)) == "FLOAT(7)"
        assert tc.process(BINARY_FLOAT()) == "BINARY_FLOAT"
        assert tc.process(BINARY_DOUBLE()) == "BINARY_DOUBLE"
        assert tc.process(sa.SmallInteger()) == "SMALLINT"
        assert tc.process(sa.Integer()) == "INTEGER"
        assert tc.process(VARCHAR2()) == "VARCHAR2"
        assert tc.process(BIGINT()) == "NUMBER(19)"
        assert tc.process(VARCHAR2(10)) == "VARCHAR2(10)"
        assert tc.process(CHAR()) == "CHAR"
        assert tc.process(CHAR(4)) == "CHAR(4)"
        assert tc.process(NCHAR()) == "NCHAR"
        assert tc.process(NCHAR(4)) == "NCHAR(4)"
        assert tc.process(sa.NVARCHAR(6)) == "NVARCHAR2(6)"
        assert tc.process(NVARCHAR2()) == "NVARCHAR2"
        assert tc.process(NVARCHAR2(4)) == "NVARCHAR2(4)"
        assert tc.process(CLOB()) == "CLOB"
        assert tc.process(NCLOB()) == "NCLOB"
        assert tc.process(sa.LargeBinary()) == "BLOB"
        assert tc.process(RAW()) == "RAW"
        assert tc.process(RAW(16)) == "RAW(16)"
        assert tc.process(LONG()) == "LONG"
        assert tc.process(LONG_RAW()) == "LONG RAW"
        assert tc.process(ROWID()) == "ROWID"
        assert tc.process(DATE()) == "DATE"
        assert tc.process(sa.TIMESTAMP()) == "TIMESTAMP"
        assert tc.process(INTERVAL_YEAR_TO_MONTH()) == "INTERVAL YEAR TO MONTH"
        assert tc.process(INTERVAL_DAY_TO_SECOND()) == "INTERVAL DAY TO SECOND"
        assert tc.process(sa.Text()) == "CLOB"
        assert tc.process(sa.DateTime()) == "DATE"


class TestDDLCompilation:
    def test_autoincrement_notnull_default_and_type_output(self):
        t = Table(
            "ddl_t",
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(30), nullable=False),
            Column("flag", Integer, server_default=sa.text("1")),
        )
        ddl = CreateTable(t).compile(dialect=TiberoDialect()).string
        assert "GENERATED ALWAYS AS IDENTITY" in ddl
        assert "NOT NULL" in ddl
        assert "DEFAULT 1" in ddl


class TestCommentCompilation:
    def test_table_and_column_comment_sql(self):
        m = MetaData()
        t = Table("cmt_t", m, Column("id", Integer, comment="identifier"), comment="table comment")
        d = TiberoDialect()
        assert (
            "COMMENT ON TABLE cmt_t IS 'table comment'"
            in SetTableComment(t).compile(dialect=d).string
        )
        assert "COMMENT ON TABLE cmt_t IS ''" in DropTableComment(t).compile(dialect=d).string
        assert (
            "COMMENT ON COLUMN cmt_t.id IS 'identifier'"
            in SetColumnComment(t.c.id).compile(dialect=d).string
        )

    def test_post_create_table_comment_clause(self):
        t = Table("post_cmt", MetaData(), Column("id", Integer), comment="hello")
        ddl = CreateTable(t).compile(dialect=TiberoDialect()).string
        assert "COMMENT ON TABLE post_cmt IS 'hello'" in ddl


class TestCompilerDirectBranches:
    def test_for_update_none_and_limit_none(self):
        stmt = select(users)
        compiled = stmt.compile(dialect=TiberoDialect())
        assert compiled.for_update_clause(stmt) == ""
        assert compiled.limit_clause(stmt) == ""


class TestWindowFunctionCompilation:
    def test_window_functions(self):
        row_number_sql = _compile(select(sa.func.row_number().over(order_by=users.c.id)))
        rank_sql = _compile(select(sa.func.rank().over(order_by=users.c.id)))
        dense_rank_sql = _compile(select(sa.func.dense_rank().over(order_by=users.c.id)))
        assert "row_number()" in row_number_sql.lower()
        assert "rank()" in rank_sql.lower()
        assert "dense_rank()" in dense_rank_sql.lower()


class TestNullsOrderCompilation:
    def test_nulls_first_last(self):
        assert "NULLS FIRST" in _compile(select(users).order_by(users.c.name.asc().nulls_first()))
        assert "NULLS LAST" in _compile(select(users).order_by(users.c.name.desc().nulls_last()))


class TestRecursiveCTECompilation:
    def test_recursive_and_non_recursive_cte(self):
        base = select(sa.literal(1).label("n")).cte("nums", recursive=True)
        recursive = base.union_all(select((base.c.n + 1).label("n")).where(base.c.n < 3))
        sql = _compile(select(recursive.c.n))
        assert "WITH" in sql
        simple_cte = select(users.c.id).cte("u")
        sql2 = _compile(select(simple_cte.c.id))
        assert "WITH" in sql2


class TestUpdateCompilation:
    def test_update(self):
        sql = _compile(sa.update(users).where(users.c.id == 1).values(name="b"))
        assert "UPDATE users" in sql
