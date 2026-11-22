import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from kf.cli import main
from kf.curator import agent as agent_mod
from kf.curator.agent import run_curation, run_judge
from kf.curator.tools import CuratorTools
from kf.flags.models import FlagStatus

from .conftest import INJECTION, git
from .fake_model import ScriptedChatModel, call, say
from .test_tools import REFUND


def add_script():
    return [
        call("list_flags"),
        call("kb_read", path="index.md"),
        call("raw_read", path="wiki/refunds.md"),
        call("decide", target="domain/refund.md", op="ADD", rationale="flag 1: refund is undefined",
             sources=["wiki/refunds.md"], confidence="medium", flags=[1]),
        call("kb_write", path="domain/refund.md", content=REFUND),
        call("run_validator"),
        say("done"),
    ]


def judge(supported=True, name="scripted-judge"):
    verdict = AIMessage(content="", tool_calls=[
        {"name": "JudgeVerdict", "args": {"supported": supported, "unsupported": []}, "id": "j1"}])
    return ScriptedChatModel(model_name=name, script=[verdict])


def tool_texts(model):
    """Every tool result the model was shown, in order, across the main agent and its subagents."""
    seen, out = set(), []
    for msgs in model.calls:
        for m in msgs:
            if isinstance(m, ToolMessage) and m.tool_call_id not in seen:
                seen.add(m.tool_call_id)
                out.append(m.content)
    return out


def record(repo, run_id):
    return json.loads((repo / "state" / "runs" / f"{run_id}.json").read_text())


def test_curation_run_on_scripted_model_opens_branch_and_updates_flags(repo, queue, raw_dir):
    main_sha = git(repo, "rev-parse", "main")
    model = ScriptedChatModel(script=add_script())
    run = run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=model, run_id="r1", judge_model=judge())
    assert run.branch == "kf/r1" and run.flags_in == [1] and run.flags_out == {1: "in_review"}
    assert [d.op for d in run.decisions] == ["ADD"]
    assert git(repo, "rev-parse", "main") == main_sha
    assert "domain/refund.md" in git(repo, "show", "kf/r1:bundle/index.md")
    assert "## " in git(repo, "show", "kf/r1:bundle/log.md")
    assert queue.list()[0].status is FlagStatus.in_review
    rec = record(repo, "r1")
    assert (rec["status"], rec["branch"], rec["judge_ok"]) == ("done", "kf/r1", True)
    assert rec["model"] == "scripted-curator" and rec["judge_model"] == "scripted-judge"
    assert rec["decisions"][0]["sources"] == ["wiki/refunds.md"] and "scores" not in rec
    assert not (repo / "bundle" / "domain").exists()  # main's working tree untouched
    assert git(repo, "worktree", "list").count("\n") == 0  # the run's worktree is gone


def test_judge_rejection_is_recorded(repo, queue, raw_dir):
    run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=ScriptedChatModel(script=add_script()),
                 run_id="r1", judge_model=judge(supported=False))
    assert record(repo, "r1")["judge_ok"] is False


def test_judge_is_null_without_judge_model(repo, queue, raw_dir):
    run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=ScriptedChatModel(script=add_script()), run_id="r1")
    assert record(repo, "r1")["judge_ok"] is None


def test_same_model_judge_is_refused(repo, queue, raw_dir):
    with pytest.raises(ValueError):
        run_judge(ScriptedChatModel(), "diff", {"s": "x"}, curator_model=ScriptedChatModel())
    with pytest.raises(ValueError):
        run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model="fireworks:m1", run_id="r1",
                     judge_model="fireworks:m1")
    assert queue.list()[0].status is FlagStatus.open


def test_injection_flag_does_not_escape(repo, injected_queue, raw_dir):
    model = ScriptedChatModel(script=[
        call("list_flags"),
        call("kb_write", path="../raw/x.json", content="{}"),
        call("write_file", file_path="/raw/x.json", content="{}"),
        call("write_file", file_path="/kb/x.md", content="x"),
        call("delete", file_path="/kb/data_access/orders.md"),
        say("done"),
    ])
    run = run_curation(repo=repo, queue=injected_queue, raw_dir=raw_dir, model=model, run_id="r1")
    texts = tool_texts(model)
    assert texts[1].startswith("error:") and "denied" in texts[1].lower()
    assert all("error" in t.lower() or "denied" in t.lower() or "not a valid tool" in t.lower() for t in texts[2:])
    assert not (raw_dir / "x.json").exists() and not (repo / "raw").exists()
    assert run.branch is None and git(repo, "branch", "--list", "kf/*") == ""
    assert (repo / "bundle" / "data_access" / "orders.md").is_file()
    assert injected_queue.list()[0].status is FlagStatus.held


def test_flag_text_never_in_system_prompt_or_opening(repo, injected_queue, raw_dir):
    model = ScriptedChatModel(script=[call("list_flags"), say("done")])
    run_curation(repo=repo, queue=injected_queue, raw_dir=raw_dir, model=model, run_id="r1")
    first = model.calls[0]
    system = [m.content for m in first if isinstance(m, SystemMessage)]
    human = [m.content for m in first if isinstance(m, HumanMessage)]
    assert system and human
    assert not any(INJECTION in str(c) for c in system + human)
    assert any(INJECTION in t for t in tool_texts(model))


def test_ingest_helper_has_no_write_tools(repo, queue, raw_dir):
    model = ScriptedChatModel(script=[
        call("task", description="collect the open flags", subagent_type="ingest"),
        call("kb_write", path="domain/refund.md", content=REFUND),  # the helper's turn
        say("one flag about refunds"),
        say("done"),
    ])
    run = run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=model, run_id="r1")
    assert any("kb_write" in t and "not a valid tool" in t.lower() for t in tool_texts(model))
    assert run.branch is None
    assert set(agent_mod.INGEST_TOOLS) == {"list_flags", "kb_ls", "kb_grep", "kb_read", "raw_read"}


def test_escalate_records_need_and_holds_flag(repo, queue, raw_dir):
    need = "ontology need: no error template covers refund failures"
    model = ScriptedChatModel(script=[
        call("list_flags"),
        call("decide", target="ontology:RefundFailure", op="ESCALATE", rationale=need, sources=[],
             confidence="low", flags=[1]),
        say("done"),
    ])
    run = run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=model, run_id="r1")
    rec = record(repo, "r1")
    assert rec["decisions"][0]["op"] == "ESCALATE" and rec["decisions"][0]["rationale"] == need
    assert run.flags_out == {1: "held"} and queue.list()[0].resolution["reason"] == "escalate"


def test_crashed_run_is_cleaned_and_main_untouched(repo, queue, raw_dir, monkeypatch):
    main_sha = git(repo, "rev-parse", "main")

    def kb_edit(self, path: str, old: str, new: str) -> str:
        """Crashes mid-run."""
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(CuratorTools, "kb_edit", kb_edit)
    crash = add_script()[:5] + [call("kb_edit", path="domain/refund.md", old="A refund", new="Refund")]
    with pytest.raises(RuntimeError, match="disk on fire"):
        run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=ScriptedChatModel(script=crash), run_id="r1")
    assert record(repo, "r1")["status"] == "running"
    assert git(repo, "branch", "--list", "kf/r1") != ""
    assert git(repo, "rev-parse", "main") == main_sha
    monkeypatch.undo()

    run = run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=ScriptedChatModel(script=add_script()),
                       run_id="r2")
    assert git(repo, "branch", "--list", "kf/r1") == ""
    assert record(repo, "r1")["status"] == "failed"
    assert run.branch == "kf/r2" and run.flags_out == {1: "in_review"}
    assert git(repo, "rev-parse", "main") == main_sha
    assert git(repo, "merge-base", "main", "kf/r2") == main_sha
    assert not (repo / "bundle" / "domain").exists()


def test_dry_run_discards_branch_and_leaves_queue(repo, queue, raw_dir):
    run = run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=ScriptedChatModel(script=add_script()),
                       run_id="r1", dry_run=True)
    assert [d.op for d in run.decisions] == ["ADD"]
    assert git(repo, "branch", "--list", "kf/*") == ""
    assert queue.list()[0].status is FlagStatus.open
    assert not (repo / "state" / "runs" / "r1.json").exists()


def test_written_concept_passes_ci_on_branch(repo, queue, raw_dir):
    run_curation(repo=repo, queue=queue, raw_dir=raw_dir, model=ScriptedChatModel(script=add_script()), run_id="r1")
    rec = record(repo, "r1")
    assert rec["ci_issues"] == []


def test_cli_curate_passes_flags(repo, raw_dir, monkeypatch, capsys, tmp_path):
    seen = {}

    def fake_run(**kw):
        seen.update(kw)
        return agent_mod.CurationRun(branch=None, decisions=[], flags_in=[], flags_out={}, run_id="r9")

    monkeypatch.setattr(agent_mod, "run_curation", fake_run)
    rc = main(["curate", "--dry-run", "--repo", str(repo), "--raw-dir", str(raw_dir), "--run-id", "r9",
               "--judge-model", "fireworks:judge", "--db", str(tmp_path / "q.db")])
    assert rc == 0
    assert seen["dry_run"] is True and seen["model"] == agent_mod.DEFAULT_MODEL
    assert seen["judge_model"] == "fireworks:judge" and seen["run_id"] == "r9"
