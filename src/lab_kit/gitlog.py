"""Read the history of a lab file from git: each committed version, oldest first, then the working tree."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import LabError

WORKING = "working tree"


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise LabError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def in_git(root: Path) -> bool:
    if shutil.which("git") is None:
        return False
    return _git(root, "rev-parse", "--is-inside-work-tree", check=False).stdout.strip() == "true"


def _has_head(root: Path) -> bool:
    return _git(root, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0


def tracked(root: Path, folder: str) -> list[str]:
    """Every path under `folder` that any commit touched, from `root`, including deleted ones."""
    if not _has_head(root):
        return []
    out = _git(root, "log", "--format=", "--name-only", "--relative", "--", folder).stdout
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def versions(root: Path, path: str) -> list[tuple[str, str | None]]:
    """(commit, text) for every commit that touched `path`, oldest first, then the working tree if it differs.

    The text is None where the file did not exist.
    """
    out: list[tuple[str, str | None]] = []
    if _has_head(root):
        shas = _git(root, "log", "--format=%H", "--", path).stdout.split()
        for sha in reversed(shas):
            shown = _git(root, "show", f"{sha}:./{path}", check=False)
            out.append((sha, shown.stdout if shown.returncode == 0 else None))
    target = root / path
    now = target.read_text(encoding="utf-8") if target.is_file() else None
    if not out or out[-1][1] != now:
        if out or now is not None:
            out.append((WORKING, now))
    return out
