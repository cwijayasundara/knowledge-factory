"""G2 verdict (spec 9b, 9c): graph_kb after curation vs the starved graph arm, on held-out seeds,
with a seed-only control (graph_kb starved on the pristine seed bundle) so the curator is the only
change that can earn the gain.

A G2 measurement is three run sets of kf_run.json records (one per seed): starved graph, graph_kb
on the curated bundle, graph_kb on the seed bundle. It is valid only when the sets are comparable
(same data roots, scenarios, runs, e2ekg commit, per-scenario row counts; one bundle commit per
set), sealed (each run read a copy of the committed seal's list, sealed before the first run),
held-out, not test runs, and reviewed by a person who is not the list author, with no scripted
approval in the approvals log or in the measured bundle.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from kf.bundle.okf import SCRIPTED_STAMP, parse_concept
from kf.review.gate import Scores
from kf.review.review import Approval

MIN_GAIN_RUNS = 2
BUNDLE_DIR = "bundle"


@dataclass(frozen=True)
class G2Result:
    valid: bool
    passed: bool
    reasons: list[str] = field(default_factory=list)


def read_approval_records(path: Path, *, include_auto: bool = False) -> list[dict]:
    """Approval lines of state/approvals.jsonl, minus voided ones (and minus Tier 0 "auto" lines
    unless include_auto).

    A `merge_failed` event line voids the approval lines of that branch logged immediately before
    it (one merge attempt logs its approver and, for tier 2, its second approver back to back)."""
    path = Path(path)
    if not path.is_file():
        return []
    lines = []
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        if isinstance(rec, dict):
            lines.append(rec)
    kept: list[dict] = []
    for rec in lines:
        if rec.get("event") == "merge_failed":
            while kept and kept[-1].get("branch") == rec.get("branch") and "event" not in kept[-1]:
                kept.pop()
            continue
        kept.append(rec)
    return [r for r in kept if "event" not in r and (include_auto or r.get("kind") != "auto")]  # auto: not approvals


def to_approvals(records: list[dict]) -> list[Approval]:
    return [Approval(r["by"], r["kind"], datetime.fromisoformat(r["at"]).astimezone(UTC), bool(r.get("test_run")))
            for r in records]


def read_approvals(path: Path) -> list[Approval]:
    return to_approvals(read_approval_records(path))


def _ident(who: str | None) -> str:
    return str(who or "").strip().removeprefix("human:").strip().casefold()


def coverage_problems(starved_recs: list[dict], kb_recs: list[dict], seed_recs: list[dict] | None = None,
                      rows: dict[str, dict] | None = None) -> list[str]:
    """Why the run sets' kf_run.json records are not comparable: data roots, scenarios, runs, exit
    codes, e2ekg commit, one bundle commit per kb set, per-(data root, scenario) scored rows."""
    sets = {"starved": starved_recs, "kb": kb_recs}
    if seed_recs is not None:
        sets["seed-kb"] = seed_recs

    def keys(recs: list[dict]) -> list[tuple]:
        return sorted((str(r.get("data_root", "")), tuple(r.get("scenarios", [])), r.get("runs")) for r in recs)

    ks = {n: keys(r) for n, r in sets.items()}
    ref = ks["starved"]
    out = []
    for i, what in ((0, "data roots (seeds)"), (1, "scenarios"), (2, "runs-per-scenario")):
        if any([k[i] for k in v] != [k[i] for k in ref] for v in ks.values()):
            out.append(f"the runs used different {what}")
    every = [r for recs in sets.values() for r in recs]
    if any(r.get("returncode") != 0 for r in every):
        out.append("an e2ekg eval invocation exited nonzero")
    clocks = {n: sorted({str(r.get("now")) for r in recs}) for n, recs in sets.items()}
    if None in {r.get("now") for r in every} or len({c for v in clocks.values() for c in v}) != 1:
        out.append(f"the runs used different clocks (now): {clocks}")
    shas = {r.get("e2ekg_sha") for r in every}
    if None in shas or len(shas) != 1:
        out.append(f"the runs used different or unrecorded e2ekg commits: {sorted(map(str, shas))}")
    for name in ("kb", "seed-kb"):
        if name in sets and len({r.get("commit") for r in sets[name]}) != 1:
            out.append(f"--{name} runs used more than one bundle commit")
    if rows:
        ref_rows = rows.get("starved")
        for name, r in rows.items():
            if r != ref_rows:
                out.append(f"unequal scored runs per seed and scenario: starved {sorted(ref_rows.items())}, "
                           f"{name} {sorted(r.items())}")
    return out


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def seal_problems(recs: list[dict], seal_file: Path, repo: Path | None = None) -> tuple[list[str], dict | None]:
    """The seal must be committed and clean in git, sealed before the first run started, and equal
    to the hash of the list copy every run read (and recorded). Each run's copy lives at its recorded
    private path outside the repo (${KF_HOME:-~/.kf}/runs/...) and must still hash to the recorded
    value and to the seal."""
    from kf.evalx import removal

    seal_file = Path(seal_file).resolve()
    info = removal.read_seal(seal_file)
    if info is None:
        return [f"removal list seal missing or malformed: {seal_file}"], None
    out = []
    top = _git(seal_file.parent, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        out.append(f"the seal {seal_file} is not in a git repo")
    else:
        root = Path(top.stdout.strip())
        rel = seal_file.relative_to(root.resolve()).as_posix()
        tracked = _git(root, "ls-files", "--error-unmatch", "--", rel).returncode == 0
        dirty = _git(root, "status", "--porcelain", "--", rel).stdout.strip()
        if not tracked or dirty:
            out.append(f"the seal {rel} is not committed and clean")
        at = _git(root, "log", "-1", "--format=%cI", "--", rel).stdout.strip()
        starts = [datetime.fromisoformat(r["started_at"]) for r in recs if r.get("started_at")]
        if len(starts) != len(recs):
            out.append("a run has no recorded start time")
        elif at and datetime.fromisoformat(at) >= min(starts):
            out.append(f"the seal was committed at {at}, not before the first run ({min(starts).isoformat()})")
    for r in recs:
        if r.get("seal_hash") != info["sha256"] or r.get("removal_sha256") != info["sha256"]:
            out.append(f"{r.get('_dir', 'a run')} did not run on the sealed list")
            break
    repos = {Path(repo).resolve()} if repo else set()
    if top.returncode == 0:
        repos.add(Path(top.stdout.strip()).resolve())
    for r in recs:
        where = r.get("_dir", "a run")
        copy = r.get("removal_copy")
        if not copy:
            out.append(f"{where}: no recorded private copy of the sealed list")
            break
        copy = Path(copy)
        if any(removal.inside_repo(copy, rp) for rp in repos):
            out.append(f"{where}: the list copy {copy} is inside the repo")
            break
        try:
            ok = (copy.is_file() and removal.digest(copy) == r.get("removal_sha256") == info["sha256"]
                  and removal.load_nonempty(copy))
        except (ValueError, OSError):
            ok = False
        if not ok:
            out.append(f"{where}: the private list copy {copy} is missing, empty or no longer matches the "
                       "recorded hash and the seal")
            break
    return out, info


def snapshot_problems(recs: list[dict], author: str | None) -> list[str]:
    """The measured bundle snapshots must hold no scripted stamp and no stamp by the list author."""
    out = []
    for snap in sorted({r.get("snapshot") or "" for r in recs}):
        if not snap or not Path(snap).is_dir():
            out.append(f"bundle snapshot missing: {snap or '(none recorded)'}")
            continue
        for f in sorted(Path(snap).rglob("*.md")):
            try:
                front = parse_concept(str(f), f.read_text(encoding="utf-8")).front
            except (ValueError, OSError, UnicodeDecodeError):
                continue
            for v in front.get("verified") or []:
                by = str(v.get("by", "")) if isinstance(v, dict) else ""
                if by == SCRIPTED_STAMP:
                    out.append(f"{f.relative_to(snap)} carries a scripted approval stamp")
                elif author and by.startswith("human:") and _ident(by) == _ident(author):
                    out.append(f"{f.relative_to(snap)} was approved by the removal list author")
    return out


_MERGE_MSG = re.compile(r"^merge (kf/[A-Za-z0-9._-]+) \(tier ([0-3])(, auto)?\)$")
_STAMP_MSG = "review: stamp verified by human:"
_STAMP_KEYS = {"verified", "x-kf-review"}


def _is_concept(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.endswith(".md") and name not in ("index.md", "log.md")


def _front(repo: Path, ref: str, path: str) -> tuple[dict, str] | None:
    p = _git(repo, "show", f"{ref}:{path}")
    if p.returncode != 0:
        return None
    try:
        c = parse_concept(path, p.stdout)
    except ValueError:
        return {}, p.stdout
    return c.front, c.body


def _blob(repo: Path, ref: str, path: str) -> str | None:
    """The blob id of path at ref, None when the path is absent there."""
    p = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}:{path}")
    return p.stdout.strip() if p.returncode == 0 else None


def _bundle_changes(repo: Path, a: str, b: str) -> list[tuple[str, str]]:
    """(status letter, path) of every bundle/ change from a to b."""
    out = _git(repo, "diff", "--name-status", "--no-renames", "-z", a, b, "--", BUNDLE_DIR + "/").stdout
    f = out.split("\0")
    return [(f[i][0], f[i + 1]) for i in range(0, len(f) - 1, 2) if f[i]]


def _merge_problems(repo: Path, m: str, p1: str, p2: str, changes: list[tuple[str, str]],
                    approvals: list[dict], runs_dir: Path) -> list[str]:
    """A merge commit on main that changes bundle/: it must be kf review's merge of kf/<run_id> (message,
    run record, approval or Tier 0 auto line), introduce exactly the merged tip's content, and every
    concept it adds or modifies must be curator-written before the human stamp."""
    short = m[:12]
    subject = _git(repo, "log", "-1", "--format=%s", m).stdout.strip()
    match = _MERGE_MSG.match(subject)
    if not match:
        return [f"merge {short} ({subject!r}) changes bundle/ but is not a kf review merge of a kf/<run_id> branch"]
    branch, auto = match.group(1), bool(match.group(3))
    out = []
    if not (runs_dir / f"{branch.removeprefix('kf/')}.json").is_file():
        out.append(f"merge {short} of {branch} has no run record {runs_dir / (branch.removeprefix('kf/') + '.json')}")
    lines = [a for a in approvals if a.get("branch") == branch]
    if auto:
        autos = [a for a in lines if a.get("kind") == "auto"]
        if not autos:
            out.append(f"merge {short} of {branch} has no Tier 0 auto line in approvals.jsonl")
        elif not any(a.get("tip") == p2 for a in autos):
            out.append(f"merge {short} of {branch}: no Tier 0 auto line records the merged tip {p2[:12]} "
                       "(an auto line without a tip predates tip binding: re-merge with the current kf)")
    elif not any(a.get("kind") in ("person", "scripted") and a.get("role") == "approver" for a in lines):
        out.append(f"merge {short} of {branch} has no approval in approvals.jsonl")
    # The pre-stamp tip: kf review stamps on one extra branch commit (verified, x-kf-review only).
    pre = p2
    p2_subject = _git(repo, "log", "-1", "--format=%s%x00%an%x00%P", p2).stdout.strip().split("\0")
    stamped = (p2_subject[0].startswith(_STAMP_MSG) and p2_subject[1] == "kf-review"
               and len(p2_subject[2].split()) == 1)
    if stamped:
        if auto:
            out.append(f"merge {short}: a Tier 0 auto-merge carries a stamp commit {p2[:12]}")
        pre = p2_subject[2].strip()
        for code, path in _bundle_changes(repo, pre, p2) + [
                ("?", x) for x in _git(repo, "diff", "--name-only", pre, p2, "--", ":!" + BUNDLE_DIR + "/").stdout.split()]:
            before, after = _front(repo, pre, path), _front(repo, p2, path)
            if code != "M" or before is None or after is None or before[1] != after[1] or {
                    k for k in before[0].keys() | after[0].keys() if before[0].get(k) != after[0].get(k)} - _STAMP_KEYS:
                out.append(f"stamp commit {p2[:12]} changes more than the review stamp in {path}")
    if not auto:
        # Bind the approval to the commit: the gated head (kf eval gate's record) is the pre-stamp tip.
        try:
            rec = json.loads((runs_dir / f"{branch.removeprefix('kf/')}.json").read_text())
        except (OSError, ValueError):
            rec = {}
        head = (rec.get("gate") or {}).get("head_commit") if isinstance(rec, dict) else None
        if head != pre:
            out.append(f"merge {short} of {branch}: the merged tip {pre[:12]} is not the gated head "
                       f"{str(head)[:12]} in the run record's gate.head_commit")
        if not stamped and any(code != "D" and _is_concept(path) for code, path in changes):
            out.append(f"merge {short} of {branch} adds or modifies concepts but has no kf review stamp commit")
    for code, path in changes:
        if _blob(repo, m, path) != _blob(repo, p2, path):
            out.append(f"merge {short} changes {path} beyond the merged branch tip {p2[:12]}")
        if code == "D" or not _is_concept(path):
            continue
        got = _front(repo, pre, path)
        gen = (got[0] if got else {}).get("generated")
        by = str(gen.get("by", "")) if isinstance(gen, dict) else ""
        if not by.startswith("kf-curator/"):
            out.append(f"merge {short} of {branch}: {path} was not written by kf-curator before the stamp "
                       f"(generated.by {by or 'missing'!r})")
    return out


def provenance_problems(repo: Path, seed_commit: str, kb_commit: str, state_dir: Path) -> list[str]:
    """Every bundle/ change between the seed commit S and the kb commit K must come from kf review
    merges of kf/<run_id> branches on K's first-parent history (review.approve_and_merge or
    auto_merge_tier0): no non-merge commit on that path may touch bundle/."""
    repo, state_dir = Path(repo), Path(state_dir)
    fp = _git(repo, "rev-list", "--first-parent", "--parents", kb_commit).stdout.split("\n")
    chain = [line.split() for line in fp if line.strip()]
    shas = [c[0] for c in chain]
    if seed_commit not in shas:
        return [f"the seed commit {seed_commit[:12]} is not on the kb commit's first-parent history"]
    approvals = read_approval_records(state_dir / "approvals.jsonl", include_auto=True)
    out = []
    for sha, *parents in chain[:shas.index(seed_commit)]:
        if len(parents) == 1:
            changes = _bundle_changes(repo, parents[0], sha)
            if changes:
                out.append(f"commit {sha[:12]} is not a curator merge and changes bundle/: "
                           + ", ".join(p for _, p in changes))
        elif len(parents) == 2:
            changes = _bundle_changes(repo, parents[0], sha)
            if changes:
                out += _merge_problems(repo, sha, parents[0], parents[1], changes, approvals, state_dir / "runs")
        else:
            if _bundle_changes(repo, parents[0], sha):
                out.append(f"octopus merge {sha[:12]} changes bundle/")
    return out


def pristine_problems(repo: Path, seed_commit: str | None, kb_commit: str | None, *,
                      state_dir: Path | None = None) -> list[str]:
    """The seed-only control must run on a seed bundle commit (no curator-written concept) that is
    an ancestor of the curated commit, and differ from it; and (R1) the whole bundle difference must
    come from reviewed curator merges (provenance_problems). state_dir holds approvals.jsonl and
    runs/<run_id>.json (default <repo>/state)."""
    if not seed_commit or not kb_commit:
        return ["the seed-only control or the kb run has no bundle commit"]
    if seed_commit == kb_commit:
        return ["the seed-only control ran on the curated bundle commit (nothing was curated)"]
    if _git(repo, "merge-base", "--is-ancestor", seed_commit, kb_commit).returncode != 0:
        return [f"the seed commit {seed_commit[:12]} is not an ancestor of the kb commit {kb_commit[:12]}"]
    ls = _git(repo, "ls-tree", "-r", "--name-only", seed_commit, "--", "bundle/")
    for path in ls.stdout.splitlines():
        if not path.endswith(".md"):
            continue
        text = _git(repo, "show", f"{seed_commit}:{path}").stdout
        try:
            front = parse_concept(path, text).front
        except ValueError:
            continue
        gen = front.get("generated")
        if isinstance(gen, dict) and str(gen.get("by", "")).startswith("kf-curator"):
            return [f"the seed-only control's bundle is not pristine: {path} was written by the curator"]
    return provenance_problems(Path(repo), seed_commit, kb_commit, Path(state_dir or Path(repo) / "state"))


def g2_verdict(starved: Scores, kb: Scores, *, seed: Scores, approvals: list[Approval], seal_ok: bool,
               heldout: bool, coverage: list[str] | None = None, list_author: str | None = None) -> G2Result:
    invalid = list(coverage or [])
    if not (starved.runs == kb.runs == seed.runs):
        invalid.append(f"unequal scored runs: starved {starved.runs}, kb {kb.runs}, seed-kb {seed.runs}")
    if not seal_ok:
        invalid.append("removal list seal missing or broken")
    if any(a.kind == "scripted" for a in approvals):
        invalid.append("a scripted approval is in the record")
    if any(a.test_run for a in approvals):
        invalid.append("a test-run approval is in the record")
    if list_author and any(a.kind == "person" and _ident(a.by) == _ident(list_author) for a in approvals):
        invalid.append("the removal list author approved a curator change (the reviewer must be blind)")
    if not heldout:
        invalid.append("not measured on held-out seeds")
    if invalid:
        return G2Result(False, False, invalid)
    reasons = []
    if kb.top1 - starved.top1 < MIN_GAIN_RUNS:
        reasons.append(f"top1 gain {kb.top1 - starved.top1} (starved {starved.top1}, kb {kb.top1}); needs >= {MIN_GAIN_RUNS}")
    if kb.top1 <= seed.top1:
        reasons.append(f"top1 does not beat the seed-only control (seed-kb {seed.top1}, kb {kb.top1})")
    for name, ref in (("starved", starved), ("seed-kb", seed)):
        if kb.trap > ref.trap:
            reasons.append(f"trap rose {ref.trap} -> {kb.trap} vs {name}")
        if kb.control_fp > ref.control_fp:
            reasons.append(f"control false positives rose {ref.control_fp} -> {kb.control_fp} vs {name}")
    return G2Result(True, not reasons, reasons)
