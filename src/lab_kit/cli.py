"""The `lab-kit` command line. Only skills call it, the way an agent calls git."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, frozen
from . import lab as lab_mod
from . import rederive as rederive_mod
from .checks import run as checks_run
from .commands import experiments, runs, setup, status
from .errors import LabError


def _lab() -> lab_mod.Lab:
    return lab_mod.load(Path.cwd())


def _print(lines: list[str]) -> None:
    for line in lines:
        print(line)


def cmd_init(args: argparse.Namespace) -> int:
    _print(setup.init(Path.cwd(), args.library))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    lab = _lab()
    problems = checks_run.run(lab, args.only)
    errors = sum(1 for p in problems if p.severity == "error")
    warnings = sum(1 for p in problems if p.severity == "warning")
    if args.json:
        print(json.dumps({"problems": [p.as_dict() for p in problems], "errors": errors, "warnings": warnings},
                         indent=2, ensure_ascii=False))
    else:
        _print([p.line() for p in problems])
        print(f"lab-kit check: {errors} errors, {warnings} warnings")
    return 1 if errors else 0


def cmd_experiment(args: argparse.Namespace) -> int:
    _print(experiments.experiment(_lab(), args.slug))
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    _print(experiments.lock(_lab(), args.slug))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    command = list(args.command or [])
    changed, code = runs.start(_lab(), args.slug, command, mission=args.mission, spend=args.spend, wait=args.wait)
    _print(changed)
    return 0 if code == 0 else 1


def cmd_runs(args: argparse.Namespace) -> int:
    _print(runs.listing(_lab(), live=args.live))
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    _print(experiments.score(_lab(), args.slug))
    return 0


def cmd_rederive(args: argparse.Namespace) -> int:
    lab = _lab()
    doc = rederive_mod.result_doc(lab, args.id)
    outcome = rederive_mod.run(lab, doc)
    if outcome.ok:
        print(f"{doc.id}: re-derived `{outcome.printed}`, its number")
        return 0
    print(f"{doc.id}: does not re-derive: {outcome.detail}")
    return 1


def cmd_freeze(args: argparse.Namespace) -> int:
    _print(frozen.freeze(_lab(), args.path))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _print(status.status(_lab()))
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"lab-kit {__version__}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lab-kit", description="A research lab's method and machinery on folio.")
    sub = p.add_subparsers(dest="command_name")

    s = sub.add_parser("init", help="Write lab.yaml, ops/, experiments/, .lab/, the skills and the roles. "
                       "Before a library exists, only the method, the skills and the roles.")
    s.add_argument("--library", help="the folder holding folio.yaml, from the lab root (default: the lab root)")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("check", help="The lab gate: folio check, then the lab checks. Changes nothing.")
    s.add_argument("--only", action="append", metavar="ID", help="run only this check (repeatable); "
                   "`folio` names folio's gate")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("experiment", help="Create experiments/<slug>/ with bin/, runs/ and a gitignore.")
    s.add_argument("slug")
    s.set_defaults(func=cmd_experiment)

    s = sub.add_parser("lock", help="Write lock.json for a locked protocol whose gate is green.")
    s.add_argument("slug")
    s.set_defaults(func=cmd_lock)

    s = sub.add_parser("run", usage="lab-kit run <slug> [--mission <file>] [--spend] [--wait] -- <command>",
                       help="Check the lock, write run.json, and run the command in the background.")
    s.add_argument("slug")
    s.add_argument("--mission", help="the mission file this run belongs to")
    s.add_argument("--spend", action="store_true", help="the run spends tokens or money")
    s.add_argument("--wait", action="store_true", help="wait for the command to end")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("runs", help="List runs and their state: running, finished, failed, orphaned.")
    s.add_argument("--live", action="store_true", help="only running and orphaned runs")
    s.set_defaults(func=cmd_runs)

    s = sub.add_parser("score", help="Create score.yaml from the lock's prediction and rule ids.")
    s.add_argument("slug")
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("rederive", help="Run one result's re-derive command against its number.")
    s.add_argument("id")
    s.set_defaults(func=cmd_rederive)

    s = sub.add_parser("freeze", help="Record a frozen surface's hashes. Only the operator asks for this.")
    s.add_argument("path")
    s.set_defaults(func=cmd_freeze)

    s = sub.add_parser("status", help="The state, the active mission, live runs, and protocols by status.")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("version", help="The lab-kit version.")
    s.set_defaults(func=cmd_version)
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    command: list[str] | None = None
    if "--" in argv:  # what follows `--` is the lab's own command, passed on untouched
        cut = argv.index("--")
        argv, command = argv[:cut], argv[cut + 1:]
    args = p.parse_args(argv)
    args.command = command
    if args.command_name is None:
        p.print_help()
        return 2
    try:
        return args.func(args)
    except LabError as exc:
        print(f"lab-kit: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
