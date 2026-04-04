# pyright: reportUnsafeMultipleInheritance=false, reportMissingTypeArgument=false
from __future__ import annotations

import inspect

from sqlalchemy.sql import sqltypes


class _NumericType:
    def __init__(self, **kw):
        super().__init__(**kw)


class _FloatType(_NumericType, sqltypes.Float):
    def __init__(self, precision=None, **kw):
        super().__init__(precision=precision, **kw)


class _IntegerType(_NumericType, sqltypes.Integer):
    def __init__(self, **kw):
        super().__init__(**kw)


class _StringType(sqltypes.String):
    def __init__(self, national=False, values=None, **kw):
        self.national = national
        self.values = values
        super().__init__(**kw)

    def __repr__(self):
        try:
            sig = inspect.signature(self.__class__.__init__)
            attributes = [p.name for p in sig.parameters.values() if p.name != "self"]
        except (ValueError, TypeError):
            attributes = []

        params = {}
        for attr in attributes:
            val = getattr(self, attr, None)
            if val is not None and val is not False:
                params[attr] = val

        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(f"{k}={v!r}" for k, v in params.items()),
        )


class NUMBER(_NumericType, sqltypes.NUMERIC):
    __visit_name__ = "NUMBER"

    def __init__(self, precision=None, scale=None, **kw):
        super().__init__(precision=precision, scale=scale, **kw)


class NUMERIC(_NumericType, sqltypes.NUMERIC):
    __visit_name__ = "NUMERIC"

    def __init__(self, precision=None, scale=None, **kw):
        super().__init__(precision=precision, scale=scale, **kw)


class DECIMAL(_NumericType, sqltypes.DECIMAL):
    __visit_name__ = "DECIMAL"

    def __init__(self, precision=None, scale=None, **kw):
        super().__init__(precision=precision, scale=scale, **kw)


class FLOAT(_FloatType, sqltypes.FLOAT):
    __visit_name__ = "FLOAT"

    def __init__(self, precision=None, **kw):
        super().__init__(precision=precision, **kw)

    def bind_processor(self, dialect):
        return None


class BINARY_FLOAT(_FloatType):
    __visit_name__ = "BINARY_FLOAT"


class BINARY_DOUBLE(_FloatType):
    __visit_name__ = "BINARY_DOUBLE"


class SMALLINT(_IntegerType, sqltypes.SMALLINT):
    __visit_name__ = "SMALLINT"


class INTEGER(_IntegerType, sqltypes.INTEGER):
    __visit_name__ = "INTEGER"


class BIGINT(_IntegerType, sqltypes.BIGINT):
    __visit_name__ = "BIGINT"


class VARCHAR2(_StringType, sqltypes.VARCHAR):
    __visit_name__ = "VARCHAR2"

    def __init__(self, length=None, **kwargs):
        super().__init__(length=length, **kwargs)


class CHAR(_StringType, sqltypes.CHAR):
    __visit_name__ = "CHAR"

    def __init__(self, length=None, **kwargs):
        super().__init__(length=length, **kwargs)


class NCHAR(_StringType, sqltypes.NCHAR):
    __visit_name__ = "NCHAR"

    def __init__(self, length=None, **kwargs):
        kwargs["national"] = True
        super().__init__(length=length, **kwargs)


class NVARCHAR2(_StringType, sqltypes.NVARCHAR):
    __visit_name__ = "NVARCHAR2"

    def __init__(self, length=None, **kwargs):
        kwargs["national"] = True
        super().__init__(length=length, **kwargs)


class CLOB(sqltypes.Text):
    __visit_name__ = "CLOB"


class NCLOB(sqltypes.Text):
    __visit_name__ = "NCLOB"


class BLOB(sqltypes.LargeBinary):
    __visit_name__ = "BLOB"


class DATE(sqltypes.DATE):
    __visit_name__ = "DATE"


class TIMESTAMP(sqltypes.TIMESTAMP):
    __visit_name__ = "TIMESTAMP"


class INTERVAL_YEAR_TO_MONTH(sqltypes.TypeEngine):
    __visit_name__ = "INTERVAL_YEAR_TO_MONTH"


class INTERVAL_DAY_TO_SECOND(sqltypes.TypeEngine):
    __visit_name__ = "INTERVAL_DAY_TO_SECOND"


class RAW(sqltypes.LargeBinary):
    __visit_name__ = "RAW"

    def __init__(self, length=None, **kw):
        self.length = length
        super().__init__(length=length, **kw)


class LONG_RAW(sqltypes.LargeBinary):
    __visit_name__ = "LONG_RAW"


class LONG(sqltypes.Text):
    __visit_name__ = "LONG"


class ROWID(sqltypes.TypeEngine):
    __visit_name__ = "ROWID"
