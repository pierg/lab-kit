"""The lab gate: `folio check` on the library, then every lab check, in one report."""

from __future__ import annotations

from folio.checks.problems import Problem
from folio.checks.run import run as folio_run

from ..errors import LabError
from ..lab import Lab
from . import files, locks, results
from .base import LabCheck, Reporter

FOLIO = "folio"

CHECKS: tuple[LabCheck, ...] = (
    LabCheck("lab-lock-recorded", "error", locks.lock_recorded),
    LabCheck("lab-lock-intact", "error", locks.lock_intact),
    LabCheck("lab-run-after-lock", "error", locks.run_after_lock),
    LabCheck("lab-roster-frozen", "error", locks.roster_frozen),
    LabCheck("lab-evidence-sealed", "error", locks.evidence_sealed),
    LabCheck("lab-rederive", "error", results.rederive),
    LabCheck("lab-result-grounded", "error", results.result_grounded),
    LabCheck("lab-score-exact", "error", results.score_exact),
    LabCheck("lab-ids-resolve", "error", files.ids_resolve),
    LabCheck("lab-frozen-intact", "error", files.frozen_intact),
    LabCheck("lab-selftest", "error", files.selftest),
    LabCheck("lab-mission-approved", "error", files.mission_approved),
    LabCheck("lab-spend-recorded", "error", files.spend_recorded),
    LabCheck("lab-append-only", "error", files.append_only),
    LabCheck("lab-method-current", "error", files.method_current),
    LabCheck("lab-state-pointer", "warning", files.state_pointer),
    LabCheck("lab-scored-reported", "warning", results.scored_reported),
)
BY_NAME = {c.name: c for c in CHECKS}


def names() -> list[str]:
    return [FOLIO, *BY_NAME]


def folio_problems(lab: Lab) -> list[Problem]:
    """folio's own gate on the library, with paths from the lab root."""
    lib = lab.library()
    return [Problem(lab.doc_path(p.path), p.severity, p.check, p.message) for p in folio_run(lib)]


def run(lab: Lab, only: list[str] | None = None) -> list[Problem]:
    """Every problem, folio's first, then the lab checks' in the order of the spec."""
    wanted = only or names()
    unknown = [n for n in wanted if n not in names()]
    if unknown:
        raise LabError(f"no check named {', '.join(unknown)}; the checks are: {', '.join(names())}")
    lab.library()  # fail loud, once, when the library does not load
    problems: list[Problem] = []
    if FOLIO in wanted:
        problems.extend(folio_problems(lab))
    for check in CHECKS:
        if check.name not in wanted:
            continue
        rep = Reporter(check.name, check.severity)
        check.fn(lab, rep)
        problems.extend(sorted(set(rep.problems)))
    return problems
