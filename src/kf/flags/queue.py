import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from kf.flags.models import Evidence, Flag, FlagIn, FlagStatus

S = FlagStatus
TRANSITIONS: dict[FlagStatus, set[FlagStatus]] = {
    S.open: {S.triaged, S.duplicate, S.declined, S.held},
    S.triaged: {S.in_review, S.declined, S.held, S.duplicate},
    S.in_review: {S.resolved, S.declined, S.held},
    S.held: {S.triaged, S.declined},
    S.resolved: {S.open},
    S.declined: set(),
    S.duplicate: set(),
}


class FlagRateLimited(Exception):
    pass


class InvalidTransition(Exception):
    pass


_SCHEMA = """
CREATE TABLE IF NOT EXISTS flags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  scenario TEXT NOT NULL,
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  target TEXT,
  knowledge_type TEXT,
  observed TEXT,
  expected TEXT,
  suggested_fix TEXT,
  evidence TEXT NOT NULL,
  workaround_used TEXT,
  severity TEXT NOT NULL,
  confidence TEXT NOT NULL,
  status TEXT NOT NULL,
  cluster_id INTEGER,
  resolution TEXT
)
"""


class FlagQueue:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _flag(row: sqlite3.Row) -> Flag:
        d = dict(row)
        d["evidence"] = [Evidence(**e) for e in json.loads(d["evidence"])]
        d["resolution"] = json.loads(d["resolution"]) if d["resolution"] else None
        return Flag(**d)

    def add(
        self, flag_in: FlagIn, *, agent_id: str, run_id: str, scenario: str, max_per_run: int = 20
    ) -> Flag:
        conn = self._conn()
        try:
            with conn:
                dup = conn.execute(
                    "SELECT * FROM flags WHERE run_id=? AND kind=? AND target IS ? AND summary=?",
                    (run_id, flag_in.kind.value, flag_in.target, flag_in.summary),
                ).fetchone()
                if dup:
                    return self._flag(dup)
                n = conn.execute("SELECT COUNT(*) FROM flags WHERE run_id=?", (run_id,)).fetchone()[0]
                if n >= max_per_run:
                    raise FlagRateLimited(f"run {run_id} reached {max_per_run} flags")
                cur = conn.execute(
                    "INSERT INTO flags (created_at, agent_id, run_id, scenario, kind, summary, target,"
                    " knowledge_type, observed, expected, suggested_fix, evidence, workaround_used,"
                    " severity, confidence, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        datetime.now(UTC).isoformat(), agent_id, run_id, scenario,
                        flag_in.kind.value, flag_in.summary, flag_in.target,
                        flag_in.knowledge_type.value if flag_in.knowledge_type else None,
                        flag_in.observed, flag_in.expected, flag_in.suggested_fix,
                        json.dumps([e.model_dump() for e in flag_in.evidence]),
                        flag_in.workaround_used, flag_in.severity.value, flag_in.confidence.value, S.open.value,
                    ),
                )
                return self._flag(conn.execute("SELECT * FROM flags WHERE id=?", (cur.lastrowid,)).fetchone())
        finally:
            conn.close()

    def list(self, status: FlagStatus | None = None) -> list[Flag]:
        conn = self._conn()
        try:
            if status is None:
                rows = conn.execute("SELECT * FROM flags ORDER BY id").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM flags WHERE status=? ORDER BY id", (FlagStatus(status).value,)
                ).fetchall()
            return [self._flag(r) for r in rows]
        finally:
            conn.close()

    def set_status(
        self, id: int, status: FlagStatus, *, cluster_id: int | None = None, resolution: dict | None = None
    ) -> Flag:
        status = FlagStatus(status)
        conn = self._conn()
        try:
            with conn:
                row = conn.execute("SELECT * FROM flags WHERE id=?", (id,)).fetchone()
                if row is None:
                    raise KeyError(id)
                cur = FlagStatus(row["status"])
                if status not in TRANSITIONS[cur]:
                    raise InvalidTransition(f"{cur.value} -> {status.value}")
                conn.execute(
                    "UPDATE flags SET status=?, cluster_id=COALESCE(?, cluster_id),"
                    " resolution=COALESCE(?, resolution) WHERE id=?",
                    (status.value, cluster_id, json.dumps(resolution) if resolution is not None else None, id),
                )
                return self._flag(conn.execute("SELECT * FROM flags WHERE id=?", (id,)).fetchone())
        finally:
            conn.close()
