"""kf eval gate: graph_kb (starved) on the curation seeds, main vs the branch served as if approved;
scores and provenance land in the run record; kf review approve recomputes the gate from them."""

import json
import subprocess
from pathlib import Path

import polars as pl
import pytest

from kf import cli
from kf.evalx import gate_run
from kf.evalx.split import CURATION_SEEDS, HELDOUT_SEEDS
from kf.review.gate import GateResult

CONCEPT = ("---\ntitle: TMS\ndescription: d\nx-kf-review: proposed\ngenerated:\n  by: kf-curator/1\n"
           "  at: '2026-11-02T00:00:00Z'\n---\n# TMS\n")


NOW = "2026-11-20T00:00:00+00:00"


def git(repo, *a):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "bundle").mkdir(parents=True)
    (r / "bundle" / "index.md").write_text("# idx\n")
    git(r, "init", "-q", "-b", "main")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "seed")
    git(r, "checkout", "-q", "-b", "kf/c1")
    (r / "bundle" / "domain").mkdir()
    (r / "bundle" / "domain" / "tms.md").write_text(CONCEPT)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "curate")
    git(r, "checkout", "-q", "main")
    (r / "state" / "runs").mkdir(parents=True)
    (r / "state" / "runs" / "c1.json").write_text(json.dumps({"run_id": "c1", "status": "done", "decisions": []}))
    return r


class FakeEval:
    """Stands in for run_eval: records the call, writes results by side (top1 per side)."""

    def __init__(self, top1):
        self.top1, self.calls = top1, []

    def __call__(self, **kw):
        self.calls.append(kw)
        side = "head" if kw["snapshot"] else "base"
        d = Path(kw["run_dir"])
        d.mkdir(parents=True)
        pl.DataFrame([dict(scenario="hero", arm="graph_kb", run=i, top1=i < self.top1[side], trap=False,
                           control_false_positive=False) for i in range(3)]).write_parquet(d / "results.parquet")
        (d / "kf_run.json").write_text(json.dumps({"data_root": str(kw["data_root"])}))
        return d


def gate(repo, tmp_path, fake):
    return gate_run.run_gate(repo, "kf/c1", scenarios=["hero"], runs=3, state_dir=tmp_path / "st",
                             data_base=tmp_path, run=fake, now=NOW)


def test_gate_runs_curation_seeds_only_and_records_scores_with_provenance(repo, tmp_path):
    fake = FakeEval({"base": 2, "head": 3})
    assert gate(repo, tmp_path, fake).passed
    roots = [Path(c["data_root"]) for c in fake.calls]
    assert {r.parent.name for r in roots} == {"data_curation"}
    assert sorted({int(r.name.removeprefix("seed-")) for r in roots}) == sorted(CURATION_SEEDS)
    assert not {int(r.name.removeprefix("seed-")) for r in roots} & set(HELDOUT_SEEDS)
    assert all(c["starve"] and c["arms"] == ["graph_kb"] and c["own_flag_sink"] and not c["heldout"]
               for c in fake.calls)
    assert {c["now"] for c in fake.calls} == {NOW}  # one explicit clock for both sides
    rec = json.loads((repo / "state" / "runs" / "c1.json").read_text())
    assert rec["scores"]["base"]["top1"] == 6 and rec["scores"]["head"]["top1"] == 9
    g = rec["gate"]
    assert g["split"] == "curation" and g["base_commit"] == git(repo, "rev-parse", "main")
    assert g["head_commit"] == git(repo, "rev-parse", "kf/c1") and rec["decisions"] == []


def test_head_serves_the_branch_concepts_as_if_approved_in_a_copy_only(repo, tmp_path):
    fake = FakeEval({"base": 1, "head": 1})
    gate(repo, tmp_path, fake)
    head = {c["snapshot"] for c in fake.calls if c["snapshot"]}
    assert len(head) == 1
    snap = Path(head.pop())
    assert "x-kf-review: approved" in (snap / "domain" / "tms.md").read_text()
    from datetime import UTC, datetime

    from kf.bundle.serve import current_concepts
    assert "domain/tms.md" in [c.path for c in current_concepts(snap, now=datetime(2026, 12, 1, tzinfo=UTC))]
    assert "proposed" in git(repo, "show", "kf/c1:bundle/domain/tms.md")  # the branch is untouched
    plain = tmp_path / "st" / "snapshots" / git(repo, "rev-parse", "kf/c1")
    assert "x-kf-review: proposed" in (plain / "domain" / "tms.md").read_text()
    assert all(c["bundle_commit"] == git(repo, "rev-parse", "main") for c in fake.calls if not c["snapshot"])


def test_gate_fails_when_head_regresses(repo, tmp_path):
    assert not gate(repo, tmp_path, FakeEval({"base": 3, "head": 1})).passed


def test_gate_needs_a_curator_branch_with_a_run_record(repo, tmp_path):
    with pytest.raises(gate_run.GateError):
        gate_run.run_gate(repo, "main", scenarios=["hero"], runs=3, state_dir=tmp_path, data_base=tmp_path,
                          run=FakeEval({"base": 1, "head": 1}), now=NOW)
    (repo / "state" / "runs" / "c1.json").unlink()
    with pytest.raises(gate_run.GateError, match="no run record"):
        gate(repo, tmp_path, FakeEval({"base": 1, "head": 1}))


def test_gate_from_record(repo, tmp_path):
    assert gate_run.gate_from_record(repo, "kf/c1", {}) is None
    gate(repo, tmp_path, FakeEval({"base": 2, "head": 2}))
    rec = json.loads((repo / "state" / "runs" / "c1.json").read_text())
    assert gate_run.gate_from_record(repo, "kf/c1", rec) == GateResult(True, [])
    hand = {"scores": rec["scores"]}  # scores written by hand, no provenance
    assert not gate_run.gate_from_record(repo, "kf/c1", hand).passed
    git(repo, "checkout", "-q", "kf/c1")
    (repo / "bundle" / "x.md").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "later")
    git(repo, "checkout", "-q", "main")
    stale = gate_run.gate_from_record(repo, "kf/c1", rec)
    assert not stale.passed and any("moved since the gate" in r for r in stale.reasons)


def test_kf_eval_gate_cli(repo, tmp_path, monkeypatch, capsys):
    fake = FakeEval({"base": 2, "head": 3})
    monkeypatch.setattr(gate_run, "run_eval", fake)
    rc = cli.main(["eval", "gate", "--branch", "kf/c1", "--repo", str(repo), "--scenarios", "hero",
                   "--state-dir", str(tmp_path / "st"), "--data-base", str(tmp_path), "--now", NOW])
    assert rc == 0 and "gate PASS" in capsys.readouterr().out
    fake.top1 = {"base": 3, "head": 0}
    rc = cli.main(["eval", "gate", "--branch", "kf/c1", "--repo", str(repo), "--scenarios", "hero",
                   "--state-dir", str(tmp_path / "st2"), "--data-base", str(tmp_path), "--now", NOW])
    assert rc == 1 and "gate FAIL" in capsys.readouterr().out


@pytest.mark.parametrize("now", [None, "not-a-time"])
def test_gate_needs_one_explicit_iso_now(repo, tmp_path, now):
    fake = FakeEval({"base": 1, "head": 1})
    with pytest.raises(gate_run.GateError, match="--now"):
        gate_run.run_gate(repo, "kf/c1", scenarios=["hero"], runs=3, state_dir=tmp_path / "st",
                          data_base=tmp_path, run=fake, now=now)
    assert fake.calls == []


def test_kf_eval_gate_cli_refuses_without_now(repo, tmp_path, monkeypatch, capsys):
    fake = FakeEval({"base": 2, "head": 3})
    monkeypatch.setattr(gate_run, "run_eval", fake)
    rc = cli.main(["eval", "gate", "--branch", "kf/c1", "--repo", str(repo), "--scenarios", "hero",
                   "--state-dir", str(tmp_path / "st"), "--data-base", str(tmp_path)])
    assert rc == 2 and "--now" in capsys.readouterr().err and fake.calls == []
