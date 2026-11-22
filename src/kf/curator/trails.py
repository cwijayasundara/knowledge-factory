"""Stage 1 input: what past eval runs' agents hit and asked to correct (e2ekg Trail output).

e2ekg's eval runner saves each LLM run as <run_dir>/runs/<scenario>__<arm>__<run>.json; the
Trail is that file's "trail" key ({"steps": [{i, at, tool, args, output}], "findings": [...]}).
A tool error is a step whose output starts "error:" (Trail.on_tool_error). A correction is what an
agent asked to change through kf_flag: its suggested_fix, else its summary.

Everything here is untrusted data. It reaches the model only as quoted text in a tool result
(CuratorTools.list_trails), never in a prompt. Free text is cut to CORRECTION_CHARS, and anything
mentioning the answer key is dropped (the trails are as-of views; this is defense in depth: any key or text containing "answer").
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from kf.curator.guard import mentions_answers

CORRECTION_CHARS = 500


@dataclass(frozen=True)
class TrailSummary:
    run_id: str
    scenario: str
    tool_errors: int
    corrections: list[str] = field(default_factory=list)


def _has_answer_key(value) -> bool:
    if isinstance(value, dict):
        return any("answer" in str(k).lower() or _has_answer_key(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_has_answer_key(v) for v in value)
    return isinstance(value, str) and (mentions_answers(value) or "answer" in value.lower())


def _summarise(run_id: str, scenario: str, trail: dict) -> TrailSummary:
    errors, corrections = 0, []
    for step in trail.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if str(step.get("output") or "").startswith("error:"):
            errors += 1
        args = step.get("args")
        if step.get("tool") == "kf_flag" and isinstance(args, dict) and not _has_answer_key(args):
            text = args.get("suggested_fix") or args.get("summary")
            if isinstance(text, str) and text.strip():
                corrections.append(text.strip()[:CORRECTION_CHARS])
    return TrailSummary(run_id, scenario, errors, corrections)


def load_trails(eval_run_dir: Path) -> list[TrailSummary]:
    """One summary per saved run file that carries a trail (engine and raw_only arms have none)."""
    out = []
    for p in sorted((Path(eval_run_dir) / "runs").glob("*.json")):
        try:
            rec = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        trail = rec.get("trail") if isinstance(rec, dict) else None
        if isinstance(trail, dict):
            out.append(_summarise(p.stem, str(rec.get("scenario") or p.stem.split("__")[0]), trail))
    return out
