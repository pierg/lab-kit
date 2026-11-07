"""The run store: a run moves there when it ends, verified; verify, fetch, and the lab-run-stored warning."""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

from lab_kit import records
from lab_kit.lab import load

EXP = "26-10-04-e_pi-error-scaling"
WRITER = ("import os, pathlib; r = pathlib.Path(os.environ['LAB_RUN']); (r / 'a').mkdir(); "
          "(r / 'a' / 'trace.txt').write_text('raw'); (r / 'b.txt').write_text('more'); "
          "open(os.environ['LAB_OUT'] + '/n.txt', 'w').write('1')")


def _with_store(store: Path, mounted: bool = True):
    """The example lab with a store: its runs/ moved there and linked, as `lab-kit migrate` leaves it."""
    def before(root: Path) -> None:
        text = (root / "lab.yaml").read_text(encoding="utf-8")
        (root / "lab.yaml").write_text(text + f"store: {store}\n", encoding="utf-8")
        if mounted:
            store.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root / "runs"), str(store / "runs"))
        else:
            shutil.rmtree(root / "runs")
        (root / "runs").symlink_to(store / "runs", target_is_directory=True)
    return before


def test_a_run_moves_to_the_store_and_leaves_nothing_here(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "labs" / "mc"
    root = make_lab(_with_store(store))
    code, out = lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)
    assert code == 0, out
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert run.base.startswith("runs/") and records.RUN_ID.match(run.run_id)
    dest = store / "runs" / EXP / run.run_id
    assert run.folder.resolve() == dest.resolve()
    assert (dest / "a" / "trace.txt").read_text() == "raw" and (dest / "out" / "n.txt").read_text() == "1"
    assert (dest / "run.log").is_file() and not (dest / "work").exists()  # an unused work/ leaves no trace
    assert not (dest / "b.txt").stat().st_mode & stat.S_IWUSR
    assert not (root / ".lab" / "running" / EXP / run.run_id).exists()
    assert not any((store / ".incoming").iterdir())
    assert set(run.data["files"]) == {"a/trace.txt", "b.txt", "out/n.txt", "run.log"}
    assert lab_kit("verify", f"{EXP}/{run.run_id}")[0] == 0
    assert lab_kit("check", "--only", "lab-run-stored", "--only", "lab-evidence-sealed") == \
        (0, "lab-kit check: 0 errors, 0 warnings\n")


def test_a_changed_file_or_record_breaks_the_seal(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "labs" / "mc"
    root = make_lab(_with_store(store))
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    copy = store / "runs" / EXP / run.run_id / "b.txt"
    copy.chmod(0o644)
    copy.write_text("edited")
    code, out = lab_kit("verify", f"{EXP}/{run.run_id}")
    assert code == 2 and "changed b.txt" in out
    copy.write_text("more")
    record = store / "runs" / EXP / run.run_id / "run.json"
    record.chmod(0o644)
    record.write_text(record.read_text().replace('"exit": 0', '"exit": 1'))
    code, out = lab_kit("check", "--only", "lab-evidence-sealed")
    assert code == 1 and "changed after the run was sealed" in out


def test_without_a_mounted_store_the_run_stays_here_and_check_warns(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "not-mounted"
    root = make_lab(_with_store(store, mounted=False))
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert run.base.startswith(".lab/running/") and (run.folder / "b.txt").is_file()
    assert "not moved to the store" in (run.folder / "run.log").read_text()
    assert not records.seal_problems(run.folder, run.data)  # sealed again after the note
    code, out = lab_kit("check", "--only", "lab-run-stored", "--only", "lab-evidence-sealed")
    assert code == 0 and "still on this machine" in out and "does not resolve here" in out
    (store / "runs").mkdir(parents=True)
    code, out = lab_kit("publish", "--pending")
    assert code == 0 and "copied and verified" in out
    assert not run.folder.exists() and (store / "runs" / EXP / run.run_id / "b.txt").is_file()


def test_a_lab_without_a_store_writes_runs_in_place(make_lab, lab_kit) -> None:
    root = make_lab()
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert run.folder.parent == root / "runs" / EXP and (run.folder / "b.txt").is_file()
    code, out = lab_kit("publish", "--pending")
    assert code == 2 and "names no `store:`" in out


LINKER = ("import os, pathlib; r = pathlib.Path(os.environ['LAB_RUN']); "
          "real = r.parent.parent / 'outside.bin'; real.write_text('bytes'); "
          "(r / 'model.bin').symlink_to(real); (r / 'res_{seed}.json').write_text('{}')")


def test_a_linked_file_is_stored_as_its_bytes(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "labs" / "mc"
    root = make_lab(_with_store(store))
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", LINKER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    copy = store / "runs" / EXP / run.run_id / "model.bin"
    assert not copy.is_symlink() and copy.read_text() == "bytes"
    assert (copy.parent / "res_{seed}.json").is_file()


def test_an_empty_folder_where_the_store_should_be_is_not_the_store(make_lab, lab_kit, tmp_path) -> None:
    root = make_lab(_with_store(tmp_path / "labs" / "mc", mounted=False))
    (tmp_path / "labs").mkdir()  # a mount point whose mount failed: not a mount, no lab folder
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert (run.folder / "b.txt").is_file() and not (tmp_path / "labs" / "mc").exists()
