"""The lab files lab-kit writes and reads: lock records, run records, manifests and scorecards."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .errors import LabError
from .lab import Lab

LOCK = "lock.json"
RUN = "run.json"
MANIFEST = "MANIFEST.sha256"
WORK_MANIFEST = "work.sha256"  # beside MANIFEST.sha256: the run's raw output under work/, which git ignores
SCORE = "score.yaml"
SPEND = "spend.json"  # written by a spending run's own command into out/
LOCK_KEYS = ("protocol", "path", "sha256", "locked")  # required; `instrument`, `commit`, `lab-kit` since 0.3.0
RUN_KEYS = ("protocol", "lock", "config", "mission", "spend", "command", "started", "ended", "exit", "pid",
            "spent", "commit", "lab-kit")
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
    return lab.experiments / slug / LOCK


def read_lock(lab: Lab, slug: str) -> LockRecord | None:
    path = lock_path(lab, slug)
    if not path.is_file():
        return None
    where = lab.rel(path)
    data = read_json(path, where)
    missing = [k for k in LOCK_KEYS if k not in data]
    if missing:
        raise LabError(f"{where}: missing {', '.join(missing)}")
    return LockRecord(slug, where, data)


# ---------------------------------------------------------------- runs


@dataclass
class RunRecord:
    slug: str
    run_id: str
    folder: Path
    data: dict[str, Any]

    @property
    def path(self) -> str:
        return f"experiments/{self.slug}/runs/{self.run_id}/{RUN}"

    @property
    def out(self) -> Path:
        return self.folder / "out"

    @property
    def manifest(self) -> Path:
        return self.folder / MANIFEST

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


def runs(lab: Lab, slug: str | None = None) -> list[RunRecord]:
    """Every run with a run.json, oldest first within each experiment."""
    out: list[RunRecord] = []
    for name in [slug] if slug else lab.experiment_slugs():
        folder = lab.experiments / name / "runs"
        if not folder.is_dir():
            continue
        for run_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
            path = run_dir / RUN
            if not path.is_file():
                continue
            out.append(RunRecord(name, run_dir.name, run_dir, read_json(path, lab.rel(path))))
    return out


def runs_without_record(lab: Lab) -> list[str]:
    """Run folders holding no run.json, from the lab root."""
    out = []
    for name in lab.experiment_slugs():
        folder = lab.experiments / name / "runs"
        if folder.is_dir():
            out.extend(lab.rel(p) for p in sorted(folder.iterdir()) if p.is_dir() and not (p / RUN).is_file())
    return out


# ---------------------------------------------------------------- manifests


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


def write_manifest(run: RunRecord) -> None:
    run.manifest.write_text(format_hashes(tree_hashes(run.out, run.out)), encoding="utf-8")


def write_work_manifest(run: RunRecord) -> None:
    """`work.sha256` beside the manifest, one line per file under `work/`, when that folder exists."""
    work = run.folder / "work"
    if work.is_dir():
        (run.folder / WORK_MANIFEST).write_text(format_hashes(tree_hashes(work, work)), encoding="utf-8")


# ---------------------------------------------------------------- scorecards


def score_path(lab: Lab, slug: str) -> Path:
    return lab.experiments / slug / SCORE
