from __future__ import annotations

import io
from datetime import date, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

JP_FONT = "HeiseiKakuGo-W5"
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

STYLE_TITLE = ParagraphStyle("title", fontName=JP_FONT, fontSize=14, leading=18, spaceAfter=6)
STYLE_SECTION = ParagraphStyle("section", fontName=JP_FONT, fontSize=11, leading=14, spaceAfter=4, spaceBefore=8)
STYLE_BODY = ParagraphStyle("body", fontName=JP_FONT, fontSize=8, leading=10)

HEADER_BG = colors.HexColor("#4472C4")
HEADER_FG = colors.white
REST_BG = colors.HexColor("#D9E2F3")
WEEKEND_BG = colors.HexColor("#FFF2CC")
OK_BG = colors.HexColor("#E2EFDA")
NG_BG = colors.HexColor("#FCE4EC")


def generate_schedule_pdf(
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
    daily_demands: list[dict] | None = None,
    pattern_demands: list[dict] | None = None,
    group_demands: list[dict] | None = None,
    groups: list[dict] | None = None,
) -> io.BytesIO:
    buf = io.BytesIO()

    member_map = {m["id"]: m["name"] for m in members}
    pattern_map = {p["id"]: p for p in patterns}
    dates = [start_date + timedelta(days=i) for i in range(num_days)]

    page_size = landscape(A4) if num_days > 15 else A4
    doc = SimpleDocTemplate(buf, pagesize=page_size, leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=10 * mm, bottomMargin=10 * mm)

    elements: list = []
    elements.append(Paragraph(schedule_name, STYLE_TITLE))

    if health_score is not None:
        info_parts = [f"健全スコア: {health_score:.1f} / 100"]
        if solve_time_seconds is not None:
            info_parts.append(f"求解時間: {solve_time_seconds:.2f}秒")
        if violations:
            info_parts.append(f"違反数: {len(violations)}")
        elements.append(Paragraph("　　".join(info_parts), STYLE_BODY))

    if score_breakdown:
        label_map = {"personal": "個人制約", "group": "グループ", "demand": "需要", "balance": "均衡性"}
        parts = [f"{label}: {score_breakdown.get(key, 0)}" for key, label in label_map.items() if key in score_breakdown]
        if parts:
            elements.append(Paragraph("スコア明細: " + "　　".join(parts), STYLE_BODY))

    elements.append(Spacer(1, 4 * mm))

    # ── Schedule grid ──
    # Split into chunks if too many days
    chunk_size = 16 if page_size == landscape(A4) else 10
    member_ids = sorted(set(a["member_id"] for a in assignments))
    assignment_lookup: dict[tuple[str, str], dict] = {}
    for a in assignments:
        assignment_lookup[(a["member_id"], a["date"])] = a

    for chunk_start in range(0, len(dates), chunk_size):
        chunk_dates = dates[chunk_start:chunk_start + chunk_size]

        if chunk_start > 0:
            elements.append(Spacer(1, 4 * mm))

        header = ["メンバー"] + [f"{d.month}/{d.day}\n({WEEKDAY_JP[d.weekday()]})" for d in chunk_dates]
        data = [header]

        for mid in member_ids:
            row = [member_map.get(mid, mid[:8])]
            for d in chunk_dates:
                a = assignment_lookup.get((mid, str(d)))
                if a is None:
                    row.append("")
                elif a.get("is_rest"):
                    row.append("休")
                else:
                    pid = a.get("pattern_id")
                    p = pattern_map.get(pid) if pid else None
                    row.append(p["name"] if p else (a.get("pattern_name") or "出勤"))
            data.append(row)

        name_w = 22 * mm
        avail = (page_size[0] - 20 * mm - name_w)
        day_w = min(avail / max(len(chunk_dates), 1), 18 * mm)
        col_widths = [name_w] + [day_w] * len(chunk_dates)

        tbl = Table(data, colWidths=col_widths, repeatRows=1)

        style_cmds: list = [
            ("FONTNAME", (0, 0), (-1, -1), JP_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTSIZE", (0, 0), (-1, 0), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
        ]

        for di, d in enumerate(chunk_dates):
            col = di + 1
            if d.weekday() >= 5:
                style_cmds.append(("BACKGROUND", (col, 0), (col, 0), colors.HexColor("#E8A020")))

            for mi, mid in enumerate(member_ids):
                row_idx = mi + 1
                a = assignment_lookup.get((mid, str(d)))
                if a and a.get("is_rest"):
                    style_cmds.append(("BACKGROUND", (col, row_idx), (col, row_idx), REST_BG))
                elif a and a.get("pattern_id"):
                    p = pattern_map.get(a["pattern_id"])
                    if p and p.get("color_code"):
                        color_hex = p["color_code"].lstrip("#")
                        if len(color_hex) == 6:
                            bg = colors.HexColor(f"#{color_hex}")
                            r, g, b = int(color_hex[:2], 16), int(color_hex[2:4], 16), int(color_hex[4:], 16)
                            fg = colors.white if (r * 0.299 + g * 0.587 + b * 0.114) < 150 else colors.black
                            style_cmds.append(("BACKGROUND", (col, row_idx), (col, row_idx), bg))
                            style_cmds.append(("TEXTCOLOR", (col, row_idx), (col, row_idx), fg))

        tbl.setStyle(TableStyle(style_cmds))
        elements.append(tbl)

    # ── Daily stats row ──
    if daily_demands:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph("日別出勤統計", STYLE_SECTION))

        demand_map = {d["date"]: d for d in daily_demands}
        for chunk_start in range(0, len(dates), chunk_size):
            chunk_dates = dates[chunk_start:chunk_start + chunk_size]
            header = ["項目"] + [f"{d.month}/{d.day}" for d in chunk_dates]

            actual_row = ["出勤人数"]
            required_row = ["必要人数"]
            diff_row = ["過不足"]

            for d in chunk_dates:
                ds = str(d)
                day_a = [a for a in assignments if a["date"] == ds and not a.get("is_rest")]
                actual = len(day_a)
                actual_row.append(str(actual))

                demand = demand_map.get(ds)
                if demand:
                    required_row.append(f"{demand['min_total']}~{demand['max_total']}")
                    diff = actual - demand["min_total"]
                    diff_row.append(f"+{diff}" if diff >= 0 else str(diff))
                else:
                    required_row.append("-")
                    diff_row.append("-")

            data = [header, actual_row, required_row, diff_row]
            col_widths_s = [name_w] + [day_w] * len(chunk_dates)
            tbl = Table(data, colWidths=col_widths_s, repeatRows=1)

            style_cmds_s: list = [
                ("FONTNAME", (0, 0), (-1, -1), JP_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ]

            for di, d in enumerate(chunk_dates):
                col = di + 1
                ds = str(d)
                demand = demand_map.get(ds)
                if demand:
                    day_a = [a for a in assignments if a["date"] == ds and not a.get("is_rest")]
                    diff = len(day_a) - demand["min_total"]
                    bg = OK_BG if diff >= 0 else NG_BG
                    style_cmds_s.append(("BACKGROUND", (col, 3), (col, 3), bg))

            tbl.setStyle(TableStyle(style_cmds_s))
            elements.append(tbl)
            if chunk_start + chunk_size < len(dates):
                elements.append(Spacer(1, 2 * mm))

    # ── Personal stats table ──
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("個人統計", STYLE_SECTION))

    work_pattern_ids = [pid for pid, p in pattern_map.items()
                        if p.get("type") in ("work", "travel", "NORMAL", "TRAVEL")]
    stat_headers = ["メンバー", "出勤", "休日", "労働時間"] + [pattern_map[pid]["name"] for pid in work_pattern_ids]
    stat_data = [stat_headers]

    all_work_days = []
    all_hours = []

    for mid in member_ids:
        ma = [a for a in assignments if a["member_id"] == mid]
        wd = sum(1 for a in ma if not a.get("is_rest"))
        rd = sum(1 for a in ma if a.get("is_rest"))
        th = 0.0
        pc: dict[str, int] = {}
        for a in ma:
            if not a.get("is_rest") and a.get("pattern_id"):
                p = pattern_map.get(a["pattern_id"])
                if p:
                    th += p.get("work_hours", 0)
                    pc[a["pattern_id"]] = pc.get(a["pattern_id"], 0) + 1

        all_work_days.append(wd)
        all_hours.append(th)

        row = [member_map.get(mid, mid[:8]), str(wd), str(rd), f"{th:.1f}h"]
        for pid in work_pattern_ids:
            row.append(str(pc.get(pid, 0)))
        stat_data.append(row)

    stat_col_w = [22 * mm, 12 * mm, 12 * mm, 16 * mm] + [12 * mm] * len(work_pattern_ids)
    tbl = Table(stat_data, colWidths=stat_col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), JP_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
    ]))
    elements.append(tbl)

    # ── Overall balance ──
    if all_work_days:
        import math
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph("全体バランス", STYLE_SECTION))
        avg_wd = sum(all_work_days) / len(all_work_days)
        avg_h = sum(all_hours) / len(all_hours)
        stddev = math.sqrt(sum((x - avg_wd) ** 2 for x in all_work_days) / len(all_work_days))
        balance_text = (
            f"出勤日数: 平均 {avg_wd:.1f}日 / 最小 {min(all_work_days)} / 最大 {max(all_work_days)} / 標準偏差 {stddev:.2f}　　"
            f"労働時間: 平均 {avg_h:.1f}h / 最小 {min(all_hours):.1f} / 最大 {max(all_hours):.1f}"
        )
        elements.append(Paragraph(balance_text, STYLE_BODY))

    # ── Violations summary ──
    if violations:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph(f"違反レポート（{len(violations)}件）", STYLE_SECTION))

        constraint_labels = {
            "daily_demand_min": "毎日需要(最小)", "daily_demand_max": "毎日需要(最大)",
            "period_days_min": "期間出勤(最小)", "period_days_max": "期間出勤(最大)",
            "weekly_days_min": "週出勤(最小)", "weekly_days_max": "週出勤(最大)",
            "consecutive_work": "連続出勤超過", "consecutive_rest": "連続休息超過",
            "group_demand_min": "グループ需要(最小)",
            "period_hours_min": "期間労働(最小)", "period_hours_max": "期間労働(最大)",
        }
        group_labels = {"personal": "個人", "demand": "需要", "group": "グループ"}

        v_headers = ["グループ", "制約種別", "優先度", "メンバー", "日付", "設定", "実績"]
        v_data = [v_headers]
        for v in violations:
            mid = v.get("target_member_id")
            v_data.append([
                group_labels.get(v.get("constraint_group", ""), v.get("constraint_group", "")),
                constraint_labels.get(v.get("constraint_type", ""), v.get("constraint_type", "")),
                v.get("priority", ""),
                member_map.get(mid, mid or "") if mid else "",
                v.get("target_date", ""),
                str(v.get("setting_value", "")),
                str(v.get("actual_value", "")),
            ])

        v_col_w = [16 * mm, 28 * mm, 12 * mm, 20 * mm, 16 * mm, 16 * mm, 12 * mm]
        tbl = Table(v_data, colWidths=v_col_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), JP_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
        ]))
        elements.append(tbl)

    # ── Warnings ──
    if warnings:
        elements.append(Spacer(1, 3 * mm))
        elements.append(Paragraph(f"警告（{len(warnings)}件）", STYLE_SECTION))
        for w in warnings:
            elements.append(Paragraph(f"[{w.get('severity', '')}] {w.get('message', '')}", STYLE_BODY))

    doc.build(elements)
    buf.seek(0)
    return buf
