# TMS — Tag Map System

> **AI-powered code navigation via natural language → exact file:line**

---

## What is TMS?

TMS (Tag Map System) is a lightweight code navigation engine for AI coding assistants (GitHub Copilot, Cursor, etc.).

Instead of the AI reading thousands of lines to find a function, TMS resolves a natural language query to the **exact file and line number** in milliseconds.

```
User  →  "fix the image send logic"
AI    →  resolve("image send")
      →  §KAKAO:IMAGE  →  core/kakao_controller.py:551
      →  read only ±30 lines  →  done
```

---

## Why I Built This

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

## The Problem It Solves

| Without TMS | With TMS |
|---|---|
| AI reads 8,000-line file entirely | Pinpoints only the relevant section |
| AI guesses function/file names | Natural language → tag → line, instantly |
| Line numbers break after refactoring | `◆BM◆` marker-based, always accurate |
| Every new AI session re-explores | TAG_MAP + auto-generated copilot-instructions |

---

## Core Concept

### 1. Insert `◆BM◆` markers in your source files

```python
# ◆BM◆ ImageSendAPI | send image via clipboard paste, Ctrl+V method
def send_image(self, hwnd, image_path):
    ...
```

### 2. `TAG_MAP.py` auto-scans and builds the index

```python
import TAG_MAP  # triggers _auto_sync() — scans all ◆BM◆ markers automatically
```

### 3. Resolve natural language to a code location

```python
results = TAG_MAP.resolve("image send")
# → [{"tag": "§KAKAO:IMAGE", "file": "core/kakao_controller.py", "line": 551, ...}]
```

---

## Files

| File | Role |
|---|---|
| `TAG_MAP.py` | Natural language matching engine + auto-sync |
| `bm.py` | Interactive bookmark explorer CLI |
| `_bm_insert.py` | Helper to insert `◆BM◆` markers |
| `_tms_propagate.py` | Propagate TMS to sub-projects |
| `_tms_watch.py` | File watcher — auto re-sync on save |

---

## Quick Start

### Step 1 — Copy files to your project root

```
your_project/
├── TAG_MAP.py    ← copy here
├── bm.py         ← copy here
├── main.py
└── src/
    └── feature.py
```

### Step 2 — Add `◆BM◆` markers to your source

```python
# ◆BM◆ UserLogin | handles login form submit, JWT token generation
def login(request):
    ...
```

### Step 3 — Import TAG_MAP (one-time auto-sync)

```python
import TAG_MAP
# Auto-scans all Python files, builds TAG_MAP, updates copilot-instructions.md
```

### Step 4 — Use in your AI session

Ask your AI assistant with your `.github/copilot-instructions.md` in context:

```
"Fix the login logic"  →  AI calls resolve("login")  →  src/auth.py:42
```

---

## Performance

| Optimization | Effect |
|---|---|
| `_RESOLVE_CACHE` — same query returns cached result | **5,343× faster** on repeat queries |
| `_PCACHE` — tokenize TAG_MAP once on load | Eliminates repeated parsing |
| `_SYNONYM_MAP` — query expansion thesaurus | 52% reduction in keyword bloat |

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

## Auto-generated `copilot-instructions.md`

On first `import TAG_MAP`, TMS creates `.github/copilot-instructions.md` with a full BM index:

```markdown
<!-- §META:BM_INDEX:BEGIN -->
| Tag | File | Line | Description |
|-----|------|------|-------------|
| §AUTH:LOGIN | src/auth.py | 42 | Login handler |
...
<!-- §META:BM_INDEX:END -->
```

The AI assistant always has the full index in context — no searching needed.

---

## Two Deployment Patterns

### External (multi-file projects)
```
project/
├── TAG_MAP.py
├── core/auth.py      # ◆BM◆ markers here
└── ui/dashboard.py   # ◆BM◆ markers here
```

### Embedded (single large file)
```python
# Paste TMS engine at the top of your large single-file app
_TMS_TAG_MAP = {
    "§IO:EXCEL": {"bm": "IO_EXCEL", "desc": "Excel export", "keywords": ["excel"]},
    ...
}
```

---

## Requirements

- Python 3.9+
- No external dependencies (standard library only)

---

## License

MIT

---

*Developed in South Korea — first public commit: 2026-03-18*
