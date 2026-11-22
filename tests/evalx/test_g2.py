import json
from datetime import UTC, datetime

import polars as pl
import pytest

from kf.evalx.g2 import G2Result, g2_verdict, read_approvals
from kf.evalx.runner import scores_from
from kf.review.gate import Scores
from kf.review.review import Approval

NOW = datetime(2026, 6, 1, tzinfo=UTC)
PERSON = Approval("alice", "person", NOW)
S, K = Scores(4, 9, 0, 0), Scores(6, 9, 0, 0)


def verdict(starved=S, kb=K, approvals=(PERSON,), seal_ok=True, heldout=True) -> G2Result:
    return g2_verdict(starved, kb, approvals=list(approvals), seal_ok=seal_ok, heldout=heldout)


def test_g2_invalid_with_scripted_approval():
    v = verdict(approvals=[PERSON, Approval("t", "scripted", NOW)])
    assert not v.valid and not v.passed and any("scripted" in r for r in v.reasons)


def test_g2_invalid_when_seal_broken():
    assert not verdict(seal_ok=False).valid


def test_g2_invalid_on_curation_seeds():
    assert not verdict(heldout=False).valid


def test_g2_passes_at_plus_two():
    v = verdict()
    assert v.valid and v.passed


def test_g2_fails_at_plus_one():
    v = verdict(kb=Scores(5, 9, 0, 0))
    assert v.valid and not v.passed


def test_g2_fails_if_trap_rises():
    assert not verdict(kb=Scores(8, 9, 1, 0)).passed


def test_g2_fails_if_control_fp_rises():
    assert not verdict(kb=Scores(8, 9, 0, 1)).passed


def _line(**kw):
    return json.dumps(kw) + "\n"


def test_read_approvals_voids_merge_failed(tmp_path):
    p = tmp_path / "approvals.jsonl"
    p.write_text(
        _line(branch="kf/a", by="t", kind="scripted", role="approver", test_run=True, tier=1, at=NOW.isoformat())
        + _line(branch="kf/a", event="merge_failed", error="x")
        + _line(branch="kf/b", by="bob", kind="person", role="approver", test_run=False, tier=1, at=NOW.isoformat())
    )
    got = read_approvals(p)
    assert [(a.by, a.kind) for a in got] == [("bob", "person")]
    assert verdict(approvals=got).valid  # the voided scripted approval does not taint the verdict


def test_read_approvals_voids_only_the_preceding_attempt(tmp_path):
    p = tmp_path / "approvals.jsonl"
    rec = dict(role="approver", test_run=False, tier=1, at=NOW.isoformat())
    p.write_text(
        _line(branch="kf/a", by="bob", kind="person", **rec)  # earlier merged attempt stays
        + _line(branch="kf/b", by="t", kind="scripted", **rec)
        + _line(branch="kf/b", by="u", kind="scripted", **rec)  # two-approver attempt
        + _line(branch="kf/b", event="merge_failed", error="x")
    )
    assert [a.by for a in read_approvals(p)] == ["bob"]


def test_read_approvals_missing_file(tmp_path):
    assert read_approvals(tmp_path / "none.jsonl") == []


def _results(path, rows):
    path.mkdir(parents=True)
    pl.DataFrame(rows).write_parquet(path / "results.parquet")


def test_scores_from_sums_arm_over_seed_dirs(tmp_path):
    base = dict(arm="graph", run=0, top1=True, trap=False, control_false_positive=False)
    _results(tmp_path / "seed-21", [
        {**base, "scenario": "hero"}, {**base, "scenario": "hero", "run": 1, "top1": False, "trap": True},
        {**base, "scenario": "ctl", "arm": "graph_kb", "control_false_positive": True}])
    _results(tmp_path / "seed-22", [{**base, "scenario": "hero"}])
    assert scores_from(tmp_path, "graph") == Scores(top1=2, runs=3, trap=1, control_fp=0)
    assert scores_from(tmp_path, "graph_kb") == Scores(top1=1, runs=1, trap=0, control_fp=1)


def test_scores_from_unknown_arm_raises(tmp_path):
    _results(tmp_path / "s", [dict(scenario="hero", arm="graph", run=0, top1=True, trap=False,
                                   control_false_positive=False)])
    with pytest.raises(ValueError):
        scores_from(tmp_path, "nope")
