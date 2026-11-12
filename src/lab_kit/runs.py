"""Runs: started detached, written on this machine, sealed when the command exits, then moved into the store.

The protocol, each step of which is a failure that already happened once:

1. `lab run` checks the lock and the resources, writes the run's record under `.lab/running/`, lists the run in
   the experiment's `runs.tsv`, starts a detached supervisor and returns. A stalled store never stalls the command.
2. The supervisor runs the command in a process group of its own, records how it ended and what it spent, and
   seals the folder: every file's hash, and one hash over the record. The seal goes into `runs.tsv`, which git
   keeps: the store is outside git, and without that row a run could be removed or rewritten with no trace.
3. It then moves the run into the store: a copy into `.incoming/`, every file checked against the seal, one
   rename into place, read-only, and only then the local copy deleted. Nothing in the store is ever
   overwritten. A move that fails leaves the run where it is and says why beside it; `lab runs publish` retries.
"""
from __future__ import annotations

import contextlib, datetime, fcntl, json, os, random, shlex, shutil, signal, string, subprocess, sys, time

from . import record as R


def stop(msg):
    raise SystemExit(msg)


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


@contextlib.contextmanager
def exclusive(root):
    """One writer at a time. Two commands started together would take the same number, or start the same run twice."""
    os.makedirs(os.path.join(root, ".lab", "running"), exist_ok=True)
    with open(os.path.join(root, ".lab", "running", ".lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def run_id_or_stop(run_id):
    if not R.RUN_ID.match(str(run_id)):
        stop(f"{run_id!r} is not a run's id, such as 20261110-1432_G1.Q2.3_k7f2")
    return run_id


def ledger(lab, x, run_id, kind, what, at, code="", seal="", used="", note=""):
    """Add one row to an experiment's runs.tsv. Rows are only ever added."""
    path = os.path.join(lab.root, x["dir"], "runs.tsv")
    text = R.read(path) if os.path.isfile(path) else ""
    row = [run_id, kind, what, str(at), str(code), str(seal)] + ([str(used), R.flat(note).replace("\t", " ")] if used or note else [])
    with open(path, "a") as f:
        f.write(("\t".join(R.LEDGER) + "\n" if not text.strip() else "" if text.endswith("\n") else "\n") + "\t".join(row) + "\n")


def listed(lab, x, run_id):
    """What an experiment's runs.tsv says of one run, read now: {"started": bool, "ended": bool}."""
    path = os.path.join(lab.root, x["dir"], "runs.tsv")
    rows = [l.split("\t") for l in R.read(path).split("\n") if l.strip()] if os.path.isfile(path) else []
    mine = [r[2] for r in rows if len(r) >= 3 and r[0] == run_id]
    return {"started": "started" in mine, "ended": "ended" in mine or "lost" in mine}


def record_end(lab, record):
    """Put an ended run's seal in its experiment's runs.tsv, once. Returns whether the row is there now."""
    x = lab.nodes.get(record.get("experiment"))
    if not x or x["type"] != "experiment" or not record.get("ended") or not record.get("seal"):
        return False
    said = listed(lab, x, record["id"])
    if said["ended"]:
        return True
    try:
        if not said["started"]:  # it started where the lab could not be written
            ledger(lab, x, record["id"], record["kind"], "started", record["started"])
        ledger(lab, x, record["id"], record["kind"], "ended", record["ended"], record.get("exit"), record["seal"])
    except OSError:
        return False
    return True


def start(lab, ident, command, trial=False, wait=False, changed=""):
    """Start one run of an experiment, detached. A trial comes before the lock and never gives a result."""
    with exclusive(lab.root):
        lab = R.Lab(lab.root)  # as it is now that no other command is writing
        run_id, rdir = _start(lab, ident, command, trial, changed)
        proc = subprocess.Popen([sys.executable, "-m", "lab_kit.supervise", rdir], cwd=lab.root, start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if wait:
        proc.wait()
    else:
        for _ in range(40):  # return once the supervisor has put its pid in the record
            if read(rdir).get("pid") or proc.poll() is not None:
                break
            time.sleep(0.05)
    return run_id


def _start(lab, ident, command, trial, changed):
    x = lab.nodes.get(ident)
    if not x or x["type"] != "experiment":
        stop(f"no experiment {ident}")
    if x["state"] in ("dropped", "replaced", "review failed"):
        stop(f"{ident} is {x['state']}")
    why = lab._blocked(x)
    if why:
        stop(f"{ident} waits on {why}")
    held = lab.holding(ident)
    if held:
        stop(f"{ident} is held by the decision {held[0]['id']}, which is not settled")
    going = [r for r in x["runs"] + x["trials"] if r["state"] == "running"]
    if going:
        stop(f"{going[0]['id']} of {ident} is still going" + (": its process is gone, `lab runs close` it first" if going[0]["orphan"] else
                                                                f": runs.tsv lists it as started, and its folder is not on this machine. If it is gone for good: `lab runs lost {going[0]['id']} \"<why>\"`" if going[0]["missing"] else ""))
    plan = os.path.join(lab.root, x["dir"], "plan")
    if R.symlinks(plan):
        stop(f"{ident}: plan/ holds a link, {R.symlinks(plan)[0]}. A run pins what it executes, and what a link points at is not in plan/: copy it in")
    if R.compiled(plan) and (x["lock"] or {}).get("kit") != "1.0.0":  # 1.0.0 hashed such a file with the plan; no later kit does
        stop(f"{ident}: plan/ holds a compiled file outside __pycache__, {R.compiled(plan)[0]}. Python would import it, and a `.pyc` is not pinned: remove it, and keep the script")
    from . import history
    if any(lab.metered(r) for r in x["uses"]):  # before the hours are spent, not after
        against = history.resources(lab) + history.decisions(lab)
        if against:
            stop(f"{ident} runs on a metered resource, and the amounts or the decisions behind them are not as git holds them:\n- " + "\n- ".join(against))
    lock = None
    if trial:
        if x["lock"]:
            stop(f"{ident} is locked: a trial run comes before the lock")
        if any(lab.metered(r) for r in x["uses"]) and lab.reviewed(x, "plan") != ("pass", True):
            stop(f"{ident} uses a metered resource: its plan is reviewed before anything runs on it, a trial too")
    else:
        if not x["lock"]:
            stop(f"{ident} is not locked")
        if not lab.lock_holds(x):
            if x["lock"].get("card") == lab.before_hash(x):  # the demand is as locked, so it is `uses:` that moved
                stop(f"{ident}: the resources it uses changed after the lock: it was locked on {', '.join(sorted(map(str, x['lock']['uses']))) or 'none'}, and `uses:` now names "
                     f"{', '.join(sorted(map(str, x['uses']))) or 'none'}. That never changes: replace the experiment")
            stop(f"{ident}: what it demands (its comparison, arms, cases, bars, outcomes or limits) changed after the lock. That never changes: replace the experiment")
        if x["finished"]:
            stop(f"{ident} has a finished run, {x['finished']['id']}, and takes no more: it is the only source of its results. A repeat is a new experiment")
        lock = {"card": x["lock"]["card"]}
        ran = [r for r in x["runs"] if not r["missing"]]  # a lost run pinned nothing that can be read
        before = ran[-1] if ran else None  # the first run is held against the plan/ that was locked
        was, how, since = (before.get("plan"), before["how"], f"what {before['id']} ran") if before else (x["lock"].get("plan"), x["lock"]["hash"], "what was locked")
        if was and not lab.plan_is(x, was, how) and not R.flat(changed):
            stop(f"{ident}: plan/ is not {since}. Say what changed and why, in a sentence the operator can read: "
                 f"lab run {ident} --changed \"<what changed since {'the last run' if before else 'the lock'}, and why>\" -- <command>")
    caps = {}
    for name in x["uses"]:
        if name not in lab.resources:
            stop(f"{ident} uses {name}, which resources.toml does not list")
        if lab.resources[name].get("retired"):
            stop(f"{ident} uses {name}, which is retired: {lab.resources[name]['retired']}")
        if not lab.metered(name):
            continue
        if not lab.granted_by(name):
            stop(f"{name}: its amounts come out of a decision. `from = \"D<n>\"` in resources.toml names the settled decision that set them, and that decision lists {name} under `about:`")
        cap, per_run = lab.cap(x, name), lab.resources[name].get("per_run")
        if not R.amount(cap):
            stop(f"{name} has no amount for one run (`per_run`), and {ident} has no override")
        if R.amount(per_run) and cap > per_run and not lab.settled_for(ident):
            stop(f"{ident}: its cap of {cap:g} {lab.resources[name].get('unit', '')} on {name} is above the {per_run:g} one run may use. That takes a decision about {ident}: `lab new decision \"<title>\" --about {ident}`")
        if cap > lab.left(name):
            stop(f"{ident}: its cap of {cap:g} on {name} is more than the {lab.left(name):g} left of what is granted. That takes a decision: `lab new decision \"<title>\" --about {ident}`")
        caps[name] = cap
    stamp = datetime.datetime.now(datetime.timezone.utc)
    run_id = f"{stamp.strftime('%Y%m%d-%H%M')}_{ident}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
    rdir = os.path.join(lab.running, run_id)
    os.makedirs(rdir)
    record = {"id": run_id, "experiment": ident, "kind": "trial" if trial else "run", "lock": lock, "command": command, "host": os.uname().nodename, "pid": None, "child": None,
              "started": now(), "ended": None, "exit": None, "cap": caps, "used": None, "commit": R.code_head(lab), "plan": lab.plan_hash(x), "hash": R.HASH, "changed": R.flat(changed), "files": {}, "seal": None}
    write(rdir, record)
    ledger(lab, x, run_id, record["kind"], "started", record["started"])
    return run_id, rdir


def read(rdir):
    return json.load(open(os.path.join(rdir, "run.json")))


def write(rdir, record):
    tmp = os.path.join(rdir, "run.json.tmp")
    open(tmp, "w").write(json.dumps(record, indent=1) + "\n")
    os.replace(tmp, os.path.join(rdir, "run.json"))


def said_used(lab, rdir):
    """What a run's command says it used, in `used.json`: ({resource: amount}, what was refused or None)."""
    path = os.path.join(rdir, "used.json")
    if not os.path.exists(path):
        return None, None
    try:
        said = json.loads(R.read(path))
    except ValueError:
        return None, "used.json cannot be read"
    if not isinstance(said, dict):
        return None, "used.json is not `{\"<resource>\": <amount>}`"
    refused = sorted(str(k) for k, v in said.items() if k in lab.resources and not R.amount(v))
    return {k: v for k, v in said.items() if k in lab.resources and R.amount(v)}, (f"used.json gives no amount for {', '.join(refused)}: an amount is a number, finite and not negative" if refused else None)


def supervise(rdir):
    """The detached half of `lab run`: run the command, seal the folder, list its seal, move it into the store."""
    lab = R.Lab(os.getcwd())
    record = read(rdir)
    record["pid"] = os.getpid()
    write(rdir, record)
    code = -1
    try:
        with open(os.path.join(rdir, "run.log"), "w") as out:
            # A group of its own, so that whatever the command starts can be found and stopped if this supervisor dies.
            proc = subprocess.Popen(record["command"], cwd=lab.root, stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
                                    env={**os.environ, "LAB_RUN": rdir, "PYTHONDONTWRITEBYTECODE": "1"})
            record["child"] = proc.pid
            write(rdir, record)
            code = proc.wait()
    finally:
        record["ended"], record["exit"] = now(), code
        record["used"], refused = said_used(lab, rdir)
        if refused:
            record["used_refused"] = refused
        seal(rdir, record)
        record_end(lab, record)
        publish(lab, rdir)


def seal(rdir, record):
    files = (os.path.relpath(os.path.join(top, f), rdir) for top, _, fs in os.walk(rdir) for f in fs)
    record["files"] = {p: R.sha(os.path.join(rdir, p)) for p in files if p not in ("run.json", "run.json.tmp")}  # only the record itself is left out
    record["seal"] = R.seal_of(record)
    write(rdir, record)


def verify(folder):
    """Why a run's folder does not match its own seal, or None."""
    try:
        record = read(folder)
    except (OSError, ValueError):
        return "its record cannot be read"
    if not isinstance(record, dict) or not isinstance(record.get("files"), dict):
        return "its record lists no files"
    if R.seal_of(record) != record.get("seal"):
        return "the record does not match its seal"
    here = {os.path.relpath(os.path.join(top, f), folder) for top, _, fs in os.walk(folder) for f in fs} - {"run.json"}
    if here != set(record["files"]):
        return f"files differ from the record: {sorted(here ^ set(record['files']))[:3]}"
    for p, h in record["files"].items():
        if R.sha(os.path.join(folder, p)) != h:
            return f"{p} does not match its hash"
    return None


def publish(lab, rdir, keep=False):
    """Move one ended run from this machine into the store. Returns where it is now, or None with the reason beside it."""
    run_id = run_id_or_stop(os.path.basename(rdir.rstrip("/")))  # the id is letters, digits, dots, a dash and underscores: safe in a path here and there
    note = rdir.rstrip("/") + ".unpublished"
    try:
        if not read(rdir).get("ended"):
            stop(f"{run_id} has not ended")
        record_end(lab, read(rdir))
        if lab.store_host():
            where = publish_ssh(lab, rdir, run_id)
        else:
            if not os.path.isdir(lab.store_root):
                raise OSError(f"the store {lab.store_root} is not here; set LAB_STORE_HOST to a machine that has it")
            dst, inc = os.path.join(lab.store_root, "runs", run_id), os.path.join(lab.store_root, ".incoming", run_id)
            if os.path.exists(dst):  # never overwrite: a copy already there counts only if it is this very run
                if verify(dst) or read(dst)["seal"] != read(rdir)["seal"]:
                    raise OSError(f"{dst} already holds a different run")
            else:
                shutil.rmtree(inc, ignore_errors=True)
                os.makedirs(os.path.dirname(inc), exist_ok=True)
                shutil.copytree(rdir, inc)
                why = verify(inc)
                if why:
                    raise OSError(f"the copy in .incoming did not verify: {why}")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.rename(inc, dst)
                for top, _, fs in os.walk(dst):
                    for f in fs:
                        os.chmod(os.path.join(top, f), 0o444)
            where = dst
        if os.path.exists(note):
            os.remove(note)
        if not keep:
            shutil.rmtree(rdir)
        return where
    except (OSError, subprocess.CalledProcessError) as err:
        open(note, "w").write(f"{now()} not moved to the store: {err}\n`lab runs publish` retries.\n")
        return None


def publish_ssh(lab, rdir, run_id):
    """The same move, onto a store this machine does not mount. Not overwriting, verified there before the rename."""
    host, root = lab.store_host(), lab.store_root
    dst, inc = f"{root}/runs/{run_id}", f"{root}/.incoming/{run_id}"
    sums = "".join(f"{h}  {p}\n" for p, h in sorted(read(rdir)["files"].items()))
    q = shlex.quote
    subprocess.run(["ssh", host, f"test ! -e {q(dst)} && rm -rf {q(inc)} && mkdir -p {q(inc)} {q(os.path.dirname(dst))}"], check=True, capture_output=True)
    subprocess.run(["rsync", "-a", rdir.rstrip("/") + "/", f"{host}:{inc}/"], check=True, capture_output=True)
    subprocess.run(["ssh", host, f"cd {q(inc)} && sha256sum -c --quiet - && test \"$(find . -type f | wc -l)\" = {len(read(rdir)['files']) + 1} "
                                 f"&& mv {q(inc)} {q(dst)} && chmod -R a-w {q(dst)}"], input=sums, text=True, check=True, capture_output=True)
    return f"{host}:{dst}"


def fetch(lab, run_id):
    """Copy one run from the store's machine into `.lab/fetched/`, and verify it against its seal."""
    run_id_or_stop(run_id)
    host = lab.store_host()
    if not host:
        stop("the store is mounted here: read the run under runs/. `lab runs fetch` is for a machine without the mount (set LAB_STORE_HOST)")
    dst = os.path.join(lab.root, ".lab", "fetched", run_id)
    os.makedirs(dst, exist_ok=True)
    try:
        subprocess.run(["rsync", "-a", f"{host}:{lab.store_root}/runs/{run_id}/", dst + "/"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as err:
        shutil.rmtree(dst, ignore_errors=True)
        stop(f"{run_id} could not be copied from {host}: {(getattr(err, 'stderr', '') or str(err)).strip().splitlines()[-1][:160]}")
    why = verify(dst)
    if why:
        stop(f"the fetched copy does not verify: {why}")
    record_end(lab, read(dst))
    return lab.rel(dst)


def stop_group(record, rdir):
    """Stop what a dead supervisor left running: the command's process group, if it is still this run's. Returns what
    could not be done, or None. A group is stopped only when one of its processes carries this run's folder in its
    environment; where that cannot be read, nothing is stopped, because the number may by now be another program's."""
    pid = record.get("child")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
        return None
    try:
        os.killpg(pid, 0)
    except OSError:
        return None  # nothing is left of it
    if not os.path.isdir("/proc/self"):
        return f"what the run left running could not be told from another program on this system, and was not stopped: look at process group {pid}"
    mine = False
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                if os.getpgid(int(p)) == pid and f"LAB_RUN={rdir}".encode() in open(f"/proc/{p}/environ", "rb").read().split(b"\0"):
                    mine = True
            except OSError:
                continue
    try:
        if mine:
            os.killpg(pid, signal.SIGKILL)
    except OSError:
        pass
    return None


def stated(lab, used):
    for name, v in (used or {}).items():
        if not lab.metered(name) or not R.amount(v):
            stop(f"--used {name}={v}: a metered resource of resources.toml, and an amount")
    return dict(used or {})


def lost(lab, run_id, why, used=None):
    """Declare lost a run that started and whose folder is nowhere: the machine died, or the folder was cleaned away. It
    counts as a run that failed, another may follow, and it stays in the experiment's list with the reason."""
    run_id_or_stop(run_id)
    if not R.flat(why):
        stop("say why the run is lost, in a sentence the operator can read")
    for r in lab.runs:
        if r["id"] == run_id:
            if not r["missing"]:
                stop(f"{run_id} is here, in {r['dir']}: " + ("it is still going, or its process died: `lab runs close`" if r["state"] == "running" else "it has ended: `lab runs publish` lists its seal"))
            if r["state"] != "running":
                stop(f"{run_id} has already ended, as runs.tsv says")
            x = lab.nodes[r["experiment"]]
            used = stated(lab, used)
            ledger(lab, x, run_id, r["kind"], "lost", now(), used=json.dumps(used, sort_keys=True) if used else "", note=why)
            return os.path.join(x["dir"], "runs.tsv")
    stop(f"no run {run_id} is listed as started")


def close(lab, run_id, why, used=None):
    """Close a run whose process died: stop what it left running, record that it stopped and what it used, seal what it
    left, move it into the store."""
    run_id_or_stop(run_id)
    if not R.flat(why):
        stop("say why the run is closed")
    for r in lab.runs:
        if r["id"] == run_id:
            if r["state"] != "running":
                stop(f"{run_id} has already ended")
            if r["missing"]:
                stop(f"{run_id} is listed in runs.tsv and its folder is not on this machine: close it where it ran, or if it is gone for good, `lab runs lost {run_id} \"<why>\"`")
            if not r["orphan"]:
                stop(f"{run_id} is still running, or ran on another machine ({r.get('host')}): close it there")
            used = stated(lab, used)
            rdir = os.path.join(lab.root, r["dir"])
            record = read(rdir)
            left = stop_group(record, rdir)
            if left:
                print(f"note: {left}", file=sys.stderr)
            record.update(ended=now(), exit=-1, closed=" ".join(why.split()))
            record["used"], refused = said_used(lab, rdir)
            if refused:
                record["used_refused"] = refused
            by_hand = {k: v for k, v in (used or {}).items() if k not in (record["used"] or {})}  # what the run wrote itself stands
            if by_hand:
                record["used"], record["used_by_hand"] = {**(record["used"] or {}), **by_hand}, sorted(by_hand)
            seal(rdir, record)
            record_end(lab, record)
            return publish(lab, rdir) or lab.rel(rdir)
    stop(f"no run {run_id}")


def listing(lab):
    out = []
    for r in lab.runs:
        state = "its process is gone: close it" if r["orphan"] else f"lost ({r['lost']})" if r["lost"] else r["state"] + (f" (exit {r['exit']})" if r["state"] == "failed" else "")
        used = "".join(f", used {v:g} {lab.resources.get(k, {}).get('unit', k)}" for k, v in (r.get("used") or {}).items() if R.amount(v))
        where = "nowhere" if r["lost"] else "listed in runs.tsv, and not here" if r["missing"] else "on this machine, not yet in the store" if r["local"] else "in the store"
        out.append(f"{r['id']}  {'trial, ' if r['kind'] == 'trial' else ''}{state}  {where}{used}")
    return out
