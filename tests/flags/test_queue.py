import pytest

from kf.flags.models import FlagIn, FlagStatus
from kf.flags.queue import FlagQueue, FlagRateLimited, InvalidTransition
from pydantic import ValidationError


def _add(q, summary="x", run_id="r", **kw):
    return q.add(FlagIn(kind="stale", summary=summary, **kw), agent_id="a", run_id=run_id, scenario="hero")


def test_add_attaches_handler_fields(tmp_path):
    f = FlagQueue(tmp_path / "q.db").add(
        FlagIn(kind="stale", summary="x"), agent_id="autorca", run_id="r1", scenario="hero"
    )
    assert (f.id, f.status, f.agent_id, f.run_id) == (1, FlagStatus.open, "autorca", "r1")


def test_rate_limit_per_run(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    for i in range(20):
        q.add(FlagIn(kind="missing", summary=f"s{i}"), agent_id="a", run_id="r", scenario="hero")
    with pytest.raises(FlagRateLimited):
        q.add(FlagIn(kind="missing", summary="s20"), agent_id="a", run_id="r", scenario="hero")
    # another run is unaffected
    assert _add(q, "s20", run_id="r2").id == 21


def test_duplicate_in_run_returns_existing(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    a = _add(q, target="t")
    b = _add(q, target="t")
    assert a.id == b.id
    assert len(q.list()) == 1
    assert _add(q, target="t", run_id="r2").id != a.id


def test_summary_over_500_rejected():
    with pytest.raises(ValidationError):
        FlagIn(kind="stale", summary="x" * 501)


def test_evidence_and_resolution_roundtrip(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    f = _add(q, evidence=[{"ref": "raw/a.txt", "excerpt": "e"}])
    assert q.list()[0].evidence[0].ref == "raw/a.txt"
    q.set_status(f.id, FlagStatus.triaged, cluster_id=3)
    g = q.set_status(f.id, FlagStatus.declined, resolution={"why": "n/a"})
    assert (g.cluster_id, g.resolution) == (3, {"why": "n/a"})


def test_list_filters_by_status(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    a, _ = _add(q, "a"), _add(q, "b")
    q.set_status(a.id, FlagStatus.held)
    assert [f.summary for f in q.list(FlagStatus.held)] == ["a"]
    assert len(q.list()) == 2


def test_transitions(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    f = _add(q)
    with pytest.raises(InvalidTransition):
        q.set_status(f.id, FlagStatus.resolved)
    q.set_status(f.id, FlagStatus.triaged)
    q.set_status(f.id, FlagStatus.in_review)
    q.set_status(f.id, FlagStatus.resolved)
    assert q.set_status(f.id, FlagStatus.open).status == FlagStatus.open
    with pytest.raises(InvalidTransition):
        q.set_status(f.id, FlagStatus.in_review)
