from enum import IntEnum

from pydantic import BaseModel

__all__ = ["BasePlanStrategy", "PlanRecord", "PlanStrategyResult", "PlanAdviceAction"]


class PlanRecord(BaseModel):
    id: int
    total_score: int
    exec_times: int


class PlanAdviceAction(IntEnum):
    BASE_ON = 1
    USE = 2


class PlanStrategyResult:
    def __init__(self, old_plan_id: int, action: PlanAdviceAction):
        self.old_plan_id = old_plan_id
        self.action = action


class BasePlanStrategy:
    def decide(self, records: list[PlanRecord]) -> PlanStrategyResult | None:
        pass
