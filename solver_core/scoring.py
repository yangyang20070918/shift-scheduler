from __future__ import annotations

import math

from .models import ScoreBreakdown, SolverOutput, Violation

CATEGORY_MAP = {
    "personal": "personal",
    "group": "group",
    "demand": "demand",
    "pattern": "personal",
    "fixed": "personal",
}


def compute_health_score(output: SolverOutput, max_penalty: int = 1000) -> tuple[float, ScoreBreakdown]:
    if output.status == "infeasible":
        return 0.0, ScoreBreakdown(personal=0, group=0, demand=0, balance=0)
    if output.total_penalty == 0:
        return 100.0, ScoreBreakdown()

    category_penalties: dict[str, int] = {
        "personal": 0, "group": 0, "demand": 0, "balance": 0,
    }

    for v in output.violations:
        cat = CATEGORY_MAP.get(v.constraint_group, "personal")
        category_penalties[cat] += 1

    overall = _penalty_to_score(output.total_penalty, max_penalty)

    breakdown = ScoreBreakdown(
        personal=_category_score(category_penalties["personal"], max_penalty // 4),
        group=_category_score(category_penalties["group"], max_penalty // 4),
        demand=_category_score(category_penalties["demand"], max_penalty // 4),
        balance=_category_score(category_penalties["balance"], max_penalty // 4),
    )

    return round(overall, 1), breakdown


def _penalty_to_score(penalty: int, max_penalty: int) -> float:
    if penalty <= 0:
        return 100.0
    ratio = penalty / max_penalty
    score = 100.0 * math.exp(-2.0 * ratio)
    return max(0.0, min(100.0, score))


def _category_score(violation_count: int, max_count: int) -> float:
    if violation_count <= 0:
        return 100.0
    ratio = violation_count / max(max_count, 1)
    score = 100.0 * math.exp(-3.0 * ratio)
    return round(max(0.0, min(100.0, score)), 1)
