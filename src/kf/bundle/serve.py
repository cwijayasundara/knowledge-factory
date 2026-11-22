"""Read-only serving of a bundle: current-knowledge filter, search, read, frozen snapshot."""

from __future__ import annotations

import re
import shutil
import subprocess
import tarfile
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from kf.bundle.okf import Concept, _ts, is_human_reviewed, load_concept

MAX_HOPS = 5
_LINK = re.compile(r"\]\(([^)\s]+)\)")


@dataclass(frozen=True)
class Hit:
    path: str
    title: str
    snippet: str


def _all_concepts(bundle: Path) -> list[Concept]:
    out = []
    for f in sorted(Path(bundle).rglob("*.md")):
        rel = f.relative_to(bundle).as_posix()
        if rel == "index.md" or rel.endswith("/index.md"):
            continue
        try:
            c = load_concept(f)
        except (ValueError, OSError):
            continue
        c.path = rel
        out.append(c)
    return out


def _stale(front: dict, now: datetime) -> bool:
    raw = front.get("stale_after")
    if raw in (None, ""):
        return False
    at = _ts(raw)
    return at is None or now >= at  # unparseable is never treated as fresh


def _is_current(c: Concept, now: datetime) -> bool:
    f = c.front
    return (
        f.get("status", "stable") == "stable"
        and not _stale(f, now)
        and f.get("x-kf-review") != "proposed"
    )


def current_concepts(bundle: Path, *, now: datetime, human_reviewed_only: bool = False) -> list[Concept]:
    out = [c for c in _all_concepts(Path(bundle)) if _is_current(c, now)]
    if human_reviewed_only:
        out = [c for c in out if is_human_reviewed(c.front)]
    return out


def _title(c: Concept) -> str:
    return str(c.front.get("title") or Path(c.path).stem)


def _snippet(text: str, terms: list[str]) -> str:
    for line in text.splitlines():
        if any(t in line.lower() for t in terms):
            return line.strip()[:200]
    return ""


def kb_search(bundle: Path, query: str, *, now: datetime, limit: int = 10) -> list[Hit]:
    bundle = Path(bundle)
    terms = [t for t in re.findall(r"\w+", query.lower()) if t]
    if not terms:
        return []
    current = {c.path: c for c in current_concepts(bundle, now=now)}
    ordered: list[str] = []
    index = bundle / "index.md"
    if index.is_file():  # index first: lines naming the query point at concepts
        for line in index.read_text(encoding="utf-8").splitlines():
            if any(t in line.lower() for t in terms):
                for target in _LINK.findall(line):
                    p = target.lstrip("/")
                    if p in current and p not in ordered:
                        ordered.append(p)
    scored = []
    for p, c in current.items():
        if p in ordered:
            continue
        text = f"{_title(c)}\n{c.front.get('description', '')}\n{c.body}".lower()
        score = sum(text.count(t) for t in terms)
        if score:
            scored.append((-score, p))
    ordered += [p for _, p in sorted(scored)]
    hits = []
    for p in ordered[:limit]:
        c = current[p]
        snip = _snippet(f"{c.front.get('description', '')}\n{c.body}", terms) or str(c.front.get("description", ""))
        hits.append(Hit(p, _title(c), snip))
    return hits


def _safe(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("/") or re.match(r"^[A-Za-z]:", p) or ".." in p.split("/"):
        raise ValueError(f"path must be bundle-relative without '..': {path!r}")
    return p


def kb_read(bundle: Path, path: str, *, now: datetime) -> str:
    bundle = Path(bundle)
    rel = _safe(path)
    seen: list[str] = []
    for _ in range(MAX_HOPS + 1):
        f = bundle / rel
        if not f.is_file():
            return f"not found: {rel}"
        c = load_concept(f)
        status = c.front.get("status", "stable")
        if status == "deprecated":
            target = c.front.get("superseded_by")
            seen.append(rel)
            if not target:
                return f"deprecated: {rel} has no replacement"
            nxt = _safe(str(target).lstrip("/"))
            if nxt in seen:
                return f"superseded-by cycle: {' -> '.join(seen + [nxt])}"
            if len(seen) > MAX_HOPS:
                break
            msg = f"superseded by {nxt}"
            rel = nxt
            if len(seen) == 1:
                first = msg
            continue
        if status != "stable" or _stale(c.front, now) or c.front.get("x-kf-review") == "proposed":
            return f"not current: {rel}"
        text = f.read_text(encoding="utf-8")
        return f"{first}\n\n{text}" if seen else text
    return f"superseded-by chain longer than {MAX_HOPS} hops: {' -> '.join(seen)}"


def snapshot(bundle: Path, dest: Path, *, commit: str) -> Path:
    """Copy the bundle tree as of 'commit' into dest/<commit>/ (frozen; later edits do not show)."""
    out = Path(dest) / commit
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    proc = subprocess.run(
        ["git", "archive", "--format=tar", commit, "--", "."],
        cwd=bundle,
        capture_output=True,
        check=True,
    )
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        tar.extractall(out, filter="data")
    return out
