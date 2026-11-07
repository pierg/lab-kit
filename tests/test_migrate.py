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


def test_a_failed_git_phase_loses_nothing_and_a_retry_reuses_the_runs(tmp_path, monkeypatch, lab_kit, folio) -> None:
    from lab_kit.commands import migrate as migrate_mod
    store = tmp_path / "labs" / "mc"
    root = _legacy(tmp_path, monkeypatch, store)
    (root / OLD_RUN / "work").mkdir()
    (root / OLD_RUN / "work" / "only-here.txt").write_text("raw, never published")
    real = migrate_mod.write_baseline

    def boom(*args, **kwargs):
        raise RuntimeError("the disk filled up")
    monkeypatch.setattr(migrate_mod, "write_baseline", boom)
    code, out = lab_kit("migrate", "--apply")
    assert code == 2 and "The runs are in place and safe" in out
    [placed] = [p for p in (store / "runs" / EXP).iterdir()]
    assert (placed / "work" / "only-here.txt").read_text() == "raw, never published"
    git(root, "reset", "-q", "--hard")
    monkeypatch.setattr(migrate_mod, "write_baseline", real)
    code, out = lab_kit("migrate", "--apply")
    assert code == 0 and "were in place already" in out, out
    assert [p.name for p in (store / "runs" / EXP).iterdir()] == [placed.name]
    _finish(root, folio)
    assert lab_kit("check")[0] == 0


def test_a_lock_that_drifted_before_is_refused(tmp_path, monkeypatch, lab_kit) -> None:
    root = _legacy(tmp_path, monkeypatch)
    protocol = root / "docs/content/protocols/pi-error-scaling.md"
    protocol.write_text(protocol.read_text().replace("100 estimates per arm", "200 estimates per arm"))
    commit(root, "an edit after the lock")
    code, out = lab_kit("migrate", "--apply")
    assert code == 2 and "the gate fails before the rewrite" in out
    assert (root / OLD_RUN).is_dir()


def test_a_run_with_no_end_moves_only_when_named(tmp_path, monkeypatch, lab_kit) -> None:
    root = _legacy(tmp_path, monkeypatch)
    record = root / OLD_RUN / "run.json"
    data = json.loads(record.read_text())
    data.update(ended=None, exit=None, pid=None)
    record.write_text(json.dumps(data))
    commit(root, "a run committed while going")
    code, out = lab_kit("migrate")
    assert "--orphaned" in out and "Problems" in out
    code, out = lab_kit("migrate", "--orphaned", OLD_RUN)
    assert "Dry run" in out and "named as dead" in out


def test_names_inside_file_names_stay(tmp_path) -> None:
    from lab_kit.commands.migrate import Plan, Run, replacements, rewriter
    plan_ = Plan(missions={"ops/missions/2026-11-04-floor.md": "missions/26-11-04-m_floor.md"},
                 experiments={"floor": "26-11-04-e_floor", "floor-2": "26-11-05-e_floor-2"})
    plan_.runs.append(Run("floor", "20261104-053817", Path("x"), {}, "26-11-04-e_floor", "26-11-04-0538-r_abcd"))
    rewrite = rewriter(replacements(plan_, []))
    text = ("see experiments/floor-2/bin and experiments/floor/runs/20261104-053817/out/x.tsv; run 20261104-053817. "
            "figures/20261104-053817.png; journal/2026/2026-11-04-floor.md; ops/missions/2026-11-04-floor.md#log")
    new, _ = rewrite(text)
    assert "experiments/26-11-05-e_floor-2/bin" in new
    assert "runs/26-11-04-e_floor/26-11-04-0538-r_abcd/out/x.tsv" in new and "run 26-11-04-0538-r_abcd." in new
    assert "figures/20261104-053817.png" in new and "journal/2026/2026-11-04-floor.md" in new
    assert "missions/26-11-04-m_floor.md#log" in new


def test_a_rewritten_protocol_is_relocked_and_late_runs_follow(tmp_path, monkeypatch, lab_kit, folio) -> None:
    def mention(root: Path) -> None:
        protocol = root / "docs/content/protocols/pi-error-scaling.md"
        protocol.write_text(protocol.read_text().replace(
            "## Pinned configuration", "The runs go in experiments/pi-error-scaling/runs.\n\n## Pinned configuration", 1))
    root = tmp_path / "lab"
    shutil.copytree(LEGACY, root, symlinks=True)
    mention(root)
    # Lock it again over the edited text, as if the protocol had said so when it was locked.
    from lab_kit import protocol as protocol_mod
    lock_path = root / "experiments/pi-error-scaling/lock.json"
    lock = json.loads(lock_path.read_text())
    old_sha = protocol_mod.hash_text((root / "docs/content/protocols/pi-error-scaling.md").read_text())
    lock["sha256"] = old_sha
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    run_json = root / OLD_RUN / "run.json"
    data = json.loads(run_json.read_text())
    data["lock"] = old_sha
    run_json.write_text(json.dumps(data, indent=2) + "\n")
    score = root / "experiments/pi-error-scaling/score.yaml"
    text = score.read_text()
    score.write_text(text.replace(text.split("lock: ")[1].split("\n")[0], old_sha, 1))
    keep = tmp_path / "late"
    shutil.copytree(root / OLD_RUN, keep)
    init_repo(root)
    commit(root, "the lab before 0.6.0")
    monkeypatch.chdir(root)
    code, out = lab_kit("migrate", "--apply")
    assert code == 0 and "took the lock hash again for 1" in out, out
    _finish(root, folio)
    code, out = lab_kit("check")
    assert code == 0, out
    late = root / "experiments/pi-error-scaling/runs/20261004-235959"
    shutil.copytree(keep, late)
    data = json.loads((late / "run.json").read_text())
    data["started"] = "2026-10-04T23:59:59+00:00"
    (late / "run.json").write_text(json.dumps(data))
    commit(root, "a late run with the old lock hash")
    assert lab_kit("migrate", "--apply")[0] == 0
    _finish(root, folio)
    code, out = lab_kit("check")
    assert code == 0, out


def test_a_pinned_configuration_that_names_a_run_is_rewritten_in_both(tmp_path, monkeypatch, lab_kit, folio) -> None:
    root = tmp_path / "lab"
    shutil.copytree(LEGACY, root, symlinks=True)
    protocol = root / "docs/content/protocols/pi-error-scaling.md"
    protocol.write_text(protocol.read_text().replace(
        "language: python 3, standard library only",
        f"language: python 3, standard library only\nprior: {OLD_RUN}/out/estimates.tsv", 1))
    from lab_kit import protocol as protocol_mod
    lock_path = root / "experiments/pi-error-scaling/lock.json"
    lock = json.loads(lock_path.read_text())
    sha = protocol_mod.hash_text(protocol.read_text())
    lock["sha256"] = sha
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    run_json = root / OLD_RUN / "run.json"
    data = json.loads(run_json.read_text())
    data["lock"] = sha
    data["config"] = {"language": data["config"]["language"], "prior": f"{OLD_RUN}/out/estimates.tsv",
                      **{k: v for k, v in data["config"].items() if k != "language"}}
    run_json.write_text(json.dumps(data, indent=2) + "\n")
    score = root / "experiments/pi-error-scaling/score.yaml"
    text = score.read_text()
    score.write_text(text.replace(text.split("lock: ")[1].split("\n")[0], sha, 1))
    init_repo(root)
    commit(root, "the lab before 0.6.0")
    monkeypatch.chdir(root)
    assert lab_kit("check", "--only", "lab-roster-frozen")[0] == 0
    code, out = lab_kit("migrate", "--apply")
    assert code == 0, out
    [run] = records.runs(load(root))
    assert run.data["config"]["prior"] == f"runs/{EXP}/{run.run_id}/out/estimates.tsv"
    _finish(root, folio)
    code, out = lab_kit("check")
    assert code == 0, out
