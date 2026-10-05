"""A lab: its root, its settings in `lab.yaml`, and the folio library beside them."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from folio import library as folio_library
from folio.errors import FolioError
from folio.library import Library

from .errors import LabError

LAB_YAML = "lab.yaml"
_KEYS = ("lab-kit", "library", "front", "frozen", "tools", "rederive_timeout")


@dataclass
class Settings:
    version: str
    library: str
    front: str | None
    frozen: list[str]
    tools: list[str]
    rederive_timeout: int


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
        if not self.experiments.is_dir():
            return []
        return sorted(p.name for p in self.experiments.iterdir() if p.is_dir() and not p.name.startswith("."))


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
    for key in ("frozen", "tools"):
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
    return Settings(version, library, front or None, lists["frozen"], lists["tools"], timeout)


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
