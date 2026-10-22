import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .schemas import MIGRATED_USERNAME, Status, Task, TaskCreate, TaskUpdate, User

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "taskflow.db"


def db_path() -> Path:
    return Path(os.environ.get("TASKFLOW_DB", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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
    """저장소 폴더를 만들고, 스키마가 최신인지 확인한다 (D-007).

    스키마(users · sessions · tasks)는 Alembic 이 만든다. 앱은 자동으로 바꾸지 않는다.
    (원본 DB 는 백업 · 수량 확인 뒤에만 바꾸기 위해서다. DATA-MIGRATION-PLAN 4절)
    """
    db_path().parent.mkdir(parents=True, exist_ok=True)
    with session() as conn:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        has_owner = "tasks" in tables and any(
            r["name"] == "owner_id" for r in conn.execute("PRAGMA table_info(tasks)")
        )
    if not {"users", "sessions"} <= tables or not has_owner:
        raise RuntimeError("저장소 구조가 최신이 아닙니다. backend 에서 `alembic upgrade head` 를 실행하세요.")


def migrated_user_id() -> int:
    """임시: 로그인 API(단위 2~3)가 붙기 전까지 모든 요청을 이전용 사용자로 처리한다."""
    with session() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (MIGRATED_USERNAME,)).fetchone()
    return row["id"]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _to_task(row: sqlite3.Row) -> Task:
    return Task(**dict(row))


def list_tasks(owner_id: int) -> list[Task]:
    """owner_id 의 카드만 돌려준다 (R-008)."""
    with session() as conn:
        rows = conn.execute(
            "SELECT id, title, description, status, created_at, updated_at"
            " FROM tasks WHERE owner_id = ? ORDER BY id",
            (owner_id,),
        ).fetchall()
    return [_to_task(r) for r in rows]


_TASK_COLUMNS = "id, title, description, status, created_at, updated_at"


def update_task(owner_id: int, task_id: int, data: TaskUpdate) -> Task | None:
    """요청에 담긴 값만 바꾼다. 카드가 없거나 남의 카드면 None (둘을 구분하지 않는다)."""
    values = data.model_dump(exclude_unset=True)
    if "status" in values:
        values["status"] = values["status"].value
    # 열 이름은 TaskUpdate 의 필드에서만 오므로 SQL 에 그대로 쓴다.
    assignments = ", ".join(f"{col} = ?" for col in [*values, "updated_at"])
    with session() as conn:
        cur = conn.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ? AND owner_id = ?",
            (*values.values(), _now(), task_id, owner_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _to_task(row)


def delete_task(owner_id: int, task_id: int) -> bool:
    """저장소에서 실제로 지운다 (D-009). 카드가 없거나 남의 카드면 False."""
    with session() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, owner_id))
    return cur.rowcount > 0


def create_task(owner_id: int, data: TaskCreate) -> Task:
    now = _now()
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (data.title, data.description, Status.TODO.value, now, now, owner_id),
        )
        row = conn.execute(f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _to_task(row)


# ---- users · sessions (R-008) ----


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with session() as conn:
        return conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()


def create_user(username: str, password_hash: str) -> User:
    """이미 있는 아이디면 sqlite3.IntegrityError."""
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, _now()),
        )
    return User(id=cur.lastrowid, username=username)


def claim_migrated_user(password_hash: str) -> User | None:
    """비밀번호가 아직 없는 이전용 계정에 비밀번호를 정한다 (D-016). 이미 받아 갔으면 None."""
    with session() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ? AND password_hash IS NULL",
            (password_hash, MIGRATED_USERNAME),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT id, username FROM users WHERE username = ?", (MIGRATED_USERNAME,)).fetchone()
    return User(**dict(row))


def create_session(session_id: str, user_id: int, expires_at: str) -> None:
    with session() as conn:
        conn.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, _now(), expires_at),
        )


def get_session_user(session_id: str, now: str) -> User | None:
    """만료되지 않은 세션의 사용자. 없거나 만료면 None. now 와 expires_at 은 같은 UTC 형식 문자열."""
    with session() as conn:
        row = conn.execute(
            "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.id = ? AND s.expires_at > ?",
            (session_id, now),
        ).fetchone()
    return None if row is None else User(**dict(row))


def delete_session(session_id: str) -> None:
    with session() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def delete_expired_sessions(now: str) -> None:
    with session() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
