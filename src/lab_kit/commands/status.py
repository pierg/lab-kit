"""`lab-kit status`: the state, the active mission, the standing budgets, live and orphaned runs, and protocols
by status."""

from __future__ import annotations

from .. import ops, records
from ..errors import LabError
from ..lab import Lab


def budgets(lab: Lab) -> list[str]:
    """One line per standing budget: what the operator granted and the missions drawing on it."""
    lines: list[str] = []
    missions = []
    for path in ops.mission_files(lab):
        try:
            missions.append(ops.read_mission(lab, path))
        except LabError:
            continue
    for path in ops.budget_files(lab):
        try:
            budget = ops.read_budget(lab, path)
        except LabError as exc:
            lines.append(f"  {lab.rel(path)}: {exc}")
            continue
        under = [m for m in missions if m.budget == budget.name and m.status != "draft"]
        named = ", ".join(f"{m.path} ({m.status}, cap {m.cap:g})" if m.cap is not None else m.path for m in under)
        lines.append(f"  {budget.name}: {budget.amount:g} granted; missions: {named or 'none'}")
    return ["Standing budgets:", *lines] if lines else ["Standing budgets: none"]


def status(lab: Lab) -> list[str]:
    lines: list[str] = []
    state = lab.root / ops.STATE
    if state.is_file():
        text = state.read_text(encoding="utf-8")
        lines.append(f"Active mission: {ops.active_mission(text) or 'not named in ' + ops.STATE}")
        lines.append(f"State ({ops.STATE}):")
        lines.extend("  " + line for line in text.strip().splitlines())
    else:
        lines.append(f"No {ops.STATE}.")
    lines.extend(budgets(lab))
    live = [r for r in records.runs(lab) if r.state in ("running", "orphaned")]
    lines.append("Live and orphaned runs:" if live else "Live and orphaned runs: none")
    lines.extend(f"  {r.slug}/{r.run_id}  {r.state}  started {r.data.get('started')}" for r in live)
    protocols = [d for d in lab.library().documents if d.is_a("protocol")]
    for wanted in ("draft", "locked"):
        found = sorted(d.id for d in protocols if d.status == wanted)
        lines.append(f"Protocols {wanted}: {', '.join(found) if found else 'none'}")
    return lines
