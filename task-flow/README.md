# task-flow

카드형 Task 관리 웹 앱. 현재는 M0(프로젝트 기본 구조)만 있다.

## 실행
백엔드 (API, 포트 8000)
```
cd backend
uv run uvicorn app.main:app --reload
```
확인: http://localhost:8000/health → `{"status":"ok"}`

프런트엔드 (Node.js 20.19+ 또는 22.12+ 필요)
```
cd frontend
npm install
npm run dev
```
