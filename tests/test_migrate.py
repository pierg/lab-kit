"""`lab-kit migrate`: a lab in the layout before 0.6.0 moves to dated ids, missions/ and one folder per run."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from conftest import commit, git, init_repo

from lab_kit import records
from lab_kit.lab import load

LEGACY = Path(__file__).resolve().parent / "fixtures" / "monte-carlo-lab-0.5"
EXP = "26-10-04-e_pi-error-scaling"
OLD_RUN = "experiments/pi-error-scaling/runs/20261004-231629"


def _legacy(tmp_path: Path, monkeypatch, store: Path | None = None) -> Path:
    root = tmp_path / "lab"
    shutil.copytree(LEGACY, root, symlinks=True)
    if store is not None:
        store.mkdir(parents=True)
        text = (root / "lab.yaml").read_text(encoding="utf-8")
        (root / "lab.yaml").write_text(text + f"store: {store}\n", encoding="utf-8")
    init_repo(root)
    commit(root, "the lab before 0.6.0")
    monkeypatch.chdir(root)
    return root


def _finish(root: Path, folio) -> None:
    assert folio(root / "docs", "index")[0] == 0
    commit(root, "migrate to the 0.6.0 layout")


def test_a_dry_run_changes_nothing(tmp_path, monkeypatch, lab_kit) -> None:
    root = _legacy(tmp_path, monkeypatch)
    code, out = lab_kit("migrate")
    assert code == 0 and f"{OLD_RUN} -> runs/{EXP}/26-10-04-2316-r_" in out and "Dry run" in out
    assert git(root, "status", "--porcelain") == ""


def test_migrate_moves_everything_and_the_gate_passes(tmp_path, monkeypatch, lab_kit, folio) -> None:
    root = _legacy(tmp_path, monkeypatch)
    code, out = lab_kit("migrate", "--apply")
    assert code == 0, out
    assert (root / "missions/26-10-04-m_pi-error-scaling.md").is_file() and not (root / "ops/missions").exists()
    assert (root / f"experiments/{EXP}/lock.json").is_file() and not (root / "experiments/pi-error-scaling").exists()
    [run] = records.runs(load(root))
    assert run.slug == EXP and records.RUN_ID.match(run.run_id)
    assert run.data["migrated"]["from"] == OLD_RUN and run.data["mission"] == "missions/26-10-04-m_pi-error-scaling.md"
    assert not records.seal_problems(run.folder, run.data) and "out/estimates.tsv" in run.data["files"]
    result = (root / "docs/content/results/R-1.md").read_text(encoding="utf-8")
    assert f"runs/{EXP}/{run.run_id}/out/estimates.tsv" in result and "experiments/pi-error-scaling" not in result
    assert (root / "docs/baseline.sha256").is_file() and "baseline: baseline.sha256" in \
        (root / "docs/folio.yaml").read_text(encoding="utf-8")
    assert "run\tpi-error-scaling/20261004-231629\t" in (root / ".lab/migration.tsv").read_text(encoding="utf-8")
    code, out = lab_kit("check")  # before the commit: folio's baseline already holds
    assert code == 0, out
    _finish(root, folio)
    code, out = lab_kit("check")
    assert code == 0 and out.strip().endswith("0 errors, 0 warnings"), out
    code, out = lab_kit("migrate")
    assert "Runs to move: 0" in out and "Missions to move: 0" in out


def test_with_a_store_runs_move_there_and_runs_links_to_it(tmp_path, monkeypatch, lab_kit, folio) -> None:
    store = tmp_path / "labs" / "mc"
    root = _legacy(tmp_path, monkeypatch, store)
    code, out = lab_kit("migrate", "--apply")
    assert code == 0, out
    assert (root / "runs").is_symlink() and (root / "runs").resolve() == (store / "runs").resolve()
    [run] = records.runs(load(root))
    assert (store / "runs" / EXP / run.run_id / "out" / "estimates.tsv").is_file()
    _finish(root, folio)
    assert lab_kit("check")[0] == 0


def test_an_old_run_that_lands_later_moves_on_a_second_pass(tmp_path, monkeypatch, lab_kit, folio) -> None:
    root = _legacy(tmp_path, monkeypatch)
    old = root / OLD_RUN
    keep = tmp_path / "late"
    shutil.copytree(old, keep)
    assert lab_kit("migrate", "--apply")[0] == 0
    _finish(root, folio)
    # A machine still on 0.5.0 commits a run in the old layout after the move.
    late = root / "experiments/pi-error-scaling/runs/20261004-235959"
    shutil.copytree(keep, late)
    data = json.loads((late / "run.json").read_text(encoding="utf-8"))
    data["started"] = "2026-10-04T23:59:59+00:00"
    (late / "run.json").write_text(json.dumps(data), encoding="utf-8")
    commit(root, "a late run, in the old layout")
    code, out = lab_kit("migrate", "--apply")
    assert code == 0, out
    assert not (root / "experiments/pi-error-scaling").exists()
    assert len(records.runs(load(root))) == 2
    _finish(root, folio)
    code, out = lab_kit("check")
    assert code == 0, out
