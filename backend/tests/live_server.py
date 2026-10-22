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


def upgrade_db(db_file: str) -> None:
    """임시 DB 에 Alembic 마이그레이션을 끝까지 적용한다 (원본 DB 가 아니다)."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "TASKFLOW_DB": db_file},
        check=True,
        capture_output=True,
    )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LiveServerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_file = str(Path(self._tmp.name) / "live.db")
        self.port = _free_port()
        self.proc: subprocess.Popen[bytes] | None = None
        upgrade_db(self.db_file)
        self.start_server()
        self.addCleanup(self.stop_server)

    def start_server(self) -> None:
        env = {**os.environ, "TASKFLOW_DB": self.db_file}
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

    def request(self, method: str, path: str, body: object | None = None) -> tuple[int, object]:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as res:
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            raw = err.read()
            return err.code, json.loads(raw) if raw else None
