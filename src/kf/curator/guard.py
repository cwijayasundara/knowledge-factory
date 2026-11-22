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
]
FORBIDDEN_PART = "_answers"  # anti-goal A1: the answer key is never reachable


class WriteGuard:
    """Checks repo-relative paths. With a root, symlinks are resolved and must stay inside it."""

    def __init__(self, deny: list[str], *, root: Path | None = None):
        self.deny = list(deny)
        self.root = Path(root) if root is not None else None

    @classmethod
    def default(cls, *, root: Path | None = None) -> WriteGuard:
        return cls(DEFAULT_DENY, root=root)

    def _match(self, rel: str) -> None:
        if FORBIDDEN_PART in rel:
            raise WriteDenied(f"{rel}: denied")
        for pattern in self.deny:
            if fnmatchcase(rel, pattern):
                raise WriteDenied(f"{rel}: denied by {pattern!r}")

    def check(self, path: str) -> None:
        p = str(path).replace("\\", "/")
        if FORBIDDEN_PART in p:
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
