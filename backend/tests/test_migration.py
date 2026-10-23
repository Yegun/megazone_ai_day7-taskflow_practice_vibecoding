import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.live_server import upgrade_db

OLD_SCHEMA = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('TODO', 'IN_PROGRESS', 'DONE')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
ROWS = [
    (16, "a", "설명", "TODO", "2026-10-20T01:00:00+00:00", "2026-10-20T01:00:00+00:00"),
    (17, "b", "", "IN_PROGRESS", "2026-10-20T02:00:00+00:00", "2026-10-21T02:00:00+00:00"),
    (40, "c", "x", "DONE", "2026-10-20T03:00:00+00:00", "2026-10-20T03:00:00+00:00"),
]
COLS = "id, title, description, status, created_at, updated_at"


def snapshot(path: str) -> dict:
    """4.1 에서 기록하는 수량: 개수 · 상태별 개수 · id 범위 · 행 내용 해시 (owner_id 제외)."""
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(f"SELECT {COLS} FROM tasks ORDER BY id").fetchall()
        by_status = dict(conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
    finally:
        conn.close()
    return {
        "count": len(rows),
        "by_status": by_status,
        "min_id": min(r[0] for r in rows) if rows else None,
        "max_id": max(r[0] for r in rows) if rows else None,
        "hash": hashlib.sha256(repr(rows).encode()).hexdigest(),
    }


def columns(path: str, table: str) -> dict[str, tuple[str, int]]:
    """열 이름 -> (자료형, NOT NULL 여부)."""
    conn = sqlite3.connect(path)
    try:
        return {r[1]: (r[2], r[3]) for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def one(path: str, sql: str):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


def tables(path: str) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


class MigrationTest(unittest.TestCase):
    """DATA-MIGRATION-PLAN 의 네 단계를 하나씩 올리며 단계마다 확인한다."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = str(Path(self._tmp.name) / "old.db")

    def _make_old(self, *, deleted_last: bool = False) -> None:
        conn = sqlite3.connect(self.db)
        conn.execute(OLD_SCHEMA)
        conn.executemany(f"INSERT INTO tasks ({COLS}) VALUES (?, ?, ?, ?, ?, ?)", ROWS)
        if deleted_last:
            conn.execute("DELETE FROM tasks WHERE id = 40")  # 시퀀스는 40 을 기억한다
        conn.commit()
        conn.close()

    def test_0001_adds_structure_and_nullable_owner_without_touching_tasks(self) -> None:
        self._make_old()
        before = snapshot(self.db)
        upgrade_db(self.db, "0001")
        self.assertEqual(snapshot(self.db), before)
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM users"), 0)
        self.assertEqual(columns(self.db, "tasks")["owner_id"], ("INTEGER", 0))  # 비워도 됨
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM tasks WHERE owner_id IS NULL"), 3)
        self.assertTrue({"users", "sessions", "tasks"} <= tables(self.db))

    def test_0002_creates_only_the_migrated_user_without_password(self) -> None:
        self._make_old()
        upgrade_db(self.db, "0002")
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM users"), 1)
        self.assertEqual(one(self.db, "SELECT username FROM users"), "migrated@test.com")
        self.assertIsNone(one(self.db, "SELECT password_hash FROM users"))
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM tasks WHERE owner_id IS NULL"), 3)

    def test_0003_gives_every_task_to_the_migrated_user(self) -> None:
        self._make_old()
        before = snapshot(self.db)
        upgrade_db(self.db, "0003")
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM tasks WHERE owner_id IS NULL"), 0)
        self.assertEqual(
            one(self.db, "SELECT COUNT(*) FROM tasks WHERE owner_id = (SELECT id FROM users)"), 3
        )
        self.assertEqual(snapshot(self.db), before)

    def test_0004_makes_owner_required_and_keeps_everything(self) -> None:
        self._make_old()
        before = snapshot(self.db)
        upgrade_db(self.db, "0004")
        self.assertEqual(snapshot(self.db), before)
        self.assertEqual(columns(self.db, "tasks")["owner_id"], ("INTEGER", 1))  # 필수
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM tasks WHERE owner_id IS NULL"), 0)
        self.assertNotIn("tasks_new", tables(self.db))

    def test_0004_refuses_and_rolls_back_when_a_task_has_no_owner(self) -> None:
        self._make_old()
        upgrade_db(self.db, "0003")
        conn = sqlite3.connect(self.db)  # 0003 뒤에 owner 없는 Task 가 하나 생긴 상황
        conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at) VALUES ('x', '', 'TODO', 'n', 'n')"
        )
        conn.commit()
        conn.close()
        with self.assertRaises(Exception):
            upgrade_db(self.db, "0004")
        # 실패한 단계는 통째로 취소된다: tasks 는 그대로, 임시 테이블도 남지 않는다.
        self.assertEqual(columns(self.db, "tasks")["owner_id"][1], 0)
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM tasks"), 4)
        self.assertNotIn("tasks_new", tables(self.db))
        self.assertEqual(one(self.db, "SELECT version_num FROM alembic_version"), "0003")

    def test_new_task_id_continues_after_old_max_even_if_last_was_deleted(self) -> None:
        self._make_old(deleted_last=True)
        upgrade_db(self.db)
        conn = sqlite3.connect(self.db)
        owner = conn.execute("SELECT id FROM users").fetchone()[0]
        cur = conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES ('n', '', 'TODO', 'n', 'n', ?)",
            (owner,),
        )
        self.assertEqual(cur.lastrowid, 41)
        conn.close()

    def test_second_upgrade_changes_nothing(self) -> None:
        self._make_old()
        upgrade_db(self.db)
        before = snapshot(self.db)
        upgrade_db(self.db)
        self.assertEqual(snapshot(self.db), before)
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM users"), 1)

    def test_fresh_database_gets_full_schema(self) -> None:
        upgrade_db(self.db)
        self.assertEqual(one(self.db, "SELECT COUNT(*) FROM tasks"), 0)
        self.assertEqual(one(self.db, "SELECT username FROM users"), "migrated@test.com")
        self.assertEqual(columns(self.db, "tasks")["owner_id"], ("INTEGER", 1))


if __name__ == "__main__":
    unittest.main()
