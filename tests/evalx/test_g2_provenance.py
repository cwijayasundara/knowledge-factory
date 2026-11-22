"""R1: g2 credits the seed->kb bundle difference to the curator only when every change arrived through a
reviewed curator merge (kf/<run_id> with a run record and an approval line), never a direct commit."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kf.evalx.g2 import pristine_problems
from kf.flags.queue import FlagQueue
from kf.review.gate import GateResult
from kf.review.review import Approval, _git, approve_and_merge, auto_merge_tier0

NOW = datetime(2026, 11, 22, tzinfo=UTC)
INDEX = '---\nokf_version: "0.3"\ntitle: B\ndescription: d\n---\n\n# Contents\n'


def concept(title="Orders", by="kf-curator/1") -> str:
    return (
        f"---\ntype: Table\ntitle: {title}\ndescription: {title} table.\nx-kf-kind: data_access\n"
        "x-kf-owner: team:data\nx-kf-review: proposed\nx-kf-risk: 1\nx-kf-confidence: high\n"
        f"sources:\n- resource: index.md\ngenerated:\n  by: {by}\n  at: '2026-11-21T00:00:00Z'\n---\n# {title}\n"
    )


def branch(repo: Path, name: str, files: dict[str, str]) -> None:
    _git(repo, "checkout", "-q", "-b", name, "main")
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change")
    _git(repo, "checkout", "-q", "main")


def direct(repo: Path, files: dict[str, str], msg="direct") -> str:
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def record(repo: Path, run_id: str, head: str | None = None) -> None:
    """The run record with the gate provenance kf eval gate writes (head_commit: the branch tip gated)."""
    (repo / "state" / "runs").mkdir(parents=True, exist_ok=True)
    head = head or _git(repo, "rev-parse", f"refs/heads/kf/{run_id}")
    (repo / "state" / "runs" / f"{run_id}.json").write_text(json.dumps(
        {"run_id": run_id, "status": "done", "gate": {"split": "curation", "head_commit": head}}))


def merge(repo: Path, name: str, tmp: Path) -> str:
    approve_and_merge(repo, name, approval=Approval("alice", "person", NOW), test_run=False,
                      gate=GateResult(True, []), queue=FlagQueue(tmp / "q.db"))
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.name", "P")
    _git(r, "config", "user.email", "p@example.invalid")
    (r / ".gitignore").write_text("state/\n")
    (r / "bundle").mkdir()
    (r / "bundle" / "index.md").write_text(INDEX)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "seed")
    return r


def seed(repo):
    return _git(repo, "rev-parse", "HEAD")


def check(repo, s, k):
    return pristine_problems(repo, s, k, state_dir=repo / "state")


def test_a_legit_curator_merge_passes(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    k = merge(repo, "kf/run-1", tmp_path)
    assert check(repo, s, k) == []


def test_a_direct_commit_to_main_touching_a_concept_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    merge(repo, "kf/run-1", tmp_path)
    k = direct(repo, {"bundle/orders.md": concept().replace("# Orders", "# Orders\nhand edit")})
    problems = check(repo, s, k)
    assert any(k[:12] in p and "bundle/orders.md" in p for p in problems), problems


def test_a_direct_commit_touching_only_non_bundle_files_passes(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    merge(repo, "kf/run-1", tmp_path)
    k = direct(repo, {"docs/notes.md": "notes\n"})
    assert check(repo, s, k) == []


def test_a_hand_edited_concept_merged_from_a_non_kf_branch_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "human/edit", {"bundle/orders.md": concept()})
    _git(repo, "merge", "--no-ff", "-q", "-m", "merge human/edit", "human/edit")
    k = _git(repo, "rev-parse", "HEAD")
    problems = check(repo, s, k)
    assert any(k[:12] in p and "kf/" in p for p in problems), problems


def test_a_non_curator_concept_inside_a_kf_merge_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept(by="human:alice")})
    record(repo, "run-1")
    k = merge(repo, "kf/run-1", tmp_path)
    problems = check(repo, s, k)
    assert any("bundle/orders.md" in p and "kf-curator" in p for p in problems), problems


def test_a_kf_merge_without_a_run_record_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    k = merge(repo, "kf/run-1", tmp_path)
    (repo / "state" / "runs" / "run-1.json").unlink()
    assert any("run record" in p for p in check(repo, s, k))


def test_a_kf_merge_without_an_approval_line_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    k = merge(repo, "kf/run-1", tmp_path)
    (repo / "state" / "approvals.jsonl").write_text("")
    assert any("approval" in p for p in check(repo, s, k))


def test_a_hand_merge_with_the_review_message_but_no_stamp_or_approval_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    _git(repo, "merge", "--no-ff", "-q", "-m", "merge kf/run-1 (tier 1)", "kf/run-1")
    assert check(repo, s, _git(repo, "rev-parse", "HEAD"))


def test_a_tier0_auto_merge_passes(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    merge(repo, "kf/run-1", tmp_path)
    text = (repo / "bundle" / "orders.md").read_text()
    branch(repo, "kf/run-2", {"bundle/orders.md": text.replace("---\n# Orders", "x-kf-usage: 3\n---\n# Orders")})
    record(repo, "run-2")
    auto_merge_tier0(repo, "kf/run-2")
    assert check(repo, s, _git(repo, "rev-parse", "HEAD")) == []


def test_the_seed_must_be_an_ancestor(repo, tmp_path):
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    _git(repo, "checkout", "-q", "kf/run-1")
    other = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "main")
    k = direct(repo, {"docs/x.md": "x\n"})
    assert any("not an ancestor" in p for p in check(repo, other, k))


def test_a_hand_merge_of_another_branch_reusing_an_approval_fails(repo, tmp_path):
    """Case A: kf/run-1 was approved; a hand merge of a different branch with kf/run-1's subject reuses it."""
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    merge(repo, "kf/run-1", tmp_path)
    branch(repo, "other", {"bundle/items.md": concept("Items")})
    _git(repo, "merge", "--no-ff", "-q", "-m", "merge kf/run-1 (tier 1)", "other")
    k = _git(repo, "rev-parse", "HEAD")
    problems = check(repo, s, k)
    assert any(k[:12] in p for p in problems), problems


def test_a_merge_whose_tip_is_not_the_gated_head_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1", head="0" * 40)
    k = merge(repo, "kf/run-1", tmp_path)
    assert any("gate" in p and "head" in p for p in check(repo, s, k))


def test_a_lookalike_curator_actor_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept(by="kf-curatorX/1")})
    record(repo, "run-1")
    k = merge(repo, "kf/run-1", tmp_path)
    assert any("kf-curatorX" in p for p in check(repo, s, k))


def test_a_legit_deletion_by_a_kf_branch_passes(repo, tmp_path):
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    merge(repo, "kf/run-1", tmp_path)
    s = _git(repo, "rev-parse", "HEAD")  # a seed holding a (non-curator) concept the next branch deletes
    _git(repo, "checkout", "-q", "-b", "kf/run-2", "main")
    _git(repo, "rm", "-q", "bundle/orders.md")
    _git(repo, "commit", "-q", "-m", "delete")
    _git(repo, "checkout", "-q", "main")
    record(repo, "run-2")
    # review.py refuses tier 3 (removal) on kf/*, so the merge and its approval line are written the way
    # approve_and_merge writes them (no stamp commit: nothing left to stamp).
    _git(repo, "merge", "--no-ff", "-q", "-m", "merge kf/run-2 (tier 3)", "kf/run-2")
    with (repo / "state" / "approvals.jsonl").open("a") as f:
        f.write(json.dumps({"branch": "kf/run-2", "by": "alice", "kind": "person", "role": "approver",
                            "test_run": False, "tier": 3, "at": NOW.isoformat()}) + "\n")
    k = _git(repo, "rev-parse", "HEAD")
    assert [p for p in check(repo, s, k) if "pristine" not in p] == []


def test_an_auto_merge_of_a_different_tip_fails(repo, tmp_path):
    s = seed(repo)
    branch(repo, "kf/run-1", {"bundle/orders.md": concept()})
    record(repo, "run-1")
    merge(repo, "kf/run-1", tmp_path)
    text = (repo / "bundle" / "orders.md").read_text()
    branch(repo, "kf/run-2", {"bundle/orders.md": text.replace("---\n# Orders", "x-kf-usage: 3\n---\n# Orders")})
    record(repo, "run-2")
    auto_merge_tier0(repo, "kf/run-2")
    lines = (repo / "state" / "approvals.jsonl").read_text().splitlines()
    auto = json.loads(lines[-1])
    assert auto["kind"] == "auto" and auto["tip"] == _git(repo, "rev-parse", "kf/run-2")
    lines[-1] = json.dumps({**auto, "tip": "0" * 40})
    (repo / "state" / "approvals.jsonl").write_text("\n".join(lines) + "\n")
    assert any("tip" in p for p in check(repo, s, _git(repo, "rev-parse", "HEAD")))
