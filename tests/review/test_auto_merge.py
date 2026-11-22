import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kf.bundle.okf import load_concept
from kf.cli import main
from kf.evalx.g2 import read_approval_records
from kf.review.review import CiFailed, ReviewRefused, _git, auto_merge_tier0

INDEX = '---\nokf_version: "0.3"\ntitle: B\ndescription: d\n---\n\n# Contents\n'


def orders(body="# Orders\n", extra="x-kf-usage: 1\n"):
    return (
        "---\ntype: Table\ntitle: Orders\ndescription: Orders table.\nx-kf-kind: data_access\n"
        "x-kf-owner: team:data\nx-kf-review: proposed\nx-kf-risk: 1\nx-kf-confidence: high\n"
        "sources:\n- resource: index.md\ngenerated:\n  by: kf-curator/1\n  at: '2026-11-21T00:00:00Z'\n"
        f"{extra}---\n{body}"
    )


def branch(repo: Path, name: str, files: dict[str, str]) -> None:
    _git(repo, "checkout", "-q", "-b", name, "main")
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change")
    _git(repo, "checkout", "-q", "main")


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.name", "T")
    _git(r, "config", "user.email", "t@example.invalid")
    (r / "bundle").mkdir()
    (r / "bundle" / "index.md").write_text(INDEX)
    (r / "bundle" / "orders.md").write_text(orders())
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "init")
    return r


def lines(repo):
    return [json.loads(x) for x in (repo / "state" / "approvals.jsonl").read_text().splitlines()]


def test_tier0_auto_merges_index_only_change(repo):
    branch(repo, "kf/r1", {"bundle/index.md": INDEX + "\n- [Orders](orders.md)\n"})
    res = auto_merge_tier0(repo, "kf/r1")
    assert res.merged and int(res.tier) == 0 and len(_git(repo, "log", "-1", "--format=%P").split()) == 2
    rec = lines(repo)[0]
    assert rec["kind"] == "auto" and rec["tier"] == 0 and rec["branch"] == "kf/r1"
    assert read_approval_records(repo / "state" / "approvals.jsonl") == []  # not an approval for g2/metrics


def test_tier0_merge_of_mechanical_frontmatter_never_stamps_verified(repo):
    branch(repo, "kf/r2", {"bundle/orders.md": orders(extra="x-kf-usage: 7\n")})
    assert auto_merge_tier0(repo, "kf/r2").merged
    front = load_concept(repo / "bundle" / "orders.md").front
    assert "verified" not in front and front["x-kf-review"] == "proposed"


def test_tier0_refuses_if_body_changed(repo):
    branch(repo, "kf/r3", {"bundle/index.md": INDEX + "\nmore\n", "bundle/orders.md": orders(body="# Orders\n\nNew.\n")})
    head = _git(repo, "rev-parse", "main")
    with pytest.raises(ReviewRefused, match="orders.md"):
        auto_merge_tier0(repo, "kf/r3")
    assert _git(repo, "rev-parse", "main") == head
    assert not (repo / "state" / "approvals.jsonl").exists()


def test_tier0_refuses_new_concept_and_empty_change(repo):
    branch(repo, "kf/r4", {"bundle/other.md": orders().replace("Orders", "Other")})
    with pytest.raises(ReviewRefused):
        auto_merge_tier0(repo, "kf/r4")
    _git(repo, "branch", "kf/r5", "main")
    with pytest.raises(ReviewRefused, match="nothing"):
        auto_merge_tier0(repo, "kf/r5")


def test_tier0_refuses_when_ci_fails(repo):
    branch(repo, "kf/r6", {"bundle/index.md": "no frontmatter\n"})
    with pytest.raises(CiFailed):
        auto_merge_tier0(repo, "kf/r6")


def test_cli_auto_merge(repo, capsys):
    branch(repo, "kf/r7", {"bundle/index.md": INDEX + "\nx\n"})
    assert main(["review", "auto-merge", "--repo", str(repo), "--branch", "kf/r7"]) == 0
    branch(repo, "kf/r8", {"bundle/orders.md": orders(body="# Orders\n\nNew.\n")})
    assert main(["review", "auto-merge", "--repo", str(repo), "--branch", "kf/r8"]) == 2


@pytest.mark.parametrize("rel", ["index.md", "log.md", "AGENTS.md", "kf-profile.yaml", "raw/x.json", "notes/other.md"])
def test_non_bundle_paths_refused(repo, rel):
    branch(repo, "kf/n", {rel: INDEX if rel.endswith(".md") else "x: 1\n"})
    head = _git(repo, "rev-parse", "main")
    with pytest.raises(ReviewRefused, match="outside bundle"):
        auto_merge_tier0(repo, "kf/n")
    assert _git(repo, "rev-parse", "main") == head


def test_non_bundle_identical_body_md_refused_and_mode_change(repo):
    (repo / "notes").mkdir()
    (repo / "notes" / "a.md").write_text(orders())
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "notes")
    branch(repo, "kf/same", {"notes/a.md": orders(extra="x-kf-usage: 9\n")})
    with pytest.raises(ReviewRefused, match="outside bundle"):
        auto_merge_tier0(repo, "kf/same")
    _git(repo, "checkout", "-q", "-b", "kf/mode", "main")
    (repo / "bundle" / "index.md").write_text(INDEX + "\nx\n")
    (repo / "bundle" / "orders.md").chmod(0o755)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "mode")
    _git(repo, "checkout", "-q", "main")
    with pytest.raises(ReviewRefused, match="mode"):
        auto_merge_tier0(repo, "kf/mode")


V = "verified:\n- by: human:alice\n  at: '2026-11-02T00:00:00Z'\n"


def reviewed(extra=""):
    return orders(extra="x-kf-usage: 1\n" + extra).replace("x-kf-review: proposed", "x-kf-review: approved")


@pytest.fixture
def reviewed_repo(repo):
    (repo / "bundle" / "orders.md").write_text(reviewed(V))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "reviewed")
    return repo


def test_usage_only_refresh_of_reviewed_concept_merges(reviewed_repo):
    branch(reviewed_repo, "kf/u", {"bundle/orders.md": reviewed(V).replace("x-kf-usage: 1", "x-kf-usage: 5")})
    assert auto_merge_tier0(reviewed_repo, "kf/u").merged


@pytest.mark.parametrize("name", ["generated", "verified", "status", "review"])
def test_trust_state_changes_refused(reviewed_repo, name):
    text = reviewed(V).replace("x-kf-usage: 1", "x-kf-usage: 2")
    text = {
        "generated": text.replace("2026-11-21T00:00:00Z", "2026-11-22T00:00:00Z"),
        "verified": text.replace("  at: '2026-11-02T00:00:00Z'\n", "  at: '2026-11-02T00:00:00Z'\n- by: human:bob\n  at: '2026-11-03T00:00:00Z'\n"),
        "status": text.replace("x-kf-risk: 1", "x-kf-risk: 1\nstatus: deprecated"),
        "review": text.replace("x-kf-review: approved", "x-kf-review: in_review"),
    }[name]
    branch(reviewed_repo, "kf/t", {"bundle/orders.md": text})
    with pytest.raises(ReviewRefused):
        auto_merge_tier0(reviewed_repo, "kf/t")
    assert not (reviewed_repo / "state" / "approvals.jsonl").exists()
