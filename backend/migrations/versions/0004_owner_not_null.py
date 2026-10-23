"""owner_id 를 비울 수 없게 바꾼다 (NOT NULL · 외래키)

SQLite 는 기존 열을 NOT NULL 로 바꿀 수 없어서 새 테이블을 만들어 옮긴다.
주인 없는 Task 가 남아 있으면 NOT NULL 에 걸려 이 단계 전체가 취소된다.

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

COPY_COLUMNS = "id, title, description, status, created_at, updated_at, owner_id"


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(
        """
        CREATE TABLE tasks_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            owner_id INTEGER NOT NULL REFERENCES users (id)
        )
        """
    )
    old_seq = bind.exec_driver_sql("SELECT seq FROM sqlite_sequence WHERE name = 'tasks'").scalar()
    op.execute(f"INSERT INTO tasks_new ({COPY_COLUMNS}) SELECT {COPY_COLUMNS} FROM tasks ORDER BY id")
    # 지워진 카드의 id 가 다시 쓰이지 않도록 자동 증가 값을 기존 값 이상으로 유지한다.
    if old_seq is not None:
        cur = bind.exec_driver_sql(
            "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = 'tasks_new'", (old_seq,)
        )
        if cur.rowcount == 0:
            bind.exec_driver_sql("INSERT INTO sqlite_sequence (name, seq) VALUES ('tasks_new', ?)", (old_seq,))
    op.execute("DROP TABLE tasks")
    op.execute("ALTER TABLE tasks_new RENAME TO tasks")
    op.execute("CREATE INDEX ix_tasks_owner_id ON tasks (owner_id)")


def downgrade() -> None:
    raise RuntimeError("되돌리기는 백업 파일로 한다 (DATA-MIGRATION-PLAN 4.6).")
