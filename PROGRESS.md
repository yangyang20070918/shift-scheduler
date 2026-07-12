# 开发进度追踪

> 本文件记录各阶段的详细开发步骤和当前状态。
> 下次继续开发时，查看本文件即可知道从哪里继续。

---

## 当前状态

| 项目 | 状态 |
|------|------|
| **当前阶段** | Phase 8 进行中（手動テスト待ち） |
| **Phase 1** | ✅ 完成（2026-07-11） |
| **Phase 2** | ✅ 完成（2026-07-12） |
| **Phase 3** | ✅ 完成（2026-07-12） |
| **Phase 4** | ✅ 完成（2026-07-12） |
| **Phase 5** | ✅ 完成（2026-07-12） |
| **Phase 6** | ✅ 完成（2026-07-12） |
| **Phase 7** | ✅ 完成（2026-07-13） |
| **Phase 8** | 🔧 進行中（手動テスト待ち） |

**下次继续开发时应该做的事：**

1. **启动后端：** `cd shift_app && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
2. **启动前端：** `cd shift_app/web && npm run dev`（端口5173，自动代理 /api → localhost:8000）
3. **开始 Phase 8：** 测试与上线

**已完成的全部页面（日本語UI）：**
- ✅ Login/Register（JWT 認証 + 自動リダイレクト）
- ✅ Pattern 管理（一覧 + 追加 + 削除、色/タイプ/時間/工時表示）
- ✅ Member 管理（一覧 + 追加/編集/削除、対応可能パターン多選択）
- ✅ Group 管理（一覧 + 追加/編集/削除、メンバー多選択）
- ✅ PersonConstraint 管理（勤務日数/時間/連続上限 CRUD）
- ✅ Schedule 一覧（新規作成 + 状態更新 + 設定/詳細リンク）
- ✅ Schedule 設定（毎日需要一括 + 固定割当 + グループ需要 + 生成 + 三方案比較）
- ✅ Schedule 結果（統計カード + スコア明細 + 排班表 + 違反レポート + 警告一覧）
- ✅ サイドバー（メンバー/パターン/グループ/個人制約/スケジュール）+ ユーザー情報 + ログアウト
- ✅ 休み希望受付管理（受付開始/メンバー別ステータス/個人リンク/受付締切）
- ✅ 個人ページ（トークン認証/カレンダー日付選択/確定提出/マイスケジュール）

**注意事项：**
- 数据库使用 SQLite（dev.db），lifespan 自动建表
- Pattern type 在 API 层用小写（work/rest/leave 等），scheduler 自动映射到 solver 枚举
- TestClient 必须用 `with` 语句才能触发 lifespan
- solver_core 在 API 中为延迟导入（仅在 generate 时加载，避免启动时 numpy 开销）
- 后端 API 已加 NoCacheMiddleware，所有 /api/ 响应自动添加 `Cache-Control: no-store`
- 前端 axios client 默认添加 `Cache-Control: no-cache` 请求头

---

## Phase 1：Solver Core 基盤 ✅ 完成

**目标：** 核心架构搭建完成，能处理基本约束，通过JSON测试  
**完成日期：** 2026-07-11  
**测试结果：** 8个测试全部通过，10人×31天求解12秒，health_score=100

### Step 1: 项目初始化 + 数据模型 ✅

- [x] git init, pyproject.toml, .gitignore
- [x] `solver_core/__init__.py`
- [x] `solver_core/models.py` — 全部 Pydantic 模型
  - PatternType(Enum), ShiftPattern, Member, PersonConstraint
  - Group, ForbiddenTransition, ChainNode, PatternChain
  - FixedAssignment, DailyDemand, GroupDemand, PeriodCarryOver
  - SolverConfig, SolverInput（顶层输入）
  - Assignment, Violation, SolverWarning, ScoreBreakdown, SolverOutput（顶层输出）

### Step 2: 约束架构 ✅

- [x] `solver_core/context.py` — SolverContext
  - 变量键管理：x_key(m,d,k), rest_key(m,d)
  - 查找辅助：pattern_idx, member_idx, available_patterns, all_patterns_for_member
  - 周分组：week_indices()（支持自定义周起始日）
  - 跨期数据：get_carry_over, get_person_constraint
- [x] `solver_core/constraints/base.py` — ConstraintSpec 体系
  - LinearConstraint, ImplicationConstraint, FixedVariable, ExactlyOne, WindowMax, MinimizeDiff
  - BaseConstraint ABC（compile + validate + priority + depends_on）
- [x] `solver_core/compiler.py` — CPSATCompiler
  - 变量创建（x_m_d_k + rest_m_d，每人每天 exactly_one）
  - 各 Spec 翻译：_add_fixed, _add_implication, _add_linear, _add_soft_linear, _add_window_max, _add_minimize_diff
  - 目标函数：penalty_vars + balance_vars 加权求和最小化
- [x] `solver_core/manager.py` — ConstraintManager
  - 注册、验证、按优先级排序编译

### Step 3: 基本约束 (P0, P1-A, P1-B, P9) ✅

- [x] `constraints/p0_fixed.py` — P0 固定排班 → FixedVariable specs
- [x] `constraints/p1a_forbidden.py` — P1-A 连续禁止 → ImplicationConstraint specs + carry_over
- [x] `constraints/p1b_chain.py` — P1-B Pattern Chain → Implication + Fixed specs + carry_over
- [x] `constraints/p9_daily_demand.py` — P9 每日人力需求 → LinearConstraint (soft, weight=100)

### Step 4: 个人约束 (P2~P7) ✅

- [x] `constraints/p2_weekly_days.py` — 周出勤天数（soft, weight=50, carry_over 第一周补正）
- [x] `constraints/p3_period_days.py` — 期间出勤天数（soft, weight=50）
- [x] `constraints/p4_weekly_hours.py` — 周劳动时间（soft, weight=40, HOURS_SCALE=10）
- [x] `constraints/p5_period_hours.py` — 期间劳动时间（soft, weight=40）
- [x] `constraints/p6_consecutive_work.py` — 连续出勤上限（WindowMax soft, weight=80 + carry_over）
- [x] `constraints/p7_consecutive_rest.py` — 连续休息上限（WindowMax soft, weight=30 + carry_over）

### Step 5: 分组 + 均衡 (P8, P10) ✅

- [x] `constraints/p8_group_demand.py` — 分组需求（soft, weight=60）
- [x] `constraints/p10_pattern_balance.py` — Pattern 均衡（MinimizeDiff, weight=10）
- [x] `constraints/__init__.py` — ALL_CONSTRAINTS 注册列表

### Step 6: Solver + 评分 ✅

- [x] `solver_core/solver.py` — MultiStageSolver
  - 三阶段求解：Stage1(40%) → Stage2(40%) → Stage3(剩余时间)
  - 每阶段间传递 hints（加速后续搜索）
  - 修复：clear_hints() 防止重复 hint 导致 MODEL_INVALID
- [x] `solver_core/scoring.py` — Penalty → HealthScore
  - 指数衰减函数：score = 100 × exp(-2 × penalty/max_penalty)
  - 分类评分：personal, group, demand, balance

### Step 7: Analyzer + 入口 ✅

- [x] `solver_core/analyzer.py` — ViolationAnalyzer
  - 检查：daily_demand 违反、period/weekly 天数、period 工时、连续出勤/休息
  - 生成 Violation 对象（含 priority, setting_value, actual_value）
- [x] `solver_core/engine.py` — 主入口 solve()
  - 完整管线：Input → Feasibility → Compile → Solve → Analyze → Score → Output
  - CLI 支持：`python -m solver_core.engine input.json`
- [x] `solver_core/feasibility.py` — FeasibilityChecker
  - 预检查：成员无可用 Pattern、需求超总人数、固定排班引用无效 Pattern
- [x] `solver_core/__main__.py` — 模块入口

### Step 8: 测试 ✅

- [x] `tests/__init__.py`
- [x] `tests/conftest.py` — 测试 fixtures（basic_10_input, minimal_input）
- [x] `tests/data/basic_10.json` — 10人×31天测试数据（5 Pattern + P0/P1-A/P3/P6/P7/P9）
- [x] `tests/test_solver_basic.py` — 8个测试用例
  - TestEndToEnd：produces_assignments, p0_fixed_respected, health_score, forbidden_transition, period_days
  - TestMinimal：minimal_3_members, empty_demands
  - TestInfeasible：impossible_demand

### Phase 1 已知限制（Phase 2 解决）

- Penalty 权重暂为硬编码默认值（未来可从 config 读取）
- Analyzer 只检查部分约束违反（P2/P3/P5/P6/P7/P9），未覆盖 P4/P8/P10
- 无 Explain Engine（仅有 Violation 列表，无因果分析）
- 无 Scenario Comparison（仅生成单一方案）
- 未做 50人/100人 性能测试

---

## Phase 2：Solver Core 完善 + 性能验证 ✅ 完成

**目标：** 全功能完成、性能达标、Explain Engine + Scenario Comparison  
**完成日期：** 2026-07-12  
**测试结果：** 23个测试全部通过，50人×31天求解6.7秒

### Step 1: Explain Engine ✅

- [x] `solver_core/explain.py` — ExplainEngine
  - 对每个 Violation 进行因果分析（按 constraint_type 分派）
  - 识别 contributing_factors（固定休息成员、需求冲突、连续区间等）
  - 生成 suggestions（调整建议，中文）
  - 支持的违反类型：demand、period_days、weekly_days、consecutive_work/rest、period_hours
- [x] 集成到 engine.py 管线（solve → analyze → explain → score）

### Step 2: Scenario Comparison ✅

- [x] `solver_core/scenario.py` — ScenarioComparator
  - 三组预设权重配置 (WeightProfile dataclass)：
    - BALANCED：默认权重
    - STAFFING_PRIORITY：P9×3, P8×3，个人约束降权
    - PERSONAL_PRIORITY：P2~P7 ×2，需求降权
  - ScenarioComparison.summary() 返回对比摘要
- [x] engine.py 增加 `solve_with_weights()` 函数
- [x] ConstraintManager.apply_weights() 动态覆盖 penalty_weight

### Step 3: Analyzer 完善 ✅

- [x] 补充 P4（周工时）违反检测
- [x] 补充 P8（分组需求）违反检测
- [x] 周约束违反标注具体周的起始日期

### Step 4: 自定义 Penalty 权重 ✅

- [x] WeightProfile 定义各优先级权重
- [x] ConstraintManager.apply_weights() 在 compile_all 时覆盖 spec 的 penalty_weight
- [x] Scenario Comparison 测试验证不同权重产生不同结果

### Step 5: 性能基准测试 ✅

- [x] `tests/test_performance.py` — 性能基准（动态生成测试数据）
- [x] 性能优化：
  - OPTIMAL 后跳过后续阶段（避免无意义重复求解）
  - num_workers=8（并行搜索）
  - clear_hints() 防止 MODEL_INVALID
- [x] 基准结果：
  - 10人 × 31天 → **0.5秒** ✅（目标10秒）
  - 20人 × 31天 → **1.4秒** ✅（目标30秒）
  - 50人 × 31天 → **6.7秒** ✅（目标2分钟）

### Step 6: 边界测试 ✅

- [x] `tests/test_edge_cases.py` — 7个测试用例
  - 全员固定休息 → feasible, 全部 is_rest
  - 单日期间 → 正常求解
  - 需求超出可用人力 → soft violation
  - carry_over 连续出勤 → 正确插入休息
  - 连续禁止 → 完全遵守
  - Pattern Chain → trigger→rest→candidate 正确执行
  - 相互矛盾约束 → feasible + 有 violations

### Step 7: JSON Schema 确定 + 文档 ✅

- [x] `solver_core/schema_input.json` — SolverInput 完整 JSON Schema（7.4KB）
- [x] `solver_core/schema_output.json` — SolverOutput 完整 JSON Schema（4.8KB）
- [x] `solver_core/README.md` — 使用说明文档
  - 快速开始（CLI + Python 调用）
  - 输入格式详解（全字段说明 + 示例 JSON）
  - 输出格式详解（status / assignments / violations）
  - 约束优先级体系一览表
  - 方案比较 API 用法
  - 性能基准
  - 架构概要 + 扩展方法

---

## Phase 3：数据库 + 后端 API ✅ 完成

**目标：** Web 层基础，CRUD API + 异步排班生成  
**完成日期：** 2026-07-12  
**测试结果：** 36个测试全部通过���23 solver + 13 API），排班生成 API 端到端验证成功

### Step 1: 技术选型与项目结构 ✅

- [x] FastAPI 0.139 + Starlette 1.3 + Uvicorn
- [x] SQLAlchemy 2.x (asyncio) + aiosqlite (dev) / PostgreSQL (prod)
- [x] JWT认证: python-jose + passlib[bcrypt]
- [x] 项目结构：api/{config, database, deps, main, models/, routers/, schemas/, services/}

### Step 2: 数据库设计 ✅

- [x] 多租户表设计（TenantMixin: tenant_id 全表贯穿）
- [x] 13个表：tenants, users, members, shift_patterns, forbidden_transitions,
      pattern_chains, groups, group_members, person_constraints,
      daily_demands, group_demands, schedules, fixed_assignments
- [x] TimestampMixin (created_at, updated_at)
- [x] Lifespan auto-create（开发用，生产用 Alembic）

### Step 3: 认证与权限 ✅

- [x] JWT 认证（register → login → Bearer token）
- [x] 多租户数据隔离（token 中嵌入 tenant_id，每个 API 自动过滤）
- [x] 角色字段（admin/user，首位注册者自动为 admin）
- [x] 重复邮箱注册返回 409

### Step 4: CRUD API ✅

- [x] Members: GET/POST/PUT/DELETE
- [x] Patterns: GET/POST/DELETE
- [x] Schedules: GET/POST + GET /{id}（含结果详情）
- [x] Health endpoint: GET /api/health

### Step 5: 排班生成 API ✅

- [x] POST /schedules/{id}/generate → BackgroundTasks 异步执行
- [x] DB → SolverInput 适配层（build_solver_input + type 映射）
- [x] 结果回写 DB（assignments, violations, warnings, health_score, solve_time）
- [x] 状态流转：draft → running → completed/failed
- [x] solver_core 延迟导入（避免 numpy/ortools 版本冲突影响 API 启动）

### Step 6: 结果与报告 API ✅

- [x] GET /schedules/{id} → 完整结果（assignments, violations, warnings, score）
- [x] GET /schedules → 列表（含 health_score, solve_time 概要）

### 已修复问题

| 问题 | 解决方案 |
|------|---------|
| models 未注册到 Base.metadata | main.py: `from .models import Base`（触发 __init__.py 注册全模型）|
| TestClient 不触发 lifespan | 改用 `with TestClient(app) as client:` 上下文管理器模式 |
| start_date 字符串入 Date 列报错 | Schema 改为 `date` 类型，Model 改为 `datetime.date` |
| Pattern type 'work' 不匹配 solver enum | scheduler 增加 _TYPE_MAP 映射（work→NORMAL 等）|
| solver_core 启动时导入 ortools 阻塞 | schedules router 和 scheduler service 改为延迟导入 |
| numexpr/bottleneck 与 numpy 2.x 不兼容 | 升级 numexpr 2.14.1, bottleneck 1.6.0 |

---

## Phase 4：管理者 Web 画面 ✅ 完成

**目标：** 管理者可通过浏览器完成基本设定操作
**完成日期：** 2026-07-12
**技术栈：** React 19 + TypeScript + Vite + Ant Design 5 + React Router 7 + Axios + dayjs

### Step 1: 前端初始化 ✅

- [x] React + TypeScript + Vite 脚手架（web/ 目录）
- [x] Ant Design 5 + React Router 7 + Axios
- [x] Vite API 代理配置（/api → localhost:8000）
- [x] API Client（axios + JWT 拦截器 + 401 自动跳转 + Cache-Control: no-cache）
- [x] Auth Context（token/user 全局状态）
- [x] AppLayout（侧边栏 + 头部用户信息 + 退出）
- [x] 路由保护（ProtectedRoute: 无 token → /login）

### Step 2: 认证页面 ✅

- [x] Login/Register 切换 Tab
- [x] 登录后自动获取用户信息、跳转到 /schedules
- [x] Logout 清除 token

### Step 3: Pattern 管理 ✅

- [x] Pattern 列表（颜色块 + 名称 + 类型标签 + 时间 + 工时）
- [x] 新增 Pattern Modal（含 ColorPicker、时间、工时输入）
- [x] 删除 Pattern（Popconfirm 确认）

### Step 4: Member 管理 ✅

- [x] Member 列表（名称 + 可用 Pattern 名称显示）
- [x] 新增/编辑 Member Modal（名称 + Pattern 多选）
- [x] 删除 Member

### Step 5: Schedule 管理 ✅

- [x] Schedule 列表（名称 + 开始日 + 天数 + 状态标签 + Health Score + Solve Time）
- [x] 新增 Schedule Modal（名称 + DatePicker + 天数）
- [x] Generate 按钮 + 自动刷新（5s/15s 后重查）
- [x] View 按钮跳转结果页

### Step 6: Schedule 结果页 ✅

- [x] 统计卡片（Health Score, Status, Solve Time, Violations 数）
- [x] 排班网格（Member x Date，Pattern 名称 + 颜色标签 / REST 标签）
- [x] 违反列表（Type, Priority, Member, Message）
- [x] Back to Schedules 导航

### Step 7: 后端缓存修复 ✅

- [x] NoCacheMiddleware（所有 /api/ 响应添加 Cache-Control: no-store）
- [x] 前端 axios 默认 Cache-Control: no-cache 请求头

### 已验证功能

| 功能 | 验证方式 |
|------|---------|
| Login/Register | 浏览器手动测试 ✅ |
| Pattern CRUD | API + 浏览器 ✅（3个 Pattern 正确显示颜色/类型/时间）|
| Member CRUD | API ✅（5人 + 3个 Pattern 关联）|
| Schedule 创建 | API ✅ |
| 排班生成 | API 端到端 ✅（5人x7天, optimal, health_score=100, 0.10s）|
| 结果页渲染 | 浏览器 ✅（统计卡片 + 网格 + 违反表）|
| 全部 36 测试 | pytest ✅ |

---

## Phase 5：排班生成与结果展示 ✅ 完成

**目标：** 需求/制约管理 + 排班生成可视化 + 结果展示 + 方案比较  
**完成日期：** 2026-07-12

### Step 1: 需求/制约/固定割当 API ✅

- [x] `api/routers/demands.py` — DailyDemand CRUD
  - GET /schedules/{id}/demands — 列表
  - POST /schedules/{id}/demands — 单日创建
  - POST /schedules/{id}/demands/batch — 一括设定（全期间统一 min/max）
  - DELETE /schedules/{id}/demands — 清除
- [x] `api/routers/constraints.py` — PersonConstraint CRUD
  - GET /constraints — 列表
  - GET /constraints/{id} — 详情
  - POST /constraints — 创建
  - PUT /constraints/{id} — 更新
  - DELETE /constraints/{id} — 删除
- [x] `api/routers/fixed_assignments.py` — FixedAssignment CRUD
  - GET /schedules/{id}/fixed-assignments — 列表
  - POST /schedules/{id}/fixed-assignments — 创建
  - DELETE /schedules/{id}/fixed-assignments/{aid} — 单个删除
  - DELETE /schedules/{id}/fixed-assignments — 全部清除
- [x] `api/main.py` — 新路由注册（demands, constraints, fixed_assignments）

### Step 2: 前端 API Client ✅

- [x] `web/src/api/demands.ts` — listDemands, batchSetDemands, clearDemands
- [x] `web/src/api/constraints.ts` — listConstraints, createConstraint, updateConstraint, deleteConstraint
- [x] `web/src/api/fixed-assignments.ts` — listFixedAssignments, createFixedAssignment, deleteFixedAssignment, clearFixedAssignments

### Step 3: 前端页面 ✅

- [x] `web/src/pages/constraints/ConstraintsPage.tsx` — 个人制约管理
  - メンバー選択 + 勤務日数(週/期間 min/max) + 勤務時間(週/期間) + 連続日数上限
  - 编辑/删除操作
- [x] `web/src/pages/schedules/ScheduleDetailPage.tsx` — スケジュール設定
  - 毎日の必要人数: 一括設定（min/max）+ クリア
  - 固定割当: メンバー/日付/タイプ(出勤/休み)/パターン 追加・削除
  - スケジュール生成ボタン + 結果を見る导航
- [x] `web/src/App.tsx` — 路由更新
  - /schedules/:id → ScheduleDetailPage（設定页）
  - /schedules/:id/result → ScheduleResultPage（結果页）
  - /constraints → ConstraintsPage
- [x] `web/src/components/AppLayout.tsx` — 侧边栏增加 Constraints 菜单

### Step 4: 端到端验证 ✅

- [x] DailyDemand batch API: 7日间 min=2/max=4 → 正确创建
- [x] PersonConstraint API: period_work_days 3~5 + max_consecutive_work 3 → 正确保存
- [x] 排班生成含需求: 5人x7天 → 15 WORK + 20 REST, health_score=100, 0.037s
- [x] 结果页面: Day Shift / Night Shift / REST 正确分配显示、Pattern 颜色渲染
- [x] TypeScript 编译通过（0 errors）

### Step 5: 日本語化 + UI改善 ✅

- [x] 全画面日本語化（Login, Patterns, Members, Constraints, Schedules, ScheduleDetail, ScheduleResult, AppLayout）
- [x] score_breakdown 可视化（Progress circle: 個人制約/グループ需要/毎日需要/均衡性 ペナルティ表示）
- [x] 生成中表示（LoadingOutlined + 「生成中...」ボタン disabled 状態）
- [x] 生成完了後の自動遷移（ポーリング2秒間隔 → 完了時に結果ページへ自動ナビゲート）

### Step 6: 違反レポート強化 ✅

- [x] `ScheduleResultPage.tsx` — 違反レポート全面リニューアル
  - Violation インターフェース更新（バックエンド Violation モデルと一致: constraint_group, target_member_id, target_date, contributing_factors, suggestions）
  - 制約種別の日本語ラベルマッピング（daily_demand_min → 毎日需要（最小）等 13種）
  - グループ別折りたたみ表示（Collapse: 個人制約/需要制約/グループ制約）
  - 展開可能行で因果分析表示（原因分析 + 改善提案）
  - 警告セクション追加（severity 別タグ表示）
- [x] 排班表をCardコンポーネントで整理

### Step 7: グループ管理 + グループ需要 ✅

- [x] `api/routers/groups.py` — Group + GroupDemand API
  - GET/POST/PUT/DELETE /groups — グループ CRUD
  - GET/POST/DELETE /schedules/{id}/group-demands — グループ需要管理
  - DELETE /schedules/{id}/group-demands — 全クリア
- [x] `api/schemas/common.py` — GroupDemandCreate/GroupDemandResponse 追加
- [x] `api/main.py` — groups ルーター登録
- [x] `web/src/api/groups.ts` — グループ + グループ需要 API クライアント
- [x] `web/src/pages/groups/GroupsPage.tsx` — グループ管理画面
  - グループ名 + メンバー多選択 + 編集/削除
- [x] `web/src/pages/schedules/ScheduleDetailPage.tsx` — グループ需要セクション追加
  - グループ/日付/パターン/最小人数 設定・表示・削除
- [x] `web/src/components/AppLayout.tsx` — サイドナビにグループメニュー追加（ApartmentOutlined アイコン）
- [x] `web/src/App.tsx` — /groups ルート追加

### Step 8: 三方案比較 + 日本語化 ✅

- [x] `api/routers/schedules.py` — POST /schedules/{id}/compare エンドポイント追加
  - ScenarioComparator を使い 3方案（均衡/人力優先/個人優先）を並列求解
  - 各方案の health_score, violations_count, score_breakdown を返却
- [x] `web/src/api/schedules.ts` — compareScenarios API + ScenarioSummary 型追加
- [x] `web/src/pages/schedules/ScheduleDetailPage.tsx` — 三方案比較 UI
  - 「三方案比較」ボタン → 3列カードで比較結果表示
  - 各方案: 健全スコア, 違反数, 求解時間, 個人/需要/均衡のペナルティバー
- [x] `solver_core/explain.py` — ExplainEngine 全テキスト日本語化
  - contributing_factors / suggestions の全メッセージを中国語→日本語に翻訳
- [x] `solver_core/scenario.py` — WeightProfile description 日本語化
- [x] 全20テスト通過確認

---

## Phase 6：导入导出 + 手机端 ✅ 完成

**目标：** Excel 支持 + 手机端レスポンシブ対応
**完成日期：** 2026-07-12

### Step 1: Excel エクスポート ✅

- [x] `api/services/export_excel.py` — 排班表 Excel 生成
  - 排班表シート: メンバー×日付の月間グリッド、Pattern 名+色、休み/週末色分け、曜日表示
  - 統計情報シート: 健全スコア、求解時間、スコア明細、メンバー別出勤/休息/労働時間集計
  - 違反レポートシート: 全違反の詳細（グループ/種別/優先度/メンバー/日付/設定値/実績値/原因分析/改善提案）
  - 警告シート: 警告一覧
- [x] `api/routers/schedules.py` — GET /schedules/{id}/export/excel エンドポイント
- [x] `web/src/api/schedules.ts` — exportExcel() Blob ダウンロード
- [x] `web/src/pages/schedules/ScheduleResultPage.tsx` — 「Excel出力」ボタン追加

### Step 2: Excel インポート ✅

- [x] `api/services/import_excel.py` — テンプレート生成 + Excel 解析
  - テンプレート: メンバー/個人制約/毎日需要の3シート、サンプルデータ付き
  - パーサー: メンバー名+パターン名、個人制約、毎日需要を解析
- [x] `api/routers/imports.py` — インポート API
  - GET /import/template — テンプレートダウンロード
  - POST /import/preview — アップロードプレビュー（新規/更新判定、警告表示）
  - POST /import/execute — インポート実行（メンバー作成/更新、個人制約設定）
- [x] `web/src/api/imports.ts` — downloadTemplate, previewImport, executeImport
- [x] `web/src/pages/members/MembersPage.tsx` — テンプレートDL + Excelインポートボタン + プレビューモーダル

### Step 3: レスポンシブ対応 ✅

- [x] `web/src/components/AppLayout.tsx` — モバイル対応レイアウト
  - PC: 固定サイドバー + スティッキーヘッダー
  - タブレット/モバイル: ハンバーガーメニュー + Drawer ナビ
  - 小画面でユーザー名非表示
  - CSS @media クエリによるブレークポイント（991px / 576px）

---

## Phase 7：休息希望流程 + 完善 ✅ 完成

**目标：** 个人用户休息希望完整流程  
**完成日期：** 2026-07-13  
**测试结果：** 36个测试全部通过，TypeScript 0 errors

### Step 1: 数据模型扩展 ✅

- [x] `api/models/rest_request.py` — RestDayRequest 模型
  - schedule_id, member_id, requested_dates(JSON), status(draft/submitted)
  - submitted_at, is_auto_submitted
- [x] `api/models/schedule.py` — Schedule 扩展
  - rest_request_deadline(Date), rest_request_max_days(Integer, default=3)
  - status: draft/requesting/running/completed/failed
- [x] `api/models/member.py` — personal_token(UUID, unique) 追加

### Step 2: 管理者用 REST API ✅

- [x] `api/routers/rest_requests.py` — 休み希望管理 API
  - GET /{schedule_id}/rest-requests — 全メンバーの希望一覧（名前付き）
  - PUT /{schedule_id}/rest-requests/{member_id} — 管理者によるメンバーの希望編集
  - POST /{schedule_id}/rest-requests/open — 受付開始（requesting状態、draft作成、トークン生成）
  - POST /{schedule_id}/rest-requests/close — 受付締切（自動提出 + P0 FixedAssignment作成 + draft復帰）

### Step 3: 個人用 API（トークン認証）✅

- [x] `api/routers/personal.py` — 個人アクセス API
  - 認証: ?token=xxx クエリパラメータ（JWT不要）
  - GET /personal/info — メンバー情報 + 対象スケジュール一覧
  - GET /personal/schedules/{id}/rest-request — 自分の希望詳細
  - PUT /personal/schedules/{id}/rest-request — 日付更新（max_days検証、提出後は変更不可）
  - POST /personal/schedules/{id}/rest-request/submit — 確定提出
  - GET /personal/schedules/{id}/my-schedule — 自分のスケジュール表示（completed時）

### Step 4: メンバートークン管理 ✅

- [x] `api/routers/members.py` — トークン管理エンドポイント追加
  - POST /{member_id}/token — トークン生成/再生成
  - GET /{member_id}/token — トークン取得

### Step 5: 管理者画面 — 休み希望受付 ✅

- [x] `web/src/api/rest-requests.ts` — 管理者用 API クライアント
- [x] `web/src/pages/schedules/ScheduleDetailPage.tsx` — 休み希望受付セクション
  - draft状態: 説明テキスト + 「休み希望受付を開始」ボタン
  - requesting状態: 受付中バッジ + 提出進捗 + メンバー別ステータス表 + 個人リンクモーダル + 「受付を締め切る」ボタン
  - 個人リンクモーダル: URL表示 + コピーボタン

### Step 6: 個人ページ（モバイル対応）✅

- [x] `web/src/api/personal.ts` — 個人 API クライアント（キャッシュバスティング付き）
- [x] `web/src/pages/personal/PersonalPage.tsx` — スマホ対応個人ページ
  - URL ベーストークン認証（/personal/:token）
  - メンバー名表示 + 対象スケジュール一覧
  - 受付中: 「休み希望を選択」→ カレンダーモーダル → 日付選択（max_days制限）→ 自動保存 → 確定提出
  - 提出済み: 提出済みタグ + 選択日表示
  - completed: 「マイスケジュールを見る」ボタン
  - max-width 480px、モバイルファーストレイアウト
- [x] `web/src/App.tsx` — /personal/:token ルート追加（ProtectedRoute外）

### Step 7: 締切処理 + P0連携 ✅

- [x] 受付締切時（close API）:
  - 全 draft → 自動 submitted（is_auto_submitted=true）
  - 各希望日 → FixedAssignment(type=rest) 自動生成
  - Schedule status → draft 復帰（生成可能状態）
- [x] 日付文字列→datetime.date変換の修正（FixedAssignment.date型対応）

### 已修复问题

| 问题 | 解决方案 |
|------|---------|
| ブラウザキャッシュで個人APIレスポンスが更新されない | personal.ts に `_t: Date.now()` キャッシュバスティング追加 |
| close API 500エラー（date型不一致） | `date_type.fromisoformat(str(d))` で文字列→date変換 |
| close API 500エラー（サーバー未リロード） | uvicorn プロセス再起動で解消 |
| 非ASCII文字のcurl JSON解析エラー | Python requests ライブラリに切替 |

---

## Phase 8：测试与上线 🔧 进行中

**目标：** 生产环境部署

### Step 1: 集成测试 ✅

- [x] `tests/test_api_integration.py` — 25个 API 集成测试
  - Demands CRUD + batch + tenant隔离
  - FixedAssignments CRUD + 全削除
  - Constraints CRUD
  - Groups + GroupDemands CRUD
  - 休み希望ライフサイクル（open → submit → close → FA生成）
  - 個人トークン認証（有効/無効/テナント境界）
  - 安全テスト（401未認証/無効JWT/期限切れトークン/二重提出/締切後提出）

### Step 2: 负荷测试 ✅

- [x] 100人×31日求解テスト → **22.7秒** ✅（目標300秒以内）
  - health_score=100, penalty=0

### Step 3: 安全审查 + 修正 ✅

- [x] SECRET_KEY 本番検証（ENV=production で未設定→RuntimeError）
- [x] CORS ミドルウェア追加（CORS_ORIGINS 環境変数で制御）
- [x] パスワード最低6文字バリデーション
- [x] ユーザー名空白バリデーション
- [x] 全サブリソースクエリに tenant_id 防御的フィルター追加
  - demands.py: DailyDemand の一覧/batch削除/クリアに tenant_id 条件追加
  - fixed_assignments.py: FixedAssignment の一覧/個別削除/全削除に tenant_id 条件追加
  - groups.py: GroupDemand の一覧/個別削除/全削除に tenant_id 条件追加

### Step 4: 手動テスト計画書 ✅

- [x] `MANUAL_TEST_PLAN.md` — 68項目の手動チェックリスト
  - 認証、パターン、メンバー、グループ、個人制約、スケジュール
  - 休み希望フロー（管理者側 + 個人ページ + 締切処理）
  - 排班生成 + 結果表示 + Excel出力 + 三方案比較
  - レスポンシブ、マルチテナント、エラーハンドリング

### Step 5: 部署 🔲

- [ ] 部署环境搭建（云服务选定、CI/CD）
- [ ] 操作手册

---

## 技术备忘

### 环境信息

- Python 3.12.3（Anaconda）
- ortools 9.15.6755
- pydantic 2.8.2, pytest 7.4.4
- FastAPI 0.139.0, Starlette 1.3.1, SQLAlchemy 2.x
- numpy 2.5.1, pandas 3.0.3, numexpr 2.14.1, bottleneck 1.6.0

### 已修复的问题

| 日期 | 问题 | 解决方案 |
|------|------|---------|
| 2026-07-11 | MultiStageSolver 第三阶段返回 MODEL_INVALID | 在 _apply_hints 开头加 clear_hints()，防止重复 hint |
| 2026-07-11 | pandas/numpy 版本冲突导致 ortools 加载警告 | 升级 pandas 到 3.0.3，警告不影响功能 |
| 2026-07-12 | 20人求解40秒超标 | 1) OPTIMAL后跳过后续stage 2) num_workers=1→8 → 降至1.4秒 |
| 2026-07-12 | numexpr/bottleneck 与 numpy 2.5.1 不兼容 | pip install --upgrade numexpr bottleneck |
| 2026-07-12 | TestClient 不触发 lifespan | 使用 `with TestClient(app) as client:` 模式 |
| 2026-07-12 | Base.metadata 为空导致 create_all 不建表 | main.py 改为 `from .models import Base`（触发全模型注册）|
| 2026-07-12 | 浏览器缓存导致 API 数据不刷新 | 后端 NoCacheMiddleware + 前端 axios Cache-Control: no-cache |
| 2026-07-12 | 排班结果全部 REST（无工作班次）| 原因: 无 DailyDemand 约束时 solver 最小化工作。解决: Phase 5 添加需求管理，设定 min_total 后正常出勤 |
| 2026-07-12 | 新增路由文件后 uvicorn --reload 未检测 | 需完全重启 uvicorn 进程（kill + restart），不能仅依赖 hot-reload |
| 2026-07-13 | 個人API(personal.ts)キャッシュ問題 | 独自 axios instance に `_t: Date.now()` キャッシュバスティング追加 |
| 2026-07-13 | close API で date 文字列→Date列の型不一致 | `date_type.fromisoformat(str(d))` で明示的変換 |

### 文件结构

```
shift_app/
├── solver_core/            ← Phase 1-2: 求解引擎（独立模块）
│   ├── __init__.py
│   ├── __main__.py
│   ├── models.py           ← 全 Pydantic 模型
│   ├── context.py          ← SolverContext
│   ├── constraints/        ← 11个约束实现
│   ├── compiler.py         ← CPSATCompiler
│   ├── manager.py          ← ConstraintManager
│   ├── feasibility.py      ← FeasibilityChecker
│   ├── solver.py           ← MultiStageSolver
│   ├── scoring.py          ← HealthScore 计算
│   ├── analyzer.py         ← ViolationAnalyzer
│   ├── explain.py          ← ExplainEngine
│   ├── scenario.py         ← ScenarioComparator
│   ├── engine.py           ← 主入口 solve()
│   ├── schema_input.json   ← Input JSON Schema
│   ├── schema_output.json  ← Output JSON Schema
│   └── README.md           ← 使用文档
├── api/                    ← Phase 3: Web API 层
│   ├── __init__.py
│   ├── main.py             ← FastAPI app + lifespan
│   ├── config.py           ← 配置（DB URL, JWT secret）
│   ├── database.py         ← Async engine + session
│   ├── deps.py             ← 依赖注入（auth, tenant）
│   ├── models/             ← SQLAlchemy 模型（13表）
│   │   ├── __init__.py     ← 全模型导出
│   │   ├── base.py         ← Base + Mixins
│   │   ├── tenant.py, user.py, member.py, pattern.py
│   │   ├── group.py, constraint.py, demand.py, schedule.py
│   ├── routers/            ← API 路由
│   │   ├── auth.py         ← register/login/me
│   │   ├── members.py      ← CRUD + トークン管理
│   │   ├── patterns.py     ← CRUD
│   │   ├── schedules.py    ← CRUD + generate + compare
│   │   ├── demands.py      ← DailyDemand CRUD + batch
│   │   ├── constraints.py  ← PersonConstraint CRUD
│   │   ├── fixed_assignments.py ← FixedAssignment CRUD
│   │   ├── groups.py       ← Group + GroupDemand CRUD
│   │   ├── imports.py      ← Excel インポート API
│   │   ├── rest_requests.py ← 休み希望管理（open/close/一覧/編集）
│   │   └── personal.py     ← 個人アクセス API（トークン認証）
│   ├── schemas/            ← Pydantic 请求/响应
│   │   ├── auth.py
│   │   └── common.py
│   └── services/           ← 业务逻辑
│       ├── auth.py         ← 注册/认证/JWT
│       ├── scheduler.py    ← DB→SolverInput + 排班执行
│       ├── export_excel.py ← Excel エクスポート生成
│       └── import_excel.py ← Excel インポート解析
├── web/                    ← Phase 4: 前端
│   ├── package.json
│   ├── vite.config.ts      ← API 代理配置
│   └── src/
│       ├── App.tsx          ← 路由 + AuthProvider
│       ├── api/             ← axios API clients (auth, members, patterns, schedules, demands, constraints, fixed-assignments, groups, imports, rest-requests, personal)
│       ├── store/auth.ts    ← AuthContext
│       ├── components/      ← AppLayout（レスポンシブ対応）
│       └── pages/           ← Login, Members(+インポート), Patterns, Constraints, Groups, Schedules, ScheduleDetail(+休み希望), ScheduleResult(+Excel出力), Personal(個人ページ)
├── tests/
│   ├── test_solver_basic.py    ← 8个 solver 端到端测试
│   ├── test_explain_scenario.py ← 5个 explain+scenario 测试
│   ├── test_performance.py     ← 3个性能基准测试
│   ├── test_edge_cases.py      ← 7个边界测试
│   ├── test_api.py             ← 13个 API 集成测试
│   └── data/basic_10.json
├── pyproject.toml
├── plan.md                 ← 设计文档（第5版）
└── PROGRESS.md             ← 本文件
```
