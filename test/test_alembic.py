from __future__ import annotations

from sqlalchemy_pytibero.alembic_impl import TiberoImpl


class TestTiberoAlembicImpl:
    def test_import_and_attributes(self):
        assert TiberoImpl.__dialect__ == "tibero"
        assert TiberoImpl.transactional_ddl is False
