"""The operator's files: `ops/STATE.md` and the missions under `ops/missions/`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from folio.errors import FolioError
from folio.frontmatter import split

from .errors import LabError
from .lab import Lab

STATE = "ops/STATE.md"
MISSIONS = "ops/missions"
LOG_HEADING = re.compile(r"^## Log[ \t]*$", re.M)
ACTIVE = re.compile(r"^\s*Active mission:\s*(.+?)\s*$", re.M | re.I)


@dataclass
class Mission:
    path: str  # from the lab root
    meta: dict[str, Any]
    text: str

    @property
    def cap(self) -> float | None:
        cap = self.meta.get("cap")
        if isinstance(cap, (int, float)) and not isinstance(cap, bool):
            return float(cap)
        return None

    @property
    def approved(self) -> str:
        return str(self.meta.get("approved") or "").strip()

    @property
    def status(self) -> str:
        return str(self.meta.get("status") or "").strip()

    def approval_problem(self) -> str | None:
        """Why this mission may not run, or None when it is approved and active."""
        if self.status == "draft":
            return (f"{self.path} is a draft: nothing runs under a mission until the operator approves it "
                    "(the plan-mission skill records `approved` and sets `status: active`)")
        if self.status != "active":
            return f"{self.path} has status `{self.status or '(none)'}`, not `active`: a run needs an active mission"
        if not approved_names_a_date(self.approved):
            return f"{self.path} records no approval with who and when (`approved:`); nothing runs before it"
        return None


STATUSES = ("draft", "active", "concluded")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def approved_names_a_date(approved: str) -> bool:
    """`approved` says who and when: some words, and a date as YYYY-MM-DD."""
    return bool(DATE.search(approved)) and bool(DATE.sub("", approved).strip(" ,;:.-"))


def mission_files(lab: Lab) -> list[Path]:
    folder = lab.root / MISSIONS
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def read_mission(lab: Lab, path: Path) -> Mission:
    where = lab.rel(path)
    text = path.read_text(encoding="utf-8")
    try:
        meta, _ = split(text, where)
    except FolioError as exc:
        raise LabError(str(exc)) from exc
    return Mission(where, meta or {}, text)


def log_of(text: str) -> str | None:
    """The mission log: everything after the `## Log` heading, or None without one."""
    match = LOG_HEADING.search(text)
    return text[match.end():] if match else None


def active_mission(text: str) -> str | None:
    """What `Active mission:` names in the state file: a path, `none`, or None when the line is missing."""
    match = ACTIVE.search(text)
    if match is None:
        return None
    value = match.group(1).strip().strip("`*")
    link = re.match(r"^\[[^\]]*\]\(([^)]+)\)$", value)
    if link:
        value = link.group(1)
    return value.strip("`")
