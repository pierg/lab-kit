"""The lab files lab-kit writes and reads: lock records, run records, manifests and scorecards."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .errors import LabError
from .lab import Lab

LOCK = "lock.json"
RUN = "run.json"                # written by lab-kit in every run's folder; the only fixed name with run.log
LOG = "run.log"                 # the command's output, written by lab-kit
SCORE = "score.yaml"
SPEND = "spend.json"  # written by a spending run's own command into its folder (or its out/, before 0.6.0)
LOCK_KEYS = ("protocol", "path", "sha256", "locked")  # required; `instrument`, `commit`, `lab-kit` since 0.3.0
RUN_KEYS = ("experiment", "id", "protocol", "lock", "config", "mission", "spend", "command", "host", "started",
            "ended", "exit", "pid", "spent", "commit", "lab-kit", "files", "seal")
PREDICTION_VERDICTS = ("HIT", "MISS", "INDETERMINATE")
RULE_VERDICTS = ("FIRED", "NOT FIRED", "INDETERMINATE")
REVIEW_VERDICTS = ("pass", "fail")


def now() -> str:
    """The current moment in UTC, to the second, as ISO 8601."""
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def script_env() -> dict[str, str]:
    """The environment lab-kit runs a lab's scripts in: the caller's, with no bytecode written.

    A `__pycache__` folder written into a frozen surface would change it.
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def provenance(root: Path) -> dict[str, Any]:
    """What a lock or a run record names about where it was taken: the git head and this lab-kit.

    `commit` is null outside git or before the first commit, so the record says there was none.
    """
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
                            capture_output=True, text=True, check=False)
    head = result.stdout.strip() if result.returncode == 0 else None
    return {"commit": head or None, "lab-kit": __version__}


def instrument_hash(folder: Path) -> str:
    """One sha256 over the instrument: every file under `folder` (an experiment's `bin/`), sorted by its
    path from `folder`, each fed as its path, a newline, then its bytes. A `__pycache__` folder is not
    the instrument and is left out."""
    digest = hashlib.sha256()
    if folder.is_dir():
        files = sorted((p.relative_to(folder).as_posix(), p) for p in folder.rglob("*")
                       if p.is_file() and "__pycache__" not in p.relative_to(folder).parts)
        for rel, path in files:
            digest.update(rel.encode("utf-8") + b"\n")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_moment(value: Any, where: str) -> _dt.datetime:
    if not isinstance(value, str):
        raise LabError(f"{where}: expected an ISO 8601 time, not {value!r}")
    try:
        moment = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LabError(f"{where}: `{value}` is not an ISO 8601 time") from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_dt.timezone.utc)
    return moment


def read_json(path: Path, where: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LabError(f"{where}: not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LabError(f"{where}: must be a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_yaml(path: Path, where: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LabError(f"{where}: not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise LabError(f"{where}: must be a mapping")
    return data


# ---------------------------------------------------------------- locks


@dataclass
class LockRecord:
    slug: str  # the experiment folder's name
    path: str  # lock.json from the lab root
    data: dict[str, Any]

    @property
    def protocol(self) -> str:
        return str(self.data.get("protocol", ""))

    @property
    def sha256(self) -> str:
        return str(self.data.get("sha256", ""))

    @property
    def instrument(self) -> str | None:
        """The hash of `bin/` at the lock; None for a lock taken before lab-kit 0.3.0."""
        value = self.data.get("instrument")
        return value if isinstance(value, str) else None

    @property
    def locked(self) -> _dt.datetime:
        return parse_moment(self.data.get("locked"), self.path)


def lock_path(lab: Lab, slug: str) -> Path:
    """An experiment's lock.json, by its id or its protocol's slug."""
    return lab.experiments / (_experiment(lab, slug)) / LOCK


def _experiment(lab: Lab, ref: str) -> str:
    if (lab.experiments / ref).is_dir():
        return ref
    return lab.experiment_for(ref) or ref


def read_lock(lab: Lab, slug: str) -> LockRecord | None:
    path = lock_path(lab, slug)
    if not path.is_file():
        return None
    where = lab.rel(path)
    data = read_json(path, where)
    missing = [k for k in LOCK_KEYS if k not in data]
    if missing:
        raise LabError(f"{where}: missing {', '.join(missing)}")
    return LockRecord(path.parent.name, where, data)


# ---------------------------------------------------------------- runs


@dataclass
class RunRecord:
    slug: str  # the experiment's id: the folder it sits under
    run_id: str
    folder: Path
    data: dict[str, Any]
    where: str = ""  # the folder from the lab root, as lab-kit names it

    @property
    def path(self) -> str:
        base = self.where or f"runs/{self.slug}/{self.run_id}"
        return f"{base}/{RUN}"

    @property
    def base(self) -> str:
        return self.path.rsplit("/", 1)[0]

    @property
    def ended(self) -> bool:
        return self.data.get("ended") is not None

    @property
    def state(self) -> str:
        """running, finished, failed or orphaned."""
        if self.ended:
            return "finished" if self.data.get("exit") == 0 else "failed"
        return "running" if _alive(self.data.get("pid")) else "orphaned"


def _alive(pid: Any) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OverflowError:
        return False
    cmdline = Path(f"/proc/{pid}/cmdline")  # where it exists, tell a reused pid from the supervisor
    if cmdline.is_file():
        try:
            return b"lab_kit.supervise" in cmdline.read_bytes()
        except OSError:
            return True
    return True


RUN_ID = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-r_[a-z0-9]{4}$")
_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def new_run_id(moment: _dt.datetime, salt: str | None = None) -> str:
    """`<YY-MM-DD-HHMM>-r_<4 characters>`: the start in UTC, and four random letters or digits, or four
    taken from `salt` (a migration names an old run by its old path, so the id is the same every time)."""
    if salt is None:
        tail = "".join(secrets.choice(_ALPHABET) for _ in range(4))
    else:
        digest = int(hashlib.sha256(salt.encode("utf-8")).hexdigest(), 16)
        tail = ""
        for _ in range(4):
            digest, k = divmod(digest, len(_ALPHABET))
            tail += _ALPHABET[k]
    return moment.astimezone(_dt.timezone.utc).strftime("%y-%m-%d-%H%M") + "-r_" + tail


def runs(lab: Lab, slug: str | None = None) -> list[RunRecord]:
    """Every run with a run.json, oldest first within each experiment, from every place runs are read."""
    seen: dict[tuple[str, str], RunRecord] = {}
    if slug and not (lab.experiments / slug).is_dir():
        slug = lab.experiment_for(slug) or slug  # a protocol's slug names its experiment
    for root in lab.run_roots():
        experiments = [root / slug] if slug else (sorted(p for p in root.iterdir() if p.is_dir()
                                                       and not p.name.startswith(".")) if root.is_dir() else [])
        for exp in experiments:
            if not exp.is_dir():
                continue
            for run_dir in sorted(p for p in exp.iterdir() if p.is_dir() and not p.name.startswith(".")):
                path = run_dir / RUN
                if not path.is_file() or (exp.name, run_dir.name) in seen:
                    continue
                where = _where(lab, root, exp.name, run_dir.name)
                seen[(exp.name, run_dir.name)] = RunRecord(exp.name, run_dir.name, run_dir,
                                                           read_json(path, f"{where}/{RUN}"), where)
    return sorted(seen.values(), key=lambda r: (r.slug, r.run_id))


def _where(lab: Lab, root: Path, slug: str, run_id: str) -> str:
    if root == lab.runs_dir:
        return f"runs/{slug}/{run_id}"
    return f"{root.relative_to(lab.root).as_posix()}/{slug}/{run_id}"


def find_run(lab: Lab, ref: str) -> RunRecord:
    """A run named `<experiment>/<run id>`, or by its run id alone."""
    ref = ref.strip("/")
    if ref.startswith("runs/"):
        ref = ref[len("runs/"):]
    slug, sep, run_id = ref.partition("/")
    for run in runs(lab, slug if sep else None):
        if (run.run_id == run_id) if sep else (run.run_id == slug):
            return run
    raise LabError(f"no run `{ref}` here: name it as <experiment>/<run id>" +
                   ("" if lab.runs_here() else "; runs/ does not resolve on this machine (`lab-kit fetch` copies one)"))


def runs_without_record(lab: Lab) -> list[str]:
    """Run folders holding no run.json, from the lab root."""
    out = []
    for root in lab.run_roots():
        for exp in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
            out.extend(f"{_where(lab, root, exp.name, p.name)}" for p in sorted(exp.iterdir())
                       if p.is_dir() and not p.name.startswith(".") and not (p / RUN).is_file())
    return out


# ---------------------------------------------------------------- the seal


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hashes(folder: Path, base: Path) -> dict[str, str]:
    """Every file under `folder`, by its path from `base`, with its sha256."""
    if folder.is_file():
        return {folder.relative_to(base).as_posix(): sha256_file(folder)}
    if not folder.is_dir():
        return {}
    return {p.relative_to(base).as_posix(): sha256_file(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def format_hashes(hashes: dict[str, str]) -> str:
    return "".join(f"{digest}  {path}\n" for path, digest in sorted(hashes.items()))


def parse_hashes(text: str, where: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        digest, sep, path = line.partition("  ")
        if not sep or len(digest) != 64 or not path:
            raise LabError(f"{where}:{number}: expected `<sha256>  <path>`")
        out[path] = digest
    return out


def run_files(folder: Path) -> dict[str, str]:
    """Every file in a run's folder but run.json, by its path from the folder, with its sha256."""
    return {p: d for p, d in tree_hashes(folder, folder).items() if p != RUN}


def seal_of(data: dict[str, Any]) -> str:
    """One sha256 over the run record, its `files` included and its `seal` left out: what `seal` records."""
    body = {k: v for k, v in data.items() if k != "seal"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def seal(folder: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Record in `data` every file of the run with its hash, then one hash over the whole record."""
    data["files"] = run_files(folder)
    data["seal"] = seal_of(data)
    return data


def seal_problems(folder: Path, data: dict[str, Any]) -> list[str]:
    """What differs between a run's folder and the files its run.json records: nothing when it holds."""
    recorded = data.get("files")
    if not isinstance(recorded, dict):
        return ["run.json records no `files`: the run was never sealed"]
    if data.get("seal") != seal_of(data):
        return ["run.json changed after the run was sealed"]
    actual = run_files(folder)
    out = [f"missing {p}" for p in sorted(set(recorded) - set(actual))]
    out += [f"extra {p}" for p in sorted(set(actual) - set(recorded))]
    out += [f"changed {p}" for p in sorted(set(recorded) & set(actual)) if recorded[p] != actual[p]]
    return out


# ---------------------------------------------------------------- scorecards


def score_path(lab: Lab, slug: str) -> Path:
    return lab.experiments / _experiment(lab, slug) / SCORE
