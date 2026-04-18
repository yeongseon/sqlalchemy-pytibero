from __future__ import annotations

import pytest

alembic = pytest.importorskip("alembic", reason="alembic not installed")

from sqlalchemy_pytibero.alembic_impl import TiberoImpl  # noqa: E402


class TestTiberoAlembicImpl:
    def test_import_and_attributes(self):
        assert TiberoImpl.__dialect__ == "tibero"
        assert TiberoImpl.transactional_ddl is False
