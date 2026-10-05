"""`lab-kit status`: the state, the active mission, live and orphaned runs, and protocols by status."""

from __future__ import annotations

from .. import ops, records
from ..lab import Lab


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
    live = [r for r in records.runs(lab) if r.state in ("running", "orphaned")]
    lines.append("Live and orphaned runs:" if live else "Live and orphaned runs: none")
    lines.extend(f"  {r.slug}/{r.run_id}  {r.state}  started {r.data.get('started')}" for r in live)
    protocols = [d for d in lab.library().documents if d.is_a("protocol")]
    for wanted in ("draft", "locked"):
        found = sorted(d.id for d in protocols if d.status == wanted)
        lines.append(f"Protocols {wanted}: {', '.join(found) if found else 'none'}")
    return lines
