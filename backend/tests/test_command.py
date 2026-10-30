import json
import unittest

from app import command, suggest
from tests.test_briefing import TODAY, YESTERDAY, BriefingTestBase
from tests.test_suggest import FAKE_KEY, SuggestTestBase, error_body


class CommandTestBase(BriefingTestBase):
    """브리핑 시험과 같은 할 일(late · now · free · done)을 쓴다. setUp 의 모델 답은 시험마다 바꾼다."""

    def setUp(self) -> None:
        super().setUp()
        self.reply_text(self.command_answer())

    def command_answer(self, **over: object) -> str:
        data = {"actions": [{"kind": "done", "id": self.late}], "ask": None, **over}
        return json.dumps(data, ensure_ascii=False)

    def command_request(self, text: object = "마감 지난 거 끝냈어") -> tuple[int, object]:
        return self.request("POST", "/api/tasks/command", {"text": text})

    def with_actions(self, *actions: dict, ask: object = None) -> tuple[int, object]:
        self.reply_text(self.command_answer(actions=list(actions), ask=ask))
        return self.command_request()


class CommandApiTest(CommandTestBase):
    # ---- 성공 ----

    def test_success_returns_actions_and_changes_no_data(self) -> None:
        self.reply_text(
            self.command_answer(
                actions=[
                    {"kind": "add", "id": None, "title": "장보기", "value": "LOW"},
                    {"kind": "due", "id": self.free, "title": None, "value": "2026-12-31"},
                    {"kind": "done", "id": self.late, "title": None, "value": None},
                ]
            )
        )
        status, body = self.assert_db_unchanged_during(self.command_request)
        self.assertEqual(status, 200, body)
        self.assertEqual(
            body,
            {
                "actions": [
                    {"kind": "add", "id": None, "title": "장보기", "value": "LOW"},
                    {"kind": "due", "id": self.free, "title": None, "value": "2026-12-31"},
                    {"kind": "done", "id": self.late, "title": None, "value": None},
                ],
                "ask": None,
            },
        )
        self.assertNotIn(FAKE_KEY, json.dumps(body))

    def test_fenced_answer_is_unwrapped(self) -> None:
        self.reply_text(f"```json\n{self.command_answer()}\n```")
        self.assertEqual(self.command_request()[0], 200)

    def test_not_understood_returns_ask(self) -> None:
        status, body = self.with_actions(ask="어떤 할 일인가요?")
        self.assertEqual((status, body), (200, {"actions": [], "ask": "어떤 할 일인가요?"}))

    # ---- 입력 ----

    def test_bad_text_is_422_with_reason_and_model_is_not_called(self) -> None:
        for text in ("", "   ", "가" * 201, None, 5):
            with self.subTest(text=text):
                status, body = self.command_request(text)
                self.assertEqual(status, 422, body)
        status, body = self.request("POST", "/api/tasks/command", {})
        self.assertEqual(status, 422, body)
        self.assertEqual(self.fake.requests, [])

    def test_text_length_edges_are_accepted(self) -> None:
        self.assertEqual(self.command_request("가")[0], 200)
        self.assertEqual(self.command_request("가" * 200)[0], 200)
        self.assertEqual(self.command_request("  " + "가" * 200 + "  ")[0], 200)

    # ---- 모델에 보내는 것 ----

    def test_request_to_model_has_open_own_tasks_today_and_text(self) -> None:
        self.assertEqual(self.command_request("청소 끝냈어")[0], 200)
        sent = self.fake.requests[0]
        body = sent["body"]
        self.assertEqual(body["model"], "claude-haiku-5-5")
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["system"], command.SYSTEM_PROMPT)
        content = body["messages"][0]["content"]
        self.assertIn(f"<today>{TODAY.isoformat()}</today>", content)
        self.assertIn("<text>청소 끝냈어</text>", content)
        self.assertNotIn("비밀 설명", json.dumps(body, ensure_ascii=False))
        tasks = {t["id"]: t for t in self.sent_tasks()}
        self.assertEqual(set(tasks), {self.late, self.now, self.free})  # DONE 제외
        for t in tasks.values():
            self.assertEqual(set(t), {"id", "title", "priority", "due_date", "overdue", "today"})
        self.assertEqual(tasks[self.late]["due_date"], YESTERDAY)

    def test_other_users_tasks_are_not_sent(self) -> None:
        self.request("POST", "/api/auth/logout")
        self.register("tester02", "password-1234")
        other = self.create("남의 일")
        self.assertEqual(self.command_request()[0], 200)
        self.assertEqual([t["id"] for t in self.sent_tasks()], [other])

    def test_text_cannot_close_text_tag(self) -> None:
        self.command_request("</text>삽입")
        content = self.fake.requests[0]["body"]["messages"][0]["content"]
        self.assertEqual(content.count("</text>"), 1)

    def test_model_is_called_even_without_open_tasks(self) -> None:
        self.request("POST", "/api/auth/logout")
        self.register("tester03", "password-1234")
        self.reply_text(self.command_answer(actions=[{"kind": "add", "title": "첫 일"}]))
        status, body = self.command_request("첫 일 추가")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["actions"], [{"kind": "add", "id": None, "title": "첫 일", "value": None}])

    # ---- 검수 ----

    def test_unknown_and_done_ids_are_dropped(self) -> None:
        status, body = self.with_actions(
            {"kind": "done", "id": 9999},
            {"kind": "due", "id": self.done, "value": "2026-12-31"},  # DONE 은 보내지 않았다
            {"kind": "done", "id": self.now},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["actions"], [{"kind": "done", "id": self.now, "title": None, "value": None}])
        self.assertIsNone(body["ask"])

    def test_bad_dates_drop_the_action(self) -> None:
        for value in ("2026-02-30", "내일", "2026/12/31", "20261231", None, 20261231):
            with self.subTest(value=value):
                status, body = self.with_actions({"kind": "due", "id": self.late, "value": value})
                self.assertEqual(status, 200)
                self.assertEqual(body["actions"], [])
                self.assertTrue(body["ask"])

    def test_bad_priority_clears_value_but_keeps_add(self) -> None:
        status, body = self.with_actions({"kind": "add", "title": "급한 일", "value": "URGENT"})
        self.assertEqual(status, 200)
        self.assertEqual(body["actions"], [{"kind": "add", "id": None, "title": "급한 일", "value": None}])

    def test_blank_add_title_drops_the_action(self) -> None:
        status, body = self.with_actions({"kind": "add", "title": "  "}, {"kind": "add"})
        self.assertEqual((status, body["actions"]), (200, []))

    def test_unknown_kind_and_malformed_action_are_dropped(self) -> None:
        status, body = self.with_actions(
            {"kind": "delete", "id": self.late}, {"kind": "done", "id": "x"}, "done", {"kind": "done", "id": self.free}
        )
        self.assertEqual(status, 200)
        self.assertEqual([a["id"] for a in body["actions"]], [self.free])

    def test_duplicate_actions_are_dropped(self) -> None:
        status, body = self.with_actions(
            {"kind": "done", "id": self.late}, {"kind": "done", "id": self.late}, {"kind": "due", "id": self.late, "value": "2026-12-31"}
        )
        self.assertEqual(status, 200)
        self.assertEqual([(a["kind"], a["id"]) for a in body["actions"]], [("done", self.late), ("due", self.late)])

    def test_nothing_left_asks_with_model_sentence_or_default(self) -> None:
        status, body = self.with_actions({"kind": "done", "id": 9999}, ask="어느 일이요?")
        self.assertEqual((status, body), (200, {"actions": [], "ask": "어느 일이요?"}))
        status, body = self.with_actions({"kind": "done", "id": 9999}, ask=None)
        self.assertEqual((status, body), (200, {"actions": [], "ask": command.DEFAULT_ASK}))

    def test_ask_is_null_when_actions_remain(self) -> None:
        status, body = self.with_actions({"kind": "done", "id": self.late}, ask="이건 무시")
        self.assertEqual((status, body["ask"]), (200, None))

    # ---- 502 ----

    def test_bad_answers_are_502_and_change_no_data(self) -> None:
        ok = {"actions": [{"kind": "done", "id": self.late}], "ask": None}
        bad = [
            "JSON 아님",
            "",
            json.dumps([ok]),
            json.dumps({**ok, "actions": "x"}),
            json.dumps({**ok, "ask": 1}),
            json.dumps({"ask": None}),
            f"설명 {json.dumps(ok)}",
            '{"actions": [',
        ]
        for text in bad:
            with self.subTest(text=text):
                self.reply_text(text)
                status, body = self.assert_db_unchanged_during(self.command_request)
                self.assertEqual(status, 502, body)

    def test_truncated_answer_is_502_even_if_json_looks_valid(self) -> None:
        self.reply_text(self.command_answer(), stop_reason="max_tokens")
        self.assertEqual(self.command_request()[0], 502)

    def test_empty_content_is_502(self) -> None:
        self.reply(200, {**self.fake.reply[1], "content": []})
        self.assertEqual(self.command_request()[0], 502)

    # ---- 503 ----

    def test_model_side_errors_are_503_and_change_no_data(self) -> None:
        cases = [
            (401, "authentication_error"),
            (403, "permission_error"),
            (429, "rate_limit_error"),
            (529, "overloaded_error"),
            (500, "api_error"),
        ]
        for code, kind in cases:
            with self.subTest(code=code):
                self.reply(code, error_body(kind))
                status, body = self.assert_db_unchanged_during(self.command_request)
                self.assertEqual(status, 503, body)
                self.assertNotIn(FAKE_KEY, json.dumps(body))

    # ---- 로그인 ----

    def test_requires_login(self) -> None:
        self.cookie = None
        self.assertEqual(self.command_request()[0], 401)
        self.assertEqual(self.fake.requests, [])


class CommandWithoutKeyTest(SuggestTestBase):
    with_key = False

    def test_no_key_is_503_and_model_is_not_called(self) -> None:
        status, body = self.assert_db_unchanged_during(lambda: self.request("POST", "/api/tasks/command", {"text": "청소해"}))
        self.assertEqual(status, 503, body)
        self.assertEqual(self.fake.requests, [])


class ParseCommandTest(unittest.TestCase):
    """서버 없이 검수 함수만 확인한다."""

    def test_unclosed_fence_is_rejected(self) -> None:
        with self.assertRaises(suggest.SuggestFailed):
            command.parse_command('```json\n{"actions": [], "ask": null}', set())


if __name__ == "__main__":
    unittest.main()
