"""시세 수집 + 일/월/연 변동 계산.

GitHub Actions(인터넷 개방)에서 실행되는 것을 전제로 yfinance 를 사용한다.
- 일  = 직전 거래일 종가 대비
- 월  = 1개월 전 캘린더일 '이전의 가장 가까운 거래일' 종가 대비
- 연  = 1년  전 캘린더일 '이전의 가장 가까운 거래일' 종가 대비
개별 티커 실패는 N/A 로 격리하고 나머지는 정상 출력한다.
주말/휴장이어도 yfinance 가 '최근 거래일 종가'를 최신값으로 주므로 별도 분기 불필요하며,
각 항목의 데이터 기준일(as_of)을 함께 기록한다.
"""
from __future__ import annotations

import ast
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd  # noqa: E402  (yfinance 의존성으로 함께 설치됨)

try:
    import yfinance as yf
except ImportError:  # 검증/오프라인 환경 대비
    yf = None

from watchlist import WATCHLIST, all_tickers  # noqa: E402

KST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------- 계산 헬퍼
def _pct(curr, prev):
    if curr is None or prev in (None, 0):
        return None
    return (curr - prev) / prev * 100.0


def _close_on_or_before(closes: pd.Series, target: pd.Timestamp):
    sub = closes[closes.index <= target]
    if len(sub) == 0:
        return None
    return float(sub.iloc[-1])


def compute_changes(closes: pd.Series) -> dict:
    """종가 시리즈(date index)에서 현재가/기준일/일·월·연 변동률 산출."""
    if closes is None:
        return {"price": None, "as_of": None, "day": None, "month": None, "year": None}
    closes = closes.dropna().sort_index()
    if len(closes) == 0:
        return {"price": None, "as_of": None, "day": None, "month": None, "year": None}

    latest_date = closes.index[-1]
    latest = float(closes.iloc[-1])
    prev = float(closes.iloc[-2]) if len(closes) >= 2 else None
    month_close = _close_on_or_before(closes, latest_date - pd.DateOffset(months=1))
    year_close = _close_on_or_before(closes, latest_date - pd.DateOffset(years=1))

    return {
        "price": latest,
        "as_of": latest_date.strftime("%Y-%m-%d"),
        "day": _pct(latest, prev),
        "month": _pct(latest, month_close),
        "year": _pct(latest, year_close),
    }


# ---------------------------------------------------------------- 데이터 소스
def _download(tickers):
    if yf is None:
        return None
    try:
        return yf.download(
            tickers,
            period="2y",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception as exc:  # 전체 실패 시 None → 항목별 폴백
        print(f"[warn] yf.download 실패: {exc}", file=sys.stderr)
        return None


def _extract_close(data, ticker):
    if data is None:
        return None
    try:
        if isinstance(data.columns, pd.MultiIndex):
            return data[ticker]["Close"]
        return data["Close"]
    except Exception:
        return None


def _naver_index(symbol: str):
    """yfinance 실패 시 KOSPI/KOSDAQ 일봉 폴백(네이버 공개 엔드포인트)."""
    try:
        import requests

        end = datetime.now(KST).strftime("%Y%m%d")
        start = (datetime.now(KST) - timedelta(days=800)).strftime("%Y%m%d")
        url = (
            "https://api.finance.naver.com/siseJson.naver?"
            f"symbol={symbol}&requestType=1&startTime={start}&endTime={end}&timeframe=day"
        )
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        rows = ast.literal_eval(r.text.strip())
        body = rows[1:]  # 0번은 헤더
        idx = pd.DatetimeIndex([pd.to_datetime(str(x[0])) for x in body])
        close = [float(x[4]) for x in body]
        return pd.Series(close, index=idx)
    except Exception as exc:
        print(f"[warn] 네이버 폴백 실패({symbol}): {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------- 메인
def fetch_all() -> dict:
    data = _download(all_tickers())
    result = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "categories": {},
    }

    for cat, items in WATCHLIST.items():
        rows = []
        for item in items:
            row = {k: item.get(k) for k in ("ticker", "name", "unit", "decimals")}
            closes = _extract_close(data, item["ticker"])

            if (closes is None or closes.dropna().empty) and item.get("naver"):
                closes = _naver_index(item["naver"])

            ch = compute_changes(closes)
            scale = item.get("scale")
            if scale and ch.get("price") is not None:
                ch["price"] = ch["price"] * scale

            row.update(ch)
            row["error"] = ch["price"] is None
            rows.append(row)
        result["categories"][cat] = rows

    return result


# ---------------------------------------------------------------- 표 렌더링
def _fmt_pct(v):
    if v is None:
        return "N/A"
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "—")
    return f"{arrow} {v:+.2f}%"


def _fmt_price(v, decimals):
    if v is None:
        return "N/A"
    return f"{v:,.{int(decimals)}f}"


def to_markdown(data: dict) -> str:
    out = []
    for cat, rows in data["categories"].items():
        out.append(f"### {cat}\n")
        out.append("| 지표 | 기준일 | 현재가 | 일 | 월 | 연 |")
        out.append("|---|---|---:|---:|---:|---:|")
        for r in rows:
            price = _fmt_price(r["price"], r["decimals"])
            unit = r["unit"]
            price_cell = f"{price} {unit}" if r["price"] is not None else "N/A"
            out.append(
                f"| {r['name']} | {r['as_of'] or '-'} | {price_cell} "
                f"| {_fmt_pct(r['day'])} | {_fmt_pct(r['month'])} | {_fmt_pct(r['year'])} |"
            )
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    d = fetch_all()
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(d))
