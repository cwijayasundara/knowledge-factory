import argparse
import sys
from pathlib import Path

from kf.bundle.ci import run_ci
from kf.evalx import removal
from kf.flags.models import FlagStatus
from kf.flags.queue import FlagQueue

DEFAULT_DB = "state/flags.db"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kf")
    sub = p.add_subparsers(dest="cmd", required=True)
    flags = sub.add_parser("flags").add_subparsers(dest="sub", required=True)
    ls = flags.add_parser("list")
    ls.add_argument("--status", choices=[s.value for s in FlagStatus])
    ls.add_argument("--db", default=DEFAULT_DB)
    ci = sub.add_parser("ci", help="run bundle CI")
    ci.add_argument("bundle")
    ci.add_argument("--base", help="base bundle dir for the no_curator_verified check")
    rv = sub.add_parser("review", help="review and merge curator branches").add_subparsers(
        dest="sub", required=True
    )
    for name in ("list", "show", "approve", "reject", "auto-merge"):
        sp = rv.add_parser(name)
        sp.add_argument("--repo", default=".")
        if name == "show" or name == "reject":
            sp.add_argument("branch")
        if name == "auto-merge":
            sp.add_argument("--branch", required=True)
        if name == "approve":
            sp.add_argument("--branch", required=True)
            sp.add_argument("--by", required=True)
            sp.add_argument("--kind", choices=["person", "scripted"], default="person")
            sp.add_argument("--test-run", action="store_true")
            sp.add_argument("--second-by", help="second distinct approver (person)")
            sp.add_argument("--db", default=DEFAULT_DB)
        if name == "reject":
            sp.add_argument("--by", required=True)
            sp.add_argument("--reason", default="")
    sl = sub.add_parser("seal", help="seal the starved baseline's removal list")
    sl.add_argument("--verify", action="store_true", help="exit 1 if the list differs from the seal")
    sl.add_argument("--list", default=str(removal.default_list()),
                    help=f"removal list outside the repo (default ${removal.LIST_ENV} or ~/.kf/removal.yaml)")
    sl.add_argument("--seal-file", default=str(removal.DEFAULT_SEAL))
    sl.add_argument("--author", help="who wrote the list (required to seal; must not approve curator changes)")
    sl.add_argument("--bundle", default=str(removal.REPO_ROOT / "bundle"),
                    help="seed bundle that must not hold any removed text")
    ev = sub.add_parser("eval", help="run e2ekg evals, G2 verdict, metrics").add_subparsers(dest="sub", required=True)
    er = ev.add_parser("run", help="run e2ekg eval over the curation or held-out seeds")
    er.add_argument("--arms", default="graph", help="comma list of e2ekg arms, e.g. graph or graph_kb")
    er.add_argument("--scenarios", default="all", help="comma list of e2ekg scenario names, or all")
    er.add_argument("--runs", type=int, default=3, help="runs per LLM arm and scenario")
    er.add_argument("--starve", action="store_true", help="knowledge-starved baseline (E2EKG_STARVE)")
    er.add_argument("--heldout", action="store_true", help="held-out seeds (default: curation seeds)")
    er.add_argument("--test-run", action="store_true", help="mark as a test run (never a headline)")
    er.add_argument("--bundle-commit", help="bundle commit to snapshot (default HEAD)")
    er.add_argument("--now", help="KF_NOW for the kb tools, an ISO timestamp with offset; required for headline "
                    "(--heldout) runs: pick one value and reuse it for baseline, treatment and control "
                    "(default for other runs: the bundle commit's author date)")
    er.add_argument("--state-dir", default=str(removal.REPO_ROOT / "state"))
    er.add_argument("--data-base", default=str(removal.REPO_ROOT), help="directory holding data_curation/ and data_heldout/")
    er.add_argument("--bundle", default=str(removal.REPO_ROOT / "bundle"))
    er.add_argument("--list", default=str(removal.default_list()), help="removal list (for the seed-overlap check)")
    eg = ev.add_parser("g2", help="G2 verdict: starved graph vs curated graph_kb vs seed-only graph_kb (held-out)")
    eg.add_argument("--starved", required=True, help="run directory of the starved graph run")
    eg.add_argument("--kb", required=True, help="run directory of the graph_kb run on the curated bundle")
    eg.add_argument("--seed-kb", required=True,
                    help="run directory of the seed-only control: graph_kb, starved, on the pristine seed commit")
    eg.add_argument("--state-dir", default=str(removal.REPO_ROOT / "state"))
    eg.add_argument("--repo", default=str(removal.REPO_ROOT), help="the bundle's git repo")
    eg.add_argument("--report", default=None, help="default reports/g2-<date>.md")
    eg.add_argument("--list", default=str(removal.default_list()))
    eg.add_argument("--seal-file", default=str(removal.DEFAULT_SEAL))
    gt = ev.add_parser("gate", help="eval gate for a curator branch: graph_kb (starved) on the curation seeds, "
                                     "main vs the branch, scores into state/runs/<run_id>.json")
    gt.add_argument("--branch", required=True, help="curator branch kf/<run_id>")
    gt.add_argument("--repo", default=str(removal.REPO_ROOT))
    gt.add_argument("--scenarios", default="all", help="comma list of e2ekg scenario names, or all")
    gt.add_argument("--runs", type=int, default=3, help="runs per scenario and side")
    gt.add_argument("--state-dir", default=str(removal.REPO_ROOT / "state"))
    gt.add_argument("--data-base", default=str(removal.REPO_ROOT), help="directory holding data_curation/")
    gt.add_argument("--list", default=str(removal.default_list()), help="removal list (both sides are starved)")
    gt.add_argument("--now", help="KF_NOW for both sides, an ISO timestamp with offset (required)")
    em = ev.add_parser("metrics", help="curator and corpus metrics as JSON")
    em.add_argument("--state-dir", default="state")
    em.add_argument("--db", default=None, help="flag queue (default <state-dir>/flags.db)")
    em.add_argument("--bundle", default="bundle")
    cu = sub.add_parser("curate", help="run the curator: flags to a proposed kf/<run_id> branch")
    cu.add_argument("--dry-run", action="store_true",
                    help="build the branch in a temp worktree, print decisions, discard it")
    cu.add_argument("--model", default=None, help="curator chat model (default: e2ekg's Fireworks GLM)")
    cu.add_argument("--judge-model", default=None, help="LLM-judge model; must differ from --model")
    cu.add_argument("--raw-dir", required=True,
                    help="the as-of raw view built by kf raw-view (never held-out data); must not contain hard "
                         "links to answer-key files (path checks cannot detect hard links)")
    cu.add_argument("--run-id", default=None, help="default: curate-<UTC timestamp>")
    cu.add_argument("--trails-dir", default=None,
                    help="a curation-seed e2ekg eval run dir whose saved trails the curator may list (held-out refused)")
    cu.add_argument("--repo", default=".")
    cu.add_argument("--db", default=DEFAULT_DB)
    rw = sub.add_parser("raw-view", help="build the curator's as-of raw view of a curation data root")
    rw.add_argument("--data-root", required=True, help="a curation data root, e.g. data_curation/seed-11")
    rw.add_argument("--out", required=True, help="the view directory to pass to kf curate --raw-dir")
    rw.add_argument("--scenarios", default="all", help="comma list of scenario names, or all")
    on = sub.add_parser("ontology-needs", help="list ontology needs the curator filed, with the e2ekg command")
    on.add_argument("--state-dir", default="state")
    args = p.parse_args(argv)
    if args.cmd == "curate":
        return _curate(args)
    if args.cmd == "eval":
        from kf.evalx import cli as evalx_cli

        return evalx_cli.run(args)
    if args.cmd == "raw-view":
        from kf.curator import rawview
        from kf.evalx.runner import E2EKG_DIR

        try:
            out = rawview.build_view(Path(args.data_root), Path(args.out),
                                     scenarios=None if args.scenarios == "all" else args.scenarios.split(","),
                                     builder=rawview.e2ekg_builder(E2EKG_DIR))
        except rawview.RawViewError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(out)
        return 0
    if args.cmd == "ontology-needs":
        from kf.curator.ontology_handoff import render_needs

        print(render_needs(Path(args.state_dir) / "ontology_needs"))
        return 0
    if args.cmd == "seal":
        return _seal(args)
    if args.cmd == "review":
        return _review(args)
    if args.cmd == "ci":
        report = run_ci(Path(args.bundle), base=Path(args.base) if args.base else None)
        for i in report.issues:
            print(f"{i.check}\t{i.path}\t{i.message}")
        return 0 if report.ok else 1
    if args.cmd == "flags" and args.sub == "list":
        status = FlagStatus(args.status) if args.status else None
        for f in FlagQueue(args.db).list(status):
            print(f"{f.id}\t{f.status.value}\t{f.kind.value}\t{f.target or '-'}\t{f.summary}")
    return 0


def _seal(args) -> int:
    if args.verify:
        if removal.verify_seal(Path(args.list), Path(args.seal_file)):
            print("seal ok")
            return 0
        print(f"seal mismatch: {args.list} vs {args.seal_file}", file=sys.stderr)
        return 1
    try:
        if not args.author:
            raise removal.RemovalRefused("the seal needs the list author: kf seal --author NAME")
        overlaps = removal.seed_overlaps(Path(args.bundle), removal.load_nonempty(Path(args.list)))
        if overlaps:
            raise removal.RemovalRefused(f"the bundle holds removal items: {', '.join(overlaps)}")
        print(removal.seal(Path(args.list), Path(args.seal_file), author=args.author))
    except (removal.RemovalRefused, OSError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0


def _curate(args) -> int:
    from datetime import UTC, datetime

    from kf.curator import agent

    from kf.evalx.split import is_heldout_path

    db = Path(args.db).expanduser().resolve()
    # A held-out run's own flag sink is <state>/evals/heldout-<stamp>/seed-N/state/flags.db (its
    # kf_run.json is written only after e2ekg exits, so the run dir name is checked too).
    if is_heldout_path(db) or any(part.startswith("heldout-") for part in db.parts):
        print(f"refused: {args.db} is a held-out flag queue (held-out data never reaches the curator)",
              file=sys.stderr)
        return 2
    run_id = args.run_id or datetime.now(UTC).strftime("curate-%Y%m%dT%H%M%SZ")
    run = agent.run_curation(
        repo=Path(args.repo), queue=FlagQueue(args.db), raw_dir=Path(args.raw_dir),
        model=args.model or agent.DEFAULT_MODEL, run_id=run_id, judge_model=args.judge_model, dry_run=args.dry_run,
        trails_dir=Path(args.trails_dir) if args.trails_dir else None,
    )
    for d in run.decisions:
        print(f"{d.op}\t{d.target}\ttier {d.tier}\t{','.join(d.sources) or '-'}\t{d.rationale}")
    print(f"run {run.run_id} {run.status} branch {run.branch or '-'} flags {run.flags_out}")
    return 0 if run.status == "done" else 1


def _review_show(repo: Path, branch: str) -> int:
    """What a blind reviewer needs: the changed files with the raw sources each concept cites, and the
    run record's decisions (op, target, tier, sources, flags, rationale). It reads only the branch and
    the run record, never the removal list."""
    from kf.review import review as rv

    print(f"{branch}\ttier {int(rv.tier_of(repo, branch))}")
    for f in rv.changed_files(repo, branch):
        print(f"{f.change}\t{f.path}")
        for s in (f.after or {}).get("sources") or []:
            if isinstance(s, dict):
                print(f"\tcites\t{s.get('id', '-')}\t{s.get('resource', '-')}")
    record = rv.read_run_record(repo, branch)
    if not record:
        print("no run record")
        return 0
    print(f"run {record.get('run_id', '-')}\tstatus {record.get('status', '-')}\tjudge_ok {record.get('judge_ok')}")
    for d in record.get("decisions") or []:
        if not isinstance(d, dict):
            continue
        print(f"decision\t{d.get('op')}\t{d.get('target')}\ttier {d.get('tier', '-')}\t"
              f"confidence {d.get('confidence', '-')}\tflags {d.get('flags') or '-'}")
        print(f"\tsources\t{', '.join(map(str, d.get('sources') or [])) or '-'}")
        print(f"\trationale\t{d.get('rationale', '')}")
    return 0


def _review(args) -> int:
    from datetime import UTC, datetime

    from kf.review import review as rv

    repo = Path(args.repo)
    if args.sub == "list":
        for b in rv._git(repo, "branch", "--list", "kf/*", "--format=%(refname:short)").splitlines():
            print(f"{b}\ttier {int(rv.tier_of(repo, b))}")
        return 0
    if args.sub == "show":
        return _review_show(repo, args.branch)
    if args.sub == "reject":
        rv.record_rejection(repo, args.branch, args.by, args.reason, datetime.now(UTC))
        return 0
    if args.sub == "auto-merge":
        try:
            res = rv.auto_merge_tier0(repo, args.branch)
        except rv.ReviewRefused as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(f"auto-merged {args.branch} tier 0 {res.merge_sha}")
        return 0
    now = datetime.now(UTC)
    record = rv.read_run_record(repo, args.branch)
    from kf.evalx.gate_run import gate_from_record

    gate = gate_from_record(repo, args.branch, record)
    second = rv.Approval(args.second_by, "person", now) if args.second_by else None
    try:
        res = rv.approve_and_merge(
            repo, args.branch, approval=rv.Approval(args.by, args.kind, now), test_run=args.test_run,
            gate=gate, queue=FlagQueue(args.db), second_approval=second,
        )
    except rv.ReviewRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(f"merged {args.branch} tier {int(res.tier)} {res.merge_sha} flags resolved: {res.resolved_flags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
