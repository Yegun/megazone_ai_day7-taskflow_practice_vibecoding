import json
import os
from datetime import date

import anthropic
from pydantic import ValidationError

from .schemas import DivisionItem
from .suggest import _FENCE_RE, MAX_RETRIES, TIMEOUT_SECONDS, SuggestFailed, SuggestUnavailable

MODEL = "claude-haiku-5-5"
MAX_TOKENS = 1024  # 항목이 여러 개인 배열이라 제안(300)보다 넉넉히 둔다.

# 역할 지시문. 중괄호가 들어 있으므로 str.format 을 쓰지 않고 그대로 보낸다.
SYSTEM_PROMPT = """너는 할 일 관리 앱 Task Flow 의 작업 분해 도우미다.
사용자가 준 Task 의 제목(title)을 보고, 그 주제를 달성하기 위해 해야 할 일들을 실행 순서대로 나눈다.

[나누는 방법]
- 몇 개로 나눌지는 네가 판단한다. 정해진 개수는 없다.
- 작은 일이면 적게, 큰 일이면 많이 나눈다. 의미 없는 쪼개기와 억지로 개수 채우기는 하지 않는다.
- 이미 충분히 작은 일이면 항목 1개만 반환한다.
- 각 항목은 혼자서 바로 실행하고 끝낼 수 있는 구체적인 행동이어야 한다.
- 원래 Task 자체를 그대로 항목으로 반복하지 않는다.
- title 은 원래 Task 의 제목과 같은 언어로, 짧은 동사형 문장으로 쓴다.

[필드 규칙]
- title: 문자열. 하위 할 일의 제목.
- priority: "LOW", "NORMAL", "HIGH" 중 하나. 이 세 값 외에는 절대 쓰지 않는다.
  근거가 없으면 "NORMAL" 을 쓴다.
- due_date: "YYYY-MM-DD" 형식 문자열 또는 null.
  - 오늘 날짜(today)를 기준으로 "내일", "모레", "이번 주", "다음 주", "월말" 같은 표현을 계산한다.
  - "이번 주"는 오늘이 속한 주의 일요일, "다음 주"는 그 다음 주의 일요일로 계산한다.
  - 제목이나 설명에 마감 근거가 없으면 null 로 둔다. 날짜를 지어내지 않는다.
  - today 보다 이전 날짜는 쓰지 않는다.
  - 전체 마감이 있으면 하위 할 일은 실행 순서에 맞춰 그 마감 이전으로 분배한다.

[출력 형식]
- 객체 {"title": ..., "priority": ..., "due_date": ...} 여러 개를 담은 JSON 배열 하나만 출력한다.
- 배열 앞뒤에 설명, 인사, 머리말, 맺음말을 붙이지 않는다.
- ```json 같은 코드 블록 표시(백틱)를 절대 쓰지 않는다. 첫 글자는 [ 이고 마지막 글자는 ] 이다.
- 모든 키와 문자열은 큰따옴표를 쓰고, 마지막 항목 뒤에 쉼표를 남기지 않는다.
- 나눌 수 없을 만큼 정보가 없으면 빈 배열 [] 을 출력한다.

[예시]
입력: title=다음 주 금요일 발표 준비 / today=2026-10-28
출력:
[{"title":"발표 핵심 메시지 정리","priority":"HIGH","due_date":"2026-11-02"},{"title":"슬라이드 초안 작성","priority":"HIGH","due_date":"2026-11-04"},{"title":"발표 리허설","priority":"NORMAL","due_date":"2026-11-05"}]"""

USER_TEMPLATE = """title: {title}
today: {today}"""


def build_user_message(title: str, today: date) -> str:
    # 제목의 줄바꿈으로 today 줄을 꾸며 넣지 못하게 한 줄로 만든다.
    one_line = " ".join(title.split())
    return USER_TEMPLATE.replace("{today}", today.isoformat()).replace("{title}", one_line)


def parse_division(text: str) -> list[DivisionItem]:
    """모델 답을 읽어 검수한다. 앞뒤 ``` 표시가 있으면 안쪽만 쓴다. 허용 밖이면 SuggestFailed."""
    fenced = _FENCE_RE.match(text)
    body = fenced.group(1) if fenced else text.strip()
    try:
        data = json.loads(body)
        if not isinstance(data, list):
            raise ValueError("JSON 배열이 아닙니다.")
        return [DivisionItem.model_validate(item) for item in data]
    except (ValueError, ValidationError) as exc:  # json.JSONDecodeError 도 ValueError
        raise SuggestFailed from exc


def divide(title: str) -> list[DivisionItem]:
    """Haiku 5.5 에 할 일 나누기를 요청한다. DB 는 건드리지 않는다. 키는 ANTHROPIC_API_KEY 환경변수에서만 읽는다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise SuggestUnavailable

    client = anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=MAX_RETRIES)
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "disabled"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(title, date.today())}],
        )
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
        raise SuggestUnavailable from exc
    except anthropic.RateLimitError as exc:
        raise SuggestUnavailable from exc
    except anthropic.APIConnectionError as exc:  # 시간 초과 포함
        raise SuggestUnavailable from exc
    except anthropic.APIStatusError as exc:
        # 5xx · 529(과부하)는 바쁨, 그 밖의 4xx 는 제안 실패.
        raise (SuggestUnavailable if exc.status_code >= 500 else SuggestFailed) from exc

    if message.stop_reason == "max_tokens":
        raise SuggestFailed
    text = "".join(block.text for block in message.content if block.type == "text")
    return parse_division(text)
