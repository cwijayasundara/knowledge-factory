import json
from pathlib import Path

import polars as pl
import pytest

from kf import cli
from kf.evalx import cli as evalx_cli
from kf.evalx import removal
from kf.evalx.runner import SealRefused


def _run_dir(p: Path, arm: str, top1: bool, *, starve: bool, heldout=True, test_run=False, seal_ok=True,
             seed=21, scenarios=("hero",), runs=3, returncode=0, rows=3, arm_rows=None):
    p.mkdir(parents=True)
    pl.DataFrame([dict(scenario="hero", arm=arm_rows or arm, run=i, top1=i < top1, trap=False,
                       control_false_positive=False) for i in range(rows)]).write_parquet(p / "results.parquet")
    (p / "kf_run.json").write_text(json.dumps(dict(
        commit="c" * 40, starve=starve, heldout=heldout, test_run=test_run, seal_ok=seal_ok,
        data_root=f"/x/data_heldout/seed-{seed}", scenarios=list(scenarios), runs=runs, returncode=returncode)))


def _setup(tmp_path, kb_kw=None, **kw):
    lst, seal = tmp_path / "removal.yaml", tmp_path / "removal.seal"
    lst.write_text("items: []\n")
    removal.seal(lst, seal)
    _run_dir(tmp_path / "s", "graph", 0, starve=True, **kw)
    _run_dir(tmp_path / "k", "graph_kb", 3, **{**kw, "starve": True, **(kb_kw or {})})
    return ["eval", "g2", "--starved", str(tmp_path / "s"), "--kb", str(tmp_path / "k"),
            "--state-dir", str(tmp_path / "state"), "--report", str(tmp_path / "g2.md"),
            "--list", str(lst), "--seal-file", str(seal)]


def test_g2_cli_writes_report_when_valid(tmp_path, capsys):
    assert cli.main(_setup(tmp_path)) == 0
    assert "PASS" in (tmp_path / "g2.md").read_text()


def test_g2_cli_accepts_a_starved_kb_run(tmp_path):
    assert cli.main(_setup(tmp_path)) == 0


def test_g2_cli_rejects_an_unstarved_kb_run(tmp_path, capsys):
    assert cli.main(_setup(tmp_path, kb_kw=dict(starve=False))) == 2
    assert "--kb holds a run that was not starved" in capsys.readouterr().err
    assert not (tmp_path / "g2.md").exists()


def test_g2_cli_rejects_an_unstarved_starved_run(tmp_path, capsys):
    argv = _setup(tmp_path)
    cfg = tmp_path / "s" / "kf_run.json"
    cfg.write_text(json.dumps({**json.loads(cfg.read_text()), "starve": False}))
    assert cli.main(argv) == 2
    assert "--starved holds a run that was not starved" in capsys.readouterr().err


def test_g2_cli_refuses_report_for_scripted_approval(tmp_path):
    argv = _setup(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "approvals.jsonl").write_text(json.dumps(
        dict(branch="kf/a", by="t", kind="scripted", at="2026-06-01T00:00:00+00:00")) + "\n")
    assert cli.main(argv) == 2 and not (tmp_path / "g2.md").exists()


@pytest.mark.parametrize("kw", [dict(heldout=False), dict(test_run=True), dict(seal_ok=False)])
def test_g2_cli_refuses_report_for_non_headline_runs(tmp_path, kw):
    assert cli.main(_setup(tmp_path, **kw)) == 2 and not (tmp_path / "g2.md").exists()


def test_g2_cli_refuses_when_seal_changed_after_run(tmp_path):
    argv = _setup(tmp_path)
    (tmp_path / "removal.yaml").write_text("items: []\n# edit\n")
    assert cli.main(argv) == 2 and not (tmp_path / "g2.md").exists()


def test_eval_run_maps_flags_onto_run_eval_per_heldout_seed(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    rc = cli.main(["eval", "run", "--arms", "graph,graph_kb", "--scenarios", "hero", "--runs", "2", "--starve",
                   "--heldout", "--test-run", "--bundle-commit", "abc", "--state-dir", str(tmp_path / "st"),
                   "--data-base", str(tmp_path)])
    assert rc == 0 and [c["data_root"].name for c in calls] == ["seed-21", "seed-22", "seed-23"]
    assert all(c["data_root"].parent.name == "data_heldout" for c in calls)
    assert calls[0]["arms"] == ["graph", "graph_kb"] and calls[0]["runs"] == 2 and calls[0]["starve"] is True
    assert calls[0]["heldout"] and calls[0]["test_run"] and calls[0]["bundle_commit"] == "abc"


def test_eval_run_defaults_to_curation_seeds(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    assert cli.main(["eval", "run", "--state-dir", str(tmp_path)]) == 0
    assert [c["data_root"].name for c in calls] == ["seed-11", "seed-12", "seed-13"]
    assert not calls[0]["heldout"]


def test_eval_run_reports_seal_refusal(tmp_path, monkeypatch):
    def refuse(**kw):
        raise SealRefused("nope")
    monkeypatch.setattr(evalx_cli, "run_eval", refuse)
    assert cli.main(["eval", "run", "--heldout", "--state-dir", str(tmp_path)]) == 2


def test_eval_metrics_prints_json(tmp_path, capsys):
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "index.md").write_text("# idx\n")
    assert cli.main(["eval", "metrics", "--state-dir", str(tmp_path / "st"), "--bundle", str(b)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["curator"]["flags"] == 0 and out["corpus"]["concepts"] == 0


@pytest.mark.parametrize("kb_kw,reason", [
    (dict(scenarios=("hero", "v-x")), "scenarios"),
    (dict(seed=22), "seeds"),
    (dict(runs=5), "runs-per-scenario"),
    (dict(returncode=1), "nonzero"),
    (dict(rows=2), "unequal scored runs"),
])
def test_g2_cli_invalid_when_runs_not_comparable(tmp_path, capsys, kb_kw, reason):
    assert cli.main(_setup(tmp_path, kb_kw=kb_kw)) == 2
    assert reason in capsys.readouterr().err and not (tmp_path / "g2.md").exists()


def test_g2_cli_missing_arm_is_invalid_not_a_traceback(tmp_path, capsys):
    assert cli.main(_setup(tmp_path, kb_kw=dict(arm_rows="graph"))) == 2
    assert "graph_kb" in capsys.readouterr().err
