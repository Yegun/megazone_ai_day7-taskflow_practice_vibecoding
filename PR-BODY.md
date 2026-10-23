## 개요
- 사용자별 Task 분리, Close #19

## 변경 내용
- 기능 추가
    - 가입
    - 로그인
    - 로그아웃

- 데이터 변경
    - owner_id 열 추가
    - 기존 데이터 이전

- API 변경
    - 현재 사용자 API
    - 모든 Task API에 로그인 요구

## 확인한것 - 데이터
- Migration 전 
    - 전체 Task 수 : 2개

    - 상태별 수
        - TODO : 0
        - DONE : 1
        - IN_PROGRESS : 1

    - 주인 없는 Task 수: 2

- Migration 후
    - 전체 Task 수 : 2

    - 상태 별 수
        - TODO : 0
        - DONE : 1
        - IN_PROGRESS : 1
    
    - 주인 없는 Task 수 : 0 (모두 이전용 계정의 id를 부여받음)
    
    - 표본 Task 
        - 제목 유지
        - 설명 유지
        - 상태 유지

- 결과 : 성공적 데이터 이전

## 확인한 것 - 분리, 회귀
- A가 B의 Task 수정 (제목)
    - 404 (Task 없음)

- 로그아웃 후, Task 접근
    - 401 (인증 실패)

- 로그인 시나리오(생성, 상태 변겨으 삭제) ==> **통과** 
