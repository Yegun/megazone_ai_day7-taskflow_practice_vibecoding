import sqlite3
import unittest

from tests.live_server import LiveServerTestCase

PW = "password-1234"


class AuthApiTest(LiveServerTestCase):
    auto_login = False

    def test_register_logs_in_and_me_returns_user_without_secrets(self) -> None:
        status, body = self.register("Alice01", PW)
        self.assertEqual(status, 201)
        self.assertEqual(body["username"], "alice01")  # 대소문자 구분 없이 소문자로 저장
        self.assertEqual(set(body), {"id", "username"})
        self.assertEqual(self.request("GET", "/api/auth/me"), (200, body))

    def test_session_cookie_attributes(self) -> None:
        self.register("alice01", PW)
        header = next(h for h in self.set_cookie_headers if h.startswith("session="))
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=lax", header)
        self.assertIn("Max-Age=1800", header)

    def test_me_without_login_is_401(self) -> None:
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)

    def test_logout_ends_session_and_same_cookie_no_longer_works(self) -> None:
        self.register("alice01", PW)
        old = self.cookie
        self.assertEqual(self.request("POST", "/api/auth/logout"), (204, None))
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)
        self.cookie = old  # 지워진 세션의 쿠키를 다시 써 본다
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)
        self.assertEqual(self.request("POST", "/api/auth/logout")[0], 401)

    def test_login_after_logout(self) -> None:
        self.register("alice01", PW)
        self.request("POST", "/api/auth/logout")
        status, body = self.login("ALICE01", PW)
        self.assertEqual((status, body["username"]), (200, "alice01"))
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 200)

    def test_wrong_password_and_unknown_user_get_identical_401(self) -> None:
        self.register("alice01", PW)
        self.request("POST", "/api/auth/logout")
        wrong = self.login("alice01", "wrong-password")
        unknown = self.login("nobody99", PW)
        self.assertEqual(wrong, unknown)
        self.assertEqual(wrong[0], 401)
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)

    def test_duplicate_username_is_409_case_insensitive(self) -> None:
        self.register("alice01", PW)
        self.request("POST", "/api/auth/logout")
        self.assertEqual(self.register("ALICE01", PW)[0], 409)

    def test_invalid_input_is_422_and_creates_nobody(self) -> None:
        for username, password in [("ab", PW), ("한글아이디", PW), ("has space", PW), ("a" * 21, PW), ("alice01", "short")]:
            with self.subTest(username=username, password=password):
                self.assertEqual(self.register(username, password)[0], 422)
        self.assertEqual(self.login("alice01", PW)[0], 401)

    def test_relogin_while_logged_in_replaces_session(self) -> None:
        self.register("alice01", PW)
        first = self.cookie
        self.assertEqual(self.login("alice01", PW)[0], 200)
        self.assertNotEqual(self.cookie, first)
        second = self.cookie
        self.cookie = first
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)
        self.cookie = second
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 200)

    def test_tampered_cookie_is_401(self) -> None:
        self.register("alice01", PW)
        token, _, sig = self.cookie.partition(".")
        self.cookie = f"{token}.{'0' * len(sig)}"
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)
        self.cookie = "garbage"
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)

    def test_expired_session_is_401(self) -> None:
        self.register("alice01", PW)
        conn = sqlite3.connect(self.db_file)
        conn.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
        conn.commit()
        conn.close()
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 401)

    def test_password_is_stored_only_as_argon2_hash_and_session_id_hashed(self) -> None:
        self.register("alice01", PW)
        conn = sqlite3.connect(self.db_file)
        (stored,) = conn.execute("SELECT password_hash FROM users WHERE username = 'alice01'").fetchone()
        (sid,) = conn.execute("SELECT id FROM sessions").fetchone()
        conn.close()
        self.assertTrue(stored.startswith("$argon2"))
        self.assertNotIn(PW, stored)
        self.assertNotIn(sid, self.cookie)  # 쿠키의 토큰 원문이 아니라 해시가 저장된다


class MigratedAccountTest(LiveServerTestCase):
    auto_login = False

    def test_migrated_account_cannot_log_in_before_someone_claims_it(self) -> None:
        self.assertEqual(self.login("migrated@test.com", PW)[0], 401)
        self.assertEqual(self.login("migrated@test.com", "")[0], 401)

    def test_first_register_claims_it_and_second_is_409(self) -> None:
        status, body = self.register("Migrated@Test.com", PW)
        self.assertEqual((status, body["username"]), (201, "migrated@test.com"))
        self.assertEqual(self.request("GET", "/api/auth/me")[0], 200)
        self.request("POST", "/api/auth/logout")
        self.assertEqual(self.register("migrated@test.com", "another-password")[0], 409)
        self.assertEqual(self.login("migrated@test.com", PW)[0], 200)

    def test_other_email_shaped_names_are_rejected(self) -> None:
        self.assertEqual(self.register("someone@test.com", PW)[0], 422)


if __name__ == "__main__":
    unittest.main()
