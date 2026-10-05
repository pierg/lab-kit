"""`lab-kit run`: in the background, and with spend recorded against a mission's cap."""

from __future__ import annotations

import json
import time
from pathlib import Path

from lab_kit import records
from lab_kit.lab import load

SPENDER = "import json, os; open(os.environ['LAB_OUT'] + '/spend.json', 'w').write(json.dumps({'spent': 3}))"


def _mission(root: Path, approved: str, cap: str, status: str = "active") -> str:
    rel = "ops/missions/2026-10-05-spend.md"
    (root / rel).write_text(f"---\ntitle: Spend\nstatus: {status}\nrests_on: [Q-1]\napproved: \"{approved}\"\n"
                            f"cap: {cap}\n---\n\n"
                            "## Log\n\n- 2026-10-05 Opened.\n", encoding="utf-8")
    return rel


def test_background_run_finishes_and_seals(make_lab, lab_kit) -> None:
    root = make_lab()
    code, out = lab_kit("run", "pi-error-scaling", "--", "python3", "experiments/pi-error-scaling/bin/sample.py")
    assert code == 0 and "running in the background" in out
    deadline = time.time() + 30
    while time.time() < deadline:
        newest = records.runs(load(root), "pi-error-scaling")[-1]
        if newest.state != "running":
            break
        time.sleep(0.2)
    assert newest.state == "finished", newest.data
    assert newest.manifest.is_file()
    assert lab_kit("check", "--only", "lab-evidence-sealed", "--only", "lab-run-after-lock",
                   "--only", "lab-roster-frozen")[0] == 0


def test_spend_needs_approval_and_stays_in_the_cap(make_lab, lab_kit) -> None:
    root = make_lab()
    unapproved = _mission(root, "", "10")
    code, out = lab_kit("run", "pi-error-scaling", "--spend", "--mission", unapproved, "--", "python3", "-c", SPENDER)
    assert code == 2 and "records no approval" in out
    nocap = _mission(root, "The operator, 2026-10-05, for one run.", "none")
    code, out = lab_kit("run", "pi-error-scaling", "--spend", "--mission", nocap, "--", "python3", "-c", SPENDER)
    assert code == 2 and "no numeric `cap:`" in out
    approved = _mission(root, "The operator, 2026-10-05, for one run.", "10")
    code, out = lab_kit("run", "pi-error-scaling", "--spend", "--wait", "--mission", approved, "--",
                        "python3", "-c", SPENDER)
    assert code == 0, out
    newest = records.runs(load(root), "pi-error-scaling")[-1]
    assert newest.data["spent"] == 3 and newest.data["mission"] == approved
    assert lab_kit("check", "--only", "lab-spend-recorded") == (0, "lab-kit check: 0 errors, 0 warnings\n")
    _mission(root, "The operator, 2026-10-05, for one run.", "2")
    code, out = lab_kit("check", "--only", "lab-spend-recorded")
    assert code == 1 and "past its cap of 2" in out


def test_failed_run_is_recorded_as_failed(make_lab, lab_kit) -> None:
    root = make_lab()
    code, out = lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", "raise SystemExit(3)")
    assert code == 1 and "exit code 3" in out
    newest = records.runs(load(root), "pi-error-scaling")[-1]
    assert newest.state == "failed" and json.loads((newest.folder / "run.json").read_text())["exit"] == 3


def test_run_refuses_a_draft_mission(make_lab, lab_kit) -> None:
    root = make_lab()
    draft = _mission(root, "", "0", status="draft")
    code, out = lab_kit("run", "pi-error-scaling", "--wait", "--mission", draft, "--", "python3", "-c", "pass")
    assert code == 2 and "is a draft" in out
    assert len(records.runs(load(root), "pi-error-scaling")) == 1
    concluded = "ops/missions/2026-10-04-pi-error-scaling.md"
    code, out = lab_kit("run", "pi-error-scaling", "--wait", "--mission", concluded, "--", "python3", "-c", "pass")
    assert code == 2 and "not `active`" in out
    active = _mission(root, "The operator, 2026-10-05, token-free.", "0")
    code, out = lab_kit("run", "pi-error-scaling", "--wait", "--mission", active, "--", "python3", "-c", "pass")
    assert code == 0, out
