"""CTA 노출·클릭 엑셀 보고서 생성"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "CTA_노출_클릭_정리.xlsx"
SHOTS = HERE / "shots"

FONT = "Arial"
BLUE = "1F6BFF"
HEAD_FILL = PatternFill("solid", fgColor="0F1E3D")
SUB_FILL = PatternFill("solid", fgColor="EAF1FF")
TEST_FILL = PatternFill("solid", fgColor="F3F4F6")
thin = Side(style="thin", color="D1D5DB")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

CTAS = [
    # position, 위치 설명, 버튼 문구, 노출 조건
    ("header", "상단 메뉴(고정 헤더)", "무료 가입", "페이지 열자마자 보임 · 모바일/데스크톱"),
    ("hero", "첫 화면", "무료 가입하고 무제한 확인하기", "페이지 열자마자 보임 · 모바일/데스크톱"),
    ("benefits", "혜택 2가지 소개 바로 아래", "무료 가입하고 두 혜택 받기", "혜택 영역까지 스크롤 시"),
    ("how", "시작 방법(3단계) 아래", "카카오로 1분 만에 시작하기", "시작 방법 영역까지 스크롤 시"),
    ("final", "페이지 맨 아래 마지막 영역", "무료 가입하고 무제한 확인하기", "끝까지 스크롤 시"),
    ("sticky", "모바일 하단 고정 버튼", "무료 가입 · 조건 확인 무제한 + 정책 연결", "모바일 전용 · 첫 화면 버튼이 사라진 뒤 표시"),
]

# Amplitude 프로젝트 890674 조회 결과 (2026-10-19 ~ 2026-10-26, 이벤트 총 횟수)
VIEWS = [
    ("2026-10-26", "header", "claude_test", 2), ("2026-10-26", "hero", "claude_test", 2),
    ("2026-10-26", "benefits", "claude_test", 2), ("2026-10-26", "how", "claude_test", 2),
    ("2026-10-26", "final", "claude_test", 2), ("2026-10-26", "sticky", "claude_test", 1),
    ("2026-10-26", "header", "(none)", 1), ("2026-10-26", "hero", "(none)", 1),
]
CLICKS = [
    ("2026-10-26", "header", "claude_test", 1), ("2026-10-26", "hero", "claude_test", 1),
    ("2026-10-26", "benefits", "claude_test", 1), ("2026-10-26", "final", "claude_test", 2),
    ("2026-10-26", "sticky", "claude_test", 1), ("2026-10-26", "hero", "(none)", 1),
]
SOURCE = "출처: Amplitude 프로젝트 890674, 이벤트 총 횟수(Event Totals), 2026-10-19~2026-10-26 조회 (2026-10-26)"


def font(**kw):
    return Font(name=FONT, **kw)


def style_header(ws, row, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = font(bold=True, color="FFFFFF")
        cell.fill = HEAD_FILL
        cell.alignment = CENTER
        cell.border = BORDER


def raw_sheet(wb, title, event_name, rows):
    ws = wb.create_sheet(title)
    ws["A1"] = f"{title} 원자료 · 이벤트 `{event_name}`"
    ws["A1"].font = font(bold=True, size=14, color="0F1E3D")
    ws["A2"] = SOURCE
    ws["A2"].font = font(size=9, color="6B7280")
    headers = ["날짜", "position (버튼 위치)", "utm_source (유입)", "구분", f"{title} 수"]
    for i, h in enumerate(headers, 1):
        ws.cell(row=4, column=i, value=h)
    style_header(ws, 4, len(headers))
    for r, (d, pos, src, n) in enumerate(rows, 5):
        ws.cell(row=r, column=1, value=d)
        ws.cell(row=r, column=2, value=pos)
        ws.cell(row=r, column=3, value=src)
        ws.cell(row=r, column=4, value=f'=IF(C{r}="claude_test","테스트","실제")')
        ws.cell(row=r, column=5, value=n).font = font(color="0000FF")  # Amplitude에서 가져온 입력값
        for c in range(1, 6):
            cell = ws.cell(row=r, column=c)
            if c != 5:
                cell.font = font()
            cell.border = BORDER
            cell.alignment = CENTER
    last = 4 + len(rows)
    total = last + 1
    ws.cell(row=total, column=1, value="합계").font = font(bold=True)
    ws.cell(row=total, column=5, value=f"=SUM(E5:E{last})").font = font(bold=True)
    for c in range(1, 6):
        ws.cell(row=total, column=c).fill = SUB_FILL
        ws.cell(row=total, column=c).border = BORDER
        ws.cell(row=total, column=c).alignment = CENTER
    ws.cell(row=total + 2, column=1, value="파란 글자 = Amplitude에서 가져온 값. 새 데이터를 붙여넣을 때는 합계 행 위에 행을 삽입하세요.").font = font(size=9, color="6B7280")
    for col, w in zip("ABCDE", [14, 22, 20, 10, 12]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"
    return ws, last


wb = Workbook()
summary = wb.active
summary.title = "요약"
views_ws, v_last = raw_sheet(wb, "노출", "LP Signup CTA Viewed", VIEWS)
clicks_ws, c_last = raw_sheet(wb, "클릭", "LP Signup CTA Clicked", CLICKS)

# ---------- 요약 ----------
ws = summary
ws["A1"] = "집플랜 랜딩페이지 · 주요 CTA 노출/클릭 정리"
ws["A1"].font = font(bold=True, size=16, color="0F1E3D")
ws["A2"] = "랜딩: https://wjdgus6480.github.io/AGM_1026_CJW/  ·  " + SOURCE
ws["A2"].font = font(size=9, color="6B7280")
ws["A3"] = "※ 현재 데이터는 대부분 테스트(utm_source = claude_test)입니다. 실제 성과는 '테스트 제외' 열을 보세요."
ws["A3"].font = font(size=10, bold=True, color="B54708")

# 2단 헤더
ws.merge_cells("A5:E5"); ws["A5"] = "CTA 정보"
ws.merge_cells("F5:H5"); ws["F5"] = "전체 (테스트 포함)"
ws.merge_cells("I5:K5"); ws["I5"] = "테스트 제외 (실제 방문)"
style_header(ws, 5, 11)
ws["I5"].fill = PatternFill("solid", fgColor=BLUE)
for c in range(9, 12):
    ws.cell(row=5, column=c).fill = PatternFill("solid", fgColor=BLUE)
heads = ["No", "스크린샷 (모바일 390px)", "position\n(버튼 위치)", "위치 설명 · 노출 조건", "버튼 문구",
         "노출", "클릭", "클릭률", "노출", "클릭", "클릭률"]
for i, h in enumerate(heads, 1):
    ws.cell(row=6, column=i, value=h)
style_header(ws, 6, 11)
for c in range(6, 9):
    ws.cell(row=6, column=c).fill = PatternFill("solid", fgColor="374151")
for c in range(9, 12):
    ws.cell(row=6, column=c).fill = PatternFill("solid", fgColor=BLUE)

IMG_W = 250  # 스크린샷 표시 폭(px)
IMG_MAX_H = 170
first = 7
for i, (pos, where, text, cond) in enumerate(CTAS):
    r = first + i
    V, C = "노출", "클릭"
    vals = [
        i + 1, None, pos, f"{where}\n· {cond}", text,
        f"=SUMIFS('{V}'!$E$5:$E${v_last},'{V}'!$B$5:$B${v_last},C{r})",
        f"=SUMIFS('{C}'!$E$5:$E${c_last},'{C}'!$B$5:$B${c_last},C{r})",
        f'=IF(F{r}=0,"-",G{r}/F{r})',
        f"=SUMIFS('{V}'!$E$5:$E${v_last},'{V}'!$B$5:$B${v_last},C{r},'{V}'!$C$5:$C${v_last},\"<>claude_test\")",
        f"=SUMIFS('{C}'!$E$5:$E${c_last},'{C}'!$B$5:$B${c_last},C{r},'{C}'!$C$5:$C${c_last},\"<>claude_test\")",
        f'=IF(I{r}=0,"-",J{r}/I{r})',
    ]
    for c, v in enumerate(vals, 1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = font(bold=(c == 3), color=(BLUE if c == 3 else "111827"))
        cell.border = BORDER
        cell.alignment = LEFT if c in (4, 5) else CENTER
        if c in (8, 11):
            cell.number_format = "0.0%"
    # 스크린샷
    src = SHOTS / f"cta_{pos}.png"
    with Image.open(src) as im:
        w, h = im.size
    scale = min(IMG_W / w, IMG_MAX_H / h)
    img = XLImage(str(src))
    img.width, img.height = round(w * scale), round(h * scale)
    ws.add_image(img, f"B{r}")
    ws.row_dimensions[r].height = max(img.height * 0.75 + 12, 48)  # px → pt

tot = first + len(CTAS)
ws.cell(row=tot, column=1, value="합계")
ws.merge_cells(start_row=tot, start_column=1, end_row=tot, end_column=5)
for col in "FGIJ":
    ws[f"{col}{tot}"] = f"=SUM({col}{first}:{col}{tot - 1})"
ws[f"H{tot}"] = f'=IF(F{tot}=0,"-",G{tot}/F{tot})'
ws[f"K{tot}"] = f'=IF(I{tot}=0,"-",J{tot}/I{tot})'
for c in range(1, 12):
    cell = ws.cell(row=tot, column=c)
    cell.font = font(bold=True)
    cell.fill = SUB_FILL
    cell.border = BORDER
    cell.alignment = CENTER
    if c in (8, 11):
        cell.number_format = "0.0%"

notes = [
    "· 노출: 버튼이 화면에 50% 이상 보이면 페이지 방문당 위치별 1번 기록 (이벤트 LP Signup CTA Viewed)",
    "· 클릭: 버튼을 누를 때마다 기록 (이벤트 LP Signup CTA Clicked)",
    "· 클릭률 = 클릭 ÷ 노출. 노출 수집은 2026-10-26 배포부터라, 그 전에 생긴 클릭(hero 실제 1건)은 노출 없이 집계될 수 있습니다.",
    "· sticky(하단 고정)는 모바일에서만 보이며, 데스크톱 방문에서는 노출이 기록되지 않습니다.",
    "· 숫자는 '노출'·'클릭' 시트의 원자료를 SUMIFS로 합산합니다. 원자료만 갱신하면 요약이 자동으로 바뀝니다.",
]
for k, n in enumerate(notes):
    ws.cell(row=tot + 2 + k, column=1, value=n).font = font(size=10, color="374151")

ws.cell(row=7, column=8).comment = Comment("클릭 ÷ 노출. 노출이 0이면 '-'로 표시", "Claude")
for col, w in zip("ABCDEFGHIJK", [5, 37, 13, 30, 26, 8, 8, 9, 8, 8, 9]):
    ws.column_dimensions[col].width = w
ws.row_dimensions[6].height = 32
ws.freeze_panes = "A7"

# ---------- 수집 기준 ----------
g = wb.create_sheet("수집 기준")
g["A1"] = "수집 기준"
g["A1"].font = font(bold=True, size=14, color="0F1E3D")
rows = [
    ("항목", "노출", "클릭"),
    ("Amplitude 이벤트", "LP Signup CTA Viewed", "LP Signup CTA Clicked"),
    ("기록 시점", "버튼이 화면에 50% 이상 보일 때", "버튼을 누를 때"),
    ("중복 처리", "페이지 방문당 위치별 1번", "누를 때마다 기록"),
    ("함께 남는 속성", "position, cta_text", "position, cta_text"),
    ("코드 위치", "index.html · 'CTA 노출' 주석 블록", "index.html · '가입 버튼 링크 연결' 블록"),
    ("테스트 방법", "평가/cta_test.py (기본: 전송 가로채기)", "평가/cta_test.py --send (실제 전송)"),
    ("테스트 데이터 구분", "utm_source = claude_test", "utm_source = claude_test"),
]
for r, row in enumerate(rows, 3):
    for c, v in enumerate(row, 1):
        cell = g.cell(row=r, column=c, value=v)
        cell.font = font(bold=(r == 3 or c == 1))
        cell.border = BORDER
        cell.alignment = LEFT
style_header(g, 3, 3)
for col, w in zip("ABC", [20, 40, 40]):
    g.column_dimensions[col].width = w

wb.calculation.fullCalcOnLoad = True  # 열 때 수식을 바로 계산
wb.save(OUT)
print(OUT)
