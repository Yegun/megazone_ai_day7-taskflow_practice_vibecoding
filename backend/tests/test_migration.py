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


class MigrationTest(unittest.TestCase):
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

    def test_existing_tasks_are_kept_and_owned_by_migrated_user(self) -> None:
        self._make_old()
        before = snapshot(self.db)
        upgrade_db(self.db)
        self.assertEqual(snapshot(self.db), before)

        conn = sqlite3.connect(self.db)
        users = conn.execute("SELECT id, username, password_hash FROM users").fetchall()
        self.assertEqual([(u[1], u[2]) for u in users], [("migrated@test.com", None)])
        owners = {r[0] for r in conn.execute("SELECT owner_id FROM tasks")}
        self.assertEqual(owners, {users[0][0]})
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "sessions", "tasks"} <= tables)
        self.assertNotIn("tasks_new", tables)
        conn.close()

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
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
        conn.close()

    def test_fresh_database_gets_full_schema(self) -> None:
        upgrade_db(self.db)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT username FROM users").fetchall(), [("migrated@test.com",)])
        conn.close()


if __name__ == "__main__":
    unittest.main()
