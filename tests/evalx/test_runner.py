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

    def __init__(self, tmp: Path, monkeypatch):
        self.tmp = tmp
        self.bundle = tmp / "bundle"
        self.bundle.mkdir()
        (self.bundle / "index.md").write_text("# idx\n")
        env = {"GIT_AUTHOR_DATE": NOW_ISO, "GIT_COMMITTER_DATE": "2030-01-01T00:00:00+00:00",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@x", "PATH": __import__("os").environ["PATH"]}
        for cmd in (["init", "-q"], ["add", "bundle"], ["commit", "-q", "-m", "x"]):
            subprocess.run(["git", *cmd], cwd=tmp, env=env, check=True)
        self.sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True).stdout.strip()
        self.removal = tmp / "removal.yaml"
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
def env(tmp_path, monkeypatch):
    return Env(tmp_path, monkeypatch)


def test_runner_builds_expected_command(env):
    removal.seal(env.removal, env.seal, author="olive")
    run_dir = env.go(starve=True, arms=["graph", "graph_kb"], scenarios=["hero", "v-x"], heldout=True)
    (call,) = env.calls
    cmd, e = call["cmd"], call["env"]
    assert cmd[:4] == ["uv", "run", "e2ekg", "eval"]
    assert cmd[cmd.index("--arms") + 1] == "graph,graph_kb" and cmd[cmd.index("--scenarios") + 1] == "hero,v-x"
    assert cmd[cmd.index("--runs") + 1] == "3" and cmd[cmd.index("--root") + 1] == str(env.tmp / "data_heldout/seed-21")
    assert call["cwd"] == env.e2ekg
    assert e["E2EKG_STARVE"] == str(run_dir / "removal.yaml")  # a copy made before e2ekg starts
    assert (run_dir / "removal.yaml").read_text() == LIST
    assert e["KF_STATE_DIR"] == str(run_dir / "state")  # held-out flags never reach the curator's queue
    snap = Path(e["KF_BUNDLE_SNAPSHOT"])
    assert snap.name == env.sha and (snap / "index.md").is_file()
    assert e["KF_NOW"] == "2026-06-01T12:00:00Z"  # author date, not committer date
    rec = json.loads((run_dir / "kf_run.json").read_text())
    assert rec["commit"] == env.sha and rec["starve"] is True and rec["test_run"] is False
    assert rec["heldout"] is True and rec["seal_ok"] is True and len(rec["seal_hash"]) == 64
    assert rec["removal_sha256"] == rec["seal_hash"] and rec["seal_author"] == "olive"
    assert rec["e2ekg_sha"] == env.e2ekg_sha and rec["snapshot"] == str(snap) and rec["started_at"]
    assert e["KF_RUN_PREFIX"] == rec["run_prefix"]


def test_runner_no_snapshot_or_starve_env_without_kb_arm(env):
    env.go(arms=["graph"], test_run=True)
    e = env.calls[0]["env"]
    assert "KF_BUNDLE_SNAPSHOT" not in e and "E2EKG_STARVE" not in e
    assert not (env.tmp / "state" / "snapshots").exists()


def test_runner_explicit_now_overrides(env):
    env.go(arms=["graph"], test_run=True, now="2026-07-01T00:00:00+00:00")
    assert env.calls[0]["env"]["KF_NOW"] == "2026-07-01T00:00:00+00:00"


@pytest.mark.parametrize("break_seal", ["missing", "mismatch"])
def test_headline_run_refused_without_valid_seal(env, break_seal):
    if break_seal == "mismatch":
        removal.seal(env.removal, env.seal, author="olive")
        env.removal.write_text("items: []\n# edited\n")
    with pytest.raises(SealRefused):
        env.go(heldout=True)
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
        env.go(heldout=True)
    assert env.calls == []


def test_a_list_edit_during_the_run_does_not_reach_it(env):
    removal.seal(env.removal, env.seal, author="olive")
    run_dir = env.go(starve=True, heldout=True)
    env.removal.write_text(LIST.replace("alias hint", "other"))
    assert (run_dir / "removal.yaml").read_text() == LIST


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
