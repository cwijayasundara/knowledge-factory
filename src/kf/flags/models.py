from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FlagKind(StrEnum):
    stale = "stale"
    missing = "missing"
    wrong = "wrong"
    ambiguous = "ambiguous"
    contradiction = "contradiction"
    other = "other"


class FlagStatus(StrEnum):
    open = "open"
    triaged = "triaged"
    in_review = "in_review"
    resolved = "resolved"
    declined = "declined"
    duplicate = "duplicate"
    held = "held"


class Evidence(BaseModel):
    ref: str
    excerpt: str | None = None


class FlagIn(BaseModel):
    """What an agent submits. Untrusted data: never placed in a system prompt."""

    kind: FlagKind
    summary: str = Field(max_length=500)
    target: str | None = None
    knowledge_type: str | None = None
    observed: str | None = None
    expected: str | None = None
    suggested_fix: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    workaround_used: str | None = None
    severity: str = "medium"
    confidence: str = "medium"


class Flag(FlagIn):
    id: int
    created_at: datetime
    agent_id: str
    run_id: str
    scenario: str
    status: FlagStatus = FlagStatus.open
    cluster_id: int | None = None
    resolution: dict | None = None
