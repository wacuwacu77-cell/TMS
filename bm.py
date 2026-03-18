#!/usr/bin/env python
"""
bm.py — 코드 북마크 탐색 도구

소스 파일에 삽입된  # ◆BM◆ <태그> | <설명>  마커를 스캔하고
자연어 쿼리로 해당 코드 위치를 찾아줍니다.

사용법:
  python bm.py               # 대화형 모드 (권장)
  python bm.py list          # 전체 북마크 목록 출력
  python bm.py find <쿼리>   # 직접 검색 후 출력
"""

import re
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
MARKER_RE = re.compile(r"#\s*◆BM◆\s+(\S+)\s*\|\s*(.+)")
ROOT = Path(__file__).parent
SNIPPET_ROWS = 15  # 미리보기 최대 줄 수
TOP_N = 5  # 검색 결과 최대 개수

EXCLUDE_DIRS = {"__pycache__", "build", ".git", "venv", ".venv"}
EXCLUDE_FILES = {"bm.py"}


# ─────────────────────────────────────────
# 스캔
# ─────────────────────────────────────────
def scan_bookmarks() -> list[dict]:
    """모든 .py 파일에서 ◆BM◆ 마커를 스캔하여 반환."""
    bookmarks = []

    for py_file in sorted(ROOT.rglob("*.py")):
        if any(part in EXCLUDE_DIRS for part in py_file.parts):
            continue
        if py_file.name in EXCLUDE_FILES:
            continue

        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for lineno, line in enumerate(lines, 1):
            m = MARKER_RE.search(line)
            if not m:
                continue

            tag = m.group(1).strip()
            desc = m.group(2).strip()

            snippet_lines = []
            for sl in lines[lineno : lineno + SNIPPET_ROWS + 5]:
                if MARKER_RE.search(sl):
                    break
                snippet_lines.append(sl)
                if len(snippet_lines) >= SNIPPET_ROWS:
                    break

            bookmarks.append(
                dict(
                    tag=tag,
                    desc=desc,
                    file=str(py_file.relative_to(ROOT)),
                    abspath=str(py_file),
                    line=lineno,
                    snippet="\n".join(snippet_lines),
                )
            )

    return bookmarks


# ─────────────────────────────────────────
# 점수 계산 — 5단계 채점 알고리즘
# ─────────────────────────────────────────
def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[\s_,|·◆§:/\-\(\)]+", text.lower()) if len(t) >= 2}


def _nospace(text: str) -> str:
    """공백·구분자 제거 (붙여쓰기 매칭용)."""
    return re.sub(r"[\s_\-]+", "", text.lower())


def _score(bm: dict, query: str) -> float:
    q = query.strip().lower()
    q_tokens = _tokenize(q)
    q_ns = _nospace(q)

    tag  = bm["tag"].lower()
    desc = bm["desc"].lower()
    tag_ns  = _nospace(tag)
    desc_ns = _nospace(desc)
    tag_toks  = _tokenize(tag)
    desc_toks = _tokenize(desc)

    score = 0.0

    # Tier 1: 완전 일치
    if q == tag:                              score += 300
    elif q in tag or tag in q:                score += 200
    if q in desc:                             score += 150

    # Tier 2: 토큰 교집합
    all_toks = tag_toks | desc_toks
    overlap = q_tokens & all_toks
    score += len(overlap) * 30

    # Tier 3: 개별 토큰 포함
    combined = tag + " " + desc
    for qt in q_tokens:
        if qt in combined:
            score += 15

    # Tier 4: nospace 붙여쓰기 매칭
    if q_ns:
        if q_ns in tag_ns or tag_ns in q_ns:  score += 160
        if q_ns in desc_ns or desc_ns in q_ns: score += 70

    # Tier 5: desc 토큰 세밀 매칭
    if desc:
        desc_overlap = q_tokens & desc_toks
        score += len(desc_overlap) * 25
        for qt in q_tokens:
            qt_ns = _nospace(qt)
            score += sum(1 for dt in desc_toks if len(dt) >= 2 and dt in qt_ns) * 12

    return score


def find_best(bookmarks: list[dict], query: str, top: int = TOP_N) -> list[dict]:
    scored = [(s, bm) for bm in bookmarks if (s := _score(bm, query)) > 0]
    scored.sort(key=lambda x: -x[0])
    return [bm for _, bm in scored[:top]]


# ─────────────────────────────────────────
# 출력 헬퍼
# ─────────────────────────────────────────
def _print_bm(bm: dict, idx: int | None = None, show_snippet: bool = True):
    num = f"[{idx}] " if idx is not None else ""
    print(f"\n  {num}◆ [{bm['tag']}]  {bm['desc']}")
    print(f"      📄 {bm['file']}  :  {bm['line']}줄")
    if show_snippet and bm["snippet"].strip():
        print("      ┌─ 코드 미리보기 ──────────────────────────")
        for sl in bm["snippet"].splitlines()[:SNIPPET_ROWS]:
            print(f"      │ {sl}")
        print("      └─────────────────────────────────────────")


def _print_list(bookmarks: list[dict]):
    if not bookmarks:
        print("  (북마크 없음)")
        return
    print(f"\n  {'#':>3}  {'태그':<22}  {'설명':<45}  위치")
    print(f"  {'─' * 3}  {'─' * 22}  {'─' * 45}  {'─' * 20}")
    for i, bm in enumerate(bookmarks, 1):
        loc = f"{bm['file']}:{bm['line']}"
        print(f"  {i:>3}  {bm['tag']:<22}  {bm['desc'][:45]:<45}  {loc}")


# ─────────────────────────────────────────
# VS Code 열기
# ─────────────────────────────────────────
def _open_vscode(bm: dict):
    target = f"{bm['abspath']}:{bm['line']}"
    try:
        subprocess.Popen(["code", "--goto", target])
        print(f"  ✅ VS Code 에서 열었습니다 → {bm['file']}:{bm['line']}")
    except FileNotFoundError:
        print("  ⚠  'code' 명령을 찾을 수 없습니다.")
        print(f"     직접 열어주세요: {bm['file']}  :  {bm['line']}줄")


# ─────────────────────────────────────────
# 대화형 모드
# ─────────────────────────────────────────
_HELP = """
  명령어:
    list              — 전체 북마크 목록
    find <쿼리>       — 자연어 검색  (또는 쿼리만 입력)
    open <번호>       — 검색 결과를 VS Code 에서 열기
    help              — 이 도움말
    q / quit          — 종료
"""


def _interactive(bookmarks: list[dict]):
    project = Path(__file__).parent.name
    print("\n ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   📌  {project} — 코드 북마크 탐색기")
    print(f"   총 {len(bookmarks)}개 북마크 인덱싱 완료")
    print(" ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  쿼리만 입력하면 바로 검색됩니다. (help 로 도움말)")

    last_results: list[dict] = []

    while True:
        try:
            raw = input("\n  BM> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  종료합니다.")
            break

        if not raw:
            continue

        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("q", "quit", "exit"):
            print("  종료합니다.")
            break

        elif cmd == "help":
            print(_HELP)

        elif cmd == "list":
            _print_list(bookmarks)

        elif cmd in ("find", "f", "검색"):
            if not arg:
                print("  사용법:  find <자연어 쿼리>")
                continue
            last_results = find_best(bookmarks, arg)
            if not last_results:
                print("  ❌ 일치하는 북마크가 없습니다.")
            else:
                for i, bm in enumerate(last_results, 1):
                    _print_bm(bm, idx=i)
                print("\n  → open <번호>  으로 VS Code 에서 열 수 있습니다.")

        elif cmd in ("open", "o"):
            if not last_results:
                print("  먼저 find 명령으로 검색하세요.")
                continue
            try:
                _open_vscode(last_results[int(arg) - 1])
            except (ValueError, IndexError):
                print(f"  번호를 1 ~ {len(last_results)} 범위로 입력하세요.")

        else:
            last_results = find_best(bookmarks, raw)
            if not last_results:
                print("  ❌ 일치하는 북마크가 없습니다.")
            else:
                for i, bm in enumerate(last_results, 1):
                    _print_bm(bm, idx=i)
                print("\n  → open <번호>  으로 VS Code 에서 열 수 있습니다.")


# ─────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────
def main():
    bookmarks = scan_bookmarks()

    if not bookmarks:
        print("  ⚠  ◆BM◆ 마커가 하나도 발견되지 않았습니다.")
        print("  소스 파일에  # ◆BM◆ 태그 | 설명  형식으로 마커를 추가하세요.")
        return

    if len(sys.argv) >= 2:
        cmd = sys.argv[1].lower()
        if cmd == "list":
            _print_list(bookmarks)
        elif cmd == "find" and len(sys.argv) >= 3:
            query = " ".join(sys.argv[2:])
            results = find_best(bookmarks, query)
            if not results:
                print("  ❌ 일치하는 북마크가 없습니다.")
            else:
                for bm in results:
                    _print_bm(bm)
        else:
            print(__doc__)
    else:
        _interactive(bookmarks)


if __name__ == "__main__":
    main()
