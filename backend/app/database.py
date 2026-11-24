from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from contextlib import contextmanager


def create_database(runtime_dir: Path) -> Engine:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{(runtime_dir / 'reportfix.db').as_posix()}", connect_args={"timeout": 5})

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record):
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()
    return engine


def database_ready(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1


@contextmanager
def immediate_transaction(engine: Engine):
    """Serialize SQLite read-then-write operations and roll back on failure."""
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
