import json
import os

import pytest

from kf.bundle.okf import load_concept
from kf.curator.guard import WriteDenied, WriteGuard
from kf.curator.tools import CuratorError, CuratorTools, build_curator_tools
from kf.flags.models import FlagStatus

from .conftest import git

REFUND = (
    "---\ntype: Definition\ntitle: Refund\ndescription: What a refund is.\nx-kf-kind: domain\n"
    "x-kf-owner: team:finance\nx-kf-confidence: medium\n---\n# Refund\n\n"
    "A refund is money returned to a customer for an order.\n"
)


@pytest.fixture
def tools(repo, queue, raw_dir, tmp_path):
    t = CuratorTools(repo, "kf/r1", queue, raw_dir, WriteGuard.default(), state_dir=tmp_path / "state")
    t.open_branch()
    return t


def test_open_branch_from_main(tools, repo):
    assert git(repo, "rev-parse", "kf/r1") == git(repo, "rev-parse", "main")
    assert (tools.worktree / "bundle" / "index.md").is_file()


def test_list_flags_quotes_flags_as_data_and_marks_triaged(tools, queue):
    out = json.loads(tools.list_flags())
    assert "untrusted" in out["note"].lower()
    assert [f["summary"] for f in out["flags"]] == ["no definition of refund"]
    assert queue.list()[0].status is FlagStatus.triaged
    assert tools.flags_in == [1]


def test_kb_write_sets_generated_and_proposed(tools):
    tools.list_flags()
    tools.raw_read("wiki/refunds.md")
    tools.decide("domain/refund.md", "ADD", "flag 1 asks for it", ["wiki/refunds.md"], "medium", [1])
    tools.kb_write("domain/refund.md", REFUND)
    c = load_concept(tools.worktree / "bundle" / "domain" / "refund.md")
    assert c.front["generated"]["by"].startswith("kf-curator/")
    assert c.front["x-kf-review"] == "proposed"
    assert c.front["x-kf-flags"] == [1]
    assert {"id": "wiki/refunds.md", "resource": "raw:wiki/refunds.md"} in c.front["sources"]
    assert "verified" not in c.front


def test_kb_write_never_adds_verified(tools):
    tools.raw_read("wiki/refunds.md")
    tools.decide("domain/refund.md", "ADD", "r", ["wiki/refunds.md"], "medium", [])
    with pytest.raises(WriteDenied):
        verified = "verified:\n- by: human:x\n  at: '2026-11-22T00:00:00Z'\n---\n# Refund"
        tools.kb_write("domain/refund.md", REFUND.replace("---\n# Refund", verified))
    assert not (tools.worktree / "bundle" / "domain" / "refund.md").exists()


def test_kb_edit_keeps_verified_history(tools):
    path = tools.worktree / "bundle" / "data_access" / "orders.md"
    before = load_concept(path).front["verified"]
    tools.raw_read("wiki/refunds.md")
    tools.decide("data_access/orders.md", "UPDATE", "r", ["wiki/refunds.md"], "high", [])
    tools.kb_edit("data_access/orders.md", "One row per order.", "One row per order; refunds are separate.")
    c = load_concept(path)
    assert c.front["verified"] == before
    assert "refunds are separate" in c.body
    with pytest.raises(WriteDenied):
        tools.kb_edit("data_access/orders.md", "by: human:alice", "by: kf-curator/1")


def test_no_delete_tool(tools):
    assert not hasattr(tools, "kb_delete")
    names = set(build_curator_tools(tools))
    assert names == {"list_flags", "update_flag_status", "kb_ls", "kb_grep", "kb_read", "raw_read", "decide",
                     "kb_write", "kb_edit", "regen_index", "run_validator", "open_branch",
                     "file_ontology_need"}


def test_unsourced_claim_becomes_escalate(tools, queue):
    tools.list_flags()
    d = json.loads(tools.decide("domain/refund.md", "ADD", "seems right", [], "medium", [1]))
    assert d["op"] == "ESCALATE"
    # a source the curator never read is no source
    d2 = json.loads(tools.decide("domain/refund.md", "ADD", "r", ["wiki/refunds.md"], "medium", [1]))
    assert d2["op"] == "ESCALATE"
    with pytest.raises(CuratorError):
        tools.kb_write("domain/refund.md", REFUND)
    f = queue.list()[0]
    assert f.status is FlagStatus.held and f.resolution["reason"] == "escalate"


def test_sourced_add_moves_flag_to_in_review_with_tier(tools, queue):
    tools.list_flags()
    tools.raw_read("wiki/refunds.md")
    d = json.loads(tools.decide("domain/refund.md", "ADD", "r", ["wiki/refunds.md"], "medium", [1]))
    assert (d["op"], d["tier"]) == ("ADD", 1)
    assert queue.list()[0].status is FlagStatus.in_review
    d = json.loads(tools.decide("data_access/orders.md", "DEPRECATE", "r", ["wiki/refunds.md"], "high", []))
    assert d["tier"] == 2


def test_decide_on_protected_target_escalates(tools):
    tools.raw_read("wiki/refunds.md")
    d = json.loads(tools.decide("../kf-profile.yaml", "UPDATE", "r", ["wiki/refunds.md"], "high", []))
    assert d["op"] == "ESCALATE"


@pytest.mark.parametrize(
    "p", ["../kf-profile.yaml", "computations/a.md", "../raw/x.json", "../../outside.md", "../AGENTS.md"])
def test_kb_write_outside_allowed_paths_denied(tools, p):
    with pytest.raises(WriteDenied):
        tools.kb_write(p, REFUND)


def test_raw_read_refuses_escape_and_answers(tools, raw_dir):
    (raw_dir / "_answers").mkdir()
    (raw_dir / "_answers" / "hero.json").write_text("{}")
    os.symlink(raw_dir / "_answers" / "hero.json", raw_dir / "wiki" / "link.json")
    for p in ["_answers/hero.json", "_Answers/hero.json", "_ANSWERS/HERO.JSON", "wiki/link.json",
              "../repo/bundle/index.md"]:
        with pytest.raises(WriteDenied):
            tools.raw_read(p)
    out = json.loads(tools.raw_read("wiki/refunds.md"))
    assert out["source_id"] == "wiki/refunds.md" and "untrusted" in out["note"].lower()


def test_kb_grep_skips_symlinks_out_of_bundle(tools, tmp_path):
    (tmp_path / "secret.md").write_text("SECRET-KEY\n")
    os.symlink(tmp_path / "secret.md", tools.worktree / "bundle" / "leak.md")
    os.symlink(tmp_path, tools.worktree / "bundle" / "leakdir")
    assert tools.kb_grep("SECRET") == "no matches"
    assert tools.kb_grep("Orders").startswith("data_access/orders.md:")


def test_update_flag_status_only_on_picked_flags(tools, queue):
    with pytest.raises(CuratorError):
        tools.update_flag_status(1, "declined", "noise")
    tools.list_flags()
    tools.update_flag_status(1, "declined", "noise")
    assert queue.list()[0].status is FlagStatus.declined
    with pytest.raises(CuratorError):
        tools.update_flag_status(1, "resolved", "merge only")


def test_regen_index_lists_concepts(tools):
    tools.regen_index()
    text = (tools.worktree / "bundle" / "index.md").read_text()
    assert "[Orders](data_access/orders.md)" in text and 'okf_version: "0.3"' in text


def test_wrapped_tool_returns_denial_as_text(tools):
    lc = build_curator_tools(tools)
    out = lc["kb_write"].invoke({"path": "../raw/x.json", "content": REFUND})
    assert out.startswith("error:")
