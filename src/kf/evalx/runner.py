"""Run an e2ekg eval for the knowledge factory and read its scores (spec 9b).

One call runs one e2ekg data root (one seed): `uv run e2ekg eval` inside external/e2ekg, with the
factory's env (KF_STATE_DIR, KF_BUNDLE_SNAPSHOT, KF_NOW, E2EKG_STARVE). The CLI runs one data root
per seed, `data_curation/seed-<N>` or `data_heldout/seed-<N>`, and e2ekg's own scenario names
(`hero`, `v-...`; the seed is the data root, e2ekg's generator adds no suffix). `kf_run.json`
beside the results records what was run; g2 reads it back.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from kf.evalx import removal
from kf.review.gate import Scores

E2EKG_DIR = Path("external/e2ekg")
KB_ARMS = ("graph_kb",)


class SealRefused(Exception):
    pass


def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def run_eval(
    *,
    arms: list[str],
    scenarios: list[str],
    runs: int,
    data_root: Path,
    bundle_commit: str | None,
    starve: bool,
    state_dir: Path,
    heldout: bool = False,
    test_run: bool = False,
    now: str | None = None,
    run_dir: Path | None = None,
    bundle: Path = Path("bundle"),
    removal_list: Path = removal.DEFAULT_LIST,
    seal_file: Path = removal.DEFAULT_SEAL,
    e2ekg_dir: Path = E2EKG_DIR,
) -> Path:
    """Run the eval; returns the run directory (results.parquet and kf_run.json inside)."""
    from kf.bundle import serve

    state_dir, data_root = Path(state_dir).resolve(), Path(data_root).resolve()
    bundle, removal_list, seal_file = Path(bundle).resolve(), Path(removal_list).resolve(), Path(seal_file).resolve()
    seal_ok = removal_list.is_file() and removal.verify_seal(removal_list, seal_file)
    seal_hash = seal_file.read_text().strip() if seal_file.is_file() else None
    if heldout and not test_run and not seal_ok:
        raise SealRefused(f"headline run refused: {seal_file} is missing or does not match {removal_list}")

    commit = _git(bundle, "rev-parse", "--verify", f"{bundle_commit or 'HEAD'}^{{commit}}")
    now = now or _git(bundle, "log", "-1", "--format=%aI", commit)  # author date: survives rebases of the run
    run_dir = Path(run_dir).resolve() if run_dir else state_dir / "evals" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env.update(KF_STATE_DIR=str(state_dir), KF_NOW=now)
    if set(arms) & set(KB_ARMS):
        env["KF_BUNDLE_SNAPSHOT"] = str(serve.snapshot(bundle, state_dir / "snapshots", commit=commit))
    if starve:
        env["E2EKG_STARVE"] = str(removal_list)

    cmd = ["uv", "run", "e2ekg", "eval", "--root", str(data_root), "--runs", str(runs),
           "--arms", ",".join(arms), "--scenarios", ",".join(scenarios), "--run-dir", str(run_dir)]
    state_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, cwd=Path(e2ekg_dir), env=env)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "kf_run.json").write_text(json.dumps({
        "commit": commit, "now": now, "seal_hash": seal_hash, "seal_ok": seal_ok, "starve": starve,
        "test_run": test_run, "heldout": heldout, "arms": arms, "scenarios": scenarios, "runs": runs,
        "data_root": str(data_root), "returncode": proc.returncode,
    }, indent=2) + "\n")
    if not (run_dir / "results.parquet").is_file():
        raise RuntimeError(f"e2ekg eval exited {proc.returncode} and wrote no results.parquet in {run_dir}")
    return run_dir


def scores_from(results_dir: Path, arm: str) -> Scores:
    """Sum an arm's scenario-runs over every results.parquet under results_dir (one per seed)."""
    import polars as pl

    files = sorted(Path(results_dir).rglob("results.parquet"))
    if not files:
        raise ValueError(f"no results.parquet under {results_dir}")
    df = pl.concat([pl.read_parquet(f) for f in files], how="diagonal_relaxed")
    d = df.filter(pl.col("arm") == arm)
    if not d.height:
        raise ValueError(f"arm {arm!r} has no runs under {results_dir}")
    return Scores(top1=int(d["top1"].sum()), runs=d.height, trap=int(d["trap"].sum()),
                  control_fp=int(d["control_false_positive"].sum()))
