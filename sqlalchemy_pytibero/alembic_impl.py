from __future__ import annotations

try:
    from alembic.ddl.impl import DefaultImpl
except ImportError:
    raise ImportError(
        "Alembic is required for migration support. Install it with: pip install sqlalchemy-pytibero[alembic]"
    ) from None


class TiberoImpl(DefaultImpl):
    __dialect__: str = "tibero"
    transactional_ddl: bool = False  # Tibero auto-commits DDL
