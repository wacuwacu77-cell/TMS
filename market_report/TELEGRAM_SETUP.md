# 텔레그램 연동 가이드

보고서 요약을 텔레그램으로 받기 위한 1회 설정. (봇은 이미 보유 중이라는 가정)

## 1. 봇 토큰 확인
1. 텔레그램에서 [@BotFather](https://t.me/BotFather) 열기
2. `/mybots` → 사용할 봇 선택 → **API Token** 확인
   - 새로 만들려면 `/newbot` 후 안내에 따라 생성
3. 토큰 형식 예: `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 2. chat_id 확인
1. 내가 만든 봇과의 대화창을 열고 아무 메시지나 1개 전송(예: `hi`)
2. 브라우저에서 아래 주소 접속(`<TOKEN>` 교체):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. 응답 JSON 의 `result[].message.chat.id` 값이 chat_id
   - 개인 채팅이면 양수, 그룹이면 보통 음수(`-100...`)

## 3. 자격증명 등록 (GitHub Actions 사용 시)
저장소 → **Settings → Secrets and variables → Actions → New repository secret**:

| 이름 | 값 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | 1번에서 확인한 토큰 |
| `TELEGRAM_CHAT_ID` | 2번에서 확인한 chat_id |
| `ANTHROPIC_API_KEY` | (선택) 시장 해설·뉴스 선별을 Claude로 보강할 때 |

> 시크릿은 로그에 노출되지 않으며, `send_telegram.py` 도 토큰을 출력하지 않는다.

## 4. 발송 테스트
로컬에서(환경변수 설정 후):
```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
python market_report/send_telegram.py --test
```
폰으로 "✅ 데일리 시장 보고서 테스트" 메시지가 오면 성공.

## 참고
- 토큰/chat_id 미설정 시에도 마크다운 보고서는 정상 생성된다(텔레그램만 생략).
- 전체 보고서 링크는 비공개 저장소 블롭 주소라 권한이 있는 본인만 열람 가능하다.
