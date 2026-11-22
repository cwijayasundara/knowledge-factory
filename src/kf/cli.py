import argparse
import sys

from pathlib import Path

from kf.bundle.ci import run_ci
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
    args = p.parse_args(argv)
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


if __name__ == "__main__":
    sys.exit(main())
