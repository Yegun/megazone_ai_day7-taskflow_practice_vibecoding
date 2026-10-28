import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, field_validator, model_validator


class Status(StrEnum):
    """허용 상태 세 값의 유일한 정의 (D-005). 저장소 CHECK 제약도 이 값을 쓴다."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class Priority(StrEnum):
    """허용 우선순위 세 값의 유일한 정의 (R-009). 저장소 CHECK 제약도 이 값을 쓴다."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


def _strip_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise ValueError("제목은 비워 둘 수 없습니다.")
    return title


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _strict_date(value: object) -> object:
    """마감일은 YYYY-MM-DD 문자열만 받는다 (R-007). 없는 날짜(2026-02-30)는 이어지는 date 검증이 거절한다."""
    if value is not None and not (isinstance(value, str) and _DATE_RE.fullmatch(value)):
        raise ValueError("마감일은 YYYY-MM-DD 형식이어야 합니다.")
    return value


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: Priority = Priority.NORMAL  # null 은 거절한다. 우선순위는 비울 수 없다 (R-009).
    due_date: date | None = None

    @field_validator("due_date", mode="before")
    @classmethod
    def due_date_format(cls, value: object) -> object:
        return _strict_date(value)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        return _strip_title(value)


class TaskUpdate(BaseModel):
    """보낸 값만 바꾼다. 보내지 않은 값은 그대로 둔다. 설명은 ""를 보내 비운다."""

    title: str | None = None
    description: str | None = None
    status: Status | None = None
    priority: Priority | None = None  # 생략하면 유지. null 은 거절한다.
    due_date: date | None = None  # 생략하면 유지. null 이면 마감일을 없앤다.

    @field_validator("due_date", mode="before")
    @classmethod
    def due_date_format(cls, value: object) -> object:
        return _strict_date(value)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _strip_title(value)

    @model_validator(mode="after")
    def at_least_one_value(self) -> "TaskUpdate":
        sent = {k: getattr(self, k) for k in self.model_fields_set}
        if not sent or any(v is None for k, v in sent.items() if k != "due_date"):
            raise ValueError(
                "title, description, status, priority, due_date 중 바꿀 값을 하나 이상 보내야 합니다. due_date 외에는 null 을 보낼 수 없습니다."
            )
        return self


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    due_date: str | None  # YYYY-MM-DD. 없으면 null
    is_overdue: bool  # 마감일이 오늘보다 이전이고 완료가 아니면 true. 저장하지 않고 목록을 줄 때 계산한다 (R-010).
    created_at: str
    updated_at: str


class SuggestRequest(BaseModel):
    """AI 제안 요청. 저장하지 않는다."""

    title: str
    description: str = ""

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        return _strip_title(value)


class Suggestion(BaseModel):
    """AI 제안 결과. 모델 답을 검수하는 데도 쓴다: 허용 밖의 값이면 ValidationError."""

    priority: Priority
    due_date: str | None  # YYYY-MM-DD 이고 실제로 있는 날짜. 없으면 null
    reason: str

    @field_validator("due_date", mode="before")
    @classmethod
    def due_date_format(cls, value: object) -> object:
        _strict_date(value)
        if value is not None:
            date.fromisoformat(value)  # 없는 날짜(2026-02-30)는 ValueError
        return value


MIGRATED_USERNAME ="migrated@test.com"
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
