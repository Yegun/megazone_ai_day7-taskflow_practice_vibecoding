import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
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
        task_columns = (
            {r["name"] for r in conn.execute("PRAGMA table_info(tasks)")} if "tasks" in tables else set()
        )
    if not {"users", "sessions"} <= tables or not {"owner_id", "priority", "due_date"} <= task_columns:
        raise RuntimeError("저장소 구조가 최신이 아닙니다. backend 에서 `alembic upgrade head` 를 실행하세요.")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _today() -> str:
    """기한 초과의 기준이 되는 오늘. 서버 PC 의 로컬 날짜다 (이슈 #26)."""
    return date.today().isoformat()


def _to_task(row: sqlite3.Row) -> Task:
    return Task(**dict(row))


def list_tasks(owner_id: int) -> list[Task]:
    """owner_id 의 카드만 돌려준다 (R-008)."""
    with session() as conn:
        rows = conn.execute(
            f"SELECT {_TASK_COLUMNS} FROM tasks WHERE owner_id = ? ORDER BY {_SORT_ORDER}",
            (_today(), owner_id),
        ).fetchall()
    return [_to_task(r) for r in rows]


# `?` 하나는 오늘 날짜다. 기한 초과: 마감일이 오늘보다 이전이고 완료가 아닌 카드 (R-010).
_TASK_COLUMNS = (
    "id, title, description, status, priority, due_date,"
    " CASE WHEN due_date < ? AND status != 'DONE' THEN 1 ELSE 0 END AS is_overdue,"
    " created_at, updated_at"
)
# 서버 정렬 (R-011): ① 기한 초과 ② 우선순위 높음 먼저 ③ 가까운 마감일(없으면 맨 뒤) ④ 만든 순서(id).
_SORT_ORDER = (
    "is_overdue DESC,"
    " CASE priority WHEN 'HIGH' THEN 0 WHEN 'NORMAL' THEN 1 ELSE 2 END,"
    " due_date IS NULL, due_date, id"
)


def update_task(owner_id: int, task_id: int, data: TaskUpdate) -> Task | None:
    """요청에 담긴 값만 바꾼다. 카드가 없거나 남의 카드면 None (둘을 구분하지 않는다)."""
    values = data.model_dump(exclude_unset=True)
    if "status" in values:
        values["status"] = values["status"].value
    if "priority" in values:
        values["priority"] = values["priority"].value
    if values.get("due_date") is not None:
        values["due_date"] = values["due_date"].isoformat()
    # 열 이름은 TaskUpdate 의 필드에서만 오므로 SQL 에 그대로 쓴다.
    assignments = ", ".join(f"{col} = ?" for col in [*values, "updated_at"])
    with session() as conn:
        cur = conn.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ? AND owner_id = ?",
            (*values.values(), _now(), task_id, owner_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = ?", (_today(), task_id)).fetchone()
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
            "INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at, owner_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.title,
                data.description,
                Status.TODO.value,
                data.priority.value,
                None if data.due_date is None else data.due_date.isoformat(),
                now,
                now,
                owner_id,
            ),
        )
        row = conn.execute(f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = ?", (_today(), cur.lastrowid)).fetchone()
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
