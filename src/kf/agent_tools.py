"""The tools a working agent gets from the factory: `kf_flag` (writes only to the flag queue) and
the read-only `kb_search` / `kb_read` over a frozen bundle snapshot.

The handler, not the model, attaches agent, run id and scenario; the queue rate-limits per run.
A flag the queue refuses comes back as a short notice, never an exception, so the agent goes on."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.tools import BaseTool, tool
from pydantic import ValidationError

from kf.bundle import serve
from kf.flags.models import Evidence, FlagIn, FlagKind, KnowledgeType, Level
from kf.flags.queue import FlagQueue, FlagRateLimited

CONTINUE = "Continue your task with the best workaround you have."


def utcnow() -> datetime:
    return datetime.now(UTC)


def make_kf_tools(*, queue_path: Path, bundle_snapshot: Path, run_id: str, agent_id: str, scenario: str,
                  now: Callable[[], datetime] = utcnow) -> dict[str, BaseTool]:
    queue_path, bundle = Path(queue_path), Path(bundle_snapshot)

    @tool(parse_docstring=True)
    def kf_flag(
        kind: FlagKind,
        summary: str,
        target: str | None = None,
        knowledge_type: KnowledgeType | None = None,
        observed: str | None = None,
        expected: str | None = None,
        suggested_fix: str | None = None,
        evidence: list[Evidence] | None = None,
        workaround_used: str | None = None,
        severity: Level = Level.medium,
        confidence: Level = Level.medium,
    ) -> str:
        """Flag company knowledge that is missing, wrong, stale, ambiguous or contradictory, then keep working.

        Args:
            kind: missing, incorrect, stale, ambiguous, contradiction or procedure_gap.
            summary: One sentence on what knowledge was missing or wrong (at most 500 characters).
            target: The bundle path of the concept or skill concerned, if one exists.
            knowledge_type: skill, domain, data_access or unknown.
            observed: What you found.
            expected: What you expected to find.
            suggested_fix: What the knowledge should say.
            evidence: Resources (and short excerpts) that show the problem.
            workaround_used: How you carried on without the knowledge.
            severity: low, medium or high.
            confidence: low, medium or high.
        """
        try:
            flag_in = FlagIn(kind=kind, summary=summary, target=target, knowledge_type=knowledge_type,
                             observed=observed, expected=expected, suggested_fix=suggested_fix,
                             evidence=evidence or [], workaround_used=workaround_used,
                             severity=severity, confidence=confidence)
        except ValidationError as e:
            return f"Flag not recorded ({e.error_count()} invalid field(s)). {CONTINUE}"
        try:
            flag = FlagQueue(queue_path).add(flag_in, agent_id=agent_id, run_id=run_id, scenario=scenario)
        except FlagRateLimited:
            return f"Flag not recorded: this run reached its flag limit. {CONTINUE}"
        return f"Flag {flag.id} recorded. {CONTINUE}"

    @tool(parse_docstring=True)
    def kb_search(query: str) -> str:
        """Search the company knowledge bundle (current, reviewed knowledge only).

        Args:
            query: Words to look for, such as a service alias, a field name or a procedure.
        """
        hits = serve.kb_search(bundle, query, now=now())
        if not hits:
            return "No current knowledge matches. Consider kf_flag with kind 'missing'."
        return "\n".join(f"{h.path} | {h.title} | {h.snippet}" for h in hits)

    @tool(parse_docstring=True)
    def kb_read(path: str) -> str:
        """Read one concept or skill from the company knowledge bundle.

        Args:
            path: The bundle-relative path kb_search returned, such as domain/aliases.md.
        """
        try:
            return serve.kb_read(bundle, path, now=now())
        except ValueError as e:
            return str(e)

    return {"kf_flag": kf_flag, "kb_search": kb_search, "kb_read": kb_read}
