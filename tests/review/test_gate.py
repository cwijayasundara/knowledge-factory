from kf.review.gate import Scores, eval_gate


def test_gate_drop_beyond_tolerance_fails():
    r = eval_gate(Scores(7, 9, 0, 0), Scores(5, 9, 0, 0))
    assert not r.passed and any("top1" in x for x in r.reasons)


def test_gate_within_tolerance_passes():
    assert eval_gate(Scores(7, 9, 0, 0), Scores(6, 9, 0, 0)).passed


def test_gate_trap_rise_fails():
    r = eval_gate(Scores(7, 9, 0, 0), Scores(7, 9, 1, 0))
    assert not r.passed and any("trap" in x for x in r.reasons)


def test_gate_control_false_positive_rise_fails():
    r = eval_gate(Scores(7, 9, 0, 0), Scores(7, 9, 0, 1))
    assert not r.passed and any("control" in x for x in r.reasons)


def test_gate_tolerance_is_one_run_worth_of_scenarios():
    # tolerance_runs is counted in scenario-runs
    assert eval_gate(Scores(7, 9, 0, 0), Scores(4, 9, 0, 0), tolerance_runs=3).passed
    assert not eval_gate(Scores(7, 9, 0, 0), Scores(3, 9, 0, 0), tolerance_runs=3).passed


def test_gate_improvement_passes():
    assert eval_gate(Scores(5, 9, 1, 1), Scores(9, 9, 0, 0)).passed
