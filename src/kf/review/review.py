"""Review and merge (spec 5.3): CI, tier, gate, approval, verified stamp, --no-ff merge, flag resolution.

Trust model: everything here is local files (state/runs/<run_id>.json, state/approvals.jsonl) and
anyone with write access to the repo is trusted. The "judge by a different model" rule for Tier 2
is enforced where judge_ok is written (a later task), not here; this module only reads judge_ok
(default false). Eval scores are recorded in the run record and the gate is computed from them by
the caller, never read as a self-asserted pass flag. Tier 3 is humans only: a curator branch
(kf/*) carrying a Tier 3 change is refused.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from kf.bundle.ci import DEFAULT_PROFILE, run_ci
from kf.bundle.okf import dump_concept, parse_concept, stamp_verified
from kf.bundle.profile import Profile
from kf.flags.models import FlagStatus
from kf.flags.queue import FlagQueue
from kf.review.gate import GateResult
from kf.review.tiers import ChangedFile, Tier, classify

BUNDLE = "bundle"
MAIN = "main"
SCRIPTED_ID = "scripted-test"
_IDENT = ("-c", "user.name=kf-review", "-c", "user.email=kf-review@localhost")


class ReviewRefused(Exception):
    pass


class ScriptedNotAllowed(ReviewRefused):
    pass


class CiFailed(ReviewRefused):
    pass


class GateRequired(ReviewRefused):
    pass


class JudgeRequired(ReviewRefused):
    pass


class CuratorTier3Refused(ReviewRefused):
    pass


@dataclass(frozen=True)
class Approval:
    by: str
    kind: Literal["person", "scripted", "auto"]  # "auto" only from auto_merge_tier0
    at: datetime


@dataclass
class MergeResult:
    merged: bool
    tier: Tier
    merge_sha: str | None = None
    resolved_flags: list[int] = field(default_factory=list)


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def _show(repo: Path, ref: str, path: str) -> bytes | None:
    p = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True)
    return p.stdout if p.returncode == 0 else None


def _as_dict(path: str, raw: bytes | None) -> dict | None:
    if raw is None:
        return None
    text = raw.decode("utf-8", errors="replace")
    if path.endswith(".md"):
        try:
            c = parse_concept(path, text)
        except ValueError:
            return {"body": text}
        return {**c.front, "body": c.body}
    return {"body": text}


def _rel(path: str) -> str:
    return path.removeprefix(BUNDLE + "/")


def changed_files(repo: Path, branch: str) -> list[ChangedFile]:
    base = _git(repo, "merge-base", MAIN, branch)
    out = _git(repo, "diff", "--name-status", "--no-renames", base, branch)
    files = []
    for line in out.splitlines():
        code, path = line.split("\t", 1)
        before = _as_dict(path, _show(repo, base, path))
        after = _as_dict(path, _show(repo, branch, path))
        change = {"A": "added", "D": "removed"}.get(code[0], "modified")
        if change == "modified" and after and after.get("status") == "deprecated":
            change = "deprecated"
        files.append(ChangedFile(_rel(path), change, before, after))
    return files


def _export(repo: Path, ref: str, dest: Path) -> Path:
    """Materialise the bundle at ref under dest; returns the bundle dir."""
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", ref, BUNDLE], cwd=repo, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest / BUNDLE


def tier_of(repo: Path, branch: str) -> Tier:
    return classify(changed_files(Path(repo), branch), profile=Profile.load(DEFAULT_PROFILE))


def record_rejection(repo: Path, branch: str, by: str, reason: str, at: datetime) -> None:
    path = Path(repo) / "state" / "rejections.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({"branch": branch, "by": by, "reason": reason, "at": at.astimezone(UTC).isoformat()}) + "\n")


def read_run_record(repo: Path, branch: str) -> dict:
    p = repo / "state" / "runs" / f"{branch.removeprefix('kf/')}.json"
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    return rec if isinstance(rec, dict) else {}


def _log_approval(repo: Path, branch: str, a: Approval, test_run: bool, tier: Tier, role: str) -> None:
    path = repo / "state" / "approvals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "branch": branch, "by": a.by, "kind": a.kind, "role": role, "test_run": test_run,
        "tier": int(tier), "at": a.at.astimezone(UTC).isoformat(),
    }
    with path.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _log_event(repo: Path, rec: dict) -> None:
    path = repo / "state" / "approvals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def _flag_ids(front: dict) -> list[int]:
    ids = []
    for v in front.get("x-kf-flags") or []:
        if isinstance(v, int) and not isinstance(v, bool):
            ids.append(v)
        elif isinstance(v, str) and v.strip().isdigit():
            ids.append(int(v))
    return ids


def _resolve(queue: FlagQueue, flag_id: int, branch: str) -> bool:
    try:
        current = next(f for f in queue.list() if f.id == flag_id).status
    except StopIteration:
        return False
    if current not in (FlagStatus.open, FlagStatus.held, FlagStatus.triaged, FlagStatus.in_review):
        return False  # resolved, declined or duplicate: leave alone
    if current in (FlagStatus.open, FlagStatus.held):
        queue.set_status(flag_id, FlagStatus.triaged)
        current = FlagStatus.triaged
    if current is FlagStatus.triaged:
        queue.set_status(flag_id, FlagStatus.in_review)
    queue.set_status(flag_id, FlagStatus.resolved, resolution={"merged": branch})
    return True


def _check_scripted(a: Approval | None, test_run: bool) -> None:
    if a is not None and a.kind == "scripted" and not test_run:
        raise ScriptedNotAllowed("scripted approvals are allowed only on --test-run runs")


def approve_and_merge(
    repo: Path,
    branch: str,
    *,
    approval: Approval | None,
    test_run: bool,
    gate: GateResult | None,
    queue: FlagQueue,
    second_approval: Approval | None = None,
) -> MergeResult:
    repo = Path(repo)
    _check_scripted(approval, test_run)
    _check_scripted(second_approval, test_run)
    if _git(repo, "rev-parse", "--abbrev-ref", "HEAD") != MAIN:
        raise ReviewRefused(f"repo must have {MAIN} checked out")
    if _git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ReviewRefused("working tree has uncommitted changes")

    # 1. CI on the branch as the curator left it, against main's bundle.
    with tempfile.TemporaryDirectory() as tmp:
        head_bundle = _export(repo, branch, Path(tmp) / "head")
        base_bundle = _export(repo, MAIN, Path(tmp) / "base")
        report = run_ci(head_bundle, base=base_bundle)
    if not report.ok:
        raise CiFailed("; ".join(f"{i.check} {i.path}: {i.message}" for i in report.issues))

    # 2. Tier and approval rules.
    files = changed_files(repo, branch)
    tier = classify(files, profile=Profile.load(DEFAULT_PROFILE))
    approvals: list[tuple[Approval, str]] = []
    if tier is Tier.T3:
        if branch.startswith("kf/"):
            raise CuratorTier3Refused("tier 3 is humans only: the curator may file a flag, not a diff")
        if approval is None or approval.kind != "person":
            if not (approval is not None and test_run):
                raise ReviewRefused("tier 3 change needs a person approval")
    if tier >= Tier.T1:
        if approval is None:
            raise ReviewRefused(f"tier {int(tier)} change needs a human approval")
        if gate is None or not gate.passed:
            reasons = "; ".join(gate.reasons) if gate else "no eval gate result"
            raise GateRequired(f"tier {int(tier)} change needs a passing eval gate: {reasons}")
        approvals.append((approval, "approver"))
        if tier is Tier.T2:
            second = second_approval is not None and second_approval.by != approval.by
            if second:
                approvals.append((second_approval, "second"))
            elif not read_run_record(repo, branch).get("judge_ok", False):
                raise JudgeRequired("tier 2+ needs a second distinct approver or judge_ok on the run record")

    # 3. Stamp verified on a later branch commit, then merge --no-ff.
    resolved: list[int] = []
    flag_ids: set[int] = set()
    with tempfile.TemporaryDirectory() as tmp:
        wt = Path(tmp) / "wt"
        _git(repo, "worktree", "add", "-q", "--detach", str(wt), branch)
        try:
            if approval is not None and tier >= Tier.T1:
                who = SCRIPTED_ID if approval.kind == "scripted" else approval.by
                for f in files:
                    if f.change in ("removed",) or not f.path.endswith(".md") or f.after is None:
                        continue
                    if f.path in ("index.md", "log.md") or f.path.endswith("/index.md") or f.path.endswith("/log.md"):
                        continue
                    p = wt / BUNDLE / f.path
                    if not p.is_file():
                        continue
                    c = parse_concept(f.path, p.read_text(encoding="utf-8"))
                    c.front = stamp_verified(c.front, f"human:{who}", approval.at)
                    c.front["x-kf-review"] = "approved"
                    p.write_text(dump_concept(c), encoding="utf-8")
                    flag_ids.update(_flag_ids(c.front))
                _git(wt, "add", "-A")
                if _git(wt, "status", "--porcelain"):
                    _git(wt, *_IDENT, "commit", "-q", "-m", f"review: stamp verified by human:{who}")
            else:
                for f in files:
                    if f.after:
                        flag_ids.update(_flag_ids(f.after))
            tip = _git(wt, "rev-parse", "HEAD")
        finally:
            _git(repo, "worktree", "remove", "--force", str(wt))
    # Record approvals first: a merged branch must never lack an approval record.
    for a, role in approvals:
        _log_approval(repo, branch, a, test_run, tier, role)
    try:
        _git(repo, *_IDENT, "merge", "--no-ff", "-q", "-m", f"merge {branch} (tier {int(tier)})", tip)
    except RuntimeError as e:
        subprocess.run(["git", "merge", "--abort"], cwd=repo, capture_output=True)
        _log_event(repo, {"branch": branch, "event": "merge_failed", "error": str(e)})
        raise
    sha = _git(repo, "rev-parse", "HEAD")
    for fid in sorted(flag_ids):
        if _resolve(queue, fid, branch):
            resolved.append(fid)
    return MergeResult(True, tier, sha, resolved)


def _auto_refusal(f: ChangedFile, profile: Profile) -> str | None:
    if classify([f], profile=profile) is not Tier.T0:
        return f"{f.path} is not tier 0"
    if f.path in ("index.md", "log.md"):
        return None
    if f.change != "modified" or f.before is None or f.after is None:
        return f"{f.path} is not an in-place edit of an existing concept"
    if f.before.get("body") != f.after.get("body"):
        return f"{f.path} body changed"
    return None


def auto_merge_tier0(repo: Path, branch: str) -> MergeResult:
    """Merge a branch with no human approval only when it is purely mechanical: CI passes against
    main, every changed file classifies Tier 0 and no concept body changed. Never stamps verified,
    never resolves flags. Logs an approvals.jsonl line with kind "auto" (not an approval for g2 or
    metrics). Anything else is refused: use approve_and_merge."""
    repo = Path(repo)
    if _git(repo, "rev-parse", "--abbrev-ref", "HEAD") != MAIN:
        raise ReviewRefused(f"repo must have {MAIN} checked out")
    if _git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ReviewRefused("working tree has uncommitted changes")
    with tempfile.TemporaryDirectory() as tmp:
        head_bundle = _export(repo, branch, Path(tmp) / "head")
        base_bundle = _export(repo, MAIN, Path(tmp) / "base")
        report = run_ci(head_bundle, base=base_bundle)
    if not report.ok:
        raise CiFailed("; ".join(f"{i.check} {i.path}: {i.message}" for i in report.issues))
    files = changed_files(repo, branch)
    if not files:
        raise ReviewRefused("nothing to merge")
    profile = Profile.load(DEFAULT_PROFILE)
    why = [r for f in files if (r := _auto_refusal(f, profile))]
    if why:
        raise ReviewRefused("not auto-mergeable: " + "; ".join(why))
    _log_event(repo, {"branch": branch, "by": "auto", "kind": "auto", "role": "auto", "test_run": False,
                      "tier": 0, "at": datetime.now(UTC).isoformat()})
    try:
        _git(repo, *_IDENT, "merge", "--no-ff", "-q", "-m", f"merge {branch} (tier 0, auto)", branch)
    except RuntimeError as e:
        subprocess.run(["git", "merge", "--abort"], cwd=repo, capture_output=True)
        _log_event(repo, {"branch": branch, "event": "merge_failed", "error": str(e)})
        raise
    return MergeResult(True, Tier.T0, _git(repo, "rev-parse", "HEAD"), [])
