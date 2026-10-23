"""임시 DB 로 실제 uvicorn 서버를 띄워 HTTP 로 호출하는 테스트 도구 (httpx · pytest 없이 표준 라이브러리만 사용)."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def upgrade_db(db_file: str, target: str = "head") -> None:
    """임시 DB 에 Alembic 마이그레이션을 target 까지 적용한다 (원본 DB 가 아니다)."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=BACKEND_DIR,
        env={**os.environ, "TASKFLOW_DB": db_file},
        check=True,
        capture_output=True,
    )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


TEST_SECRET = "test-secret-not-for-real-use"
DEFAULT_USER = ("tester01", "password-1234")


class LiveServerTestCase(unittest.TestCase):
    # True 면 시작할 때 DEFAULT_USER 로 가입해 로그인한 상태로 둔다. 인증 자체를 시험하는 테스트는 False.
    auto_login = True

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_file = str(Path(self._tmp.name) / "live.db")
        self.port = _free_port()
        self.proc: subprocess.Popen[bytes] | None = None
        upgrade_db(self.db_file)
        self.cookie: str | None = None  # 지금 요청에 실어 보낼 session 쿠키 값
        self.set_cookie_headers: list[str] = []  # 마지막 응답의 Set-Cookie 원문
        self.start_server()
        self.addCleanup(self.stop_server)
        if self.auto_login:
            status, _ = self.register(*DEFAULT_USER)
            assert status == 201, status

    def start_server(self) -> None:
        env = {**os.environ, "TASKFLOW_DB": self.db_file, "SESSION_SECRET_KEY": TEST_SECRET}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(self.port)],
            cwd=BACKEND_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                self.request("GET", "/api/health")
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("서버가 시작되지 않았습니다.")

    def stop_server(self) -> None:
        if self.proc is not None:
            self.proc.terminate()
            self.proc.wait(timeout=10)
            self.proc = None

    def restart_server(self) -> None:
        self.stop_server()
        self.start_server()

    def register(self, username: str, password: str) -> tuple[int, object]:
        return self.request("POST", "/api/auth/register", {"username": username, "password": password})

    def login(self, username: str, password: str) -> tuple[int, object]:
        return self.request("POST", "/api/auth/login", {"username": username, "password": password})

    def _remember_cookie(self, headers: list[str]) -> None:
        self.set_cookie_headers = headers
        for header in headers:
            name_value, _, attrs = header.partition(";")
            name, _, value = name_value.partition("=")
            if name.strip() != "session":
                continue
            # 지우라는 응답(빈 값 또는 Max-Age=0)이면 쿠키를 버린다.
            self.cookie = None if not value.strip('"') or "Max-Age=0" in attrs else value

    def request(self, method: str, path: str, body: object | None = None) -> tuple[int, object]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if self.cookie is not None:
            headers["Cookie"] = f"session={self.cookie}"
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req) as res:
                self._remember_cookie(res.headers.get_all("Set-Cookie") or [])
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            self._remember_cookie(err.headers.get_all("Set-Cookie") or [])
            raw = err.read()
            return err.code, json.loads(raw) if raw else None
