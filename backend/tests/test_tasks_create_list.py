import unittest

from tests.live_server import LiveServerTestCase


class CreateListApiTest(LiveServerTestCase):
    def test_first_run_creates_file_and_returns_empty_list(self) -> None:
        status, body = self.request("GET", "/api/tasks")
        self.assertEqual((status, body), (200, []))

    def test_create_returns_201_todo_card_with_id(self) -> None:
        status, body = self.request("POST", "/api/tasks", {"title": "  첫 카드 ", "description": "설명"})
        self.assertEqual(status, 201)
        self.assertEqual(body["title"], "첫 카드")
        self.assertEqual(body["description"], "설명")
        self.assertEqual(body["status"], "TODO")
        self.assertIsInstance(body["id"], int)
        self.assertEqual(self.request("GET", "/api/tasks")[1], [body])

    def test_description_is_optional(self) -> None:
        status, body = self.request("POST", "/api/tasks", {"title": "제목만"})
        self.assertEqual((status, body["description"]), (201, ""))

    def test_blank_or_missing_title_is_rejected_and_nothing_saved(self) -> None:
        for payload in [{"title": ""}, {"title": "   "}, {"description": "설명만"}, {}]:
            with self.subTest(payload=payload):
                status, _ = self.request("POST", "/api/tasks", payload)
                self.assertEqual(status, 422)
        self.assertEqual(self.request("GET", "/api/tasks")[1], [])

    def test_cards_survive_server_restart(self) -> None:
        _, created = self.request("POST", "/api/tasks", {"title": "남아야 함"})
        self.restart_server()
        self.assertEqual(self.request("GET", "/api/tasks")[1], [created])


if __name__ == "__main__":
    unittest.main()
