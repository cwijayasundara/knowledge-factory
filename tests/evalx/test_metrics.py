from datetime import UTC, datetime

from kf.evalx.metrics import corpus_metrics, curator_metrics, flag_recurrence
from kf.flags.models import FlagIn, FlagStatus
from kf.flags.queue import FlagQueue
from kf.review.review import Approval

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def _flag(q, n, status=None):
    f = q.add(FlagIn(kind="missing", summary=f"s{n}"), agent_id="a", run_id=f"r{n}", scenario="hero")
    for s in status or []:  # a merge resolves with {"merged": branch}, as review._resolve does
        q.set_status(f.id, s, resolution={"merged": "kf/x"} if s is FlagStatus.resolved else None)
    return f.id


RESOLVE = [FlagStatus.triaged, FlagStatus.in_review, FlagStatus.resolved]


def test_flag_recurrence_counts_reopened(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    a = _flag(q, 1, RESOLVE)
    _flag(q, 2, RESOLVE)  # resolved and stays resolved
    _flag(q, 3)  # never resolved
    assert flag_recurrence(q) == 0
    q.set_status(a, FlagStatus.open)
    assert flag_recurrence(q) == 1


def test_curator_metrics(tmp_path):
    q = FlagQueue(tmp_path / "q.db")
    _flag(q, 1, RESOLVE)
    _flag(q, 2, [FlagStatus.declined])
    _flag(q, 3, [FlagStatus.triaged, FlagStatus.held])
    _flag(q, 4)
    m = curator_metrics(q, [Approval("a", "person", NOW), Approval("t", "scripted", NOW)], rejections=1)
    assert m["flags"] == 4 and m["resolved"] == 1
    assert m["declined_share"] == 0.25 and m["held_share"] == 0.25
    assert m["approvals_person"] == 1 and m["approvals_scripted"] == 1
    assert m["review_acceptance_rate"] == 2 / 3 and m["flag_recurrence"] == 0


def test_curator_metrics_empty(tmp_path):
    m = curator_metrics(FlagQueue(tmp_path / "q.db"), [])
    assert m["flags"] == 0 and m["declined_share"] is None and m["review_acceptance_rate"] is None


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_corpus_metrics(tmp_path):
    b = tmp_path / "bundle"
    _write(b / "index.md", "# idx\n[a](domain/a.md)\n[b](domain/b.md)\n")
    _write(b / "domain/a.md", "---\ntitle: a\nsources: [raw/x.log]\nverified:\n- {by: 'human:al', at: '2026-01-01T00:00:00Z'}\n---\nsee [b](b.md) and [gone](gone.md)\n")
    _write(b / "domain/b.md", "---\ntitle: b\nstale_after: '2026-01-01T00:00:00Z'\n---\nbody\n")
    _write(b / "domain/c.md", "---\ntitle: c\n---\nlinked by nobody\n")
    m = corpus_metrics(b, NOW)
    assert m["concepts"] == 3
    assert m["citation_coverage"] == 1 / 3 and m["human_reviewed_ratio"] == 1 / 3
    assert m["stale_ratio"] == 1 / 3
    assert m["orphans"] == 1 and m["broken_links"] == 1
