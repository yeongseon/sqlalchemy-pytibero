# pyright: reportIncompatibleMethodOverride=false, reportArgumentType=false
from __future__ import annotations

from sqlalchemy.sql import compiler
from sqlalchemy.sql import sqltypes


class TiberoCompiler(compiler.SQLCompiler):
    def visit_sysdate_func(self, fn, **kw):
        return "SYSDATE"

    def visit_systimestamp_func(self, fn, **kw):
        return "SYSTIMESTAMP"

    def visit_dual_func(self, fn, **kw):
        return "DUAL"

    def visit_nvl_func(self, fn, **kw):
        return "NVL(%s)" % self.function_argspec(fn, **kw)

    def default_from(self):
        return " FROM DUAL"

    def visit_cast(self, cast, **kw):
        type_ = self.process(cast.typeclause)
        if type_ is None:
            return self.process(cast.clause.self_group())
        return f"CAST({self.process(cast.clause)} AS {type_})"

    def render_literal_value(self, value, type_):
        value = super().render_literal_value(value, type_)
        return value.replace("\\", "\\\\")

    def get_select_precolumns(self, select, **kw):
        if bool(select._distinct):
            return "DISTINCT "
        return ""

    def visit_join(self, join, asfrom=False, **kwargs):
        return "".join(
            (
                self.process(join.left, asfrom=True, **kwargs),
                (join.isouter and " LEFT OUTER JOIN " or " INNER JOIN "),
                self.process(join.right, asfrom=True, **kwargs),
                " ON ",
                self.process(join.onclause, **kwargs),
            )
        )

    def for_update_clause(self, select, **kw):
        if select._for_update_arg is None:
            return ""
        text = " FOR UPDATE"
        if select._for_update_arg.of:
            text += " OF " + ", ".join(self.process(col, **kw) for col in select._for_update_arg.of)
        if select._for_update_arg.nowait:
            text += " NOWAIT"
        return text

    def limit_clause(self, select, **kw):
        limit_clause = select._limit_clause
        offset_clause = select._offset_clause
        if limit_clause is None and offset_clause is None:
            return ""
        if limit_clause is None and offset_clause is not None:
            return "\n OFFSET %s ROWS" % self.process(offset_clause, **kw)
        if offset_clause is not None:
            return "\n OFFSET %s ROWS FETCH FIRST %s ROWS ONLY" % (
                self.process(offset_clause, **kw),
                self.process(limit_clause, **kw),
            )
        return "\n FETCH FIRST %s ROWS ONLY" % self.process(limit_clause, **kw)


class TiberoDDLCompiler(compiler.DDLCompiler):
    def get_column_specification(self, column, **kw):
        colspec = [
            self.preparer.format_column(column),
            self.dialect.type_compiler_instance.process(column.type, type_expression=column),
        ]

        if not column.nullable:
            colspec.append("NOT NULL")

        if (
            column.table is not None
            and column is column.table._autoincrement_column
            and column.server_default is None
        ):
            colspec.append("GENERATED ALWAYS AS IDENTITY")
        else:
            default = self.get_column_default_string(column)
            if default is not None:
                colspec.append("DEFAULT " + default)

        return " ".join(colspec)

    def post_create_table(self, table):
        if table.comment is None:
            return ""
        literal = self.sql_compiler.render_literal_value(table.comment, sqltypes.String())
        return f"\nCOMMENT ON TABLE {self.preparer.format_table(table)} IS {literal}"

    def visit_set_table_comment(self, create, **kw):
        return "COMMENT ON TABLE %s IS %s" % (
            self.preparer.format_table(create.element),
            self.sql_compiler.render_literal_value(create.element.comment, sqltypes.String()),
        )

    def visit_drop_table_comment(self, drop, **kw):
        return "COMMENT ON TABLE %s IS ''" % (self.preparer.format_table(drop.element),)

    def visit_set_column_comment(self, create, **kw):
        return "COMMENT ON COLUMN %s.%s IS %s" % (
            self.preparer.format_table(create.element.table),
            self.preparer.format_column(create.element),
            self.sql_compiler.render_literal_value(create.element.comment, sqltypes.String()),
        )


class TiberoTypeCompiler(compiler.GenericTypeCompiler):
    def visit_BOOLEAN(self, type_, **kw):
        return "NUMBER(1)"

    def visit_NUMERIC(self, type_, **kw):
        if type_.precision is None:
            return "NUMERIC"
        if type_.scale is None:
            return f"NUMERIC({type_.precision})"
        return f"NUMERIC({type_.precision}, {type_.scale})"

    def visit_NUMBER(self, type_, **kw):
        if type_.precision is None:
            return "NUMBER"
        if type_.scale is None:
            return f"NUMBER({type_.precision})"
        return f"NUMBER({type_.precision}, {type_.scale})"

    def visit_DECIMAL(self, type_, **kw):
        if type_.precision is None:
            return "DECIMAL"
        if type_.scale is None:
            return f"DECIMAL({type_.precision})"
        return f"DECIMAL({type_.precision}, {type_.scale})"

    def visit_FLOAT(self, type_, **kw):
        if type_.precision is None:
            return "FLOAT"
        return f"FLOAT({type_.precision})"

    def visit_BINARY_FLOAT(self, type_, **kw):
        return "BINARY_FLOAT"

    def visit_BINARY_DOUBLE(self, type_, **kw):
        return "BINARY_DOUBLE"

    def visit_SMALLINT(self, type_, **kw):
        return "SMALLINT"

    def visit_INTEGER(self, type_, **kw):
        return "INTEGER"

    def visit_BIGINT(self, type_, **kw):
        return "NUMBER(19)"

    def visit_VARCHAR(self, type_, **kw):
        return self.visit_VARCHAR2(type_, **kw)

    def visit_VARCHAR2(self, type_, **kw):
        if type_.length:
            return f"VARCHAR2({type_.length})"
        return "VARCHAR2"

    def visit_CHAR(self, type_, **kw):
        if getattr(type_, "national", False):
            return self.visit_NCHAR(type_, **kw)
        if type_.length:
            return f"CHAR({type_.length})"
        return "CHAR"

    def visit_NCHAR(self, type_, **kw):
        if type_.length:
            return f"NCHAR({type_.length})"
        return "NCHAR"

    def visit_NVARCHAR(self, type_, **kw):
        return self.visit_NVARCHAR2(type_, **kw)

    def visit_NVARCHAR2(self, type_, **kw):
        if type_.length:
            return f"NVARCHAR2({type_.length})"
        return "NVARCHAR2"

    def visit_CLOB(self, type_, **kw):
        return "CLOB"

    def visit_NCLOB(self, type_, **kw):
        return "NCLOB"

    def visit_BLOB(self, type_, **kw):
        return "BLOB"

    def visit_RAW(self, type_, **kw):
        if getattr(type_, "length", None):
            return f"RAW({type_.length})"
        return "RAW"

    def visit_LONG(self, type_, **kw):
        return "LONG"

    def visit_LONG_RAW(self, type_, **kw):
        return "LONG RAW"

    def visit_ROWID(self, type_, **kw):
        return "ROWID"

    def visit_DATE(self, type_, **kw):
        return "DATE"

    def visit_TIMESTAMP(self, type_, **kw):
        return "TIMESTAMP"

    def visit_INTERVAL_YEAR_TO_MONTH(self, type_, **kw):
        return "INTERVAL YEAR TO MONTH"

    def visit_INTERVAL_DAY_TO_SECOND(self, type_, **kw):
        return "INTERVAL DAY TO SECOND"

    def visit_large_binary(self, type_, **kw):
        return "BLOB"

    def visit_text(self, type_, **kw):
        return "CLOB"

    def visit_datetime(self, type_, **kw):
        return "DATE"
