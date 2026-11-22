from datetime import UTC, datetime

import pytest

from kf import agent_tools


@pytest.fixture(autouse=True)
def _no_kf_now(monkeypatch):
    """A KF_NOW from the caller's shell (an eval env) must not leak into these tests."""
    monkeypatch.delenv("KF_NOW", raising=False)


def test_utcnow_defaults_to_the_clock(monkeypatch):
    monkeypatch.delenv("KF_NOW", raising=False)
    assert abs((agent_tools.utcnow() - datetime.now(UTC)).total_seconds()) < 5


def test_utcnow_uses_kf_now_when_set(monkeypatch):
    monkeypatch.setenv("KF_NOW", "2026-06-01T12:00:00Z")
    assert agent_tools.utcnow() == datetime(2026, 6, 1, 12, tzinfo=UTC)


def test_utcnow_assumes_utc_for_naive_kf_now(monkeypatch):
    monkeypatch.setenv("KF_NOW", "2026-06-01T12:00:00")
    assert agent_tools.utcnow() == datetime(2026, 6, 1, 12, tzinfo=UTC)


def test_kb_tools_use_kf_now_for_staleness(tmp_path, monkeypatch):
    b = tmp_path / "b" / "domain"
    b.mkdir(parents=True)
    (b / "a.md").write_text("---\ntitle: a\nstale_after: '2026-03-01T00:00:00Z'\n---\nalias tms\n")
    t = agent_tools.make_kf_tools(queue_path=tmp_path / "q.db", bundle_snapshot=tmp_path / "b", run_id="r",
                                  agent_id="x", scenario="hero")
    monkeypatch.setenv("KF_NOW", "2026-02-01T00:00:00Z")
    assert "domain/a.md" in t["kb_search"].invoke({"query": "tms"})
    monkeypatch.setenv("KF_NOW", "2026-04-01T00:00:00Z")
    assert "domain/a.md" not in t["kb_search"].invoke({"query": "tms"})
