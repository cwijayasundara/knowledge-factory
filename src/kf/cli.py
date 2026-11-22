import argparse
import sys

from pathlib import Path

from kf.bundle.ci import run_ci
from kf.flags.models import FlagStatus
from kf.flags.queue import FlagQueue
from kf.review.gate import GateResult

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
    args = p.parse_args(argv)
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
    gate = record.get("gate")
    gate = GateResult(bool(gate.get("passed")), list(gate.get("reasons", []))) if isinstance(gate, dict) else None
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
