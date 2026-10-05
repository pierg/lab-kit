"""What every lab check shares: its name, its default severity, and how it reports a problem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from folio.checks.problems import Problem

from ..errors import LabError
from ..lab import Lab


@dataclass
class Reporter:
    check: str
    severity: str  # the check's default: "error" or "warning"
    problems: list[Problem] = field(default_factory=list)

    def add(self, path: str, message: str, severity: str | None = None) -> None:
        self.problems.append(Problem(path, severity or self.severity, self.check, message))

    def warn(self, path: str, message: str) -> None:
        self.add(path, message, "warning")

    def guard(self, path: str, action: Callable[[], None]) -> None:
        """Run one item's part of a check; a file lab-kit cannot read becomes a problem on that file."""
        try:
            action()
        except LabError as exc:
            self.add(path, str(exc))


CheckFn = Callable[[Lab, Reporter], None]


@dataclass(frozen=True)
class LabCheck:
    name: str
    severity: str
    fn: CheckFn
