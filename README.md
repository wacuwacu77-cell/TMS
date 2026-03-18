# TMS — Tag Map System

> **AI-powered code navigation via natural language → exact file:line**
> **자연어 한 마디로 정확한 파일:라인을 찾아주는 AI 코드 내비게이션 엔진**

---

## What is TMS? / TMS란?

**[EN]**
TMS (Tag Map System) is a lightweight code navigation engine for AI coding assistants (GitHub Copilot, Cursor, etc.).

Instead of the AI reading thousands of lines to find a function, TMS resolves a natural language query to the **exact file and line number** in milliseconds.

**[KO]**
TMS(Tag Map System)는 GitHub Copilot, Cursor 등 AI 코딩 어시스턴트를 위한 경량 코드 내비게이션 엔진입니다.

AI가 함수를 찾기 위해 수천 줄을 통째로 읽는 대신, 자연어 쿼리 하나로 **정확한 파일:라인 번호**를 밀리초 안에 반환합니다.

```
사용자 →  "이미지 발송 부분 고쳐줘"
AI     →  resolve("이미지 발송")
       →  §KAKAO:IMAGE  →  core/kakao_controller.py:551
       →  해당 줄 ±30줄만 읽음  →  수정 완료

User  →  "fix the image send logic"
AI    →  resolve("image send")
      →  §KAKAO:IMAGE  →  core/kakao_controller.py:551
      →  read only ±30 lines  →  done
```

---

## Why I Built This / 만든 이유

**[EN]**
I don't know how to code. At all.

Everything I build is done through **vibe coding** — describing what I want in natural language and letting GitHub Copilot write the actual code. That means every single change I make costs tokens, and every interaction depends entirely on the AI understanding my intent.

My first project started as one massive context file — thousands of lines in a single `.py`. When it grew too large, I split it into multiple files by role. That's when the real problem started.

**After splitting:**
- I had no idea where any piece of code lived
- Every time I said *"fix the X feature"*, Copilot had to search through thousands of lines
- Each command burned tokens just for the AI to *find* the relevant code before even touching it
- Workflow slowed to a crawl

I couldn't fix this the "normal" way because I don't write code — I describe what I need. So I had to think of a solution that worked *within* my vibe coding workflow.

The idea I came up with:

> What if every function had a tag, and I pre-mapped the natural language phrases I'd likely say to those tags?

That way, when I say *"fix the image send part"*, the AI doesn't search — it **resolves** my words directly to the exact file and line. No wasted tokens. No blind searching.

That's TMS. Built by someone who can't code, for anyone else who codes the same way.

If you're a vibe coder who relies on AI assistants and hates watching tokens burn on file exploration — this was made for you.

---

**[KO]**
저는 코딩을 전혀 모릅니다.

제가 만드는 모든 것은 **바이브 코딩** 방식으로 만들어집니다. 원하는 것을 자연어로 설명하고 GitHub Copilot이 실제 코드를 작성하는 방식이죠. 즉, 모든 변경사항은 토큰 비용이 발생하고, 모든 상호작용은 AI가 제 의도를 얼마나 잘 파악하느냐에 달려 있습니다.

처음에는 수천 줄짜리 단일 `.py` 파일 하나로 시작했습니다. 파일이 너무 커지자 역할별로 여러 파일로 분리했는데, 그때부터 진짜 문제가 생겼습니다.

**파일 분리 후 문제점:**
- 어떤 코드가 어느 파일에 있는지 전혀 알 수 없었음
- *"X 기능 고쳐줘"* 라고 할 때마다 Copilot이 수천 줄을 처음부터 뒤져야 했음
- 실제 수정 전에 코드를 **찾는 것**만으로도 토큰이 낭비됨
- 업무 효율이 급격히 떨어짐

저는 코드를 직접 쓰지 않으므로 일반적인 방식으로는 이 문제를 해결할 수 없었습니다. 그래서 바이브 코딩 워크플로우 안에서 동작하는 해결책을 고민했습니다.

제가 생각해낸 아이디어:

> 각 함수마다 태그를 달고, 내가 자주 쓸 자연어 표현을 그 태그에 미리 매핑해두면 어떨까?

그러면 *"이미지 발송 부분 고쳐줘"* 라고 했을 때 AI가 검색하지 않고 — 제 말을 바로 정확한 파일과 라인으로 **해석**합니다. 토큰 낭비 없음. 맹목적인 탐색 없음.

이것이 TMS입니다. 코딩을 모르는 사람이, 같은 방식으로 코딩하는 모든 분들을 위해 만들었습니다.

AI 어시스턴트에 의존하면서 파일 탐색에 토큰이 낭비되는 것이 답답하셨던 바이브 코더라면 — 이 도구는 여러분을 위해 만들어졌습니다.

---

## The Problem It Solves / 해결하는 문제

| Without TMS / TMS 없이 | With TMS / TMS 사용 시 |
|---|---|
| AI reads 8,000-line file entirely / AI가 8,000줄 파일 전체를 읽음 | Pinpoints only the relevant section / 해당 섹션만 핀포인트 |
| AI guesses function/file names / AI가 함수·파일명을 추측함 | Natural language → tag → line, instantly / 자연어 → 태그 → 라인, 즉시 |
| Line numbers break after refactoring / 리팩토링 후 라인 번호 무효화 | `◆BM◆` marker-based, always accurate / 마커 기반으로 항상 정확 |
| Every new AI session re-explores / 새 AI 세션마다 처음부터 탐색 | TAG_MAP + auto-generated copilot-instructions / 자동 생성 인덱스로 즉시 파악 |

---

## Core Concept / 핵심 개념

### 1. Insert `◆BM◆` markers in your source files / 소스 파일에 `◆BM◆` 마커 삽입

```python
# ◆BM◆ ImageSendAPI | send image via clipboard paste, Ctrl+V method
# ◆BM◆ 이미지발송API | 클립보드 붙여넣기(Ctrl+V) 방식으로 이미지 발송
def send_image(self, hwnd, image_path):
    ...
```

### 2. `TAG_MAP.py` auto-scans and builds the index / 자동 스캔 및 인덱스 생성

```python
import TAG_MAP  # triggers _auto_sync() — scans all ◆BM◆ markers automatically
               # _auto_sync() 실행 — 모든 ◆BM◆ 마커를 자동 스캔
```

### 3. Resolve natural language to a code location / 자연어를 코드 위치로 변환

```python
results = TAG_MAP.resolve("이미지 발송")  # 한국어도 동작
results = TAG_MAP.resolve("image send")   # English also works
# → [{"tag": "§KAKAO:IMAGE", "file": "core/kakao_controller.py", "line": 551, ...}]
```

---

## Files / 파일 구성

| File | Role / 역할 |
|---|---|
| `TAG_MAP.py` | Natural language matching engine + auto-sync / 자연어 매칭 엔진 + 자동 동기화 |
| `bm.py` | Interactive bookmark explorer CLI / 대화형 북마크 탐색 CLI |
| `_bm_insert.py` | Helper to insert `◆BM◆` markers / 마커 삽입 도우미 |
| `_tms_propagate.py` | Propagate TMS to sub-projects / 하위 프로젝트에 TMS 전파 |
| `_tms_watch.py` | File watcher — auto re-sync on save / 파일 감시 — 저장 시 자동 재동기화 |

---

## Quick Start / 빠른 시작

### Step 1 — Copy files to your project root / 프로젝트 루트에 파일 복사

```
your_project/
├── TAG_MAP.py    ← copy here / 여기에 복사
├── bm.py         ← copy here / 여기에 복사
├── main.py
└── src/
    └── feature.py
```

### Step 2 — Add `◆BM◆` markers to your source / 소스에 마커 추가

```python
# ◆BM◆ UserLogin | handles login form submit, JWT token generation
# ◆BM◆ 로그인처리 | 로그인 폼 제출, JWT 토큰 생성
def login(request):
    ...
```

### Step 3 — Import TAG_MAP (one-time auto-sync) / TAG_MAP 임포트 (최초 1회 자동 동기화)

```python
import TAG_MAP
# Auto-scans all Python files, builds TAG_MAP, updates copilot-instructions.md
# 모든 Python 파일 자동 스캔, TAG_MAP 생성, copilot-instructions.md 갱신
```

### Step 4 — Use in your AI session / AI 세션에서 사용

Ask your AI assistant with your `.github/copilot-instructions.md` in context:
`.github/copilot-instructions.md` 파일을 컨텍스트에 포함한 상태에서 AI에게 요청:

```
"로그인 로직 고쳐줘"  →  AI가 resolve("로그인") 호출  →  src/auth.py:42
"Fix the login logic"  →  AI calls resolve("login")   →  src/auth.py:42
```

---

## Performance / 성능

| Optimization / 최적화 기법 | Effect / 효과 |
|---|---|
| `_RESOLVE_CACHE` — same query returns cached result / 동일 쿼리 캐시 반환 | **5,343× faster** on repeat queries / 반복 쿼리 5,343배 빠름 |
| `_PCACHE` — tokenize TAG_MAP once on load / TAG_MAP 최초 1회만 토큰화 | Eliminates repeated parsing / 반복 파싱 제거 |
| `_SYNONYM_MAP` — query expansion thesaurus / 쿼리 확장 시소러스 | 52% reduction in keyword bloat / 키워드 52% 절감 |

### Keywords anti-bloat via `_SYNONYM_MAP`

```python
# BAD: adding more and more keywords
"§AUTH:LOGIN": {"keywords": ["login", "sign in", "signin", "log in", "authenticate", ...]}

# GOOD: one keyword + synonym map
"§AUTH:LOGIN": {"keywords": ["login"]}

_SYNONYM_MAP = {
    "sign in":     "login",
    "authenticate":"login",
    "signin":      "login",
}
# Query "sign in" expands to "sign in login" → matches §AUTH:LOGIN
```

---

## Auto-generated `copilot-instructions.md` / 자동 생성 인덱스

**[EN]** On first `import TAG_MAP`, TMS creates `.github/copilot-instructions.md` with a full BM index:

**[KO]** 첫 `import TAG_MAP` 시 TMS가 `.github/copilot-instructions.md`에 전체 BM 인덱스를 자동 생성합니다:

```markdown
<!-- §META:BM_INDEX:BEGIN -->
| Tag | File | Line | Description |
|-----|------|------|-------------|
| §AUTH:LOGIN | src/auth.py | 42 | Login handler / 로그인 처리 |
...
<!-- §META:BM_INDEX:END -->
```

**[EN]** The AI assistant always has the full index in context — no searching needed.

**[KO]** AI 어시스턴트가 항상 전체 인덱스를 컨텍스트로 갖고 있어 탐색이 필요 없습니다.

---

## Two Deployment Patterns / 두 가지 배포 패턴

### External (multi-file projects) / 외장형 (다중 파일 프로젝트)
```
project/
├── TAG_MAP.py
├── core/auth.py      # ◆BM◆ markers here / ◆BM◆ 마커 삽입
└── ui/dashboard.py   # ◆BM◆ markers here / ◆BM◆ 마커 삽입
```

### Embedded (single large file) / 내장형 (대형 단일 파일)
```python
# Paste TMS engine at the top of your large single-file app
# 대형 단일 파일 상단에 TMS 엔진을 임베딩
_TMS_TAG_MAP = {
    "§IO:EXCEL": {"bm": "IO_EXCEL", "desc": "Excel export / 엑셀 저장", "keywords": ["excel", "엑셀"]},
    ...
}
```

---

## Requirements / 요구사항

- Python 3.9+
- No external dependencies (standard library only) / 외부 의존성 없음 (표준 라이브러리만 사용)

---

## License

MIT

---

*Developed in South Korea — first public commit: 2026-03-18*

*대한민국에서 개발 — 최초 공개 커밋: 2026-03-18*
