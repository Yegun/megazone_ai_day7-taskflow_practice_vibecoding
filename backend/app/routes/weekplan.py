import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from .. import db, suggest, weekplan
from ..auth import current_user
from ..schemas import User, WeekPlan

# 로그인한 사람의 DONE 아닌 할 일로 일주일 계획을 돌려주기만 한다. 저장하지 않으며 DB 를 바꾸지 않는다 (401).
router = APIRouter(prefix="/tasks", tags=["weekplan"], dependencies=[Depends(current_user)])

CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/weekplan")
def plan_week(user: CurrentUser) -> WeekPlan:
    try:
        tasks = db.list_tasks(user.id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="저장소 오류가 발생했습니다.") from exc
    try:
        return weekplan.plan(tasks)
    except suggest.SuggestUnavailable as exc:
        raise HTTPException(status_code=503, detail="AI 기능이 꺼져 있거나 지금은 사용할 수 없습니다.") from exc
    except suggest.SuggestFailed as exc:
        raise HTTPException(status_code=502, detail="제안에 실패했습니다.") from exc
