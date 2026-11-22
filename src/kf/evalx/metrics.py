"""Curator and corpus metrics (spec 9b): what the factory does to the flag queue and the bundle."""

from __future__ import annotations

import statistics
from datetime import datetime
from pathlib import Path

from kf.bundle.ci import CODE_RE, LINK_RE, SCHEME_RE, _concept_files, _visible, check_links
from kf.bundle.okf import is_human_reviewed, load_concept
from kf.bundle.serve import _stale
from kf.flags.models import FlagStatus
from kf.flags.queue import FlagQueue
from kf.review.review import Approval


def flag_recurrence(queue: FlagQueue) -> int:
    """Flags that came back after a resolved change: reopened (open with a resolution on record), or
    filed again (same kind, target and summary) after an earlier flag was resolved."""
    flags = queue.list()
    resolved = {}
    for f in flags:
        if f.status is FlagStatus.resolved:
            resolved.setdefault((f.kind, f.target, f.summary), f.id)
    reopened = sum(1 for f in flags if f.status is FlagStatus.open and f.resolution)
    again = sum(1 for f in flags if f.status is not FlagStatus.resolved and not f.resolution
                and resolved.get((f.kind, f.target, f.summary), f.id) < f.id)
    return reopened + again


def _share(n: int, total: int) -> float | None:
    return n / total if total else None


def curator_metrics(queue: FlagQueue, approvals: list[Approval], *, rejections: int = 0,
                    resolution_hours: list[float] | None = None) -> dict:
    """`approvals` must already exclude voided ones (g2.read_approvals). Revert rate needs git
    history and is not computed here."""
    flags = queue.list()
    n = len(flags)
    by = lambda s: sum(1 for f in flags if f.status is s)  # noqa: E731
    return {
        "flags": n,
        "resolved": by(FlagStatus.resolved),
        "declined_share": _share(by(FlagStatus.declined), n),
        "held_share": _share(by(FlagStatus.held), n),
        "flag_recurrence": flag_recurrence(queue),
        "approvals_person": sum(1 for a in approvals if a.kind == "person" and not a.test_run),
        "approvals_scripted": sum(1 for a in approvals if a.kind == "scripted"),
        "review_acceptance_rate": _share(len(approvals), len(approvals) + rejections),
        "median_resolution_hours": statistics.median(resolution_hours) if resolution_hours else None,
    }


def corpus_metrics(bundle: Path, now: datetime) -> dict:
    """Citation coverage (a non-empty `sources` or `citations` list), human-reviewed ratio, stale
    ratio, orphans (concepts no other file links to) and broken links."""
    bundle = Path(bundle)
    files = _concept_files(bundle)
    concepts = []
    for f in files:
        try:
            concepts.append((f, load_concept(f)))
        except (ValueError, OSError):
            continue
    n = len(concepts)
    cited = sum(1 for _, c in concepts if c.front.get("sources") or c.front.get("citations"))
    linked: set[Path] = set()
    root = bundle.resolve()
    for f in _visible(bundle):
        try:
            body = CODE_RE.sub("", load_concept(f).body)
        except (ValueError, OSError):
            continue
        for target in LINK_RE.findall(body):
            path = target.split("#", 1)[0].split("?", 1)[0]
            if SCHEME_RE.match(target) or not path:
                continue
            dest = ((root / path.lstrip("/")) if path.startswith("/") else (f.parent / path)).resolve()
            if dest != f.resolve():
                linked.add(dest)
    return {
        "concepts": n,
        "citation_coverage": _share(cited, n),
        "human_reviewed_ratio": _share(sum(1 for _, c in concepts if is_human_reviewed(c.front)), n),
        "stale_ratio": _share(sum(1 for _, c in concepts if _stale(c.front, now)), n),
        "orphans": sum(1 for f, _ in concepts if f.resolve() not in linked),
        "broken_links": len(check_links(bundle)),
    }
