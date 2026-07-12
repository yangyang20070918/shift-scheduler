from __future__ import annotations

import io
from datetime import date, timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def generate_schedule_excel(
    schedule_name: str,
    start_date: date,
    num_days: int,
    assignments: list[dict],
    violations: list[dict],
    warnings: list[dict],
    score_breakdown: dict | None,
    health_score: float | None,
    solve_time_seconds: float | None,
    members: list[dict],
    patterns: list[dict],
) -> io.BytesIO:
    wb = Workbook()

    member_map = {m["id"]: m["name"] for m in members}
    pattern_map = {p["id"]: p for p in patterns}
    dates = [start_date + timedelta(days=i) for i in range(num_days)]

    _build_schedule_sheet(wb, schedule_name, dates, assignments, member_map, pattern_map)
    _build_stats_sheet(wb, dates, assignments, member_map, pattern_map, health_score, solve_time_seconds, score_breakdown)
    _build_violations_sheet(wb, violations, member_map)
    if warnings:
        _build_warnings_sheet(wb, warnings)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
REST_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
WEEKEND_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def _build_schedule_sheet(wb, name, dates, assignments, member_map, pattern_map):
    ws = wb.active
    ws.title = "排班表"

    ws.cell(row=1, column=1, value=name).font = Font(bold=True, size=14)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(len(dates) + 1, 10))

    header_row = 3
    ws.cell(row=header_row, column=1, value="メンバー").font = HEADER_FONT
    ws.cell(row=header_row, column=1).fill = HEADER_FILL
    ws.cell(row=header_row, column=1).border = THIN_BORDER
    ws.cell(row=header_row, column=1).alignment = Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 14

    for di, d in enumerate(dates):
        col = di + 2
        wd = WEEKDAY_JP[d.weekday()]
        cell = ws.cell(row=header_row, column=col, value=f"{d.month}/{d.day}({wd})")
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col)].width = 10

    member_ids = sorted(set(a["member_id"] for a in assignments))
    assignment_lookup: dict[tuple[str, str], dict] = {}
    for a in assignments:
        assignment_lookup[(a["member_id"], a["date"])] = a

    for mi, mid in enumerate(member_ids):
        row = header_row + 1 + mi
        name_cell = ws.cell(row=row, column=1, value=member_map.get(mid, mid))
        name_cell.border = THIN_BORDER
        name_cell.font = Font(bold=True, size=10)

        for di, d in enumerate(dates):
            col = di + 2
            a = assignment_lookup.get((mid, str(d)))
            cell = ws.cell(row=row, column=col)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(horizontal="center")

            if d.weekday() >= 5:
                cell.fill = WEEKEND_FILL

            if a is None:
                cell.value = ""
            elif a.get("is_rest"):
                cell.value = "休"
                cell.fill = REST_FILL
                cell.font = Font(color="666666", size=10)
            else:
                pid = a.get("pattern_id")
                p = pattern_map.get(pid) if pid else None
                cell.value = p["name"] if p else (a.get("pattern_name") or "出勤")
                if p and p.get("color_code"):
                    color = p["color_code"].lstrip("#")
                    if len(color) == 6:
                        cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                        r, g, b = int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16)
                        text_color = "FFFFFF" if (r * 0.299 + g * 0.587 + b * 0.114) < 150 else "000000"
                        cell.font = Font(color=text_color, size=10)


def _build_stats_sheet(wb, dates, assignments, member_map, pattern_map, health_score, solve_time, score_breakdown):
    ws = wb.create_sheet("統計情報")

    ws.cell(row=1, column=1, value="統計情報").font = Font(bold=True, size=14)

    row = 3
    if health_score is not None:
        ws.cell(row=row, column=1, value="健全スコア").font = Font(bold=True)
        ws.cell(row=row, column=2, value=round(health_score, 1))
        row += 1
    if solve_time is not None:
        ws.cell(row=row, column=1, value="求解時間").font = Font(bold=True)
        ws.cell(row=row, column=2, value=f"{solve_time:.2f}秒")
        row += 1

    if score_breakdown:
        row += 1
        ws.cell(row=row, column=1, value="スコア明細").font = Font(bold=True, size=12)
        row += 1
        label_map = {"personal": "個人制約", "group": "グループ需要", "demand": "毎日需要", "balance": "均衡性", "total_penalty": "合計ペナルティ"}
        for key, label in label_map.items():
            if key in score_breakdown:
                ws.cell(row=row, column=1, value=label)
                ws.cell(row=row, column=2, value=score_breakdown[key])
                row += 1

    row += 1
    ws.cell(row=row, column=1, value="メンバー別統計").font = Font(bold=True, size=12)
    row += 1
    headers = ["メンバー", "出勤日数", "休息日数", "合計労働時間"]
    for ci, h in enumerate(headers):
        cell = ws.cell(row=row, column=ci + 1, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 14

    member_ids = sorted(set(a["member_id"] for a in assignments))
    for mid in member_ids:
        row += 1
        member_assignments = [a for a in assignments if a["member_id"] == mid]
        work_days = sum(1 for a in member_assignments if not a.get("is_rest"))
        rest_days = sum(1 for a in member_assignments if a.get("is_rest"))
        total_hours = 0.0
        for a in member_assignments:
            if not a.get("is_rest") and a.get("pattern_id"):
                p = pattern_map.get(a["pattern_id"])
                if p:
                    total_hours += p.get("work_hours", 0)

        ws.cell(row=row, column=1, value=member_map.get(mid, mid)).border = THIN_BORDER
        ws.cell(row=row, column=2, value=work_days).border = THIN_BORDER
        ws.cell(row=row, column=3, value=rest_days).border = THIN_BORDER
        ws.cell(row=row, column=4, value=round(total_hours, 1)).border = THIN_BORDER


def _build_violations_sheet(wb, violations, member_map):
    ws = wb.create_sheet("違反レポート")

    ws.cell(row=1, column=1, value="違反レポート").font = Font(bold=True, size=14)

    if not violations:
        ws.cell(row=3, column=1, value="違反はありません").font = Font(color="008000", size=12)
        return

    headers = ["グループ", "制約種別", "優先度", "メンバー", "対象日", "設定値", "実績値", "原因分析", "改善提案"]
    col_widths = [12, 20, 8, 14, 12, 10, 10, 30, 30]
    row = 3
    for ci, h in enumerate(headers):
        cell = ws.cell(row=row, column=ci + 1, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        ws.column_dimensions[get_column_letter(ci + 1)].width = col_widths[ci]

    constraint_labels = {
        "daily_demand_min": "毎日需要（最小）",
        "daily_demand_max": "毎日需要（最大）",
        "period_days_min": "期間出勤日数（最小）",
        "period_days_max": "期間出勤日数（最大）",
        "weekly_days_min": "週出勤日数（最小）",
        "weekly_days_max": "週出勤日数（最大）",
        "consecutive_work": "連続出勤超過",
        "consecutive_rest": "連続休息超過",
        "group_demand_min": "グループ需要（最小）",
        "period_hours_min": "期間労働時間（最小）",
        "period_hours_max": "期間労働時間（最大）",
    }
    group_labels = {"personal": "個人制約", "demand": "需要制約", "group": "グループ制約"}

    for v in violations:
        row += 1
        ws.cell(row=row, column=1, value=group_labels.get(v.get("constraint_group", ""), v.get("constraint_group", ""))).border = THIN_BORDER
        ws.cell(row=row, column=2, value=constraint_labels.get(v.get("constraint_type", ""), v.get("constraint_type", ""))).border = THIN_BORDER
        ws.cell(row=row, column=3, value=v.get("priority", "")).border = THIN_BORDER
        mid = v.get("target_member_id")
        ws.cell(row=row, column=4, value=member_map.get(mid, mid or "")).border = THIN_BORDER
        ws.cell(row=row, column=5, value=v.get("target_date", "")).border = THIN_BORDER
        ws.cell(row=row, column=6, value=v.get("setting_value", "")).border = THIN_BORDER
        ws.cell(row=row, column=7, value=v.get("actual_value", "")).border = THIN_BORDER
        factors = v.get("contributing_factors", [])
        ws.cell(row=row, column=8, value="\n".join(factors) if factors else "").border = THIN_BORDER
        ws.cell(row=row, column=8).alignment = Alignment(wrap_text=True)
        suggestions = v.get("suggestions", [])
        ws.cell(row=row, column=9, value="\n".join(suggestions) if suggestions else "").border = THIN_BORDER
        ws.cell(row=row, column=9).alignment = Alignment(wrap_text=True)


def _build_warnings_sheet(wb, warnings):
    ws = wb.create_sheet("警告")
    ws.cell(row=1, column=1, value="警告一覧").font = Font(bold=True, size=14)

    headers = ["種別", "重要度", "メッセージ"]
    row = 3
    for ci, h in enumerate(headers):
        cell = ws.cell(row=row, column=ci + 1, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 50

    for w in warnings:
        row += 1
        ws.cell(row=row, column=1, value=w.get("warning_type", "")).border = THIN_BORDER
        ws.cell(row=row, column=2, value=w.get("severity", "")).border = THIN_BORDER
        ws.cell(row=row, column=3, value=w.get("message", "")).border = THIN_BORDER
