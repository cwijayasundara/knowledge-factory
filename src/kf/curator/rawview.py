"""`kf raw-view`: the curator's as-of raw sources (spec 5.4).

The curator reads raw sources only as they were observable at each scenario's cutoff, never the
generator's full raw tree (which holds post-cutoff data and the answer key). This builds, per
scenario, e2ekg's own as-of raw view (e2ekg.evals.rawview.ensure_raw_view, run in e2ekg's
environment) into <out>/<scenario>/ and writes a marker file; `kf curate --raw-dir` accepts only a
directory carrying that marker. Held-out data roots are refused (spec 9b).
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from kf.curator.guard import mentions_answers
from kf.evalx.split import is_heldout_path

MARKER = ".kf-raw-view.json"
_SCRIPT = """import sys
from datetime import datetime
from pathlib import Path
from e2ekg.evals.rawview import ensure_raw_view
raw, proc, as_of, dest = sys.argv[1:5]
ensure_raw_view(Path(raw), Path(proc), datetime.fromisoformat(as_of), Path(dest))
"""


class RawViewError(Exception):
    pass


def is_raw_view(path: Path) -> bool:
    try:
        return isinstance(json.loads((Path(path) / MARKER).read_text()), dict)
    except (OSError, ValueError):
        return False


def mark(dest: Path, meta: dict) -> Path:
    """Write the marker that tells kf curate `dest` is an as-of raw view."""
    p = Path(dest) / MARKER
    p.write_text(json.dumps({**meta, "built_at": datetime.now(UTC).isoformat()}, indent=2) + "\n")
    return p


def scenario_as_of(data_root: Path, scenario: str) -> datetime:
    harvest = Path(data_root) / "graph" / scenario / "as_of" / "harvest.json"
    try:
        return datetime.fromisoformat(json.loads(harvest.read_text())["as_of"])
    except (OSError, ValueError, KeyError) as e:
        raise RawViewError(f"{harvest}: no as-of cutoff ({e}); run e2ekg harvest --as-of first") from e


def e2ekg_builder(e2ekg_dir: Path) -> Callable[[Path, Path, datetime, Path], None]:
    def build(raw: Path, proc: Path, as_of: datetime, dest: Path) -> None:
        if not (Path(e2ekg_dir) / "pyproject.toml").is_file():
            raise RawViewError(f"{e2ekg_dir} is not an e2ekg checkout: run bash integration/apply.sh first")
        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        p = subprocess.run(["uv", "run", "python", "-c", _SCRIPT, str(raw), str(proc), as_of.isoformat(), str(dest)],
                           cwd=Path(e2ekg_dir), env=env, capture_output=True, text=True)
        if p.returncode != 0:
            raise RawViewError(f"e2ekg raw view for {raw} failed: {p.stderr.strip()[-2000:]}")
    return build


def build_view(data_root: Path, out: Path, *, scenarios: list[str] | None = None,
               builder: Callable[[Path, Path, datetime, Path], None]) -> Path:
    data_root, out = Path(data_root).resolve(), Path(out).resolve()
    if is_heldout_path(data_root) or is_heldout_path(out):
        raise RawViewError(f"{data_root}: held-out data never reaches the curator (spec 9b)")
    raw = data_root / "raw"
    if not raw.is_dir():
        raise RawViewError(f"{raw}: no raw tree (run e2ekg generate first)")
    names = scenarios or sorted(p.name for p in raw.iterdir() if p.is_dir() and not mentions_answers(p.name))
    if any(mentions_answers(n) for n in names):
        raise RawViewError("the answer key is not a scenario")
    out.mkdir(parents=True, exist_ok=True)
    cutoffs = {}
    for s in names:
        as_of = scenario_as_of(data_root, s)
        builder(raw / s, data_root / "processed" / s, as_of, out / s)
        cutoffs[s] = as_of.isoformat()
    mark(out, {"data_root": str(data_root), "scenarios": names, "as_of": cutoffs})
    return out
