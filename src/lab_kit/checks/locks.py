"""Checks on locks and runs: the lock is recorded and intact, and every run follows it."""

from __future__ import annotations

from .. import protocol as protocol_mod
from .. import records
from ..errors import LabError
from ..lab import Lab, protocol_slug
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
                rep.add(where, f"is locked but no experiments/<YY-MM-DD>-e_{doc.id}/{records.LOCK} exists; "
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
    """A locked protocol, its status set aside, hashes to the value in its lock.json, and the experiment's
    `bin/` hashes to the lock's `instrument` when the lock records one."""
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
            if lock.instrument is not None:
                bin_hash = records.instrument_hash(lab.experiments / slug / "bin")
                if bin_hash != lock.instrument:
                    rep.add(f"experiments/{slug}/bin", f"bin/ changed since its lock: it hashes to {bin_hash[:12]}, "
                                                       f"and {path} records {lock.instrument[:12]}")
        rep.guard(path, one)


def run_after_lock(lab: Lab, rep: Reporter) -> None:
    """Every run belongs to a locked experiment, records the lock's hash, and started after the lock."""
    for where in records.runs_without_record(lab):
        rep.add(where, f"is a run folder with no {records.RUN}")
    by_experiment: dict[str, list[records.RunRecord]] = {}
    for run in records.runs(lab):
        by_experiment.setdefault(run.slug, []).append(run)
    for slug, found in sorted(by_experiment.items()):
        def per_experiment(slug=slug, found=found) -> None:
            if not (lab.experiments / slug).is_dir():
                for run in found:
                    rep.add(run.path, f"belongs to experiments/{slug}/, which does not exist")
                return
            lock = records.read_lock(lab, slug)
            for run in found:
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
        rep.guard(f"runs/{slug}", per_experiment)


def roster_frozen(lab: Lab, rep: Reporter) -> None:
    """Every run's configuration equals its locked protocol's pinned configuration."""
    pinned_by: dict[str, object] = {}
    for run in records.runs(lab):
        def one(run=run) -> None:
            if run.slug not in pinned_by:
                lock = records.read_lock(lab, run.slug)
                proto = protocol_mod.find(lab, lock.protocol if lock else protocol_slug(run.slug))
                pinned_by[run.slug] = ((proto, protocol_mod.as_recorded(protocol_mod.pinned_config(proto.text(), proto.path)))
                                      if proto else None)
            found = pinned_by[run.slug]
            if found is None:
                return
            proto, pinned = found
            if run.data.get("config") != pinned:
                rep.add(run.path, f"its `config` differs from the yaml block under `## Pinned configuration` "
                                  f"in {proto.path}: a run uses exactly the pinned configuration")
        rep.guard(run.path, one)


def evidence_sealed(lab: Lab, rep: Reporter) -> None:
    """Every ended run's folder matches the seal in its run.json; a run with no end and no live process is
    orphaned. Where runs/ does not resolve (the store is not mounted), the checks that read runs are skipped."""
    if not lab.runs_here():
        where = f"the store {lab.settings.store} is not mounted" if lab.settings.store else "there is no runs/ folder"
        rep.warn("runs", f"does not resolve here ({where}), so the checks that read runs, their evidence, "
                         "re-derive commands and spend were skipped; run the gate where runs/ resolves")
    for run in records.runs(lab):
        def one(run=run) -> None:
            state = run.state
            if state == "orphaned":
                rep.warn(run.path, "has no end and no live process: it is orphaned; close it honestly or "
                                   "start a fresh run with the same configuration")
                return
            if state == "running":
                return
            wrong = records.seal_problems(run.folder, run.data)
            if wrong:
                rep.add(run.path, "its folder does not match its seal: " + "; ".join(wrong[:5])
                        + (f" (and {len(wrong) - 5} more)" if len(wrong) > 5 else ""))
        rep.guard(run.path, one)


def run_stored(lab: Lab, rep: Reporter) -> None:
    """With a store in lab.yaml, no ended run is left on local disk (warning)."""
    if not lab.settings.store:
        return
    from ..store import pending
    for run in pending(lab):
        rep.warn(run.path, f"ended but is still on this machine, not in the store {lab.settings.store}; "
                           "`lab-kit publish --pending` moves it")
