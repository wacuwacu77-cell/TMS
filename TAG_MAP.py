"""
TAG_MAP.py — 계층형 코드 태그 맵 (AI 컨텍스트 내비게이션)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

§계층:카테고리:기능  형식의 태그를 자연어 키워드와 매핑합니다.
AI에게 "로그인 로직 수정해줘" → §AUTH:LOGIN 라인으로 바로 이동합니다.

사용법:
  사람 → "회원가입 처리 부분 고쳐줘"
  AI   →  TAG_MAP에서 §AUTH:REGISTER 매칭 → src/auth.py:42 직행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[이식 체크리스트]
  1. 아래 TAG_MAP = {} 은 처음엔 비워두세요.
     소스에 ◆BM◆ 마커를 추가 후 import TAG_MAP 하면 자동으로 채워집니다.
  2. _FILE_PREFIX 를 현재 프로젝트 구조에 맞게 수정하세요.
     (미등록 파일은 _derive_prefix() 가 경로에서 자동 유추합니다)
  3. _SYNONYM_MAP 에 프로젝트 도메인 동의어를 추가하세요.
     예) 쇼핑몰: "장바구니" → "카트", "결제" → "구매"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# §META:TAGMAP:BEGIN
TAG_MAP = {}
# §META:TAGMAP:END


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 자연어 → 태그 매칭 엔진  (수정 불필요)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import re
from pathlib import Path

_ROOT = Path(__file__).parent
_MARKER_RE = re.compile(r"#\s*◆BM◆\s+(\S+)\s*\|\s*(.+)")

# ── BM 설명 캐시 {상대경로: {bm_tag: 설명문}} ─────────────
_DESC_CACHE: dict[str, dict[str, str]] = {}


def _get_bm_desc(rel_path: str, bm_tag: str) -> str:
    """소스 파일에서 ◆BM◆ 마커의 설명 텍스트를 반환 (파일당 1회 캐시)."""
    if rel_path not in _DESC_CACHE:
        _DESC_CACHE[rel_path] = {}
        fpath = _ROOT / rel_path
        if fpath.exists():
            for line in fpath.read_text("utf-8", errors="ignore").splitlines():
                m = _MARKER_RE.search(line)
                if m:
                    _DESC_CACHE[rel_path][m.group(1)] = m.group(2).strip()
    return _DESC_CACHE.get(rel_path, {}).get(bm_tag, "")


# §SYNC:UTIL_FNS:BEGIN
def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[\s_,|·§:/\-\(\)]+", text.lower()) if len(t) >= 2}


def _nospace(text: str) -> str:
    """공백·구분자를 모두 제거한 소문자 문자열 반환 (붙여쓰기 매칭용)."""
    return re.sub(r"[\s_\-]+", "", text.lower())
# §SYNC:UTIL_FNS:END


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [수정 필요] 프로젝트 도메인 동의어 사전
# 키: 사용자가 쓸 표현 / 값: 코드·BM에서 사용하는 표현
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SYNONYM_MAP: dict[str, str] = {
    # 예시 — 필요 없는 항목은 삭제하고 프로젝트에 맞게 추가
    "실행":   "시작",
    "조회":   "불러오기",
    "등록":   "추가",
    "제거":   "삭제",
    "보내기": "전송",
}


def _expand_query(q: str) -> str:
    """시소러스로 쿼리 토큰에 동의어 추가 (붙여쓴 복합어도 처리)."""
    tokens = _tokenize(q)
    extras = [_SYNONYM_MAP[t] for t in tokens if t in _SYNONYM_MAP]
    expanded = (q + " " + " ".join(extras)).strip() if extras else q
    q_ns = _nospace(q)
    for src_kw, dst_kw in _SYNONYM_MAP.items():
        src_ns = _nospace(src_kw)
        if len(src_ns) >= 2 and src_ns in q_ns:
            expanded = expanded + " " + q_ns.replace(src_ns, _nospace(dst_kw))
    return expanded.strip()


# ── 태그별 사전 계산 캐시 ────────────────────────────────────
_PCACHE: dict[str, dict] = {}


def _build_pcache() -> None:
    """모든 태그의 토큰/nospace를 1회만 계산해서 캐시."""
    for tag, info in TAG_MAP.items():
        bm = info["bm"]
        desc = _get_bm_desc(info["file"], bm)
        kw_text = " ".join(info["keywords"])
        _PCACHE[tag] = {
            "bm_lower":    bm.lower(),
            "tag_lower":   tag.lower(),
            "bm_ns":       _nospace(bm),
            "tag_ns":      _nospace(tag),
            "bm_tokens":   _tokenize(bm + " " + tag),
            "kw_text":     kw_text.lower(),
            "kw_ns":       _nospace(kw_text),
            "kw_tokens":   _tokenize(kw_text),
            "kw_list_ns":  [_nospace(k) for k in info["keywords"]],
            "desc":        desc.lower(),
            "desc_ns":     _nospace(desc),
            "desc_tokens": _tokenize(desc),
        }


# ── resolve 결과 캐시 ─────────────────────────────────────────
_RESOLVE_CACHE: dict[str, list] = {}


def resolve(query: str, top: int = 5) -> list[dict]:
    """
    자연어 쿼리로 TAG_MAP에서 매칭되는 태그를 찾고
    실제 파일에서 ◆BM◆ 마커 위치(라인 번호)까지 반환합니다.

    띄어쓰기 유무와 관계없이 매칭됩니다.
    예) "사용자목록" == "사용자 목록", "로그인처리" == "로그인 처리"

    Returns: [{"tag": "§AUTH:LOGIN", "file": "...", "line": 42, "bm": "...", "keywords": [...]}, ...]
    """
    cache_key = f"{query.strip().lower()}|{top}"
    if cache_key in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[cache_key]

    if not _PCACHE:
        _build_pcache()

    q = _expand_query(query.strip().lower())
    q_tokens = _tokenize(q)
    q_ns = _nospace(q)
    scored = []

    # §SYNC:RESOLVE_LOOP:BEGIN
    for tag, info in TAG_MAP.items():
        score = 0.0
        pc = _PCACHE[tag]
        bm_tag    = pc["bm_lower"]
        tag_lower = pc["tag_lower"]
        kw_text   = pc["kw_text"]

        if q in tag_lower or tag_lower in q:
            score += 200
        if q in bm_tag or bm_tag in q:
            score += 150
        if q in kw_text:
            score += 100

        all_tokens = pc["bm_tokens"] | pc["kw_tokens"]
        overlap = q_tokens & all_tokens
        score += len(overlap) * 30

        for qt in q_tokens:
            if qt in kw_text or qt in bm_tag:
                score += 15

        if q_ns and (q_ns in pc["bm_ns"] or pc["bm_ns"] in q_ns):
            score += 120
        if q_ns and (q_ns in pc["tag_ns"] or pc["tag_ns"] in q_ns):
            score += 160
        if q_ns and q_ns in pc["kw_ns"]:
            score += 80
        if q_ns:
            for kw_kns in pc["kw_list_ns"]:
                if q_ns in kw_kns or kw_kns in q_ns:
                    score += 60
                    break

        desc = pc["desc"]
        if desc:
            desc_overlap = q_tokens & pc["desc_tokens"]
            score += len(desc_overlap) * 25
            if q in desc:
                score += 90
            if q_ns and (q_ns in pc["desc_ns"] or pc["desc_ns"] in q_ns):
                score += 70
            for qt in q_tokens:
                if qt in desc:
                    score += 10
            for qt in q_tokens:
                qt_ns = _nospace(qt)
                matches = sum(1 for dt in pc["desc_tokens"] if len(dt) >= 2 and dt in qt_ns)
                score += matches * 12

        if score > 0:
            scored.append((score, tag, info))

    scored.sort(key=lambda x: -x[0])
    # §SYNC:RESOLVE_LOOP:END
    results = []
    for _, tag, info in scored[:top]:
        line = _find_bm_line(info["file"], info["bm"])
        results.append(
            {
                "tag": tag,
                "file": info["file"],
                "line": line,
                "bm": info["bm"],
                "keywords": info["keywords"],
            }
        )

    _RESOLVE_CACHE[cache_key] = results
    return results


def _find_bm_line(rel_path: str, bm_tag: str) -> int:
    """파일에서 ◆BM◆ <bm_tag> 마커의 라인 번호를 반환."""
    fpath = _ROOT / rel_path
    if not fpath.exists():
        return 0
    for i, line in enumerate(fpath.read_text("utf-8").splitlines(), 1):
        m = _MARKER_RE.search(line)
        if m and m.group(1) == bm_tag:
            return i
    return 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [수정 필요] 파일 → §카테고리 접두사 매핑
# 여기에 없는 파일은 _derive_prefix() 가 경로에서 자동 유추합니다.
# 예) core/sender.py → §CORE:SENDER (자동)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_FILE_PREFIX: dict[str, str] = {
    # 예시:
    # "main.py":             "APP",
    # "src/auth.py":         "AUTH",
    # "src/api/users.py":    "API:USERS",
}

_SKIP_FILES = {"TAG_MAP.py", "bm.py"}


def _derive_prefix(rel_path: str) -> str:
    """_FILE_PREFIX에 없는 파일의 §태그 접두사를 경로에서 자동 유추합니다.

    예) 'ui/main_window.py'   → 'UI:MAIN_WINDOW'
        'core/sender.py'      → 'CORE:SENDER'
        'main.py'             → 'MAIN'
    """
    from pathlib import PurePosixPath
    p = PurePosixPath(rel_path)
    stem = p.stem.upper().replace("-", "_")
    folder = p.parent.name
    if folder and folder != ".":
        return f"{folder.upper().replace('-', '_')}:{stem}"
    return stem


def _scan_bookmarks() -> list[dict]:
    """프로젝트 내 모든 .py 파일에서 ◆BM◆ 마커를 스캔합니다."""
    results = []
    for py in sorted(_ROOT.rglob("*.py")):
        if py.name in _SKIP_FILES or "__pycache__" in str(py):
            continue
        rel = py.relative_to(_ROOT).as_posix()
        try:
            lines = py.read_text("utf-8").splitlines()
        except Exception:
            continue
        for i, line_text in enumerate(lines, 1):
            m = _MARKER_RE.search(line_text)
            if m:
                results.append(
                    {
                        "file": rel,
                        "bm": m.group(1),
                        "desc": m.group(2).strip(),
                        "line": i,
                    }
                )
    return results


def _make_keywords(desc: str) -> list[str]:
    """BM 설명 텍스트에서 키워드 리스트를 자동 생성합니다."""
    stopwords = {"및", "의", "을", "를", "에", "에서", "로", "으로", "후", "시"}
    words = re.split(r"[,\s/·|()\[\]—\-]+", desc)
    return [w for w in words if len(w) >= 2 and w not in stopwords]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 지속화 (TAG_MAP.py 소스 + copilot-instructions.md 갱신)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _persist_tag_map() -> bool:
    """현재 메모리 TAG_MAP을 TAG_MAP.py 소스의 BEGIN~END 영역에 덮어씁니다."""
    import pprint as _pp

    src_path = Path(__file__)
    try:
        src = src_path.read_text(encoding="utf-8")
    except Exception:
        return False
    _S = "# §META:TAGMAP:BEGIN"
    _E = "# §META:TAGMAP:END"
    if _S not in src or _E not in src:
        return False
    file_order = list(dict.fromkeys(v["file"] for v in TAG_MAP.values()))
    by_file: dict = {f: [] for f in file_order}
    for tag, info in TAG_MAP.items():
        by_file.setdefault(info["file"], []).append((tag, info))
    _DIVIDER = "    # " + "━" * 50
    lines = [_S, "TAG_MAP = {"]
    for fpath, entries in by_file.items():
        if not entries:
            continue
        lines.append(_DIVIDER)
        lines.append(f"    # --- {fpath}")
        lines.append(_DIVIDER)
        for tag, info in entries:
            kw = _pp.pformat(info["keywords"], width=120, compact=True)
            auto = "  # [AUTO]" if info.get("_auto") else ""
            lines.append(f"    {tag!r}: {{")
            lines.append(f'        "file": {info["file"]!r},')
            lines.append(f'        "bm": {info["bm"]!r},{auto}')
            lines.append(f'        "keywords": {kw},')
            lines.append("    },")
    lines.append("}")
    lines.append(_E)
    new_block = "\n".join(lines)
    s = src.index(_S)
    e = src.index(_E) + len(_E)
    new_src = src[:s] + new_block + src[e:]
    try:
        src_path.write_text(new_src, encoding="utf-8")
        return True
    except Exception:
        return False


def _persist_instructions() -> bool:
    """copilot-instructions.md 내 BM 인덱스 테이블을 현재 TAG_MAP 기준으로 재생성합니다.
    파일이 없으면 프로젝트 이름을 제목으로 자동 생성합니다."""
    inst_path = Path(__file__).parent / ".github" / "copilot-instructions.md"
    _S = "<!-- §META:BM_INDEX:BEGIN -->"
    _E = "<!-- §META:BM_INDEX:END -->"
    if not inst_path.exists():
        inst_path.parent.mkdir(parents=True, exist_ok=True)
        project_name = Path(__file__).parent.name
        template = (
            f"# {project_name} — AI 탐색 지침\n\n"
            "## 탐색 규칙 (필독)\n"
            "코드를 수정하기 전에 반드시 아래 순서를 따를 것:\n"
            "1. **파일 전체를 읽지 말 것.** 아래 BM 인덱스에서 관련 섹션을 찾는다.\n"
            '2. `grep_search("◆BM◆ {BM태그}", file)` 로 정확한 라인 번호를 찾는다.\n'
            "3. 해당 라인 ±30줄만 `read_file`로 읽어 컨텍스트를 파악한다.\n"
            "4. 수정 후 `get_errors`로 오류 확인.\n\n"
            "---\n\n"
            "## BM 인덱스 — 파일별 북마크 태그\n\n"
            f"{_S}\n{_E}\n"
        )
        try:
            inst_path.write_text(template, encoding="utf-8")
        except Exception:
            return False
    try:
        inst = inst_path.read_text(encoding="utf-8")
    except Exception:
        return False
    if _S not in inst or _E not in inst:
        return False
    file_order = list(dict.fromkeys(v["file"] for v in TAG_MAP.values()))
    by_file: dict = {f: [] for f in file_order}
    for tag, info in TAG_MAP.items():
        by_file.setdefault(info["file"], []).append((tag, info))
    table_lines = [_S]
    for fpath, entries in by_file.items():
        if not entries:
            continue
        table_lines.append(f"\n### {fpath}")
        table_lines.append("| BM태그 | 설명 |")
        table_lines.append("|--------|------|")
        for tag, info in entries:
            auto = " [AUTO]" if info.get("_auto") else ""
            table_lines.append(f"| {info['bm']} | {tag}{auto} |")
    table_lines.append("\n" + _E)
    new_block = "\n".join(table_lines)
    s = inst.index(_S)
    e = inst.index(_E) + len(_E)
    new_inst = inst[:s] + new_block + inst[e:]
    try:
        inst_path.write_text(new_inst, encoding="utf-8")
        return True
    except Exception:
        return False


def bm_register(
    tag: str, file: str, bm: str, desc: str, keywords: list | None = None
) -> None:
    """새 BM 태그를 TAG_MAP에 등록하고 TAG_MAP.py + copilot-instructions.md를 동시 갱신합니다."""
    kws = keywords if keywords else _make_keywords(desc)
    if tag not in TAG_MAP:
        TAG_MAP[tag] = {"file": file, "bm": bm, "keywords": kws}
    else:
        existing = TAG_MAP[tag]
        existing["file"] = file
        existing["bm"] = bm
        for kw in kws:
            if kw not in existing["keywords"]:
                existing["keywords"].append(kw)
    _persist_tag_map()
    _persist_instructions()


def _auto_sync():
    """
    모듈 로드 시 자동 동기화:
    - 코드에 ◆BM◆가 있지만 TAG_MAP에 없는 항목 → 자동 등록
    - TAG_MAP에 있지만 코드에서 ◆BM◆가 삭제된 항목 → 자동 제거
    """
    code_bms = _scan_bookmarks()
    code_set = {(b["file"], b["bm"]) for b in code_bms}
    code_desc = {(b["file"], b["bm"]): b["desc"] for b in code_bms}
    map_set = {(info["file"], info["bm"]) for info in TAG_MAP.values()}

    new_bms = code_set - map_set
    for file, bm in sorted(new_bms):
        desc = code_desc.get((file, bm), "")
        prefix = _FILE_PREFIX.get(file, _derive_prefix(file))
        tag = f"§{prefix}:{bm}"
        keywords = _make_keywords(desc)
        TAG_MAP[tag] = {
            "file": file,
            "bm": bm,
            "keywords": keywords,
            "_auto": True,
        }

    stale_tags = [
        tag
        for tag, info in TAG_MAP.items()
        if (info["file"], info["bm"]) not in code_set
    ]
    for tag in stale_tags:
        del TAG_MAP[tag]

    if new_bms or stale_tags:
        _persist_tag_map()
        _persist_instructions()


def sync() -> dict:
    """
    동기화 상태를 상세 리포트로 반환합니다.

    Returns:
        {
            "new": [{"tag", "file", "bm", "desc"}, ...],
            "stale": [{"tag", "file", "bm"}, ...],
            "auto_count": int,
            "curated_count": int,
            "total_code": int,
            "total_map": int,
        }
    """
    code_bms = _scan_bookmarks()
    code_set = {(b["file"], b["bm"]) for b in code_bms}
    code_desc = {(b["file"], b["bm"]): b["desc"] for b in code_bms}
    map_set = {(info["file"], info["bm"]) for info in TAG_MAP.values()}

    new_bms = code_set - map_set
    stale_bms = map_set - code_set

    new_entries = []
    for file, bm in sorted(new_bms):
        desc = code_desc.get((file, bm), "")
        prefix = _FILE_PREFIX.get(file, _derive_prefix(file))
        new_entries.append({"tag": f"§{prefix}:{bm}", "file": file, "bm": bm, "desc": desc})

    stale_entries = []
    for tag, info in list(TAG_MAP.items()):
        if (info["file"], info["bm"]) in stale_bms:
            stale_entries.append({"tag": tag, "file": info["file"], "bm": info["bm"]})

    auto_count = sum(1 for v in TAG_MAP.values() if v.get("_auto"))
    curated_count = len(TAG_MAP) - auto_count

    return {
        "new": new_entries,
        "stale": stale_entries,
        "auto_count": auto_count,
        "curated_count": curated_count,
        "total_code": len(code_set),
        "total_map": len(TAG_MAP),
    }


# ── 모듈 로드 시 자동 동기화 실행 ──
_auto_sync()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 이식 검증 (python TAG_MAP.py --verify)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _verify() -> None:
    """TMS 이식 상태를 자가 진단하고 결과를 출력합니다.

    사용법:
        python TAG_MAP.py --verify
    """
    print("\n  ━━━ TMS 이식 검증 ━━━")
    ok = True

    # 1. ◆BM◆ 마커 스캔
    bms = _scan_bookmarks()
    if bms:
        print(f"  ✅ ◆BM◆ 마커: {len(bms)}개 발견")
        for b in bms[:3]:
            print(f"       {b['file']}:{b['line']}  [{b['bm']}]  {b['desc'][:40]}")
        if len(bms) > 3:
            print(f"       ... 외 {len(bms)-3}개")
    else:
        print("  ⚠️  ◆BM◆ 마커 없음 — 소스 파일에 마커를 추가하세요")
        ok = False

    # 2. TAG_MAP 상태
    if TAG_MAP:
        print(f"  ✅ TAG_MAP: {len(TAG_MAP)}개 엔트리")
    else:
        print("  ⚠️  TAG_MAP 비어있음 — import TAG_MAP 으로 auto_sync를 실행하세요")
        ok = False

    # 3. stale/new 체크
    rpt = sync()
    if rpt["new"]:
        print(f"  ⚠️  미등록 마커 {len(rpt['new'])}개: {[x['bm'] for x in rpt['new']]}")
        ok = False
    else:
        print(f"  ✅ 미등록 마커 없음")

    if rpt["stale"]:
        print(f"  ⚠️  삭제된 마커 {len(rpt['stale'])}개: {[x['bm'] for x in rpt['stale']]}")
        ok = False
    else:
        print(f"  ✅ stale 항목 없음")

    # 4. copilot-instructions.md 존재 확인
    inst_path = Path(__file__).parent / ".github" / "copilot-instructions.md"
    if inst_path.exists():
        print(f"  ✅ copilot-instructions.md 존재")
    else:
        print(f"  ⚠️  .github/copilot-instructions.md 없음 — import TAG_MAP 으로 생성하세요")
        ok = False

    # 5. resolve() 단순 테스트
    if TAG_MAP:
        test_q = list(TAG_MAP.values())[0].get("keywords", [""])[0]
        if test_q:
            results = resolve(test_q, top=1)
            if results and results[0]["line"] > 0:
                print(f"  ✅ resolve() 동작: '{test_q}' → {results[0]['tag']} (line={results[0]['line']})")
            else:
                print(f"  ⚠️  resolve() 라인 번호 반환 실패 — ◆BM◆ 마커와 TAG_MAP bm 값이 일치하는지 확인")
                ok = False

    # 최종 결과
    print()
    if ok:
        print("  ✅ 이식 검증 통과 — TMS가 정상 동작합니다.\n")
    else:
        print("  ❌ 이식 검증 실패 — 위 항목을 확인하세요.\n")


if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        _verify()
    else:
        print("사용법: python TAG_MAP.py --verify")
        print(f"현재 TAG_MAP: {len(TAG_MAP)}개 엔트리")
        s = sync()
        print(f"sync: new={len(s['new'])}, stale={len(s['stale'])}, total={s['total_map']}")
