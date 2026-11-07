"""`lab-kit migrate`: move a lab from the layout before 0.6.0 to this one.

Before 0.6.0 a run lived in `experiments/<slug>/runs/<YYYYMMDD-HHMMSS>/`, its `out/` and manifests in git
and its raw `work/` and `run.log` on the run's machine or in the store; missions lived in
`ops/missions/<YYYY-MM-DD>-<slug>.md`. From 0.6.0:

- a mission is `missions/<YY-MM-DD>-m_<slug>.md`, its date the one its old name carried;
- an experiment is `experiments/<YY-MM-DD>-e_<slug>/`, its date the day of its lock (or of its first run,
  or of its first commit, for one never locked);
- a run is one folder, `runs/<experiment>/<YY-MM-DD-HHMM>-r_<4 characters>/`, its date its start and its
  four characters taken from its old path, so the same run always gets the same id. The folder holds
  everything the run had: `out/`, `work/` and `run.log` (fetched from the store, or from this machine),
  and a `run.json` with the old record, the new `experiment`, `id`, `mission` and `migrated`, sealed
  with every file's hash. `MANIFEST.sha256`, `work.sha256` and `store.json` are checked first, then left
  behind: the seal replaces them.

Every git-tracked text file outside the moved runs is rewritten: old paths and ids become new ones
(longest first, never inside a longer word), and the lock hashes are taken again where a protocol or an
experiment's `bin/` changed with them, with `migrated` in the lock record. `.lab/migration.tsv` keeps
every old name with its new one. The old copies in the store and on the machines stay where they are.

Without `--apply` it changes nothing and prints the plan. With it, it stops at the first problem before
any file in git moves: every run is assembled and verified first. Run it again after old runs land
from machines still on an older lab-kit: it moves only what is still in the old layout.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
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
STAGING = ".lab/migrating"
OLD_RUN_ID = re.compile(r"^\d{8}-\d{6}(?:-\d+)?$")
OLD_MISSION = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)$")
LEFT_BEHIND = ("MANIFEST.sha256", "work.sha256", "store.json")


@dataclass
class Run:
    slug: str            # the old experiment folder
    old_id: str
    folder: Path         # the old run folder in the checkout
    data: dict
    experiment: str = ""  # the new experiment id
    new_id: str = ""


@dataclass
class Plan:
    missions: dict[str, str] = field(default_factory=dict)     # old path -> new path
    experiments: dict[str, str] = field(default_factory=dict)  # old folder -> new id
    runs: list[Run] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


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
        stamp = run.old_id[:15]
        return _dt.datetime.strptime(stamp, "%Y%m%d-%H%M%S").replace(tzinfo=_dt.timezone.utc)


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


def plan(lab: Lab) -> Plan:
    out = Plan()
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
    for slug in lab.experiment_slugs():
        if EXPERIMENT_ID.match(slug):
            continue
        folder = lab.experiments / slug
        existing = lab.experiment_for(slug) if any(EXPERIMENT_ID.match(n) for n in lab.experiment_slugs()) else None
        if existing and existing != slug:
            out.experiments[slug] = existing  # old runs landed in an old folder after the move
            continue
        lock = records.read_lock(lab, slug)
        day = _day(lock.data.get("locked")) if lock else None
        if day is None:
            starts = []
            runs_dir = folder / "runs"
            for run_json in sorted(runs_dir.glob("*/run.json")) if runs_dir.is_dir() else []:
                started = _day(records.read_json(run_json, lab.rel(run_json)).get("started"))
                if started:
                    starts.append(started)
            day = min(starts) if starts else None
        day = day or _first_commit_day(lab, f"experiments/{slug}") or _dt.date.today()
        out.experiments[slug] = experiment_id(slug, day)
    for slug in lab.experiment_slugs():
        runs_dir = lab.experiments / slug / "runs"
        if not runs_dir.is_dir():
            continue
        new_exp = out.experiments.get(slug, slug)
        taken: set[str] = set()
        if lab.runs_here() and (lab.runs_dir / new_exp).is_dir():
            taken = {p.name for p in (lab.runs_dir / new_exp).iterdir()}
        for folder in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
            run_json = folder / records.RUN
            if not run_json.is_file():
                out.problems.append(f"{lab.rel(folder)} has no run.json")
                continue
            data = records.read_json(run_json, lab.rel(run_json))
            run = Run(slug, folder.name, folder, data, new_exp)
            if data.get("ended") is None:
                out.problems.append(f"{lab.rel(folder)} has not ended; migrate after it ends")
            salt, n = f"{slug}/{folder.name}", 1
            run.new_id = records.new_run_id(_moment(run), salt)
            while run.new_id in taken:
                n += 1
                run.new_id = records.new_run_id(_moment(run), f"{salt}#{n}")
            taken.add(run.new_id)
            out.runs.append(run)
    return out


# ---------------------------------------------------------------- assembling runs


def _verify_against(folder: Path, manifest: Path) -> list[str]:
    expected = records.parse_hashes(manifest.read_text(encoding="utf-8"), str(manifest))
    actual = records.tree_hashes(folder, folder)
    out = [f"missing {p}" for p in sorted(set(expected) - set(actual))]
    out += [f"extra {p}" for p in sorted(set(actual) - set(expected))]
    out += [f"changed {p}" for p in sorted(set(expected) & set(actual)) if expected[p] != actual[p]]
    return out


def assemble(lab: Lab, run: Run, missions: dict[str, str], locks: dict[str, tuple[str, str]],
             stage: Path) -> Path:
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
    work_manifest = run.folder / "work.sha256"
    host = run.data.get("host")
    if stored.is_file():
        record = records.read_json(stored, f"{where}/store.json")
        source = Path(str(record.get("store") or ""))
        host = host or record.get("by")
        if not source.is_dir():
            raise LabError(f"{where}: its raw output is recorded at {source}, which is not here; "
                           "migrate on a machine that mounts the store")
        for name in ("work", records.LOG):
            if (dest / name).exists():
                store_mod.remove(dest / name) if (dest / name).is_dir() else (dest / name).unlink()
            if (source / name).is_dir():
                shutil.copytree(source / name, dest / name, symlinks=False)
            elif (source / name).is_file():
                shutil.copy2(source / name, dest / name)
    store_mod.writable(dest)
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
    if data.get("lock") in locks.get(run.experiment, ("", ""))[:1]:
        data["lock"] = locks[run.experiment][1]
    data = {"experiment": run.experiment, "id": run.new_id, **{k: v for k, v in data.items()
                                                                 if k not in ("experiment", "id")}}
    data.setdefault("host", host)
    data["migrated"] = {"from": where, "on": records.now(), "by": f"lab-kit {__version__}"}
    records.write_json(dest / records.RUN, records.seal(dest, data))
    return dest


# ---------------------------------------------------------------- rewriting


def _text_files(lab: Lab) -> list[Path]:
    names = _git(lab, "ls-files", "-z").split("\0")
    out = []
    for name in names:
        if not name or name.startswith(".lab/method/") or name.startswith(f"{RUNS}/") or name == TABLE:
            continue
        path = lab.root / name
        if path.is_symlink() or not path.is_file():
            continue
        out.append(path)
    return out


def replacements(plan_: Plan, table: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    """Every old name with its new one, longest first."""
    pairs: dict[str, str] = {}
    rows = list(table)
    rows += [("mission", o, n) for o, n in plan_.missions.items()]
    rows += [("experiment", o, n) for o, n in plan_.experiments.items()]
    rows += [("run", f"{r.slug}/{r.old_id}", f"{r.experiment}/{r.new_id}") for r in plan_.runs]
    bare_runs: dict[str, set[str]] = {}
    for kind, old, new in rows:
        if kind == "mission":
            pairs[old] = new
            pairs[Path(old).stem] = Path(new).stem
        elif kind == "experiment":
            pairs[f"experiments/{old}/runs"] = f"{RUNS}/{new}"
            pairs[f"experiments/{old}"] = f"experiments/{new}"
        elif kind == "run":
            slug, old_id = old.split("/")
            exp, new_id = new.split("/")
            pairs[f"experiments/{slug}/runs/{old_id}"] = f"{RUNS}/{exp}/{new_id}"
            pairs[f"experiments/{exp}/runs/{old_id}"] = f"{RUNS}/{exp}/{new_id}"
            bare_runs.setdefault(old_id, set()).add(new_id)
    for old_id, news in bare_runs.items():
        if len(news) == 1:  # a bare old run id names one run only
            pairs[old_id] = next(iter(news))
    pairs[f"{ops.OLD_MISSIONS}/"] = f"{ops.MISSIONS}/"
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


def rewriter(pairs: list[tuple[str, str]]):
    if not pairs:
        return lambda text: (text, 0)
    lookup = dict(pairs)
    # Never inside a longer name; a run id is left alone where it names an archive file (`<id>.work.tar.zst`).
    pattern = re.compile(r"(?<![\w-])(" + "|".join(re.escape(o) for o, _ in pairs) + r")(?![\w-]|\.work\b|\.tar\b)")

    def apply(text: str) -> tuple[str, int]:
        return pattern.subn(lambda m: lookup[m.group(1)], text)
    return apply


# ---------------------------------------------------------------- the command


def migrate(lab: Lab, apply: bool = False) -> list[str]:
    if apply and _git(lab, "status", "--porcelain", "--untracked-files=no").strip():
        raise LabError("the checkout has uncommitted changes; commit or stash them, then migrate")
    plan_ = plan(lab)
    table = _old_table(lab)
    lines = [f"Missions to move: {len(plan_.missions)}",
             *[f"  {o} -> {n}" for o, n in sorted(plan_.missions.items())],
             f"Experiments to rename: {sum(1 for o, n in plan_.experiments.items() if o != n)}",
             *[f"  experiments/{o} -> experiments/{n}" for o, n in sorted(plan_.experiments.items())],
             f"Runs to move: {len(plan_.runs)}",
             *[f"  {lab.rel(r.folder)} -> {RUNS}/{r.experiment}/{r.new_id}" for r in plan_.runs[:20]]]
    if len(plan_.runs) > 20:
        lines.append(f"  ... and {len(plan_.runs) - 20} more")
    target = (store_mod.runs_root(lab) if lab.settings.store else lab.runs_dir)
    lines.append(f"Runs go to: {target}")
    if plan_.problems:
        lines += ["Problems (nothing moves until they are fixed):", *[f"  {p}" for p in plan_.problems]]
        if apply:
            raise LabError("\n".join(lines))
        return lines
    if not apply:
        rewrite = rewriter(replacements(plan_, table))
        touched = 0
        moved_runs = {r.folder for r in plan_.runs}
        for path in _text_files(lab):
            if any(path.is_relative_to(f) for f in moved_runs):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if rewrite(text)[1]:
                touched += 1
        return lines + [f"Files whose text would be rewritten: {touched}", "Dry run: nothing changed. "
                        "Run with --apply on a machine that mounts the store."]
    if lab.settings.store and not store_mod.mounted(Path(lab.settings.store)):
        raise LabError(f"the store {lab.settings.store} is not mounted here; migrate where it is")
    return lines + _apply(lab, plan_, table)


def _apply(lab: Lab, plan_: Plan, table: list[tuple[str, str, str]]) -> list[str]:
    out: list[str] = []
    stage = lab.root / STAGING
    store_mod.remove(stage)
    # 1. The new lock hashes are known only after the rewrite, but the runs must be assembled from the
    #    files as committed: assemble first, with the old lock hash, and fix `lock` in run.json after.
    assembled = [(run, assemble(lab, run, {**{o: n for k, o, n in table if k == "mission"}, **plan_.missions},
                                {}, stage)) for run in plan_.runs]
    out.append(f"assembled and verified {len(assembled)} runs under {STAGING}/")
    # 2. Move missions and experiments in git; drop the old run folders from git.
    for run in plan_.runs:
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
    for old, new in sorted(plan_.experiments.items()):
        if old == new:
            continue
        src = lab.experiments / old
        if (lab.experiments / new).exists():  # an old folder that only held runs landed after the move
            leftover = [p for p in src.rglob("*") if p.is_file() and p.name not in (".gitignore", ".gitkeep")]
            if leftover:
                raise LabError(f"experiments/{old}/ still holds {lab.rel(leftover[0])}; move it by hand")
            _git(lab, "rm", "-r", "-q", "--ignore-unmatch", "--", f"experiments/{old}")
            store_mod.remove(src)
            continue
        _git(lab, "mv", f"experiments/{old}", f"experiments/{new}")
        gitignore = lab.experiments / new / ".gitignore"
        if gitignore.is_file() and "runs/" in gitignore.read_text(encoding="utf-8"):
            _git(lab, "rm", "-q", "-f", "--", lab.rel(gitignore))
    old_missions = lab.root / ops.OLD_MISSIONS
    if old_missions.is_dir() and plan_.missions:
        if (old_missions / ".gitkeep").is_file():
            _git(lab, "rm", "-q", "-f", "--ignore-unmatch", "--", f"{ops.OLD_MISSIONS}/.gitkeep")
            (old_missions / ".gitkeep").unlink(missing_ok=True)
        if old_missions.is_dir() and not any(old_missions.iterdir()):
            old_missions.rmdir()
    out.append(f"moved {len(plan_.missions)} missions and "
               f"{sum(1 for o, n in plan_.experiments.items() if o != n)} experiments")
    # 3. Rewrite every text file in git.
    rewrite = rewriter(replacements(plan_, table))
    rewritten: list[Path] = []
    total = 0
    for path in _text_files(lab):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new, n = rewrite(text)
        if n:
            path.write_text(new, encoding="utf-8")
            rewritten.append(path)
            total += n
    out.append(f"rewrote {total} old names in {len(rewritten)} files")
    # 4. Take the lock hashes again where the protocol or bin/ changed with the rewrite.
    relocked: dict[str, tuple[str, str]] = {}
    for exp in lab.experiment_slugs():
        path = lab.experiments / exp / records.LOCK
        if not path.is_file():
            continue
        data = records.read_json(path, lab.rel(path))
        proto = protocol_mod.find(lab, str(data.get("protocol", "")))
        changed = False
        if proto is not None:
            sha = protocol_mod.hash_text(proto.text())
            if sha != data.get("sha256"):
                relocked[exp] = (str(data.get("sha256")), sha)
                data["sha256"] = sha
                changed = True
        if data.get("instrument"):
            inst = records.instrument_hash(lab.experiments / exp / "bin")
            if inst != data["instrument"]:
                data["instrument"] = inst
                changed = True
        if changed or exp in plan_.experiments.values():
            data.setdefault("migrated", {"on": records.now(), "by": f"lab-kit {__version__}",
                                         "why": "paths and ids renamed to the 0.6.0 layout"})
            records.write_json(path, data)
    for old_sha, new_sha in relocked.values():  # a scorecard names its lock's hash
        for score in lab.experiments.glob(f"*/{records.SCORE}"):
            text = score.read_text(encoding="utf-8")
            if old_sha in text:
                score.write_text(text.replace(old_sha, new_sha), encoding="utf-8")
    if relocked:
        out.append(f"took the lock hash again for {len(relocked)} experiments whose protocol text changed")
    # 5. Fix each run's `lock`, seal it, and move it into the store (or runs/).
    if lab.settings.store:
        store_mod.ensure_link(lab)
        dest_root = store_mod.runs_root(lab)
    else:
        dest_root = lab.runs_dir
    for run, folder in assembled:
        data = records.read_json(folder / records.RUN, str(folder))
        if run.experiment in relocked and data.get("lock") == relocked[run.experiment][0]:
            data["lock"] = relocked[run.experiment][1]
            records.write_json(folder / records.RUN, records.seal(folder, data))
        if lab.settings.store:
            store_mod.place(dest_root, run.experiment, run.new_id, folder, data)
        else:
            target = dest_root / run.experiment / run.new_id
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise LabError(f"{lab.rel(target)} exists already")
            shutil.copytree(folder, target)
    store_mod.remove(stage)
    out.append(f"moved {len(assembled)} runs to {dest_root}")
    # 6. The table of old and new names, the gitignore, the version and the shipped files.
    table_path = lab.root / TABLE
    rows = [] if table_path.is_file() else ["# kind\told\tnew\n"]
    rows += [f"mission\t{o}\t{n}\n" for o, n in sorted(plan_.missions.items())]
    rows += [f"experiment\t{o}\t{n}\n" for o, n in sorted(plan_.experiments.items()) if o != n]
    rows += [f"run\t{r.slug}/{r.old_id}\t{r.experiment}/{r.new_id}\n" for r in plan_.runs]
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
    rewrite as each one's first version (folio model §10), and name that file in folio.yaml."""
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


def dump(plan_: Plan) -> str:
    """The plan as JSON, for a test or a review."""
    return json.dumps({"missions": plan_.missions, "experiments": plan_.experiments,
                       "runs": {f"{r.slug}/{r.old_id}": f"{r.experiment}/{r.new_id}" for r in plan_.runs},
                       "problems": plan_.problems}, indent=2)
