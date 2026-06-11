# 데일리 시장 보고서 (Daily Market Report)

매일 오전 9시(KST)에 **실물 거래지표(금·은·원유·천연가스·곡물) + 증시 + 환율·금리 + 암호화폐**의
일/월/연 변동과 **주요 뉴스(연합뉴스·매일경제·인베스팅닷컴)**를 정리해
`reports/YYYY-MM-DD.md` 로 커밋하고 텔레그램으로 요약 발송한다.

> TMS 코어(코드 내비게이션)와 무관한 독립 모듈이다. TMS 코어의 "의존성 0" 정책은 그대로 유지된다.

## 구성

| 파일 | 역할 |
|---|---|
| `watchlist.py` | 지표 정의(티커·한글명·단위). **종목 추가/삭제는 여기서** |
| `fetch_market.py` | 시세 수집 + 일/월/연 변동 계산(거래일 보정) |
| `fetch_news.py` | 매체별 RSS 수집 + 키워드 필터 → 후보 리스트 |
| `build_report.py` | 시세+뉴스+해설 → `reports/YYYY-MM-DD.md` 생성 (오케스트레이터) |
| `send_telegram.py` | 보고서 요약을 텔레그램으로 발송 |
| `report_template.md` | 보고서 포맷 기준 |
| `TELEGRAM_SETUP.md` | 텔레그램 봇 연동 가이드 |
| `DAILY_REPORT_SOP.md` | (대안 A) Claude 예약 세션 작업 지침 |

## 실행 방식: GitHub Actions (기본)

`.github/workflows/daily-report.yml` 이 매일 `00:00 UTC`(=09:00 KST)에 실행한다.
러너는 인터넷이 열려 있어 별도 네트워크 정책 변경이 필요 없다.

흐름: 의존성 설치 → `build_report.py`(시세+뉴스+해설) → `reports/`를 `main`에 커밋 → `send_telegram.py`.

### 사전 준비 (저장소 Secrets)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — 텔레그램 발송용 (`TELEGRAM_SETUP.md` 참고)
- `ANTHROPIC_API_KEY` — (선택) 시장 해설·뉴스 선별을 Claude로 보강. 없으면 규칙 기반 폴백.

> cron 스케줄은 워크플로가 **기본 브랜치(main)** 에 있어야 동작한다. 본 기능 머지 후 활성화된다.

## 로컬 실행 / 검증
```bash
pip install -r market_report/requirements.txt

python market_report/fetch_market.py        # 지표 표 미리보기
python market_report/fetch_news.py           # 뉴스 후보 미리보기
python market_report/build_report.py         # reports/<오늘>.md 생성

export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
python market_report/send_telegram.py --test # 발송 테스트
```

## 변동 기준
- 일 = 직전 거래일 종가 대비
- 월 = 1개월 전 캘린더일 이전의 가장 가까운 거래일 종가 대비
- 연 = 1년 전 캘린더일 이전의 가장 가까운 거래일 종가 대비
- 주말·공휴일에도 보고하며, 데이터는 "마지막 거래일 종가" 기준(보고서에 기준일 명시).

## 안내
- 개별 지표/뉴스 수집 실패는 `N/A`/건너뜀으로 격리되어 전체는 계속 생성된다.
- 본 보고서는 자동 생성 정보이며 투자 권유가 아니다.
