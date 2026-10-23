"""이전용 계정 migrated@test.com 을 비밀번호 없이 만든다 (D-016)

비밀번호 없는 계정은 로그인할 수 없다. 이 아이디로 처음 가입하는 사람이 비밀번호를 정하고 계정을 받는다.

Revision ID: 0002
Revises: 0001
"""
from datetime import UTC, datetime

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

MIGRATED_USERNAME = "migrated@test.com"


def upgrade() -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    op.get_bind().exec_driver_sql(
        "INSERT INTO users (username, password_hash, created_at)"
        " SELECT ?, NULL, ? WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = ?)",
        (MIGRATED_USERNAME, now, MIGRATED_USERNAME),
    )


def downgrade() -> None:
    raise RuntimeError("되돌리기는 백업 파일로 한다 (DATA-MIGRATION-PLAN 4.6).")
