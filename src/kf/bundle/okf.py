"""OKF concept files: YAML frontmatter plus Markdown body."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

BOM = chr(0xFEFF)


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps timestamps as the text the author wrote (OKF section 5)."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


@dataclass
class Concept:
    path: str
    front: dict = field(default_factory=dict)
    body: str = ""


def parse_concept(path: str, text: str) -> Concept:
    text = text.removeprefix(BOM)
    lines = text.split("\n")
    if lines[0].rstrip() != "---":
        return Concept(path, {}, text)
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            front = yaml.load("\n".join(lines[1:i]), Loader=_Loader) or {}
            if not isinstance(front, dict):
                raise ValueError(f"{path}: frontmatter is not a mapping")
            return Concept(path, front, "\n".join(lines[i + 1 :]))
    raise ValueError(f"{path}: unterminated frontmatter")


def load_concept(file: Path) -> Concept:
    return parse_concept(str(file), Path(file).read_text(encoding="utf-8"))


def dump_concept(c: Concept) -> str:
    front = yaml.safe_dump(c.front, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{front}---\n{c.body}"


def _ts(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00").replace("z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


SCRIPTED_STAMP = "human:scripted-test"  # the scripted test approver's stamp (spec 9c): never human-reviewed


def is_human_reviewed(front: dict) -> bool:
    """True when a human: verified entry (not the scripted test approver's) is at or after
    generated.at (current, OKF 5.3)."""
    generated = front.get("generated")
    gen_at = _ts(generated.get("at")) if isinstance(generated, dict) else None
    for v in front.get("verified") or []:
        if not isinstance(v, dict) or not str(v.get("by", "")).startswith("human:") or v.get("by") == SCRIPTED_STAMP:
            continue
        at = _ts(v.get("at"))
        if at is not None and (gen_at is None or at >= gen_at):
            return True
    return False


def stamp_verified(front: dict, by: str, at: datetime) -> dict:
    """Return a copy of front with a verified entry appended; history is kept."""
    out = copy.deepcopy(front)
    entry = {"by": by, "at": at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    out["verified"] = list(out.get("verified") or []) + [entry]
    return out
