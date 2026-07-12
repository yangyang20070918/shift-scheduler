from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from .models import SolverInput, SolverOutput


@dataclass
class WeightProfile:
    name: str
    description: str
    p2_weight: int = 50
    p3_weight: int = 50
    p4_weight: int = 40
    p5_weight: int = 40
    p6_weight: int = 80
    p7_weight: int = 30
    p8_weight: int = 60
    p9_weight: int = 100
    p10_weight: int = 10


BALANCED = WeightProfile(
    name="balanced",
    description="均衡方案：各制約をデフォルト重みで均等に最適化",
)

STAFFING_PRIORITY = WeightProfile(
    name="staffing_priority",
    description="人力優先：毎日・グループの人力需要を最優先で充足",
    p9_weight=300,
    p8_weight=180,
    p2_weight=30,
    p3_weight=30,
    p6_weight=50,
    p7_weight=20,
    p10_weight=5,
)

PERSONAL_PRIORITY = WeightProfile(
    name="personal_priority",
    description="個人優先：個人の出勤日数・労働時間・連続制約を最優先",
    p2_weight=100,
    p3_weight=100,
    p4_weight=80,
    p5_weight=80,
    p6_weight=160,
    p7_weight=60,
    p9_weight=60,
    p8_weight=40,
    p10_weight=20,
)

ALL_PROFILES = [BALANCED, STAFFING_PRIORITY, PERSONAL_PRIORITY]


@dataclass
class ScenarioResult:
    profile: WeightProfile
    output: SolverOutput


@dataclass
class ScenarioComparison:
    scenarios: list[ScenarioResult] = field(default_factory=list)

    def summary(self) -> dict[str, dict[str, float]]:
        result = {}
        for s in self.scenarios:
            result[s.profile.name] = {
                "health_score": s.output.health_score,
                "total_penalty": s.output.total_penalty,
                "violations": len(s.output.violations),
                "personal_score": s.output.score_breakdown.personal,
                "demand_score": s.output.score_breakdown.demand,
                "balance_score": s.output.score_breakdown.balance,
            }
        return result


class ScenarioComparator:

    def compare(self, input_data: SolverInput, profiles: list[WeightProfile] | None = None) -> ScenarioComparison:
        from .engine import solve_with_weights

        if profiles is None:
            profiles = ALL_PROFILES

        comparison = ScenarioComparison()
        for profile in profiles:
            inp_copy = deepcopy(input_data)
            output = solve_with_weights(inp_copy, profile)
            comparison.scenarios.append(ScenarioResult(
                profile=profile, output=output,
            ))

        return comparison
