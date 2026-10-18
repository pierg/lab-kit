"""What the missions under each standing budget commit, shared by the gate and `lab-kit status`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from . import ops, records
from .errors import LabError
from .lab import Lab


@dataclass
class Use:
    budget: ops.Budget
    missions: list[tuple[str, float]] = field(default_factory=list)  # (mission path, amount committed)

    @property
    def committed(self) -> float:
        return sum(amount for _, amount in self.missions)

    @property
    def left(self) -> float:
        return self.budget.amount - self.committed


def _mission_path(value: object) -> str | None:
    return PurePosixPath(value).as_posix() if isinstance(value, str) and value else None


def spent_by_mission(lab: Lab, problems: list[tuple[str, str]]) -> dict[str, float]:
    """What the spending runs recorded, per mission; a spend that is not a finite number >= 0 is a problem."""
    spent: dict[str, float] = {}
    for run in records.runs(lab):
        mission = _mission_path(run.data.get("mission"))
        if run.data.get("spend") is not True or mission is None or run.data.get("spent") is None:
            continue  # not spending, or still running (lab-spend-recorded names an ended run with no spend)
        amount = ops.finite(run.data.get("spent"))
        if amount is None or amount < 0:
            problems.append((run.path, f"records spend `{run.data.get('spent')}`, not a finite number >= 0"))
            continue
        spent[mission] = spent.get(mission, 0.0) + amount
    return spent


def uses(lab: Lab, missions: list[ops.Mission] | None = None) -> tuple[dict[str, Use], list[tuple[str, str]]]:
    """Each budget with what its missions commit: an active mission its cap, or what it spent when that is
    more; a concluded one what it spent; a draft nothing. Also every problem found on the way."""
    problems: list[tuple[str, str]] = []
    found: dict[str, Use] = {}
    broken: set[str] = set()
    for name in ops.budget_clashes(lab):
        problems.append((f"{ops.BUDGETS}/{name}.yml", f"budget `{name}` has both a .yaml and a .yml file; keep one"))
        broken.add(name)
    for path in ops.budget_files(lab):
        if path.stem in broken:
            continue
        try:
            budget = ops.read_budget(lab, path)
        except LabError as exc:
            problems.append((lab.rel(path), str(exc)))
            broken.add(path.stem)
            continue
        problems.extend((budget.path, problem) for problem in budget.problems())
        found[budget.name] = Use(budget)
    if missions is None:
        missions = []
        for path in ops.mission_files(lab):
            try:
                missions.append(ops.read_mission(lab, path))
            except LabError:
                continue
    spent = spent_by_mission(lab, problems)
    for mission in missions:
        if not mission.budget:
            continue
        if mission.budget in broken:
            problems.append((mission.path, f"draws on budget `{mission.budget}`, which is not a valid budget"))
            continue
        if mission.budget not in found:
            problems.append((mission.path, f"draws on budget `{mission.budget}`, but "
                                           f"{ops.BUDGETS}/{mission.budget}.yaml does not exist"))
            continue
        if mission.status == "draft":
            continue
        cap = ops.finite(mission.meta.get("cap"))
        if cap is None or cap < 0:
            problems.append((mission.path, f"draws on budget `{mission.budget}` but records no `cap:` that is "
                                           "a finite number >= 0"))
            continue
        used = spent.get(mission.path, 0.0)
        amount = used if mission.status == "concluded" else max(cap, used)
        found[mission.budget].missions.append((mission.path, amount))
    return found, problems
