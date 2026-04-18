"""Offline tests for the aioodbc async dialect."""

from __future__ import annotations

import pytest

aioodbc = pytest.importorskip("aioodbc")  # noqa: E402

from sqlalchemy.engine import make_url  # noqa: E402

from sqlalchemy_pytibero.aioodbc import TiberoDialectAsync_aioodbc  # noqa: E402


class TestTiberoDialectAsyncAioodbc:
    def setup_method(self):
        self.dialect = TiberoDialectAsync_aioodbc()

    def test_is_async(self):
        assert self.dialect.is_async is True

    def test_driver(self):
        assert self.dialect.driver == "aioodbc"

    def test_supports_statement_cache(self):
        assert TiberoDialectAsync_aioodbc.supports_statement_cache is True

    def test_create_connect_args_basic(self):
        url = make_url("tibero+aioodbc://user:pwd@myhost:8629/mydb")
        args, kwargs = self.dialect.create_connect_args(url)
        dsn = kwargs["dsn"]
        assert "DRIVER={Tibero 7 ODBC Driver}" in dsn
        assert "SERVER=myhost" in dsn
        assert "PORT=8629" in dsn
        assert "DB=mydb" in dsn
        assert "UID=user" in dsn
        assert "PWD=pwd" in dsn

    def test_create_connect_args_defaults(self):
        url = make_url("tibero+aioodbc://@localhost/")
        args, kwargs = self.dialect.create_connect_args(url)
        dsn = kwargs["dsn"]
        assert "SERVER=localhost" in dsn
        assert "DRIVER={Tibero 7 ODBC Driver}" in dsn

    def test_create_connect_args_no_database(self):
        url = make_url("tibero+aioodbc://user:pwd@host:8629/")
        args, kwargs = self.dialect.create_connect_args(url)
        dsn = kwargs["dsn"]
        assert "DB=" not in dsn

    def test_create_connect_args_custom_driver(self):
        url = make_url("tibero+aioodbc://user:pwd@host:8629/db?driver=MyDriver")
        args, kwargs = self.dialect.create_connect_args(url)
        dsn = kwargs["dsn"]
        assert "DRIVER={MyDriver}" in dsn

    def test_entry_point(self):
        from importlib.metadata import entry_points

        eps = entry_points(group="sqlalchemy.dialects", name="tibero.aioodbc")
        assert len(list(eps)) >= 1

    def test_name_inherited(self):
        assert self.dialect.name == "tibero"
