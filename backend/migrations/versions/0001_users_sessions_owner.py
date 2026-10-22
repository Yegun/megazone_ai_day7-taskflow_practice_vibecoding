"""users · sessions 추가, tasks.owner_id 추가 (#6, R-008)

기존 Task 는 이전용 계정 migrated@test.com 에 붙인다 (D-016).
이미 owner_id 가 있으면 건너뛴다.

Revision ID: 0001
Revises:
"""
from datetime import UTC, datetime

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

MIGRATED_USERNAME = "migrated@test.com"
COPY_COLUMNS = "id, title, description, status, created_at, updated_at"

# 허용 상태 세 값 (D-005, app/schemas.py Status 와 같은 값. 마이그레이션은 앱 코드가 바뀌어도 고정이어야 하므로 따로 적는다.)
STATUS_CHECK = "status IN ('TODO', 'IN_PROGRESS', 'DONE')"


def _tables() -> set[str]:
    rows = op.get_bind().exec_driver_sql("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {r[0] for r in rows}


def _task_columns() -> set[str]:
    rows = op.get_bind().exec_driver_sql("PRAGMA table_info(tasks)")
    return {r[1] for r in rows}


def upgrade() -> None:
    tables = _tables()
    if "tasks" in tables and "owner_id" in _task_columns():
        return

    op.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users (id),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_sessions_user_id ON sessions (user_id)")

    # 비밀번호 없이 만든다. 이 아이디로 처음 가입하는 사람이 비밀번호를 정한다 (D-016).
    now = datetime.now(UTC).isoformat(timespec="seconds")
    op.get_bind().exec_driver_sql(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, NULL, ?)",
        (MIGRATED_USERNAME, now),
    )

    op.execute(
        f"""
        CREATE TABLE tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK ({STATUS_CHECK}),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            owner_id INTEGER NOT NULL REFERENCES users (id)
        )
        """
    )

    if "tasks" in tables:
        bind = op.get_bind()
        old_seq = bind.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name = 'tasks'").scalar()
        op.execute(
            f"""
            INSERT INTO tasks_new ({COPY_COLUMNS}, owner_id)
            SELECT {COPY_COLUMNS}, (SELECT id FROM users WHERE username = '{MIGRATED_USERNAME}')
            FROM tasks ORDER BY id
            """
        )
        # 지워진 카드의 id 가 다시 쓰이지 않도록 자동 증가 값을 기존 값 이상으로 유지한다.
        if old_seq is not None:
            cur = bind.exec_driver_sql(
                "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = 'tasks_new'", (old_seq,)
            )
            if cur.rowcount == 0:
                bind.exec_driver_sql(
                    "INSERT INTO sqlite_sequence (name, seq) VALUES ('tasks_new', ?)", (old_seq,)
                )
        op.execute("DROP TABLE tasks")

    op.execute("ALTER TABLE tasks_new RENAME TO tasks")
    op.execute("CREATE INDEX ix_tasks_owner_id ON tasks (owner_id)")


def downgrade() -> None:
    raise RuntimeError("되돌리기는 백업 파일로 한다 (DATA-MIGRATION-PLAN 4.6).")
