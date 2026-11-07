"""A lab: its root, its settings in `lab.yaml`, and the folio library beside them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from folio import library as folio_library
from folio.errors import FolioError
from folio.library import Library

from .errors import LabError

LAB_YAML = "lab.yaml"
RUNS = "runs"                      # every run's folder: a link to <store>/runs, or a plain folder
RUNNING = ".lab/running"           # a run's folder while it runs, on local disk, when the lab has a store
FETCHED = ".lab/fetched"           # runs copied here from the store, on a machine that does not mount it
EXPERIMENT_ID = re.compile(r"^(\d{2}-\d{2}-\d{2})-e_([a-z0-9]+(?:-[a-z0-9]+)*)$")
_KEYS = ("lab-kit", "library", "front", "frozen", "rederive_timeout", "store")


@dataclass
class Settings:
    version: str
    library: str
    front: str | None
    frozen: list[str]
    rederive_timeout: int
    store: str | None = None


@dataclass
class Lab:
    root: Path
    settings: Settings
    cache: dict[str, Any] = field(default_factory=dict)

    @property
    def library_dir(self) -> Path:
        return (self.root / self.settings.library).resolve()

    def library(self) -> Library:
        """The folio library, loaded once. Its charter's `root` must be the lab root."""
        if "library" not in self.cache:
            try:
                lib = folio_library.load_at(self.library_dir)
            except FolioError as exc:
                raise LabError(f"the library in `{self.settings.library}` does not load: {exc}") from exc
            if lib.charter.root_dir != self.root:
                raise LabError(
                    f"{self.settings.library}/folio.yaml: `root` resolves to {lib.charter.root_dir}, not the lab "
                    f"root {self.root}; set it with `folio config set root {_relative_root(self)}` in the library")
            self.cache["library"] = lib
        return self.cache["library"]

    def reload(self) -> Library:
        self.cache.pop("library", None)
        return self.library()

    def rel(self, path: Path) -> str:
        """A path from the lab root, with forward slashes."""
        return path.resolve().relative_to(self.root).as_posix()

    def doc_path(self, doc_file_path: str) -> str:
        """A library file's path from the lab root."""
        if self.settings.library in (".", ""):
            return doc_file_path
        return f"{Path(self.settings.library).as_posix().rstrip('/')}/{doc_file_path}"

    @property
    def experiments(self) -> Path:
        return self.root / "experiments"

    def experiment_slugs(self) -> list[str]:
        """Every experiment folder's name: its id, `<YY-MM-DD>-e_<slug>` (a folder from before 0.6.0 is the bare slug)."""
        if not self.experiments.is_dir():
            return []
        return sorted(p.name for p in self.experiments.iterdir() if p.is_dir() and not p.name.startswith("."))

    def experiment_for(self, slug: str) -> str | None:
        """The id of the experiment whose protocol is `slug`, or None."""
        for name in self.experiment_slugs():
            if protocol_slug(name).casefold() == slug.casefold():
                return name
        return None

    @property
    def runs_dir(self) -> Path:
        return self.root / RUNS

    def runs_here(self) -> bool:
        """Whether `runs/` resolves to a folder here; a link to a store this machine does not mount does not."""
        return self.runs_dir.is_dir()

    def run_roots(self) -> list[Path]:
        """Where runs are read from: `runs/` when it resolves, runs still running here, and fetched copies."""
        roots = [self.runs_dir] if self.runs_here() else []
        return roots + [p for p in (self.root / RUNNING, self.root / FETCHED) if p.is_dir()]


def protocol_slug(experiment_id: str) -> str:
    """The protocol slug inside an experiment id: `portfolio-floor` in `26-11-04-e_portfolio-floor`."""
    match = EXPERIMENT_ID.match(experiment_id)
    return match.group(2) if match else experiment_id


def _relative_root(lab: Lab) -> str:
    depth = len(Path(lab.settings.library).parts)
    return "/".join([".."] * depth) or "."


def find_root(start: Path) -> Path:
    here = start.resolve()
    for folder in (here, *here.parents):
        if (folder / LAB_YAML).is_file():
            return folder
    raise LabError(f"no {LAB_YAML} at or above {here}; run `lab-kit init` in the lab's root first")


def parse_settings(raw: Any, where: str) -> Settings:
    if not isinstance(raw, dict):
        raise LabError(f"{where}: must be a mapping")
    if "tools" in raw:
        raise LabError(f"{where}: `tools` was removed in lab-kit 0.5.0, which no longer runs scripts' "
                       "--selftest; delete the key and test those scripts in the lab's own test suite")
    unknown = sorted(set(raw) - set(_KEYS))
    if unknown:
        raise LabError(f"{where}: unknown key(s) {', '.join(unknown)}; the keys are {', '.join(_KEYS)}")
    version = raw.get("lab-kit")
    if not isinstance(version, str) or not version:
        raise LabError(f"{where}: `lab-kit` must name the version this lab is checked with, as a string")
    library = raw.get("library")
    if not isinstance(library, str) or not library:
        raise LabError(f"{where}: `library` must name the folder holding folio.yaml (\".\" for the root)")
    front = raw.get("front")
    if front is not None and not isinstance(front, str):
        raise LabError(f"{where}: `front` must be a document id")
    lists = {}
    for key in ("frozen",):
        value = raw.get(key) or []
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise LabError(f"{where}: `{key}` must be a list of paths from the lab root")
        for v in value:
            if Path(v).is_absolute() or ".." in Path(v).parts:
                raise LabError(f"{where}: `{key}` path `{v}` must stay inside the lab")
        lists[key] = value
    timeout = raw.get("rederive_timeout", 120)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise LabError(f"{where}: `rederive_timeout` must be a positive whole number of seconds")
    store = raw.get("store")
    if store is not None and (not isinstance(store, str) or not Path(store).is_absolute()):
        raise LabError(f"{where}: `store` must be an absolute path, such as /labs/<lab>")
    return Settings(version, library, front or None, lists["frozen"], timeout, store or None)


def load_at(root: Path) -> Lab:
    root = root.resolve()
    path = root / LAB_YAML
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LabError(f"{LAB_YAML}: not valid YAML: {exc}") from exc
    lab = Lab(root, parse_settings(raw, LAB_YAML))
    if not (lab.library_dir / "folio.yaml").is_file():
        raise LabError(f"{LAB_YAML}: `library: {lab.settings.library}` holds no folio.yaml")
    return lab


def load(start: Path) -> Lab:
    return load_at(find_root(start))
