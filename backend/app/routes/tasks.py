import sqlite3

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import Task, TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _storage_error(exc: sqlite3.Error) -> HTTPException:
    return HTTPException(status_code=500, detail="저장소 오류가 발생했습니다.")


@router.get("")
def list_tasks() -> list[Task]:
    try:
        return db.list_tasks()
    except sqlite3.Error as exc:
        raise _storage_error(exc) from exc


@router.post("", status_code=201)
def create_task(data: TaskCreate) -> Task:
    try:
        return db.create_task(data)
    except sqlite3.Error as exc:
        raise _storage_error(exc) from exc
