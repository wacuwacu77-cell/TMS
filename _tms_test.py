"""TMS _tms_auto_sync + resolve() 테스트"""
import sys, time
from unittest.mock import MagicMock

# tkinter 계열 전부 mock
for mod in [
    'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox',
    'tkinterdnd2', 'winsound', 'numpy', 'pandas', 'openpyxl',
    'openpyxl.styles', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont'
]:
    sys.modules[mod] = MagicMock()

import importlib.util
spec = importlib.util.spec_from_file_location('aa', 'analysis_app.py')
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except Exception as e:
    import traceback
    print(f'Import error: {type(e).__name__}: {e}')
    traceback.print_exc()
    sys.exit(1)

time.sleep(1.0)  # daemon thread 대기

print(f'Import OK')
print(f'TAG_MAP entries: {len(module.TAG_MAP)}')

# ◆BM◆ 마커 스캔
scanned = module._tms_scan_bm_markers()
print(f'\n스캔된 BM 마커: {len(scanned)}개')
for info in scanned[:5]:
    ln = info.get('line', '?')
    bm = info.get('bm', '?')
    desc = info.get('desc_inline', '')[:40]
    print(f'  {bm}: line={ln}, desc={desc}')

# TAG_MAP에서 line 필드 확인
print('\nTAG_MAP line 필드 샘플:')
for tag, info in list(module.TAG_MAP.items())[:5]:
    ln = info.get('line', 'NONE')
    bm = info.get('bm', '?')
    print(f'  {tag}: bm={bm}, line={ln}')

# resolve() 테스트 (score 포함 — resolved dict에 없으니 direct 계산)
print('\nresolve() 정확도 테스트:')

# 기대값: (쿼리, 예상 태그)
test_cases = [
    ('예측엔진',      '§CORE:ENGINE'),
    ('엑셀저장',      '§IO:EXCEL'),
    ('편향보정',      '§CORE:BIAS'),
    ('배송완료토글',  '§FILTER:DELIVERED'),
    ('주간계획팝업',  '§POPUP:WEEKLY'),
    ('설정팝업',      '§POPUP:SETTINGS'),
    ('이력차트',      '§POPUP:DETAIL:GRAPH'),
    ('메모저장',      '§POPUP:DETAIL:MEMO'),
    ('소진캘린더',    '§POPUP:CALENDAR'),
    ('사양가편집',    '§POPUP:FARM:EDIT'),
    ('인쇄미리보기',  '§IO:PRINT'),
    ('트리뷰생성',    '§RENDER:TREE'),
    ('드래그선택',    '§FILTER:DRAG'),
    ('배송리포트',    '§POPUP:DELIVERY'),
    ('토스트알림',    '§GUARD:TOAST'),
    ('차번배송현황',  '§POPUP:TRUCK'),
]
ok = 0
for q, expected in test_cases:
    results = module.resolve(q, top=3)
    tags = [r['tag'] for r in results]
    hit = expected in tags
    rank = tags.index(expected) + 1 if hit else -1
    ln = results[0]['line'] if results else '?'
    status = 'OK' if (hit and rank == 1) else (f'Top{rank}' if hit else 'MISS')
    first_tag = results[0]['tag'] if results else '(없음)'
    if hit and rank == 1:
        ok += 1
    print(f'  [{status}] "{q}" -> {first_tag} (line={ln})  expected={expected}')

print(f'\n정확도: {ok}/{len(test_cases)} ({ok/len(test_cases)*100:.0f}%)')

