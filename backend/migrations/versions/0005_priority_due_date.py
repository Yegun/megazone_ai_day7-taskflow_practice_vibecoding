"""tasks 에 우선순위(priority)와 마감일(due_date) 열을 더한다 (#26, R-009 · R-007)

- priority: 필수. LOW · NORMAL · HIGH 만 받는다. 기존 Task 는 모두 NORMAL 이 된다.
- due_date: 선택(NULL 허용). YYYY-MM-DD 문자열. 기존 Task 는 모두 NULL 이다.
열만 추가하므로 기존 행 · status CHECK · owner_id 외래키 · 자동 증가 id 는 그대로다.
되돌리기는 이 단계에 없다. 적용 전에 만든 백업 파일로 한다 (DATA-MIGRATION-PLAN 4.6).

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'NORMAL'"
        " CHECK (priority IN ('LOW', 'NORMAL', 'HIGH'))"
    )
    # date() 는 없는 날짜(2026-02-30)를 다른 날로 바꾸고 다른 형식은 NULL 로 돌려주므로, 원래 값과 같을 때만 받는다.
    op.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT CHECK (date(due_date) IS due_date)")
