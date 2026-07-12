from __future__ import annotations

from datetime import date, timedelta

from .models import SolverInput


class SolverContext:

    def __init__(self, inp: SolverInput):
        self.input = inp
        self.num_members = len(inp.members)
        self.num_patterns = len(inp.patterns)
        self.num_days = inp.num_days

        self.day_dates: list[date] = [
            inp.start_date + timedelta(days=d) for d in range(inp.num_days)
        ]

        self._pattern_id_to_idx: dict[str, int] = {
            p.id: i for i, p in enumerate(inp.patterns)
        }
        self._member_id_to_idx: dict[str, int] = {
            m.id: i for i, m in enumerate(inp.members)
        }

        self._available_patterns: list[list[int]] = []
        for m in inp.members:
            if m.available_pattern_ids:
                avail = [
                    self._pattern_id_to_idx[pid]
                    for pid in m.available_pattern_ids
                    if pid in self._pattern_id_to_idx
                ]
            else:
                avail = list(range(self.num_patterns))
            non_companion = [
                k for k in avail if not inp.patterns[k].is_companion
            ]
            self._available_patterns.append(non_companion)

        self._companion_pattern_indices: set[int] = {
            i for i, p in enumerate(inp.patterns) if p.is_companion
        }

        self._person_constraints: dict[str, object] = {
            pc.member_id: pc for pc in inp.person_constraints
        }

        self._carry_over: dict[str, object] = {
            co.member_id: co for co in inp.carry_over
        }

        self._fixed_map: dict[tuple[str, date], object] = {
            (fa.member_id, fa.date): fa for fa in inp.fixed_assignments
        }

        self._daily_demand_map: dict[date, object] = {
            dd.date: dd for dd in inp.daily_demands
        }

        self._group_id_to_idx: dict[str, int] = {
            g.id: i for i, g in enumerate(inp.groups)
        }

    def x_key(self, m: int, d: int, k: int) -> str:
        return f"x_{m}_{d}_{k}"

    def rest_key(self, m: int, d: int) -> str:
        return f"rest_{m}_{d}"

    def pattern_idx(self, pattern_id: str) -> int:
        return self._pattern_id_to_idx[pattern_id]

    def member_idx(self, member_id: str) -> int:
        return self._member_id_to_idx[member_id]

    def available_patterns(self, m: int) -> list[int]:
        return self._available_patterns[m]

    def all_patterns_for_member(self, m: int) -> list[int]:
        avail = self._available_patterns[m]
        companions = list(self._companion_pattern_indices)
        return sorted(set(avail) | set(companions))

    def get_person_constraint(self, member_id: str):
        return self._person_constraints.get(member_id)

    def get_carry_over(self, member_id: str):
        return self._carry_over.get(member_id)

    def get_fixed(self, member_id: str, d: date):
        return self._fixed_map.get((member_id, d))

    def get_daily_demand(self, d: date):
        return self._daily_demand_map.get(d)

    def week_indices(self) -> list[list[int]]:
        week_start = self.input.config.week_start_day
        weeks: list[list[int]] = []
        current_week: list[int] = []

        for di, dt in enumerate(self.day_dates):
            dow = dt.isoweekday()
            if dow == week_start and current_week:
                weeks.append(current_week)
                current_week = []
            current_week.append(di)

        if current_week:
            weeks.append(current_week)

        return weeks

    def group_member_indices(self, group_id: str) -> list[int]:
        gidx = self._group_id_to_idx.get(group_id)
        if gidx is None:
            return []
        group = self.input.groups[gidx]
        return [
            self._member_id_to_idx[mid]
            for mid in group.member_ids
            if mid in self._member_id_to_idx
        ]
