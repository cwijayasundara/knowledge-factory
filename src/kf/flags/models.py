from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FlagKind(StrEnum):
    missing = "missing"
    incorrect = "incorrect"
    stale = "stale"
    ambiguous = "ambiguous"
    contradiction = "contradiction"
    procedure_gap = "procedure_gap"


class KnowledgeType(StrEnum):
    skill = "skill"
    domain = "domain"
    data_access = "data_access"
    unknown = "unknown"


class Level(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class FlagStatus(StrEnum):
    open = "open"
    triaged = "triaged"
    in_review = "in_review"
    resolved = "resolved"
    declined = "declined"
    duplicate = "duplicate"
    held = "held"


class Evidence(BaseModel):
    resource: str
    excerpt: str | None = Field(default=None, max_length=1000)


class FlagIn(BaseModel):
    """What an agent submits. Untrusted data: never placed in a system prompt."""

    kind: FlagKind
    summary: str = Field(max_length=500)
    target: str | None = None
    knowledge_type: KnowledgeType | None = None
    observed: str | None = None
    expected: str | None = None
    suggested_fix: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    workaround_used: str | None = None
    severity: Level = Level.medium
    confidence: Level = Level.medium


class Flag(FlagIn):
    id: int
    created_at: datetime
    agent_id: str
    run_id: str
    scenario: str
    status: FlagStatus = FlagStatus.open
    cluster_id: int | None = None
    resolution: dict | None = None
