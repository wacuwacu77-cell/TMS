# 데일리 보고서 작업 지침 (대안 A — Claude 예약 세션용)

> 기본 실행 주체는 **GitHub Actions**(`.github/workflows/daily-report.yml`)다.
> 이 문서는 환경 네트워크를 개방하고 Claude Code 예약 세션으로 전환할 경우의 작업 순서다.

## 전제
- 예약 세션 환경의 네트워크 정책에 다음 도메인이 허용되어 있어야 한다:
  `query1.finance.yahoo.com`, `www.yna.co.kr`, `www.mk.co.kr`, `kr.investing.com`,
  `api.finance.naver.com`, `api.telegram.org`
- 환경변수: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (해설 보강 시 `ANTHROPIC_API_KEY` 불필요 — 세션 자체가 수행)

## 매일 작업 순서
1. `pip install -r market_report/requirements.txt`
2. `python market_report/fetch_market.py --json` 실행 → 시세 확보
3. `python market_report/fetch_news.py` 실행 → 뉴스 후보 확보(부족하면 WebSearch 보완)
4. 후보에서 시장영향도 순 **Top 5~7** 선별 + 한 줄 요약 작성
5. `report_template.md` 포맷으로 `reports/YYYY-MM-DD.md` 작성(수치 표 + 뉴스 + 시장 해설)
   - 직접 작성 대신 `python market_report/build_report.py` 를 써도 됨(이 경우 4~5 자동)
6. `git add reports/ && git commit && git push` (보고서는 `master` 의 `reports/` 에 누적)
7. `python market_report/send_telegram.py reports/YYYY-MM-DD.md` 로 요약 발송

## 주의
- 같은 날 재실행 시 보고서 파일은 덮어쓰고, 텔레그램 중복 발송에 유의한다.
- 수치는 직전 거래일 종가 기준이며 보고서에 데이터 기준일을 명시한다.
