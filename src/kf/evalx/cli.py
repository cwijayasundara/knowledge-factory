"""Handlers for `kf eval run|g2|metrics` (parser lives in kf.cli)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from kf.evalx import removal
from kf.evalx.g2 import (coverage_problems, g2_verdict, pristine_problems, read_approval_records, seal_problems,
                         snapshot_problems, to_approvals)
from kf.evalx.metrics import corpus_metrics, curator_metrics
from kf.evalx.runner import SealRefused, resolve_commit, row_counts, run_eval, scores_from
from kf.evalx.split import CURATION_SEEDS, HELDOUT_SEEDS
from kf.flags.queue import FlagQueue


def run(args) -> int:
    return {"run": _run, "g2": _g2, "metrics": _metrics}[args.sub](args)


def _run(args) -> int:
    seeds, prefix = (HELDOUT_SEEDS, "data_heldout") if args.heldout else (CURATION_SEEDS, "data_curation")
    if args.heldout and not args.test_run:
        try:
            overlaps = removal.seed_overlaps(Path(args.bundle), removal.load_nonempty(Path(args.list)))
        except (removal.RemovalRefused, OSError) as e:
            print(f"refused: {e}", file=sys.stderr)
            return 1
        if overlaps:
            print(f"refused: the bundle holds removal items: {', '.join(overlaps)}", file=sys.stderr)
            return 1
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    split = "heldout" if args.heldout else "curation"
    parent = Path(args.state_dir) / "evals" / f"{split}-{stamp}"
    try:
        commit = resolve_commit(Path(args.bundle), args.bundle_commit)  # once: every seed sees one bundle
    except RuntimeError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    for seed in seeds:
        try:
            run_dir = run_eval(
                arms=args.arms.split(","), scenarios=args.scenarios.split(","), runs=args.runs,
                data_root=Path(args.data_base) / prefix / f"seed-{seed}", bundle_commit=commit,
                starve=args.starve, state_dir=Path(args.state_dir), heldout=args.heldout,
                test_run=args.test_run, now=args.now, run_dir=parent / f"seed-{seed}", bundle=Path(args.bundle),
                removal_list=Path(args.list), run_prefix=f"{split}-{stamp}-seed{seed}",
            )
        except SealRefused as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(f"seed {seed}: {run_dir}")
    print(parent)
    return 0


def _records(run_dir: str) -> list[dict]:
    files = sorted(Path(run_dir).rglob("kf_run.json"))
    if not files:
        raise SystemExit(f"no kf_run.json under {run_dir}")
    return [{**json.loads(f.read_text()), "_dir": str(f.parent)} for f in files]


def _g2(args) -> int:
    sets = {"starved": _records(args.starved), "kb": _records(args.kb), "seed-kb": _records(args.seed_kb)}
    arms = {"starved": "graph", "kb": "graph_kb", "seed-kb": "graph_kb"}
    problems = []
    # Every arm uses the starved prompts (spec 9b); the bundle is the only difference.
    for name, recs in sets.items():
        if not all(r["starve"] for r in recs):
            problems.append(f"--{name} holds a run that was not starved")
    recs = [r for rs in sets.values() for r in rs]
    seal_issues, seal_info = seal_problems(recs, Path(args.seal_file))
    problems += seal_issues
    if Path(args.list).is_file() and not removal.verify_seal(Path(args.list), Path(args.seal_file)):
        problems.append(f"{args.list} changed since it was sealed")
    author = (seal_info or {}).get("author")
    if seal_info is not None and not author:
        problems.append("the seal records no list author")
    seal_ok = not seal_issues and all(r["seal_ok"] for r in recs)
    heldout = all(r["heldout"] for r in recs) and not any(r["test_run"] for r in recs)
    approvals = to_approvals(read_approval_records(Path(args.state_dir) / "approvals.jsonl"))
    problems += snapshot_problems(sets["kb"] + sets["seed-kb"], author)
    commit = {n: (sets[n][0].get("commit") if sets[n] else None) for n in ("kb", "seed-kb")}
    problems += pristine_problems(Path(args.repo), commit["seed-kb"], commit["kb"])
    scores, rows = {}, {}
    for name in sets:
        d = getattr(args, {"starved": "starved", "kb": "kb", "seed-kb": "seed_kb"}[name])
        try:
            scores[name] = scores_from(Path(d), arms[name])
            rows[name] = row_counts(Path(d), arms[name])
        except ValueError as e:
            problems.append(str(e))
    if len(scores) < len(sets):
        print("invalid, no G2 report written: " + "; ".join(problems), file=sys.stderr)
        return 2
    verdict = g2_verdict(scores["starved"], scores["kb"], seed=scores["seed-kb"], approvals=approvals,
                         seal_ok=seal_ok, heldout=heldout, list_author=author,
                         coverage=problems + coverage_problems(sets["starved"], sets["kb"], sets["seed-kb"], rows))
    if not verdict.valid:
        print("invalid, no G2 report written: " + "; ".join(verdict.reasons), file=sys.stderr)
        return 2
    word = "PASS" if verdict.passed else "FAIL"
    now = datetime.now(UTC)
    body = [f"# G2: {word}", "", f"- starved graph: {scores['starved']}", f"- graph_kb (curated): {scores['kb']}",
            f"- graph_kb (seed-only control): {scores['seed-kb']}", f"- kb commit: {commit['kb']}",
            f"- seed commit: {commit['seed-kb']}", f"- e2ekg commit: {recs[0].get('e2ekg_sha')}",
            f"- removal list seal: {seal_info['sha256']}", f"- measured: {now.isoformat()}"]
    body += [f"- {r}" for r in verdict.reasons]
    report = Path(args.report) if args.report else removal.REPO_ROOT / "reports" / f"g2-{now:%Y-%m-%d}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(body) + "\n")
    print(f"G2 {word}" + "".join(f"; {r}" for r in verdict.reasons) + f" ({report})")
    return 0 if verdict.passed else 1


def _metrics(args) -> int:
    state = Path(args.state_dir)
    queue = FlagQueue(args.db or state / "flags.db")
    records = read_approval_records(state / "approvals.jsonl")
    rej = state / "rejections.jsonl"
    rejections = sum(1 for line in rej.read_text().splitlines() if line.strip()) if rej.is_file() else 0
    merged_at: dict[str, datetime] = {}
    for r in records:
        merged_at.setdefault(r["branch"], datetime.fromisoformat(r["at"]))
    hours = []
    for f in queue.list():
        at = merged_at.get((f.resolution or {}).get("merged"))
        if at is not None:
            hours.append((at - f.created_at).total_seconds() / 3600)
    out = {
        "curator": curator_metrics(queue, to_approvals(records), rejections=rejections, resolution_hours=hours),
        "corpus": corpus_metrics(Path(args.bundle), datetime.now(UTC)),
    }
    print(json.dumps(out, indent=2))
    return 0
