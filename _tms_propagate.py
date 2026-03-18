#!/usr/bin/env python3
"""
_tms_propagate.py — TMS 코어 알고리즘 전파 스크립트
══════════════════════════════════════════════════════

tagmap_kit/TAG_MAP.py (마스터)의 §SYNC 블록을
kakao_sender/TAG_MAP.py 와 analysis_app.py 에 자동 반영합니다.

동기화 블록:
  §SYNC:UTIL_FNS      — _tokenize + _nospace 유틸 함수 (순수 알고리즘)
  §SYNC:RESOLVE_LOOP  — resolve() 내부 채점 for 루프 (핵심 알고리즘)

사용법:
  python _tms_propagate.py           # 실제 반영
  python _tms_propagate.py --dry-run # 변경 미리보기 (파일 수정 없음)
  python _tms_propagate.py --check   # 동기화 상태만 확인

새 동기화 블록 추가 방법:
  1. tagmap_kit/TAG_MAP.py 에 마커 삽입:
         # §SYNC:NEWBLOCK:BEGIN
         ... (알고리즘 코드) ...
         # §SYNC:NEWBLOCK:END  (들여쓰기 무관)
  2. kakao_sender/TAG_MAP.py, analysis_app.py 에도 동일 마커 삽입
  3. 아래 SYNC_BLOCKS 리스트에 항목 추가
"""

import sys
from pathlib import Path

ROOT        = Path(__file__).parent
MASTER      = ROOT / "kakao_sender" / "tagmap_kit" / "TAG_MAP.py"
TARGET_KK   = ROOT / "kakao_sender" / "TAG_MAP.py"
TARGET_APP  = ROOT / "analysis_app.py"
TARGET_QT   = ROOT / "qt_migration" / "analysis_app_qt.py"

DRY_RUN = "--dry-run" in sys.argv or "--check" in sys.argv
CHECK   = "--check" in sys.argv


# ─────────────────────────────────────────────────────────────────────
# 이름 변환 테이블
# ─────────────────────────────────────────────────────────────────────

# kakao_sender: 마스터와 동일 이름 체계 → 변환 없음
RENAME_KK = None

# analysis_app / analysis_app_qt: 내장형(_tms_ 접두사) 변환
RENAME_APP_UTIL_FNS = {
    # 함수 선언
    "def _tokenize(":  "def _tms_tokenize(",
    "def _nospace(":   "def _tms_nospace(",
    # re 모듈 호출 (embedded에서는 _tms_re로 임포트됨)
    "re.split(":       "_tms_re.split(",
    "re.sub(":         "_tms_re.sub(",
}

RENAME_APP_RESOLVE_LOOP = {
    # 캐시 접근 방식 변환 (internal에서는 .get() + None guard 사용)
    "pc = _PCACHE[tag]":  "pc = _TMS_PCACHE.get(tag)\n        if not pc:\n            continue",
    # nospace 함수 호출
    "_nospace(qt)":        "_tms_nospace(qt)",
}


# ─────────────────────────────────────────────────────────────────────
# 동기화 블록 목록: (블록명, kakao_sender변환, analysis_app변환, qt변환)
# qt는 이미 _tms_ 접두사 사용 → analysis_app와 동일한 변환 적용
# ─────────────────────────────────────────────────────────────────────
SYNC_BLOCKS = [
    # (블록명, TARGET_KK 변환, TARGET_APP 변환, TARGET_QT 변환)
    ("UTIL_FNS",     RENAME_KK, RENAME_APP_UTIL_FNS,     RENAME_APP_UTIL_FNS),
    ("RESOLVE_LOOP", RENAME_KK, RENAME_APP_RESOLVE_LOOP,  RENAME_APP_RESOLVE_LOOP),
]


# ─────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────

def _extract_block(src: str, block_name: str) -> str | None:
    """§SYNC:BLOCK_NAME:BEGIN ~ END 사이 내용 추출 (들여쓰기 무관)."""
    begin_tag = f"# §SYNC:{block_name}:BEGIN"
    end_tag   = f"# §SYNC:{block_name}:END"
    if begin_tag not in src or end_tag not in src:
        return None
    # BEGIN 마커 다음 줄부터
    s = src.index(begin_tag) + len(begin_tag)
    if s < len(src) and src[s] == "\n":
        s += 1
    # END 마커 줄 시작으로
    e_pos = src.index(end_tag)
    e = e_pos
    while e > 0 and src[e - 1] != "\n":
        e -= 1
    return src[s:e]


def _replace_block(src: str, block_name: str, new_content: str) -> str:
    """§SYNC:BLOCK_NAME:BEGIN ~ END 사이를 new_content로 교체."""
    begin_tag = f"# §SYNC:{block_name}:BEGIN"
    end_tag   = f"# §SYNC:{block_name}:END"
    if begin_tag not in src or end_tag not in src:
        return src
    s = src.index(begin_tag) + len(begin_tag)
    if s < len(src) and src[s] == "\n":
        s += 1
    e_pos = src.index(end_tag)
    e = e_pos
    while e > 0 and src[e - 1] != "\n":
        e -= 1
    return src[:s] + new_content + src[e:]


def _apply_rename(code: str, rename: dict | None) -> str:
    if not rename:
        return code
    for old, new in rename.items():
        code = code.replace(old, new)
    return code


def _diff_summary(a: str, b: str) -> str:
    """변경된 줄 수 요약 반환."""
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    changed = sum(1 for x, y in zip(a_lines, b_lines) if x != y)
    added   = max(0, len(b_lines) - len(a_lines))
    removed = max(0, len(a_lines) - len(b_lines))
    parts = []
    if changed:
        parts.append(f"~{changed}줄")
    if added:
        parts.append(f"+{added}줄")
    if removed:
        parts.append(f"-{removed}줄")
    return ", ".join(parts) if parts else "변경 없음"


# ─────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 58)
    print("TMS 코어 전파 스크립트")
    print(f"  마스터  : {MASTER.relative_to(ROOT)}")
    print(f"  타겟 1  : {TARGET_KK.relative_to(ROOT)}")
    print(f"  타겟 2  : {TARGET_APP.relative_to(ROOT)}")
    print(f"  타겟 3  : {TARGET_QT.relative_to(ROOT)}")
    if DRY_RUN:
        mode = "CHECK" if CHECK else "DRY-RUN"
        print(f"  모드    : [{mode}]  파일을 수정하지 않습니다")
    print("=" * 58)

    for path in (MASTER, TARGET_KK, TARGET_APP, TARGET_QT):
        if not path.exists():
            print(f"[ERROR] 파일 없음: {path}")
            return 1

    master_src = MASTER.read_text("utf-8")
    kk_src     = TARGET_KK.read_text("utf-8")
    app_src    = TARGET_APP.read_text("utf-8")
    qt_src     = TARGET_QT.read_text("utf-8")

    kk_changed  = False
    app_changed = False
    qt_changed  = False
    any_diff    = False

    for block_name, rename_kk, rename_app, rename_qt in SYNC_BLOCKS:
        print(f"\n── §SYNC:{block_name} ──")

        master_block = _extract_block(master_src, block_name)
        if master_block is None:
            print(f"  [SKIP] 마스터에 §SYNC:{block_name} 마커 없음")
            continue

        # ── kakao_sender ──────────────────────────────────────────
        kk_target = _apply_rename(master_block, rename_kk)
        kk_cur    = _extract_block(kk_src, block_name)
        if kk_cur is None:
            print(f"  [WARN] kakao_sender 에 §SYNC:{block_name} 마커 없음 → 건너뜀")
        elif kk_cur == kk_target:
            print(f"  [OK]   kakao_sender — 이미 최신")
        else:
            diff = _diff_summary(kk_cur, kk_target)
            if DRY_RUN:
                print(f"  [DIFF] kakao_sender — {diff} 변경 예정")
            else:
                kk_src = _replace_block(kk_src, block_name, kk_target)
                kk_changed = True
                print(f"  [✓]   kakao_sender — 업데이트 ({diff})")
            any_diff = True

        # ── analysis_app ──────────────────────────────────────────
        app_target = _apply_rename(master_block, rename_app)
        app_cur    = _extract_block(app_src, block_name)
        if app_cur is None:
            print(f"  [WARN] analysis_app 에 §SYNC:{block_name} 마커 없음 → 건너뜀")
        elif app_cur == app_target:
            print(f"  [OK]   analysis_app — 이미 최신")
        else:
            diff = _diff_summary(app_cur, app_target)
            if DRY_RUN:
                print(f"  [DIFF] analysis_app — {diff} 변경 예정")
            else:
                app_src = _replace_block(app_src, block_name, app_target)
                app_changed = True
                print(f"  [✓]   analysis_app — 업데이트 ({diff})")
            any_diff = True

        # ── analysis_app_qt ───────────────────────────────────────
        qt_target = _apply_rename(master_block, rename_qt)
        qt_cur    = _extract_block(qt_src, block_name)
        if qt_cur is None:
            print(f"  [WARN] analysis_app_qt 에 §SYNC:{block_name} 마커 없음 → 건너뜀")
        elif qt_cur == qt_target:
            print(f"  [OK]   analysis_app_qt — 이미 최신")
        else:
            diff = _diff_summary(qt_cur, qt_target)
            if DRY_RUN:
                print(f"  [DIFF] analysis_app_qt — {diff} 변경 예정")
            else:
                qt_src = _replace_block(qt_src, block_name, qt_target)
                qt_changed = True
                print(f"  [✓]   analysis_app_qt — 업데이트 ({diff})")
            any_diff = True

    # ── 파일 저장 ─────────────────────────────────────────────────
    print()
    if not DRY_RUN:
        saved = []
        if kk_changed:
            TARGET_KK.write_text(kk_src, "utf-8")
            saved.append(TARGET_KK.name)
        if app_changed:
            TARGET_APP.write_text(app_src, "utf-8")
            saved.append(TARGET_APP.name)
        if qt_changed:
            TARGET_QT.write_text(qt_src, "utf-8")
            saved.append(TARGET_QT.name)
        if saved:
            print(f"[SAVED] {', '.join(saved)}")
        else:
            print("모든 블록이 최신 상태입니다.")
    elif any_diff:
        print("실제 반영하려면:  python _tms_propagate.py")
    else:
        print("모든 블록이 최신 상태입니다.")

    print("완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
