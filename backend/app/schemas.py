import re
from enum import StrEnum

from pydantic import BaseModel, field_validator, model_validator


class Status(StrEnum):
    """허용 상태 세 값의 유일한 정의 (D-005). 저장소 CHECK 제약도 이 값을 쓴다."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


def _strip_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise ValueError("제목은 비워 둘 수 없습니다.")
    return title


class TaskCreate(BaseModel):
    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        return _strip_title(value)


class TaskUpdate(BaseModel):
    """보낸 값만 바꾼다. 보내지 않은 값은 그대로 둔다. 설명은 ""를 보내 비운다."""

    title: str | None = None
    description: str | None = None
    status: Status | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _strip_title(value)

    @model_validator(mode="after")
    def at_least_one_value(self) -> "TaskUpdate":
        sent = {k: getattr(self, k) for k in self.model_fields_set}
        if not sent or any(v is None for v in sent.values()):
            raise ValueError("title, description, status 중 바꿀 값을 null 없이 하나 이상 보내야 합니다.")
        return self


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    created_at: str
    updated_at: str


MIGRATED_USERNAME = "migrated@test.com"
_USERNAME_RE = re.compile(r"^[a-z0-9]{4,20}$")


class Credentials(BaseModel):
    """가입 · 로그인 요청. 아이디는 영문 · 숫자 4~20자이고 대소문자를 구분하지 않는다(소문자로 저장).
    이전용 계정 migrated@test.com 만 예외로 받는다 (D-016)."""

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_rule(cls, value: str) -> str:
        name = value.strip().lower()
        if name != MIGRATED_USERNAME and not _USERNAME_RE.fullmatch(name):
            raise ValueError("아이디는 영문 · 숫자 4~20자로 입력해야 합니다.")
        return name

    @field_validator("password")
    @classmethod
    def password_rule(cls, value: str) -> str:
        if not 8 <= len(value) <= 128:
            raise ValueError("비밀번호는 8~128자로 입력해야 합니다.")
        return value


class Login(BaseModel):
    """로그인 요청. 형식 오류와 불일치를 구분하지 않도록 규칙 검사 없이 받는다."""

    username: str
    password: str

    @field_validator("username")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.strip().lower()


class User(BaseModel):
    id: int
    username: str
