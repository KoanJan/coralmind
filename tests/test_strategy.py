import pytest

from coralmind.strategy.advising import ThresholdStrategy, PlanRecord, PlanAdviceAction


class TestThresholdStrategy:
    
    def test_init_default_values(self):
        strategy = ThresholdStrategy()
        assert strategy.s0 == 8.5
        assert strategy.s1 == 9.5
        assert strategy.c == 3
    
    def test_init_custom_values(self):
        strategy = ThresholdStrategy(s0=7.0, s1=9.0, c=5)
        assert strategy.s0 == 7.0
        assert strategy.s1 == 9.0
        assert strategy.c == 5
    
    def test_init_invalid_thresholds(self):
        with pytest.raises(AssertionError):
            ThresholdStrategy(s0=9.5, s1=8.5)
    
    def test_decide_insufficient_records(self):
        strategy = ThresholdStrategy(c=3)
        records = [
            PlanRecord(id=1, total_score=18, exec_times=2),
            PlanRecord(id=2, total_score=16, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is None
    
    def test_decide_no_records(self):
        strategy = ThresholdStrategy()
        result = strategy.decide([])
        assert result is None
    
    def test_decide_records_with_zero_exec_times(self):
        strategy = ThresholdStrategy(c=2)
        records = [
            PlanRecord(id=1, total_score=10, exec_times=0),
            PlanRecord(id=2, total_score=20, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is None
    
    def test_decide_use_action_high_score(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=2)
        records = [
            PlanRecord(id=1, total_score=28, exec_times=3),
            PlanRecord(id=2, total_score=18, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is not None
        assert result.old_plan_id == 1
        assert result.action == PlanAdviceAction.USE
    
    def test_decide_base_on_action_medium_score(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=2)
        records = [
            PlanRecord(id=1, total_score=17, exec_times=2),
            PlanRecord(id=2, total_score=14, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is not None
        assert result.old_plan_id == 1
        assert result.action == PlanAdviceAction.BASE_ON
    
    def test_decide_none_action_low_score(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=2)
        records = [
            PlanRecord(id=1, total_score=10, exec_times=2),
            PlanRecord(id=2, total_score=8, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is None
    
    def test_decide_selects_best_average_score(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=2)
        records = [
            PlanRecord(id=1, total_score=27, exec_times=3),
            PlanRecord(id=2, total_score=19, exec_times=2),
            PlanRecord(id=3, total_score=25, exec_times=3),
        ]
        result = strategy.decide(records)
        assert result is not None
        assert result.old_plan_id == 2
        assert result.action == PlanAdviceAction.USE
    
    def test_decide_exactly_at_s0_threshold(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=2)
        records = [
            PlanRecord(id=1, total_score=16, exec_times=2),
            PlanRecord(id=2, total_score=14, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is not None
        assert result.action == PlanAdviceAction.BASE_ON
    
    def test_decide_exactly_at_s1_threshold(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=2)
        records = [
            PlanRecord(id=1, total_score=18, exec_times=2),
            PlanRecord(id=2, total_score=16, exec_times=2),
        ]
        result = strategy.decide(records)
        assert result is not None
        assert result.action == PlanAdviceAction.USE
    
    def test_decide_minimum_records_for_use(self):
        strategy = ThresholdStrategy(s0=8.0, s1=9.0, c=3)
        records = [
            PlanRecord(id=1, total_score=28, exec_times=3),
            PlanRecord(id=2, total_score=27, exec_times=3),
            PlanRecord(id=3, total_score=26, exec_times=3),
        ]
        result = strategy.decide(records)
        assert result is not None
        assert result.action == PlanAdviceAction.USE
