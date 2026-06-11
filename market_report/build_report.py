"""시세 + 뉴스 + 해설을 합쳐 reports/YYYY-MM-DD.md 생성.

- 뉴스 선별/요약 및 시장 해설은 ANTHROPIC_API_KEY 가 있으면 Claude API로,
  없으면 규칙 기반(키워드 랭킹·템플릿)으로 자동 폴백한다.
- 멱등성: 같은 날 다시 실행하면 파일을 새로 덮어쓴다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetch_market  # noqa: E402
import fetch_news  # noqa: E402

KST = timezone(timedelta(hours=9))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


# ---------------------------------------------------------------- 요약/해설
def _top_movers(market: dict, n: int = 5):
    rows = [r for rows in market["categories"].values() for r in rows if r.get("day") is not None]
    rows.sort(key=lambda r: abs(r["day"]), reverse=True)
    return rows[:n]


def _rule_based(market: dict, news: list) -> dict:
    movers = _top_movers(market, 5)
    if movers:
        parts = [f"{m['name']} {m['day']:+.2f}%" for m in movers]
        overview = "전일 대비 변동이 큰 지표: " + ", ".join(parts) + "."
        ups = [m for m in movers if m["day"] > 0]
        downs = [m for m in movers if m["day"] < 0]
        commentary = (
            (f"상승: {', '.join(m['name'] for m in ups)}. " if ups else "")
            + (f"하락: {', '.join(m['name'] for m in downs)}. " if downs else "")
            + "수치는 직전 거래일 종가 기준이며, 자세한 등락은 위 표를 참고하십시오."
        )
    else:
        overview = "이용 가능한 시세 데이터가 없습니다."
        commentary = "데이터 수집에 실패했습니다. 소스 상태를 확인하십시오."

    selected = [
        {"title": c["title"], "summary": c["title"], "source": c["source"], "link": c["link"]}
        for c in news[:7]
    ]
    return {"overview": overview, "commentary": commentary, "news": selected}


def _claude_summary(market: dict, news: list, api_key: str) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    movers = _top_movers(market, 8)
    movers_txt = "\n".join(
        f"- {m['name']}: 일 {m['day']:+.2f}%, 월 "
        f"{('%+.2f%%' % m['month']) if m['month'] is not None else 'N/A'}, 연 "
        f"{('%+.2f%%' % m['year']) if m['year'] is not None else 'N/A'}"
        for m in movers
    )
    news_txt = "\n".join(f"[{i}] ({c['source']}) {c['title']}" for i, c in enumerate(news))

    prompt = (
        "다음은 오늘 아침 한국 시장 보고서용 데이터입니다.\n\n"
        f"## 주요 등락 지표\n{movers_txt}\n\n"
        f"## 뉴스 후보(번호)\n{news_txt}\n\n"
        "아래 JSON 형식으로만 답하세요(설명 금지):\n"
        "{\n"
        '  "overview": "오늘 시장 분위기 핵심 요약 3~5문장(사실 기반, 과도한 단정 금지)",\n'
        '  "commentary": "수치와 뉴스를 연결한 시장 해설 4~6문장",\n'
        '  "news_indices": [위 후보 중 시장영향도 높은 5~7개 번호],\n'
        '  "news_summaries": {"번호": "해당 기사 한 줄 요약", ...}\n'
        "}\n"
    )

    resp = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    parsed = json.loads(text[text.find("{"): text.rfind("}") + 1])

    selected = []
    summaries = {str(k): v for k, v in parsed.get("news_summaries", {}).items()}
    for idx in parsed.get("news_indices", [])[:7]:
        try:
            c = news[int(idx)]
        except (ValueError, IndexError):
            continue
        selected.append(
            {
                "title": c["title"],
                "summary": summaries.get(str(idx), c["title"]),
                "source": c["source"],
                "link": c["link"],
            }
        )
    if not selected:
        selected = _rule_based(market, news)["news"]

    return {
        "overview": parsed.get("overview", ""),
        "commentary": parsed.get("commentary", ""),
        "news": selected,
    }


def summarize(market: dict, news: list) -> dict:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            return _claude_summary(market, news, key)
        except Exception as exc:
            print(f"[warn] Claude 요약 실패 → 규칙 기반 폴백: {exc}", file=sys.stderr)
    return _rule_based(market, news)


# ---------------------------------------------------------------- 렌더링
def render(market: dict, summary: dict, now: datetime, movers: dict | None = None) -> str:
    # 데이터 기준일(가장 흔한 as_of)
    as_ofs = [r["as_of"] for rows in market["categories"].values() for r in rows if r.get("as_of")]
    data_date = max(as_ofs) if as_ofs else "N/A"

    lines = [
        f"# 📊 데일리 시장 보고서 — {now.strftime('%Y-%m-%d (%a)')}",
        "",
        f"- 보고 생성: {market['generated_at']}",
        f"- 데이터 기준일: **{data_date}** (직전 거래일 종가 기준 · 주말/휴장 시 마지막 거래일)",
        "",
        "## 📌 한눈에 보기",
        "",
        summary["overview"] or "_요약 없음_",
        "",
        "## 💹 지표 대시보드",
        "",
        "> 변동: 일=전일 종가 / 월=1개월 전 / 연=1년 전 대비",
        "",
        fetch_market.to_markdown(market),
    ]
    if movers:
        mv_md = _render_movers(movers)
        if mv_md:
            lines.append(mv_md)
    lines += [
        "## 📰 오늘의 뉴스",
        "",
    ]
    if summary["news"]:
        for i, n in enumerate(summary["news"], 1):
            lines.append(f"{i}. **{n['title']}** ({n['source']})")
            if n["summary"] and n["summary"] != n["title"]:
                lines.append(f"   - {n['summary']}")
            lines.append(f"   - {n['link']}")
    else:
        lines.append("_수집된 뉴스가 없습니다._")
    lines += [
        "",
        "## 🧭 오늘의 시장 해설",
        "",
        summary["commentary"] or "_해설 없음_",
        "",
        "---",
        "_본 보고서는 자동 생성되었으며 투자 권유가 아닙니다._",
        "",
    ]
    return "\n".join(lines)


def _render_movers(movers: dict) -> str:
    rises = movers.get("rises", [])
    falls = movers.get("falls", [])
    if not rises and not falls:
        return ""
    lines = ["### 📈 코스피 당일 등락 상위", ""]
    if rises:
        lines.append("**상승 Top 5**")
        for s in rises:
            lines.append(f"- {s['name']} `▲ {s['pct']:+.2f}%`")
    if falls:
        lines.append("")
        lines.append("**하락 Top 5**")
        for s in falls:
            lines.append(f"- {s['name']} `▼ {s['pct']:+.2f}%`")
    lines.append("")
    return "\n".join(lines)


def main():
    now = datetime.now(KST)
    market = fetch_market.fetch_all()
    movers = fetch_market.fetch_kospi_movers()
    news = fetch_news.fetch_news()
    summary = summarize(market, news)
    content = render(market, summary, now, movers)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"{now.strftime('%Y-%m-%d')}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(path)
    return path


if __name__ == "__main__":
    main()
