"""
_tms_watch.py — TMS 마스터 자동 전파 감시 데몬

실행:  python _tms_watch.py
종료:  Ctrl+C

마스터(kakao_sender/tagmap_kit/TAG_MAP.py)가 저장될 때마다
_tms_propagate.py 를 자동 실행해 3개 타겟에 반영한다.

  타겟 1: kakao_sender/TAG_MAP.py
  타겟 2: analysis_app.py
  타겟 3: qt_migration/analysis_app_qt.py
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT   = Path(__file__).parent
MASTER = ROOT / "kakao_sender" / "tagmap_kit" / "TAG_MAP.py"
PROP   = ROOT / "_tms_propagate.py"
POLL   = 2  # 감시 간격 (초)


def _run_propagate() -> bool:
    result = subprocess.run(
        [sys.executable, str(PROP)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        encoding="utf-8",
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}", flush=True)
    return result.returncode == 0


def main() -> None:
    if not MASTER.exists():
        print(f"[ERROR] 마스터 파일 없음: {MASTER}")
        sys.exit(1)

    print("=" * 58)
    print("TMS Watch — 마스터 변경 자동 전파")
    print(f"  감시 대상: {MASTER.relative_to(ROOT)}")
    print(f"  폴링 간격: {POLL}초")
    print(f"  종료: Ctrl+C")
    print("=" * 58)

    last_mtime = MASTER.stat().st_mtime

    try:
        while True:
            time.sleep(POLL)
            try:
                mtime = MASTER.stat().st_mtime
            except FileNotFoundError:
                continue

            if mtime != last_mtime:
                last_mtime = mtime
                ts = time.strftime("%H:%M:%S")
                print(f"\n[{ts}] 변경 감지 → 전파 시작...")
                ok = _run_propagate()
                print(f"[{ts}] {'완료 ✓' if ok else '오류 ✗'}\n", flush=True)

    except KeyboardInterrupt:
        print("\n[TMS Watch] 종료")


if __name__ == "__main__":
    main()
