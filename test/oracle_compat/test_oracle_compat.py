from __future__ import annotations

import os
import socket
import time
import unittest
import uuid

import oracledb
from sqlalchemy import (
    BLOB,
    CLOB,
    CHAR,
    INTEGER,
    NCHAR,
    NVARCHAR,
    VARCHAR,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Sequence,
    String,
    Table,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session


def _oracle_url() -> str:
    host = os.environ.get("SA_ORACLE_HOST", "localhost")
    port = os.environ.get("SA_ORACLE_PORT", "1521")
    service = os.environ.get("SA_ORACLE_SERVICE", "XEPDB1")
    user = os.environ.get("SA_ORACLE_USER", "testuser")
    password = os.environ.get("SA_ORACLE_PASSWORD", "TestUserPwd1")
    return f"oracle+oracledb://{user}:{password}@{host}:{port}/?service_name={service}"


def _oracle_dsn() -> str:
    host = os.environ.get("SA_ORACLE_HOST", "localhost")
    port = os.environ.get("SA_ORACLE_PORT", "1521")
    service = os.environ.get("SA_ORACLE_SERVICE", "XEPDB1")
    return f"{host}:{port}/{service}"


def _wait_for_port(host: str, port: int, timeout: int = 300) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(2)
    raise TimeoutError(f"Oracle XE service did not become ready on {host}:{port}")


_SKIP = os.getenv("SA_ORACLE_COMPAT_RUN") != "1"
_SUFFIX = uuid.uuid4().hex[:8].upper()


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.host = os.environ.get("SA_ORACLE_HOST", "localhost")
        cls.port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(cls.host, cls.port)
        cls.engine = create_engine(_oracle_url(), echo=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_connect_and_select_from_dual(self) -> None:
        conn = oracledb.connect(
            user=os.environ.get("SA_ORACLE_USER", "testuser"),
            password=os.environ.get("SA_ORACLE_PASSWORD", "TestUserPwd1"),
            dsn=_oracle_dsn(),
        )
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 1)
        finally:
            conn.close()

    def test_server_version_banner(self) -> None:
        with self.engine.connect() as conn:
            version = conn.execute(text("SELECT BANNER FROM V$VERSION")).scalar()
            self.assertIsNotNone(version)
            self.assertRegex(str(version), r"\d+")

    def test_default_schema(self) -> None:
        with self.engine.connect() as conn:
            schema = conn.execute(
                text("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
            ).scalar()
            self.assertIsNotNone(schema)
            self.assertEqual(
                str(schema).upper(), os.environ.get("SA_ORACLE_USER", "testuser").upper()
            )


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleDDLAndDML(unittest.TestCase):
    TABLE_NAME = f"ORA_COMPAT_CORE_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)
        with cls.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                CREATE TABLE {cls.TABLE_NAME} (
                    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    name VARCHAR2(100),
                    value INTEGER
                )
                """
                )
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {cls.TABLE_NAME}"))
        cls.engine.dispose()

    def test_01_insert(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO {self.TABLE_NAME} (name, value) VALUES (:name, :value)"),
                [{"name": "alpha", "value": 10}, {"name": "beta", "value": 20}],
            )
            conn.execute(
                text(f"INSERT INTO {self.TABLE_NAME} (name, value) VALUES (:name, :value)"),
                {"name": "gamma", "value": 30},
            )

    def test_02_select(self) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(f"SELECT name, value FROM {self.TABLE_NAME} ORDER BY value")
            ).fetchall()
            self.assertEqual(len(rows), 3)
            self.assertEqual([r[0] for r in rows], ["alpha", "beta", "gamma"])

    def test_03_update(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(f"UPDATE {self.TABLE_NAME} SET value = :value WHERE name = :name"),
                {"name": "beta", "value": 99},
            )
        with self.engine.connect() as conn:
            val = conn.execute(
                text(f"SELECT value FROM {self.TABLE_NAME} WHERE name = :name"),
                {"name": "beta"},
            ).scalar()
            self.assertEqual(val, 99)

    def test_04_delete(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(f"DELETE FROM {self.TABLE_NAME} WHERE name = :name"),
                {"name": "gamma"},
            )
        with self.engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")).scalar()
            self.assertEqual(count, 2)

    def test_05_offset_fetch(self) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"""
                SELECT name
                FROM {self.TABLE_NAME}
                ORDER BY value
                OFFSET 0 ROWS FETCH FIRST 1 ROWS ONLY
                """
                )
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "alpha")

            rows_offset = conn.execute(
                text(
                    f"""
                SELECT name
                FROM {self.TABLE_NAME}
                ORDER BY value
                OFFSET 1 ROWS FETCH FIRST 1 ROWS ONLY
                """
                )
            ).fetchall()
            self.assertEqual(len(rows_offset), 1)
            self.assertEqual(rows_offset[0][0], "beta")


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleSchemaReflection(unittest.TestCase):
    TABLE_PARENT = f"ORA_PARENT_{_SUFFIX}"
    TABLE_CHILD = f"ORA_CHILD_{_SUFFIX}"
    INDEX_NAME = f"IDX_ORA_CHILD_VAL_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)
        cls.metadata = MetaData()

        cls.parent = Table(
            cls.TABLE_PARENT,
            cls.metadata,
            Column("id", Integer, primary_key=True),
            Column("label", String(50)),
        )
        cls.child = Table(
            cls.TABLE_CHILD,
            cls.metadata,
            Column("id", Integer, primary_key=True),
            Column("parent_id", Integer, ForeignKey(f"{cls.TABLE_PARENT}.id")),
            Column("val", Integer),
        )
        Index(cls.INDEX_NAME, cls.child.c.val)
        cls.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_has_table(self) -> None:
        insp = inspect(self.engine)
        self.assertTrue(insp.has_table(self.TABLE_PARENT))
        self.assertFalse(insp.has_table("NONEXISTENT_ORACLE_COMPAT_TABLE"))

    def test_get_table_names(self) -> None:
        insp = inspect(self.engine)
        tables = [t.upper() for t in insp.get_table_names()]
        self.assertIn(self.TABLE_PARENT.upper(), tables)
        self.assertIn(self.TABLE_CHILD.upper(), tables)

    def test_get_columns(self) -> None:
        insp = inspect(self.engine)
        cols = insp.get_columns(self.TABLE_PARENT)
        col_names = [c["name"].upper() for c in cols]
        self.assertIn("ID", col_names)
        self.assertIn("LABEL", col_names)

    def test_get_pk_constraint(self) -> None:
        insp = inspect(self.engine)
        pk = insp.get_pk_constraint(self.TABLE_PARENT)
        pk_cols = [c.upper() for c in pk["constrained_columns"]]
        self.assertIn("ID", pk_cols)

    def test_get_foreign_keys(self) -> None:
        insp = inspect(self.engine)
        fks = insp.get_foreign_keys(self.TABLE_CHILD)
        self.assertGreaterEqual(len(fks), 1)
        fk = fks[0]
        self.assertEqual(fk["referred_table"].upper(), self.TABLE_PARENT.upper())
        self.assertIn("ID", [c.upper() for c in fk["referred_columns"]])

    def test_get_indexes(self) -> None:
        insp = inspect(self.engine)
        indexes = insp.get_indexes(self.TABLE_CHILD)
        idx_names = [i["name"].upper() for i in indexes]
        self.assertIn(self.INDEX_NAME.upper(), idx_names)


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleDataTypes(unittest.TestCase):
    TABLE_NAME = f"ORA_TYPES_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)
        with cls.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                CREATE TABLE {cls.TABLE_NAME} (
                    col_int       INTEGER,
                    col_bigint    NUMBER(19),
                    col_smallint  SMALLINT,
                    col_varchar   VARCHAR2(200),
                    col_char      CHAR(10),
                    col_nchar     NCHAR(30),
                    col_nvarchar  NVARCHAR2(100),
                    col_numeric   NUMERIC(12, 3),
                    col_float     FLOAT,
                    col_number    NUMBER,
                    col_date      DATE,
                    col_clob      CLOB,
                    col_blob      BLOB
                )
                """
                )
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {cls.TABLE_NAME}"))
        cls.engine.dispose()

    def test_reflect_column_types(self) -> None:
        insp = inspect(self.engine)
        cols = insp.get_columns(self.TABLE_NAME)
        reflected = {c["name"].upper(): c["type"] for c in cols}

        self.assertIsInstance(reflected["COL_INT"], INTEGER)
        self.assertEqual(getattr(reflected["COL_BIGINT"], "precision", None), 19)
        self.assertEqual(getattr(reflected["COL_NUMERIC"], "scale", None), 3)
        self.assertIsInstance(reflected["COL_VARCHAR"], VARCHAR)
        self.assertIsInstance(reflected["COL_CHAR"], CHAR)
        self.assertIsInstance(reflected["COL_NCHAR"], NCHAR)
        self.assertIsInstance(reflected["COL_NVARCHAR"], NVARCHAR)
        # Oracle reflects FLOAT as DOUBLE_PRECISION; accept either type.
        float_type_name = type(reflected["COL_FLOAT"]).__name__
        self.assertIn(float_type_name, ("FLOAT", "DOUBLE_PRECISION"))
        number_type_name = type(reflected["COL_NUMBER"]).__name__
        self.assertIn(number_type_name, ("NUMERIC", "NUMBER", "Numeric"))
        date_type_name = type(reflected["COL_DATE"]).__name__
        self.assertIn(date_type_name, ("DATE", "Date", "DATETIME"))
        self.assertIsInstance(reflected["COL_CLOB"], CLOB)
        self.assertIsInstance(reflected["COL_BLOB"], BLOB)


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleORM(unittest.TestCase):
    TABLE_NAME = f"ORA_ORM_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)

        seq_name = f"ORA_ORM_SEQ_{_SUFFIX}"
        cls.seq_name = seq_name

        class Base(DeclarativeBase):
            pass

        class User(Base):
            __tablename__ = cls.TABLE_NAME
            id = Column(Integer, Sequence(seq_name), primary_key=True)
            username = Column(String(64), nullable=False)
            email = Column(String(128))

        cls.Base = Base
        cls.User = User
        cls.Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_01_insert_query(self) -> None:
        with Session(self.engine) as session:
            session.add(self.User(username="alice", email="alice@test.local"))
            session.add(self.User(username="bob", email="bob@test.local"))
            session.commit()

        with Session(self.engine) as session:
            users = session.query(self.User).order_by(self.User.username).all()
            self.assertEqual(len(users), 2)
            self.assertEqual(users[0].username, "alice")
            self.assertEqual(users[1].username, "bob")

    def test_02_update(self) -> None:
        with Session(self.engine) as session:
            user = session.query(self.User).filter_by(username="alice").first()
            self.assertIsNotNone(user)
            user.email = "alice_new@test.local"
            session.commit()

        with Session(self.engine) as session:
            user = session.query(self.User).filter_by(username="alice").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, "alice_new@test.local")

    def test_03_delete(self) -> None:
        with Session(self.engine) as session:
            user = session.query(self.User).filter_by(username="bob").first()
            self.assertIsNotNone(user)
            session.delete(user)
            session.commit()

        with Session(self.engine) as session:
            count = session.query(self.User).count()
            self.assertEqual(count, 1)


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleIsolationLevel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_default_isolation_level(self) -> None:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM DUAL")).scalar()
            self.assertEqual(result, 1)
            dialect_level = self.engine.dialect.default_isolation_level
            self.assertIn(dialect_level, ("READ COMMITTED", "SERIALIZABLE", "AUTOCOMMIT"))

    def test_set_serializable(self) -> None:
        serializable_engine = create_engine(
            _oracle_url(), isolation_level="SERIALIZABLE", echo=False
        )
        try:
            with serializable_engine.connect() as conn:
                result = conn.execute(text("SELECT 1 FROM DUAL")).scalar()
                self.assertEqual(result, 1)
        finally:
            serializable_engine.dispose()


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleTransaction(unittest.TestCase):
    TABLE_NAME = f"ORA_TXN_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)
        with cls.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                CREATE TABLE {cls.TABLE_NAME} (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR2(50)
                )
                """
                )
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {cls.TABLE_NAME}"))
        cls.engine.dispose()

    def test_commit_persists(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO {self.TABLE_NAME} (id, name) VALUES (:id, :name)"),
                {"id": 1, "name": "committed"},
            )
        with self.engine.connect() as conn:
            value = conn.execute(
                text(f"SELECT name FROM {self.TABLE_NAME} WHERE id = :id"),
                {"id": 1},
            ).scalar()
            self.assertEqual(str(value).strip(), "committed")

    def test_rollback_reverts(self) -> None:
        conn = self.engine.connect()
        try:
            trans = conn.begin()
            conn.execute(
                text(f"INSERT INTO {self.TABLE_NAME} (id, name) VALUES (:id, :name)"),
                {"id": 2, "name": "rollback_me"},
            )
            trans.rollback()
        finally:
            conn.close()

        with self.engine.connect() as conn:
            count = conn.execute(
                text(f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE id = :id"),
                {"id": 2},
            ).scalar()
            self.assertEqual(count, 0)


@unittest.skipIf(_SKIP, "set SA_ORACLE_COMPAT_RUN=1")
class TestOracleSequence(unittest.TestCase):
    SEQ_NAME = f"ORA_SEQ_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        host = os.environ.get("SA_ORACLE_HOST", "localhost")
        port = int(os.environ.get("SA_ORACLE_PORT", "1521"))
        _wait_for_port(host, port)
        cls.engine = create_engine(_oracle_url(), echo=False)
        with cls.engine.begin() as conn:
            conn.execute(text(f"CREATE SEQUENCE {cls.SEQ_NAME} START WITH 1 INCREMENT BY 1"))

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.engine.begin() as conn:
            conn.execute(text(f"DROP SEQUENCE {cls.SEQ_NAME}"))
        cls.engine.dispose()

    def test_sequence_nextval(self) -> None:
        with self.engine.connect() as conn:
            val1 = conn.execute(text(f"SELECT {self.SEQ_NAME}.NEXTVAL FROM DUAL")).scalar()
            val2 = conn.execute(text(f"SELECT {self.SEQ_NAME}.NEXTVAL FROM DUAL")).scalar()
            self.assertIsNotNone(val1)
            self.assertIsNotNone(val2)
            self.assertEqual(val2, val1 + 1)

    def test_has_sequence_reflection(self) -> None:
        with self.engine.connect() as conn:
            insp = inspect(conn)
            has_sequence = insp.dialect.has_sequence(conn, self.SEQ_NAME)
            self.assertTrue(has_sequence)


if __name__ == "__main__":
    unittest.main()
