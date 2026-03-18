"""TMS 테스트 스크립트"""
import shutil

S = '\u00a7'  # § 섹션 기호
BM = '\u25c6BM\u25c6'  # ◆BM◆

with open('analysis_app.py', 'r', encoding='utf-8-sig') as f:
    content = f.read()

# 삽입 정의: (§태그_줄_접두사, 들여쓰기, BM태그, 설명)
# 접두사는 해당 줄의 시작부터 §TAG까지. 줄 끝 \n 포함시 exact match, 없으면 pattern match.
inserts = [
    # indent=0 (최상위)
    (f'# {S}SYS:CONFIG ',      '', 'SYS_CONFIG',           '설정 저장/복원 (_load_ui_state, _save_settings)'),
    (f'# {S}CORE:BIAS ',       '', 'CORE_BIAS',            '예측 편향 보정 (bias / 적중률 / 오차 누적)'),
    (f'# {S}POPUP:CALENDAR:WIDGET ', '', 'POPUP_CALENDAR_WIDGET', '날짜 선택 공통 달력 위젯'),
    (f'# {S}CORE:ENGINE\n',    '', 'CORE_ENGINE',          '사료 주문 예측 엔진 (process_file)'),
    (f'# {S}IO:EXCEL\n',       '', 'IO_EXCEL',             '엑셀 저장 (save_to_excel)'),
    (f'# {S}POPUP:CREDIT\n',   '', 'POPUP_CREDIT',         '개발자 정보 / 알고리즘 설명 팝업'),
    (f'# {S}UI:MAIN\n',        '', 'UI_MAIN',              '메인 창 (launch_gui) / 버튼바 / 드래그앤드롭'),
    # indent=4 (launch_gui 내부)
    (f'    # {S}GUARD:FLASH\n',     '    ', 'GUARD_FLASH',    '팝업 외부클릭 경고 / 깜빡임'),
    (f'    # {S}GUARD:POPUP\n',     '    ', 'GUARD_POPUP',    '팝업 중복 방지 / 포커스 이동'),
    (f'    # {S}GUARD:TOAST\n',     '    ', 'GUARD_TOAST',    '경고 토스트 알림 (_show_toast)'),
    (f'    # {S}GUARD:RB_TOAST\n',  '    ', 'GUARD_RB_TOAST', '우측 하단 비침습 알림'),
    (f'    # {S}FILTER:SORT ',      '    ', 'FILTER_SORT',    '컬럼 정렬 (sortby)'),
    (f'    # {S}RENDER ',           '    ', 'RENDER',         '결과 테이블 렌더 컨테이너 전체'),
    (f'    # {S}POPUP:SETTINGS\n',  '    ', 'POPUP_SETTINGS', '설정 팝업 (화이트리스트 · 블랙리스트 · 컬럼)'),
    (f'    # {S}POPUP:FARM\n',      '    ', 'POPUP_FARM',     '사양가현황 팝업 전체'),
    (f'    # {S}CORE:FILE_LOAD ',   '    ', 'CORE_FILE_LOAD', '파일 분석 시작 / 백그라운드 스레드'),
    (f'    # {S}CORE:QUEUE ',       '    ', 'CORE_QUEUE',     '백그라운드 워커 큐 처리 / 진행률'),
    # indent=8 (render_table 내부)
    (f'        # {S}IO:UTILS ',         '        ', 'IO_UTILS',         '이미지 저장/렌더 공통 헬퍼'),
    (f'        # {S}POPUP:CALENDAR ',   '        ', 'POPUP_CALENDAR',   '소진 캘린더 팝업'),
    (f'        # {S}POPUP:WEEKLY ',     '        ', 'POPUP_WEEKLY',     '주간계획 팝업'),
    (f'        # {S}FILTER:LEGEND ',    '        ', 'FILTER_LEGEND',    '범례 필터 (배경색 / 글자색 토글)'),
    (f'        # {S}RENDER:TREE\n',     '        ', 'RENDER_TREE',      'Treeview 생성 / 컬럼 설정 / 행 색상'),
    (f'        # {S}FILTER:DRAG ',      '        ', 'FILTER_DRAG',      '드래그 다중 선택'),
    (f'        # {S}FILTER:DELIVERED ', '        ', 'FILTER_DELIVERED', '배송완료 토글'),
    (f'        # {S}FILTER:MAIN\n',     '        ', 'FILTER_MAIN',      '실시간 필터 (_apply_filter_impl)'),
    (f'        # {S}FILTER:CARD ',      '        ', 'FILTER_CARD',      '요약 카드 필터 (음수재고 / 급등 / 참고)'),
    (f'        # {S}POPUP:DETAIL\n',    '        ', 'POPUP_DETAIL',     '상세이력 팝업 전체'),
    (f'        # {S}IO:IMAGE ',         '        ', 'IO_IMAGE',         '결과 이미지 빌드 (_build_result_image)'),
    (f'        # {S}IO:SAVE ',          '        ', 'IO_SAVE',          '이미지 파일 저장 (save_result_image)'),
    (f'        # {S}IO:PRINT ',         '        ', 'IO_PRINT',         '인쇄 미리보기 (print_result_image)'),
    (f'        # {S}POPUP:DELIVERY ',   '        ', 'POPUP_DELIVERY',   '배송 리포트 팝업 (날짜범위·7탭·엑셀 내보내기)'),
    (f'        # {S}POPUP:TRUCK\n',     '        ', 'POPUP_TRUCK',      '배송현황 팝업'),
    (f'        # {S}POPUP:FARM:EDIT\n', '        ', 'POPUP_FARM_EDIT',  '사양가현황 인라인 셀 편집'),
    (f'        # {S}POPUP:FARM:SAVE\n', '        ', 'POPUP_FARM_SAVE',  '사양가현황 전체 저장'),
    # indent=12 (show_detail_popup 내부)
    (f'            # {S}POPUP:DETAIL:MEMO\n',  '            ', 'POPUP_DETAIL_MEMO',  '상세이력 메모 저장'),
    (f'            # {S}POPUP:DETAIL:TABLE\n', '            ', 'POPUP_DETAIL_TABLE', '상세이력 테이블'),
    (f'            # {S}POPUP:DETAIL:GRAPH\n', '            ', 'POPUP_DETAIL_GRAPH', '상세이력 그래프'),
]

new_content = content
replaced = 0
skipped = 0
missed = []

for (prefix, indent, bm_tag, desc) in inserts:
    marker_line = f'{indent}# {BM} {bm_tag} | {desc}\n'
    
    # 이미 삽입됐으면 스킵
    if marker_line in new_content:
        skipped += 1
        continue
    
    # prefix가 줄 끝(\n)을 포함하면 exact replacement
    if prefix.endswith('\n'):
        if prefix in new_content:
            new_content = new_content.replace(prefix, prefix + marker_line, 1)
            replaced += 1
        else:
            missed.append(bm_tag)
    else:
        # prefix 다음에 나오는 줄 끝까지를 찾아서 그 뒤에 삽입
        import re as _re
        escaped = _re.escape(prefix)
        pat = escaped + r'[^\n]*\n'
        m = _re.search(pat, new_content)
        if m:
            original = m.group(0)
            new_content = new_content.replace(original, original + marker_line, 1)
            replaced += 1
        else:
            missed.append(bm_tag)

print(f'삽입: {replaced}개, 스킵(이미있음): {skipped}개, 실패: {len(missed)}개')
if missed:
    print(f'실패 목록: {missed}')

if replaced > 0:
    shutil.copy('analysis_app.py', 'analysis_app.py.bak_bm')
    with open('analysis_app.py', 'w', encoding='utf-8-sig') as f:
        f.write(new_content)
    new_lines = new_content.count('\n') + 1
    print(f'저장 완료: {new_lines}줄')
else:
    print('변경 없음 — 파일 저장 안 함')

