"""지표 워치리스트 정의.

사용자가 종목을 추가/삭제하기 가장 쉬운 단일 지점.
각 항목:
  ticker   : yfinance 심볼
  name     : 보고서에 표시할 한글명
  unit     : 단위(표시용)
  decimals : 현재가 소수 자릿수
  scale    : (선택) 현재가에 곱할 보정 계수. 예) ^TNX 는 수익률×10 으로 들어와 0.1
  naver    : (선택) yfinance 실패 시 네이버 지수 폴백 심볼(KOSPI/KOSDAQ)
"""

WATCHLIST = {
    "원자재": [
        {"ticker": "GC=F",  "name": "금",       "unit": "$/oz",    "decimals": 2},
        {"ticker": "SI=F",  "name": "은",       "unit": "$/oz",    "decimals": 2},
        {"ticker": "HG=F",  "name": "구리",     "unit": "$/lb",    "decimals": 3},
        {"ticker": "CL=F",  "name": "WTI 원유", "unit": "$/bbl",   "decimals": 2},
        {"ticker": "BZ=F",  "name": "브렌트유", "unit": "$/bbl",   "decimals": 2},
        {"ticker": "NG=F",  "name": "천연가스", "unit": "$/MMBtu", "decimals": 3},
        {"ticker": "TIO=F", "name": "철광석",   "unit": "$/t",     "decimals": 2},
        {"ticker": "ZC=F",  "name": "옥수수",   "unit": "¢/bu",    "decimals": 2},
        {"ticker": "ZW=F",  "name": "밀",       "unit": "¢/bu",    "decimals": 2},
        {"ticker": "ZS=F",  "name": "대두",     "unit": "¢/bu",    "decimals": 2},
    ],
    "증시": [
        {"ticker": "^KS11", "name": "코스피",     "unit": "pt", "decimals": 2, "naver": "KOSPI"},
        {"ticker": "^KQ11", "name": "코스닥",     "unit": "pt", "decimals": 2, "naver": "KOSDAQ"},
        {"ticker": "^GSPC", "name": "S&P 500",   "unit": "pt", "decimals": 2},
        {"ticker": "^IXIC", "name": "나스닥",     "unit": "pt", "decimals": 2},
        {"ticker": "^DJI",  "name": "다우",       "unit": "pt", "decimals": 2},
        {"ticker": "^N225", "name": "닛케이225",  "unit": "pt", "decimals": 2},
        {"ticker": "000001.SS", "name": "상하이종합", "unit": "pt", "decimals": 2},
    ],
    "환율·금리": [
        {"ticker": "KRW=X",     "name": "원/달러",     "unit": "원",  "decimals": 2},
        {"ticker": "EURUSD=X",  "name": "유로/달러",   "unit": "$",   "decimals": 4},
        {"ticker": "JPY=X",     "name": "달러/엔",     "unit": "엔",  "decimals": 2},
        {"ticker": "DX-Y.NYB",  "name": "달러인덱스",  "unit": "pt",  "decimals": 2},
        {"ticker": "^TNX",      "name": "미 국채10년", "unit": "%",   "decimals": 2, "scale": 0.1},
    ],
    "암호화폐": [
        {"ticker": "BTC-USD", "name": "비트코인",   "unit": "$", "decimals": 0},
        {"ticker": "ETH-USD", "name": "이더리움",   "unit": "$", "decimals": 0},
    ],
}


def all_tickers():
    return [item["ticker"] for items in WATCHLIST.values() for item in items]
