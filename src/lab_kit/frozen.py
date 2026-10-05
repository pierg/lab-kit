"""Frozen surfaces: the hashes `lab-kit freeze` records in `.lab/frozen.sha256`."""

from __future__ import annotations

from pathlib import Path

from . import records
from .errors import LabError
from .lab import Lab

FROZEN = ".lab/frozen.sha256"


def surface_hashes(lab: Lab, surface: str) -> dict[str, str]:
    """Every file of a surface (a file, or a folder and all it holds), by its path from the lab root."""
    target = lab.root / surface
    if not target.exists():
        raise LabError(f"frozen surface `{surface}` does not exist")
    return records.tree_hashes(target, lab.root)


def belongs(path: str, surface: str) -> bool:
    surface = surface.rstrip("/")
    return path == surface or path.startswith(surface + "/")


def recorded(lab: Lab) -> dict[str, str]:
    path = lab.root / FROZEN
    if not path.is_file():
        return {}
    return records.parse_hashes(path.read_text(encoding="utf-8"), FROZEN)


def freeze(lab: Lab, surface: str) -> list[str]:
    """Record a surface's hashes, replacing what was recorded for it before."""
    surface = Path(surface).as_posix().rstrip("/")
    listed = [s.rstrip("/") for s in lab.settings.frozen]
    if surface not in listed:
        raise LabError(f"`{surface}` is not listed under `frozen:` in lab.yaml; list it there first")
    hashes = surface_hashes(lab, surface)
    if not hashes:
        raise LabError(f"frozen surface `{surface}` holds no file")
    kept = {p: d for p, d in recorded(lab).items() if not belongs(p, surface)}
    kept.update(hashes)
    out = lab.root / FROZEN
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(records.format_hashes(kept), encoding="utf-8")
    return [f"updated {FROZEN}: recorded {len(hashes)} file(s) of {surface}"]
