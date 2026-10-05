"""Checks on locks and runs: the lock is recorded and intact, and every run follows it."""

from __future__ import annotations

from .. import protocol as protocol_mod
from .. import records
from ..errors import LabError
from ..lab import Lab
from .base import Reporter

LOCKED_STATES = ("locked", "abandoned")


def lock_recorded(lab: Lab, rep: Reporter) -> None:
    """Every locked protocol has a lock.json naming it; every lock.json names a locked or abandoned protocol."""
    lib = lab.library()
    for doc in lib.documents:
        if not doc.is_a("protocol") or doc.status != "locked":
            continue
        where = lab.doc_path(doc.main.path) if doc.main else doc.key

        def one(doc=doc, where=where) -> None:
            lock = records.read_lock(lab, doc.id)
            if lock is None:
                rep.add(where, f"is locked but experiments/{doc.id}/{records.LOCK} does not exist; "
                               f"run `lab-kit lock {doc.id}`")
            elif lock.protocol.casefold() != doc.id.casefold():
                rep.add(lock.path, f"names protocol `{lock.protocol}`, not `{doc.id}`, the experiment it sits in")
        rep.guard(where, one)
    for slug in lab.experiment_slugs():
        path = f"experiments/{slug}/{records.LOCK}"

        def check_lock(slug=slug, path=path) -> None:
            lock = records.read_lock(lab, slug)
            if lock is None:
                return
            proto = protocol_mod.find(lab, lock.protocol)
            if proto is None:
                rep.add(path, f"names protocol `{lock.protocol}`, which is not in the library")
            elif proto.status not in LOCKED_STATES:
                rep.add(path, f"names protocol `{lock.protocol}`, whose status is `{proto.status}`, "
                              "not locked or abandoned")
        rep.guard(path, check_lock)


def lock_intact(lab: Lab, rep: Reporter) -> None:
    """A locked protocol, its status set aside, hashes to the value in its lock.json."""
    for slug in lab.experiment_slugs():
        path = f"experiments/{slug}/{records.LOCK}"

        def one(slug=slug, path=path) -> None:
            lock = records.read_lock(lab, slug)
            if lock is None:
                return
            proto = protocol_mod.find(lab, lock.protocol)
            if proto is None:
                return  # lab-lock-recorded names it
            actual = protocol_mod.hash_text(proto.text())
            if actual != lock.sha256:
                rep.add(proto.path, f"changed since its lock: its hash, status set aside, is {actual[:12]}, "
                                    f"and {path} records {lock.sha256[:12]}")
        rep.guard(path, one)


def run_after_lock(lab: Lab, rep: Reporter) -> None:
    """Every run belongs to a locked experiment, records the lock's hash, and started after the lock."""
    for where in records.runs_without_record(lab):
        rep.add(where, f"is a run folder with no {records.RUN}")
    for slug in lab.experiment_slugs():
        def per_experiment(slug=slug) -> None:
            lock = records.read_lock(lab, slug)
            for run in records.runs(lab, slug):
                data = run.data
                if lock is None:
                    rep.add(run.path, f"belongs to experiment `{slug}`, which has no {records.LOCK}: "
                                      "no run starts before the lock")
                    continue
                if data.get("protocol") != lock.protocol:
                    rep.add(run.path, f"names protocol `{data.get('protocol')}`, not `{lock.protocol}`")
                if data.get("lock") != lock.sha256:
                    rep.add(run.path, "records a lock hash that is not the one in "
                                      f"experiments/{slug}/{records.LOCK}")
                try:
                    started = records.parse_moment(data.get("started"), run.path + ": `started`")
                except LabError as exc:
                    rep.add(run.path, str(exc))
                    continue
                if started < lock.locked:
                    rep.add(run.path, f"started at {data.get('started')}, before the lock at "
                                      f"{lock.data.get('locked')}")
        rep.guard(f"experiments/{slug}", per_experiment)


def roster_frozen(lab: Lab, rep: Reporter) -> None:
    """Every run's configuration equals its locked protocol's pinned configuration."""
    for slug in lab.experiment_slugs():
        def per_experiment(slug=slug) -> None:
            lock = records.read_lock(lab, slug)
            proto = protocol_mod.find(lab, lock.protocol if lock else slug)
            if proto is None:
                return
            pinned = protocol_mod.pinned_config(proto.text(), proto.path)
            for run in records.runs(lab, slug):
                if run.data.get("config") != pinned:
                    rep.add(run.path, f"its `config` differs from the yaml block under `## Pinned configuration` "
                                      f"in {proto.path}: a run uses exactly the pinned configuration")
        rep.guard(f"experiments/{slug}", per_experiment)


def evidence_sealed(lab: Lab, rep: Reporter) -> None:
    """Every finished run's out/ matches its manifest; a run with no end and no live process is orphaned."""
    for run in records.runs(lab):
        def one(run=run) -> None:
            state = run.state
            if state == "orphaned":
                rep.warn(run.path, "has no end and no live process: it is orphaned; close it honestly or "
                                   "start a fresh run with the same configuration")
                return
            if state == "running":
                return
            manifest_path = run.path.rsplit("/", 1)[0] + "/" + records.MANIFEST
            if not run.manifest.is_file():
                rep.add(manifest_path, "is missing for a run that ended")
                return
            recorded = records.parse_hashes(run.manifest.read_text(encoding="utf-8"), manifest_path)
            actual = records.tree_hashes(run.out, run.out)
            for name in sorted(set(recorded) | set(actual)):
                if name not in actual:
                    rep.add(manifest_path, f"lists out/{name}, which is gone")
                elif name not in recorded:
                    rep.add(manifest_path, f"does not list out/{name}, added after the run ended")
                elif recorded[name] != actual[name]:
                    rep.add(manifest_path, f"out/{name} changed after the run ended")
        rep.guard(run.path, one)
