"""텔레그램 요약 발송.

- 환경변수 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 사용.
- 보고서 .md 에서 핵심만 추려 4096자 이내 요약본으로 전송, 전체는 레포 링크.
- 토큰 미설정 시 에러 없이 경고만 출력하고 통과(graceful).
- 사용: python send_telegram.py [reports/YYYY-MM-DD.md]
        python send_telegram.py --test
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    requests = None

KST = timezone(timedelta(hours=9))
TG_LIMIT = 4096
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _send(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(
        url,
        data={"chat_id": chat_id, "text": text[:TG_LIMIT], "disable_web_page_preview": True},
        timeout=20,
    )
    if r.status_code != 200:
        print(f"[error] 텔레그램 발송 실패 {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return False
    return True


def _summarize_md(md_path: str) -> str:
    """보고서에서 한눈에보기 + 뉴스 제목 + 링크를 추려 요약본 구성."""
    date = os.path.splitext(os.path.basename(md_path))[0]
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    overview, news_titles = [], []
    section = None
    for ln in lines:
        if ln.startswith("## "):
            section = ln
            continue
        if section and "한눈에 보기" in section and ln.strip() and not ln.startswith(("#", ">")):
            overview.append(ln.strip())
        elif section and "오늘의 뉴스" in section and ln.lstrip().startswith(tuple("123456789")):
            news_titles.append(ln.strip().lstrip("0123456789. ").replace("**", ""))

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    link = f"https://github.com/{repo}/blob/main/reports/{date}.md" if repo else f"reports/{date}.md"

    out = [f"📊 데일리 시장 보고서 — {date}", ""]
    if overview:
        out += [" ".join(overview), ""]
    if news_titles:
        out.append("📰 주요 뉴스")
        out += [f"• {t}" for t in news_titles[:7]]
        out.append("")
    out.append(f"전체 보고서: {link}")
    return "\n".join(out)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[warn] TELEGRAM_BOT_TOKEN/CHAT_ID 미설정 — 텔레그램 발송 생략(마크다운만 생성됨).")
        return 0
    if requests is None:
        print("[warn] requests 미설치 — 텔레그램 발송 생략.")
        return 0

    args = [a for a in sys.argv[1:]]
    if "--test" in args:
        ok = _send(token, chat_id, f"✅ 데일리 시장 보고서 테스트 — {datetime.now(KST):%Y-%m-%d %H:%M KST}")
        return 0 if ok else 1

    if args:
        md_path = args[0]
    else:
        date = datetime.now(KST).strftime("%Y-%m-%d")
        md_path = os.path.join(REPO_ROOT, "reports", f"{date}.md")

    if not os.path.exists(md_path):
        print(f"[error] 보고서 파일 없음: {md_path}", file=sys.stderr)
        return 1

    ok = _send(token, chat_id, _summarize_md(md_path))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
