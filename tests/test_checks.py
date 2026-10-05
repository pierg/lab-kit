"""One failing case for each lab check: the gate names the check that catches it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import commit

EXP = "experiments/pi-error-scaling"
RUN = f"{EXP}/runs/20261004-231629"
PROTOCOL = "docs/content/protocols/pi-error-scaling.md"
MISSION = "ops/missions/2026-10-04-pi-error-scaling.md"


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def edit_json(path: Path, **changes) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def problems(lab_kit, *only: str) -> tuple[int, list[dict]]:
    args = ["check", "--json"]
    for name in only:
        args += ["--only", name]
    code, out = lab_kit(*args)
    return code, json.loads(out)["problems"]


def named(found: list[dict], check: str, severity: str = "error") -> list[dict]:
    return [p for p in found if p["check"] == check and p["severity"] == severity]


def test_lock_recorded(make_lab, lab_kit) -> None:
    root = make_lab(lambda r: (r / EXP / "lock.json").unlink())
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-lock-recorded")


def test_lock_intact(make_lab, lab_kit) -> None:
    root = make_lab()
    edit(root / PROTOCOL, "100 estimates per arm", "200 estimates per arm")
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-lock-intact")
    # folio's own frozen check catches the same edit.
    assert named(found, "frozen")


def test_lock_intact_ignores_the_status(make_lab, lab_kit) -> None:
    root = make_lab()
    edit(root / PROTOCOL, "status: locked", "status: abandoned")
    code, found = problems(lab_kit, "lab-lock-intact", "lab-lock-recorded")
    assert code == 0, found


def test_run_after_lock(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit_json(r / RUN / "run.json", started="2026-10-03T00:00:00+00:00"))
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-run-after-lock")


def test_roster_frozen(make_lab, lab_kit) -> None:
    def change(root: Path) -> None:
        data = json.loads((root / RUN / "run.json").read_text(encoding="utf-8"))
        data["config"]["repeats"] = 10
        (root / RUN / "run.json").write_text(json.dumps(data), encoding="utf-8")
    make_lab(change)
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-roster-frozen")


def test_evidence_sealed(make_lab, lab_kit) -> None:
    root = make_lab()
    with (root / RUN / "out" / "estimates.tsv").open("a", encoding="utf-8") as handle:
        handle.write("64\t100\t64100\t3.0\n")
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-evidence-sealed")


def test_orphaned_run_is_a_warning(make_lab, lab_kit) -> None:
    def orphan(root: Path) -> None:
        folder = root / EXP / "runs" / "20261004-010000"
        (folder / "out").mkdir(parents=True)
        data = json.loads((root / RUN / "run.json").read_text(encoding="utf-8"))
        data.update(started="2026-10-04T01:00:00+00:00", ended=None, exit=None, pid=None)
        (folder / "run.json").write_text(json.dumps(data), encoding="utf-8")
    make_lab(orphan)
    code, found = problems(lab_kit, "lab-evidence-sealed")
    assert code == 0 and named(found, "lab-evidence-sealed", "warning")
    code, out = lab_kit("runs", "--live")
    assert "orphaned" in out


def test_rederive(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / "docs/content/results/R-2.md", 'number: "-0.493"', 'number: "-0.492"'))
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-rederive")
    assert "printed `-0.493`" in named(found, "lab-rederive")[0]["message"]
    assert lab_kit("rederive", "R-2")[0] == 1


def test_result_grounded(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / EXP / "score.yaml", "verdict: pass", "verdict: fail"))
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-result-grounded")


def test_score_exact(make_lab, lab_kit) -> None:
    def drop_p4(root: Path) -> None:
        text = (root / EXP / "score.yaml").read_text(encoding="utf-8")
        start = text.index("  P4:")
        end = text.index("  D1:")
        (root / EXP / "score.yaml").write_text(text[:start] + text[end:], encoding="utf-8")
    make_lab(drop_p4)
    code, found = problems(lab_kit)
    assert code == 1 and any("does not score P4" in p["message"] for p in named(found, "lab-score-exact"))


def test_ids_resolve(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / "ops/STATE.md", "its result is R-2", "its result is R-9"))
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-ids-resolve")


def test_frozen_intact(make_lab, lab_kit) -> None:
    root = make_lab()
    with (root / "substrate" / "estimator.py").open("a", encoding="utf-8") as handle:
        handle.write("# a reformat\n")
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-frozen-intact")


def test_selftest(make_lab, lab_kit) -> None:
    root = make_lab()
    (root / EXP / "bin" / "broken.py").write_text("raise SystemExit('no selftest here')\n", encoding="utf-8")
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-selftest")


def test_spend_recorded(make_lab, lab_kit) -> None:
    def spend(root: Path) -> None:
        edit_json(root / RUN / "run.json", spend=True, mission=MISSION, spent=5)
    make_lab(spend)
    code, found = problems(lab_kit)
    assert code == 1
    messages = [p["message"] for p in named(found, "lab-spend-recorded")]
    assert any("past its cap" in m for m in messages)


def test_mission_approved(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / MISSION, 'approved: "The operator, 2026-10-04: token-free only, no stage spends."\n',
                            ""))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "records no approval" in named(found, "lab-mission-approved")[0]["message"]


def test_mission_approved_names_who_and_when(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / MISSION, "The operator, 2026-10-04: token-free only", "Token-free only"))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "YYYY-MM-DD" in named(found, "lab-mission-approved")[0]["message"]


def test_mission_status_is_known(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / MISSION, "status: concluded", "status: done"))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "is not one of draft, active, concluded" in named(found, "lab-mission-approved")[0]["message"]


def test_nothing_runs_under_a_draft_mission(make_lab, lab_kit) -> None:
    draft = "ops/missions/2026-10-05-next.md"

    def plan(root: Path) -> None:
        (root / draft).write_text("---\ntitle: Next\nstatus: draft\nrests_on: [Q-1]\ncap: 0\n---\n\n"
                                  "## Log\n\n- 2026-10-05 Drafted.\n", encoding="utf-8")
    root = make_lab(plan)
    assert problems(lab_kit, "lab-mission-approved") == (0, [])
    edit_json(root / RUN / "run.json", mission=draft)
    edit(root / "ops/STATE.md", "Active mission: none", f"Active mission: {draft}")
    code, found = problems(lab_kit, "lab-mission-approved")
    messages = [p["message"] for p in named(found, "lab-mission-approved")]
    assert code == 1 and any("a draft mission" in m for m in messages)
    assert any("draft awaiting approval" in m for m in messages)


def test_append_only(make_lab, lab_kit) -> None:
    root = make_lab()
    edit(root / MISSION, "- 2026-10-04 Opened, for Q-1.", "- 2026-10-04 Opened.")
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-append-only")


def test_append_only_reads_history(make_lab, lab_kit) -> None:
    root = make_lab()
    edit_json(root / EXP / "lock.json", locked="2026-10-03T00:00:00+00:00")
    commit(root, "rewrite the lock record")
    code, found = problems(lab_kit, "lab-append-only")
    assert code == 1 and "after its first commit" in named(found, "lab-append-only")[0]["message"]


def test_append_only_allows_a_new_log_entry(make_lab, lab_kit) -> None:
    root = make_lab()
    with (root / MISSION).open("a", encoding="utf-8") as handle:
        handle.write("- 2026-10-05 A note after the end.\n")
    commit(root, "log")
    assert problems(lab_kit, "lab-append-only") == (0, [])


def test_method_current(make_lab, lab_kit) -> None:
    root = make_lab()
    with (root / ".lab/method/DISCIPLINE.md").open("a", encoding="utf-8") as handle:
        handle.write("\nA local rule.\n")
    code, found = problems(lab_kit)
    assert code == 1 and named(found, "lab-method-current")


def test_state_pointer(make_lab, lab_kit) -> None:
    make_lab(lambda r: edit(r / "ops/STATE.md", "Active mission: none", "Active mission: ops/missions/gone.md"))
    code, found = problems(lab_kit, "lab-state-pointer")
    assert code == 0 and named(found, "lab-state-pointer", "warning")


def test_state_pointer_numbers_cite_ids(make_lab, lab_kit) -> None:
    make_lab(lambda r: (r / "ops/STATE.md").write_text(
        "# State\n\nActive mission: none\n\nThe ratio was 0.66 at the second arm.\n", encoding="utf-8"))
    code, found = problems(lab_kit, "lab-state-pointer")
    assert code == 0 and "cites no id" in named(found, "lab-state-pointer", "warning")[0]["message"]


def test_scored_reported(make_lab, lab_kit) -> None:
    def other(root: Path) -> None:
        (root / "experiments/other").mkdir()
        (root / "experiments/other/score.yaml").write_text(
            "protocol: other\nlock: x\nreview: {verdict: '', record: ''}\nscores: {}\nrecord: {}\n", encoding="utf-8")
    make_lab(other)
    code, found = problems(lab_kit, "lab-scored-reported")
    assert code == 0 and named(found, "lab-scored-reported", "warning")


@pytest.mark.parametrize("name", [
    "lab-lock-recorded", "lab-lock-intact", "lab-run-after-lock", "lab-roster-frozen", "lab-evidence-sealed",
    "lab-rederive", "lab-result-grounded", "lab-score-exact", "lab-ids-resolve", "lab-frozen-intact",
    "lab-selftest", "lab-spend-recorded", "lab-append-only", "lab-method-current", "lab-state-pointer",
    "lab-scored-reported",
])
def test_every_check_is_registered(name) -> None:
    from lab_kit.checks.run import BY_NAME
    assert name in BY_NAME
