import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, Response

from . import db
from .schemas import User

COOKIE_NAME = "session"
SESSION_TTL = timedelta(minutes=30)  # D-017. 서버 세션 만료와 쿠키 Max-Age 를 같게 둔다. 연장하지 않는다.

NOT_LOGGED_IN = "로그인이 필요합니다."

_hasher = PasswordHasher()
# 없는 아이디로 로그인해도 해시 검증 시간이 비슷하도록 쓰는 더미 해시.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def load_env_file() -> None:
    """backend/.env 의 값을 환경변수에 채운다(이미 있는 값은 덮지 않는다). 값은 Git 에 없다."""
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def secret_key() -> bytes:
    key = os.environ.get("SESSION_SECRET_KEY", "")
    if not key:
        raise RuntimeError("SESSION_SECRET_KEY 가 비어 있습니다. backend/.env 에 값을 채우세요.")
    return key.encode()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """password_hash 가 없는 계정(비밀번호 전의 이전용 계정)이나 없는 아이디도 같은 시간을 들여 False."""
    try:
        if password_hash is None:
            _hasher.verify(_DUMMY_HASH, password)
            return False
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _session_id(token: str) -> str:
    """DB 에는 토큰 원문이 아니라 SHA-256 값을 둔다."""
    return hashlib.sha256(token.encode()).hexdigest()


def _sign(token: str) -> str:
    return hmac.new(secret_key(), token.encode(), hashlib.sha256).hexdigest()


def _token_from_cookie(value: str | None) -> str | None:
    if not value or "." not in value:
        return None
    token, _, signature = value.partition(".")
    return token if hmac.compare_digest(signature, _sign(token)) else None


def start_session(response: Response, user: User) -> None:
    """세션을 만들고 HttpOnly 쿠키로 싣는다. 만료된 세션도 이때 청소한다."""
    now = datetime.now(UTC)
    db.delete_expired_sessions(now.isoformat(timespec="seconds"))
    token = secrets.token_urlsafe(32)
    expires_at = (now + SESSION_TTL).isoformat(timespec="seconds")
    db.create_session(_session_id(token), user.id, expires_at)
    response.set_cookie(
        COOKIE_NAME,
        f"{token}.{_sign(token)}",
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        path="/",
    )


def drop_session(request: Request) -> None:
    """요청에 실린 세션을 서버에서 없앤다 (쿠키는 건드리지 않는다)."""
    token = _token_from_cookie(request.cookies.get(COOKIE_NAME))
    if token is not None:
        db.delete_session(_session_id(token))


def end_session(request: Request, response: Response) -> None:
    drop_session(request)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


def current_user(request: Request) -> User:
    """로그인한 사용자. 쿠키가 없거나 서명이 틀리거나 세션이 없거나 만료되면 401."""
    token = _token_from_cookie(request.cookies.get(COOKIE_NAME))
    user = None if token is None else db.get_session_user(_session_id(token), _now())
    if user is None:
        raise HTTPException(status_code=401, detail=NOT_LOGGED_IN)
    return user
