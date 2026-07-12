# 自动排班系统 - 开发计划书（第5版）

---

## 1. 项目概要

开发一款SaaS型自动排班系统。客户通过Web浏览器登录，设定人员信息、勤务Pattern、各种约束条件后，系统自动生成满足约束的排班表。个人用户可通过手机提交休息希望日并查看自己的排班。

### 1.1 核心设计思想

本系统不是简单地「用算法排班」，而是构建一套**架构完整、可扩展的排班平台**。核心模块包括：

| 模块 | 职责 |
|------|------|
| **Constraint Manager** | 统一管理所有约束（P0~Pn），插件式+依赖图架构 |
| **Constraint Compiler** | 将约束描述翻译为求解器指令，解耦约束定义与求解器实现 |
| **Feasibility Checker** | 求解前快速预检查，数学上判断是否有解 |
| **Multi-stage Solver** | 多阶段求解：先求可行解，再持续优化质量 |
| **Score / Penalty System** | 内部Penalty + 外部Health Score的双层评分 |
| **Violation Analyzer** | 求解后检测违反，分析哪些约束被违反及违反程度 |
| **Explain Engine** | 对违反进行因果分析+可信度评级+调整建议 |
| **Scenario Comparison** | 生成多个方案供客户比较选择 |

### 1.2 速度目标

50人规模、1个月排班，**2分钟以内**出结果。

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                      前端（React）                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ 管理者画面 │ │ 个人画面  │ │ 结果展示  │ │ 方案比较   │ │
│  │  (PC)    │ │  (手机)  │ │          │ │            │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────┐
│                   后端（FastAPI）                         │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Solver Core（独立模块）               │   │
│  │                                                  │   │
│  │  Input(JSON)                                     │   │
│  │    ↓                                             │   │
│  │  Validator（输入検証）                              │   │
│  │    ↓                                             │   │
│  │  Feasibility Checker（可行性予検査）                │   │
│  │    ↓                                             │   │
│  │  Constraint Manager ─→ Constraint Compiler       │   │
│  │   ┌────┐┌────┐┌────┐       ↓                    │   │
│  │   │ P0 ││ P1 ││...│    CP-SAT Engine            │   │
│  │   └────┘└────┘└────┘       ↓                    │   │
│  │                       Solution                   │   │
│  │                          ↓                       │   │
│  │                  Violation Analyzer               │   │
│  │                          ↓                       │   │
│  │                    Explain Engine                 │   │
│  │                          ↓                       │   │
│  │                  Scenario Comparison              │   │
│  │                          ↓                       │   │
│  │                    Output(JSON)                   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Web Layer（API + 导入导出）                │   │
│  │  FastAPI / Excel / PDF / 認証                    │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                 ┌───────┴───────┐
                 │  PostgreSQL   │
                 └───────────────┘
```

**Solver Core は完全に独立したモジュール**。FastAPI・React・データベースに一切依存しない。入出力はJSON。これにより：
- Solver単体でテスト・ベンチマーク可能
- 将来CP-SATをGurobiやOptaPlannerに差し替えてもConstraint定義は変更不要
- Web層は Solver Core を呼ぶだけの薄いラッパー

### 2.2 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | React + TypeScript | 响应式设计，PC和手机共用代码库 |
| 后端API | Python FastAPI | 与OR-Tools同语言，异步高性能 |
| 求解引擎 | Google OR-Tools CP-SAT | 约束满足+优化求解 |
| 数据库 | PostgreSQL | 多租户数据隔离 |
| 认证 | JWT | 登录/权限控制 |
| Excel处理 | openpyxl | 导入/导出 |
| PDF生成 | WeasyPrint | HTML→PDF转换 |
| 部署 | Docker + 云服务 | 可选AWS/GCP/Azure |

### 2.3 系统形态

| 端 | 说明 |
|---|------|
| PC Web | 管理者主操作端，全部功能 |
| 手机 Web | 响应式页面，个人提交休息希望日+查看自己排班 |
| 桌面应用 | 暂不做，后续有需求再追加 |

---

## 3. 用户角色与权限

| 角色 | 权限范围 | 操作端 |
|------|---------|-------|
| 系统管理员 | 管理公司账户、系统全局设定 | PC Web |
| 公司管理者 | 本公司全部操作 | PC Web |
| 个人用户 | 提交休息希望日、查看自己的排班表（月/周） | 手机Web + PC Web |

- 个人用户不可查看他人排班（后续可按需扩展）
- 管理者可随时修改任何人的休息日和排班
- 个人用户确定提交后不可再修改

---

## 4. 底层模型设计：Time Slot + Pattern

### 4.1 设计思想

**底层统一按Time Slot建模，Pattern只是Time Slot的组合。**

这样无论客户以后提出「早班需要2人」还是「14:00~18:00需要3人」，底层都不用改，只是输入方式不同。

### 4.2 Time Slot（时间槽）

- 分辨率：**30分钟**为一个Slot
- 一天 = 48个Slot（00:00~00:30, 00:30~01:00, ..., 23:30~24:00）
- Slot编号：0~47

### 4.3 Pattern（勤务模式）的定义

每个Pattern本质上是一组Time Slot的集合：

| 属性 | 说明 | 示例 |
|------|------|------|
| 名称 | 显示名 | 「早番」「-」 |
| 类型（Type） | Pattern的业务分类 | NORMAL |
| 开始时间 | 勤务开始时刻 | 08:00 |
| 结束时间 | 勤务结束时刻 | 17:00 |
| 休憩时间 | 扣除的休息时间 | 1小时 |
| 实际工时 | 自动计算或手动指定 | 8.0小时（0800-0800设定时为0） |
| 覆盖Slot | 系统自动计算 | Slot 16~33 |
| 跨日标志 | 结束时间<开始时间时自动设为true | false |
| 伴随专用 | 此Pattern只能在Chain中出现，不可独立排班 | true（「-」等） |
| 显示颜色 | 排班表中的显示色 | #FF6B6B |

#### Pattern Type（类型）

Pattern不只是一个名字+时间，还有业务分类。统计和逻辑判断用Type而非字符串匹配：

| Type | 说明 | 示例 |
|------|------|------|
| NORMAL | 通常勤务 | 早番、遅番、夜勤 |
| REST | 休息（公休、有休等） | 休、有休 |
| LEAVE | 请假（病假、事假等） | 病欠、事欠 |
| TRAINING | 研修 | 研修 |
| MEETING | 会议 | 会議 |
| ONCALL | 待机 | 待機 |
| HOLIDAY | 祝日休息 | 祝日 |
| COMPANION | Chain伴随 | -（夜勤明け） |

好处：
- 统计时 `pattern.type == REST` 即可，不用判断「休」「有休」「公休」等字符串
- 不同Type可以有不同的计算规则（如REST/LEAVE不计入出勤天数和劳动时间）
- 将来扩展新Type不影响现有逻辑

跨日Pattern（如夜勤22:00~翌06:00）覆盖当日的Slot 44~47和翌日的Slot 0~11。

伴随专用Pattern（如「-」）：工时和时间由客户自由设定。可能是0工时（工时全部算在夜勤里），也可能有独立工时（夜勤8h + 「-」8h）。算出勤天数，因为实际上人是在工作的（从前一天晚上到第二天白天一直在）。

### 4.4 两种配置模式

客户可以选择其中一种或同时使用：

#### Pattern模式（简单模式）

适合大多数客户。直接设定各Pattern需要多少人：

```
7/16(木)：早番 3人、遅番 3人、夜勤 1人
```

系统内部转换为Time Slot需求：
- Slot 16~33（早番覆盖）：≥ 3人
- Slot 30~45（遅番覆盖）：≥ 3人（重叠Slot累加）
- Slot 44~47 + 翌日Slot 0~11（夜勤覆盖）：≥ 1人

#### Time Slot模式（高级模式）

适合医院、护理、客服中心等按时间覆盖排班的行业：

```
7/16(木)：09:00~13:00 至少5人、13:00~17:00 至少3人、17:00~22:00 至少2人
```

直接映射到对应Slot的需求。

#### 统一的内部表达

无论客户用哪种模式输入，内部统一转换为：

```
demand[date][slot] = 需求人数
```

求解器使用统一的Slot级需求约束。

### 4.5 覆盖度计算

求解器中，某天某Slot的覆盖人数计算：

```
coverage[d][t] = sum(x[p][d][k] for p, k where pattern k covers slot t on day d)
                + sum(x[p][d-1][k] for p, k where pattern k is cross-day and covers slot t on day d)
```

覆盖度约束：
```
coverage[d][t] >= demand[d][t]   ∀ d, t
```

---

## 5. 约束体系

### 5.1 约束类别（Constraint Group）

约束按**业务含义**分为5个类别，便于UI展示和客户理解：

| 类别 | 包含约束 | 说明 |
|------|---------|------|
| **Fixed（固定）** | P0 | 不可变更的指定排班 |
| **Pattern（勤务规则）** | P1-A, P1-B | 勤务Pattern间的转换规则和连鎖规则 |
| **Personal（个人条件）** | P2, P3, P4, P5, P6, P7 | 每人的出勤/工时/连续天数约束 |
| **Group（组需求）** | P8 | 各组的出勤配置需求 |
| **Demand（总需求）** | P9 | 每日总体人员需求 |

客户在UI上可以按类别折叠/展开查看，也可以临时**禁用整个类别**重新求解（例如隐藏Personal约束看看纯粹按需求排会怎样）。

### 5.2 约束优先级详细

| 优先级 | 类别 | 名称 | 约束内容 | 硬/软 |
|--------|------|------|---------|-------|
| **P0** | Fixed | 固定排班 | 指定出勤/休息（含个人休息希望） | 硬约束（预处理固定） |
| **P1-A** | Pattern | 连续勤务禁止 | Pattern A→B禁止 | 硬约束 |
| **P1-B** | Pattern | Pattern Chain | 触发Pattern后必须跟随指定序列（如夜勤→-→休） | 硬约束 |
| **P2** | Personal | 周出勤天数 | 每人每周出勤天数范围 | 软约束（高权重） |
| **P3** | Personal | 期间出勤天数 | 每人整周期出勤天数范围 | 软约束（高权重） |
| **P4** | Personal | 周劳动时间 | 每人每周劳动时间范围 | 软约束（高权重） |
| **P5** | Personal | 期间劳动时间 | 每人整周期劳动时间范围 | 软约束（高权重） |
| **P6** | Personal | 连续出勤上限 | 每人连续出勤天数不超过上限 | 软约束（中权重） |
| **P7** | Personal | 连续休息上限 | 每人连续休息天数不超过上限 | 软约束（中权重） |
| **P8** | Group | 组出勤需求 | 每日每组×每Pattern出勤人数≥下限 | 软约束（低权重） |
| **P9** | Demand | 每日需求 | 每日总出勤人数范围 | 软约束（低权重） |
| **P10** | - | Pattern平衡 | 每人各可用Pattern出勤次数均衡 | 优化目标（最低权重） |

说明：
- P0、P1-A、P1-B始终为硬约束，违反则无解
- P2~P9为软约束，通过Penalty System处理优先级
- P10为纯优化目标，不存在「违反」的概念，只有「好」和「更好」

### 5.3 约束管理器（Constraint Manager）

插件式架构，每种约束类型是一个独立模块。约束之间可以声明**依赖关系**。

```
BaseConstraint（基类）
├── group: str              # 所属类别（fixed/pattern/personal/group/demand）
├── priority: int           # 优先级编号
├── penalty_weight: int     # 惩罚权重
├── depends_on: List[str]   # 依赖的其他约束ID（依赖图）
│
├── validate(data) → List[Warning]              # 输入验证
├── compile(data) → ConstraintSpec              # 生成求解器无关的约束描述
├── check_violations(solution, data) → List[Violation]  # 违反检查
└── suggest_fix(violation, data) → List[Suggestion]     # 调整建议
```

#### 约束依赖图（Constraint Dependency Graph）

约束之间不是完全独立的。例如：

```
P8（组出勤需求：夜班组至少2人）
  └── depends_on: P1（需要知道哪些Pattern属于夜班，哪些人可排夜班）

P4（周劳动时间）
  └── depends_on: Pattern定义（需要知道每个Pattern的工时）

P1-B（Pattern Chain）
  └── depends_on: P1-A（Chain结束后恢复禁止规则检查）
```

ConstraintManager按依赖图的拓扑顺序处理约束，确保被依赖的约束先编译。这也使得Explain Engine可以沿依赖图追溯违反的根因。

每个约束类型（P0~P10）实现为BaseConstraint的子类。新增约束只需：
1. 创建新的子类，声明depends_on
2. 注册到ConstraintManager
3. 其余（UI展示、违反报告、解释引擎）自动适配

### 5.4 P1-B Pattern Chain（勤务連鎖）详细设计

#### 概念

特定Pattern出勤时，必须跟随固定的后续序列。典型场景：夜勤后需要明け休み。

#### Chain定义

| 属性 | 说明 | 示例 |
|------|------|------|
| 触发Pattern | 发起连鎖的Pattern | 「夜勤」 |
| 后续序列 | 触发后必须跟随的Pattern/休息（有序列表） | [「-」, 「休」] |
| 连鎖总长度 | 含触发日的总天数 | 3天 |

系统支持多条Chain并存：
```
夜勤A → [-, 休]       连鎖3天
夜勤B → [明休]         连鎖2天
特勤  → [-, -, 休]     连鎖4天
```

连鎖最大长度上限：**5天**（实际场景中夜勤连鎖不会超过这个长度）。

#### 内部表现：Graph（后续可分岐）

UI上客户看到的是简单的Chain（线性序列），但内部用**Graph（有向图）**保存：

```
当前（线性Chain）：
  夜勤 → [-] → [休]

将来可扩展为（分岐Graph）：
  夜勤 → [-] → [休 OR 日勤]
```

内部数据结构为Node的有向图，每个Node可以有多个后续候选。当前阶段只支持单一后续（线性），但数据结构已为分岐预留空间，将来扩展时不需要重构。

#### CP-SAT约束建模

```
// 触发Pattern后必须跟随指定序列
x[p][d][夜勤] = 1  →  x[p][d+1][-] = 1
x[p][d][夜勤] = 1  →  rest[p][d+2] = 1

// 伴随Pattern不可独立出现
x[p][d][-] = 1     →  x[p][d-1][夜勤] = 1

// 将来分岐时：
// x[p][d][夜勤] = 1  →  x[p][d+1][-] = 1
// x[p][d][-] = 1     →  (rest[p][d+1] = 1 OR x[p][d+1][日勤] = 1)
```

#### 边界处理

**周期末尾**：周期最后 (连鎖長度-1) 天内禁止排触发Pattern。

例：连鎖3天、周期31天 → 第30、31天不能排夜勤。系统自动处理。

**跨期处理**：如果前一期末尾有未完成的Chain（如前一期最后一天排了夜勤），本期开头必须继续Chain的后续序列。通过PeriodCarryOver数据实现（详见5.5节）。

#### 与其他约束的交互

| 约束 | 交互说明 |
|------|---------|
| P1-A 连续禁止 | Chain内部的转换由Chain定义，P1-A不适用于Chain内部。Chain结束后的下一天恢复P1-A检查 |
| P2/P3 出勤天数 | 「-」算出勤天数（因为实际在工作）。Chain中的「休」算休息 |
| P4/P5 劳动时间 | 「-」的工时按客户设定值计算。可能是0（工时全归夜勤），也可能有值（如夜勤8h+-8h） |
| P6 连续出勤 | 夜勤和「-」都算连续出勤天数。Chain中的「休」打断连续出勤 |
| P9 每日需求 | Chain日（「-」和「休」）的出勤人数中，「-」计为出勤，「休」不计 |

### 5.5 跨期引继与周约束处理

#### 周开始日设定

| 设定项 | 层级 | 说明 | 默认值 |
|--------|------|------|--------|
| 周开始曜日 | 公司级 | 一周从哪天开始 | 月曜日 |

#### 跨期处理的必要性

排班周期可能不与自然周对齐。以下约束需要参考前一期的数据：

| 约束 | 需要的前期数据 | 用途 |
|------|-------------|------|
| P1-A 连续禁止 | 前期最后1天的Pattern | 本期第1天不排禁止转换的Pattern |
| P1-B Chain | 前期最后N天的Pattern序列 | 未完成Chain须在本期开头继续 |
| P2 周出勤天数 | 前期同一自然周内的出勤天数 | 计算第一周的剩余出勤额度 |
| P4 周劳动时间 | 前期同一自然周内的劳动时间 | 计算第一周的剩余工时额度 |
| P6 连续出勤 | 前期末尾的连续出勤天数 | 累计到本期开头 |
| P7 连续休息 | 前期末尾的连续休息天数 | 累计到本期开头 |

#### 跨期周约束的计算方式

```
示例：周开始=月曜、本期从木曜(7/16)开始

前一期                              本期
... [月][火][水] | [木][金][土][日]  [月][火][水][木] ...
    ← 前期末3天 →   ← 本期第1周(4天) →  ← 完整第2周 →
    ←─── 同一自然周（跨期） ──→
```

**第一周（跨期周）处理**：
1. 查询前期结果中同一自然周的数据
2. 如果前期数据存在：
   ```
   前期该周已出勤 = 2天、已劳动 = 16h
   本期第一周约束：
     出勤天数：max(0, 周下限-2) ~ max(0, 周上限-2)
     劳动时间：max(0, 周时间下限-16) ~ max(0, 周时间上限-16)
   ```
3. 如果无前期数据（首次使用）：按比例调整
   ```
   本期第一周只有4天（共7天中）：
     调整后下限 = ceil(原始下限 × 4/7)
     调整后上限 = floor(原始上限 × 4/7)
   ```

**末尾周**：只约束本期内的天数，下期生成时会反查本期数据。

#### PeriodCarryOver数据模型

排班结果确定后自动计算并保存，供下一期参考：

```
PeriodCarryOver（期末引继数据）
├── period_id
├── user_id
├── last_day_pattern_id              -- 最终日的Pattern（P1-A用）
├── last_n_days_patterns: [...]      -- 最后N天的Pattern序列（P1-B Chain用）
├── trailing_work_days: int          -- 期末连续出勤天数（P6用）
├── trailing_rest_days: int          -- 期末连续休息天数（P7用）
├── last_week_work_days: int         -- 最终周已出勤天数（P2用）
└── last_week_work_hours: float      -- 最终周已劳动时间（P4用）
```

### 5.6 Constraint Compiler（约束编译器）

#### 设计思想

Constraint不直接调用CP-SAT API。中间增加Compiler层：

```
Constraint（约束定义）
  ↓ compile()
ConstraintSpec（求解器无关的中間表現）
  ↓
Constraint Compiler
  ↓ translate()
CP-SAT Model（求解器固有の指令）
```

#### 好处

1. **求解器可替换**：将来如果CP-SAT换成Gurobi、OptaPlanner或自研求解器，只需写新的Compiler后端，所有Constraint定义不用改
2. **约束可测试**：ConstraintSpec是纯数据结构，可以独立验证正确性，不依赖求解器
3. **关注点分离**：Constraint作者只需要描述「什么约束」，不需要知道「怎么翻译成CP-SAT」

#### ConstraintSpec（中间表现）

```python
ConstraintSpec:
  type: "hard" | "soft"
  penalty_weight: int           # soft时的惩罚权重
  expressions: [
    {
      type: "implication",      # x=1 → y=1
      condition: Variable,
      consequence: Variable
    },
    {
      type: "linear_bound",     # min ≤ sum(vars) ≤ max
      variables: [Variable],
      coefficients: [int],
      min: int,
      max: int
    },
    {
      type: "forbidden_assignment",  # x[d][k] = 0
      variable: Variable,
      value: 0
    }
  ]
```

当前版本的Compiler只需支持CP-SAT后端。后端接口预留，将来扩展。

---

## 6. 评分系统（Score / Penalty System）

### 6.1 设计思想

**双层评分**：内部用Penalty（原始惩罚分），外部展示Health Score（0~100分）。

```
内部：Penalty（越小越好）
  CP-SAT目标函数 = Minimize 总Penalty

外部：Health Score（越高越好）
  客户看到的分数 = 100 - normalize(Penalty)
```

这样内部Penalty可以自由增长（加新约束时不用担心数值膨胀），外部始终是直觉友好的0~100分。

### 6.2 惩罚权重设计

| 优先级 | 约束 | 惩罚权重（每单位违反） | 说明 |
|--------|------|---------------------|------|
| P2 | 周出勤天数 | 100,000 / 天 | 偏离范围每1天 |
| P3 | 期间出勤天数 | 50,000 / 天 | 偏离范围每1天 |
| P4 | 周劳动时间 | 40,000 / 小时 | 偏离范围每1小时 |
| P5 | 期间劳动时间 | 30,000 / 小时 | 偏离范围每1小时 |
| P6 | 连续出勤上限 | 20,000 / 天 | 超过上限每1天 |
| P7 | 连续休息上限 | 15,000 / 天 | 超过上限每1天 |
| P8 | 组出勤需求 | 10,000 / 人 | 不足每1人 |
| P9 | 每日需求 | 5,000 / 人 | 不足或超出每1人 |
| P10 | Pattern平衡 | 100 / 单位 | max-min差每1 |
| - | 日间出勤均衡 | 50 / 单位 | 偏离目标值 |
| - | 时段均衡 | 30 / 单位 | 各Pattern偏差 |
| - | 个人出勤分布 | 20 / 单位 | 分布不均度 |

权重之间保持**数量级差距**，确保高优先级约束的满足不会被低优先级的优化牺牲。

### 6.3 双层分数的计算

#### 内部层：Penalty

```
总Penalty = sum(各约束的 penalty_weight × violation_amount)
```

Penalty是CP-SAT直接优化的目标函数。数值可能很大（几十万），但不暴露给客户。

#### 外部层：Health Score

```
Health Score = 100 - normalize(总Penalty)
```

归一化方式：根据问题规模（人数×天数×Pattern数）设定理论最大Penalty作为基准，将实际Penalty映射到0~100分。

各Constraint Group也各自有子分数：

```
排班结果 Health Score：92分

得分明细：
  个人条件满足度：  98分  ████████████████████░░  (P2~P7)
  组需求满足度：    90分  ██████████████████░░░░  (P8)
  每日需求満足度：  88分  █████████████████░░░░░  (P9)
  均衡性：         95分  ███████████████████░░░  (P10+Balance)
```

内部Penalty在日志和调试信息中输出（开发者用）。客户画面只显示Health Score。

---

## 7. 求解引擎

### 7.1 可行性预检查（Feasibility Checker）

在调用CP-SAT之前，用**纯数学计算**快速判断是否有解。耗时 < 1秒。

#### 检查项

| 检查 | 计算方式 | 判定 |
|------|---------|------|
| 总人日检查 | 全员可出勤总人日 vs 每日需求下限之和 | 总人日 < 需求总量 → 必定违反P9 |
| 个人可用天数 | 周期天数 - P0指定休息天数 | < 期间出勤天数下限 → 必定违反P3 |
| 个人工时可行性 | 期间出勤天数上限 × 最长Pattern工时 | < 期间工时下限 → 必定违反P5 |
| 个人工时可行性2 | 期间出勤天数下限 × 最短Pattern工时 | > 期间工时上限 → 必定违反P5 |
| 连续出勤可行性 | 连续出勤上限 vs 周出勤天数下限 | 7天内要出勤6天但连续上限为3 → 可能矛盾 |
| 组覆盖检查 | 各组的可用成员数 vs 组需求 | 某组可用成员 < 需求 → 必定违反P8 |
| Pattern覆盖检查 | 可用某Pattern的总人数 vs 该Pattern需求 | 可用人数不足 → 影响需求 |
| P1-A死锁检查 | 禁止链分析 | 所有Pattern形成环路 → 无合法连续排班 |
| P1-B Chain可行性 | 连鎖长度 vs 周期剩余天数 | 连鎖太长导致可排天数不足 |
| P1-B Chain与P3冲突 | 连鎖占用天数 vs 出勤天数上限 | Chain的出勤天数 > 期间出勤上限 |

#### 输出

- **可行**：全部检查通过，进入求解
- **有风险**：部分检查接近极限，提示客户但继续求解
- **不可行**：明确矛盾，返回具体原因，建议客户修改设定后重试

### 7.2 多阶段求解（Multi-stage Solver）

```
┌─────────────────────────────────────────────┐
│ Stage 0：预处理（< 1秒）                      │
│  - 加载PeriodCarryOver（前期引继数据）          │
│  - 固定P0变量                                │
│  - 固定P1-B Chain的连鎖变量                    │
│  - 周期末尾禁止Chain触发Pattern                │
│  - Feasibility Check                        │
│  - 构建变量和硬约束（P1-A, P1-B）              │
├─────────────────────────────────────────────┤
│ Stage 1：求可行解（总时间的40%）                │
│  - P2~P9作为软约束（高权重penalty）             │
│  - 不加平衡性目标                             │
│  - 目标：尽快找到一个约束违反最少的解             │
│  - 保存此解作为"保底解"                        │
├─────────────────────────────────────────────┤
│ Stage 2：质量优化（总时间的40%）                │
│  - 以Stage 1的解作为warm start hint           │
│  - 加入平衡性目标和P10（低权重penalty）          │
│  - 约束：总惩罚不能比Stage 1更差                │
│  - 在不牺牲约束满足度的前提下优化平衡性           │
├─────────────────────────────────────────────┤
│ Stage 3：持续改善（剩余时间）                   │
│  - 继续搜索更优解                             │
│  - CP-SAT内部持续寻找更好的解                  │
│  - 超时后返回当前最优解                        │
└─────────────────────────────────────────────┘
```

时间分配示例（总时间限制120秒）：
- Stage 0：< 1秒
- Stage 1：~48秒
- Stage 2：~48秒
- Stage 3：~24秒

如果Stage 1在10秒内就找到了满意解，剩余时间全部给Stage 2和Stage 3。

### 7.3 方案比较（Scenario Comparison）

生成多个方案，用不同的权重配置求解，供客户比较选择。

#### 三种预设方案

| 方案 | 权重倾向 | 特点 |
|------|---------|------|
| 方案A：均衡型 | 标准权重 | 各方面平衡 |
| 方案B：人员配置优先 | P8/P9权重提高2倍，平衡性权重降低 | 尽可能满足每日人员需求 |
| 方案C：个人平衡优先 | P6/P7/P10权重提高2倍，P8/P9权重降低 | 优先保证个人的工作生活平衡 |

#### 时间分配

- 默认模式：只生成方案A（均衡型），全部时间用于1个方案
- 比较模式：客户手动选择「生成多方案」，时间三等分，每方案约40秒

#### 结果展示

```
┌──────────────────────────────────────────────────────────┐
│                    方案比较                                │
├──────────┬──────────────┬───────────────┬────────────────┤
│          │ 方案A（均衡）  │ 方案B（配置优先）│ 方案C（个人优先）│
├──────────┼──────────────┼───────────────┼────────────────┤
│ 总分      │    92分      │     89分      │     94分       │
│ P9违反数  │    3处       │     0处       │     7处        │
│ P3违反数  │    1处       │     2处       │     0处        │
│ 均衡度    │    良        │     可         │     优         │
│ 连续出勤最大│   4天       │     5天       │     3天        │
├──────────┼──────────────┼───────────────┼────────────────┤
│          │   [选择]      │    [选择]      │    [选择]      │
└──────────┴──────────────┴───────────────┴────────────────┘
```

客户点击「选择」采用该方案。

---

## 8. Violation Analyzer + Explain Engine

### 8.0 Violation Analyzer（違反分析器）

Solver出力（Solution）を受け取り、各約束の違反を検出・定量化する独立モジュール。

```
Solution
  ↓
Violation Analyzer
  ├── 各Constraintのcheck_violations()を呼出
  ├── 違反の程度を定量化（何人不足、何日超過等）
  ├── 違反間の関連性を依存グラフから分析
  └── ViolationReport を生成
        ↓
  Explain Engine（原因分析+建議）
```

Violation AnalyzerとExplain Engineを分離する理由：
- Violation Analyzerは**事実の検出**（何が違反しているか）
- Explain Engineは**原因の推論**（なぜ違反しているか、どう直すか）
- 将来Explain Engineだけ高度化（AI推論等）しても、Analyzerは安定

### 8.1 Explain Engine 设计思想

不是简单的「原因推测」，而是完整的**违反原因分析+可信度评级+调整建议**系统。

当客户问「为什么山田每天上班？」时，系统给出：

```
山田太郎：出勤30天（期间31天中）

影响因素分析：                              可信度
  ① P5 期间劳动时间下限：200小时           ★★★★★（数学的に確定）
     → 200h ÷ 8h（白班工时）= 至少25天出勤
  ② 可用Pattern：仅「白班」（8h/天）        ★★★★★（数学的に確定）
     → 没有更长工时的Pattern可选择
  ③ P0 指定休息：仅1天（7/20）             ★★★★★（数学的に確定）
     → 最多可出勤30天
  ④ P9 每日需求下限5人 × 可用人数少         ★★★☆☆（間接要因の推定）
     → 该成员被需要的频率高

综合结果：至少需要25天，实际排了30天。
主要原因：①②③（確定）、④は间接要因。

调整建议（効果予測付き）：
  • 期间劳动时间下限 200h→160h → 预估出勤减至20~22天（效果：大）
  • 追加可用Pattern「遅番」10h   → 単日工時増、出勤日数減（效果：大）
  • 追加指定休息日              → 直接減少出勤天数（效果：中）
```

#### 可信度の算出方法

| 可信度 | 判定基準 | 例 |
|--------|---------|-----|
| ★★★★★ | 数学的に確定。この約束を外せば確実に改善 | 工時下限÷Pattern工時=最低出勤天数 |
| ★★★★☆ | 高確率。依存グラフで直接繋がる要因 | 組需求がP1のPattern制限に直接依存 |
| ★★★☆☆ | 推定。間接的な影響因子 | 需求下限による人手不足の波及 |
| ★★☆☆☆ | 可能性。複合要因の一部 | 複数約束の組み合わせ効果 |

### 8.2 实现方式

违反原因分析不需要重新求解，而是通过**约束参数的数学推导**：

1. **识别异常**：某人出勤天数、某日人数等偏离正常范围
2. **收集关联约束**：该人/该日的所有生效约束
3. **计算理论极限**：每个约束单独对结果的影响（如工时下限→最少出勤天数）
4. **识别紧约束**：哪些约束是「绷紧的」（实际值 = 约束边界值）
5. **交叉分析**：多个约束共同导致的结果（P3+P6一起导致P9违反）
6. **生成建议**：对每个紧约束，计算如果放松会怎样

### 8.3 约束违反一览表

#### 单条违反记录的结构

```
违反项：
  优先级：P9
  约束名称：每日出勤需求
  对象：7/25(金)
  设定值：≥ 5人
  实际值：3人

影响因素：
  ✓ P0 固定休息：该日3人指定休息
  ✓ P3 月出勤天数：2人已达月出勤上限
  ✓ P6 连续出勤：1人已达连续出勤上限

建议：
  • 减少7/25的指定休息人数
  • 提高相关成员的月出勤天数上限
```

注意：影响因素是**多个约束共同导致**，不是简单的「P9因为P3导致」。

---

## 9. 警告系统

### 9.1 第一层：输入时实时验证（事前提醒）

客户设定/修改时立即检查，在画面上实时提示：

| 检查项 | 条件 | 提醒信息 |
|--------|------|---------|
| 出勤天数下限过高 | 期间出勤下限 > 可用天数 | 「○○的出勤天数下限设定过高」 |
| 劳动时间与天数矛盾 | 周工时下限 ÷ 最长Pattern工时 > 周出勤上限 | 「○○的劳动时间下限与出勤天数上限矛盾」 |
| 总人手不足 | 全员可出勤总人日 < 需求下限合计 | 「全体人手不足」 |
| 连续禁止过严 | 禁止链导致死锁 | 「连续勤务禁止设定过严」 |
| 无可用Pattern | 某人可用Pattern列表为空 | 「○○没有设定可用Pattern」 |
| 休息上限过小 | 连续休息上限≤1 且无指定休息 | 「○○的连续休息上限过小」 |
| 组成员不足 | 组需求 > 组成员中该Pattern可用人数 | 「○○组的成员不足以满足需求」 |
| Chain周期末尾 | Chain长度 > 剩余天数時自動禁止 | 「周期最後X天は夜勤を排班できません（Chain制約）」 |
| 伴随Pattern単独設定 | 伴随Patternが需求やP0に直接指定された | 「○○は伴随専用Pattern、Chain以外で使用不可」 |

### 9.2 第二层：求解后异常检测（事后提醒）

| 检查项 | 判定条件 | 提醒信息 |
|--------|---------|---------|
| 出勤天数异常多 | 出勤 ≥ 周期天数 × 85% | 「○○出勤XX天，建议检查相关设定」 |
| 休息天数异常少 | 休息 ≤ 周期天数 × 10% | 「○○休息仅XX天」 |
| 某日出勤不足 | 出勤 < 需求下限 | 「X月X日出勤不足」 |

### 9.3 平衡性（不警告，内置算法）

出勤分布不均衡（前半月满后半月空）不作为警告。通过Penalty System的平衡性目标在算法内部解决。

---

## 10. 客户设定项一览

### 10.1 公司级设定

| 设定项 | 说明 | 示例 |
|--------|------|------|
| 公司名称 | 显示用 | 「株式会社ABC」 |
| 周开始曜日 | 一周的开始日 | 月曜日（默认） |
| 排班周期默认起始日 | 每月几号开始 | 1或16 |
| 排班周期默认天数 | 默认周期长度 | 31、14等 |
| 需求配置模式 | Pattern模式 / Time Slot模式 | Pattern模式 |
| Time Slot分辨率 | 高级模式的时间粒度 | 30分钟 |
| 休息希望提交上限天数 | 每人每周期可指定的天数 | 3天 |
| 休息希望自动提交日 | 截止日 | 每月20日 |
| 异常检测阈值 | 出勤率判定 | 85% |

### 10.2 勤务Pattern设定

| 属性 | 说明 | 示例 |
|------|------|------|
| Pattern名称 | 显示名 | 「早番」「-」 |
| 开始时间 | 勤务开始 | 08:00 |
| 结束时间 | 勤务结束 | 17:00（跨日如翌01:00） |
| 休憩时间 | 扣除休息 | 1小时 |
| 実際工時 | 自动计算或手动 | 8.0小时（0800-0800时为0） |
| 覆盖Slot | 自动计算 | Slot 16~33 |
| 伴随専用 | 只能在Chain中出现 | false（「-」设为true） |
| 显示颜色 | 排班表显示色 | #FF6B6B |

### 10.3 Pattern Chain设定（P1-B）

定义触发Pattern和其后续连鎖序列：

```
Chain定义示例：
  触发：「夜勤」
  后续：[「-」, 「休」]
  连鎖长度：3天

排班结果中：
  7/10  7/11  7/12
  夜勤   -     休
  └──── Chain ────┘
```

支持多条Chain。连鎖最大长度上限5天。

注意：「-」的工时和时间由客户自由设定。可以设为0800-0800（0工时，全部工时归入夜勤），也可以设为独立工时（如夜勤8h + 「-」8h = 合计16h）。

### 10.4 连续勤務禁止设定（P1-A）

Matrix形式设定Pattern间的禁止转换（Chain内部不受此约束影响）：

```
         → 早番  遅番  夜勤
早番 →      -     ○    ○
遅番 →      ○     -    ○
夜勤 →      ×     ○    -
         （× = 禁止，○ = 允许）

※ 夜勤→早番 は禁止。但夜勤→「-」はChainの一部なのでP1-Aの対象外。
```

### 10.5 组设定

| 属性 | 说明 |
|------|------|
| 组名 | 「正社员」「有钥匙组」等 |
| 所属成员 | 勾选成员列表（一人可属多组） |

### 10.6 个人设定

| 设定项 | 范围类型 | 说明 |
|--------|---------|------|
| 可用Pattern列表 | 选择 | 此人能排哪些Pattern |
| 周出勤天数 | 下限~上限 | P2 |
| 期间出勤天数 | 下限~上限 | P3 |
| 周劳动时间 | 下限~上限 | P4 |
| 期间劳动时间 | 下限~上限 | P5 |
| 连续出勤天数上限 | 上限 | P6 |
| 连续休息天数上限 | 上限 | P7 |

「期间」= 排班周期全长。一个月的周期就是月天数/月劳动时间，半个月的周期就是该半月。

### 10.7 排班周期设定

| 设定项 | 说明 |
|--------|------|
| 起始日 | 任意日期 |
| 天数 | 任意天数（7~45天） |
| 结束日 | 自动计算 |
| 休息希望提交截止日 | 超过此日自动确认 |

### 10.8 每日需求设定（P9）

针对每一天设定出勤人数下限/上限。支持批量设定（平日/周末统一）。

Pattern模式下也可指定各Pattern需求人数。

### 10.9 组需求设定（P8）

针对每一天设定每组×每Pattern（或每Time Slot范围）的出勤人数下限。

### 10.10 固定排班设定（P0）

指定某人某日出某Pattern或休息。来源可以是管理者指定或个人休息希望。

---

## 11. 休息希望日流程

### 11.1 完整流程

```
管理者创建排班周期，设定截止日
  ↓
个人用户在手机上选择希望休息的日期（≤上限天数）
  ├── 确定提交前可多次修改
  ↓
个人用户点击「确定提交」
  → 锁定，个人不可再修改
  ↓
截止日到达
  → 未手动确认的自动提交
  → 未设定任何日期的 → 视为不指定休息日
  → 全员锁定
  ↓
已提交的休息希望日 → 自动设为P0（指定休息）
  ↓
管理者可随时查看/修改任何人的休息希望
```

### 11.2 设定项

| 设定项 | 层级 | 说明 |
|--------|------|------|
| 休息希望提交上限天数 | 公司级 | 每人每周期最大天数 |
| 休息希望截止日 | 周期级 | 具体日期 |

---

## 12. 数据导入/导出

### 12.1 Excel导出

格式：
- 行：成员
- 列：日期
- 单元格：Pattern名称（休息为「休」）
- 附加Sheet：违反报告、警告信息、得分明细

### 12.2 PDF导出

可打印格式。表格 + 统计信息（每人出勤天数、劳动时间汇总）。

### 12.3 Excel导入（初始设定数据）

提供模板，客户填写后上传。可导入：成员列表、个人约束、每日需求。

### 12.4 Excel再导入（修改后反映）

流程：
1. 管理者导出排班结果Excel
2. 在Excel中手动修改
3. 上传修改后的Excel
4. 系统与当前结果做diff
5. 变更单元格高亮显示（黄色背景）
6. 对修改后排班重新运行约束检查，显示新增违反
7. 管理者确认 → 保存为当前结果

---

## 13. 数据模型

### 13.1 核心实体

```
Company（公司/租户）
├── id, name
├── week_start_day: 1                     -- 周开始曜日（1=月曜, 7=日曜）
├── demand_mode: "pattern" | "timeslot"    -- 需求配置模式
├── timeslot_resolution: 30               -- Time Slot分辨率（分钟）
├── default_period_start_day
├── default_period_length
├── rest_request_max_days
├── rest_request_auto_submit_day
├── anomaly_threshold_work_rate
└── created_at, updated_at

User（用户）
├── id, company_id
├── name, email, password_hash
├── role: system_admin | company_admin | member
└── is_active

ShiftPattern（勤务Pattern）
├── id, company_id
├── name, start_time, end_time
├── type: NORMAL|REST|LEAVE|TRAINING|MEETING|ONCALL|HOLIDAY|COMPANION
├── break_hours, work_hours
├── covered_slots: [int]                  -- 覆盖的Time Slot列表
├── is_cross_day: bool                    -- 跨日标志
├── is_companion: bool                    -- 伴随専用（type=COMPANIONと連動）
├── color_code
└── is_active, sort_order

ForbiddenTransition（連続勤務禁止 P1-A）
├── id, company_id
├── from_pattern_id
└── to_pattern_id

PatternChain（Pattern連鎖 P1-B）
├── id, company_id
├── trigger_pattern_id                    -- 触发Pattern（如「夜勤」）
├── total_length: int                     -- 連鎖総日数（含触发日）
└── nodes: [                              -- Graph構造（当前为線形、将来可分岐）
      {day_offset: 1, candidates: [pattern_id]},       -- 第2天：[-]
      {day_offset: 2, candidates: ["rest"]}            -- 第3天：[休]
    ]                                     -- 将来: candidates可有多个（分岐）

Group（组）
├── id, company_id
└── name

GroupMember（组成员）
├── group_id
└── user_id

PersonPatternAvailability（个人Pattern可用性）
├── user_id
├── pattern_id
└── is_available

PersonConstraint（个人约束 P2~P7 — 固定字段）
├── user_id
├── weekly_work_days_min, weekly_work_days_max      -- P2
├── period_work_days_min, period_work_days_max      -- P3
├── weekly_work_hours_min, weekly_work_hours_max    -- P4
├── period_work_hours_min, period_work_hours_max    -- P5
├── max_consecutive_work_days                       -- P6
├── max_consecutive_rest_days                       -- P7
└── extra_constraints: JSONB                        -- 将来のP11~用（拡張約束）

PersonConstraintExtension（拡張約束 — EAV方式、将来のP11~用）
├── user_id
├── constraint_type: str       -- 约束类型ID（如 "max_night_shifts_per_month"）
├── min_value: float (nullable)
├── max_value: float (nullable)
└── value: float (nullable)

※ P2~P7は固定字段（查询頻繁、性能重要）
※ 将来追加のP11~は EAV表 または JSONB で柔軟に拡張
※ Constraint Managerがどちらのストレージからも透過的に読み取る

SchedulePeriod（排班周期）
├── id, company_id
├── start_date, end_date, total_days
├── rest_request_deadline
├── status: draft | requesting | ready | generating | completed
└── created_at

DailyDemand（每日需求 P9）
├── period_id, date
├── min_total, max_total
└── pattern_demands: [{pattern_id, min_count}]   -- Pattern模式时的各Pattern需求

SlotDemand（Time Slot需求 - 高级模式用）
├── period_id, date
├── slot_start, slot_end
└── min_count

GroupDailyDemand（组需求 P8）
├── period_id, date
├── group_id, pattern_id
└── min_count

FixedAssignment（固定排班 P0）
├── period_id, user_id, date
├── type: work | rest
├── pattern_id (nullable)
└── source: admin_set | rest_request

RestDayRequest（休息希望）
├── id, user_id, period_id
├── dates: [日期列表]
├── status: draft | submitted
├── submitted_at
└── is_auto_submitted

ScheduleResult（排班结果）
├── id, period_id
├── scenario_type: balanced | staffing_priority | personal_priority
├── generated_at
├── solve_time_seconds
├── total_penalty: int                     -- 内部Penalty（开发者调试用）
├── health_score: float                    -- 外部Health Score 0~100（客户表示用）
├── score_breakdown: {personal, group, demand, balance}  -- 各类别Health Score
├── is_selected                            -- 客户选择的方案
└── solver_status: optimal | feasible | timeout

ScheduleResultDetail（排班结果明细）
├── result_id, user_id, date
├── pattern_id (null = 休息)
└── is_manually_modified

ConstraintViolation（约束违反）
├── result_id
├── priority: P2~P9
├── constraint_group: personal | group | demand
├── constraint_type
├── target_user_id (nullable)
├── target_date (nullable)
├── setting_value, actual_value
├── contributing_factors: [{priority, description}]  -- 影响因素
└── suggestions: [{description, estimated_impact}]   -- 调整建议

Warning（警告）
├── result_id (nullable, 事前警告时为null)
├── company_id
├── warning_type: pre_solve | post_solve
├── severity: info | warning | error
├── target
└── message

PeriodCarryOver（期末引继数据）
├── period_id
├── user_id
├── last_day_pattern_id              -- 最終日のPattern（P1-A用）
├── last_n_days_patterns: [...]      -- 最後N日のPattern列（P1-B Chain用）
├── trailing_work_days: int          -- 期末連続出勤日数（P6用）
├── trailing_rest_days: int          -- 期末連続休息日数（P7用）
├── last_week_work_days: int         -- 最終週の出勤日数（P2用）
└── last_week_work_hours: float      -- 最終週の労働時間（P4用）
```

### 13.2 数据隔离

多租户采用共享数据库、按company_id隔离。所有查询带company_id过滤，API层强制检查。

### 13.3 历史数据

排班结果保存6个月。超过6个月由定期任务自动清理明细数据，保留周期元信息。

---

## 14. 画面设计概要

### 14.1 管理者画面（PC）

| 画面 | 主要内容 |
|------|---------|
| 仪表板 | 当前周期状态、休息希望提交进度、最近警告 |
| 成员管理 | 成员列表、增删改 |
| 成员详细设定 | 可用Pattern、个人约束(P2~P7) |
| Pattern管理 | Pattern列表、增删改、颜色、伴随标志、Time Slot覆盖可视化 |
| Pattern Chain設定 | Chain定義（触发Pattern + 後続序列）の追加/编辑 |
| 連続禁止設定 | Pattern×Pattern的矩阵式勾选（Chain内部は対象外の注記付き） |
| 组管理 | 组列表、成员分配 |
| 排班周期管理 | 周期列表、创建新周期 |
| 需求设定 | Pattern模式：各Pattern需求 / Time Slot模式：时间段需求 |
| 固定排班 | 日历形式设定P0 |
| 排班生成 | 生成按钮、单方案/多方案切换、进度条 |
| 方案比较 | 三方案并排比较、得分明细、选择按钮 |
| 排班结果 | 月历视图 + 表格一览、得分显示 |
| 违反报告 | 表格形式、影响因素、调整建议、可按类别/成员筛选 |
| 警告一览 | 事前+事后警告 |
| 导出/导入 | Excel/PDF下载、Excel上传（初始数据、再导入） |

按Constraint Group分类展示设定：
- 管理者可以折叠/展开各类别
- 可以临时禁用整个类别重新求解

### 14.2 个人画面（手机）

| 画面 | 主要内容 |
|------|---------|
| 登录 | 账号密码 |
| 首页 | 当前周期信息、提交状态 |
| 休息希望提交 | 日历形式选择日期、确定提交按钮 |
| 我的排班（月） | 月历形式 |
| 我的排班（周） | 周视图 |

---

## 15. 性能目标与上限

### 15.1 求解速度目标

| 人数 | Pattern上限 | 组上限 | 周期天数 | 单方案目标 | 三方案目标 |
|------|-----------|--------|---------|-----------|-----------|
| 20人 | 50 | 30 | 31天 | 30秒 | 90秒 |
| 50人 | 30 | 30 | 31天 | 2分钟 | 2分钟×3 |
| 100人 | 20 | 30 | 31天 | 2分钟 | 2分钟×3 |

三方案模式下，总时间相应增加（每方案独立计时）。

### 15.2 系统限制

| 项目 | 上限 |
|------|------|
| 每公司成员数 | 200人 |
| 排班周期天数 | 7~45天 |
| 单方案求解超时 | 120秒 |
| 历史数据保存 | 6个月 |

---

## 16. 开发阶段计划

### 开发方针：Solver Core 先行

**整个项目最难、最有价值的部分是求解引擎。** Web/API/DB都是常规工程，Solver Core才是核心竞争力。因此：

1. 先把Solver Core作为独立模块开发、测试、调优到稳定
2. Solver Core不依赖FastAPI、React、PostgreSQL，输入输出都是JSON
3. Solver Core稳定后，再包上Web层

```
Phase 1~2：Solver Core（独立模块、JSON in/out）
    ↓ 速度・正確性が安定してから
Phase 3~7：Web層（API + 画面 + DB）
```

---

### Phase 1：Solver Core 基盤（约4~5周）

**目标：核心架构搭建完成，能处理基本约束，通过JSON测试**

输入：JSON文件（members, patterns, constraints, demands）
输出：JSON文件（schedule, violations, score）

- Time Slot + Pattern底层模型（含Pattern Type）
- Constraint Manager架构（BaseConstraint + 依赖图）
- Constraint Compiler（约束描述 → CP-SAT中间表现 → CP-SAT指令）
- P0（固定排班）、P1-A（连续禁止）、P1-B（Pattern Chain / Graph）
- P2~P7（个人约束：出勤天数、劳动时间、连续天数）
- P8（组需求）、P9（每日需求）
- 跨期引继逻辑（PeriodCarryOver）
- Score / Penalty System（内部Penalty）
- Multi-stage Solver（Stage 0~3）
- 基础单元测试（10人规模）

### Phase 2：Solver Core 完善 + 性能验证（约3~4周）

**目标：全功能完成、性能达标、质量可控**

- P10（Pattern平衡优化）
- 平衡性优化目标（日间、时段、个人分布）
- Feasibility Checker（可行性预检查）
- Violation Analyzer（违反检出+定量化）
- Explain Engine（原因分析+可信度+调整建议）
- Scenario Comparison（三方案生成）
- Health Score（外部评分 0~100）
- 性能基准测试：
  - 10人 × 31天 → 目标10秒
  - 20人 × 31天 → 目标30秒
  - 50人 × 31天 → 目标2分钟
  - 100人 × 31天 → 目标2分钟
- 边界测试（极端设定、全员休息、需求超出等）
- Solver Core的入出力JSON schema確定

**Phase 2完了時点で、Solver Coreは完全に独立動作可能**

---

### Phase 3：数据库 + 后端API（约3~4周）

- 数据库设计与建表（含PersonConstraint混合模型：固定字段+JSONB扩展）
- 用户认证系统（JWT、多租户数据隔离）
- 全部设定项的CRUD API
- 排班生成API（异步任务、调用Solver Core）
- 结果查询API
- 违反报告/警告API
- 输入验证（第一层警告）API

### Phase 4：管理者Web画面（约4~5周）

- 成员管理画面
- Pattern管理画面（Type选择、Time Slot覆盖可视化、伴随标志）
- Pattern Chain设定画面
- 连续禁止设定画面（矩阵式、Chain内部除外注记）
- 组管理画面
- 约束设定画面（按Constraint Group分类展示、折叠/禁用）
- 排班周期管理画面
- 需求设定画面（Pattern模式 + Time Slot模式）
- 固定排班设定画面
- 输入时实时警告提示

### Phase 5：排班生成与结果展示（约3~4周）

- 排班生成画面（进度条）
- 方案比较画面（三方案并排、Health Score）
- 排班结果展示（月历+表格）
- Health Score + 得分明细展示
- 违反报告画面（影响因素、可信度、调整建议）
- 警告一览画面

### Phase 6：导入导出 + 手机端（约3~4周）

- Excel导出（排班表+违反报告+得分）
- PDF导出
- Excel导入（初始数据模板）
- Excel再导入（差异高亮+约束重检查）
- 手机端响应式页面（休息希望提交、个人排班查看月/周）

### Phase 7：休息希望流程 + 完善（约2~3周）

- 休息希望提交/确认/自动提交流程
- 截止日自动处理（定时任务）
- 历史数据清理（定时任务）
- 多租户数据隔离验证

### Phase 8：测试与上线（约2~3周）

- 集成测试
- 负荷测试（100人规模）
- 安全审查（认证、数据隔离、注入防御）
- 部署环境搭建
- 操作手册

**预估总工期：22~30周**

---

## 17. 将来扩展（已在架构中预留）

以下功能当前不实现，但架构已为其预留扩展空间：

| 功能 | 预留方式 | 说明 |
|------|---------|------|
| **Constraint Profile（行业模板）** | Constraint Manager插件化 | 医院Profile、工厂Profile、便利店Profile等，各自启用/禁用不同的约束集合 |
| **Pattern Chain分岐** | Graph内部構造 | Chain中允许OR分岐（如：夜勤→-→休OR日勤） |
| **求解器切替** | Constraint Compiler | CP-SAT→Gurobi/OptaPlanner、只需写新的Compiler后端 |
| **P11~扩展约束** | EAV表 + JSONB + Constraint Manager | 新约束类型无需改DB schema |
| **自定义Penalty权重** | Score System | 暴露给高级客户调整各约束的优先级权重 |

---

## 18. 开放问题与后续需求

以下功能暂不实现，后续按需追加：

- 个人用户查看他人排班
- 画面上拖拽手动微调排班
- 排班模板（按周重复的固定Pattern）
- 邮件/推送通知
- 多语言支持
- 桌面应用版本
