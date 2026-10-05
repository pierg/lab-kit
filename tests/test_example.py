"""The example lab passes the gate with no error and no warning, in a git repository of its own."""

from __future__ import annotations

import json

from lab_kit import __version__


def test_example_passes(make_lab, lab_kit) -> None:
    make_lab()
    code, out = lab_kit("check")
    assert code == 0, out
    assert out.strip().endswith("0 errors, 0 warnings"), out


def test_check_json_and_only(make_lab, lab_kit) -> None:
    make_lab()
    code, out = lab_kit("check", "--json")
    assert code == 0 and json.loads(out) == {"problems": [], "errors": 0, "warnings": 0}
    code, out = lab_kit("check", "--only", "lab-selftest", "--only", "folio")
    assert code == 0, out
    code, out = lab_kit("check", "--only", "lab-nothing")
    assert code == 2 and "no check named lab-nothing" in out


def test_version(lab_kit) -> None:
    assert lab_kit("version") == (0, f"lab-kit {__version__}\n")


def test_rederive_status_runs(make_lab, lab_kit) -> None:
    make_lab()
    assert lab_kit("rederive", "R-2") == (0, "R-2: re-derived `-0.493`, its number\n")
    # A superseded result still re-derives its own number.
    assert lab_kit("rederive", "R-1")[0] == 0
    code, out = lab_kit("status")
    assert code == 0 and "Active mission: none" in out and "Protocols locked: pi-error-scaling" in out
    code, out = lab_kit("runs")
    assert code == 0 and "finished" in out
    assert lab_kit("runs", "--live") == (0, "No live runs.\n")
