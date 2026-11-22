import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kf.cli import main
from kf.flags.models import FlagIn, FlagStatus
from kf.flags.queue import FlagQueue
from kf.bundle.okf import load_concept
from kf.review.gate import GateResult
from kf.review.review import (
    Approval,
    CiFailed,
    GateRequired,
    JudgeRequired,
    ScriptedNotAllowed,
    _git,
    approve_and_merge,
)

NOW = datetime(2026, 11, 22, tzinfo=UTC)
PASS = GateResult(True, [])
FAIL = GateResult(False, ["top1 dropped"])
INDEX = '---\nokf_version: "0.3"\ntitle: B\ndescription: d\n---\n\n# Contents\n'


def orders(flags: str = "") -> str:
    return (
        "---\ntype: Table\ntitle: Orders\ndescription: Orders table.\nx-kf-kind: data_access\n"
        "x-kf-owner: team:data\nx-kf-review: proposed\nx-kf-risk: 1\nx-kf-confidence: high\n"
        "sources:\n- resource: index.md\ngenerated:\n  by: kf-curator/1\n  at: '2026-11-21T00:00:00Z'\n"
        f"{flags}---\n# Orders\n"
    )


def commit_branch(repo: Path, branch: str, files: dict[str, str], base: str = "main") -> None:
    _git(repo, "checkout", "-q", "-b", branch, base)
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "curator change")
    _git(repo, "checkout", "-q", "main")


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.name", "Git Config Person")
    _git(r, "config", "user.email", "gitconfig@example.invalid")
    (r / "bundle").mkdir()
    (r / "bundle" / "index.md").write_text(INDEX)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "init")
    commit_branch(r, "kf/run-1", {"bundle/orders.md": orders(flags="x-kf-flags:\n- 1\n")})
    return r


@pytest.fixture
def q(tmp_path):
    queue = FlagQueue(tmp_path / "q.db")
    for s in ("one", "two"):
        f = queue.add(FlagIn(kind="stale", summary=s), agent_id="a", run_id="r", scenario="s")
        queue.set_status(f.id, FlagStatus.triaged)
        queue.set_status(f.id, FlagStatus.in_review)
    return queue


def person(by="alice"):
    return Approval(by, "person", NOW)


def go(repo, q, **kw):
    args = dict(approval=person(), test_run=False, gate=PASS, queue=q)
    args.update(kw)
    return approve_and_merge(repo, "kf/run-1", **args)


def write_run(repo: Path, **rec) -> None:
    (repo / "state" / "runs").mkdir(parents=True, exist_ok=True)
    (repo / "state" / "runs" / "run-1.json").write_text(json.dumps(rec))


def test_scripted_refused_outside_test_run(repo, q):
    with pytest.raises(ScriptedNotAllowed):
        go(repo, q, approval=Approval("scripted-test", "scripted", NOW))
    assert not (repo / "state" / "approvals.jsonl").exists()


def test_merge_stamps_verified_and_resolves_flags(repo, q):
    res = go(repo, q)
    assert res.merged
    c = load_concept(repo / "bundle" / "orders.md")
    assert c.front["verified"][0]["by"] == "human:alice"
    assert [f.status for f in q.list()] == [FlagStatus.resolved, FlagStatus.in_review]
    rec = json.loads((repo / "state" / "approvals.jsonl").read_text().splitlines()[0])
    assert rec["by"] == "alice" and rec["kind"] == "person" and rec["branch"] == "kf/run-1"


def test_merge_is_no_ff(repo, q):
    go(repo, q)
    parents = _git(repo, "log", "-1", "--format=%P", "main").split()
    assert len(parents) == 2


def test_ci_failure_blocks_merge(repo, q):
    commit_branch(repo, "kf/run-2", {"bundle/bad.md": orders().replace("x-kf-owner: team:data\n", "")})
    head = _git(repo, "rev-parse", "main")
    with pytest.raises(CiFailed):
        approve_and_merge(repo, "kf/run-2", approval=person(), test_run=False, gate=PASS, queue=q)
    assert _git(repo, "rev-parse", "main") == head


def test_gate_failure_blocks_tier1(repo, q):
    with pytest.raises(GateRequired):
        go(repo, q, gate=FAIL)
    with pytest.raises(GateRequired):
        go(repo, q, gate=None)


def test_approver_not_taken_from_git_config(repo, q):
    go(repo, q, approval=person("bob"))
    assert load_concept(repo / "bundle" / "orders.md").front["verified"][0]["by"] == "human:bob"
    assert "Git Config Person" not in str(load_concept(repo / "bundle" / "orders.md").front)


def test_scripted_in_test_run_stamps_scripted_test(repo, q):
    go(repo, q, approval=Approval("whoever", "scripted", NOW), test_run=True)
    assert load_concept(repo / "bundle" / "orders.md").front["verified"][0]["by"] == "human:scripted-test"
    rec = json.loads((repo / "state" / "approvals.jsonl").read_text().splitlines()[0])
    assert rec["kind"] == "scripted" and rec["test_run"] is True


def test_flags_resolved_only_for_named_ids(repo, q):
    go(repo, q)
    one, two = q.list()
    assert one.status == FlagStatus.resolved and two.status == FlagStatus.in_review


def test_tier2_single_approver_needs_judge_ok(repo, q):
    _git(repo, "branch", "-D", "kf/run-1")
    commit_branch(repo, "kf/run-1", {"bundle/orders.md": orders().replace("confidence: high", "confidence: low")})
    with pytest.raises(JudgeRequired):
        go(repo, q)
    write_run(repo, judge_ok=False)
    with pytest.raises(JudgeRequired):
        go(repo, q)
    write_run(repo, judge_ok=True)
    assert go(repo, q).merged


def test_tier2_second_approval_path(repo, q):
    _git(repo, "branch", "-D", "kf/run-1")
    commit_branch(repo, "kf/run-1", {"bundle/orders.md": orders().replace("confidence: high", "confidence: low")})
    with pytest.raises(JudgeRequired):
        go(repo, q, second_approval=person("alice"))  # same approver does not count
    assert go(repo, q, second_approval=person("carol")).merged
    lines = (repo / "state" / "approvals.jsonl").read_text().splitlines()
    assert [json.loads(x)["by"] for x in lines] == ["alice", "carol"]


def test_tier0_needs_no_approval_but_ci(repo, q):
    commit_branch(repo, "kf/run-3", {"bundle/log.md": "# Log\n\n- entry\n"})
    res = approve_and_merge(repo, "kf/run-3", approval=None, test_run=False, gate=None, queue=q)
    assert res.merged and res.tier == 0
    assert not (repo / "state" / "approvals.jsonl").exists()


def test_cli_approve_and_scripted_refusal(repo, q, tmp_path, capsys):
    db = str(tmp_path / "q.db")
    base = ["review", "approve", "--repo", str(repo), "--db", db, "--branch", "kf/run-1", "--by", "x"]
    write_run(repo, gate={"passed": True, "reasons": []})
    assert main([*base, "--kind", "scripted"]) == 2
    assert main(["review", "list", "--repo", str(repo)]) == 0
    assert "kf/run-1" in capsys.readouterr().out
    assert main([*base, "--by", "alice"]) == 0
    assert load_concept(repo / "bundle" / "orders.md").front["verified"][0]["by"] == "human:alice"
