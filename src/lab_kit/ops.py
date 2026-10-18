"""The operator's files: `ops/STATE.md`, the missions under `ops/missions/` and the standing budgets under
`ops/budgets/`."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from folio.errors import FolioError
from folio.frontmatter import split

from .errors import LabError
from .lab import Lab

STATE = "ops/STATE.md"
MISSIONS = "ops/missions"
BUDGETS = "ops/budgets"
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

    @property
    def budget(self) -> str:
        """The standing budget the mission draws on, by name, or "" when the operator approved it alone."""
        return str(self.meta.get("budget") or "").strip()

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


def finite(value: Any) -> float | None:
    """A real, finite number, or None: booleans, strings, NaN and infinities are not amounts."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


@dataclass
class Grant:
    amount: float | None
    approved: str


@dataclass
class Budget:
    """A standing budget: money the operator granted once for many missions, in grants that only grow."""

    path: str  # from the lab root
    name: str
    meta: dict[str, Any]

    @property
    def grants(self) -> list[Grant]:
        found = self.meta.get("grants")
        out: list[Grant] = []
        for grant in found if isinstance(found, list) else []:
            grant = grant if isinstance(grant, dict) else {}
            out.append(Grant(finite(grant.get("amount")), str(grant.get("approved") or "").strip()))
        return out

    @property
    def amount(self) -> float:
        return sum(g.amount for g in self.grants if g.amount is not None and g.amount > 0)

    def problems(self) -> list[str]:
        """What makes the file not a standing budget, empty when it is one."""
        found = self.meta.get("grants")
        if not isinstance(found, list) or not found:
            return ["has no `grants:`, the list of the operator's grants, each with `amount` and `approved`"]
        out = []
        for number, grant in enumerate(self.grants, 1):
            if grant.amount is None or grant.amount <= 0:
                out.append(f"grant {number} has no positive, finite numeric `amount`")
            if not approved_names_a_date(grant.approved):
                out.append(f"grant {number} must record `approved`: who granted it and the date, as YYYY-MM-DD")
        return out


def budget_files(lab: Lab) -> list[Path]:
    folder = lab.root / BUDGETS
    return sorted([*folder.glob("*.yaml"), *folder.glob("*.yml")]) if folder.is_dir() else []


def budget_clashes(lab: Lab) -> list[str]:
    """Budget names held by both a .yaml and a .yml file: one name, one file."""
    stems = [p.stem for p in budget_files(lab)]
    return sorted({s for s in stems if stems.count(s) > 1})


def read_budget(lab: Lab, path: Path) -> Budget:
    where = lab.rel(path)
    try:
        meta = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LabError(f"{where} is not valid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise LabError(f"{where} is not a mapping with `grants:`")
    return Budget(where, path.stem, meta)


def grants_of(text: str | None) -> tuple[list[Any], Any] | None:
    """The raw `grants` list and `unit` of a budget file's text, or None when it does not parse to them."""
    try:
        meta = yaml.safe_load(text or "")
    except yaml.YAMLError:
        return None
    found = meta.get("grants") if isinstance(meta, dict) else None
    return (found, meta.get("unit")) if isinstance(found, list) else None


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
