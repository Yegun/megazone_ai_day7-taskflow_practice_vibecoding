import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import auth, db
from ..schemas import MIGRATED_USERNAME, Credentials, Login, User

router = APIRouter(prefix="/auth", tags=["auth"])

STORAGE_ERROR = HTTPException(status_code=500, detail="저장소 오류가 발생했습니다.")
LOGIN_FAILED = HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
USERNAME_TAKEN = HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")


@router.post("/register", status_code=201)
def register(data: Credentials, request: Request, response: Response) -> User:
    password_hash = auth.hash_password(data.password)
    try:
        user = None
        if data.username == MIGRATED_USERNAME:
            # 비밀번호 전의 이전용 계정이면 이 사람이 계정과 기존 Task 를 받는다 (D-016).
            user = db.claim_migrated_user(password_hash)
        else:
            user = db.create_user(data.username, password_hash)
        if user is None:
            raise USERNAME_TAKEN
        auth.drop_session(request)  # 이미 로그인한 상태면 이전 세션을 버린다.
        auth.start_session(response, user)
    except sqlite3.IntegrityError as exc:
        raise USERNAME_TAKEN from exc
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
    return user


@router.post("/login")
def login(data: Login, request: Request, response: Response) -> User:
    try:
        row = db.get_user_by_username(data.username)
        ok = auth.verify_password(data.password, None if row is None else row["password_hash"])
        if row is None or not ok:
            raise LOGIN_FAILED
        auth.drop_session(request)  # 이미 로그인한 상태면 새 세션으로 교체한다.
        user = User(id=row["id"], username=row["username"])
        auth.start_session(response, user)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, _: Annotated[User, Depends(auth.current_user)]) -> None:
    try:
        auth.end_session(request, response)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc


@router.get("/me")
def me(user: Annotated[User, Depends(auth.current_user)]) -> User:
    return user
