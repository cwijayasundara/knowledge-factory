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

E2EKG_DIR = removal.REPO_ROOT / "external" / "e2ekg"
KB_ARMS = ("graph_kb",)


class SealRefused(Exception):
    pass


def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def explicit_now(now: str | None) -> str:
    """The --now value of a headline or gate run: an ISO 8601 timestamp with a UTC offset. One value is
    picked once and passed to every arm (starved, treatment, control; main and branch for a gate), so
    stale_after filtering is the same everywhere. ValueError otherwise."""
    if not now or not str(now).strip():
        raise ValueError("an explicit --now ISO timestamp is required (pick one value and reuse it for every arm)")
    try:
        t = datetime.fromisoformat(str(now).strip())
    except ValueError as e:
        raise ValueError(f"--now {now!r} is not an ISO 8601 timestamp") from e
    if t.tzinfo is None:
        raise ValueError(f"--now {now!r} has no UTC offset (e.g. 2026-11-20T00:00:00+00:00)")
    return str(now).strip()


def resolve_commit(bundle: Path, ref: str | None) -> str:
    """The full sha of `ref` (default HEAD) in the bundle's repo. Resolve once per invocation, so a
    merge during a multi-seed run cannot change the bundle between seeds."""
    return _git(Path(bundle), "rev-parse", "--verify", f"{ref or 'HEAD'}^{{commit}}")


def _e2ekg_sha(e2ekg_dir: Path) -> str | None:
    try:
        return _git(Path(e2ekg_dir), "rev-parse", "HEAD")
    except RuntimeError:
        return None


def private_copy_path(run_dir: Path, state_dir: Path) -> Path:
    """Where a starved run's list copy lives: ${KF_HOME:-~/.kf}/runs/<run dir relative to
    <state_dir>/evals>/removal.yaml (else runs/<parent>/<name>/), outside the repo the reviewer browses."""
    run_dir, evals = Path(run_dir).resolve(), (Path(state_dir) / "evals").resolve()
    rel = run_dir.relative_to(evals) if evals in run_dir.parents else Path(run_dir.parent.name) / run_dir.name
    return removal.kf_home().resolve() / "runs" / rel / "removal.yaml"


def _toplevel(path: Path) -> Path | None:
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return Path(_git(p if p.is_dir() else p.parent, "rev-parse", "--show-toplevel"))
    except RuntimeError:
        return None


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
    bundle: Path = removal.REPO_ROOT / "bundle",
    removal_list: Path | None = None,
    seal_file: Path = removal.DEFAULT_SEAL,
    e2ekg_dir: Path = E2EKG_DIR,
    run_prefix: str | None = None,
    own_flag_sink: bool = False,
    snapshot: Path | None = None,
) -> Path:
    """Run the eval; returns the run directory (results.parquet and kf_run.json inside).

    Flags go to <state_dir>/flags.db (the curator's queue) only for curation runs; a held-out run
    (or one with own_flag_sink, such as a gate run) writes them to <run_dir>/state/flags.db, so
    held-out data never reaches the curator (spec 9b). A starved run reads a copy of the removal
    list made before e2ekg starts, so a later edit of the list cannot reach it; the copy lives in a
    private run area outside the repo (${KF_HOME:-~/.kf}/runs/..., dirs 0700, file 0600) and its path
    and sha256 go into kf_run.json, so no list text is in the repo the blind reviewer browses.
    `snapshot` replaces the bundle snapshot of `bundle_commit` (the gate's as-if-approved copy)."""
    from kf.bundle import serve

    state_dir, data_root = Path(state_dir).resolve(), Path(data_root).resolve()
    removal_list = Path(removal_list or removal.default_list()).expanduser().resolve()
    bundle, seal_file = Path(bundle).resolve(), Path(seal_file).resolve()
    if not (Path(e2ekg_dir) / "pyproject.toml").is_file():
        raise RuntimeError(f"{e2ekg_dir} is not an e2ekg checkout: run bash integration/apply.sh first")
    seal_ok = removal_list.is_file() and removal.verify_seal(removal_list, seal_file)
    seal_info = removal.read_seal(seal_file)
    seal_hash = seal_info["sha256"] if seal_info else None
    if heldout and not test_run:
        try:
            now = explicit_now(now)
        except ValueError as e:
            raise SealRefused(f"headline run refused: {e}") from e
        if not seal_ok:
            raise SealRefused(f"headline run refused: {seal_file} is missing or does not match {removal_list}")
        try:
            removal.load_nonempty(removal_list)
        except removal.RemovalRefused as e:
            raise SealRefused(f"headline run refused: {e}") from e
    if starve and not removal_list.is_file():
        raise SealRefused(f"a starved run needs the removal list: {removal_list} not found")

    run_dir = Path(run_dir).resolve() if run_dir else state_dir / "evals" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if starve:
        private = private_copy_path(run_dir, state_dir)
        for repo in {removal.REPO_ROOT, _toplevel(bundle), _toplevel(state_dir)} - {None}:
            if removal.inside_repo(private, repo):
                raise SealRefused(f"the private run area {private.parent} must be outside the repo {repo} "
                                  "(set KF_HOME to a directory the reviewer does not browse)")

    commit = resolve_commit(bundle, bundle_commit)
    now = now or _git(bundle, "log", "-1", "--format=%aI", commit)  # author date: survives rebases of the run
    run_dir.mkdir(parents=True, exist_ok=True)
    flag_state = run_dir / "state" if (heldout or own_flag_sink) else state_dir
    prefix = run_prefix or f"{'heldout' if heldout else 'curation'}-{run_dir.parent.name}-{run_dir.name}"

    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "E2EKG_STARVE", "KF_BUNDLE_SNAPSHOT")}
    env.update(KF_STATE_DIR=str(flag_state), KF_NOW=now, KF_RUN_PREFIX=prefix)
    snap = None
    if set(arms) & set(KB_ARMS):
        snap = Path(snapshot).resolve() if snapshot else serve.snapshot(bundle, state_dir / "snapshots", commit=commit)
        env["KF_BUNDLE_SNAPSHOT"] = str(snap)
    list_copy = None
    if starve:
        list_copy = private_copy_path(run_dir, state_dir)
        removal.write_private_copy(removal_list, list_copy, area=removal.kf_home().resolve() / "runs")
        env["E2EKG_STARVE"] = str(list_copy)

    cmd = ["uv", "run", "e2ekg", "eval", "--root", str(data_root), "--runs", str(runs),
           "--arms", ",".join(arms), "--scenarios", ",".join(scenarios), "--run-dir", str(run_dir)]
    flag_state.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    proc = subprocess.run(cmd, cwd=Path(e2ekg_dir), env=env)
    (run_dir / "kf_run.json").write_text(json.dumps({
        "commit": commit, "now": now, "seal_hash": seal_hash, "seal_ok": seal_ok,
        "seal_author": seal_info.get("author") if seal_info else None,
        "removal_sha256": removal.digest(list_copy) if list_copy else None,
        "removal_copy": str(list_copy) if list_copy else None, "starve": starve,
        "test_run": test_run, "heldout": heldout, "arms": arms, "scenarios": scenarios, "runs": runs,
        "data_root": str(data_root), "returncode": proc.returncode, "started_at": started,
        "e2ekg_sha": _e2ekg_sha(e2ekg_dir), "snapshot": str(snap) if snap else None,
        "flag_state_dir": str(flag_state), "run_prefix": prefix,
    }, indent=2) + "\n")
    if not (run_dir / "results.parquet").is_file():
        raise RuntimeError(f"e2ekg eval exited {proc.returncode} and wrote no results.parquet in {run_dir}")
    return run_dir


def row_counts(run_dir: Path, arm: str) -> dict[tuple[str, str], int]:
    """(data_root, scenario) -> scored runs of `arm`, over every kf_run.json under run_dir."""
    import polars as pl

    out: dict[tuple[str, str], int] = {}
    for rec_file in sorted(Path(run_dir).rglob("kf_run.json")):
        res = rec_file.parent / "results.parquet"
        if not res.is_file():
            continue
        root = json.loads(rec_file.read_text()).get("data_root", "")
        d = pl.read_parquet(res).filter(pl.col("arm") == arm)
        for scenario, n in d.group_by("scenario").len().iter_rows():
            out[(root, scenario)] = out.get((root, scenario), 0) + n
    return out


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
