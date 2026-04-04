import sys

if "--dburi" in sys.argv or any(a.startswith("--dburi=") for a in sys.argv):
    from sqlalchemy.dialects import registry

    registry.register("tibero", "sqlalchemy_pytibero.dialect", "TiberoDialect")
    registry.register("tibero.pytibero", "sqlalchemy_pytibero.dialect", "TiberoDialect")

    import pytest

    pytest.register_assert_rewrite("sqlalchemy.testing.assertions")

    from sqlalchemy.testing.plugin.pytestplugin import *  # noqa: E402, F401, F403
