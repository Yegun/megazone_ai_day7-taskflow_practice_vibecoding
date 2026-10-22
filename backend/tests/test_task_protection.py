import sqlite3
import unittest

from tests.live_server import LiveServerTestCase

PW = "password-1234"
TASK_PATHS = [("GET", "/api/tasks", None), ("POST", "/api/tasks", {"title": "x"}),
              ("PATCH", "/api/tasks/1", {"title": "y"}), ("DELETE", "/api/tasks/1", None)]


class TaskProtectionTest(LiveServerTestCase):
    """API-SPEC-CHANGE 4절 시나리오 1~8."""

    auto_login = False

    def as_user(self, username: str) -> None:
        self.cookie = None
        status, _ = self.register(username, PW)
        self.assertEqual(status, 201)

    def make_bobs_task(self) -> int:
        self.as_user("bob0001")
        _, task = self.request("POST", "/api/tasks", {"title": "밥의 카드", "description": "비공개"})
        self.cookie = None
        return task["id"]

    def test_1_2_every_task_api_without_login_is_401(self) -> None:
        for method, path, body in TASK_PATHS:
            with self.subTest(method=method):
                self.assertEqual(self.request(method, path, body)[0], 401)

    def test_401_does_not_depend_on_task_existing(self) -> None:
        bobs = self.make_bobs_task()
        self.assertEqual(self.request("PATCH", f"/api/tasks/{bobs}", {"title": "y"})[0], 401)
        self.assertEqual(self.request("DELETE", f"/api/tasks/99999")[0], 401)

    def test_3_other_users_task_cannot_be_updated_and_stays_unchanged(self) -> None:
        bobs = self.make_bobs_task()
        self.as_user("alice01")
        status, _ = self.request("PATCH", f"/api/tasks/{bobs}", {"title": "해킹", "status": "DONE"})
        self.assertEqual(status, 404)
        self.login("bob0001", PW)
        (task,) = self.request("GET", "/api/tasks")[1]
        self.assertEqual((task["title"], task["description"], task["status"]), ("밥의 카드", "비공개", "TODO"))
        self.assertEqual(task["updated_at"], task["created_at"])

    def test_4_other_users_task_cannot_be_deleted(self) -> None:
        bobs = self.make_bobs_task()
        self.as_user("alice01")
        self.assertEqual(self.request("DELETE", f"/api/tasks/{bobs}")[0], 404)
        self.login("bob0001", PW)
        self.assertEqual(len(self.request("GET", "/api/tasks")[1]), 1)

    def test_5_own_task_can_be_updated(self) -> None:
        self.as_user("alice01")
        _, mine = self.request("POST", "/api/tasks", {"title": "내 카드"})
        status, body = self.request("PATCH", f"/api/tasks/{mine['id']}", {"status": "DONE"})
        self.assertEqual((status, body["status"]), (200, "DONE"))
        self.assertEqual(self.request("DELETE", f"/api/tasks/{mine['id']}")[0], 204)

    def test_6_list_has_only_own_tasks(self) -> None:
        self.make_bobs_task()
        self.as_user("alice01")
        self.assertEqual(self.request("GET", "/api/tasks"), (200, []))
        _, mine = self.request("POST", "/api/tasks", {"title": "앨리스"})
        self.assertEqual(self.request("GET", "/api/tasks")[1], [mine])

    def test_7_after_logout_same_session_is_401(self) -> None:
        self.as_user("alice01")
        old = self.cookie
        self.request("POST", "/api/auth/logout")
        self.cookie = old
        self.assertEqual(self.request("GET", "/api/tasks")[0], 401)

    def test_8_unknown_id_and_others_task_get_identical_404(self) -> None:
        bobs = self.make_bobs_task()
        self.as_user("alice01")
        for method, body in [("PATCH", {"title": "y"}), ("DELETE", None)]:
            with self.subTest(method=method):
                others = self.request(method, f"/api/tasks/{bobs}", body)
                unknown = self.request(method, "/api/tasks/99999", body)
                self.assertEqual(others, unknown)
                self.assertEqual(others[0], 404)

    def test_new_task_owner_is_logged_in_user_and_body_owner_is_ignored(self) -> None:
        self.as_user("bob0001")
        bob_id = self.request("GET", "/api/auth/me")[1]["id"]
        self.as_user("alice01")
        alice_id = self.request("GET", "/api/auth/me")[1]["id"]
        _, task = self.request("POST", "/api/tasks", {"title": "t", "owner_id": bob_id})
        self.assertNotIn("owner_id", task)
        conn = sqlite3.connect(self.db_file)
        (owner,) = conn.execute("SELECT owner_id FROM tasks WHERE id = ?", (task["id"],)).fetchone()
        conn.close()
        self.assertEqual(owner, alice_id)

    def test_owner_cannot_be_changed_by_patch(self) -> None:
        self.as_user("alice01")
        _, mine = self.request("POST", "/api/tasks", {"title": "t"})
        self.request("PATCH", f"/api/tasks/{mine['id']}", {"title": "u", "owner_id": 1})
        conn = sqlite3.connect(self.db_file)
        (owner,) = conn.execute("SELECT owner_id FROM tasks WHERE id = ?", (mine["id"],)).fetchone()
        mine_id = conn.execute("SELECT id FROM users WHERE username = 'alice01'").fetchone()[0]
        conn.close()
        self.assertEqual(owner, mine_id)

    def test_migrated_tasks_go_to_whoever_claims_the_account(self) -> None:
        conn = sqlite3.connect(self.db_file)
        conn.execute(
            "INSERT INTO tasks (title, description, status, created_at, updated_at, owner_id)"
            " VALUES ('옛 카드', '', 'TODO', 'n', 'n', (SELECT id FROM users WHERE username='migrated@test.com'))"
        )
        conn.commit()
        conn.close()
        self.as_user("alice01")
        self.assertEqual(self.request("GET", "/api/tasks")[1], [])
        self.cookie = None
        self.assertEqual(self.register("migrated@test.com", PW)[0], 201)
        self.assertEqual([t["title"] for t in self.request("GET", "/api/tasks")[1]], ["옛 카드"])


if __name__ == "__main__":
    unittest.main()
