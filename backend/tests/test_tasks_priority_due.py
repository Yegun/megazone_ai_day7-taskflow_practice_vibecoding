import sqlite3
import unittest
from datetime import date, timedelta

from tests.live_server import DEFAULT_USER, LiveServerTestCase


def day(offset: int) -> str:
    """오늘 기준 offset 일 뒤(음수면 전)의 날짜. 서버도 같은 PC 의 로컬 날짜를 쓴다."""
    return (date.today() + timedelta(days=offset)).isoformat()


class PriorityDueApiTest(LiveServerTestCase):
    def create(self, title: str = "t", **fields) -> dict:
        status, body = self.request("POST", "/api/tasks", {"title": title, **fields})
        self.assertEqual(status, 201, body)
        return body

    def patch(self, task_id: int, **fields) -> tuple[int, object]:
        return self.request("PATCH", f"/api/tasks/{task_id}", fields)

    def get(self, task_id: int) -> dict:
        return next(t for t in self.request("GET", "/api/tasks")[1] if t["id"] == task_id)

    def titles(self) -> list[str]:
        return [t["title"] for t in self.request("GET", "/api/tasks")[1]]

    # ---- 등록 (시나리오 9 · 10 · 11 · 17) ----

    def test_create_without_new_fields_gets_normal_and_no_due_date(self) -> None:
        card = self.create()
        self.assertEqual((card["priority"], card["due_date"], card["is_overdue"]), ("NORMAL", None, False))

    def test_create_with_priority_and_due_date_saves_them(self) -> None:
        card = self.create(priority="HIGH", due_date=day(3))
        self.assertEqual((card["priority"], card["due_date"]), ("HIGH", day(3)))
        self.assertEqual(self.get(card["id"]), card)

    def test_create_accepts_past_date_and_null_due_date(self) -> None:
        past = self.create("past", due_date=day(-30))
        self.assertEqual(past["due_date"], day(-30))
        self.assertEqual(self.create("none", due_date=None)["due_date"], None)

    def test_create_rejects_bad_priority_and_due_date_and_saves_nothing(self) -> None:
        bad = [
            {"priority": "URGENT"},
            {"priority": "high"},
            {"priority": None},
            {"priority": 1},
            {"due_date": "2026-02-30"},
            {"due_date": "2026-9-3"},
            {"due_date": "2026/09/03"},
            {"due_date": "2026-09-03T10:00:00"},
            {"due_date": "20260903"},
            {"due_date": 20260903},
            {"due_date": ""},
        ]
        for fields in bad:
            with self.subTest(fields=fields):
                status, _ = self.request("POST", "/api/tasks", {"title": "x", **fields})
                self.assertEqual(status, 422)
        self.assertEqual(self.request("GET", "/api/tasks")[1], [])

    # ---- 수정 (시나리오 10 · 11 · 12 · 13 · 14 · 15 · 16) ----

    def test_edit_priority_and_due_date(self) -> None:
        card = self.create(priority="LOW", due_date=day(1))
        status, body = self.patch(card["id"], priority="HIGH", due_date=day(9))
        self.assertEqual((status, body["priority"], body["due_date"]), (200, "HIGH", day(9)))
        self.assertEqual(self.get(card["id"]), body)

    def test_title_only_or_status_only_edit_keeps_priority_and_due_date(self) -> None:
        card = self.create(priority="HIGH", due_date=day(5))
        self.patch(card["id"], title="새 제목")
        after_title = self.get(card["id"])
        self.assertEqual((after_title["priority"], after_title["due_date"]), ("HIGH", day(5)))
        self.patch(card["id"], status="IN_PROGRESS")
        after_status = self.get(card["id"])
        self.assertEqual((after_status["priority"], after_status["due_date"]), ("HIGH", day(5)))
        self.assertEqual(after_status["status"], "IN_PROGRESS")

    def test_null_due_date_removes_it_and_omitting_keeps_it(self) -> None:
        card = self.create(due_date=day(5))
        self.assertEqual(self.patch(card["id"], description="d")[1]["due_date"], day(5))
        status, body = self.patch(card["id"], due_date=None)
        self.assertEqual((status, body["due_date"]), (200, None))
        self.assertIsNone(self.get(card["id"])["due_date"])

    def test_clearing_due_date_alone_is_a_valid_edit_even_when_already_empty(self) -> None:
        card = self.create()
        self.assertEqual(self.patch(card["id"], due_date=None)[0], 200)

    def test_edit_rejects_bad_priority_and_due_date_and_changes_nothing(self) -> None:
        card = self.create("원래", priority="HIGH", due_date=day(5))
        bad = [
            {"priority": None},
            {"priority": "URGENT"},
            {"priority": "low"},
            {"due_date": "2026-02-30"},
            {"due_date": "2026-9-3"},
            {"due_date": 5},
        ]
        for fields in bad:
            with self.subTest(fields=fields):
                # 같은 요청의 다른 값(제목)도 저장되지 않는다.
                status, _ = self.patch(card["id"], title="바뀌면 안 됨", **fields)
                self.assertEqual(status, 422)
        self.assertEqual(self.get(card["id"]), card)

    def test_priority_or_due_date_change_refreshes_updated_at(self) -> None:
        card = self.create(priority="LOW")
        conn = sqlite3.connect(self.db_file)
        conn.execute("UPDATE tasks SET updated_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (card["id"],))
        conn.commit()
        conn.close()
        self.patch(card["id"], priority="HIGH")
        self.assertNotEqual(self.get(card["id"])["updated_at"], "2000-01-01T00:00:00+00:00")

    # ---- 기한 초과 판정표 (R-010, IMPACT-ANALYSIS 2절) ----

    def test_overdue_table(self) -> None:
        cases = {-1: True, 0: False, 1: False, None: False}  # 미완료 카드
        for offset, expected in cases.items():
            for status in ("TODO", "IN_PROGRESS"):
                with self.subTest(offset=offset, status=status):
                    card = self.create(due_date=None if offset is None else day(offset))
                    self.patch(card["id"], status=status)
                    self.assertEqual(self.get(card["id"])["is_overdue"], expected)
        for offset in (-1, 0, 1, None):  # 완료 카드는 어느 경우에도 아니다
            with self.subTest(offset=offset, status="DONE"):
                card = self.create(due_date=None if offset is None else day(offset))
                self.patch(card["id"], status="DONE")
                self.assertFalse(self.get(card["id"])["is_overdue"])

    def test_overdue_comes_back_in_create_and_edit_responses_too(self) -> None:
        card = self.create(due_date=day(-2))
        self.assertTrue(card["is_overdue"])
        status, body = self.patch(card["id"], status="DONE")
        self.assertEqual((status, body["is_overdue"]), (200, False))

    def test_past_due_date_does_not_change_status(self) -> None:
        card = self.create(due_date=day(-10))
        self.assertEqual(self.get(card["id"])["status"], "TODO")

    # ---- 정렬 (R-011) ----

    def test_list_order(self) -> None:
        self.create("a 보통 마감없음")
        self.create("b 높음 마감없음", priority="HIGH")
        self.create("c 낮음 어제", priority="LOW", due_date=day(-1))
        self.create("d 높음 내일", priority="HIGH", due_date=day(1))
        self.create("e 보통 3일전", due_date=day(-3))
        self.create("f 높음 어제", priority="HIGH", due_date=day(-1))
        self.create("g 높음 내일 (d 와 같음)", priority="HIGH", due_date=day(1))
        self.create("h 높음 5일뒤", priority="HIGH", due_date=day(5))
        done = self.create("i 완료 높음 어제", priority="HIGH", due_date=day(-1))
        self.patch(done["id"], status="DONE")
        self.assertEqual(
            [t.split()[0] for t in self.titles()],
            # 기한 초과(우선순위 순) → 나머지 높음(가까운 마감일, 같으면 만든 순서, 마감일 없음은 뒤) → 보통
            ["f", "e", "c", "i", "d", "g", "h", "b", "a"],
        )

    def test_order_follows_status_and_priority_changes(self) -> None:
        a = self.create("a", priority="LOW", due_date=day(-1))
        b = self.create("b", priority="HIGH")
        self.assertEqual(self.titles(), ["a", "b"])  # 기한 초과가 가장 먼저
        self.patch(a["id"], status="DONE")
        self.assertEqual(self.titles(), ["b", "a"])
        self.patch(a["id"], status="TODO", priority="HIGH")
        self.assertEqual(self.titles(), ["a", "b"])
        self.assertEqual(self.get(b["id"])["priority"], "HIGH")

    def test_equal_cards_keep_creation_order(self) -> None:
        for name in ("x", "y", "z"):
            self.create(name, due_date=day(2))
        self.assertEqual(self.titles(), ["x", "y", "z"])

    def test_sorting_does_not_mix_other_users_cards(self) -> None:
        mine = self.create("mine", priority="LOW")
        self.register("bob12345", "password-1234")
        bob = self.create("bob-high", priority="HIGH", due_date=day(-1))
        self.assertEqual(self.titles(), ["bob-high"])
        self.assertEqual(self.patch(mine["id"], priority="HIGH")[0], 404)
        self.login(*DEFAULT_USER)
        self.assertEqual(self.titles(), ["mine"])
        self.assertEqual(self.patch(bob["id"], priority="LOW")[0], 404)

    def test_values_survive_server_restart(self) -> None:
        card = self.create(priority="HIGH", due_date=day(-1))
        self.restart_server()
        self.assertEqual(self.request("GET", "/api/tasks")[1], [card])


if __name__ == "__main__":
    unittest.main()
