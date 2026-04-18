# pyright: reportMissingImports=false
"""aioodbc async dialect for Tibero."""

from __future__ import annotations

from sqlalchemy.connectors.aioodbc import aiodbcConnector

from sqlalchemy_pytibero.dialect import TiberoDialect


class TiberoDialectAsync_aioodbc(aiodbcConnector, TiberoDialect):
    driver = "aioodbc"
    supports_statement_cache = True

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username="user", database="database")
        query = dict(url.query)

        host = opts.get("host", "localhost")
        port = opts.get("port", 8629)
        database = opts.get("database", "")
        user = opts.get("user", "tibero")
        password = opts.get("password", "")
        driver_name = query.get("driver", "Tibero 7 ODBC Driver")

        parts = [f"DRIVER={{{driver_name}}}"]
        parts.append(f"SERVER={host}")
        parts.append(f"PORT={port}")
        if database:
            parts.append(f"DB={database}")
        if user:
            parts.append(f"UID={user}")
        if password:
            parts.append(f"PWD={password}")

        # Pass through extra query params as DSN attributes
        skip_keys = {"driver"}
        for key, value in query.items():
            if key.lower() not in skip_keys:
                parts.append(f"{key}={value}")

        dsn = ";".join(parts)
        return ([], {"dsn": dsn})


dialect = TiberoDialectAsync_aioodbc
