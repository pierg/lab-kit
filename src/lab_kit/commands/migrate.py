"""`lab-kit migrate`: move a lab from the layout before 0.6.0 to this one.

Before 0.6.0 a run lived in `experiments/<slug>/runs/<YYYYMMDD-HHMMSS>/`, its `out/` and manifests in git
and its raw `work/` and `run.log` on the run's machine or in the store; missions lived in
`ops/missions/<YYYY-MM-DD>-<slug>.md`. From 0.6.0:

- a mission is `missions/<YY-MM-DD>-m_<slug>.md`, its date the one its old name carried;
- an experiment is `experiments/<YY-MM-DD>-e_<slug>/`, its date the day of its lock (or of its first run,
  or of its first commit, for one never locked);
- a run is one folder, `runs/<experiment>/<YY-MM-DD-HHMM>-r_<4 characters>/`, its date its start and its
  four characters taken from its old path, so the same run always gets the same id. The folder holds
  everything the run had: `out/`, `work/` and `run.log` (from the store, or from this machine), and a
  `run.json` with the old record, the new `experiment`, `id`, `mission` and `migrated`, sealed with every
  file's hash. `MANIFEST.sha256`, `work.sha256` and `store.json` are checked first, then left behind.

It works in two phases, so a failure never loses data:

1. **Runs.** Before anything in git changes, every run is assembled (in the store's `.incoming/` when
   the lab has a store, so nothing large lands on local disk), verified against its old manifests,
   sealed, and moved into place. A run already in place from an earlier attempt (its `migrated.from`
   names the same old folder and it verifies) is kept and reused.
2. **Git.** Old run folders leave the checkout, missions and experiments move, every git-tracked text
   file is rewritten (old paths and ids to new ones, longest first, never inside a longer name), the
   lock hashes are taken again where the rewrite changed a protocol or `bin/`, the rewritten documents
   go in the library's `baseline.sha256` (folio's `baseline`), and `.lab/migration.tsv` records every old
   name. If this phase fails, `git reset --hard` and run it again: the runs already in place are reused.

It refuses to start unless the gate's lifecycle checks (folio's `permanent` and `frozen`, and
`lab-lock-intact`) pass first, so a rewrite never hides an earlier edit. Without `--apply` it changes
nothing and prints the plan. Run it again after old runs land from machines on an older lab-kit.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .. import __version__, ops, records
from .. import protocol as protocol_mod
from .. import store as store_mod
from ..errors import LabError
from ..lab import EXPERIMENT_ID, RUNS, Lab
from .experiments import experiment_id
from .setup import ignore_runs, install

TABLE = ".lab/migration.tsv"
BASELINE = "baseline.sha256"  # in the library, beside folio.yaml
STAGING = ".lab/migrating"    # for a lab without a store; with one, `<store>/.incoming/migrate-<host>/`
OLD_MISSION = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)$")
LEFT_BEHIND = ("MANIFEST.sha256", "work.sha256", "store.json")
GATE_FIRST = ("permanent", "frozen", "lab-lock-intact")


@dataclass
class Run:
    slug: str            # the old experiment folder
    old_id: str
    folder: Path         # the old run folder in the checkout
    data: dict
    experiment: str = ""  # the new experiment id
    new_id: str = ""
    placed: bool = False  # already in place from an earlier attempt


@dataclass
class Plan:
    missions: dict[str, str] = field(default_factory=dict)     # old path -> new path
    experiments: dict[str, str] = field(default_factory=dict)  # old folder -> new id
    runs: list[Run] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    orphaned: list[str] = field(default_factory=list)  # runs committed without an end, named by the operator


def _git(lab: Lab, *args: str, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", str(lab.root), *args], capture_output=True, text=True, check=False)
    if check and done.returncode:
        raise LabError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def _first_commit_day(lab: Lab, path: str) -> _dt.date | None:
    days = _git(lab, "log", "--format=%cs", "--", path, check=False).split()
    return _dt.date.fromisoformat(days[-1]) if days else None


def _day(value: object) -> _dt.date | None:
    try:
        return records.parse_moment(value, "").astimezone(_dt.timezone.utc).date()
    except LabError:
        return None


def _moment(run: Run) -> _dt.datetime:
    try:
        return records.parse_moment(run.data.get("started"), "")
    except LabError:
        return _dt.datetime.strptime(run.old_id[:15], "%Y%m%d-%H%M%S").replace(tzinfo=_dt.timezone.utc)


def _old_table(lab: Lab) -> list[tuple[str, str, str]]:
    path = lab.root / TABLE
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            kind, old, new = line.split("\t")[:3]
            rows.append((kind, old, new))
    return rows


def target_root(lab: Lab) -> Path:
    """Where the runs go: the store's runs/ when the lab has a store, else the lab's own runs/."""
    return store_mod.runs_root(lab) if lab.settings.store else lab.runs_dir


def stage_root(lab: Lab) -> Path:
    if lab.settings.store:
        return store_mod.root(lab) / ".incoming" / f"migrate-{socket.gethostname()}"
    return lab.root / STAGING


def _placed_from(folder: Path) -> str | None:
    """The old path a run folder in place was migrated from, if it was."""
    path = folder / records.RUN
    if not path.is_file():
        return None
    try:
        data = records.read_json(path, str(path))
    except LabError:
        return None
    moved = data.get("migrated")
    return moved.get("from") if isinstance(moved, dict) else None


def plan(lab: Lab, orphaned: list[str] | None = None) -> Plan:
    out = Plan()
    named_orphans = {o.strip("/") for o in orphaned or []}
    old_missions = lab.root / ops.OLD_MISSIONS
    for path in sorted(old_missions.glob("*.md")) if old_missions.is_dir() else []:
        match = OLD_MISSION.match(path.stem)
        if match:
            year, month, day, slug = match.groups()
            stamp = f"{year[2:]}-{month}-{day}"
        else:
            first = _first_commit_day(lab, lab.rel(path)) or _dt.date.today()
            stamp, slug = first.strftime("%y-%m-%d"), path.stem
        out.missions[f"{ops.OLD_MISSIONS}/{path.name}"] = f"{ops.MISSIONS}/{stamp}-m_{slug}.md"
    has_new = any(EXPERIMENT_ID.match(n) for n in lab.experiment_slugs())
    for slug in lab.experiment_slugs():
        if EXPERIMENT_ID.match(slug):
            continue
        existing = lab.experiment_for(slug) if has_new else None
        if existing and existing != slug:
            out.experiments[slug] = existing  # old runs landed in an old folder after the move
            continue
        lock = records.read_lock(lab, slug)
        day = _day(lock.data.get("locked")) if lock else None
        if day is None:
            runs_dir = lab.experiments / slug / "runs"
            starts = [d for d in (_day(records.read_json(p, lab.rel(p)).get("started"))
                                  for p in sorted(runs_dir.glob("*/run.json"))) if d] if runs_dir.is_dir() else []
            day = min(starts) if starts else None
        day = day or _first_commit_day(lab, f"experiments/{slug}") or _dt.date.today()
        out.experiments[slug] = experiment_id(slug, day)
    target = target_root(lab)
    for slug in lab.experiment_slugs():
        runs_dir = lab.experiments / slug / "runs"
        if not runs_dir.is_dir():
            continue
        new_exp = out.experiments.get(slug, slug)
        placed: dict[str, str] = {}  # old path -> id, for runs an earlier attempt put in place
        taken: set[str] = set()
        if (target / new_exp).is_dir():
            for folder in (target / new_exp).iterdir():
                taken.add(folder.name)
                source = _placed_from(folder)
                if source:
                    placed[source] = folder.name
        for folder in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
            rel = lab.rel(folder)
            run_json = folder / records.RUN
            if not run_json.is_file():
                out.problems.append(f"{rel} has no run.json")
                continue
            data = records.read_json(run_json, f"{rel}/{records.RUN}")
            run = Run(slug, folder.name, folder, data, new_exp)
            if data.get("ended") is None:
                if rel in named_orphans:
                    out.orphaned.append(rel)  # it moves as it is; the gate still calls it orphaned
                else:
                    out.problems.append(f"{rel} has no end: it may still be running on its host. Migrate after "
                                        f"it ends, or, if it is dead, name it with --orphaned {rel}")
            if rel in placed:
                run.new_id, run.placed = placed[rel], True
            else:
                salt, n = f"{slug}/{folder.name}", 1
                run.new_id = records.new_run_id(_moment(run), salt)
                while run.new_id in taken:
                    n += 1
                    run.new_id = records.new_run_id(_moment(run), f"{salt}#{n}")
                taken.add(run.new_id)
            out.runs.append(run)
    return out


# ---------------------------------------------------------------- rewriting


def _text_files(lab: Lab) -> list[Path]:
    names = _git(lab, "ls-files", "-z").split("\0")
    out = []
    for name in names:
        if not name or name.startswith(".lab/method/") or name.startswith(f"{RUNS}/") or name == TABLE:
            continue
        if re.match(r"^experiments/[^/]+/runs/", name):  # runs leave git as they are
            continue
        path = lab.root / name
        if path.is_symlink() or not path.is_file():
            continue
        out.append(path)
    return out


def replacements(plan_: Plan, table: list[tuple[str, str, str]]) -> tuple[dict[str, str], dict[str, str]]:
    """Old paths with their new ones, and bare old run ids with their new ones."""
    paths: dict[str, str] = {}
    bare: dict[str, set[str]] = {}
    rows = list(table)
    rows += [("mission", o, n) for o, n in plan_.missions.items()]
    rows += [("experiment", o, n) for o, n in plan_.experiments.items()]
    rows += [("run", f"{r.slug}/{r.old_id}", f"{r.experiment}/{r.new_id}") for r in plan_.runs]
    for kind, old, new in rows:
        if kind == "mission":
            paths[old] = new
            paths[old[:-3]] = new[:-3]  # the path without .md, as in an anchor or a prose mention
        elif kind == "experiment":
            paths[f"experiments/{old}/runs"] = f"{RUNS}/{new}"
            paths[f"experiments/{old}"] = f"experiments/{new}"
        elif kind == "run":
            slug, old_id = old.split("/")
            exp, new_id = new.split("/")
            for form in (f"experiments/{slug}/runs/{old_id}", f"experiments/{exp}/runs/{old_id}",
                         f"{RUNS}/{exp}/{old_id}"):
                paths[form] = f"{RUNS}/{exp}/{new_id}"
            bare.setdefault(old_id, set()).add(new_id)
    paths[f"{ops.OLD_MISSIONS}/"] = f"{ops.MISSIONS}/"
    return paths, {old: next(iter(new)) for old, new in bare.items() if len(new) == 1}


def rewriter(pairs: tuple[dict[str, str], dict[str, str]]):
    paths, bare = pairs

    def compile_(keys, tail):
        keys = sorted(keys, key=len, reverse=True)
        return re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in keys) + r")" + tail) if keys else None
    # A path never inside a longer name. A bare run id only where it stands alone as a word: never where it
    # names a file (`<id>.png`, `<id>.work.tar.zst`), which is not renamed.
    path_re = compile_(paths, r"(?![\w-]|\.\w)")
    bare_re = compile_(bare, r"(?=$|[\s/`)\]\"',;:]|\.(?:$|\s))")

    def apply(text: str) -> tuple[str, int]:
        total = 0
        if path_re is not None:
            text, n = path_re.subn(lambda m: paths[m.group(1)], text)
            total += n
        if bare_re is not None:
            text, n = bare_re.subn(lambda m: bare[m.group(1)], text)
            total += n
        return text, total
    return apply


def _read(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _instrument_after(folder: Path, rewrite, rewritable: set[Path]) -> str:
    """`records.instrument_hash` of `folder` as it will be once its git-tracked text files are rewritten."""
    digest = hashlib.sha256()
    if folder.is_dir():
        files = sorted((p.relative_to(folder).as_posix(), p) for p in folder.rglob("*")
                       if p.is_file() and "__pycache__" not in p.relative_to(folder).parts)
        for rel, path in files:
            digest.update(rel.encode("utf-8") + b"\n")
            text = _read(path) if path in rewritable else None
            digest.update(path.read_bytes() if text is None else rewrite(text)[0].encode("utf-8"))
    return digest.hexdigest()


# ---------------------------------------------------------------- phase 1: runs


def _verify_against(folder: Path, manifest: Path) -> list[str]:
    expected = records.parse_hashes(manifest.read_text(encoding="utf-8"), str(manifest))
    actual = records.tree_hashes(folder, folder)
    out = [f"missing {p}" for p in sorted(set(expected) - set(actual))]
    out += [f"extra {p}" for p in sorted(set(actual) - set(expected))]
    out += [f"changed {p}" for p in sorted(set(expected) & set(actual)) if expected[p] != actual[p]]
    return out


def assemble(lab: Lab, run: Run, missions: dict[str, str], locks: dict[str, tuple[str, str]],
             stage: Path) -> tuple[Path, dict]:
    """Build the run's new folder under `stage`, verified against its old manifests, and seal it."""
    where = lab.rel(run.folder)
    dest = stage / run.experiment / run.new_id
    store_mod.remove(dest)
    dest.mkdir(parents=True)
    for item in sorted(run.folder.iterdir()):
        if item.name in LEFT_BEHIND or item.name == records.RUN:
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name, symlinks=False)
        else:
            shutil.copy2(item, dest / item.name)
    manifest = run.folder / "MANIFEST.sha256"
    if manifest.is_file():
        wrong = _verify_against(dest / "out", manifest)
        if wrong:
            raise LabError(f"{where}/out/ does not match its MANIFEST.sha256 ({'; '.join(wrong[:3])})")
    stored = run.folder / "store.json"
    host = run.data.get("host")
    if stored.is_file():
        record = records.read_json(stored, f"{where}/store.json")
        source = Path(str(record.get("store") or ""))
        host = host or record.get("by")
        if not source.is_dir():
            raise LabError(f"{where}: its raw output is recorded at {source}, which is not here; "
                           "migrate on a machine that mounts the store")
        for name in ("work", records.LOG):
            if not (source / name).exists():
                continue  # keep what is here when the store has none
            if (dest / name).is_dir():
                store_mod.remove(dest / name)
            elif (dest / name).exists():
                (dest / name).unlink()
            if (source / name).is_dir():
                shutil.copytree(source / name, dest / name, symlinks=False)
            else:
                shutil.copy2(source / name, dest / name)
    store_mod.writable(dest)
    work_manifest = run.folder / "work.sha256"
    if work_manifest.is_file():
        if not (dest / "work").is_dir():
            raise LabError(f"{where}: work.sha256 lists its raw output, but work/ is neither here nor in the store")
        wrong = _verify_against(dest / "work", work_manifest)
        if wrong:
            raise LabError(f"{where}/work/ does not match its work.sha256 ({'; '.join(wrong[:3])})")
    data = dict(run.data)
    mission = data.get("mission")
    if isinstance(mission, str) and mission in missions:
        data["mission"] = missions[mission]
    old_new = locks.get(run.experiment)
    if old_new and data.get("lock") == old_new[0]:
        data["lock"] = old_new[1]
    data = {"experiment": run.experiment, "id": run.new_id, **{k: v for k, v in data.items()
                                                                 if k not in ("experiment", "id")}}
    data.setdefault("host", host)
    data["migrated"] = {"from": where, "by": f"lab-kit {__version__}"}
    records.write_json(dest / records.RUN, records.seal(dest, data))
    return dest, data


def _put_in_place(lab: Lab, run: Run, built: Path, data: dict) -> None:
    """Move an assembled run into place, verified, read-only; the staged copy then goes."""
    target = target_root(lab) / run.experiment / run.new_id
    if target.exists():
        raise LabError(f"{target} exists and was not migrated from {lab.rel(run.folder)}; nothing is overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(built, target)  # the stage is on the same filesystem: one step
    except OSError:
        store_mod.place(target_root(lab), run.experiment, run.new_id, built, data)
        store_mod.remove(built)
        return
    wrong = records.seal_problems(target, data)
    if wrong:
        raise LabError(f"{target} does not match its seal after the move ({'; '.join(wrong[:3])})")
    store_mod._read_only(target)


# ---------------------------------------------------------------- the command


def preflight(lab: Lab, plan_: Plan) -> list[str]:
    """What would make the git phase fail, found before anything changes."""
    out: list[str] = []
    if lab.settings.store:
        if not store_mod.mounted(Path(lab.settings.store)):
            out.append(f"the store {lab.settings.store} is not mounted here; migrate where it is")
        link = lab.runs_dir
        if link.is_symlink():
            if Path(os.readlink(link)) != store_mod.runs_root(lab):
                out.append(f"runs/ links to {os.readlink(link)}, not {store_mod.runs_root(lab)}")
        elif link.exists():
            out.append("runs/ is a folder here, but the lab has a store: move it aside first")
    for old, new in plan_.missions.items():
        if (lab.root / new).exists():
            out.append(f"{new} exists already; {old} cannot move there")
    for old, new in plan_.experiments.items():
        if old != new and (lab.experiments / new).exists():
            leftover = [p for p in (lab.experiments / old).rglob("*") if p.is_file()
                        and p.name not in (".gitignore", ".gitkeep") and "runs" not in p.relative_to(
                            lab.experiments / old).parts]
            if leftover:
                out.append(f"experiments/{old}/ holds {lab.rel(leftover[0])}, but experiments/{new}/ exists; "
                           "move it by hand")
    for slug in plan_.experiments:
        try:
            lock = records.read_lock(lab, slug)
            if lock is not None and protocol_mod.find(lab, lock.protocol) is None:
                out.append(f"experiments/{slug}/lock.json names protocol `{lock.protocol}`, not in the library")
        except LabError as exc:
            out.append(str(exc))
    return out


def gate_first(lab: Lab) -> list[str]:
    """The lifecycle checks that must pass before a rewrite, so it never hides an earlier edit."""
    from ..checks import run as checks_run
    found = checks_run.run(lab, ["folio", "lab-lock-intact"])
    return [p.line() for p in found if p.severity == "error" and p.check in GATE_FIRST]


def migrate(lab: Lab, apply: bool = False, orphaned: list[str] | None = None) -> list[str]:
    if apply and _git(lab, "status", "--porcelain", "--untracked-files=no").strip():
        raise LabError("the checkout has uncommitted changes; commit or stash them, then migrate")
    plan_ = plan(lab, orphaned)
    table = _old_table(lab)
    lines = [f"Missions to move: {len(plan_.missions)}",
             *[f"  {o} -> {n}" for o, n in sorted(plan_.missions.items())],
             f"Experiments to rename: {sum(1 for o, n in plan_.experiments.items() if o != n)}",
             *[f"  experiments/{o} -> experiments/{n}" for o, n in sorted(plan_.experiments.items()) if o != n],
             f"Runs to move: {len(plan_.runs)}"
             + (f" ({sum(r.placed for r in plan_.runs)} already in place)" if any(r.placed for r in plan_.runs) else ""),
             *[f"  {lab.rel(r.folder)} -> {RUNS}/{r.experiment}/{r.new_id}" for r in plan_.runs[:20]]]
    if len(plan_.runs) > 20:
        lines.append(f"  ... and {len(plan_.runs) - 20} more")
    lines.append(f"Runs go to: {target_root(lab)}")
    if plan_.orphaned:
        lines += ["Runs with no end, named as dead, moved as they are:", *[f"  {p}" for p in plan_.orphaned]]
    if not (plan_.missions or plan_.runs or any(o != n for o, n in plan_.experiments.items())):
        return lines + ["Nothing to migrate."]
    problems = plan_.problems + preflight(lab, plan_)
    if apply and not problems:
        problems += [f"the gate fails before the rewrite: {p}" for p in gate_first(lab)]
    if problems:
        lines += ["Problems (nothing moves until they are fixed):", *[f"  {p}" for p in problems]]
        if apply:
            raise LabError("\n".join(lines))
        return lines
    rewrite = rewriter(replacements(plan_, table))
    if not apply:
        touched = sum(1 for path in _text_files(lab) if (text := _read(path)) is not None and rewrite(text)[1])
        return lines + [f"Files whose text would be rewritten: {touched}",
                        "Dry run: nothing changed. Run with --apply on a machine that mounts the store."]
    return lines + _apply(lab, plan_, table, rewrite)


def _new_locks(lab: Lab, plan_: Plan, rewrite) -> dict[str, tuple[str, str, str | None, str | None]]:
    """Per experiment (new id): (old sha256, new sha256, old instrument, new instrument) after the rewrite."""
    out = {}
    rewritable = set(_text_files(lab))
    for old, new in plan_.experiments.items():
        if old != new and (lab.experiments / new).is_dir():
            continue  # moved by an earlier pass: its lock is already in the new layout
        lock = records.read_lock(lab, old)
        if lock is None:
            continue
        proto = protocol_mod.find(lab, lock.protocol)
        sha = protocol_mod.hash_text(rewrite(proto.text())[0])  # as the gate reads it
        inst = _instrument_after(lab.experiments / old / "bin", rewrite, rewritable) if lock.instrument else None
        out[new] = (lock.sha256, sha, lock.instrument, inst)
    return out


def _earlier_locks(table: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    """Lock hashes an earlier pass took again, per experiment: a late run naming the old one gets the new."""
    out = {}
    for kind, exp, rest in table:
        if kind == "lock":
            old, _, new = rest.partition(">")
            out[exp] = (old, new)
    return out


def _apply(lab: Lab, plan_: Plan, table: list[tuple[str, str, str]], rewrite) -> list[str]:
    out: list[str] = []
    locks = _new_locks(lab, plan_, rewrite)
    missions = {**{o: n for k, o, n in table if k == "mission"}, **plan_.missions}
    run_locks = {**_earlier_locks(table), **{k: (v[0], v[1]) for k, v in locks.items()}}
    # Phase 1: every run assembled, verified, sealed and put in place before git changes at all.
    stage = stage_root(lab)
    stage.mkdir(parents=True, exist_ok=True)
    moved = 0
    for run in plan_.runs:
        if run.placed:
            target = target_root(lab) / run.experiment / run.new_id
            data = records.read_json(target / records.RUN, str(target))
            wrong = records.seal_problems(target, data)
            if wrong:
                raise LabError(f"{target}, placed by an earlier attempt, does not match its seal "
                               f"({'; '.join(wrong[:3])}); look at it before migrating again")
            continue
        try:
            built, data = assemble(lab, run, missions, run_locks, stage)
            _put_in_place(lab, run, built, data)
        except Exception as exc:
            raise LabError(f"{exc}\nNothing in git changed; the runs put in place so far are reused when you run "
                           "`lab-kit migrate --apply` again.") from exc
        moved += 1
    store_mod.remove(stage)
    out.append(f"put {moved} runs in place under {target_root(lab)}, each verified and sealed"
               + (f"; {len(plan_.runs) - moved} were in place already" if moved < len(plan_.runs) else ""))
    try:
        out += _git_phase(lab, plan_, table, rewrite, locks)
    except Exception as exc:
        raise LabError(f"{exc}\nThe runs are in place and safe. The checkout is part-way: run `git reset --hard` "
                       "and `lab-kit migrate --apply` again; it reuses the runs in place.") from exc
    return out


def _git_phase(lab: Lab, plan_: Plan, table, rewrite, locks) -> list[str]:
    out: list[str] = []
    for run in plan_.runs:  # every run is in place and verified: its old folder leaves the checkout
        _git(lab, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", lab.rel(run.folder))
        store_mod.remove(run.folder)
    for old in sorted({r.slug for r in plan_.runs}):
        runs_dir = lab.experiments / old / "runs"
        if runs_dir.is_dir():
            _git(lab, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", lab.rel(runs_dir))
            store_mod.remove(runs_dir)
    for old, new in sorted(plan_.missions.items()):
        (lab.root / new).parent.mkdir(parents=True, exist_ok=True)
        _git(lab, "mv", old, new)
    old_missions = lab.root / ops.OLD_MISSIONS
    if old_missions.is_dir() and plan_.missions:
        if (old_missions / ".gitkeep").is_file():
            _git(lab, "rm", "-q", "-f", "--ignore-unmatch", "--", f"{ops.OLD_MISSIONS}/.gitkeep")
            (old_missions / ".gitkeep").unlink(missing_ok=True)
        if old_missions.is_dir() and not any(old_missions.iterdir()):
            old_missions.rmdir()
    for old, new in sorted(plan_.experiments.items()):
        if old == new:
            continue
        src = lab.experiments / old
        if (lab.experiments / new).exists():  # an old folder that only held runs landed after the move
            _git(lab, "rm", "-r", "-q", "-f", "--ignore-unmatch", "--", f"experiments/{old}")
            store_mod.remove(src)
            continue
        _git(lab, "mv", f"experiments/{old}", f"experiments/{new}")
        gitignore = lab.experiments / new / ".gitignore"
        if gitignore.is_file():  # its run rules have no folder left to apply to; any other rule stays
            kept = [line for line in gitignore.read_text(encoding="utf-8").splitlines(keepends=True)
                    if "runs/" not in line and not line.startswith("# A run's scratch")]
            if any(line.strip() for line in kept):
                gitignore.write_text("".join(kept), encoding="utf-8")
            else:
                _git(lab, "rm", "-q", "-f", "--", lab.rel(gitignore))
    out.append(f"moved {len(plan_.missions)} missions and "
               f"{sum(1 for o, n in plan_.experiments.items() if o != n)} experiments")
    rewritten: list[Path] = []
    total = 0
    for path in _text_files(lab):
        text = _read(path)
        if text is None:
            continue
        new, n = rewrite(text)
        if n:
            path.write_bytes(new.encode("utf-8"))  # bytes in, bytes out: line endings stay as they were
            rewritten.append(path)
            total += n
    out.append(f"rewrote {total} old names in {len(rewritten)} files")
    relocked = 0
    for exp, (old_sha, new_sha, old_inst, new_inst) in locks.items():
        path = lab.experiments / exp / records.LOCK
        data = records.read_json(path, lab.rel(path))
        proto = protocol_mod.find(lab, str(data.get("protocol", "")))
        if protocol_mod.hash_text(proto.text()) != new_sha:
            raise LabError(f"{proto.path} does not hash as planned after the rewrite")
        if new_inst is not None and records.instrument_hash(lab.experiments / exp / "bin") != new_inst:
            raise LabError(f"experiments/{exp}/bin/ does not hash as planned after the rewrite")
        changed = new_sha != old_sha or new_inst != old_inst
        data["sha256"] = new_sha
        if new_inst is not None:
            data["instrument"] = new_inst
        data.setdefault("migrated", {"by": f"lab-kit {__version__}", "why": "paths and ids renamed to the "
                                     "0.6.0 layout" + (", so the hash was taken again" if changed else "")})
        records.write_json(path, data)
        if new_sha != old_sha:
            relocked += 1
            score = lab.experiments / exp / records.SCORE
            if score.is_file() and old_sha in (text := score.read_text(encoding="utf-8")):
                score.write_text(text.replace(old_sha, new_sha), encoding="utf-8")
    if relocked:
        out.append(f"took the lock hash again for {relocked} experiments whose protocol text changed")
    if lab.settings.store:
        out.extend(store_mod.ensure_link(lab))
    table_path = lab.root / TABLE
    day = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    rows = [] if table_path.is_file() else ["# kind\told\tnew\tmigrated on\n"]
    rows += [f"mission\t{o}\t{n}\t{day}\n" for o, n in sorted(plan_.missions.items())]
    rows += [f"experiment\t{o}\t{n}\t{day}\n" for o, n in sorted(plan_.experiments.items()) if o != n]
    rows += [f"run\t{r.slug}/{r.old_id}\t{r.experiment}/{r.new_id}\t{day}\n" for r in plan_.runs]
    rows += [f"lock\t{exp}\t{old}>{new}\t{day}\n" for exp, (old, new, _, _) in sorted(locks.items()) if old != new]
    table_path.parent.mkdir(parents=True, exist_ok=True)
    with table_path.open("a", encoding="utf-8") as handle:
        handle.writelines(rows)
    out.append(f"recorded every old name and its new one in {TABLE}")
    out.extend(ignore_runs(lab.root))
    lab_yaml = lab.root / "lab.yaml"
    text = lab_yaml.read_text(encoding="utf-8")
    lab_yaml.write_text(re.sub(r"(?m)^lab-kit:\s*\S+", f"lab-kit: {__version__}", text, count=1), encoding="utf-8")
    out.extend(install(lab.root))
    out.extend(write_baseline(lab, rewritten))
    out += ["Next: run the lab's own index (`folio index`) and gate, then commit everything in one commit."]
    return out


def write_baseline(lab: Lab, rewritten: list[Path]) -> list[str]:
    """List every rewritten document in the library's baseline file, so folio's lifecycle checks take the
    rewrite as each one's reference (folio model §10), and name that file in folio.yaml. Lines are only added."""
    library = lab.library_dir
    content = library / "content"
    mine = sorted(p for p in rewritten if p.is_relative_to(content))
    if not mine:
        return []
    path = library / BASELINE
    current: dict[str, str] = {}
    text = path.read_text(encoding="utf-8") if path.is_file() else (
        f"# Documents rewritten by lab-kit migrate on the record (paths and ids renamed to the {__version__}\n"
        "# layout). folio's permanent and frozen checks read each from this text on. Lines are only added.\n")
    for line in text.splitlines():
        digest, sep, rel = line.partition("  ")
        if sep and not line.startswith("#"):
            current[rel] = digest
    added = ""
    for doc in mine:
        rel = doc.relative_to(library).as_posix()
        digest = records.sha256_file(doc)
        if current.get(rel) != digest:
            added += f"{digest}  {rel}\n"
    path.write_text(text + ("" if text.endswith("\n") else "\n") + added, encoding="utf-8")
    out = [f"listed {len(mine)} rewritten documents in {lab.rel(path)}"]
    charter = library / "folio.yaml"
    text = charter.read_text(encoding="utf-8")
    if not re.search(r"(?m)^baseline:", text):
        charter.write_text(text + ("" if text.endswith("\n") else "\n") + f"baseline: {BASELINE}\n", encoding="utf-8")
        out.append(f"set `baseline: {BASELINE}` in {lab.rel(charter)}")
    return out
