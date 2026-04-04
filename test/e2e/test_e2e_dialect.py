from __future__ import annotations

import os
import socket
import time
import unittest
import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session


def _tibero_url() -> str:
    host = os.environ.get("SA_TIBERO_HOST", "localhost")
    port = os.environ.get("SA_TIBERO_PORT", "8629")
    database = os.environ.get("SA_TIBERO_DATABASE", "TIBERO")
    user = os.environ.get("SA_TIBERO_USER", "tibero")
    password = os.environ.get("SA_TIBERO_PASSWORD", "tmax")
    driver = os.environ.get("SA_TIBERO_DRIVER", "Tibero 7 ODBC Driver")
    return f"tibero+pytibero://{user}:{password}@{host}:{port}/{database}?driver={driver}"


def _wait_for_port(host: str, port: int, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(2)
    raise TimeoutError(f"Tibero service did not become ready on {host}:{port}")


_SKIP = not (os.getenv("SA_TIBERO_RUN_E2E") == "1")
_SUFFIX = uuid.uuid4().hex[:8].upper()


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_connect_and_select_from_dual(self) -> None:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM DUAL")).scalar()
            self.assertEqual(result, 1)

    def test_server_version(self) -> None:
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


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestDDLAndDML(unittest.TestCase):
    TABLE_NAME = f"E2E_CORE_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)
        cls.metadata = MetaData()
        cls.tbl = Table(
            cls.TABLE_NAME,
            cls.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(100)),
            Column("value", Integer),
        )
        cls.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_01_insert(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.tbl.insert().values(name="alpha", value=10))
            conn.execute(self.tbl.insert().values(name="beta", value=20))
            conn.execute(self.tbl.insert().values(name="gamma", value=30))

    def test_02_select(self) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(self.tbl.select().order_by(self.tbl.c.value)).fetchall()
            self.assertEqual(len(rows), 3)
            names = [r[1] for r in rows]
            self.assertEqual(names, ["alpha", "beta", "gamma"])

    def test_03_update(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.tbl.update().where(self.tbl.c.name == "beta").values(value=99))
        with self.engine.connect() as conn:
            row = conn.execute(self.tbl.select().where(self.tbl.c.name == "beta")).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[2], 99)

    def test_04_delete(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.tbl.delete().where(self.tbl.c.name == "gamma"))
        with self.engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")).scalar()
            self.assertEqual(count, 2)

    def test_05_limit_offset(self) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(
                self.tbl.select().order_by(self.tbl.c.value).limit(1).offset(0)
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][1], "alpha")

            rows_offset = conn.execute(
                self.tbl.select().order_by(self.tbl.c.value).limit(1).offset(1)
            ).fetchall()
            self.assertEqual(len(rows_offset), 1)
            self.assertEqual(rows_offset[0][1], "beta")


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestSchemaReflection(unittest.TestCase):
    TABLE_PARENT = f"E2E_PARENT_{_SUFFIX}"
    TABLE_CHILD = f"E2E_CHILD_{_SUFFIX}"
    INDEX_NAME = f"IDX_CHILD_VAL_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)
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
        self.assertFalse(insp.has_table("NONEXISTENT_TABLE_XYZ_99"))

    def test_get_table_names(self) -> None:
        insp = inspect(self.engine)
        tables = insp.get_table_names()
        upper_tables = [t.upper() for t in tables]
        self.assertIn(self.TABLE_PARENT.upper(), upper_tables)
        self.assertIn(self.TABLE_CHILD.upper(), upper_tables)

    def test_get_columns(self) -> None:
        insp = inspect(self.engine)
        cols = insp.get_columns(self.TABLE_PARENT)
        col_names = [c["name"].upper() for c in cols]
        self.assertIn("ID", col_names)
        self.assertIn("LABEL", col_names)

    def test_get_pk_constraint(self) -> None:
        insp = inspect(self.engine)
        pk = insp.get_pk_constraint(self.TABLE_PARENT)
        self.assertIsNotNone(pk)
        pk_cols = [c.upper() for c in pk["constrained_columns"]]
        self.assertIn("ID", pk_cols)

    def test_get_foreign_keys(self) -> None:
        insp = inspect(self.engine)
        fks = insp.get_foreign_keys(self.TABLE_CHILD)
        self.assertTrue(len(fks) >= 1)
        fk = fks[0]
        self.assertIn("ID", [c.upper() for c in fk["referred_columns"]])
        self.assertEqual(fk["referred_table"].upper(), self.TABLE_PARENT.upper())

    def test_get_indexes(self) -> None:
        insp = inspect(self.engine)
        indexes = insp.get_indexes(self.TABLE_CHILD)
        idx_names = [i["name"].upper() for i in indexes]
        self.assertIn(self.INDEX_NAME.upper(), idx_names)


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestDataTypes(unittest.TestCase):
    TABLE_NAME = f"E2E_TYPES_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)
        with cls.engine.begin() as conn:
            conn.execute(
                text(f"""
                CREATE TABLE {cls.TABLE_NAME} (
                    col_int       INTEGER,
                    col_bigint    NUMBER(19),
                    col_smallint  SMALLINT,
                    col_varchar   VARCHAR2(200),
                    col_char      CHAR(10),
                    col_nvarchar  NVARCHAR2(100),
                    col_numeric   NUMERIC(12, 3),
                    col_float     FLOAT,
                    col_number    NUMBER,
                    col_date      DATE,
                    col_clob      CLOB,
                    col_blob      BLOB
                )
            """)
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {cls.TABLE_NAME}"))
        cls.engine.dispose()

    def test_reflect_column_types(self) -> None:
        insp = inspect(self.engine)
        cols = insp.get_columns(self.TABLE_NAME)
        type_map = {c["name"].upper(): type(c["type"]).__name__ for c in cols}

        self.assertIn(type_map.get("COL_INT"), ("INTEGER", "Integer", "INT", "NUMBER"))
        self.assertIn(
            type_map.get("COL_SMALLINT"),
            ("SMALLINT", "SmallInteger", "NUMBER"),
        )
        self.assertIn(type_map.get("COL_VARCHAR"), ("VARCHAR2", "VARCHAR", "String"))
        self.assertIn(type_map.get("COL_CHAR"), ("CHAR", "String"))
        self.assertIn(type_map.get("COL_NUMERIC"), ("NUMERIC", "Numeric", "NUMBER"))
        self.assertIn(type_map.get("COL_DATE"), ("DATE", "Date"))

    def test_insert_and_read_types(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(f"""
                INSERT INTO {self.TABLE_NAME}
                    (col_int, col_bigint, col_smallint, col_varchar, col_char,
                     col_numeric, col_float, col_number, col_date)
                VALUES (42, 9999999999, 7, 'hello', 'world',
                        123.456, 1.5, 2.5, SYSDATE)
            """)
            )
        with self.engine.connect() as conn:
            row = conn.execute(
                text(f"""
                SELECT col_int, col_bigint, col_smallint, col_varchar, col_char,
                       col_numeric, col_float
                FROM {self.TABLE_NAME}
            """)
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 42)
            self.assertEqual(row[1], 9999999999)
            self.assertEqual(row[2], 7)
            self.assertEqual(row[3].strip(), "hello")


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestORM(unittest.TestCase):
    TABLE_NAME = f"E2E_ORM_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)

        class Base(DeclarativeBase):
            pass

        class User(Base):
            __tablename__ = cls.TABLE_NAME
            id = Column(Integer, primary_key=True, autoincrement=True)
            username = Column(String(64), nullable=False)
            email = Column(String(128))

        cls.Base = Base
        cls.User = User
        cls.Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_01_orm_insert_and_query(self) -> None:
        with Session(self.engine) as session:
            session.add(self.User(username="alice", email="alice@test.com"))
            session.add(self.User(username="bob", email="bob@test.com"))
            session.commit()

        with Session(self.engine) as session:
            users = session.query(self.User).order_by(self.User.username).all()
            self.assertEqual(len(users), 2)
            self.assertEqual(users[0].username, "alice")
            self.assertEqual(users[1].username, "bob")

    def test_02_orm_update(self) -> None:
        with Session(self.engine) as session:
            user = session.query(self.User).filter_by(username="alice").first()
            self.assertIsNotNone(user)
            user.email = "alice_new@test.com"
            session.commit()

        with Session(self.engine) as session:
            user = session.query(self.User).filter_by(username="alice").first()
            self.assertEqual(user.email, "alice_new@test.com")

    def test_03_orm_delete(self) -> None:
        with Session(self.engine) as session:
            user = session.query(self.User).filter_by(username="bob").first()
            self.assertIsNotNone(user)
            session.delete(user)
            session.commit()

        with Session(self.engine) as session:
            count = session.query(self.User).count()
            self.assertEqual(count, 1)


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestIsolationLevel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def test_default_isolation_level(self) -> None:
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT SYS_CONTEXT('USERENV', 'ISOLATION_LEVEL') FROM DUAL")
            ).scalar()
            self.assertIsNotNone(result)

    def test_set_isolation_level(self) -> None:
        eng = create_engine(
            _tibero_url(),
            isolation_level="SERIALIZABLE",
            echo=False,
        )
        try:
            with eng.connect() as conn:
                result = conn.execute(text("SELECT 1 FROM DUAL")).scalar()
                self.assertEqual(result, 1)
        finally:
            eng.dispose()


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestTransaction(unittest.TestCase):
    TABLE_NAME = f"E2E_TXN_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)
        with cls.engine.begin() as conn:
            conn.execute(
                text(f"""
                CREATE TABLE {cls.TABLE_NAME} (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR2(50)
                )
            """)
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {cls.TABLE_NAME}"))
        cls.engine.dispose()

    def test_commit(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(f"INSERT INTO {self.TABLE_NAME} (id, name) VALUES (1, 'committed')"))
        with self.engine.connect() as conn:
            row = conn.execute(text(f"SELECT name FROM {self.TABLE_NAME} WHERE id = 1")).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0].strip(), "committed")

    def test_rollback(self) -> None:
        conn = self.engine.connect()
        try:
            trans = conn.begin()
            conn.execute(
                text(f"INSERT INTO {self.TABLE_NAME} (id, name) VALUES (2, 'rollback_me')")
            )
            trans.rollback()
        finally:
            conn.close()

        with self.engine.connect() as conn:
            count = conn.execute(
                text(f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE id = 2")
            ).scalar()
            self.assertEqual(count, 0)


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestForUpdate(unittest.TestCase):
    TABLE_NAME = f"E2E_FORUPD_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)
        cls.metadata = MetaData()
        cls.tbl = Table(
            cls.TABLE_NAME,
            cls.metadata,
            Column("id", Integer, primary_key=True),
            Column("val", Integer),
        )
        cls.metadata.create_all(cls.engine)
        with cls.engine.begin() as conn:
            conn.execute(cls.tbl.insert().values(id=1, val=100))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_for_update(self) -> None:
        with self.engine.begin() as conn:
            row = conn.execute(
                self.tbl.select().where(self.tbl.c.id == 1).with_for_update()
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], 100)
            conn.execute(self.tbl.update().where(self.tbl.c.id == 1).values(val=200))
        with self.engine.connect() as conn:
            row = conn.execute(self.tbl.select().where(self.tbl.c.id == 1)).fetchone()
            self.assertEqual(row[1], 200)


@unittest.skipIf(_SKIP, "set SA_TIBERO_RUN_E2E=1 to run e2e tests")
class TestSequence(unittest.TestCase):
    SEQ_NAME = f"E2E_SEQ_{_SUFFIX}"

    @classmethod
    def setUpClass(cls) -> None:
        _wait_for_port(
            os.environ["SA_TIBERO_HOST"],
            int(os.environ["SA_TIBERO_PORT"]),
        )
        cls.engine = create_engine(_tibero_url(), echo=False)
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

    def test_has_sequence(self) -> None:
        insp = inspect(self.engine)
        self.assertTrue(insp.dialect.has_sequence(self.engine.connect(), self.SEQ_NAME))


if __name__ == "__main__":
    unittest.main()
