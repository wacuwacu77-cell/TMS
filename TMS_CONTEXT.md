# TMS (Tag Map System) — 완전 이식 컨텍스트
> **새 세션에서 TMS를 이식할 때 이 파일 하나만 참조하면 됩니다.**
> `#file:c:\Users\wacu\dist\TMS_CONTEXT.md`

---

## PART 1. TMS란 무엇인가

### 1-1. 핵심 개념

TMS는 소스코드에 `# ◆BM◆ 태그명 | 설명` 마커를 심고,
`resolve("자연어 쿼리")` 한 번으로 **정확한 파일:라인 번호**를 반환하는 **AI 코드 내비게이션 엔진**이다.

```
사용자 → "이미지 발송 부분 수정해줘"
AI     → resolve("이미지 발송") 
       → §KAKAO:IMAGE  →  core/kakao_controller.py:551
       → 해당 줄 ±30줄만 read_file → 수정 완료
```

### 1-2. 존재 이유

| 문제 | TMS 해결 |
|------|---------|
| AI가 8000줄 파일을 통째로 읽음 → 컨텍스트 낭비 | BM 인덱스로 해당 섹션만 핀포인트 |
| 함수명·파일명을 AI가 모름 | 자연어 → 태그 → 라인 자동 변환 |
| 코드 이동 시 라인 번호 무효화 | ◆BM◆ 마커 기반으로 항상 정확 |
| 새 세션에서 처음부터 탐색 | TAG_MAP + copilot-instructions 자동 생성 |

### 1-3. 두 가지 패턴

| 패턴 | 언제 사용 | 실제 예 |
|------|-----------|---------|
| **외장형** (다중 파일) | 일반 프로젝트 | `kakao_sender/TAG_MAP.py` |
| **내장형** (단일 파일) | 대형 단일 .py | `analysis_app.py` 상단 임베딩 |

### 1-4. 핵심 설계 철학 — keywords 비대화 악순환 방지

#### 문제: keywords를 늘릴수록 TAG_MAP이 비대해지는 악순환

```
처음: '§FILTER:MAIN': {keywords: ["필터", "검색"]}

탐색 실패 → "찾기"도 추가 → "검색어"도 추가 → "조회"도 추가 ...
→ 점점 커지는 TAG_MAP → copilot-instructions 비대화 → AI 컨텍스트 낭비
```

#### 해결: 쿼리 확장 시소러스 `_SYNONYM_MAP` / `_TMS_SYNONYM_MAP`

```python
# keywords에는 대표 단어 1개만
'§FILTER:MAIN': {keywords: ["필터"]}

# 시소러스가 쿼리를 실시간 확장
_TMS_SYNONYM_MAP = {
    "검색": "필터",   # "검색" 쿼리 → "검색 필터"로 확장 후 매칭
    "찾기": "필터",   # "찾기" 쿼리 → "찾기 필터"로 확장 후 매칭
    "조회": "불러오기",
    ...
}
# 결과: keywords 323개 → 155개 (52% 절감)
```

이 방향 전환으로 **keywords를 늘리는 대신 시소러스로 쿼리를 확장**하는 구조가 됐다.

#### 같이 도입된 성능 최적화 3종

| 기법 | 동작 | 효과 |
|------|------|------|
| `_PCACHE` / `_TMS_PCACHE` | TAG_MAP 전체 토큰·nospace를 최초 1회만 계산 | 반복 파싱 제거 |
| `_RESOLVE_CACHE` / `_TMS_RESOLVE_CACHE` | 동일 쿼리는 dict 조회로 즉시 반환 | **5343배** 속도 향상 |
| `_get_bm_desc()` | ◆BM◆ 마커 설명을 소스에서 동적 유추 | TAG_MAP에 `desc` 직접 기술 불필요 |

> **외장형** (`kakao_sender/TAG_MAP.py`): `_get_bm_desc(file, bm_tag)` — 파일을 열어 ◆BM◆ 줄 설명 추출  
> **내장형** (`analysis_app.py`): `info.get("desc", "")` — TAG_MAP 엔트리에 `desc` 키로 직접 보유

---

## PART 2. 핵심 데이터 구조

### 2-1. TAG_MAP 엔트리 — 외장형 (파일 참조 있음)

```python
"§KAKAO:IMAGE": {
    "file": "core/kakao_controller.py",   # 소스 파일 상대경로 (필수)
    "bm":   "이미지발송API",               # ◆BM◆ 마커 태그와 1:1 대응 (필수)
    "keywords": ["이미지", "사진", "발송", "첨부"],  # 자연어 검색 키워드
    "_auto": True,   # 자동 등록 항목에만 존재. 없으면 수동 큐레이션
},
```

### 2-2. TAG_MAP 엔트리 — 내장형 (단일 파일)

```python
'§IO:EXCEL': {
    "bm":      "IO_EXCEL",           # § 제거 + : → _ (단일 파일이라 file 필드 없음)
    "desc":    "엑셀 저장 (save_to_excel)",  # 설명 직접 포함
    "keywords": ["엑셀저장", "xlsx", "범례시트"],
    "_auto":   True,   # 자동 등록 항목에만
},
```

### 2-3. bm 명명 규칙

```
외장형:  자유로운 한국어/영어 (파일명 컨텍스트로 구분)
         예) "이미지발송API", "채팅방열기", "발송루프"

내장형:  §TAG → bm 자동 변환
         §CORE:BIAS   →  CORE_BIAS
         §UI:MAIN     →  UI_MAIN
         §IO:EXCEL    →  IO_EXCEL
         규칙: tag.lstrip("§").replace(":", "_")
```

### 2-4. ◆BM◆ 물리 마커 형식

```python
# ◆BM◆ 이미지발송API | 이미지 파일 클립보드 복사 후 Ctrl+V 발송
def send_image(self, hwnd, image_path):
    ...
```

```python
# ◆BM◆ IO_EXCEL | 엑셀 저장 (save_to_excel) — 등급색·신뢰도색·범례 포함
def save_to_excel(df, path):
    ...
```

- 태그명: 공백 없이 (붙여쓰기)
- `|` 이후: 설명·동의어를 풍부하게 → 검색 정확도 직결
- TAGmap 블록(`# §META:TAGMAP`) 내부 마커는 스캔에서 자동 제외

---

## PART 3. 완전 알고리즘

### 3-1. resolve() — 5단계 채점

```python
def resolve(query: str, top: int = 5) -> list[dict]:
    q = _expand_query(query.strip().lower())   # 시소러스 확장
    q_tokens = _tokenize(q)
    q_ns     = _nospace(q)                     # 붙여쓰기 정규화

    for tag, info in TAG_MAP.items():
        score = 0.0
        pc = _PCACHE[tag]   # 사전계산 캐시

        # ── Tier 1: 완전 일치 ──────────────────── (+200 / +150 / +100)
        if q in pc["tag_lower"] or pc["tag_lower"] in q:  score += 200
        if q in pc["bm_lower"]  or pc["bm_lower"]  in q:  score += 150
        if q in pc["kw_text"]:                             score += 100

        # ── Tier 2: 토큰 교집합 ─────────────────── (+30/개)
        overlap = q_tokens & (pc["bm_tokens"] | pc["kw_tokens"])
        score += len(overlap) * 30

        # ── Tier 3: 개별 토큰 포함 ──────────────── (+15/개)
        for qt in q_tokens:
            if qt in pc["kw_text"] or qt in pc["bm_lower"]: score += 15

        # ── Tier 4: nospace 붙여쓰기 매칭 ──────────(+80~160)
        if q_ns in pc["bm_ns"]  or pc["bm_ns"]  in q_ns:  score += 120
        if q_ns in pc["tag_ns"] or pc["tag_ns"] in q_ns:  score += 160
        if q_ns in pc["kw_ns"]:                            score += 80
        for kw_ns in pc["kw_list_ns"]:
            if q_ns in kw_ns or kw_ns in q_ns:
                score += 60; break             # 첫 매칭만 카운트

        # ── Tier 5: desc(설명문) 매칭 ───────────── (+10~90)
        desc = pc["desc"]
        if desc:
            score += len(q_tokens & pc["desc_tokens"]) * 25
            if q in desc:                      score += 90
            if q_ns in pc["desc_ns"] or pc["desc_ns"] in q_ns: score += 70
            for qt in q_tokens:
                if qt in desc:                 score += 10
            # 복합토큰 → desc 분해 매칭 ("사진발송" → "사진"+"발송" 각각)
            for qt in q_tokens:
                qt_ns = _nospace(qt)
                score += sum(1 for dt in pc["desc_tokens"]
                             if len(dt) >= 2 and dt in qt_ns) * 12

    # 결과: 라인 번호까지 포함해서 반환
    results = [{"tag", "file"(외장형만), "line", "bm", "keywords"}, ...]
```

### 3-2. _PCACHE — 사전 계산 캐시 구조

```python
_PCACHE[tag] = {
    "bm_lower":    bm.lower(),
    "tag_lower":   tag.lower(),
    "bm_ns":       _nospace(bm),           # 붙여쓰기 버전
    "tag_ns":      _nospace(tag),
    "bm_tokens":   _tokenize(bm + " " + tag),
    "kw_text":     " ".join(keywords).lower(),
    "kw_ns":       _nospace(kw_text),
    "kw_tokens":   _tokenize(kw_text),
    "kw_list_ns":  [_nospace(k) for k in keywords],
    "desc":        desc.lower(),           # 외장형: ◆BM◆ 마커에서 동적 추출
    "desc_ns":     _nospace(desc),         # 내장형: info["desc"] 직접 사용
    "desc_tokens": _tokenize(desc),
}
```

### 3-3. 시소러스 확장 (_SYNONYM_MAP)

```python
# kakao_sender 도메인 동의어 (25개 — keywords 비대화 방지 핵심)
_SYNONYM_MAP = {
    "방":      "채팅",     "단톡":       "그룹채팅",
    "창":      "윈도우",   "사진":       "이미지",
    "영상":    "동영상",   "문자":       "텍스트",
    "전송":    "발송",     "보내기":     "발송",
    "지연":    "딜레이",   "1:1":       "친구채팅",
    "단체":    "그룹",     "오픈":       "그룹",
    "개인":    "친구",     "비디오":     "동영상",
    "속도":    "딜레이",   "대기":       "딜레이",
    "닫기":    "종료",     "오픈채팅":   "그룹채팅",
    "단톡방":  "그룹채팅", "그룹방":     "그룹채팅",
    "개인톡":  "친구채팅",
}

# analysis_app 도메인 동의어 (18개)
_TMS_SYNONYM_MAP = {
    "예측":     "엔진",     "소진":     "재고",     "출고":   "배송",
    "농장":     "사양가",   "축사":     "사양가",   "차량":   "트럭",
    "검색":     "필터",     "찾기":     "필터",     "정렬":   "소트",
    "내보내기": "엑셀",     "다운로드": "엑셀",
    "다이얼로그":"팝업",   "모달":     "팝업",
    "체크":     "토글",     "끄기":     "토글",
    "실행":     "시작",     "조회":     "불러오기", "등록":   "추가",
    "제거":     "삭제",
}
```

_expand_query 동작:
```
resolve("단톡방 열기")  →  expand → "단톡방 열기 그룹채팅"  →  §KAKAO:OPEN_GROUP 매칭
resolve("엑셀저장")     →  expand → "엑셀저장 엑셀"         →  §IO:EXCEL 매칭
resolve("내보내기")     →  expand → "내보내기 엑셀"         →  §IO:EXCEL 매칭  (keyword 추가 불필요)
```

### 3-4. _auto_sync 동작 규칙 (핵심 불변 규칙)

```
◆BM◆ 마커 있음  +  TAG_MAP에 없음          →  자동 등록 (_auto=True)
◆BM◆ 마커 없음  +  TAG_MAP에 _auto=True    →  자동 제거
◆BM◆ 마커 없음  +  TAG_MAP에 _auto 키 없음 →  절대 건드리지 않음 (수동 큐레이션 보호)
```

---

## PART 4. 두 패턴 완전 비교

### 4-1. 외장형 — kakao_sender/TAG_MAP.py

**구조**: 독립 파일 `TAG_MAP.py` + 소스 파일들 분리

```python
# TAG_MAP.py 핵심 구성
TAG_MAP = { ... }              # §META:TAGMAP:BEGIN/END 블록
_get_bm_desc(rel, bm)          # 소스 파일에서 ◆BM◆ 설명 동적 추출
_find_bm_line(rel, bm)         # _ROOT/rel 파일을 열어 마커 탐색
_FILE_PREFIX = {               # 파일별 §접두사 매핑 (프로젝트 구조 정의)
    "main.py":                 "APP",
    "ui/main_window.py":       "WIN",
    "core/kakao_controller.py":"KAKAO",
    "db/database.py":          "DB",
}
_derive_prefix(rel_path)       # 미등록 파일 prefix 자동 유추
_scan_bookmarks()              # _ROOT.rglob("*.py") 전체 스캔
_auto_sync()                   # 모듈 로드 시 동기식 실행
_persist_tag_map()             # TAG_MAP.py BEGIN/END 블록 갱신
_persist_instructions()        # .github/copilot-instructions.md 갱신
bm_register(tag,file,bm,desc)  # 수동 등록 API
sync()                         # 상태 리포트 dict 반환
```

**실제 TAG_MAP 엔트리 (kakao_sender)**
- `§APP:ENTRY` → main.py
- `§WIN:INIT/STYLE/MENU/TABS/STATUSBAR/...` → ui/main_window.py (17개 섹션)
- `§TAB:SEND:*` → ui/tab_send.py (25개+)
- `§TAB:RECIP:*` → ui/tab_recipients.py
- `§TAB:TMPL:*/HIST:*` → ui/tab_templates_history.py
- `§SEND:TASK/THREAD/LOOP/EXECUTE` → core/sender.py
- `§KAKAO:INIT/FIND_MAIN/OPEN_CHAT/TEXT/IMAGE/VIDEO/...` → core/kakao_controller.py
- `§UTIL:GET_TEXT/SET_TEXT/CTRL_V/DELAY/...` → core/kakao_controller.py
- `§DB:CONN/CTX/INIT/RECIP:*/HIST:*/TMPL:*/SESSION:*` → db/database.py
- `§LOG:MEMORY/RECENT/SETUP/GET` → core/logger.py
- `§IO:EXCEL:READ/WRITE/SETTINGS` → data/excel_reader.py

**트리거 방식**: `main.py` 상단에서 `import TAG_MAP` → `_auto_sync()` 자동 실행

### 4-2. 내장형 — analysis_app.py (단일 파일 7351줄)

**구조**: 소스 파일 상단에 TAG_MAP + TMS 엔진 통째 임베딩

```python
# §META:TAGMAP:BEGIN
TAG_MAP: dict[str, dict] = {
    '§CORE:ENGINE': {"bm": "CORE_ENGINE", "desc": "...", "keywords": [...]},
    ...
}
# §META:TAGMAP:END

# TMS 엔진 함수들 (외장형과 동일 알고리즘, 단 file 필드 없음)
_tms_re / _TMS_MARKER_RE
_tms_tokenize / _tms_nospace / _tms_expand_query
_TMS_SYNONYM_MAP / _TMS_PCACHE / _TMS_RESOLVE_CACHE
resolve(query, top=5)
_tms_find_bm_line(bm_tag)      # __file__ (자기 자신)에서 탐색
_tms_scan_bm_markers()         # TAG_MAP 블록 제외 후 자기 자신 스캔
_tms_persist()                 # TAG_MAP 블록 갱신
_tms_persist_instructions()    # .github/copilot-instructions.md 갱신
_tagmap_register(tag, desc, kw) # 수동 등록 (기존 API 유지)
_tms_auto_sync()               # daemon thread로 비동기 실행

# 앱 하단 트리거
threading.Thread(target=_tms_auto_sync, daemon=True).start()
```

**실제 TAG_MAP 37개 엔트리 (analysis_app.py)**

| 태그 | BM | 설명 | 라인(2026-03-14 기준) |
|------|----|------|----------------------|
| §SYS:CONFIG | SYS_CONFIG | 설정 저장/복원 | ~452 |
| §CORE:BIAS | CORE_BIAS | 예측 편향 보정 | ~560 |
| §POPUP:CALENDAR:WIDGET | POPUP_CALENDAR_WIDGET | 날짜선택 위젯 | ~661 |
| §CORE:ENGINE | CORE_ENGINE | 사료 예측 엔진 | ~842 |
| §IO:EXCEL | IO_EXCEL | 엑셀 저장 | ~1271 |
| §POPUP:CREDIT | POPUP_CREDIT | 개발자 정보 팝업 | ~1419 |
| §UI:MAIN | UI_MAIN | 메인 창 (launch_gui) | ~1631 |
| §GUARD:FLASH | GUARD_FLASH | 팝업 깜빡임 경고 | ~1741 |
| §GUARD:POPUP | GUARD_POPUP | 팝업 중복 방지 | ~1769 |
| §GUARD:TOAST | GUARD_TOAST | 경고 토스트 알림 | ~1784 |
| §GUARD:RB_TOAST | GUARD_RB_TOAST | 우측 하단 비침습 알림 | ~1830 |
| §FILTER:SORT | FILTER_SORT | 컬럼 정렬 | ~1987 |
| §RENDER | RENDER | 결과 테이블 렌더 컨테이너 | ~2085 |
| §IO:UTILS | IO_UTILS | 이미지 저장/렌더 헬퍼 | ~2225 |
| §POPUP:CALENDAR | POPUP_CALENDAR | 소진 캘린더 팝업 | ~2251 |
| §POPUP:WEEKLY | POPUP_WEEKLY | 주간계획 팝업 | ~2482 |
| §FILTER:LEGEND | FILTER_LEGEND | 범례 필터 | (render_table 내) |
| §RENDER:TREE | RENDER_TREE | Treeview 생성 | ~2844 |
| §FILTER:DRAG | FILTER_DRAG | 드래그 다중 선택 | ~3047 |
| §FILTER:DELIVERED | FILTER_DELIVERED | 배송완료 토글 | ~3168 |
| §FILTER:MAIN | FILTER_MAIN | 실시간 필터 | ~3349 |
| §FILTER:CARD | FILTER_CARD | 요약카드 필터 | ~3534 |
| §POPUP:DETAIL | POPUP_DETAIL | 상세이력 팝업 | ~3587 |
| §POPUP:DETAIL:MEMO | POPUP_DETAIL_MEMO | 메모 저장 | ~3630 |
| §POPUP:DETAIL:TABLE | POPUP_DETAIL_TABLE | 이력 테이블 | ~3813 |
| §POPUP:DETAIL:GRAPH | POPUP_DETAIL_GRAPH | 이력 차트 | ~3944 |
| §IO:IMAGE | IO_IMAGE | 결과 이미지 빌드 | ~4165 |
| §IO:SAVE | IO_SAVE | 이미지 저장 | ~4323 |
| §IO:PRINT | IO_PRINT | 인쇄 미리보기 | ~4345 |
| §POPUP:DELIVERY | POPUP_DELIVERY | 배송 리포트 팝업 | ~4494 |
| §POPUP:TRUCK | POPUP_TRUCK | 배송현황 팝업 | ~5249 |
| §POPUP:SETTINGS | POPUP_SETTINGS | 설정 팝업 | ~5562 |
| §POPUP:FARM | POPUP_FARM | 사양가현황 팝업 | ~6331 |
| §POPUP:FARM:EDIT | POPUP_FARM_EDIT | 인라인 셀 편집 | ~6705 |
| §POPUP:FARM:SAVE | POPUP_FARM_SAVE | 전체 저장 | |
| §CORE:FILE_LOAD | CORE_FILE_LOAD | 파일 분석 시작 | |
| §CORE:QUEUE | CORE_QUEUE | 워커 큐 처리 | |

---

## PART 5. 지속화 시스템

### 5-1. §META:TAGMAP:BEGIN/END 블록

TAG_MAP 딕셔너리를 소스 파일 자체에 저장하는 자기수정(self-modifying) 패턴.

```
소스 파일
┌─────────────────────────────┐
│  ...                        │
│  # §META:TAGMAP:BEGIN       │ ← 이 사이를 _persist_*()가
│  TAG_MAP = { ... }          │   덮어씀 (자동 갱신)
│  # §META:TAGMAP:END         │
│  ...                        │
│  # ◆BM◆ IO_EXCEL | 설명    │ ← _scan_*()이 탐색
│  def save_to_excel():       │
└─────────────────────────────┘
```

### 5-2. copilot-instructions.md 자동 생성

```markdown
# 프로젝트명 — AI 탐색 지침

## 탐색 규칙
1. 파일 전체를 읽지 말 것 — BM 인덱스에서 관련 섹션을 찾는다
2. grep_search("◆BM◆ {BM태그}", file) 로 정확한 라인 번호를 찾는다
3. 해당 라인 ±30줄만 read_file로 읽어 컨텍스트를 파악한다

<!-- §META:BM_INDEX:BEGIN -->
### core/kakao_controller.py
| BM태그 | 설명 |
|--------|------|
| 이미지발송API | §KAKAO:IMAGE |
| 채팅방열기 | §KAKAO:OPEN_CHAT |
...
<!-- §META:BM_INDEX:END -->
```

---

## PART 6. 이식 절차 (6단계)

### STEP 1. 패턴 선택

```
단일 거대 파일 (1000줄+)?  →  내장형 (analysis_app.py 방식)
여러 파일로 구성?           →  외장형 (kakao_sender 방식)
```

### STEP 2. 파일 배치

**외장형**:
```
프로젝트/
├── TAG_MAP.py    ← kakao_sender/tagmap_kit/TAG_MAP.py 복사
├── bm.py         ← kakao_sender/tagmap_kit/bm.py 복사
├── main.py
└── src/
```

**내장형**:
```
# 소스 파일 상단 (import 블록 직후)에 TMS 엔진 블록을 직접 삽입
# c:\Users\wacu\dist\analysis_app.py lines 54~519 를 복사해서 적응
```

### STEP 3. 설정 수정

**외장형 — TAG_MAP.py 3곳**:
```python
# (A) TAG_MAP = {} 비우기 (마커 추가 후 auto_sync가 채움)

# (B) _FILE_PREFIX 프로젝트 구조에 맞게
_FILE_PREFIX = {
    "main.py":      "APP",
    "src/auth.py":  "AUTH",
    "src/api.py":   "API",
}

# (C) _SYNONYM_MAP 도메인 동의어
_SYNONYM_MAP = {
    "로그인": "인증",
    "가입":   "등록",
}
```

**내장형** — `_TMS_SYNONYM_MAP` 만 수정:
```python
_TMS_SYNONYM_MAP = {
    "예측": "소진",
    "배송": "출고",
}
```

### STEP 4. ◆BM◆ 마커 삽입

```python
# ◆BM◆ 로그인처리 | 사용자 인증, JWT 발급, 세션 생성
def login(username, password):
    ...

# ◆BM◆ DB_연결 | SQLite 데이터베이스 연결, 컨텍스트 관리자
class DatabaseManager:
    ...
```

**대량 삽입이 필요할 때** (기존 코드에 § 주석이 있는 경우):
`c:\Users\wacu\dist\_bm_insert.py` 패턴 참조 — § 주석 뒤에 ◆BM◆ 마커를 일괄 삽입하는 스크립트.

### STEP 5. 트리거 등록

**외장형**:
```python
# main.py 상단
import TAG_MAP  # 자동으로 _auto_sync() 실행됨
```

**내장형**:
```python
# 소스 파일 하단
threading.Thread(target=_tms_auto_sync, daemon=True).start()
```

### STEP 6. 검증

**외장형**:
```bash
python TAG_MAP.py --verify
# → ✅ ◆BM◆ 마커: N개 발견
# → ✅ TAG_MAP: N개 엔트리
# → ✅ stale 항목 없음
# → ✅ copilot-instructions.md 존재
# → ✅ resolve() 동작
```

**내장형** (tkinter 없는 환경):
```bash
python _tms_test.py  # c:\Users\wacu\dist\_tms_test.py 참조
```

---

## PART 7. 주요 API 레퍼런스

### resolve(query, top=5)

```python
# 외장형
import TAG_MAP
results = TAG_MAP.resolve("이미지 발송")
# [{"tag": "§KAKAO:IMAGE", "file": "core/kakao_controller.py",
#   "line": 551, "bm": "이미지발송API", "keywords": [...]}]

# 내장형 (analysis_app.py)
from analysis_app import resolve
results = resolve("엑셀저장")
# [{"tag": "§IO:EXCEL", "bm": "IO_EXCEL", "line": 1271, ...}]
```

### bm_register(tag, file, bm, desc, keywords=None) — 외장형 전용

```python
TAG_MAP.bm_register(
    tag="§AUTH:LOGIN",
    file="src/auth.py",
    bm="로그인처리",
    desc="사용자 인증, JWT 발급, 세션 생성",
    keywords=["로그인", "인증", "JWT"],
)
# TAG_MAP.py + copilot-instructions.md 동시 갱신
```

### _tagmap_register(tag, desc, kw) — 내장형 전용

```python
_tagmap_register("§NEW:FUNC", "새 기능 설명", ["키워드1", "키워드2"])
```

### sync() — 외장형 전용

```python
rpt = TAG_MAP.sync()
# {
#   "new": [{"tag", "file", "bm", "desc"}, ...],
#   "stale": [{"tag", "file", "bm"}, ...],
#   "auto_count": 5,
#   "curated_count": 50,
#   "total_code": 55,
#   "total_map": 55,
# }
```

---

## PART 8. 정확도 달성 히스토리

| 단계 | 정확도 | 주요 변경 | 핵심 인사이트 |
|------|--------|-----------|---------------|
| 초기 단순 키워드 | ~60% | exact match만 | — |
| Tier 1~3 계층 | ~75% | keywords **323개** | keywords 추가가 유일한 수단 |
| `_SYNONYM_MAP` 도입 | ~85% | 동의어 쿼리 확장 | **방향 전환**: 키워드 대신 시소러스 |
| `_PCACHE` + nospace | ~90% | 붙여쓰기 무시, 1회 파싱 | 성능 + 정확도 동시 향상 |
| `_RESOLVE_CACHE` + desc 채점 | ~95% | 동일 쿼리 즉시 반환 (5343배), desc 활용 | keywords 없이도 desc로 매칭 |
| 불필요 keywords 168개 제거 | ~95% | keywords **155개** (52% 절감) | 시소러스가 커버하므로 삭제 가능 |
| ◆BM◆ 마커 전체 삽입 후 | **100%** | analysis_app 16/16 통과 | BM desc 내용이 채점에 반영됨 |

### 해결된 엣지 케이스

```
"이력차트"  → §POPUP:DETAIL:GRAPH 아닌 §POPUP:DETAIL 이 1위
해결: §POPUP:DETAIL:GRAPH keywords에 "이력차트", "_show_chart" 추가

"사양가편집" → §POPUP:FARM:EDIT 아닌 §POPUP:FARM 이 1위
해결: §POPUP:FARM keywords에서 "사양가편집" 제거
     §POPUP:FARM:EDIT keywords에 "사양가편집", "농장편집" 추가
```

---

## PART 9. 이식 킷 파일 목록

```
c:\Users\wacu\dist\kakao_sender\tagmap_kit\
├── TAG_MAP.py       — 외장형 이식 템플릿 (빈 TAG_MAP, 완전한 엔진)
├── bm.py            — CLI 탐색기 (독립 동작, TAG_MAP 없이도 사용 가능)
└── 이식방법.txt     — 6단계 설치 가이드

c:\Users\wacu\dist\
├── TMS_SESSION.md   — 세션 이식 파일 (이 세션 재개 시 참조)
├── TMS_CONTEXT.md   — 이 파일 (TMS 이식 시 AI에게 제공하는 완전 컨텍스트)
├── _bm_insert.py    — ◆BM◆ 마커 일괄 삽입 스크립트 (기존 코드 대량 마킹)
└── _tms_test.py     — 내장형 TMS 테스트 스크립트

레퍼런스 구현:
  c:\Users\wacu\dist\kakao_sender\TAG_MAP.py    — 완성형 외장형 (155 엔트리)
  c:\Users\wacu\dist\analysis_app.py            — 완성형 내장형 (37 엔트리, 7351줄)
```

---

## PART 10. 새 프로젝트 이식 요청 방법

새 세션에서 이 파일을 참조해서 TMS 이식을 요청하려면:

```
#file:c:\Users\wacu\dist\TMS_CONTEXT.md

[프로젝트명]에 TMS를 이식해줘.

프로젝트 루트: [경로]
패턴: 외장형 / 내장형 (선택)
주요 파일:
  - main.py
  - src/auth.py
  - src/database.py
  ...

도메인 동의어: (있으면 제공)
  "회원" → "사용자"
  "주문" → "결제"
```

TMS 전담 세션: `#file:c:\Users\wacu\dist\TMS_SESSION.md`

---

## PART 11. 알고리즘 전체 소스 (복사용)

### 11-1. 핵심 유틸 함수

```python
import re

_TMS_MARKER_RE = re.compile(r"#\s*◆BM◆\s+(\S+)\s*\|\s*(.+)")

def _tms_tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[\s_,|·§:/\-\(\)]+", text.lower()) if len(t) >= 2}

def _tms_nospace(text: str) -> str:
    return re.sub(r"[\s_\-]+", "", text.lower())

def _tms_expand_query(q: str) -> str:
    tokens = _tms_tokenize(q)
    extras = [_TMS_SYNONYM_MAP[t] for t in tokens if t in _TMS_SYNONYM_MAP]
    expanded = (q + " " + " ".join(extras)).strip() if extras else q
    q_ns = _tms_nospace(q)
    for src_kw, dst_kw in _TMS_SYNONYM_MAP.items():
        src_ns = _tms_nospace(src_kw)
        if len(src_ns) >= 2 and src_ns in q_ns:
            expanded = expanded + " " + q_ns.replace(src_ns, _tms_nospace(dst_kw))
    return expanded.strip()
```

### 11-2. PCACHE 빌드 — 내장형 버전

```python
_TMS_PCACHE: dict[str, dict] = {}

def _tms_build_pcache() -> None:
    for tag, info in TAG_MAP.items():
        bm  = info.get("bm", "")
        desc = info.get("desc", "").lower()
        kw_text = " ".join(info.get("keywords", []))
        _TMS_PCACHE[tag] = {
            "bm_lower":    bm.lower(),
            "tag_lower":   tag.lower(),
            "bm_ns":       _tms_nospace(bm),
            "tag_ns":      _tms_nospace(tag),
            "bm_tokens":   _tms_tokenize(bm + " " + tag),
            "kw_text":     kw_text.lower(),
            "kw_ns":       _tms_nospace(kw_text),
            "kw_tokens":   _tms_tokenize(kw_text),
            "kw_list_ns":  [_tms_nospace(k) for k in info.get("keywords", [])],
            "desc":        desc,
            "desc_ns":     _tms_nospace(desc),
            "desc_tokens": _tms_tokenize(desc),
        }
```

### 11-3. 마커 탐색 — 내장형 (_tms_find_bm_line)

```python
def _tms_find_bm_line(bm_tag: str) -> int:
    """이 파일(단일 파일)에서 ◆BM◆ <bm_tag> 마커 라인 번호 반환."""
    _S = "# §META:TAGMAP:BEGIN"
    _E = "# §META:TAGMAP:END"
    try:
        src = open(__file__, encoding="utf-8").read()
        # TAG_MAP 블록 제외
        try:
            s, e = src.index(_S), src.index(_E) + len(_E)
            src_scan = src[:s] + src[e:]
        except ValueError:
            src_scan = src
        for i, line in enumerate(src_scan.splitlines(), 1):
            m = _TMS_MARKER_RE.search(line)
            if m and m.group(1) == bm_tag:
                return i
    except Exception:
        pass
    return 0
```

### 11-4. _auto_sync — 내장형 버전

```python
def _tms_auto_sync() -> None:
    markers = _tms_scan_bm_markers()
    code_bms = {m["bm"] for m in markers}
    code_desc_inline = {m["bm"]: m["desc_inline"] for m in markers}
    map_by_bm = {info.get("bm", ""): tag for tag, info in TAG_MAP.items()}
    changed = False

    # _auto 항목 중 마커가 사라진 것 제거
    stale = [tag for tag, info in list(TAG_MAP.items())
             if info.get("_auto") and info.get("bm", "") not in code_bms]
    for tag in stale:
        del TAG_MAP[tag]; changed = True

    # 새 ◆BM◆ 마커 자동 등록
    stopwords = {"및","의","을","를","에","에서","로","으로","후","시"}
    for bm in sorted(code_bms):
        if bm not in map_by_bm:
            desc_inline = code_desc_inline.get(bm, "")
            parts = bm.split("_")
            tag = "§" + ":".join(parts) if len(parts) >= 2 else "§" + bm
            keywords = [w for w in re.split(r"[,\s/·|()\[\]—\-]+", desc_inline)
                        if len(w) >= 2 and w not in stopwords]
            TAG_MAP[tag] = {
                "bm": bm, "desc": desc_inline or f"(자동감지) {bm}",
                "keywords": keywords, "_auto": True,
            }
            changed = True

    if changed:
        _TMS_PCACHE.clear()
        _TMS_RESOLVE_CACHE.clear()
        _tms_persist()
        _tms_persist_instructions()
```

---

## PART 12. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| resolve() 결과 없음 | PCACHE 미초기화 | `_tms_build_pcache()` 직접 호출 |
| 라인 번호 0 반환 | ◆BM◆ 마커 없음 | 해당 섹션에 마커 삽입 |
| auto_sync 후 TAG_MAP 비어있음 | stale 전체 삭제됨 | `_auto` 없는 수동 큐레이션으로 등록 |
| § 문자 MISS | 파이썬 인라인 -c 문자열 인코딩 | .py 파일로 작성 후 실행 |
| 정확도 낮음 | 동의어·keywords 부족 | `_SYNONYM_MAP` + 해당 태그 keywords 보강 |
| 잘못된 태그 1위 | 상위 태그 keywords 과다 | 해당 키워드를 구체적 하위 태그로 이동 |
