"""`lab-kit init`: lab.yaml, ops/, experiments/, .lab/, the skills and the agent roles, and the lab pack on.

Before a folio library exists, `lab-kit init` installs only the method, the skills and the roles,
so the set-up-lab skill is there to read: it creates the library and runs `lab-kit init --library` again.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from folio import library as folio_library
from folio.commands.charter_cmds import pack_on
from folio.errors import FolioError

from .. import __version__, data
from ..errors import LabError
from ..frozen import FROZEN
from ..lab import LAB_YAML
from ..ops import MISSIONS, STATE

_LAB_YAML = """\
lab-kit: {version}               # the version this lab is checked with
library: {library}                # where folio.yaml is; "." for the root
front:                       # the front door's id: a project document
frozen: []                   # surfaces never edited in place; record each with `lab-kit freeze`
tools: []                    # lab-wide scripts; each must pass --selftest
rederive_timeout: 120        # seconds per re-derive command
"""

_STATE = """\
# State

Active mission: none

Next: the operator's first objective, planned through the plan-mission skill.
"""


def _link(root: Path, link: str, wanted: str) -> list[str]:
    path = root / link
    if path.is_symlink():
        if os.readlink(path) != wanted:
            raise LabError(f"{link} links to {os.readlink(path)}, not {wanted}; move it aside first")
        return []
    if path.exists():
        raise LabError(f"{link} exists and is not a link to {wanted}; move it aside first")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(wanted)
    return [f"linked {link} -> {wanted}"]


def install(root: Path) -> list[str]:
    """Copy the method, the skills and the roles into the lab, as this version ships them."""
    changed: list[str] = []
    for src, dest in data.shipped_files():
        target = root / dest
        if target.is_file() and target.read_bytes() == src.read_bytes():
            continue
        existed = target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        changed.append(f"{'updated' if existed else 'created'} {dest}")
    changed.extend(_link(root, ".claude/skills", os.path.join("..", ".agents", "skills")))
    changed.extend(_link(root, ".claude/agents", os.path.join("..", ".agents", "agents")))
    return changed


def _write_new(root: Path, rel: str, text: str) -> list[str]:
    path = root / rel
    if path.exists():
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return [f"created {rel}"]


SKILLS_ONLY = ("No folio library here yet: installed lab-kit's method, skills and roles only. "
               "Next: read .agents/skills/set-up-lab/SKILL.md and follow it.")


def init(root: Path, library: str | None) -> list[str]:
    root = root.resolve()
    existing = root / LAB_YAML
    changed: list[str] = []
    if library is None and not existing.is_file() and not (root / "folio.yaml").is_file():
        return install(root) + [SKILLS_ONLY]
    library = library or "."
    if existing.is_file():
        text = existing.read_text(encoding="utf-8")
        updated = re.sub(r"(?m)^lab-kit:\s*\S+", f"lab-kit: {__version__}", text, count=1)
        if updated != text:
            existing.write_text(updated, encoding="utf-8")
            changed.append(f"updated {LAB_YAML}: lab-kit {__version__}")
        library = _library_of(updated)
    lib_dir = (root / library).resolve()
    if not (lib_dir / "folio.yaml").is_file():
        raise LabError(f"`{library}` holds no folio.yaml; set the library up with folio first")
    try:
        lib = folio_library.load_at(lib_dir)
    except FolioError as exc:
        raise LabError(f"the library in `{library}` does not load: {exc}") from exc
    if lib.charter.root_dir != root:
        depth = len(lib_dir.relative_to(root).parts)
        raise LabError(f"{library}/folio.yaml: `root` resolves to {lib.charter.root_dir}, not the lab root; "
                       f"run `folio config set root {'/'.join(['..'] * depth) or '.'}` in the library first")
    if not existing.is_file():
        changed.extend(_write_new(root, LAB_YAML, _LAB_YAML.format(version=__version__, library=library)))
    changed.extend(_write_new(root, STATE, _STATE))
    changed.extend(_write_new(root, f"{MISSIONS}/.gitkeep", ""))
    changed.extend(_write_new(root, "experiments/.gitkeep", ""))
    changed.extend(_write_new(root, FROZEN, ""))
    changed.extend(install(root))
    if "lab" not in lib.charter.pack_names:
        lines = pack_on(lib, "lab").splitlines()
        changed.extend(f"{line} (in {library})" if library not in (".", "") else line for line in lines)
    return changed


def _library_of(text: str) -> str:
    match = re.search(r"(?m)^library:\s*(\S+)", text)
    if match is None:
        raise LabError(f"{LAB_YAML} names no `library`")
    return match.group(1)
