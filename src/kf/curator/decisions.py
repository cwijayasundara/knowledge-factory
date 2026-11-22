"""Reconcile-stage decisions (report stage 5), logged on the run record."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from kf.flags.models import Level

Op = Literal["ADD", "UPDATE", "DEPRECATE", "NOOP", "ESCALATE"]
WRITE_OPS: frozenset[str] = frozenset({"ADD", "UPDATE", "DEPRECATE"})


class Decision(BaseModel):
    run_id: str
    target: str
    op: Op
    rationale: str
    sources: list[str] = Field(default_factory=list)
    confidence: Level = Level.medium
    tier: int = Field(ge=0, le=3)
    flags: list[int] = Field(default_factory=list)
