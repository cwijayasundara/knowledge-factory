"""The knowledge-starved baseline's removal list (spec 7, 9b) and its seal.

Each item deletes one `match` text from one e2ekg prompt file (`prompts/<name>.md`) for every
LLM arm (e2ekg patch 0003, env E2EKG_STARVE). An item must say where the removed knowledge is
derivable from (catalog, logs, tags), so the curator is never asked for what it cannot know.

The real list lives outside the repo working tree (spec 9c: the blind reviewer works in the repo
and must not see it): `--list`, else $KF_REMOVAL_LIST, else ~/.kf/removal.yaml. The tracked
evalx/removal.template.yaml is only a template. The list is sealed before the first measured run:
`seal` writes the sha256 of the file's bytes, the list author and the time to the seal file
(integration/removal.seal), which is committed alone; `verify_seal` checks the list is unchanged
since. An empty list is refused: it would make a "starved" baseline that starves nothing.
"""
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

REPO_ROOT = Path(__file__).resolve().parents[3]
LIST_ENV = "KF_REMOVAL_LIST"
TEMPLATE = REPO_ROOT / "evalx" / "removal.template.yaml"
DEFAULT_SEAL = REPO_ROOT / "integration" / "removal.seal"  # state/ is git-ignored; the seal is committed


class RemovalRefused(ValueError):
    pass


def default_list() -> Path:
    """$KF_REMOVAL_LIST, else ~/.kf/removal.yaml (outside the repo working tree)."""
    return Path(os.environ.get(LIST_ENV) or Path.home() / ".kf" / "removal.yaml").expanduser()


def kf_home() -> Path:
    """$KF_HOME, else ~/.kf: the list author's private area outside the repo."""
    return Path(os.environ.get("KF_HOME") or Path.home() / ".kf").expanduser()


def write_private_copy(src: Path, dest: Path, *, area: Path) -> Path:
    """Copy the list to dest (mode 0600), every directory from area down to dest's parent mode 0700."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    d, area = dest.parent, Path(area)
    while True:
        os.chmod(d, 0o700)
        if d == area or area not in d.parents:
            break
        d = d.parent
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, Path(src).read_bytes())
    finally:
        os.close(fd)
    return dest


def inside_repo(path: Path, repo: Path = REPO_ROOT) -> bool:
    p, r = Path(path).expanduser().resolve(), Path(repo).resolve()
    return p == r or r in p.parents

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RemovalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Text
    file: Annotated[str, StringConstraints(pattern=r"^prompts/[A-Za-z0-9_]+\.md$")]
    match: Annotated[str, StringConstraints(min_length=1)]  # exact text, not stripped
    why_derivable_from: Text


class RemovalList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RemovalItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [i.id for i in self.items]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate removal item ids: {dupes}")
        return self

    @classmethod
    def load(cls, path: Path) -> "RemovalList":
        data = yaml.safe_load(Path(path).read_text()) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected a mapping with an 'items' list")
        return cls.model_validate({**data, "items": data.get("items") or []})


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def seed_overlaps(bundle: Path, removal: RemovalList) -> list[str]:
    """Ids of removal items whose match text (whitespace and case normalized) appears in any bundle file.

    A seed bundle that already holds a removed text would hand the starved baseline its knowledge back."""
    texts = [_norm(p.read_text(encoding="utf-8", errors="replace"))
             for p in sorted(Path(bundle).rglob("*")) if p.is_file() and ".git" not in p.parts]
    return [i.id for i in removal.items if _norm(i.match) and any(_norm(i.match) in t for t in texts)]


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_nonempty(path: Path) -> RemovalList:
    """The list at `path`; RemovalRefused when it has no items or does not parse. The error names
    fields and line numbers only, never the list's text (it may reach logs a blind reviewer reads)."""
    from pydantic import ValidationError

    try:
        rl = RemovalList.load(path)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" near line {mark.line + 1}" if mark is not None else ""
        raise RemovalRefused(f"{path}: the removal list is not valid YAML{where}") from None
    except ValidationError as e:
        fields = sorted({".".join(map(str, err["loc"])) for err in e.errors(include_input=False)})
        raise RemovalRefused(f"{path}: the removal list does not validate: {', '.join(fields)}") from None
    except ValueError:
        raise RemovalRefused(f"{path}: expected a mapping with an 'items' list") from None
    if not rl.items:
        raise RemovalRefused(f"{path}: the removal list has no items (a starved run would starve nothing)")
    return rl


def seal(path: Path, seal_path: Path = DEFAULT_SEAL, *, author: str, now: datetime | None = None,
         repo: Path = REPO_ROOT) -> str:
    """Validate the list (non-empty, outside the repo working tree), write its sha256, the list
    author and the time to `seal_path` and return the hash."""
    if not author or not author.strip():
        raise RemovalRefused("the seal needs the list author (kf seal --author NAME)")
    if inside_repo(path, repo):
        raise RemovalRefused(f"{path}: the removal list must live outside the repo working tree "
                             f"(--list, ${LIST_ENV} or ~/.kf/removal.yaml)")
    load_nonempty(path)
    h = digest(path)
    seal_path = Path(seal_path)
    seal_path.parent.mkdir(parents=True, exist_ok=True)
    at = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    seal_path.write_text(json.dumps({"sha256": h, "author": author.strip(), "sealed_at": at}, indent=2) + "\n")
    return h


def read_seal(seal_path: Path = DEFAULT_SEAL) -> dict | None:
    """The seal's {sha256, author, sealed_at}, or None when it is missing or malformed."""
    try:
        data = json.loads(Path(seal_path).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("sha256"), str):
        return None
    return data


def verify_seal(path: Path, seal_path: Path = DEFAULT_SEAL) -> bool:
    """True when `seal_path` holds the sha256 of the list's current bytes."""
    s = read_seal(seal_path)
    return s is not None and Path(path).is_file() and s["sha256"] == digest(path)
