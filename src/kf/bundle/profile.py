"""kf-profile.yaml: required keys, enums and stale_after defaults per x-kf-kind."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import yaml
from pydantic import BaseModel


class KindRule(BaseModel):
    required: list[str]
    stale_after_days: int


class Profile(BaseModel):
    okf_version: str
    enums: dict[str, list[str | int]]
    kinds: dict[str, KindRule]

    @classmethod
    def load(cls, path: Path) -> Profile:
        return cls.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    def stale_after(self, kind: str, since: datetime) -> datetime:
        return since + timedelta(days=self.kinds[kind].stale_after_days)
