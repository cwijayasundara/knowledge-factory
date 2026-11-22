"""Ontology handoff: the curator files a structured need; a person runs e2ekg's own proposal flow.

The curator never writes Turtle. A need is a small JSON file under state/ontology_needs/; `kf ontology-needs`
lists them with the exact `e2ekg ontology propose` command (mine, propose, gate; approval stays manual).
The example text is untrusted data: it is only stored and printed, never executed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# e2ekg ontology propose mines its own candidates from processed data and writes gated proposals.
PROPOSE_COMMAND = "e2ekg ontology propose --proc data/processed/hero --out ontology/proposals"


class OntologyNeed(BaseModel):
    flag_ids: list[int] = Field(default_factory=list)
    kind: Literal["error_template", "metric_tag", "event_type"]
    example: str


def _next_id(out_dir: Path) -> int:
    return max((int(p.stem) for p in out_dir.glob("*.json") if p.stem.isdigit()), default=0) + 1


def file_ontology_need(need: OntologyNeed, *, out_dir: Path) -> Path:
    """Write the need to <out_dir>/<id>.json (id = next number) and return the path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    nid = _next_id(out_dir)
    path = out_dir / f"{nid:03d}.json"
    path.write_text(json.dumps({"id": nid, **need.model_dump()}, indent=2), encoding="utf-8")
    return path


def list_ontology_needs(out_dir: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(out_dir).glob("*.json"))]


def render_needs(out_dir: Path) -> str:
    needs = list_ontology_needs(out_dir)
    if not needs:
        return "no ontology needs filed"
    lines = [f"{n['id']}\t{n['kind']}\tflags {','.join(map(str, n['flag_ids'])) or '-'}\t{json.dumps(n['example'])}"
             for n in needs]
    lines += ["", "Run (approval stays manual: move an accepted file from ontology/proposals/ to ontology/extensions/):",
              PROPOSE_COMMAND]
    return "\n".join(lines)
