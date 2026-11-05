"""The run store: publish, verify, fetch, and the lab-work-stored warning."""

from __future__ import annotations

import stat
from pathlib import Path

from lab_kit import records
from lab_kit.lab import load

WRITER = ("import os, pathlib; w = pathlib.Path(os.environ['LAB_WORK']); (w / 'a').mkdir(); "
          "(w / 'a' / 'trace.txt').write_text('raw'); (w / 'b.txt').write_text('more'); "
          "open(os.environ['LAB_OUT'] + '/n.txt', 'w').write('1')")


def _with_store(store: Path):
    def before(root: Path) -> None:
        text = (root / "lab.yaml").read_text(encoding="utf-8")
        (root / "lab.yaml").write_text(text + f"store: {store}\n", encoding="utf-8")
    return before


def test_a_run_publishes_to_the_store_and_drops_its_local_copy(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "labs" / "mc"
    store.mkdir(parents=True)
    root = make_lab(_with_store(store))
    code, out = lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)
    assert code == 0, out
    run = records.runs(load(root), "pi-error-scaling")[-1]
    dest = store / "experiments" / "pi-error-scaling" / "runs" / run.run_id
    assert (dest / "work" / "a" / "trace.txt").read_text() == "raw"
    assert (dest / "run.log").is_file()
    assert not (dest / "work" / "b.txt").stat().st_mode & stat.S_IWUSR
    assert not (run.folder / "work").exists() and not (run.folder / "run.log").exists()
    assert (run.folder / "store.json").is_file()
    assert not any((store / ".incoming").iterdir())
    ref = f"pi-error-scaling/{run.run_id}"
    assert lab_kit("verify", ref)[0] == 0
    code, out = lab_kit("fetch", ref)
    assert code == 0 and (run.folder / "work" / "b.txt").read_text() == "more"
    assert (run.folder / "work" / "b.txt").stat().st_mode & stat.S_IWUSR
    assert lab_kit("check", "--only", "lab-work-stored") == (0, "lab-kit check: 0 errors, 0 warnings\n")


def test_a_tampered_store_copy_fails_verify_and_is_never_overwritten(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "labs" / "mc"
    store.mkdir(parents=True)
    root = make_lab(_with_store(store))
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    ref = f"pi-error-scaling/{run.run_id}"
    lab_kit("fetch", ref)
    copy = store / "experiments" / "pi-error-scaling" / "runs" / run.run_id / "work" / "b.txt"
    copy.chmod(0o644)
    copy.write_text("edited")
    code, out = lab_kit("verify", ref)
    assert code == 2 and "changed b.txt" in out
    (run.folder / "store.json").unlink()
    code, out = lab_kit("publish", ref)
    assert code == 1 and "never overwritten" in out
    assert (run.folder / "work" / "b.txt").read_text() == "more"


def test_without_a_mounted_store_the_run_stays_here_and_check_warns(make_lab, lab_kit, tmp_path) -> None:
    root = make_lab(_with_store(tmp_path / "not-mounted"))
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert (run.folder / "work" / "b.txt").is_file()
    assert "not published to the store" in (run.folder / "run.log").read_text()
    code, out = lab_kit("check", "--only", "lab-work-stored")
    assert code == 0 and "never published" in out and "1 warnings" in out
    (tmp_path / "not-mounted").mkdir()
    code, out = lab_kit("publish", "--pending")
    assert code == 0 and "copied and verified" in out
    assert not (run.folder / "work").exists()


def test_a_lab_without_a_store_is_unchanged(make_lab, lab_kit) -> None:
    root = make_lab()
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert (run.folder / "work" / "b.txt").is_file() and not (run.folder / "store.json").exists()
    code, out = lab_kit("publish", "--pending")
    assert code == 2 and "names no `store:`" in out


LINKER = ("import os, pathlib; w = pathlib.Path(os.environ['LAB_WORK']); "
          "real = pathlib.Path(os.environ['LAB_RUN_DIR']).parent.parent / 'outside.bin'; real.write_text('bytes'); "
          "(w / 'model.bin').symlink_to(real); (w / 'res_{seed}.json').write_text('{}')")


def test_a_linked_file_is_stored_as_its_bytes(make_lab, lab_kit, tmp_path) -> None:
    store = tmp_path / "labs" / "mc"
    store.mkdir(parents=True)
    root = make_lab(_with_store(store))
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", LINKER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    copy = store / "experiments" / "pi-error-scaling" / "runs" / run.run_id / "work" / "model.bin"
    assert not copy.is_symlink() and copy.read_text() == "bytes"
    assert (copy.parent / "res_{seed}.json").is_file()


def test_an_empty_folder_where_the_store_should_be_is_not_the_store(make_lab, lab_kit, tmp_path) -> None:
    root = make_lab(_with_store(tmp_path / "labs" / "mc"))
    (tmp_path / "labs").mkdir()  # a mount point whose mount failed: not a mount, no lab folder
    assert lab_kit("run", "pi-error-scaling", "--wait", "--", "python3", "-c", WRITER)[0] == 0
    run = records.runs(load(root), "pi-error-scaling")[-1]
    assert (run.folder / "work" / "b.txt").is_file() and not (tmp_path / "labs" / "mc").exists()
