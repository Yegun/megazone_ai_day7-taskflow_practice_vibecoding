"""주인이 없는 기존 Task 를 모두 이전용 계정에 넘긴다 (D-016)

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

MIGRATED_USERNAME = "migrated@test.com"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        "UPDATE tasks SET owner_id = (SELECT id FROM users WHERE username = ?) WHERE owner_id IS NULL",
        (MIGRATED_USERNAME,),
    )


def downgrade() -> None:
    raise RuntimeError("되돌리기는 백업 파일로 한다 (DATA-MIGRATION-PLAN 4.6).")
