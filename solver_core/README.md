# Solver Core — 自动排班求解引擎

独立的 Python 模块，无 Web 依赖。输入 JSON，输出 JSON。

---

## 快速开始

```bash
# 安装依赖
pip install ortools>=9.10 pydantic>=2.0

# 命令行执行
python -m solver_core.engine tests/data/basic_10.json

# Python 调用
from solver_core.engine import solve
output = solve("tests/data/basic_10.json")  # 文件路径
output = solve({"start_date": "2026-07-01", ...})  # dict
output = solve(solver_input_object)  # SolverInput 对象
```

---

## 输入格式 (SolverInput)

完整 JSON Schema: `solver_core/schema_input.json`

### 顶层字段

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| start_date | string (date) | ✅ | 排班开始日期，格式 "YYYY-MM-DD" |
| num_days | int | ✅ | 排班天数 |
| patterns | array[ShiftPattern] | ✅ | 班次定义 |
| members | array[Member] | ✅ | 成员列表 |
| person_constraints | array[PersonConstraint] | | 个人约束 |
| groups | array[Group] | | 分组定义 |
| forbidden_transitions | array[ForbiddenTransition] | | 连续禁止规则 |
| pattern_chains | array[PatternChain] | | 班次链 |
| fixed_assignments | array[FixedAssignment] | | 固定排班 |
| daily_demands | array[DailyDemand] | | 每日人力需求 |
| group_demands | array[GroupDemand] | | 分组需求 |
| carry_over | array[PeriodCarryOver] | | 跨期引继数据 |
| config | SolverConfig | | 求解器配置 |

### ShiftPattern

```json
{
  "id": "A",
  "name": "早班A",
  "type": "NORMAL",
  "start_time": "08:00",
  "end_time": "16:00",
  "break_hours": 1.0,
  "work_hours": 7.0,
  "is_companion": false,
  "color_code": "#4CAF50"
}
```

- `type`: NORMAL / REST / LEAVE / TRAINING / MEETING / ONCALL / HOLIDAY / COMPANION
- `is_companion`: true 时为伴随 Pattern，只能出现在 Chain 内部

### PersonConstraint

```json
{
  "member_id": "m01",
  "weekly_work_days_min": 4,
  "weekly_work_days_max": 5,
  "period_work_days_min": 20,
  "period_work_days_max": 23,
  "weekly_work_hours_min": 30.0,
  "weekly_work_hours_max": 40.0,
  "period_work_hours_min": 140.0,
  "period_work_hours_max": 170.0,
  "max_consecutive_work_days": 5,
  "max_consecutive_rest_days": 3
}
```

所有字段可选（null = 不约束）。

### PatternChain

```json
{
  "id": "night_chain",
  "trigger_pattern_id": "N",
  "total_length": 3,
  "nodes": [
    {"day_offset": 1, "is_rest": true, "candidates": []},
    {"day_offset": 2, "is_rest": false, "candidates": ["A", "B"]}
  ]
}
```

当 trigger 被分配后，后续天数强制执行 Chain 节点规则。

### PeriodCarryOver

```json
{
  "member_id": "m01",
  "last_day_pattern_id": "N",
  "last_n_days_patterns": ["A", "N"],
  "trailing_work_days": 3,
  "trailing_rest_days": 0,
  "last_week_work_days": 4,
  "last_week_work_hours": 30.0
}
```

从上一期间引继的状态数据，用于跨期约束的连续性。

### SolverConfig

```json
{
  "time_limit_seconds": 120,
  "week_start_day": 1,
  "stage1_ratio": 0.4,
  "stage2_ratio": 0.4
}
```

- `week_start_day`: 1=周一 ... 7=周日
- `stage1_ratio` / `stage2_ratio`: 多阶段求解的时间分配比例

---

## 输出格式 (SolverOutput)

完整 JSON Schema: `solver_core/schema_output.json`

```json
{
  "status": "optimal",
  "solve_time_seconds": 1.234,
  "total_penalty": 0,
  "health_score": 100.0,
  "score_breakdown": {
    "personal": 100.0,
    "group": 100.0,
    "demand": 100.0,
    "balance": 100.0
  },
  "assignments": [...],
  "violations": [...],
  "warnings": [...]
}
```

### status

| 值 | 含义 |
|------|------|
| optimal | 找到最优解（证明无更好解） |
| feasible | 找到可行解（可能非最优，受时间限制） |
| infeasible | 无可行解（硬约束冲突或预检查失败） |
| timeout | 超时未找到任何解 |

### Assignment

```json
{"member_id": "m01", "date": "2026-07-01", "pattern_id": "A", "is_rest": false}
```

### Violation

```json
{
  "priority": "P9",
  "constraint_group": "demand",
  "constraint_type": "daily_demand_min",
  "target_member_id": null,
  "target_date": "2026-07-05",
  "setting_value": "4",
  "actual_value": "3",
  "contributing_factors": ["固定休息成员(2人): m01, m02"],
  "suggestions": ["考虑减少2026-07-05的休息人数"]
}
```

---

## 约束优先级体系

| 优先级 | 类型 | 说明 | 处理方式 |
|--------|------|------|---------|
| P0 | 固定排班 | 管理者手动指定的排班 | 硬约束 |
| P1-A | 连续禁止 | 例：夜班后禁止接早班 | 硬约束 |
| P1-B | Pattern Chain | 例：夜班→强制休→日班 | 硬约束 |
| P2 | 周出勤天数 | 每周最少/最多出勤天数 | 软约束 (weight=50) |
| P3 | 期间出勤天数 | 整个期间最少/最多出勤天数 | 软约束 (weight=50) |
| P4 | 周劳动时间 | 每周最少/最多工时 | 软约束 (weight=40) |
| P5 | 期间劳动时间 | 整个期间最少/最多工时 | 软约束 (weight=40) |
| P6 | 连续出勤上限 | 最大连续出勤天数 | 软约束 (weight=80) |
| P7 | 连续休息上限 | 最大连续休息天数 | 软约束 (weight=30) |
| P8 | 分组需求 | 特定组的特定班次最低人数 | 软约束 (weight=60) |
| P9 | 每日需求 | 每天最低/最高出勤人数 | 软约束 (weight=100) |
| P10 | 班次均衡 | 各成员间班次分配公平性 | 优化目标 (weight=10) |

---

## 方案比较 (Scenario Comparison)

```python
from solver_core.scenario import ScenarioComparator

comparator = ScenarioComparator()
comparison = comparator.compare(solver_input)

for s in comparison.scenarios:
    print(f"{s.profile.name}: score={s.output.health_score}")

print(comparison.summary())
```

三种预设方案：
- **balanced**: 默认权重，各方面均衡
- **staffing_priority**: 人力需求优先，个人约束放宽
- **personal_priority**: 个人约束优先，需求允许部分违反

---

## 性能基准

| 规模 | 求解时间 | 目标 |
|------|---------|------|
| 10人 × 31天 | 0.5秒 | < 10秒 |
| 20人 × 31天 | 1.4秒 | < 30秒 |
| 50人 × 31天 | 6.7秒 | < 2分钟 |

测试环境：Python 3.12, OR-Tools 9.15, 8 workers

---

## 架构概要

```
JSON Input
  → SolverInput (Pydantic validation)
  → FeasibilityChecker.check()
  → ConstraintManager.compile_all() → List[ConstraintSpec]
  → CPSATCompiler (ConstraintSpec → CP-SAT model)
  → MultiStageSolver.solve()
  → ViolationAnalyzer.analyze()
  → ExplainEngine.explain()
  → scoring.compute_health_score()
  → SolverOutput (JSON)
```

扩展新约束：
1. 在 `constraints/` 下创建新文件，继承 `BaseConstraint`
2. 实现 `compile(ctx) → List[ConstraintSpec]`
3. 在 `constraints/__init__.py` 的 `ALL_CONSTRAINTS` 中注册
