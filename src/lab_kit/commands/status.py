"""`lab-kit status`: the state, the active mission, the standing budgets, live and orphaned runs, and protocols
by status."""

from __future__ import annotations

from .. import ops, records
from ..budgets import uses as budget_uses
from ..lab import Lab


def budgets(lab: Lab) -> list[str]:
    """One line per standing budget: granted, committed and left, then the missions drawing on it."""
    found, _ = budget_uses(lab)
    lines: list[str] = []
    for name, use in sorted(found.items()):
        unit = f" {use.budget.meta['unit']}" if use.budget.meta.get("unit") else ""
        lines.append(f"  {name}: {use.budget.amount:g}{unit} granted, {use.committed:g} committed, "
                     f"{use.left:g} left")
        lines.extend(f"    {path}: {amount:g}" for path, amount in use.missions)
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
