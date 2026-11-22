"""Bundle CI: official OKF validator, profile lint, links, PII, curator-verified guard."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from kf.bundle.okf import Concept, load_concept
from kf.bundle.profile import Profile

REPO_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = REPO_ROOT / "external" / "okf" / "skills" / "okf-generate" / "scripts" / "validate.py"
DEFAULT_PROFILE = REPO_ROOT / "kf-profile.yaml"

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
CODE_RE = re.compile(r"```.*?```|`[^`]*`", re.S)
PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<![\w.])(?:\+?\d{1,3}[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    "key": re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|xox[abp]-[A-Za-z0-9-]{10,})"
        r"|(?i:api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{16,}"
    ),
}


@dataclass(frozen=True)
class Issue:
    check: str
    path: str
    message: str


@dataclass
class CiReport:
    ok: bool
    issues: list[Issue] = field(default_factory=list)


def _visible(bundle: Path) -> list[Path]:
    return [
        p for p in sorted(bundle.rglob("*.md"))
        if not any(part.startswith(".") for part in p.relative_to(bundle).parts)
    ]


def _concept_files(bundle: Path) -> list[Path]:
    return [p for p in _visible(bundle) if p.name not in ("index.md", "log.md")]


def _rel(bundle: Path, p: Path) -> str:
    return p.relative_to(bundle).as_posix()


def run_validator(bundle: Path) -> list[Issue]:
    if not VALIDATOR.is_file():
        return [Issue("okf_validator", str(VALIDATOR), "validator missing; run scripts/fetch_okf.sh")]
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bundle), "--strict"], capture_output=True, text=True
    )
    if proc.returncode == 0:
        return []
    out = (proc.stdout + proc.stderr).strip()
    return [Issue("okf_validator", str(bundle), f"validate.py --strict exited {proc.returncode}: {out}")]


def lint_bundle(bundle: Path, profile: Profile) -> list[Issue]:
    issues: list[Issue] = []
    for f in _concept_files(bundle):
        rel = _rel(bundle, f)
        try:
            front = load_concept(f).front
        except ValueError as e:
            issues.append(Issue("profile", rel, str(e)))
            continue
        if f.name == "SKILL.md":
            if "type" in front:
                issues.append(Issue("profile", rel, "SKILL.md must not have a type: key"))
            continue
        if "x-kf-kind" not in front:
            continue
        kind = front["x-kf-kind"]
        if kind not in profile.kinds:
            issues.append(Issue("profile", rel, f"x-kf-kind {kind!r} not in {sorted(profile.kinds)}"))
            continue
        for key in profile.kinds[kind].required:
            if key not in front:
                issues.append(Issue("profile", rel, f"{kind} concept missing required key {key}"))
        for key, allowed in profile.enums.items():
            if key in front and (isinstance(front[key], bool) or front[key] not in allowed):
                issues.append(Issue("profile", rel, f"{key} value {front[key]!r} not in {allowed}"))
    return issues


def check_links(bundle: Path) -> list[Issue]:
    issues = []
    root = bundle.resolve()
    for f in _visible(bundle):
        body = CODE_RE.sub("", load_concept(f).body)
        for target in LINK_RE.findall(body):
            if SCHEME_RE.match(target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0].split("?", 1)[0]
            if not path:
                continue
            dest = ((root / path.lstrip("/")) if path.startswith("/") else (f.parent / path)).resolve()
            if not dest.exists() or root not in (dest, *dest.parents):
                issues.append(Issue("links", _rel(bundle, f), f"broken link: {target}"))
    return issues


def scan_pii(bundle: Path) -> list[Issue]:
    issues = []
    for f in _visible(bundle):
        text = f.read_text(encoding="utf-8")
        for name, rx in PII_PATTERNS.items():
            if rx.search(text):
                issues.append(Issue("pii", _rel(bundle, f), f"possible {name} found"))
    return issues


def _verified(front: dict) -> list[tuple[str, str]]:
    return [(str(v.get("by")), str(v.get("at"))) for v in front.get("verified") or [] if isinstance(v, dict)]


def no_curator_verified(bundle: Path, base: Path) -> list[Issue]:
    issues = []
    for f in _concept_files(bundle):
        rel = _rel(bundle, f)
        head: Concept = load_concept(f)
        old = base / rel
        old_keys = set(_verified(load_concept(old).front)) if old.is_file() else set()
        added = [k for k in _verified(head.front) if k not in old_keys]
        if not added:
            continue
        gen = head.front.get("generated")
        by = str(gen.get("by", "")) if isinstance(gen, dict) else ""
        if by.startswith("kf-curator"):
            issues.append(Issue("no_curator_verified", rel, "verified entry added to a curator-generated concept"))
        elif any(not b.startswith("human:") for b, _ in added):
            issues.append(Issue("no_curator_verified", rel, "non-human verified entry added"))
    return issues


def run_ci(bundle: Path, *, base: Path | None = None, profile: Path | None = None) -> CiReport:
    bundle = Path(bundle)
    issues = run_validator(bundle)
    issues += lint_bundle(bundle, Profile.load(profile or DEFAULT_PROFILE))
    issues += check_links(bundle)
    issues += scan_pii(bundle)
    if base is not None:
        issues += no_curator_verified(bundle, Path(base))
    return CiReport(ok=not issues, issues=issues)
