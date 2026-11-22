"""`kf eval gate`: produce the eval gate (spec 5.3, 9b) for a curator branch kf/<run_id>.

graph_kb, starved, runs on the CURATION seeds (the "gate scenarios"; held-out seeds are for G2 only:
choosing merges by held-out scores would be selection on the test set, anti-goal A3) twice: over
main's bundle and over the branch's bundle with its proposed concepts served as if approved (in a
copy of the snapshot only; the branch is not touched). Both runs use one KF_NOW and keep their flags
in their own run dirs. The scores and their provenance (base and head commits, seeds, run dirs) go
into state/runs/<run_id>.json, where `kf review approve` recomputes the gate from them.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from kf.bundle import serve
from kf.bundle.okf import dump_concept, parse_concept
from kf.evalx.runner import E2EKG_DIR, _git, explicit_now, run_eval, scores_from
from kf.evalx.split import CURATION_SEEDS
from kf.review.gate import GateResult, eval_gate
from kf.review.review import BUNDLE, MAIN

ARM = "graph_kb"
UNREVIEWED = ("proposed", "in_review")


class GateError(Exception):
    pass


def as_approved_snapshot(bundle: Path, dest: Path, *, commit: str) -> Path:
    """A copy of the bundle snapshot at `commit` in which every proposed or in_review concept is
    marked approved, so the eval serves the branch's knowledge. Reused when it already exists."""
    snap = serve.snapshot(bundle, dest, commit=commit)
    out = Path(dest) / f"{snap.name}-as-approved"
    if out.is_dir():
        return out
    tmp = Path(tempfile.mkdtemp(prefix=".gate-", dir=dest))
    try:
        work = tmp / "b"
        shutil.copytree(snap, work, symlinks=True)
        for f in sorted(work.rglob("*.md")):
            if f.is_symlink():
                continue
            try:
                c = parse_concept(str(f), f.read_text(encoding="utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if c.front.get("x-kf-review") in UNREVIEWED:
                c.front["x-kf-review"] = "approved"
                f.write_text(dump_concept(c), encoding="utf-8")
        work.rename(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def record_path(repo: Path, branch: str) -> Path:
    return Path(repo) / "state" / "runs" / f"{branch.removeprefix('kf/')}.json"


def run_gate(repo: Path, branch: str, *, scenarios: list[str], runs: int, state_dir: Path, data_base: Path,
             removal_list: Path | None = None, now: str | None = None, e2ekg_dir: Path = E2EKG_DIR,
             run=None) -> GateResult:
    run = run or run_eval
    repo = Path(repo).resolve()
    if not branch.startswith("kf/"):
        raise GateError(f"{branch}: the gate is for curator branches (kf/<run_id>)")
    rec_path = record_path(repo, branch)
    try:
        record = json.loads(rec_path.read_text())
    except (OSError, ValueError) as e:
        raise GateError(f"no run record for {branch} at {rec_path}: {e}") from e
    try:
        base, head = _git(repo, "rev-parse", MAIN), _git(repo, "rev-parse", f"refs/heads/{branch}")
    except RuntimeError as e:
        raise GateError(str(e)) from e
    try:
        now = explicit_now(now)  # one explicit clock for both sides
    except ValueError as e:
        raise GateError(str(e)) from e
    state_dir = Path(state_dir).resolve()
    bundle = repo / BUNDLE
    head_snap = as_approved_snapshot(bundle, state_dir / "snapshots", commit=head)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = branch.removeprefix("kf/")
    parent = state_dir / "evals" / f"gate-{run_id}-{stamp}"
    for side, commit, snap in (("base", base, None), ("head", head, head_snap)):
        for seed in CURATION_SEEDS:
            run(arms=[ARM], scenarios=scenarios, runs=runs,
                data_root=Path(data_base) / "data_curation" / f"seed-{seed}", bundle_commit=commit,
                starve=True, state_dir=state_dir, heldout=False, test_run=False, now=now,
                run_dir=parent / side / f"seed-{seed}", bundle=bundle, removal_list=removal_list,
                e2ekg_dir=e2ekg_dir, run_prefix=f"gate-{run_id}-{stamp}-{side}-seed{seed}",
                own_flag_sink=True, snapshot=snap)
    scores = {side: scores_from(parent / side, ARM) for side in ("base", "head")}
    record = json.loads(rec_path.read_text())  # re-read: the eval took a while
    record["scores"] = {k: asdict(v) for k, v in scores.items()}
    record["gate"] = {"split": "curation", "seeds": list(CURATION_SEEDS), "arm": ARM, "starve": True,
                      "base_commit": base, "head_commit": head, "now": now, "scenarios": scenarios,
                      "runs": runs, "run_dir": str(parent), "at": datetime.now(UTC).isoformat()}
    tmp = rec_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2))
    tmp.replace(rec_path)
    return eval_gate(scores["base"], scores["head"])


def gate_from_record(repo: Path, branch: str, record: dict) -> GateResult | None:
    """The gate recomputed from the run record's scores, or a failing result when the scores are not
    from `kf eval gate` on curation seeds for the branch's and main's current commits. None when no
    gate was run."""
    from kf.review.gate import Scores

    scores, prov = record.get("scores"), record.get("gate")
    if not scores and not prov:
        return None
    try:
        result = eval_gate(Scores(**scores["base"]), Scores(**scores["head"]))
    except (KeyError, TypeError):
        return GateResult(False, ["malformed gate scores in the run record"])
    if not isinstance(prov, dict) or prov.get("split") != "curation":
        return GateResult(False, ["the gate scores have no curation-seed provenance (run kf eval gate)"])
    try:
        base, head = _git(Path(repo), "rev-parse", MAIN), _git(Path(repo), "rev-parse", f"refs/heads/{branch}")
    except RuntimeError as e:
        return GateResult(False, [str(e)])
    stale = [f"{name} moved since the gate ({prov.get(key, '?')[:12]} -> {now[:12]})"
             for name, key, now in (("main", "base_commit", base), (branch, "head_commit", head))
             if prov.get(key) != now]
    if stale:
        return GateResult(False, stale + ["re-run kf eval gate"])
    return result

