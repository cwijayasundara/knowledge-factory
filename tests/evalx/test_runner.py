import json
import subprocess
from pathlib import Path

import pytest

from kf.evalx import removal
from kf.evalx.runner import SealRefused, run_eval

NOW_ISO = "2026-06-01T12:00:00+00:00"
LIST = ('items:\n  - id: a\n    file: prompts/autorca.md\n    match: "alias hint"\n'
        '    why_derivable_from: catalog\n')


class Env:
    """A tmp repo: a bundle repo with one commit, a removal list with its seal, a fake e2ekg."""

    def __init__(self, tmp: Path, monkeypatch, outside: Path):
        self.tmp = tmp
        self.kf_home = outside / "kfhome"
        monkeypatch.setenv("KF_HOME", str(self.kf_home))
        self.bundle = tmp / "bundle"
        self.bundle.mkdir()
        (self.bundle / "index.md").write_text("# idx\n")
        env = {"GIT_AUTHOR_DATE": NOW_ISO, "GIT_COMMITTER_DATE": "2030-01-01T00:00:00+00:00",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@x", "PATH": __import__("os").environ["PATH"]}
        for cmd in (["init", "-q"], ["add", "bundle"], ["commit", "-q", "-m", "x"]):
            subprocess.run(["git", *cmd], cwd=tmp, env=env, check=True)
        self.sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True).stdout.strip()
        self.removal = outside / "removal.yaml"  # the real list lives outside the repo
        self.removal.write_text(LIST)
        self.seal = tmp / "removal.seal"
        self.e2ekg = tmp / "e2ekg"
        self.e2ekg.mkdir()
        (self.e2ekg / "pyproject.toml").write_text("[project]\nname = 'e2ekg'\n")
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "e"]):
            subprocess.run(["git", *cmd], cwd=self.e2ekg, env=env, check=True)
        self.e2ekg_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.e2ekg, capture_output=True,
                                        text=True).stdout.strip()
        self.calls: list[dict] = []
        monkeypatch.setattr(subprocess, "run", self._run, raising=True)
        self._real_run = None

    def _run(self, cmd, **kw):
        if cmd[0] == "git":
            return REAL_RUN(cmd, **kw)
        self.calls.append({"cmd": cmd, **kw})
        run_dir = Path(cmd[cmd.index("--run-dir") + 1])
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "results.parquet").write_bytes(b"")
        return subprocess.CompletedProcess(cmd, 0)

    def go(self, **kw):
        args = dict(arms=["graph_kb"], scenarios=["hero"], runs=3, data_root=self.tmp / "data_heldout" / "seed-21",
                    bundle_commit=None, starve=False, state_dir=self.tmp / "state", bundle=self.bundle,
                    removal_list=self.removal, seal_file=self.seal, e2ekg_dir=self.e2ekg)
        args.update(kw)
        return run_eval(**args)


REAL_RUN = subprocess.run


@pytest.fixture
def env(tmp_path, monkeypatch, tmp_path_factory):
    return Env(tmp_path, monkeypatch, tmp_path_factory.mktemp("outside"))


def test_runner_builds_expected_command(env):
    removal.seal(env.removal, env.seal, author="olive")
    run_dir = env.go(starve=True, arms=["graph", "graph_kb"], scenarios=["hero", "v-x"], heldout=True,
                     now="2026-06-02T00:00:00+00:00")
    (call,) = env.calls
    cmd, e = call["cmd"], call["env"]
    assert cmd[:4] == ["uv", "run", "e2ekg", "eval"]
    assert cmd[cmd.index("--arms") + 1] == "graph,graph_kb" and cmd[cmd.index("--scenarios") + 1] == "hero,v-x"
    assert cmd[cmd.index("--runs") + 1] == "3" and cmd[cmd.index("--root") + 1] == str(env.tmp / "data_heldout/seed-21")
    assert call["cwd"] == env.e2ekg
    private = env.kf_home / "runs" / run_dir.relative_to(env.tmp / "state" / "evals") / "removal.yaml"
    assert e["E2EKG_STARVE"] == str(private.resolve())  # a private copy made before e2ekg starts
    assert private.read_text() == LIST and not (run_dir / "removal.yaml").exists()
    assert e["KF_STATE_DIR"] == str(run_dir / "state")  # held-out flags never reach the curator's queue
    snap = Path(e["KF_BUNDLE_SNAPSHOT"])
    assert snap.name == env.sha and (snap / "index.md").is_file()
    assert e["KF_NOW"] == "2026-06-02T00:00:00+00:00"  # the headline's explicit clock
    rec = json.loads((run_dir / "kf_run.json").read_text())
    assert rec["now"] == "2026-06-02T00:00:00+00:00"
    assert rec["commit"] == env.sha and rec["starve"] is True and rec["test_run"] is False
    assert rec["heldout"] is True and rec["seal_ok"] is True and len(rec["seal_hash"]) == 64
    assert rec["removal_sha256"] == rec["seal_hash"] and rec["seal_author"] == "olive"
    assert rec["removal_copy"] == str(private.resolve())
    assert rec["e2ekg_sha"] == env.e2ekg_sha and rec["snapshot"] == str(snap) and rec["started_at"]
    assert e["KF_RUN_PREFIX"] == rec["run_prefix"]


def test_runner_no_snapshot_or_starve_env_without_kb_arm(env):
    env.go(arms=["graph"], test_run=True)
    e = env.calls[0]["env"]
    assert "KF_BUNDLE_SNAPSHOT" not in e and "E2EKG_STARVE" not in e
    assert not (env.tmp / "state" / "snapshots").exists()


def test_non_headline_run_defaults_now_to_the_author_date(env):
    env.go(arms=["graph"], test_run=True)
    assert env.calls[0]["env"]["KF_NOW"] == "2026-06-01T12:00:00Z"  # author date, not committer date


@pytest.mark.parametrize("now", [None, "", "yesterday"])
def test_headline_run_refused_without_an_explicit_iso_now(env, now):
    removal.seal(env.removal, env.seal, author="olive")
    with pytest.raises(SealRefused, match="--now"):
        env.go(starve=True, heldout=True, now=now)
    assert env.calls == []


def test_runner_explicit_now_overrides(env):
    env.go(arms=["graph"], test_run=True, now="2026-07-01T00:00:00+00:00")
    assert env.calls[0]["env"]["KF_NOW"] == "2026-07-01T00:00:00+00:00"


@pytest.mark.parametrize("break_seal", ["missing", "mismatch"])
def test_headline_run_refused_without_valid_seal(env, break_seal):
    if break_seal == "mismatch":
        removal.seal(env.removal, env.seal, author="olive")
        env.removal.write_text("items: []\n# edited\n")
    with pytest.raises(SealRefused, match="does not match"):
        env.go(heldout=True, now=NOW_ISO)
    assert env.calls == [] and not (env.tmp / "state" / "evals").exists()


def test_test_run_records_failed_seal_and_proceeds(env):
    run_dir = env.go(heldout=True, test_run=True)
    rec = json.loads((run_dir / "kf_run.json").read_text())
    assert rec["seal_ok"] is False and rec["test_run"] is True and rec["seal_hash"] is None


def test_curation_run_is_not_headline(env):
    run_dir = env.go(arms=["graph"], heldout=False)  # no seal needed: not a held-out run
    assert len(env.calls) == 1
    assert env.calls[0]["env"]["KF_STATE_DIR"] == str((env.tmp / "state").resolve())  # the curator's queue
    assert json.loads((run_dir / "kf_run.json").read_text())["flag_state_dir"] == str((env.tmp / "state").resolve())


def test_missing_results_raises(env, monkeypatch):
    def run(cmd, **kw):
        return REAL_RUN(cmd, **kw) if cmd[0] == "git" else subprocess.CompletedProcess(cmd, 1)
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError):
        env.go(arms=["graph"], test_run=True)


def test_headline_run_refused_for_an_empty_list(env):
    env.removal.write_text("items: []\n")
    env.seal.write_text(json.dumps({"sha256": removal.digest(env.removal), "author": "olive"}))
    with pytest.raises(SealRefused, match="no items"):
        env.go(heldout=True, now=NOW_ISO)
    assert env.calls == []


def test_a_list_edit_during_the_run_does_not_reach_it(env):
    removal.seal(env.removal, env.seal, author="olive")
    env.go(starve=True, heldout=True, now=NOW_ISO)
    env.removal.write_text(LIST.replace("alias hint", "other"))
    assert Path(env.calls[0]["env"]["E2EKG_STARVE"]).read_text() == LIST


def test_own_flag_sink_keeps_flags_in_the_run_dir(env):
    run_dir = env.go(arms=["graph_kb"], own_flag_sink=True)
    assert env.calls[0]["env"]["KF_STATE_DIR"] == str(run_dir / "state")


def test_run_prefix_is_passed_to_e2ekg(env):
    env.go(arms=["graph_kb"], run_prefix="curation-X-seed11")
    assert env.calls[0]["env"]["KF_RUN_PREFIX"] == "curation-X-seed11"


def test_missing_e2ekg_checkout_is_a_clear_error(env, tmp_path):
    with pytest.raises(RuntimeError, match="integration/apply.sh"):
        env.go(arms=["graph"], e2ekg_dir=tmp_path / "nope")


def test_default_paths_are_anchored_to_the_repo_root():
    from kf.evalx import runner

    root = Path(__file__).resolve().parents[2]
    assert runner.E2EKG_DIR == root / "external" / "e2ekg"
    assert removal.DEFAULT_SEAL == root / "integration" / "removal.seal"


def test_the_private_copy_is_owner_only(env):
    import stat

    removal.seal(env.removal, env.seal, author="olive")
    env.go(starve=True, heldout=True, now=NOW_ISO)
    copy = Path(env.calls[0]["env"]["E2EKG_STARVE"])
    assert stat.S_IMODE(copy.stat().st_mode) == 0o600
    for d in (copy.parent, copy.parent.parent, env.kf_home / "runs"):
        assert stat.S_IMODE(d.stat().st_mode) == 0o700, d


def test_a_private_area_inside_the_repo_is_refused(env, monkeypatch):
    removal.seal(env.removal, env.seal, author="olive")
    monkeypatch.setenv("KF_HOME", str(env.tmp / "kfhome"))  # env.tmp is the bundle's repo
    with pytest.raises(SealRefused, match="outside the repo"):
        env.go(starve=True, heldout=True, now=NOW_ISO)
    assert env.calls == []


SENTINEL = "zq-sentinel-7f3a"


def test_no_list_text_lands_in_the_repo_tree(env, monkeypatch):
    """Runs (one ok, one failing, one refused) leave no removal-list text anywhere in the repo tree."""
    env.removal.write_text(LIST.replace("alias hint", SENTINEL))
    removal.seal(env.removal, env.seal, author="olive")
    env.go(starve=True, heldout=True, now=NOW_ISO, arms=["graph", "graph_kb"])

    def chatty(cmd, **kw):  # an e2ekg that logs its env and fails
        if cmd[0] == "git":
            return REAL_RUN(cmd, **kw)
        run_dir = Path(cmd[cmd.index("--run-dir") + 1])
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "e2ekg.log").write_text(json.dumps(kw["env"]))
        return subprocess.CompletedProcess(cmd, 1)
    monkeypatch.setattr(subprocess, "run", chatty)
    errors = []
    with pytest.raises(RuntimeError) as e:
        env.go(starve=True, heldout=True, now=NOW_ISO, run_dir=env.tmp / "state" / "evals" / "x" / "seed-21")
    errors.append(str(e.value))
    env.removal.write_text("items:\n  - id: a\n    file: nope\n    match: " + SENTINEL + "\n")
    with pytest.raises(SealRefused) as e:
        env.go(starve=True, heldout=True, now=NOW_ISO)
    errors.append(str(e.value))
    leaks = [p for p in env.tmp.rglob("*") if p.is_file() and SENTINEL.encode() in p.read_bytes()]
    assert leaks == [] and not any(SENTINEL in m for m in errors)


def test_an_invalid_list_error_does_not_quote_the_list(tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text("items:\n  - id: a\n    file: nope\n    match: " + SENTINEL + "\n    why_derivable_from: c\n")
    with pytest.raises(removal.RemovalRefused) as e:
        removal.load_nonempty(p)
    assert SENTINEL not in str(e.value) and "file" in str(e.value)
    p.write_text("items: [" + SENTINEL + "\n  - : :\n")
    with pytest.raises(removal.RemovalRefused) as e:
        removal.load_nonempty(p)
    assert SENTINEL not in str(e.value)
