"""뉴스 수집: 매체별 RSS → 키워드 필터 → 중복 제거 → 시장영향도 순 후보 리스트.

RSS URL 은 런타임 유효성 검사 대상이며, 차단/변경 시 해당 매체만 건너뛴다.
최종 Top 5~7 선별/요약은 build_report.py 가 (Claude API 또는 규칙 기반으로) 수행한다.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:
    requests = None

try:
    import feedparser
except ImportError:
    feedparser = None

KST = timezone(timedelta(hours=9))

# 후보 RSS(런타임 검증). 매체별로 여러 후보를 두어 첫 URL이 막히면 다음을 시도한다.
# 인베스팅닷컴은 403 이 잦아 후순위.
FEEDS = [
    {
        "name": "연합뉴스",
        "urls": [
            "https://www.yna.co.kr/rss/economy.xml",
            "https://www.yna.co.kr/rss/news.xml",
            "https://www.yna.co.kr/rss/all.xml",
        ],
    },
    {
        "name": "매일경제",
        "urls": [
            "https://www.mk.co.kr/rss/30100041/",  # 경제
            "https://www.mk.co.kr/rss/40300001/",  # 증권
            "https://www.mk.co.kr/rss/30000001/",  # 전체
        ],
    },
    {
        "name": "인베스팅닷컴",
        "urls": [
            "https://kr.investing.com/rss/news_25.rss",  # 경제
            "https://kr.investing.com/rss/news.rss",
            "https://www.investing.com/rss/news.rss",
        ],
    },
]

# 시장영향도 키워드(가중치 부여용) — 경제·금융·지정학·정책·사건사고
KEYWORDS = [
    # 경제·금융
    "금리", "환율", "유가", "원유", "금값", "증시", "코스피", "코스닥", "나스닥",
    "S&P", "다우", "연준", "Fed", "FOMC", "물가", "인플레", "수출", "반도체",
    "달러", "엔화", "위안", "채권", "국채", "실적", "고용", "무역", "관세",
    "원자재", "비트코인", "가상자산", "경기", "GDP", "부채", "긴축", "완화",
    "금통위", "기준금리", "한은", "외환보유액", "경상수지", "무역수지",
    # 지정학·국제 정세
    "전쟁", "분쟁", "제재", "외교", "협정", "조약", "북한", "중동", "우크라이나",
    "대만", "NATO", "G7", "G20", "OPEC", "이스라엘", "러시아", "트럼프",
    "미중", "미국 대통령", "지정학",
    # 한국 정치·정책
    "국회", "정부", "대통령", "법안", "규제", "세금", "추경", "예산",
    "공정위", "금감원", "금융위", "산업부",
    # 사건·사고
    "지진", "태풍", "홍수", "화재", "폭발", "파업", "항만", "물류", "공급망",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyMarketReport/1.0)"}


def _normalize(title: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", title.lower())


def _words(title: str) -> set:
    """제목에서 의미 있는 단어 집합 추출(2자 이상). 특수문자는 공백으로 치환."""
    clean = re.sub(r"[^\w가-힣]", " ", title)
    return {w for w in clean.split() if len(w) >= 2}


def _is_duplicate(title: str, seen_words: list) -> bool:
    """overlap coefficient 0.6 이상이면 중복으로 간주.
    짧은 제목이 긴 제목의 부분집합인 경우도 잡기 위해 min 기반 측정 사용."""
    w = _words(title)
    if not w:
        return False
    for sw in seen_words:
        intersection = len(w & sw)
        denom = min(len(w), len(sw))
        if denom > 0 and intersection / denom >= 0.6:
            return True
    return False


def _score(title: str) -> int:
    return sum(1 for kw in KEYWORDS if kw.lower() in title.lower())


def _parse_feed(url: str):
    """requests(UA 지정)로 받아 feedparser 파싱. 실패 시 빈 리스트."""
    if feedparser is None:
        return []
    try:
        if requests is not None:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
        else:
            parsed = feedparser.parse(url)
        return parsed.entries or []
    except Exception as exc:
        print(f"[warn] RSS 실패 {url}: {exc}", file=sys.stderr)
        return []


def _published(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None) or entry.get(key) if hasattr(entry, "get") else None
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).astimezone(KST)
            except Exception:
                pass
    return None


def fetch_news(max_candidates: int = 30) -> list:
    candidates = []
    seen_norm = set()    # 완전 중복 제거
    seen_words = []      # 유사도 기반 중복 제거

    for feed in FEEDS:
        entries = []
        for url in feed["urls"]:
            entries = _parse_feed(url)
            if entries:
                break  # 첫 성공 URL 사용
        for entry in entries:
            title = (getattr(entry, "title", "") or "").strip()
            link = (getattr(entry, "link", "") or "").strip()
            if not title or not link:
                continue
            norm = _normalize(title)
            if not norm or norm in seen_norm:
                continue
            # 유사도 기반 중복 제거
            if _is_duplicate(title, seen_words):
                continue
            seen_norm.add(norm)
            seen_words.append(_words(title))
            pub = _published(entry)
            candidates.append(
                {
                    "title": title,
                    "link": link,
                    "source": feed["name"],
                    "published": pub.strftime("%Y-%m-%d %H:%M") if pub else None,
                    "_score": _score(title),
                    "_ts": pub.timestamp() if pub else 0.0,
                }
            )

    # 시장영향도(키워드 점수) → 최신순
    candidates.sort(key=lambda c: (c["_score"], c["_ts"]), reverse=True)
    return candidates[:max_candidates]


if __name__ == "__main__":
    items = fetch_news()
    print(json.dumps(items, ensure_ascii=False, indent=2))
    print(f"\n# 후보 {len(items)}건", file=sys.stderr)
