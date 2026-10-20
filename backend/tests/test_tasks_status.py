import unittest

from tests.live_server import LiveServerTestCase

STATUSES = ["TODO", "IN_PROGRESS", "DONE"]


class StatusChangeApiTest(LiveServerTestCase):
    def create(self, title: str) -> dict:
        return self.request("POST", "/api/tasks", {"title": title})[1]

    def test_any_status_to_any_status(self) -> None:
        # 방향 제한이 없다 (D-010): 세 값 사이의 모든 이동이 된다.
        for start in STATUSES:
            for target in STATUSES:
                with self.subTest(start=start, target=target):
                    task = self.create(f"{start}->{target}")
                    self.request("PATCH", f"/api/tasks/{task['id']}", {"status": start})
                    status, body = self.request(
                        "PATCH", f"/api/tasks/{task['id']}", {"status": target}
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(body["status"], target)
                    self.assertEqual(body["title"], task["title"])

    def test_other_cards_are_unchanged(self) -> None:
        a, b = self.create("a"), self.create("b")
        self.request("PATCH", f"/api/tasks/{a['id']}", {"status": "DONE"})
        _, tasks = self.request("GET", "/api/tasks")
        by_id = {t["id"]: t for t in tasks}
        self.assertEqual(by_id[a["id"]]["status"], "DONE")
        self.assertEqual(by_id[b["id"]]["status"], "TODO")

    def test_status_outside_three_values_is_rejected_and_unchanged(self) -> None:
        task = self.create("x")
        for payload in [{"status": "ARCHIVED"}, {"status": ""}, {"status": "todo"}, {}]:
            with self.subTest(payload=payload):
                status, _ = self.request("PATCH", f"/api/tasks/{task['id']}", payload)
                self.assertEqual(status, 422)
        self.assertEqual(self.request("GET", "/api/tasks")[1][0]["status"], "TODO")

    def test_unknown_id_is_404(self) -> None:
        status, _ = self.request("PATCH", "/api/tasks/9999", {"status": "DONE"})
        self.assertEqual(status, 404)

    def test_status_survives_server_restart(self) -> None:
        task = self.create("남아야 함")
        self.request("PATCH", f"/api/tasks/{task['id']}", {"status": "IN_PROGRESS"})
        self.restart_server()
        self.assertEqual(self.request("GET", "/api/tasks")[1][0]["status"], "IN_PROGRESS")

    def test_nothing_changes_status_by_itself(self) -> None:
        # 자동 변경 없음 (D-006): 등록만 한 카드는 목록을 여러 번 읽어도 TODO 다.
        self.create("x")
        for _ in range(3):
            self.assertEqual(self.request("GET", "/api/tasks")[1][0]["status"], "TODO")


if __name__ == "__main__":
    unittest.main()
