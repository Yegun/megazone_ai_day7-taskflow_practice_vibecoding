import sqlite3

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import Task, TaskCreate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


STORAGE_ERROR = HTTPException(status_code=500, detail="저장소 오류가 발생했습니다.")


@router.get("")
def list_tasks() -> list[Task]:
    try:
        return db.list_tasks()
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc


@router.patch("/{task_id}")
def update_task(task_id: int, data: TaskUpdate) -> Task:
    try:
        task = db.update_task(task_id, data)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
    if task is None:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없습니다.")
    return task


@router.post("", status_code=201)
def create_task(data: TaskCreate) -> Task:
    try:
        return db.create_task(data)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
