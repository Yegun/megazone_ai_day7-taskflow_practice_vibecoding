import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app import db
from app.schemas import Status, TaskCreate
from tests.live_server import upgrade_db


def _migrated_id() -> int:
    return db.get_user_by_username("migrated@test.com")["id"]


class DbTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "sub" / "test.db"
        os.environ["TASKFLOW_DB"] = str(self.path)
        self.addCleanup(os.environ.pop, "TASKFLOW_DB", None)


class InitDbTest(DbTestCase):
    def _upgrade(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        upgrade_db(str(self.path))

    def test_init_refuses_when_schema_is_not_migrated(self) -> None:
        with self.assertRaises(RuntimeError):
            db.init_db()

    def test_init_creates_folder_and_starts_empty_after_upgrade(self) -> None:
        self._upgrade()
        db.init_db()
        self.assertTrue(self.path.exists())
        self.assertEqual(db.list_tasks(_migrated_id()), [])

    def test_init_twice_keeps_data(self) -> None:
        self._upgrade()
        db.init_db()
        owner = _migrated_id()
        db.create_task(owner, TaskCreate(title="a"))
        db.init_db()
        self.assertEqual(len(db.list_tasks(owner)), 1)

    def test_storage_rejects_status_outside_three_values(self) -> None:
        self._upgrade()
        with self.assertRaises(sqlite3.IntegrityError):
            with db.session() as conn:
                conn.execute(
                    "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
                    " VALUES ('x', '', 'ARCHIVED', 'n', 'n', ?)",
                    (_migrated_id(),),
                )

    def test_storage_rejects_task_without_existing_owner(self) -> None:
        self._upgrade()
        with self.assertRaises(sqlite3.IntegrityError):
            with db.session() as conn:
                conn.execute(
                    "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
                    " VALUES ('x', '', 'TODO', 'n', 'n', 9999)"
                )


class CreateTaskTest(DbTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        upgrade_db(str(self.path))
        db.init_db()
        self.owner = _migrated_id()

    def test_new_task_is_todo_with_id_and_times(self) -> None:
        task = db.create_task(self.owner, TaskCreate(title="  할 일  ", description="설명"))
        self.assertEqual(task.title, "할 일")
        self.assertEqual(task.description, "설명")
        self.assertEqual(task.status, Status.TODO)
        self.assertEqual(task.created_at, task.updated_at)
        self.assertGreater(task.id, 0)

    def test_description_defaults_to_empty_string(self) -> None:
        self.assertEqual(db.create_task(self.owner, TaskCreate(title="a")).description, "")

    def test_list_is_in_registration_order_and_survives_new_connection(self) -> None:
        first = db.create_task(self.owner, TaskCreate(title="1"))
        second = db.create_task(self.owner, TaskCreate(title="2"))
        self.assertEqual([t.id for t in db.list_tasks(self.owner)], [first.id, second.id])


class TitleValidationTest(unittest.TestCase):
    def test_blank_titles_rejected(self) -> None:
        for title in ["", "   ", "\t\n"]:
            with self.subTest(title=title), self.assertRaises(ValidationError):
                TaskCreate(title=title)

    def test_missing_title_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TaskCreate()  # type: ignore[call-arg]


if __name__ == "__main__":
    unittest.main()
