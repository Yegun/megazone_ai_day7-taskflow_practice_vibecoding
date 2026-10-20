import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app import db
from app.schemas import Status, TaskCreate


class DbTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "sub" / "test.db"
        os.environ["TASKFLOW_DB"] = str(self.path)
        self.addCleanup(os.environ.pop, "TASKFLOW_DB", None)


class InitDbTest(DbTestCase):
    def test_creates_file_and_starts_empty(self) -> None:
        self.assertFalse(self.path.exists())
        db.init_db()
        self.assertTrue(self.path.exists())
        self.assertEqual(db.list_tasks(), [])

    def test_init_twice_keeps_data(self) -> None:
        db.init_db()
        db.create_task(TaskCreate(title="a"))
        db.init_db()
        self.assertEqual(len(db.list_tasks()), 1)

    def test_storage_rejects_status_outside_three_values(self) -> None:
        db.init_db()
        with self.assertRaises(sqlite3.IntegrityError):
            with db.session() as conn:
                conn.execute(
                    "INSERT INTO tasks (title, description, status, created_at, updated_at)"
                    " VALUES ('x', '', 'ARCHIVED', 'n', 'n')"
                )


class CreateTaskTest(DbTestCase):
    def setUp(self) -> None:
        super().setUp()
        db.init_db()

    def test_new_task_is_todo_with_id_and_times(self) -> None:
        task = db.create_task(TaskCreate(title="  할 일  ", description="설명"))
        self.assertEqual(task.title, "할 일")
        self.assertEqual(task.description, "설명")
        self.assertEqual(task.status, Status.TODO)
        self.assertEqual(task.created_at, task.updated_at)
        self.assertGreater(task.id, 0)

    def test_description_defaults_to_empty_string(self) -> None:
        self.assertEqual(db.create_task(TaskCreate(title="a")).description, "")

    def test_list_is_in_registration_order_and_survives_new_connection(self) -> None:
        first = db.create_task(TaskCreate(title="1"))
        second = db.create_task(TaskCreate(title="2"))
        self.assertEqual([t.id for t in db.list_tasks()], [first.id, second.id])


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
