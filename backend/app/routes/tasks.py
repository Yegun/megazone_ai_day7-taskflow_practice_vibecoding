import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..auth import current_user
from ..schemas import Task, TaskCreate, TaskUpdate, User

# 모든 Task 요청은 로그인이 필요하다(401). 남의 Task 는 없는 Task 와 같은 404 로 응답한다 (R-008).
router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(current_user)])

CurrentUser = Annotated[User, Depends(current_user)]


STORAGE_ERROR = HTTPException(status_code=500, detail="저장소 오류가 발생했습니다.")


@router.get("")
def list_tasks(user: CurrentUser) -> list[Task]:
    try:
        return db.list_tasks(user.id)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc


@router.patch("/{task_id}")
def update_task(task_id: int, data: TaskUpdate, user: CurrentUser) -> Task:
    try:
        task = db.update_task(user.id, task_id, data)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
    if task is None:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없습니다.")
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, user: CurrentUser) -> None:
    try:
        deleted = db.delete_task(user.id, task_id)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="카드를 찾을 수 없습니다.")


@router.post("", status_code=201)
def create_task(data: TaskCreate, user: CurrentUser) -> Task:
    try:
        return db.create_task(user.id, data)
    except sqlite3.Error as exc:
        raise STORAGE_ERROR from exc
