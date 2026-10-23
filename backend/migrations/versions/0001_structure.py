"""구조 추가: users · sessions 표와 tasks.owner_id 열 (#6, R-008)

owner_id 는 비워도 되는 열로 먼저 추가한다. 채우기(0003)와 필수로 바꾸기(0004)는 뒤 단계다.

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 새로 설치한 DB 에는 tasks 가 아직 없다. 이전 버전(owner_id 없음)과 같은 모양으로 먼저 만든다.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
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
    op.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER REFERENCES users (id)")


def downgrade() -> None:
    raise RuntimeError("되돌리기는 백업 파일로 한다 (DATA-MIGRATION-PLAN 4.6).")
