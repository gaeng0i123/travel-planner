# Claude Code 행동 지침 — Travel Planner

## 여행 대화 세션 시작 시

사용자가 여행 관련 이야기(개발 외 여행 고민·일정·선택지 등)를 꺼낼 때:

1. `python3 scripts/read_thinklog.py` 를 실행해 구글독스 thinklog 최신 내용을 읽는다.
2. 그 내용을 바탕으로 사전지식을 갖추고 대화한다.
3. 대화하면서 중요한 내용(결정사항, 고민, 아이디어)을 `worklog.md`에 계속 기록한다.

## "정리해줘" 받았을 때

1. 이번 세션에서 나온 핵심 내용을 요약한다.
2. `worklog.md`에 최종 정리 내용을 기록한다.
3. `python3 scripts/update_thinklog.py` 를 실행해 구글독스 하단에 날짜별 이력으로 추가한다.

## worklog.md 작성 규칙

- 세션마다 `## YYYY-MM-DD` 헤더로 구분
- 소제목: `### 주제`, 내용은 불릿 리스트
- 기존 내용은 절대 삭제하지 않고 아래에 추가만 한다
