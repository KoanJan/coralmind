from .base import BasePlanStrategy, PlanAdviceAction, PlanRecord, PlanStrategyResult

__all__ = ["ThresholdStrategy"]


class ThresholdStrategy(BasePlanStrategy):
    """
    Two-threshold strategy
    """

    def __init__(self, s0: float = 8.5, s1: float = 9.5, c: int = 3):
        assert s0 < s1
        self.s0 = s0
        self.s1 = s1
        self.c = c

    def decide(self, records: list[PlanRecord]) -> PlanStrategyResult | None:
        records = [record for record in records if record.exec_times > 0]
        if len(records) == 0:
            return None
        if len(records) < self.c:
            return None
        best_old_plan = max(records, key=lambda v: v.total_score / v.exec_times)
        avg_score = best_old_plan.total_score / best_old_plan.exec_times
        if avg_score >= self.s1:
            return PlanStrategyResult(old_plan_id=best_old_plan.id, action=PlanAdviceAction.USE)
        elif avg_score >= self.s0:
            return PlanStrategyResult(old_plan_id=best_old_plan.id, action=PlanAdviceAction.BASE_ON)
        else:
            return None
