"""`lab-kit run` and `lab-kit runs`: start a run against the lock, and list the runs."""

from __future__ import annotations

import datetime as _dt
import os
import socket
import subprocess
import sys

from .. import ops
from .. import protocol as protocol_mod
from .. import records
from .. import store as store_mod
from ..errors import LabError
from ..lab import RUNNING, Lab


def _run_id(lab: Lab, slug: str) -> str:
    while True:
        run_id = records.new_run_id(_dt.datetime.now(_dt.timezone.utc))
        if not any((root / slug / run_id).exists() for root in (lab.runs_dir, lab.root / RUNNING)):
            return run_id


def _check_mission(lab: Lab, mission: str | None, spend: bool) -> str | None:
    if mission is None:
        if spend:
            raise LabError("a run that spends names its mission: --mission missions/<id>.md")
        return None
    target = ops.mission_path(lab, mission)
    if target is None or not target.is_file():
        raise LabError(f"mission {mission} does not exist")
    rel = lab.rel(target)
    record = ops.read_mission(lab, target)
    problem = record.approval_problem()
    if problem is not None:
        raise LabError(problem)
    if spend and record.cap is None:
        raise LabError(f"{rel} records no numeric `cap:`; no run spends without the operator's approval and a cap")
    return rel


def start(lab: Lab, slug: str, command: list[str], mission: str | None = None, spend: bool = False,
          wait: bool = False) -> tuple[list[str], int]:
    """Start a run; with `wait`, block until it ends. Returns what changed and the command's exit code."""
    if not command:
        raise LabError("name the command after `--`: lab-kit run <slug> -- <command>")
    if not (lab.experiments / slug).is_dir():
        slug = lab.experiment_for(slug) or slug
    lock = records.read_lock(lab, slug)
    if lock is None:
        raise LabError(f"experiments/{slug}/{records.LOCK} does not exist: no run starts before the lock")
    proto = protocol_mod.require(lab, lock.protocol)
    if proto.status != "locked":
        raise LabError(f"{proto.path} has status `{proto.status}`, not `locked`")
    if protocol_mod.hash_text(proto.text()) != lock.sha256:
        raise LabError(f"{proto.path} changed since its lock; no run starts against a broken lock")
    if lock.instrument is not None and records.instrument_hash(lab.experiments / slug / "bin") != lock.instrument:
        raise LabError(f"experiments/{slug}/bin/ changed since its lock; no run starts against a broken lock")
    config = protocol_mod.pinned_config(proto.text(), proto.path)
    mission_rel = _check_mission(lab, mission, spend)
    if lab.settings.store:
        store_mod.ensure_link(lab)
        base_dir = lab.root / RUNNING
    else:
        base_dir = lab.runs_dir
    run_id = _run_id(lab, slug)
    run_dir = base_dir / slug / run_id
    run_dir.mkdir(parents=True)
    base = lab.rel(run_dir)
    records.write_json(run_dir / records.RUN, {
        "experiment": slug, "id": run_id, "protocol": lock.protocol, "lock": lock.sha256, "config": config,
        "mission": mission_rel, "spend": spend, "command": command, "host": socket.gethostname(),
        "started": records.now(), "ended": None, "exit": None, "pid": None, "spent": None,
        **records.provenance(lab.root),
    })
    changed = [f"created {base}/{records.RUN}", f"started {' '.join(command)}", f"log: {base}/{records.LOG}"]
    if lab.settings.store:
        changed.append(f"when it ends, it is sealed and moves to runs/{slug}/{run_id} in the store")
    child = subprocess.Popen([sys.executable, "-m", "lab_kit.supervise", str(run_dir), str(lab.root)],
                             cwd=lab.root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True, env=_child_env())
    data = records.read_json(run_dir / records.RUN, f"{base}/{records.RUN}")
    data["pid"] = child.pid
    records.write_json(run_dir / records.RUN, data)
    if not wait:
        return changed + [f"running in the background; `lab-kit runs --live` shows it"], 0
    code = child.wait()
    final = run_dir if run_dir.is_dir() else lab.runs_dir / slug / run_id
    data = records.read_json(final / records.RUN, f"runs/{slug}/{run_id}/{records.RUN}")
    changed.append(f"sealed runs/{slug}/{run_id} ({len(data.get('files') or {})} files)")
    changed.append(f"ended with exit code {data.get('exit')}")
    return changed, code


def _child_env() -> dict[str, str]:
    """The environment for the supervisor, with this package importable the way it is here."""
    env = dict(os.environ)
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env["PYTHONPATH"] = here + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def listing(lab: Lab, live: bool = False) -> list[str]:
    rows = []
    for run in records.runs(lab):
        state = run.state
        if live and state not in ("running", "orphaned"):
            continue
        exit_code = run.data.get("exit")
        rows.append(f"{run.base}  {state:<9} started {run.data.get('started')}"
                    + (f"  exit {exit_code}" if exit_code is not None else ""))
    if not rows:
        return ["No live runs." if live else "No runs."]
    return rows
