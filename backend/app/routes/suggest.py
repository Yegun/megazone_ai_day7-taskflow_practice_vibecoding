from fastapi import APIRouter, Depends, HTTPException

from .. import suggest
from ..auth import current_user
from ..schemas import Suggestion, SuggestRequest

# 제안만 돌려준다. 저장하지 않으며 DB 를 바꾸지 않는다. 로그인이 필요하다(401).
router = APIRouter(prefix="/tasks", tags=["suggest"], dependencies=[Depends(current_user)])


@router.post("/suggest")
def suggest_task(data: SuggestRequest) -> Suggestion:
    try:
        return suggest.suggest(data.title, data.description)
    except suggest.SuggestUnavailable as exc:
        raise HTTPException(status_code=503, detail="AI 기능이 꺼져 있거나 지금은 사용할 수 없습니다.") from exc
    except suggest.SuggestFailed as exc:
        raise HTTPException(status_code=502, detail="제안에 실패했습니다.") from exc
