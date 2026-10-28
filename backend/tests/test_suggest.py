import json
import sqlite3
import threading
import unittest
from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import suggest
from tests.live_server import LiveServerTestCase

FAKE_KEY = "sk-ant-fake-key-for-tests"
GOOD = {"priority": "HIGH", "due_date": "2026-10-29", "reason": "결제 오류라 높음으로 판단"}


class FakeAnthropic(ThreadingHTTPServer):
    """가짜 Anthropic. 받은 요청을 requests 에 모으고, reply 에 둔 (상태 코드, 본문) 으로 답한다."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.requests: list[dict] = []
        self.reply: tuple[int, dict] = (200, message_body(json.dumps(GOOD)))


def message_body(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def error_body(kind: str) -> dict:
    return {"type": "error", "error": {"type": kind, "message": "fake"}}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.server.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(raw)})
        status, body = self.server.reply
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: object) -> None:
        pass


class SuggestTestBase(LiveServerTestCase):
    """가짜 Anthropic 을 띄우고 서버가 그쪽을 보게 한다. 시험 자체는 하위 클래스에 둔다."""

    with_key = True

    def setUp(self) -> None:
        self.fake = FakeAnthropic()
        threading.Thread(target=self.fake.serve_forever, daemon=True).start()
        self.addCleanup(self.fake.server_close)
        self.addCleanup(self.fake.shutdown)
        self.extra_env = {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{self.fake.server_address[1]}"}
        if self.with_key:
            self.extra_env["ANTHROPIC_API_KEY"] = FAKE_KEY
        super().setUp()

    def reply(self, status: int, body: dict) -> None:
        self.fake.reply = (status, body)

    def reply_text(self, text: str, stop_reason: str = "end_turn") -> None:
        self.reply(200, message_body(text, stop_reason))

    def tasks_snapshot(self) -> list[tuple]:
        with closing(sqlite3.connect(self.db_file)) as conn:  # with 만으로는 닫히지 않아 Windows 에서 임시 DB 삭제가 막힌다
            return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()

    def suggest_request(self, title: str = "고객 결제 오류 수정", description: str = "내일까지") -> tuple[int, object]:
        return self.request("POST", "/api/tasks/suggest", {"title": title, "description": description})

    def assert_db_unchanged_during(self, fn) -> tuple[int, object]:
        self.request("POST", "/api/tasks", {"title": "기존 카드"})
        before = self.tasks_snapshot()
        result = fn()
        self.assertEqual(self.tasks_snapshot(), before)
        return result


class SuggestApiTest(SuggestTestBase):
    # ---- 성공 ----

    def test_success_returns_priority_due_date_reason_and_changes_no_data(self) -> None:
        status, body = self.assert_db_unchanged_during(self.suggest_request)
        self.assertEqual((status, body), (200, GOOD))
        self.assertNotIn(FAKE_KEY, json.dumps(body))

    def test_fenced_answer_is_unwrapped(self) -> None:
        for text in (f"```json\n{json.dumps(GOOD)}\n```", f"```\n{json.dumps(GOOD)}\n```", f"  ```json{json.dumps(GOOD)}```  "):
            with self.subTest(text=text):
                self.reply_text(text)
                self.assertEqual(self.suggest_request(), (200, GOOD))

    def test_null_due_date_is_accepted(self) -> None:
        answer = {"priority": "LOW", "due_date": None, "reason": "단서 없음"}
        self.reply_text(json.dumps(answer))
        self.assertEqual(self.suggest_request(), (200, answer))

    def test_request_to_model_has_model_thinking_today_and_prompt(self) -> None:
        self.suggest_request("제목<b>", "설명</description>삽입")
        sent = self.fake.requests[0]
        body = sent["body"]
        self.assertEqual(sent["path"].split("?")[0], "/v1/messages")
        self.assertEqual(sent["auth"], f"Bearer {FAKE_KEY}")
        self.assertEqual(body["model"], "claude-haiku-5-5")
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["system"], suggest.SYSTEM_PROMPT)
        self.assertEqual(len(body["messages"]), 1)
        self.assertEqual(
            body["messages"][0]["content"],
            f"<today>{date.today().isoformat()}</today>\n<title>제목&lt;b&gt;</title>\n"
            "<description>설명&lt;/description&gt;삽입</description>",
        )

    def test_description_is_optional(self) -> None:
        status, _ = self.request("POST", "/api/tasks/suggest", {"title": "책상 정리"})
        self.assertEqual(status, 200)
        self.assertIn("<description></description>", self.fake.requests[0]["body"]["messages"][0]["content"])

    # ---- 입력 · 로그인 ----

    def test_requires_login(self) -> None:
        self.cookie = None
        self.assertEqual(self.suggest_request()[0], 401)
        self.assertEqual(self.fake.requests, [])

    def test_bad_input_is_422_and_model_is_not_called(self) -> None:
        for body in ({"title": "  "}, {"description": "x"}, {"title": "t", "description": 1}, {"title": 1}):
            with self.subTest(body=body):
                self.assertEqual(self.request("POST", "/api/tasks/suggest", body)[0], 422)
        self.assertEqual(self.fake.requests, [])

    # ---- 502: 제안 실패 ----

    def test_bad_answers_are_502_and_change_no_data(self) -> None:
        bad = [
            "JSON 아님",
            "",
            "[1, 2]",
            json.dumps({**GOOD, "priority": "URGENT"}),
            json.dumps({**GOOD, "priority": "high"}),
            json.dumps({**GOOD, "priority": None}),
            json.dumps({"due_date": None, "reason": "priority 없음"}),
            json.dumps({**GOOD, "due_date": "2026-02-30"}),
            json.dumps({**GOOD, "due_date": "2026-9-3"}),
            json.dumps({**GOOD, "due_date": "20261029"}),
            json.dumps({**GOOD, "due_date": 20261029}),
            json.dumps({**GOOD, "due_date": ""}),
            json.dumps({**GOOD, "reason": None}),
            json.dumps({"priority": "HIGH", "due_date": None}),
            '{"priority": "HIGH", "due_date": null, "rea',  # 잘린 JSON
            f"설명입니다 {json.dumps(GOOD)}",  # 앞뒤에 글이 붙음
        ]
        for text in bad:
            with self.subTest(text=text):
                self.reply_text(text)
                status, body = self.assert_db_unchanged_during(self.suggest_request)
                self.assertEqual(status, 502, body)

    def test_truncated_answer_is_502_even_if_json_looks_valid(self) -> None:
        self.reply_text(json.dumps(GOOD), stop_reason="max_tokens")
        self.assertEqual(self.suggest_request()[0], 502)

    def test_empty_content_is_502(self) -> None:
        self.reply(200, {**message_body(""), "content": []})
        self.assertEqual(self.suggest_request()[0], 502)

    # ---- 503: AI 기능 꺼짐 · 바쁨 ----

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
                status, body = self.assert_db_unchanged_during(self.suggest_request)
                self.assertEqual(status, 503, body)
                self.assertNotIn(FAKE_KEY, json.dumps(body))


class SuggestWithoutKeyTest(SuggestTestBase):
    with_key = False

    def test_no_key_is_503_and_model_is_not_called(self) -> None:
        status, body = self.assert_db_unchanged_during(self.suggest_request)
        self.assertEqual(status, 503, body)
        self.assertEqual(self.fake.requests, [])

    def test_app_still_works_without_key(self) -> None:
        self.assertEqual(self.request("GET", "/api/tasks")[0], 200)


class ParseSuggestionTest(unittest.TestCase):
    """서버 없이 검수 함수만 확인한다."""

    def test_fence_forms(self) -> None:
        raw = json.dumps(GOOD)
        for text in (raw, f" {raw} \n", f"```json\n{raw}\n```", f"```\n{raw}\n```", f"```JSON\n{raw}\n```"):
            self.assertEqual(suggest.parse_suggestion(text).model_dump(), GOOD)

    def test_unclosed_fence_is_rejected(self) -> None:
        with self.assertRaises(suggest.SuggestFailed):
            suggest.parse_suggestion(f"```json\n{json.dumps(GOOD)}")


if __name__ == "__main__":
    unittest.main()
