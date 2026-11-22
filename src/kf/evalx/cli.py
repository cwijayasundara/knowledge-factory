"""Handlers for `kf eval run|g2|metrics` (parser lives in kf.cli)."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from kf.evalx import removal
from kf.evalx.g2 import g2_verdict, read_approval_records, to_approvals
from kf.evalx.metrics import corpus_metrics, curator_metrics
from kf.evalx.runner import SealRefused, run_eval, scores_from
from kf.evalx.split import CURATION_SEEDS, HELDOUT_SEEDS
from kf.flags.queue import FlagQueue


def run(args) -> int:
    return {"run": _run, "g2": _g2, "metrics": _metrics}[args.sub](args)


def _run(args) -> int:
    seeds, prefix = (HELDOUT_SEEDS, "data_heldout") if args.heldout else (CURATION_SEEDS, "data_curation")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    parent = Path(args.state_dir) / "evals" / stamp
    for seed in seeds:
        try:
            run_dir = run_eval(
                arms=args.arms.split(","), scenarios=args.scenarios.split(","), runs=args.runs,
                data_root=Path(args.data_base) / prefix / f"seed-{seed}", bundle_commit=args.bundle_commit,
                starve=args.starve, state_dir=Path(args.state_dir), heldout=args.heldout,
                test_run=args.test_run, now=args.now, run_dir=parent / f"seed-{seed}", bundle=Path(args.bundle),
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
    return [json.loads(f.read_text()) for f in files]


def _g2(args) -> int:
    starved_recs, kb_recs = _records(args.starved), _records(args.kb)
    problems = []
    if not all(r["starve"] for r in starved_recs):
        problems.append("--starved holds a run that was not starved")
    if any(r["starve"] for r in kb_recs):
        problems.append("--kb holds a starved run")
    seal_now = removal.verify_seal(Path(args.list), Path(args.seal_file))
    recs = starved_recs + kb_recs
    seal_ok = seal_now and all(r["seal_ok"] for r in recs)
    heldout = all(r["heldout"] for r in recs) and not any(r["test_run"] for r in recs)
    approvals = to_approvals(read_approval_records(Path(args.state_dir) / "approvals.jsonl"))
    verdict = g2_verdict(scores_from(Path(args.starved), "graph"), scores_from(Path(args.kb), "graph_kb"),
                         approvals=approvals, seal_ok=seal_ok, heldout=heldout)
    if problems:
        print("invalid: " + "; ".join(problems), file=sys.stderr)
        return 2
    if not verdict.valid:
        print("invalid, no G2 report written: " + "; ".join(verdict.reasons), file=sys.stderr)
        return 2
    starved, kb = scores_from(Path(args.starved), "graph"), scores_from(Path(args.kb), "graph_kb")
    word = "PASS" if verdict.passed else "FAIL"
    body = [f"# G2: {word}", "", f"- starved graph: {starved}", f"- graph_kb: {kb}",
            f"- kb commit: {kb_recs[0]['commit']}", f"- measured: {datetime.now(UTC).isoformat()}"]
    body += [f"- {r}" for r in verdict.reasons]
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(body) + "\n")
    print(f"G2 {word}" + "".join(f"; {r}" for r in verdict.reasons))
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
