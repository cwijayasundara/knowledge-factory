import json
import subprocess
from pathlib import Path

import polars as pl
import pytest

from kf import cli
from kf.evalx import cli as evalx_cli
from kf.evalx import removal
from kf.evalx.runner import SealRefused

LIST = 'items:\n  - id: a\n    file: prompts/autorca.md\n    match: "alias hint"\n    why_derivable_from: catalog\n'
SEED = "---\ntitle: S\ngenerated:\n  by: seed/1\n  at: '2026-11-01T00:00:00Z'\n---\n# S\n"
CURATED = ("---\ntitle: C\ngenerated:\n  by: kf-curator/1\n  at: '2026-11-02T00:00:00Z'\n"
           "verified:\n- by: human:{who}\n  at: '2026-11-03T00:00:00Z'\n---\n# C\n")
UNSTAMPED = ("---\ntitle: C\ngenerated:\n  by: kf-curator/1\n  at: '2026-11-02T00:00:00Z'\n---\n# C\n")
LATER = "2099-01-01T00:00:00+00:00"
CLOCK = "2026-11-20T00:00:00+00:00"


def git(cwd, *a):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class World:
    """A bundle repo (seed commit, committed seal, curated commit), the list outside it, snapshots."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.repo = tmp / "repo"
        (self.repo / "bundle").mkdir(parents=True)
        (self.repo / "bundle" / "a.md").write_text(SEED)
        git(self.repo, "init", "-q", "-b", "main")
        self.commit_all("seed")
        self.seed = git(self.repo, "rev-parse", "HEAD")
        self.list = tmp / "removal.yaml"
        self.list.write_text(LIST)
        self.seal = self.repo / "integration" / "removal.seal"
        removal.seal(self.list, self.seal, author="olive")
        self.commit_all("seal")
        # As kf review merges: the curator's commit (gated), a kf-review stamp commit, merge --no-ff.
        git(self.repo, "checkout", "-q", "-b", "kf/a")
        (self.repo / "bundle" / "c.md").write_text(UNSTAMPED)
        self.commit_all("curated")
        gated = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "bundle" / "c.md").write_text(CURATED.format(who="alice"))
        git(self.repo, "add", "-A")
        subprocess.run(["git", "-c", "user.name=kf-review", "-c", "user.email=kf-review@localhost", "commit", "-q",
                        "-m", "review: stamp verified by human:alice"], cwd=self.repo, check=True)
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "--no-ff", "-q", "-m", "merge kf/a (tier 1)", "kf/a")
        self.kb = git(self.repo, "rev-parse", "HEAD")
        (tmp / "state" / "runs").mkdir(parents=True)
        (tmp / "state" / "runs" / "a.json").write_text(json.dumps(
            {"run_id": "a", "status": "done", "gate": {"split": "curation", "head_commit": gated}}))
        self.sha = removal.digest(self.list)
        self.snap = {}
        for name, files in (("kb", {"a.md": SEED, "c.md": CURATED.format(who="alice")}), ("seed", {"a.md": SEED})):
            d = tmp / f"snap-{name}"
            d.mkdir()
            for f, t in files.items():
                (d / f).write_text(t)
            self.snap[name] = d

    def commit_all(self, msg):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)

    def run_dir(self, p: Path, arm: str, top1: int, *, seed=21, scenarios=("hero",), runs=3, rows=None,
                arm_rows=None, copy=LIST, **rec):
        p.mkdir(parents=True)
        rows = rows or [("hero", 3)]
        data = [dict(scenario=s, arm=arm_rows or arm, run=i, top1=False, trap=False, control_false_positive=False)
                for s, n in rows for i in range(n)]
        for d in data[:top1]:
            d["top1"] = True
        pl.DataFrame(data).write_parquet(p / "results.parquet")
        private = self.tmp / "kf-home" / "runs" / p.name / "removal.yaml"  # outside the repo
        if copy is not None:
            private.parent.mkdir(parents=True, exist_ok=True)
            private.write_text(copy)
        rec.setdefault("removal_copy", str(private))
        kb = arm == "graph_kb"
        base = dict(commit=self.kb, starve=True, heldout=True, test_run=False, seal_ok=True, seal_hash=self.sha,
                    removal_sha256=self.sha, data_root=f"/x/data_heldout/seed-{seed}", scenarios=list(scenarios),
                    runs=runs, returncode=0, started_at=LATER, e2ekg_sha="e" * 40, now=CLOCK,
                    snapshot=str(self.snap["kb"]) if kb else None)
        (p / "kf_run.json").write_text(json.dumps({**base, **rec}))


def _setup(tmp_path, kb_kw=None, seed_kw=None, seed_top1=1, **kw):
    w = World(tmp_path)
    _approvals(tmp_path)
    w.run_dir(tmp_path / "s", "graph", 0, **kw)
    w.run_dir(tmp_path / "k", "graph_kb", 3, **{**kw, **(kb_kw or {})})
    w.run_dir(tmp_path / "sk", "graph_kb", seed_top1, **{**kw, "commit": w.seed, "snapshot": str(w.snap["seed"]),
                                                 **(seed_kw or {})})
    return ["eval", "g2", "--starved", str(tmp_path / "s"), "--kb", str(tmp_path / "k"),
            "--seed-kb", str(tmp_path / "sk"), "--repo", str(w.repo),
            "--state-dir", str(tmp_path / "state"), "--report", str(tmp_path / "g2.md"),
            "--list", str(w.list), "--seal-file", str(w.seal)]


def _invalid(argv, capsys, reason, tmp_path):
    assert cli.main(argv) == 2
    err = capsys.readouterr().err
    assert reason in err, err
    assert not (tmp_path / "g2.md").exists()


def _approvals(tmp_path, **rec):
    (tmp_path / "state").mkdir(exist_ok=True)
    line = dict(branch="kf/a", by="alice", kind="person", role="approver", test_run=False, tier=1,
                at="2026-06-01T00:00:00+00:00")
    (tmp_path / "state" / "approvals.jsonl").write_text(json.dumps({**line, **rec}) + "\n")


def test_g2_cli_writes_report_when_valid(tmp_path, capsys):
    argv = _setup(tmp_path)
    _approvals(tmp_path)
    assert cli.main(argv) == 0, capsys.readouterr().err
    text = (tmp_path / "g2.md").read_text()
    assert "PASS" in text and "seed-only control" in text


def test_g2_cli_default_report_is_dated(tmp_path, monkeypatch):
    argv = _setup(tmp_path)
    i = argv.index("--report")
    del argv[i:i + 2]
    monkeypatch.setattr(removal, "REPO_ROOT", tmp_path / "root")
    assert cli.main(argv) == 0
    [report] = (tmp_path / "root" / "reports").iterdir()
    assert report.name.startswith("g2-20") and report.suffix == ".md"


def test_g2_cli_needs_the_seed_only_control(tmp_path):
    argv = _setup(tmp_path)
    i = argv.index("--seed-kb")
    with pytest.raises(SystemExit):
        cli.main(argv[:i] + argv[i + 2:])


def test_g2_fails_when_kb_does_not_beat_the_seed_only_control(tmp_path, capsys):
    """+3 over starved, but the seed bundle alone does as well: the curator earned nothing."""
    assert cli.main(_setup(tmp_path, seed_top1=3)) == 1
    assert "seed-only control" in capsys.readouterr().out
    assert "FAIL" in (tmp_path / "g2.md").read_text()


@pytest.mark.parametrize("kb_kw,reason", [
    (dict(starve=False), "--kb holds a run that was not starved"),
    (dict(scenarios=("hero", "v-x")), "scenarios"),
    (dict(seed=22), "data roots"),
    (dict(data_root="/elsewhere/data_heldout/seed-21"), "data roots"),
    (dict(runs=5), "runs-per-scenario"),
    (dict(returncode=1), "nonzero"),
    (dict(rows=[("hero", 2)]), "unequal scored runs"),
    (dict(rows=[("hero", 2), ("v-x", 1)]), "unequal scored runs per seed and scenario"),
    (dict(e2ekg_sha="f" * 40), "e2ekg commits"),
    (dict(e2ekg_sha=None), "e2ekg commits"),
    (dict(seal_hash="0" * 64), "did not run on the sealed list"),
    (dict(copy=None), "is missing, empty or no longer matches"),
    (dict(copy=LIST + "# edit\n"), "is missing, empty or no longer matches"),
    (dict(removal_copy=None), "no recorded private copy"),
    (dict(started_at="2000-01-01T00:00:00+00:00"), "not before the first run"),
    (dict(snapshot="/nowhere"), "bundle snapshot missing"),
    (dict(now="2026-11-21T00:00:00+00:00"), "different clocks"),
    (dict(now=None), "different clocks"),
    (dict(arm_rows="graph"), "graph_kb"),
])
def test_g2_cli_invalid_when_runs_not_comparable(tmp_path, capsys, kb_kw, reason):
    _invalid(_setup(tmp_path, kb_kw=kb_kw), capsys, reason, tmp_path)


@pytest.mark.parametrize("seed_kw,reason", [
    (dict(starve=False), "--seed-kb holds a run that was not starved"),
    (dict(commit=None), "no bundle commit"),
    (dict(now="2026-11-01T00:00:00+00:00"), "different clocks"),
])
def test_g2_cli_invalid_seed_only_control(tmp_path, capsys, seed_kw, reason):
    _invalid(_setup(tmp_path, seed_kw=seed_kw), capsys, reason, tmp_path)


def test_g2_cli_invalid_when_the_control_ran_on_the_curated_commit(tmp_path, capsys):
    argv = _setup(tmp_path)
    rec = tmp_path / "sk" / "kf_run.json"
    rec.write_text(json.dumps({**json.loads(rec.read_text()), "commit": json.loads(
        (tmp_path / "k" / "kf_run.json").read_text())["commit"]}))
    _invalid(argv, capsys, "nothing was curated", tmp_path)


def test_g2_cli_invalid_when_the_control_bundle_is_not_pristine(tmp_path, capsys):
    argv = _setup(tmp_path)
    repo = tmp_path / "repo"
    curated = git(repo, "rev-parse", "HEAD")
    (repo / "bundle" / "d.md").write_text(CURATED.format(who="alice"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "more")
    later = git(repo, "rev-parse", "HEAD")
    for d, commit in (("sk", curated), ("k", later)):
        rec = tmp_path / d / "kf_run.json"
        rec.write_text(json.dumps({**json.loads(rec.read_text()), "commit": commit}))
    _invalid(argv, capsys, "not pristine", tmp_path)


def test_g2_cli_invalid_when_kb_runs_used_two_bundle_commits(tmp_path, capsys):
    w_argv = _setup(tmp_path)
    rec = tmp_path / "k" / "kf_run.json"
    second = tmp_path / "k" / "seed-22"
    second.mkdir()
    for f in ("results.parquet",):
        (second / f).write_bytes((tmp_path / "k" / f).read_bytes())
    (second / "kf_run.json").write_text(json.dumps({**json.loads(rec.read_text()), "commit": "d" * 40}))
    _invalid(w_argv, capsys, "more than one bundle commit", tmp_path)


def test_g2_cli_invalid_when_main_got_a_direct_bundle_commit(tmp_path, capsys):
    argv = _setup(tmp_path)
    repo = tmp_path / "repo"
    (repo / "bundle" / "c.md").write_text(CURATED.format(who="alice") + "hand edit\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "hand")
    later = git(repo, "rev-parse", "HEAD")
    rec = tmp_path / "k" / "kf_run.json"
    rec.write_text(json.dumps({**json.loads(rec.read_text()), "commit": later}))
    _invalid(argv, capsys, f"commit {later[:12]} is not a curator merge", tmp_path)


def test_g2_cli_invalid_when_the_list_copy_is_inside_the_repo(tmp_path, capsys):
    argv = _setup(tmp_path)
    inside = tmp_path / "repo" / "state" / "evals" / "removal.yaml"
    inside.parent.mkdir(parents=True)
    inside.write_text(LIST)
    rec = tmp_path / "k" / "kf_run.json"
    rec.write_text(json.dumps({**json.loads(rec.read_text()), "removal_copy": str(inside)}))
    _invalid(argv, capsys, "is inside the repo", tmp_path)


def test_g2_cli_rejects_an_unstarved_starved_run(tmp_path, capsys):
    argv = _setup(tmp_path)
    cfg = tmp_path / "s" / "kf_run.json"
    cfg.write_text(json.dumps({**json.loads(cfg.read_text()), "starve": False}))
    _invalid(argv, capsys, "--starved holds a run that was not starved", tmp_path)


@pytest.mark.parametrize("rec,reason", [
    (dict(kind="scripted", by="t"), "scripted approval"),
    (dict(test_run=True), "test-run approval"),
    (dict(by="Olive "), "removal list author approved"),
])
def test_g2_cli_refuses_tainted_approvals(tmp_path, capsys, rec, reason):
    argv = _setup(tmp_path)
    _approvals(tmp_path, **rec)
    _invalid(argv, capsys, reason, tmp_path)


@pytest.mark.parametrize("who,reason", [("scripted-test", "scripted approval stamp"),
                                        ("olive", "approved by the removal list author")])
def test_g2_cli_scans_the_measured_bundle_for_stamps(tmp_path, capsys, who, reason):
    """A fresh --state-dir hides approvals.jsonl; the snapshot's verified stamps still show them."""
    argv = _setup(tmp_path)
    (tmp_path / "snap-kb" / "c.md").write_text(CURATED.format(who=who))
    _invalid(argv, capsys, reason, tmp_path)


@pytest.mark.parametrize("kw", [dict(heldout=False), dict(test_run=True), dict(seal_ok=False)])
def test_g2_cli_refuses_report_for_non_headline_runs(tmp_path, kw):
    assert cli.main(_setup(tmp_path, **kw)) == 2 and not (tmp_path / "g2.md").exists()


def test_g2_cli_refuses_when_list_changed_after_seal(tmp_path, capsys):
    argv = _setup(tmp_path)
    (tmp_path / "removal.yaml").write_text(LIST + "# edit\n")
    _invalid(argv, capsys, "changed since it was sealed", tmp_path)


def test_g2_cli_refuses_an_uncommitted_seal(tmp_path, capsys):
    argv = _setup(tmp_path)
    seal = tmp_path / "repo" / "integration" / "removal.seal"
    seal.write_text(seal.read_text() + " ")
    _invalid(argv, capsys, "not committed and clean", tmp_path)


def test_eval_run_maps_flags_onto_run_eval_per_heldout_seed(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    monkeypatch.setattr(evalx_cli, "resolve_commit", lambda bundle, ref: "f" * 40 if ref == "abc" else None)
    rc = cli.main(["eval", "run", "--arms", "graph,graph_kb", "--scenarios", "hero", "--runs", "2", "--starve",
                   "--heldout", "--test-run", "--bundle-commit", "abc", "--state-dir", str(tmp_path / "st"),
                   "--data-base", str(tmp_path)])
    assert rc == 0 and [c["data_root"].name for c in calls] == ["seed-21", "seed-22", "seed-23"]
    assert all(c["data_root"].parent.name == "data_heldout" for c in calls)
    assert calls[0]["arms"] == ["graph", "graph_kb"] and calls[0]["runs"] == 2 and calls[0]["starve"] is True
    assert calls[0]["heldout"] and calls[0]["test_run"]
    # one commit resolved once for every seed (a merge during the run cannot change the bundle)
    assert {c["bundle_commit"] for c in calls} == {"f" * 40}
    prefixes = [c["run_prefix"] for c in calls]
    assert all(p.startswith("heldout-") for p in prefixes) and [p[-6:] for p in prefixes] == [
        "seed21", "seed22", "seed23"]
    assert calls[0]["run_dir"].parent.name.startswith("heldout-")


@pytest.mark.parametrize("now", [None, "soon"])
def test_headline_eval_run_needs_an_explicit_iso_now(tmp_path, monkeypatch, capsys, now):
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    lst = tmp_path / "removal.yaml"
    lst.write_text(LIST)
    argv = ["eval", "run", "--heldout", "--state-dir", str(tmp_path), "--list", str(lst),
            "--bundle", str(tmp_path / "nob")]
    assert cli.main(argv + (["--now", now] if now else [])) == 2
    assert not calls and "--now" in capsys.readouterr().err


def test_headline_eval_run_passes_one_now_to_every_seed(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    monkeypatch.setattr(evalx_cli, "resolve_commit", lambda bundle, ref: "f" * 40)
    lst = tmp_path / "removal.yaml"
    lst.write_text(LIST)
    assert cli.main(["eval", "run", "--heldout", "--state-dir", str(tmp_path), "--list", str(lst),
                     "--bundle", str(tmp_path / "nob"), "--now", CLOCK]) == 0
    assert [c["now"] for c in calls] == [CLOCK] * 3


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
    lst = tmp_path / "removal.yaml"
    lst.write_text(LIST)
    assert cli.main(["eval", "run", "--heldout", "--state-dir", str(tmp_path), "--list", str(lst)]) == 2


@pytest.mark.parametrize("content", [None, "items: []\n"])
def test_headline_eval_run_refuses_a_missing_or_empty_list(tmp_path, monkeypatch, capsys, content):
    calls = []
    monkeypatch.setattr(evalx_cli, "run_eval", lambda **kw: calls.append(kw) or kw["run_dir"])
    lst = tmp_path / "removal.yaml"
    if content is not None:
        lst.write_text(content)
    assert cli.main(["eval", "run", "--heldout", "--state-dir", str(tmp_path), "--list", str(lst)]) == 1
    assert not calls and "refused" in capsys.readouterr().err


def test_eval_metrics_prints_json(tmp_path, capsys):
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "index.md").write_text("# idx\n")
    assert cli.main(["eval", "metrics", "--state-dir", str(tmp_path / "st"), "--bundle", str(b)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["curator"]["flags"] == 0 and out["corpus"]["concepts"] == 0


