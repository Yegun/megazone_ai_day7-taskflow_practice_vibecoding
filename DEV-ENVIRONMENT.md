# DEV-ENVIRONMENT

개발 컴퓨터의 환경 기록. 확인한 날짜: 2026-10-19.
아래 버전은 각 도구의 `--version` 출력을 그대로 옮긴 것이다.

## 운영체제 · 셸
- 운영체제: Microsoft Windows 11 Pro 10.0.22631
- 셸: PowerShell 7.6.7 (Git Bash 도 사용 가능)

## 도구별 버전

| 도구 | 명령 | 결과 (그대로) |
|---|---|---|
| git | `git --version` | `git version 2.56.0.windows.2` |
| node | `node --version` | 실행 안 됨. `'node' 용어는 cmdlet, 함수, 스크립트 파일 또는 실행 프로그램의 이름으로 인식되지 않습니다.` |
| npm | `npm --version` | 실행 안 됨. `'npm' 용어는 cmdlet, 함수, 스크립트 파일 또는 실행 프로그램의 이름으로 인식되지 않습니다.` |
| uv | `uv --version` | `uv 0.13.1 (62faed335 2026-10-13 x86_64-pc-windows-msvc)` |
| python | `python --version` | `Python` (종료 코드 9009. 버전이 나오지 않는다) |

## 참고
- `python` 은 Microsoft Store 연결용 빈 실행 파일(`C:\Users\EZ\AppData\Local\Microsoft\WindowsApps\python.exe`)로 연결되어 있고 실제 Python 이 아니다.
- 실제 Python 은 uv 가 관리하는 것이다: `uv run --no-project python --version` 결과 `Python 3.12.15`. `C:\Users\EZ\.local\bin\python3.12.exe --version` 결과도 `Python 3.12.15`.
- node 와 npm 은 설치되어 있지 않다. React · Vite 화면을 만들려면 Node.js 가 필요하다. Vite 공식 문서는 20.19 이상 또는 22.12 이상을 요구한다.

## 새로 설치한 것
없음. 이 기록을 만들면서 아무것도 설치하지 않았다.
