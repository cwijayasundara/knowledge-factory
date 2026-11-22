"""G2 verdict (spec 9b): graph_kb after curation vs the starved graph arm, on held-out seeds."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from kf.review.gate import Scores
from kf.review.review import Approval

MIN_GAIN_RUNS = 2


@dataclass(frozen=True)
class G2Result:
    valid: bool
    passed: bool
    reasons: list[str] = field(default_factory=list)


def read_approval_records(path: Path) -> list[dict]:
    """Approval lines of state/approvals.jsonl, minus voided ones.

    A `merge_failed` event line voids the approval lines of that branch logged immediately before
    it (one merge attempt logs its approver and, for tier 2, its second approver back to back)."""
    path = Path(path)
    if not path.is_file():
        return []
    lines = []
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if isinstance(rec, dict):
            lines.append(rec)
    kept: list[dict] = []
    for rec in lines:
        if rec.get("event") == "merge_failed":
            while kept and kept[-1].get("branch") == rec.get("branch") and "event" not in kept[-1]:
                kept.pop()
            continue
        kept.append(rec)
    return [r for r in kept if "event" not in r]


def to_approvals(records: list[dict]) -> list[Approval]:
    return [Approval(r["by"], r["kind"], datetime.fromisoformat(r["at"]).astimezone(UTC)) for r in records]


def read_approvals(path: Path) -> list[Approval]:
    return to_approvals(read_approval_records(path))


def g2_verdict(starved: Scores, kb: Scores, *, approvals: list[Approval], seal_ok: bool, heldout: bool) -> G2Result:
    invalid = []
    if not seal_ok:
        invalid.append("removal list seal missing or broken")
    if any(a.kind == "scripted" for a in approvals):
        invalid.append("a scripted approval is in the record")
    if not heldout:
        invalid.append("not measured on held-out seeds")
    if invalid:
        return G2Result(False, False, invalid)
    reasons = []
    if kb.top1 - starved.top1 < MIN_GAIN_RUNS:
        reasons.append(f"top1 gain {kb.top1 - starved.top1} (starved {starved.top1}, kb {kb.top1}); needs >= {MIN_GAIN_RUNS}")
    if kb.trap > starved.trap:
        reasons.append(f"trap rose {starved.trap} -> {kb.trap}")
    if kb.control_fp > starved.control_fp:
        reasons.append(f"control false positives rose {starved.control_fp} -> {kb.control_fp}")
    return G2Result(True, not reasons, reasons)
