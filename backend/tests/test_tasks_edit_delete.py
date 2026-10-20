import unittest

from tests.live_server import LiveServerTestCase


class EditDeleteApiTest(LiveServerTestCase):
    def create(self, title: str, description: str = "") -> dict:
        return self.request("POST", "/api/tasks", {"title": title, "description": description})[1]

    def patch(self, task: dict, body: object) -> tuple[int, object]:
        return self.request("PATCH", f"/api/tasks/{task['id']}", body)

    def tasks(self) -> list[dict]:
        return self.request("GET", "/api/tasks")[1]

    # ---- 수정 ----
    def test_edit_title_description_and_status_in_one_request(self) -> None:
        task = self.create("옛 제목", "옛 설명")
        status, body = self.patch(
            task, {"title": "  새 제목 ", "description": "새 설명", "status": "DONE"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            (body["title"], body["description"], body["status"]), ("새 제목", "새 설명", "DONE")
        )
        self.assertEqual(self.tasks(), [body])

    def test_values_not_sent_are_left_alone(self) -> None:
        task = self.create("제목", "설명")
        self.patch(task, {"status": "IN_PROGRESS"})
        _, body = self.patch(task, {"title": "바뀐 제목"})
        self.assertEqual((body["description"], body["status"]), ("설명", "IN_PROGRESS"))

    def test_description_can_be_cleared_with_empty_string(self) -> None:
        task = self.create("제목", "지울 설명")
        _, body = self.patch(task, {"description": ""})
        self.assertEqual(body["description"], "")

    def test_blank_title_is_rejected_and_nothing_changes(self) -> None:
        task = self.create("제목", "설명")
        for payload in [{"title": ""}, {"title": "   "}, {"title": "  ", "status": "DONE"}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.patch(task, payload)[0], 422)
        self.assertEqual(self.tasks(), [task])

    def test_empty_body_or_null_values_are_rejected(self) -> None:
        task = self.create("제목")
        for payload in [{}, {"title": None}, {"description": None}, {"status": None}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.patch(task, payload)[0], 422)
        self.assertEqual(self.tasks(), [task])

    def test_edit_unknown_id_is_404(self) -> None:
        self.assertEqual(self.request("PATCH", "/api/tasks/9999", {"title": "x"})[0], 404)

    def test_edit_survives_server_restart(self) -> None:
        task = self.create("제목")
        _, edited = self.patch(task, {"title": "고친 제목", "description": "고친 설명"})
        self.restart_server()
        self.assertEqual(self.tasks(), [edited])

    # ---- 삭제 ----
    def test_delete_returns_204_and_card_is_gone(self) -> None:
        keep, drop = self.create("남길 것"), self.create("지울 것")
        status, body = self.request("DELETE", f"/api/tasks/{drop['id']}")
        self.assertEqual((status, body), (204, None))
        self.assertEqual(self.tasks(), [keep])

    def test_deleted_card_does_not_come_back_after_restart(self) -> None:
        task = self.create("지울 것")
        self.request("DELETE", f"/api/tasks/{task['id']}")
        self.restart_server()
        self.assertEqual(self.tasks(), [])

    def test_delete_unknown_or_already_deleted_id_is_404(self) -> None:
        task = self.create("x")
        self.assertEqual(self.request("DELETE", f"/api/tasks/{task['id']}")[0], 204)
        self.assertEqual(self.request("DELETE", f"/api/tasks/{task['id']}")[0], 404)
        self.assertEqual(self.request("DELETE", "/api/tasks/9999")[0], 404)


if __name__ == "__main__":
    unittest.main()
