"""Standing budgets: missions under one fit inside what the operator granted, and grants only grow."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import commit
from test_checks import RUN, edit, edit_json, named, problems

BUDGET = "ops/budgets/credits.yaml"
GRANT = "  - amount: 200\n    approved: \"The operator, 2026-10-04: the standing budget for live runs\"\n"


def budget(root: Path, grants: str = GRANT) -> None:
    (root / "ops/budgets").mkdir(exist_ok=True)
    (root / BUDGET).write_text(f"title: Provider credits\nunit: USD\ngrants:\n{grants}", encoding="utf-8")


def mission(root: Path, slug: str, cap: float, status: str = "active", name: str = "credits") -> str:
    path = f"ops/missions/2026-10-05-{slug}.md"
    approved = "" if status == "draft" else 'approved: "The commander, 2026-10-05, under budget credits"\n'
    (root / path).write_text(f"---\ntitle: {slug}\nstatus: {status}\nrests_on: [Q-1]\nbudget: {name}\n"
                             f"cap: {cap}\n{approved}---\n\n## Log\n\n- 2026-10-05 Drafted.\n", encoding="utf-8")
    return path


def test_missions_inside_the_budget_pass(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        mission(root, "first", 120)
        mission(root, "second", 80)
    make_lab(setup)
    assert problems(lab_kit, "lab-mission-approved") == (0, [])


def test_missions_past_the_budget_fail(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        mission(root, "first", 150)
        mission(root, "second", 100)
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1
    problem = named(found, "lab-mission-approved")[0]
    assert problem["path"] == BUDGET and "commit 250" in problem["message"] and "past the 200" in problem["message"]


def test_a_draft_commits_nothing(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        mission(root, "first", 150)
        mission(root, "second", 100, status="draft")
    make_lab(setup)
    assert problems(lab_kit, "lab-mission-approved") == (0, [])


def test_a_new_grant_makes_room(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root, GRANT + GRANT.replace("2026-10-04", "2026-10-06"))
        mission(root, "first", 150)
        mission(root, "second", 100)
    make_lab(setup)
    assert problems(lab_kit, "lab-mission-approved") == (0, [])


def test_a_concluded_mission_commits_what_it_spent(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        done = mission(root, "first", 150, status="concluded")
        mission(root, "second", 150)
        edit_json(root / RUN / "run.json", spend=True, mission=done, spent=40)
    make_lab(setup)
    assert problems(lab_kit, "lab-mission-approved") == (0, [])


def test_a_mission_names_a_budget_that_exists(make_lab, lab_kit) -> None:
    make_lab(lambda r: mission(r, "first", 50, name="nowhere"))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "ops/budgets/nowhere.yaml does not exist" in named(found, "lab-mission-approved")[0]["message"]


def test_a_mission_under_a_budget_has_a_cap(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        edit(root / mission(root, "first", 50), "cap: 50\n", "")
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "a finite number >= 0" in named(found, "lab-mission-approved")[0]["message"]


def test_a_grant_records_who_and_when(make_lab, lab_kit) -> None:
    make_lab(lambda r: budget(r, GRANT.replace("The operator, 2026-10-04: t", "T")))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "who granted it and the date" in named(found, "lab-mission-approved")[0]["message"]


def test_a_grant_has_an_amount(make_lab, lab_kit) -> None:
    make_lab(lambda r: budget(r, GRANT.replace("amount: 200", "amount: lots")))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "no positive, finite numeric `amount`" in named(found, "lab-mission-approved")[0]["message"]


def test_grants_are_only_added(make_lab, lab_kit) -> None:
    root = make_lab(budget)
    with (root / BUDGET).open("a", encoding="utf-8") as handle:
        handle.write(GRANT.replace("2026-10-04", "2026-10-06"))
    commit(root, "a second grant")
    assert problems(lab_kit, "lab-append-only") == (0, [])
    edit(root / BUDGET, "amount: 200", "amount: 900")
    code, found = problems(lab_kit, "lab-append-only")
    assert code == 1 and "grant is only ever added" in named(found, "lab-append-only")[0]["message"]


def test_a_budget_is_never_deleted(make_lab, lab_kit) -> None:
    root = make_lab(budget)
    (root / BUDGET).unlink()
    code, found = problems(lab_kit, "lab-append-only")
    assert code == 1 and "never deleted" in named(found, "lab-append-only")[0]["message"]


def test_status_shows_the_budgets(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        mission(root, "first", 120)
    make_lab(setup)
    code, out = lab_kit("status")
    assert code == 0 and "credits: 200 USD granted, 120 committed, 80 left" in out
    assert "ops/missions/2026-10-05-first.md: 120" in out


@pytest.mark.parametrize("cap", ["-100", ".nan", ".inf"])
def test_a_cap_under_a_budget_is_finite_and_not_negative(make_lab, lab_kit, cap) -> None:
    def setup(root: Path) -> None:
        budget(root)
        mission(root, "first", 150)
        edit(root / mission(root, "second", 1), "cap: 1\n", f"cap: {cap}\n")
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "a finite number >= 0" in named(found, "lab-mission-approved")[0]["message"]


def test_an_infinite_grant_is_no_grant(make_lab, lab_kit) -> None:
    make_lab(lambda r: budget(r, GRANT.replace("amount: 200", "amount: .inf")))
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "finite numeric `amount`" in named(found, "lab-mission-approved")[0]["message"]


def test_a_negative_spend_is_refused(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        done = mission(root, "first", 150, status="concluded")
        edit_json(root / RUN / "run.json", spend=True, mission=done, spent=-500)
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "not a finite number >= 0" in named(found, "lab-mission-approved")[0]["message"]


def test_an_active_mission_commits_what_it_spent_past_its_cap(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        active = mission(root, "first", 10)
        mission(root, "second", 150)
        edit_json(root / RUN / "run.json", spend=True, mission="./" + active, spent=90)
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "commit 240" in named(found, "lab-mission-approved")[0]["message"]


def test_a_budget_that_does_not_parse_is_named(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        (root / "ops/budgets").mkdir()
        (root / BUDGET).write_text("- just a list\n", encoding="utf-8")
        mission(root, "first", 50)
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and any("not a valid budget" in p["message"] for p in named(found, "lab-mission-approved"))


def test_the_unit_never_changes(make_lab, lab_kit) -> None:
    root = make_lab(budget)
    edit(root / BUDGET, "unit: USD", "unit: kUSD")
    code, found = problems(lab_kit, "lab-append-only")
    assert code == 1 and "unit of a standing budget never changes" in named(found, "lab-append-only")[0]["message"]


def test_a_live_spending_run_is_not_bad_spend(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        live = mission(root, "first", 150)
        edit_json(root / RUN / "run.json", spend=True, mission=live, spent=None)
    make_lab(setup)
    assert problems(lab_kit, "lab-mission-approved") == (0, [])


def test_a_deleted_yml_budget_is_caught(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        (root / BUDGET).rename(root / "ops/budgets/credits.yml")
    root = make_lab(setup)
    (root / "ops/budgets/credits.yml").unlink()
    code, found = problems(lab_kit, "lab-append-only")
    assert code == 1 and "never deleted" in named(found, "lab-append-only")[0]["message"]


def test_one_name_one_budget_file(make_lab, lab_kit) -> None:
    def setup(root: Path) -> None:
        budget(root)
        (root / "ops/budgets/credits.yml").write_text((root / BUDGET).read_text(encoding="utf-8"), encoding="utf-8")
    make_lab(setup)
    code, found = problems(lab_kit, "lab-mission-approved")
    assert code == 1 and "keep one" in named(found, "lab-mission-approved")[0]["message"]
