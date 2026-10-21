# Bug.md

SCENARIO-REVIEW.md의 시나리오 예상결과와 실제 결과가 다르게 나온 경우(판정에서 '차이'로 저장된 항목)를 세분화 하여 저장. 

## 버그 1 

### 재현 순서
1. 카드 제목에 공백 만을 넣는다.
2. 등록 버튼을 누른다. 
3. 공백 제목을 가진 새로운 카드가 할 일열에 새로 나타난다. 

### 기대 결과
- 등록 버튼을 누르면, '제목을 입력해주세요' 라는 안내가 나온다.
- 새로운 카드 등록이 되지않는다.


### 실제 결과
- 등록 버튼을 누르면, 공백 제목을 가진 새로운 카드가 할 일 열에 새롭게 등록된다. 


### 증거

- 웹사이트 관리자 탭 내부 NETWORK Request와 Response 
- Netword: Patch /api/tasks/번호 요청시
Payload(Request): 
status
: 
"IN_PROGRESS"

Response
{
    "id": 16,
    "title": "안녕",
    "description": "",
    "status": "TODO",
    "created_at": "2026-10-21T06:28:21+00:00",
    "updated_at": "2026-10-21T06:29:23+00:00"
}








## 버그 2 

### 재현 순서 
1. 카드 상태를 '완료'로 바꾼다
2. F5로 새로고침한다

### 기대 결과
- 카드의 완료 열에 그대로 있음

### 실제 결과
- 카드 상태가 할 일로 원복된다. 

### 증거
- 캡처 : F5 전과 후

- 웹사이트 관리자 탭 내부 NETWORK Request와 Response 
- Netword: Patch /api/tasks/번호 요청시
- Request = {"status": "DONE"}
- Response = {"status": "TODO"}









