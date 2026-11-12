"""lab: the one interface to a lab, for the agent and for CI. See docs/model.md, section 5."""
from __future__ import annotations

import os, sys

from . import __version__, checks, runs, views, write
from .record import Lab, amount, find_root

USAGE = """To look
  lab now                                   the lab on one screen: what waits on the operator, what is yours next
  lab show <id or path>                     a goal, a question, an experiment, a build, a reading or a decision
  lab brief <question>                      a question's briefing, as the operator's page gives it: say this in chat
  lab since [<date>]                        what happened since the last decision was recorded
  lab define <term>                         a glossary entry
To write
  lab new decision "<title>" [--about <id>]...           something to discuss with the operator; fill its card
  lab decide <decision> --with <who> "<what was decided and why, in the lab's words>"
  lab new goal "<title>" --from <decision>
  lab new question <goal> "<short name>" --asks "<the question, in full>" --from <decision>
  lab new experiment|build|reading <question> "<title>" [--replaces <experiment> --because "<why>"]
  lab log <id> doing "<what you are starting on>" "<why now>"
  lab log <id> agent|result|stuck "<what happened>" ["<so what>"]
  lab answer <question> yes|no "<what the answer rests on>"
For evidence
  lab lock <experiment>
  lab run <experiment> [--trial] [--wait] [--changed "<what changed since the last run, and why>"] -- <command>
  lab runs                                  every run; also: lab runs publish [--keep] | fetch <run>
  lab runs close <run> "<why>" [--used <resource>=<amount>]...   a run whose process died; --used for one that wrote no used.json
  lab runs lost <run> "<why>" [--used <resource>=<amount>]...    a run that started and whose folder is gone for good
  lab review <experiment> plan|results pass|fail "<note>" [--by <who>]
  lab check [--no-rederive] [--strict]      runs every command in results.tsv: only on a lab you trust. --strict fails when
                                            history or the store could not be checked, as in CI
Once
  lab init [<folder>]"""


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "version":
        print(__version__)
        return 0
    if cmd == "init":
        root = rest[0] if rest else os.getcwd()
        print("wrote " + ", ".join(write.init(root)))
        return 0
    command = None
    if cmd == "run":  # everything after `--` is the command, untouched
        if "--" not in rest:
            raise SystemExit(USAGE)
        i = rest.index("--")
        rest, command = rest[:i], rest[i + 1:]
    held = None
    if cmd in ("new", "log", "decide", "answer", "lock", "review"):  # one writer at a time, on the lab as it then is
        held = runs.exclusive(find_root())
        held.__enter__()
    lab = Lab()

    def flag(name, many=False, switch=False):
        """Take `--name value`, or the switch `--name`, out of the arguments."""
        found = []
        while name in rest:
            i = rest.index(name)
            if switch:
                del rest[i]
                return True
            if i + 1 >= len(rest):
                raise SystemExit(f"{name} needs a value")
            found.append(rest[i + 1])
            del rest[i:i + 2]
        return False if switch else found if many else (found[-1] if found else "")

    if cmd == "now" and not rest:
        print(views.now(lab))
    elif cmd == "show" and len(rest) == 1:
        print(views.show(lab, rest[0]))
    elif cmd == "brief" and len(rest) == 1:
        print(views.brief(lab, rest[0]))
    elif cmd == "since" and len(rest) <= 1:
        print(views.since(lab, rest[0] if rest else None))
    elif cmd == "define" and rest:
        print(views.define(lab, " ".join(rest)))
    elif cmd == "new":
        replaces, origin, about, because = flag("--replaces"), flag("--from"), flag("--about", many=True), flag("--because")
        asks = flag("--asks")
        if len(rest) == 2 and rest[0] in ("goal", "decision"):
            ident, path = write.new(lab, rest[0], None, rest[1], origin=origin or None, about=about)
        elif len(rest) == 3:
            ident, path = write.new(lab, rest[0], rest[1], rest[2], replaces or None, origin=origin or None, because=because, asks=asks)
        else:
            raise SystemExit(USAGE)
        print(f"made {ident}: {path}")
    elif cmd == "log":
        if not 3 <= len(rest) <= 4:
            raise SystemExit(USAGE)
        print(f"added to {write.log(lab, rest[0], rest[1], rest[2], rest[3] if len(rest) == 4 else '')}")
    elif cmd == "decide":
        with_ = flag("--with")
        if len(rest) != 2:
            raise SystemExit(USAGE)
        print(f"decided: {write.decide(lab, rest[0], rest[1], with_)}")
    elif cmd == "answer":
        if len(rest) != 3:
            raise SystemExit(USAGE)
        print(f"answered: {write.answer(lab, rest[0], rest[1], rest[2])}")
    elif cmd == "lock" and len(rest) == 1:
        print(f"locked: {write.lock(lab, rest[0])}")
    elif cmd == "run":
        trial, wait, changed = flag("--trial", switch=True), flag("--wait", switch=True), flag("--changed")
        if len(rest) != 1 or not command:
            raise SystemExit(USAGE)
        run_id = runs.start(lab, rest[0], command, trial=trial, wait=wait, changed=changed)
        r = next((x for x in Lab(lab.root).runs if x["id"] == run_id), None)
        if wait:
            print(f"{run_id}: {r['state']}" + (f" (exit {r['exit']})" if r["state"] == "failed" else "") + f", {r['dir']}" + ("" if not r["local"] else "; not yet in the store"))
        else:
            print(f"started {run_id}: it runs on without this session. `lab runs` shows it; its output is in .lab/running/{run_id}/run.log until it ends")
    elif cmd == "runs":
        if not rest:
            print("\n".join(runs.listing(lab)) or "no runs")
        elif rest[0] in ("close", "lost"):
            used = {}
            for pair in flag("--used", many=True):
                name, _, text = pair.partition("=")
                try:
                    used[name] = float(text) if "." in text or "e" in text.lower() else int(text)
                except ValueError:
                    raise SystemExit(f"--used {pair}: <resource>=<amount>")
            if len(rest) != 3:
                raise SystemExit(USAGE)
            if rest[0] == "lost":
                with runs.exclusive(lab.root):
                    print(f"recorded as lost in {runs.lost(Lab(lab.root), rest[1], rest[2], used)}; commit it")
            else:
                print(f"closed: {runs.close(lab, rest[1], rest[2], used)}")
        elif rest[0] == "publish":
            keep = flag("--keep", switch=True)
            for r in lab.runs:  # a run that ended where the lab could not be written gets its seal listed here
                if not r["missing"] and not r["local"] and r["state"] != "running" and runs.record_end(lab, runs.read(os.path.join(lab.root, r["dir"]))) and not (lab.nodes.get(r["experiment"], {}).get("listed", {}).get(r["id"]) or {}).get("ended"):
                    print(f"{r['id']}: its seal is now in runs.tsv")
            ended = [r for r in lab.runs if r["local"] and r["state"] != "running"]
            for r in ended:
                where = runs.publish(lab, os.path.join(lab.root, r["dir"]), keep=keep)
                print(f"{r['id']}: " + (f"in the store, {where}" if where else "not moved; the reason is beside it"))
            if not ended:
                print("nothing to move")
        elif rest[0] == "fetch" and len(rest) == 2:
            print(f"fetched and verified: {runs.fetch(lab, rest[1])}")
        else:
            raise SystemExit(USAGE)
    elif cmd == "review":
        by = flag("--by")
        if len(rest) != 4:
            raise SystemExit(USAGE)
        print(f"recorded in {write.review(lab, rest[0], rest[1], rest[2], rest[3], by or None)}")
    elif cmd == "check":
        if set(rest) - {"--no-rederive", "--strict"}:
            raise SystemExit(USAGE)
        problems, notes, unchecked = checks.run(lab, rederive="--no-rederive" not in rest)
        for n in notes:
            print(f"note: {n}")
        if problems:
            print("\n".join(problems))
            print(f"{len(problems)} problem(s)")
            return 1
        if unchecked and "--strict" in rest:
            print("not everything could be checked here (see the notes): with --strict that is a failure")
            return 1
        print("the record is sound")
        print(checks.summary(lab))
    else:
        raise SystemExit(USAGE)
    return 0


def run():
    """What the `lab` command starts. A reader that closes the pipe (`lab now | head -1`) ends it quietly."""
    try:
        code = main()
        sys.stdout.flush()  # here, not when the interpreter exits, so a closed pipe is caught
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())  # nothing is left to flush into the closed pipe
        code = 0
    sys.exit(code)


if __name__ == "__main__":
    run()
