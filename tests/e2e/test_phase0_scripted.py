"""Phase 0 end to end, scripted: no network model, no e2ekg data.

Two agent flags -> kf curate (scripted curator) -> branch kf/<run_id> -> kf ci on the branch ->
kf review approve --kind scripted --test-run merges -> flags resolved -> a second curate is a NOOP.
"""

import json
import subprocess
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from kf.agent_tools import make_kf_tools
from kf.bundle.ci import VALIDATOR
from kf.bundle.okf import load_concept
from kf.cli import main
from kf.curator.agent import run_curation
from kf.flags.models import FlagStatus
from kf.flags.queue import FlagQueue

from curator.fake_model import ScriptedChatModel, call, say

ROOT = Path(__file__).resolve().parents[2]
CONCEPT = "domain/severity/sev2.md"
OLD = "major impact on a key experience."
NEW = "major impact on a key experience, and the on-call rotation is paged."
SEV2 = (
    '---\ntype: Definition\ntitle: "SEV2"\ndescription: "SEV2 definition."\nx-kf-kind: domain\n'
    "x-kf-owner: team:incident-management\nx-kf-review: approved\nx-kf-confidence: high\n"
    "sources:\n  - id: seed\n    resource: https://example.com/severity\n"
    "generated:\n  by: seed/1\n  at: '2026-11-01T00:00:00Z'\n"
    "verified:\n  - by: human:alice\n    at: '2026-11-02T00:00:00Z'\n---\n"
    f"# SEV2\n\nSEV2 means {OLD}\n"
)
INDEX = '---\nokf_version: "0.3"\ntitle: B\ndescription: d\n---\n\n# Contents\n'


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(scope="module", autouse=True)
def okf_validator():
    if not VALIDATOR.is_file():
        subprocess.run(["bash", str(ROOT / "scripts" / "fetch_okf.sh")], capture_output=True)
    if not VALIDATOR.is_file():
        pytest.skip(f"OKF validator missing at {VALIDATOR} and scripts/fetch_okf.sh could not clone it")


@pytest.fixture
def world(tmp_path):
    repo = tmp_path / "repo"
    (repo / "bundle" / "domain" / "severity").mkdir(parents=True)
    (repo / "bundle" / "index.md").write_text(INDEX)
    (repo / "bundle" / CONCEPT).write_text(SEV2)
    git(repo, "init", "-q", "-b", "main")
    ident = ("-c", "user.name=t", "-c", "user.email=t@localhost")
    git(repo, *ident, "add", "-A")
    git(repo, *ident, "commit", "-q", "-m", "seed")
    raw = tmp_path / "raw"
    (raw / "wiki").mkdir(parents=True)
    (raw / "wiki" / "severity.md").write_text(f"SEV2 is {NEW}\n")
    return repo, raw, FlagQueue(tmp_path / "state" / "flags.db")


def curator_script() -> list[AIMessage]:
    return [
        call("list_flags"),
        call("kb_read", path=CONCEPT),
        call("raw_read", path="wiki/severity.md"),
        call("decide", target=CONCEPT, op="UPDATE", rationale="flags 1 and 2: SEV2 omits the page",
             sources=["wiki/severity.md"], confidence="high", flags=[1, 2]),
        call("kb_edit", path=CONCEPT, old=OLD, new=NEW),
        call("run_validator"),
        say("done"),
    ]


def judge() -> ScriptedChatModel:
    verdict = AIMessage(content="", tool_calls=[
        {"name": "JudgeVerdict", "args": {"supported": True, "unsupported": []}, "id": "j1"}])
    return ScriptedChatModel(model_name="scripted-judge", script=[verdict])


def test_phase0_scripted_end_to_end(world, tmp_path):
    repo, raw, queue = world

    # 1. an agent files two flags through its kf_flag tool
    flag = make_kf_tools(queue_path=queue.path, bundle_snapshot=repo / "bundle", run_id="eval-1",
                         agent_id="autorca", scenario="hero")["kf_flag"]
    for summary in ("SEV2 definition omits who is paged", "SEV2 page policy is missing"):
        assert "recorded" in flag.invoke({"kind": "incorrect", "summary": summary, "target": CONCEPT})
    assert [f.status for f in queue.list()] == [FlagStatus.open] * 2

    # 2. kf curate (scripted curator) proposes branch kf/e2e-1
    run = run_curation(repo=repo, queue=queue, raw_dir=raw, model=ScriptedChatModel(script=curator_script()),
                       run_id="e2e-1", judge_model=judge())
    assert (run.status, run.branch, run.judge_ok) == ("done", "kf/e2e-1", True)
    assert [(d.op, d.target) for d in run.decisions] == [("UPDATE", CONCEPT)]
    assert run.flags_out == {1: "in_review", 2: "in_review"}
    assert NEW in git(repo, "show", f"kf/e2e-1:bundle/{CONCEPT}") and NEW not in (repo / "bundle" / CONCEPT).read_text()

    # 3. kf ci passes on the branch (the tier-2 gate reads the scores the eval step recorded)
    wt = tmp_path / "branch-wt"
    git(repo, "worktree", "add", "-q", "--detach", str(wt), "kf/e2e-1")
    assert main(["ci", str(wt / "bundle")]) == 0
    git(repo, "worktree", "remove", "--force", str(wt))
    record = repo / "state" / "runs" / "e2e-1.json"
    rec = json.loads(record.read_text())
    same = dict(top1=5, runs=9, trap=0, control_fp=0)
    record.write_text(json.dumps({**rec, "scores": {"base": same, "head": same}}))

    # 4. a scripted approval on a --test-run merges, stamps verified and resolves the flags
    assert main(["review", "approve", "--repo", str(repo), "--branch", "kf/e2e-1", "--by", "scripted-test",
                 "--kind", "scripted", "--test-run", "--db", str(queue.path)]) == 0
    merged = load_concept(repo / "bundle" / CONCEPT)
    assert NEW in merged.body and merged.front["x-kf-review"] == "approved"
    assert {"by": "human:scripted-test"}.items() <= merged.front["verified"][-1].items()
    assert [f.status for f in queue.list()] == [FlagStatus.resolved] * 2
    approval = json.loads((repo / "state" / "approvals.jsonl").read_text().splitlines()[0])
    assert (approval["by"], approval["kind"], approval["test_run"]) == ("scripted-test", "scripted", True)
    assert git(repo, "log", "-1", "--format=%P").count(" ") == 1  # a --no-ff merge commit
    assert main(["ci", str(repo / "bundle")]) == 0

    # 5. a second curate with no new flags is a NOOP: no branch
    again = run_curation(repo=repo, queue=queue, raw_dir=raw, run_id="e2e-2",
                         model=ScriptedChatModel(script=[call("list_flags"), say("nothing to do")]))
    assert (again.status, again.branch, again.flags_in) == ("done", None, [])
    assert git(repo, "branch", "--list", "kf/*").split() == ["kf/e2e-1"]
