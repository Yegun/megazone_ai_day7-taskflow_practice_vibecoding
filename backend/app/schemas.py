from enum import StrEnum

from pydantic import BaseModel, field_validator


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


class Task(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    created_at: str
    updated_at: str
