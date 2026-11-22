"""Review tier classifier (spec 5.3): maps a change set to Tier 0-3, highest wins."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import PurePosixPath
from typing import Literal

from kf.bundle.profile import Profile


class Tier(IntEnum):
    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3


@dataclass(frozen=True)
class ChangedFile:
    path: str  # bundle-relative, except repo-root files (kf-profile.yaml, AGENTS.md, CODEOWNERS)
    change: Literal["added", "modified", "deprecated", "removed"]
    before: dict | None  # frontmatter plus "body"
    after: dict | None


_ROOT_PROTECTED = {"kf-profile.yaml", "AGENTS.md", "CODEOWNERS"}
_T0_PATHS = {"index.md", "log.md"}
# Frontmatter keys whose change alone, with an unchanged body, is mechanical.
_MECHANICAL_KEYS = {"x-kf-usage", "generated"}


def _is_protected(path: str) -> bool:
    p = PurePosixPath(path)
    if path in _ROOT_PROTECTED or p.parts[0] == "computations":
        return True
    # tier rules and the curator prompt
    return p.name == "tiers.py" or (p.parts[0] == "curator" and "prompt" in p.name)


def _is_human_reviewed(fm: dict) -> bool:
    return bool(fm.get("verified")) or fm.get("x-kf-review") == "approved"


def _classify_one(f: ChangedFile) -> Tier:
    if f.change == "removed" or _is_protected(f.path):
        return Tier.T3
    if f.path in _T0_PATHS:
        return Tier.T0
    before, after = f.before or {}, f.after or {}
    if f.change == "deprecated" or after.get("status") == "deprecated":
        return Tier.T2
    if after.get("x-kf-confidence") == "low":
        return Tier.T2

    if f.change == "modified":
        if f.before is None or f.after is None:
            return Tier.T2  # cannot show the edit is harmless
        if before.get("body") == after.get("body"):
            changed = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
            if changed <= _MECHANICAL_KEYS:
                return Tier.T0
        if before.get("status") == "stable" or _is_human_reviewed(before):
            return Tier.T2

    parts = PurePosixPath(f.path).parts
    if parts[0] == "skills" or parts[-1] == "SKILL.md":
        return Tier.T1
    if parts[0] == "data_access" or after.get("x-kf-kind") == "data_access":
        return Tier.T1
    if f.change == "added" and not after.get("sources"):
        return Tier.T2
    return Tier.T1


def classify(files: list[ChangedFile], *, profile: Profile) -> Tier:
    """Highest tier across files; an empty change set is Tier 0."""
    return max((_classify_one(f) for f in files), default=Tier.T0)
