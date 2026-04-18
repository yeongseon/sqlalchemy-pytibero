from __future__ import annotations

from unittest.mock import patch

from sqlalchemy.sql import sqltypes

from sqlalchemy_pytibero.dialect import TiberoDialect
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


class TestVisitNames:
    def test_all_visit_names(self):
        assert NUMBER.__visit_name__ == "NUMBER"
        assert NUMERIC.__visit_name__ == "NUMERIC"
        assert DECIMAL.__visit_name__ == "DECIMAL"
        assert FLOAT.__visit_name__ == "FLOAT"
        assert BINARY_FLOAT.__visit_name__ == "BINARY_FLOAT"
        assert BINARY_DOUBLE.__visit_name__ == "BINARY_DOUBLE"
        assert SMALLINT.__visit_name__ == "SMALLINT"
        assert INTEGER.__visit_name__ == "INTEGER"
        assert BIGINT.__visit_name__ == "BIGINT"
        assert VARCHAR2.__visit_name__ == "VARCHAR2"
        assert CHAR.__visit_name__ == "CHAR"
        assert NCHAR.__visit_name__ == "NCHAR"
        assert NVARCHAR2.__visit_name__ == "NVARCHAR2"
        assert CLOB.__visit_name__ == "CLOB"
        assert NCLOB.__visit_name__ == "NCLOB"
        assert BLOB.__visit_name__ == "BLOB"
        assert DATE.__visit_name__ == "DATE"
        assert TIMESTAMP.__visit_name__ == "TIMESTAMP"
        assert INTERVAL_YEAR_TO_MONTH.__visit_name__ == "INTERVAL_YEAR_TO_MONTH"
        assert INTERVAL_DAY_TO_SECOND.__visit_name__ == "INTERVAL_DAY_TO_SECOND"
        assert RAW.__visit_name__ == "RAW"
        assert LONG_RAW.__visit_name__ == "LONG_RAW"
        assert LONG.__visit_name__ == "LONG"
        assert ROWID.__visit_name__ == "ROWID"


class TestTypeInstantiation:
    def test_numeric_types(self):
        assert isinstance(NUMBER(precision=10, scale=2), sqltypes.NUMERIC)
        assert isinstance(NUMERIC(precision=10, scale=2), sqltypes.NUMERIC)
        assert isinstance(DECIMAL(precision=10, scale=2), sqltypes.DECIMAL)
        assert isinstance(FLOAT(precision=10), sqltypes.FLOAT)
        assert isinstance(BINARY_FLOAT(), sqltypes.Float)
        assert isinstance(BINARY_DOUBLE(), sqltypes.Float)
        assert isinstance(SMALLINT(), sqltypes.SMALLINT)
        assert isinstance(INTEGER(), sqltypes.INTEGER)
        assert isinstance(BIGINT(), sqltypes.BIGINT)

    def test_string_lob_and_other_types(self):
        assert isinstance(VARCHAR2(100), sqltypes.VARCHAR)
        assert isinstance(CHAR(10), sqltypes.CHAR)
        assert isinstance(NCHAR(12), sqltypes.NCHAR)
        assert isinstance(NVARCHAR2(15), sqltypes.NVARCHAR)
        assert isinstance(CLOB(), sqltypes.Text)
        assert isinstance(NCLOB(), sqltypes.Text)
        assert isinstance(BLOB(), sqltypes.LargeBinary)
        assert isinstance(DATE(), sqltypes.DATE)
        assert isinstance(TIMESTAMP(), sqltypes.TIMESTAMP)
        assert isinstance(INTERVAL_YEAR_TO_MONTH(), sqltypes.TypeEngine)
        assert isinstance(INTERVAL_DAY_TO_SECOND(), sqltypes.TypeEngine)
        assert isinstance(RAW(16), sqltypes.LargeBinary)
        assert isinstance(LONG_RAW(), sqltypes.LargeBinary)
        assert isinstance(LONG(), sqltypes.Text)
        assert isinstance(ROWID(), sqltypes.TypeEngine)


class TestRepr:
    def test_string_repr(self):
        r = repr(VARCHAR2(length=255))
        assert "VARCHAR2" in r
        assert "255" in r

    def test_repr_signature_error_path(self):
        with patch("sqlalchemy_pytibero.types.inspect.signature", side_effect=ValueError("x")):
            assert repr(CHAR(length=8)) == "CHAR()"


class TestBindProcessor:
    def test_float_bind_processor_returns_none(self):
        assert FLOAT().bind_processor(None) is None


class TestDialectTypeResolution:
    def test_ischema_name_synonyms_map_to_expected_types(self):
        assert TiberoDialect.ischema_names["LONG VARCHAR"] is VARCHAR2
        assert TiberoDialect.ischema_names["TIMESTAMP WITH TIME ZONE"] is TIMESTAMP
        assert TiberoDialect.ischema_names["TIMESTAMP WITH LOCAL TIME ZONE"] is TIMESTAMP

    def test_resolve_timestamp_variants(self):
        dialect = TiberoDialect()

        resolved = dialect._resolve_column_type("TIMESTAMP WITH TIME ZONE", None, None, None)
        assert isinstance(resolved, TIMESTAMP)

        resolved = dialect._resolve_column_type("TIMESTAMP WITH LOCAL TIME ZONE", None, None, None)
        assert isinstance(resolved, TIMESTAMP)
