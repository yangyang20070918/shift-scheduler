from .p0_fixed import P0FixedConstraint
from .p1a_forbidden import P1AForbiddenConstraint
from .p1b_chain import P1BChainConstraint
from .p2_weekly_days import P2WeeklyDaysConstraint
from .p3_period_days import P3PeriodDaysConstraint
from .p4_weekly_hours import P4WeeklyHoursConstraint
from .p5_period_hours import P5PeriodHoursConstraint
from .p6_consecutive_work import P6ConsecutiveWorkConstraint
from .p7_consecutive_rest import P7ConsecutiveRestConstraint
from .p8_group_demand import P8GroupDemandConstraint
from .p9_daily_demand import P9DailyDemandConstraint
from .p10_pattern_balance import P10PatternBalanceConstraint

ALL_CONSTRAINTS = [
    P0FixedConstraint,
    P1AForbiddenConstraint,
    P1BChainConstraint,
    P2WeeklyDaysConstraint,
    P3PeriodDaysConstraint,
    P4WeeklyHoursConstraint,
    P5PeriodHoursConstraint,
    P6ConsecutiveWorkConstraint,
    P7ConsecutiveRestConstraint,
    P8GroupDemandConstraint,
    P9DailyDemandConstraint,
    P10PatternBalanceConstraint,
]
