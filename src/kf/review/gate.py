"""Eval gate (spec 5.3): a Tier 1+ change must not regress held-out scores."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scores:
    top1: int  # scenario-runs with the right top-1 root cause
    runs: int  # total scenario-runs in the arm
    trap: int  # scenario-runs that fell into a trap
    control_fp: int  # control scenario-runs with a false positive


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def eval_gate(base: Scores, head: Scores, *, tolerance_runs: int = 1) -> GateResult:
    """Fail if top1 drops by more than tolerance_runs scenario-runs, or trap/control_fp rise."""
    reasons = []
    if base.top1 - head.top1 > tolerance_runs:
        reasons.append(
            f"top1 dropped {base.top1} -> {head.top1} (tolerance {tolerance_runs} of {head.runs} runs)"
        )
    if head.trap > base.trap:
        reasons.append(f"trap rate rose {base.trap} -> {head.trap}")
    if head.control_fp > base.control_fp:
        reasons.append(f"control false positives rose {base.control_fp} -> {head.control_fp}")
    return GateResult(not reasons, reasons)
