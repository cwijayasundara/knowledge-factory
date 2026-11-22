"""The knowledge-starved baseline's removal list (spec 7, 9b) and its seal.

Each item deletes one `match` text from one e2ekg prompt file (`prompts/<name>.md`) for every
LLM arm (e2ekg patch 0003, env E2EKG_STARVE). An item must say where the removed knowledge is
derivable from (catalog, logs, tags), so the curator is never asked for what it cannot know.

The list is sealed before the first measured run: `seal` writes the sha256 of the file's bytes
to the seal file, which is committed alone; `verify_seal` checks the list is unchanged since.
"""
import hashlib
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DEFAULT_LIST = Path("evalx/removal.yaml")
DEFAULT_SEAL = Path("integration/removal.seal")  # state/ is git-ignored; the seal is committed

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


def _digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(path: Path, seal_path: Path = DEFAULT_SEAL) -> str:
    """Validate the list, write the sha256 of its bytes to `seal_path` and return it."""
    RemovalList.load(path)
    h = _digest(path)
    seal_path = Path(seal_path)
    seal_path.parent.mkdir(parents=True, exist_ok=True)
    seal_path.write_text(h + "\n")
    return h


def verify_seal(path: Path, seal_path: Path = DEFAULT_SEAL) -> bool:
    """True when `seal_path` holds the sha256 of the list's current bytes."""
    seal_path = Path(seal_path)
    return seal_path.is_file() and seal_path.read_text().strip() == _digest(path)
