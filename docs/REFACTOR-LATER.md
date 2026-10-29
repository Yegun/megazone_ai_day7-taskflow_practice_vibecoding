# REFACTOR-LATER

PR #31(AI로 할 일 만들기) 리뷰에서 나온 항목 중 지금 고치지 않고 미룬 것.
기준 diff: `main` ↔ `feature/task-specification`. 중요한 순서.

| # | 관점 | 파일 · 줄 | 무엇이 | 왜 | 제안 | 시점 |
|---|---|---|---|---|---|---|
| 1 | 중복 | `backend/app/division.py` 15, 78-106 | `suggest.py` 의 비공개 `_FENCE_RE` 를 import 해서 쓴다. `divide()` 의 키 읽기 · 클라이언트 생성 · 예외를 503/502 로 나누는 부분이 `suggest.suggest()` 와 거의 같고, `DivisionItem` 도 `Suggestion` 과 같은 검증을 되풀이한다. | 세 번째 AI 기능이 또 복사하면 세 군데가 된다. 429 처리나 타임아웃을 한쪽만 고치면 서로 어긋난다. | 공통 모듈(`ai_client.py` 등)로 "호출 → 예외 분류 → 코드블록 제거" 를 뽑는다. | 세 번째 AI 기능을 만들기 전 |
| 2 | 이름 | `backend/app/division.py` 15, 75, 104 · `backend/app/routes/division.py` 147-149 · `frontend/src/components/DivisionParts.tsx` | 나누기가 실패해도 `SuggestFailed` / `SuggestUnavailable` 이 나가고 응답 문구도 "제안에 실패했습니다." 이다. 버튼은 `suggest-button` 클래스를 그대로 쓴다. | 로그나 오류만 보고는 AI 제안 실패인지 나누기 실패인지 구분되지 않는다. 502 에 4xx 와 파싱 실패가 섞여 원인도 알 수 없다. | `AiUnavailable` / `AiFailed` 처럼 중립적인 이름으로 바꾸거나, 문구와 로그에 "나누기" 를 넣는다. 4xx 와 파싱 실패는 로그로 구분한다. | #1 중복 정리와 함께 |
| 3 | 빠진 검사 | `frontend/src/components/TaskBoard.tsx` `handleCreateMany` · `frontend/src/components/TaskForm.tsx` `handleRegisterAll` | 한 건씩 순서대로 등록하다 실패하면 실패한 항목부터 전부 미리 보기에 되돌린다. 막는 장치는 `registeringAll` 상태 하나뿐이고 ref 잠금은 없다. | 타임아웃처럼 서버에는 저장됐는데 응답만 못 받은 경우 [모두 등록] 을 다시 누르면 같은 할 일이 두 번 생긴다. 로그아웃(401) 중간에도 같은 상태가 된다. | 실패한 항목은 "성공 여부 불확실" 로 안내한다. 재시도 전에 목록을 새로 불러오거나 `useRef` 잠금으로 이중 호출을 막는다. | 위험은 낮음. 여유가 있을 때 |

## 같이 미룬 것

- 호출 횟수 제한(사용자별 간격 · 횟수), 응답 항목 수 상한은 이번에 넣지 않았다. 제목 길이 상한(200자)만 먼저 넣었다.
