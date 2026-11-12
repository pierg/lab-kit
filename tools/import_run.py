"""Bring an experiment that ran under lab-kit 0.6 into a 1.0 lab as what it was: its lock, and its sealed runs.

    import_run.py <lab> lock  <experiment> --locked <iso time> [--commit <sha>]
    import_run.py <lab> run   <experiment> <old run folder> [--trial] [--cap <resource>=<amount>] [--used <resource>=<amount>] [--changed "<what changed since the run before>"]

`lock` writes the experiment's lock with the time the old plan was locked. `run` copies a sealed run's files
into `runs/` under a 1.0 run id, with the times, host and exit its old record holds. A trial is imported before
the lock, so that the lock lists it. Nothing is invented: a field the old record lacks stays empty.
"""
import datetime, json, os, shutil, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from lab_kit import record as R, runs  # noqa: E402


def flag(args, name, many=False):
    found = []
    while name in args:
        i = args.index(name)
        found.append(True if i + 1 >= len(args) or args[i + 1].startswith("--") else args[i + 1])
        del args[i:i + (1 if found[-1] is True else 2)]
    return found if many else (found[-1] if found else None)


def amounts(pairs):
    return {k: float(v) if "." in v else int(v) for k, v in (p.split("=") for p in pairs)}


def main(argv):
    root, verb, ident, rest = argv[0], argv[1], argv[2], list(argv[3:])
    lab = R.Lab(root)
    x = lab.nodes[ident]
    d = os.path.join(lab.root, x["dir"])
    if verb == "lock":
        record = {"locked": flag(rest, "--locked"), "commit": flag(rest, "--commit"), "kit": __import__("lab_kit").__version__, "card": lab.before_hash(x), "plan": lab.plan_hash(x), "hash": R.HASH, "uses": sorted(x["uses"]),
                  "trials": [r["id"] for r in x["trials"]]}
        open(os.path.join(d, "lock.json"), "w").write(json.dumps(record, indent=1) + "\n")
        return print(f"locked {ident} as of {record['locked']}")
    trial, cap, used = flag(rest, "--trial"), amounts(flag(rest, "--cap", many=True)), amounts(flag(rest, "--used", many=True))
    src = rest[0].rstrip("/")
    old = json.load(open(os.path.join(src, "run.json")))
    stamp = datetime.datetime.fromisoformat(old["started"])
    run_id = f"{stamp.strftime('%Y%m%d-%H%M')}_{ident}_{os.path.basename(src)[-4:].lower().replace('_', 'x')}"
    dst = os.path.join(lab.store, run_id)
    shutil.copytree(src, dst, ignore=lambda folder, names: ["run.json"] if os.path.samefile(folder, src) else [])  # only the old record itself
    record = {"id": run_id, "experiment": ident, "kind": "trial" if trial else "run",
              "lock": None if trial else {"card": x["lock"]["card"]}, "plan": lab.plan_hash(x), "hash": R.HASH, "changed": flag(rest, "--changed") or "", "command": old.get("command"), "host": old.get("host"),
              "pid": None, "started": old["started"], "ended": old["ended"], "exit": old["exit"], "cap": cap, "used": used or None,
              "commit": old.get("commit"), "files": {}, "seal": None, "imported_from": os.path.basename(src)}
    if old.get("closed"):
        record["closed"] = old["closed"]
    runs.seal(dst, record)
    runs.record_end(lab, record)  # the run is listed in the experiment's runs.tsv, as one that `lab run` started is
    for top, _, fs in os.walk(dst):
        for f in fs:
            os.chmod(os.path.join(top, f), 0o444)
    print(run_id)


if __name__ == "__main__":
    main(sys.argv[1:])
