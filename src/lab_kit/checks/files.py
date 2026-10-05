"""Checks on the lab's own files: ids, frozen surfaces, selftests, spend, history, method and state."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from folio.checks.rules import measurements

from .. import __version__, data, frozen, gitlog, ops, records
from ..records import script_env
from ..errors import LabError
from ..lab import Lab
from .base import Reporter

STATE_WORDS = 300


def _id_pattern(lab: Lab) -> re.Pattern[str] | None:
    prefixes = sorted(lab.library().prefixes)
    if not prefixes:
        return None
    return re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(p) for p in prefixes) + r")-\d+\b")


def ids_resolve(lab: Lab, rep: Reporter) -> None:
    """Every id cited in a lab file resolves to a document in the library."""
    lib = lab.library()
    pattern = _id_pattern(lab)

    def resolve(where: str, ident: object, what: str) -> None:
        if not isinstance(ident, str) or not ident or not lib.find(ident):
            rep.add(where, f"{what} `{ident}` names no document in the library")

    def text_ids(where: str, text: str) -> None:
        if pattern is None:
            return
        for ident in sorted(set(pattern.findall(text))):
            resolve(where, ident, "cites")

    if lab.settings.front:
        resolve("lab.yaml", lab.settings.front, "`front`")
    state = lab.root / ops.STATE
    if state.is_file():
        text_ids(ops.STATE, state.read_text(encoding="utf-8"))
    for path in ops.mission_files(lab):
        where = lab.rel(path)

        def mission(path=path, where=where) -> None:
            m = ops.read_mission(lab, path)
            rests = m.meta.get("rests_on") or []
            for ident in rests if isinstance(rests, list) else [rests]:
                resolve(where, ident, "`rests_on`")
            text_ids(where, m.text)
        rep.guard(where, mission)
    for slug in lab.experiment_slugs():
        lock_where = f"experiments/{slug}/{records.LOCK}"

        def lock(slug=slug, where=lock_where) -> None:
            record = records.read_lock(lab, slug)
            if record is not None:
                resolve(where, record.protocol, "`protocol`")
        rep.guard(lock_where, lock)
        for run in records.runs(lab, slug):
            resolve(run.path, run.data.get("protocol"), "`protocol`")
        score_path = records.score_path(lab, slug)
        if score_path.is_file():
            where = lab.rel(score_path)

            def score(score_path=score_path, where=where) -> None:
                card = records.read_yaml(score_path, where)
                resolve(where, card.get("protocol"), "`protocol`")
                for name, entry in (card.get("record") or {}).items():
                    if isinstance(entry, dict):
                        if "protocol" in entry:
                            resolve(where, entry["protocol"], f"`record.{name}.protocol`")
                        if entry.get("supersedes"):
                            resolve(where, entry["supersedes"], f"`record.{name}.supersedes`")
                text_ids(where, score_path.read_text(encoding="utf-8"))
            rep.guard(where, score)


def frozen_intact(lab: Lab, rep: Reporter) -> None:
    """Every frozen surface matches its hashes in .lab/frozen.sha256."""
    try:
        recorded = frozen.recorded(lab)
    except LabError as exc:
        rep.add(frozen.FROZEN, str(exc))
        return
    surfaces = [s.rstrip("/") for s in lab.settings.frozen]
    for path in sorted(recorded):
        if not any(frozen.belongs(path, s) for s in surfaces):
            rep.add(frozen.FROZEN, f"records {path}, which no surface under `frozen:` in lab.yaml covers")
    for surface in surfaces:
        mine = {p: d for p, d in recorded.items() if frozen.belongs(p, surface)}
        if not mine:
            rep.add("lab.yaml", f"frozen surface `{surface}` has no recorded hash; the operator runs "
                                f"`lab-kit freeze {surface}`")
            continue
        target = lab.root / surface
        actual = records.tree_hashes(target, lab.root) if target.exists() else {}
        for path in sorted(set(mine) | set(actual)):
            if path not in actual:
                rep.add(path, f"is gone from frozen surface `{surface}`")
            elif path not in mine:
                rep.add(path, f"was added to frozen surface `{surface}` after it was frozen")
            elif mine[path] != actual[path]:
                rep.add(path, f"changed: frozen surface `{surface}` is never edited in place")


def _command(path: Path) -> list[str] | None:
    if path.suffix == ".py":
        return [sys.executable, str(path)]
    if path.suffix == ".sh":
        return ["bash", str(path)]
    if path.stat().st_mode & 0o111:
        return [str(path)]
    return None


def scripts(lab: Lab) -> list[Path]:
    found: list[Path] = []
    for slug in lab.experiment_slugs():
        folder = lab.experiments / slug / "bin"
        if folder.is_dir():
            found.extend(p for p in sorted(folder.iterdir())
                         if p.is_file() and not p.name.startswith(".") and p.suffix not in (".pyc", ".md"))
    found.extend(lab.root / t for t in lab.settings.tools)
    return found


def selftest(lab: Lab, rep: Reporter) -> None:
    """Every script in experiments/*/bin/ and under `tools:` passes --selftest."""
    for path in scripts(lab):
        where = lab.rel(path) if path.exists() else path.relative_to(lab.root).as_posix()
        if not path.is_file():
            rep.add("lab.yaml", f"tool `{where}` does not exist")
            continue
        command = _command(path)
        if command is None:
            rep.add(where, "is neither a .py or .sh script nor executable, so it cannot run --selftest")
            continue
        try:
            done = subprocess.run([*command, "--selftest"], cwd=lab.root, capture_output=True, text=True,
                                  timeout=lab.settings.rederive_timeout, check=False, env=script_env())
        except subprocess.TimeoutExpired:
            rep.add(where, f"--selftest ran past {lab.settings.rederive_timeout}s")
            continue
        if done.returncode != 0:
            tail = (done.stderr.strip() or done.stdout.strip()).splitlines()[-1:] or [""]
            rep.add(where, f"--selftest exited {done.returncode}: {tail[0]}".rstrip(": "))


def mission_approved(lab: Lab, rep: Reporter) -> None:
    """Missions are draft, active or concluded; an active or concluded one records who approved it and when;
    nothing runs under a draft, and the state never names a draft as active."""
    statuses: dict[str, str] = {}
    for path in ops.mission_files(lab):
        where = lab.rel(path)
        try:
            mission = ops.read_mission(lab, path)
        except LabError as exc:
            rep.add(where, str(exc))
            continue
        statuses[where] = mission.status
        if mission.status not in ops.STATUSES:
            rep.add(where, f"`status: {mission.status or '(none)'}` is not one of {', '.join(ops.STATUSES)}")
            continue
        if mission.status == "draft":
            continue
        if not mission.approved:
            rep.add(where, f"is {mission.status} but records no approval: `approved:` names who approved "
                           "the mission and when (the plan-mission skill records it)")
        elif not ops.approved_names_a_date(mission.approved):
            rep.add(where, f"`approved: {mission.approved}` must name who approved the mission and the date, "
                           "as YYYY-MM-DD")
    for run in records.runs(lab):
        named = run.data.get("mission")
        if isinstance(named, str) and statuses.get(named) == "draft":
            rep.add(run.path, f"runs under {named}, a draft mission: nothing runs before the operator approves it")
    state = lab.root / ops.STATE
    if state.is_file():
        active = ops.active_mission(state.read_text(encoding="utf-8"))
        if active and statuses.get(active) == "draft":
            rep.add(ops.STATE, f"names {active} as the active mission, but it is a draft awaiting approval")


def spend_recorded(lab: Lab, rep: Reporter) -> None:
    """A spending run names a mission with the operator's approval and a cap, and stays within the cap."""
    spent_by_mission: dict[str, float] = {}
    caps: dict[str, float] = {}
    for run in records.runs(lab):
        if run.data.get("spend") is not True:
            continue
        mission_path = run.data.get("mission")
        if not isinstance(mission_path, str) or not mission_path:
            rep.add(run.path, "spends but names no mission; a spending run needs one with the operator's approval")
            continue
        target = lab.root / mission_path
        if not target.is_file():
            rep.add(run.path, f"spends under mission {mission_path}, which does not exist")
            continue
        try:
            mission = ops.read_mission(lab, target)
        except LabError as exc:
            rep.add(mission_path, str(exc))
            continue
        if not mission.approved:
            rep.add(mission_path, f"records no operator approval (`approved:`), yet run {run.path} spends")
        if mission.cap is None:
            rep.add(mission_path, f"records no numeric `cap:`, yet run {run.path} spends")
            continue
        caps[mission_path] = mission.cap
        spent = run.data.get("spent")
        if run.ended:
            if not isinstance(spent, (int, float)) or isinstance(spent, bool):
                rep.add(run.path, "spent but recorded no spend: its command writes "
                                  f"out/{records.SPEND} with `spent`")
                continue
        if isinstance(spent, (int, float)) and not isinstance(spent, bool):
            spent_by_mission[mission_path] = spent_by_mission.get(mission_path, 0.0) + float(spent)
    for mission_path, total in sorted(spent_by_mission.items()):
        if total > caps[mission_path]:
            rep.add(mission_path, f"its runs spent {total:g}, past its cap of {caps[mission_path]:g}")


def _lab_files(lab: Lab) -> list[str]:
    """The append-only lab files: missions, lock records and run records, now or ever committed."""
    current = [lab.rel(p) for p in ops.mission_files(lab)]
    for slug in lab.experiment_slugs():
        if records.lock_path(lab, slug).is_file():
            current.append(f"experiments/{slug}/{records.LOCK}")
    current.extend(run.path for run in records.runs(lab))
    pattern = re.compile(r"^(ops/missions/[^/]+\.md|experiments/[^/]+/lock\.json|"
                         r"experiments/[^/]+/runs/[^/]+/run\.json)$")
    ever = [p for folder in ("ops/missions", "experiments") for p in gitlog.tracked(lab.root, folder)
            if pattern.match(p)]
    return sorted(set(current) | set(ever))


def append_only(lab: Lab, rep: Reporter) -> None:
    """Committed mission log entries, lock records and run records are unchanged in later commits."""
    if not gitlog.in_git(lab.root):
        rep.warn("lab.yaml", "the lab is not in a git repository, so lab-append-only could not be checked")
        return
    for path in _lab_files(lab):
        history = gitlog.versions(lab.root, path)
        committed = [(sha, text) for sha, text in history if sha != gitlog.WORKING]
        if not committed:
            continue
        first_sha, first = committed[0]
        if path.startswith("ops/missions/"):
            previous = ops.log_of(first or "")
            for sha, text in history[1:]:
                label = "the working tree" if sha == gitlog.WORKING else f"commit {sha[:7]}"
                if text is None:
                    rep.add(path, f"was deleted in {label}; a mission file is never deleted")
                    break
                log = ops.log_of(text)
                if previous is not None and (log is None or not log.startswith(previous.rstrip())):
                    rep.add(path, f"its log was changed in {label}: entries are only ever added at the bottom")
                    break
                previous = log
            continue
        for sha, text in history[1:]:
            label = "the working tree" if sha == gitlog.WORKING else f"commit {sha[:7]}"
            if text != first:
                what = "deleted" if text is None else "changed"
                rep.add(path, f"was {what} in {label} after its first commit {first_sha[:7]}; "
                              "lock and run records never change once committed")
                break


def method_current(lab: Lab, rep: Reporter) -> None:
    """The method, the five skills and the four roles match the lab-kit version in lab.yaml."""
    if lab.settings.version != __version__:
        rep.add("lab.yaml", f"`lab-kit: {lab.settings.version}`, but this is lab-kit {__version__}; "
                            "install that version, or run `lab-kit init` to move the lab to this one")
        return
    for src, dest in data.shipped_files():
        target = lab.root / dest
        if not target.is_file():
            rep.add(dest, f"is missing; lab-kit {__version__} ships it (`lab-kit init` restores it)")
        elif target.read_bytes() != src.read_bytes():
            rep.add(dest, f"differs from what lab-kit {__version__} ships; it is never hand-edited "
                          "(`lab-kit init` restores it)")


def state_pointer(lab: Lab, rep: Reporter) -> None:
    """ops/STATE.md names an active mission or none, stays short, and cites ids for its numbers."""
    path = lab.root / ops.STATE
    if not path.is_file():
        rep.add(ops.STATE, "does not exist; it says what is true now and points to the active mission")
        return
    text = path.read_text(encoding="utf-8")
    active = ops.active_mission(text)
    if active is None:
        rep.add(ops.STATE, "has no `Active mission:` line naming a mission file or `none`")
    elif active.lower() != "none" and not (lab.root / active).is_file():
        rep.add(ops.STATE, f"names active mission `{active}`, which does not exist")
    elif active.lower() != "none" and not active.startswith(ops.MISSIONS + "/"):
        rep.add(ops.STATE, f"names active mission `{active}`, which is not under {ops.MISSIONS}/")
    words = len(text.split())
    if words > STATE_WORDS:
        rep.add(ops.STATE, f"has {words} words, past {STATE_WORDS}: it is a pointer, never a record")
    pattern = _id_pattern(lab)
    for number, line in enumerate(text.splitlines(), 1):
        found = measurements(line)
        if found and (pattern is None or not pattern.search(line)):
            rep.add(ops.STATE, f"line {number}: `{found[0]}` cites no id; a number in the state cites its result")
