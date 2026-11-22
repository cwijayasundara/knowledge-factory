import argparse
import sys

from pathlib import Path

from kf.bundle.ci import run_ci
from kf.evalx import removal
from kf.flags.models import FlagStatus
from kf.flags.queue import FlagQueue
from kf.review.gate import GateResult, Scores, eval_gate

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
    for name in ("list", "show", "approve", "reject"):
        sp = rv.add_parser(name)
        sp.add_argument("--repo", default=".")
        if name == "show" or name == "reject":
            sp.add_argument("branch")
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
    sl.add_argument("--list", default=str(removal.DEFAULT_LIST))
    sl.add_argument("--seal-file", default=str(removal.DEFAULT_SEAL))
    ev = sub.add_parser("eval", help="run e2ekg evals, G2 verdict, metrics").add_subparsers(dest="sub", required=True)
    er = ev.add_parser("run", help="run e2ekg eval over the curation or held-out seeds")
    er.add_argument("--arms", default="graph", help="comma list of e2ekg arms, e.g. graph or graph_kb")
    er.add_argument("--scenarios", default="all", help="comma list of e2ekg scenario names, or all")
    er.add_argument("--runs", type=int, default=3, help="runs per LLM arm and scenario")
    er.add_argument("--starve", action="store_true", help="knowledge-starved baseline (E2EKG_STARVE)")
    er.add_argument("--heldout", action="store_true", help="held-out seeds (default: curation seeds)")
    er.add_argument("--test-run", action="store_true", help="mark as a test run (never a headline)")
    er.add_argument("--bundle-commit", help="bundle commit to snapshot (default HEAD)")
    er.add_argument("--now", help="KF_NOW for the kb tools (default: the bundle commit's author date)")
    er.add_argument("--state-dir", default="state")
    er.add_argument("--data-base", default=".", help="directory holding data_curation/ and data_heldout/")
    er.add_argument("--bundle", default="bundle")
    eg = ev.add_parser("g2", help="G2 verdict from a starved graph run and a graph_kb run")
    eg.add_argument("--starved", required=True, help="run directory of the starved graph run")
    eg.add_argument("--kb", required=True, help="run directory of the graph_kb run")
    eg.add_argument("--state-dir", default="state")
    eg.add_argument("--report", default="reports/g2.md")
    eg.add_argument("--list", default=str(removal.DEFAULT_LIST))
    eg.add_argument("--seal-file", default=str(removal.DEFAULT_SEAL))
    em = ev.add_parser("metrics", help="curator and corpus metrics as JSON")
    em.add_argument("--state-dir", default="state")
    em.add_argument("--db", default=None, help="flag queue (default <state-dir>/flags.db)")
    em.add_argument("--bundle", default="bundle")
    args = p.parse_args(argv)
    if args.cmd == "eval":
        from kf.evalx import cli as evalx_cli

        return evalx_cli.run(args)
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
    print(removal.seal(Path(args.list), Path(args.seal_file)))
    return 0


def _gate_from_scores(scores) -> GateResult | None:
    """Compute the gate from recorded scores; missing or malformed scores mean no gate result."""
    try:
        return eval_gate(Scores(**scores["base"]), Scores(**scores["head"]))
    except (KeyError, TypeError):
        return None


def _review(args) -> int:
    from datetime import UTC, datetime

    from kf.review import review as rv

    repo = Path(args.repo)
    if args.sub == "list":
        for b in rv._git(repo, "branch", "--list", "kf/*", "--format=%(refname:short)").splitlines():
            print(f"{b}\ttier {int(rv.tier_of(repo, b))}")
        return 0
    if args.sub == "show":
        print(f"{args.branch}\ttier {int(rv.tier_of(repo, args.branch))}")
        for f in rv.changed_files(repo, args.branch):
            print(f"{f.change}\t{f.path}")
        return 0
    if args.sub == "reject":
        rv.record_rejection(repo, args.branch, args.by, args.reason, datetime.now(UTC))
        return 0
    now = datetime.now(UTC)
    record = rv.read_run_record(repo, args.branch)
    gate = _gate_from_scores(record.get("scores"))
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
