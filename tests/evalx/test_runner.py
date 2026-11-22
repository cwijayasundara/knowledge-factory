import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kf.evalx import removal
from kf.evalx.runner import SealRefused, run_eval

NOW_ISO = "2026-06-01T12:00:00+00:00"


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
        for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "x"]):
            subprocess.run(["git", *cmd], cwd=tmp, env=env, check=True)
        self.sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True).stdout.strip()
        self.removal = tmp / "removal.yaml"
        self.removal.write_text("items: []\n")
        self.seal = tmp / "removal.seal"
        self.e2ekg = tmp / "e2ekg"
        self.e2ekg.mkdir()
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
    removal.seal(env.removal, env.seal)
    run_dir = env.go(starve=True, arms=["graph", "graph_kb"], scenarios=["hero", "v-x"], heldout=True)
    (call,) = env.calls
    cmd, e = call["cmd"], call["env"]
    assert cmd[:4] == ["uv", "run", "e2ekg", "eval"]
    assert cmd[cmd.index("--arms") + 1] == "graph,graph_kb" and cmd[cmd.index("--scenarios") + 1] == "hero,v-x"
    assert cmd[cmd.index("--runs") + 1] == "3" and cmd[cmd.index("--root") + 1] == str(env.tmp / "data_heldout/seed-21")
    assert call["cwd"] == env.e2ekg
    assert e["E2EKG_STARVE"] == str(env.removal.resolve())
    assert e["KF_STATE_DIR"] == str((env.tmp / "state").resolve())
    snap = Path(e["KF_BUNDLE_SNAPSHOT"])
    assert snap.name == env.sha and (snap / "index.md").is_file()
    assert e["KF_NOW"] == "2026-06-01T12:00:00Z"  # author date, not committer date
    rec = json.loads((run_dir / "kf_run.json").read_text())
    assert rec["commit"] == env.sha and rec["starve"] is True and rec["test_run"] is False
    assert rec["heldout"] is True and rec["seal_ok"] is True and len(rec["seal_hash"]) == 64


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
        removal.seal(env.removal, env.seal)
        env.removal.write_text("items: []\n# edited\n")
    with pytest.raises(SealRefused):
        env.go(heldout=True)
    assert env.calls == [] and not (env.tmp / "state" / "evals").exists()


def test_test_run_records_failed_seal_and_proceeds(env):
    run_dir = env.go(heldout=True, test_run=True)
    rec = json.loads((run_dir / "kf_run.json").read_text())
    assert rec["seal_ok"] is False and rec["test_run"] is True and rec["seal_hash"] is None


def test_curation_run_is_not_headline(env):
    env.go(arms=["graph"], heldout=False)  # no seal needed: not a held-out run
    assert len(env.calls) == 1


def test_missing_results_raises(env, monkeypatch):
    def run(cmd, **kw):
        return REAL_RUN(cmd, **kw) if cmd[0] == "git" else subprocess.CompletedProcess(cmd, 1)
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError):
        env.go(arms=["graph"], test_run=True)
