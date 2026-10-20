import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .schemas import Status, Task, TaskCreate

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "taskflow.db"


def db_path() -> Path:
    return Path(os.environ.get("TASKFLOW_DB", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    """트랜잭션 하나. 성공하면 커밋, 예외면 롤백하고 항상 연결을 닫는다."""
    conn = connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    """저장소 파일과 테이블이 없으면 만든다 (D-007)."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    allowed = ", ".join(f"'{s.value}'" for s in Status)
    with session() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL CHECK (status IN ({allowed})),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _to_task(row: sqlite3.Row) -> Task:
    return Task(**dict(row))


def list_tasks() -> list[Task]:
    with session() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [_to_task(r) for r in rows]


def create_task(data: TaskCreate) -> Task:
    now = _now()
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (data.title, data.description, Status.TODO.value, now, now),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _to_task(row)
