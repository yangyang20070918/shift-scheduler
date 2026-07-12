from __future__ import annotations

import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)


def generate_import_template() -> io.BytesIO:
    wb = Workbook()

    ws_members = wb.active
    ws_members.title = "メンバー"
    headers = ["名前", "対応可能パターン（カンマ区切り）"]
    for ci, h in enumerate(headers):
        cell = ws_members.cell(row=1, column=ci + 1, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
    ws_members.column_dimensions["A"].width = 20
    ws_members.column_dimensions["B"].width = 40
    ws_members.cell(row=2, column=1, value="山田太郎")
    ws_members.cell(row=2, column=2, value="日勤,夜勤")
    ws_members.cell(row=3, column=1, value="佐藤花子")
    ws_members.cell(row=3, column=2, value="日勤,夜勤,短時間")

    ws_constraints = wb.create_sheet("個人制約")
    c_headers = [
        "メンバー名", "週出勤下限", "週出勤上限",
        "期間出勤下限", "期間出勤上限",
        "連続出勤上限", "連続休息上限",
    ]
    for ci, h in enumerate(c_headers):
        cell = ws_constraints.cell(row=1, column=ci + 1, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        ws_constraints.column_dimensions[chr(65 + ci)].width = 14
    ws_constraints.cell(row=2, column=1, value="山田太郎")
    ws_constraints.cell(row=2, column=4, value=20)
    ws_constraints.cell(row=2, column=5, value=23)
    ws_constraints.cell(row=2, column=6, value=5)

    ws_demands = wb.create_sheet("毎日需要")
    d_headers = ["日付（YYYY-MM-DD）", "最小人数", "最大人数"]
    for ci, h in enumerate(d_headers):
        cell = ws_demands.cell(row=1, column=ci + 1, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        ws_demands.column_dimensions[chr(65 + ci)].width = 20
    ws_demands.cell(row=2, column=1, value="2026-07-01")
    ws_demands.cell(row=2, column=2, value=3)
    ws_demands.cell(row=2, column=3, value=5)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def parse_import_excel(file_bytes: bytes) -> dict:
    wb = load_workbook(io.BytesIO(file_bytes), read_only=True)
    result: dict = {"members": [], "constraints": [], "demands": []}

    if "メンバー" in wb.sheetnames:
        ws = wb["メンバー"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            name = row[0]
            if not name:
                continue
            patterns_str = str(row[1] or "") if len(row) > 1 else ""
            pattern_names = [p.strip() for p in patterns_str.split(",") if p.strip()]
            result["members"].append({"name": str(name), "pattern_names": pattern_names})

    if "個人制約" in wb.sheetnames:
        ws = wb["個人制約"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            name = row[0]
            if not name:
                continue
            c: dict = {"member_name": str(name)}
            fields = [
                ("weekly_work_days_min", 1), ("weekly_work_days_max", 2),
                ("period_work_days_min", 3), ("period_work_days_max", 4),
                ("max_consecutive_work_days", 5), ("max_consecutive_rest_days", 6),
            ]
            for field, idx in fields:
                if len(row) > idx and row[idx] is not None:
                    try:
                        c[field] = int(row[idx])
                    except (ValueError, TypeError):
                        pass
            result["constraints"].append(c)

    if "毎日需要" in wb.sheetnames:
        ws = wb["毎日需要"]
        for row in ws.iter_rows(min_row=2, values_only=True):
            date_val = row[0]
            if not date_val:
                continue
            d: dict = {"date": str(date_val)}
            if len(row) > 1 and row[1] is not None:
                try:
                    d["min_total"] = int(row[1])
                except (ValueError, TypeError):
                    pass
            if len(row) > 2 and row[2] is not None:
                try:
                    d["max_total"] = int(row[2])
                except (ValueError, TypeError):
                    pass
            result["demands"].append(d)

    wb.close()
    return result
