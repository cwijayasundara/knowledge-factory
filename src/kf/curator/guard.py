"""Write guard (spec 5.4): tool permissions, not prompt rules, keep the curator off protected paths."""

from __future__ import annotations

import posixpath
from fnmatch import fnmatchcase
from pathlib import Path


class WriteDenied(Exception):
    pass


# Repo-relative patterns; fnmatch's * also matches "/", so "raw/*" covers every depth.
DEFAULT_DENY = [
    "raw", "raw/*", "*/raw", "*/raw/*",
    "bundle/computations", "bundle/computations/*",
    "kf-profile.yaml", "*/kf-profile.yaml",
    "AGENTS.md", "*/AGENTS.md",
    "CODEOWNERS", "*/CODEOWNERS",
    "*tiers.py",                      # tier rules
    "*curator/*prompt*",              # the curator prompt
    ".git", ".git/*", "*/.git", "*/.git/*",
    "ontology", "ontology/*",         # the ontology goes through e2ekg's proposal flow
    "*.ttl",                          # the curator never writes Turtle
]
FORBIDDEN_PART = "_answers"  # anti-goal A1: the answer key is never reachable


def mentions_answers(path: object) -> bool:
    """True when the path names the answer key in any letter case (macOS and Windows file systems
    are case-insensitive, so _Answers opens _answers)."""
    return FORBIDDEN_PART in str(path).casefold()


class WriteGuard:
    """Checks repo-relative paths. With a root, symlinks are resolved and must stay inside it."""

    def __init__(self, deny: list[str], *, root: Path | None = None):
        self.deny = list(deny)
        self.root = Path(root) if root is not None else None

    @classmethod
    def default(cls, *, root: Path | None = None) -> WriteGuard:
        return cls(DEFAULT_DENY, root=root)

    def _match(self, rel: str) -> None:
        if mentions_answers(rel):
            raise WriteDenied(f"{rel}: denied")
        for pattern in self.deny:
            if fnmatchcase(rel, pattern):
                raise WriteDenied(f"{rel}: denied by {pattern!r}")

    def check(self, path: str) -> None:
        p = str(path).replace("\\", "/")
        if mentions_answers(p):
            raise WriteDenied(f"{path}: denied")
        if p.startswith("/"):
            raise WriteDenied(f"{path}: absolute paths are denied")
        rel = posixpath.normpath(p)
        if rel in (".", "..") or rel.startswith("../"):
            raise WriteDenied(f"{path}: resolves outside the repo")
        self._match(rel)
        if self.root is not None:
            root = self.root.resolve()
            target = (root / rel).resolve()
            if target != root and root not in target.parents:
                raise WriteDenied(f"{path}: resolves outside the repo")
            self._match(target.relative_to(root).as_posix())
