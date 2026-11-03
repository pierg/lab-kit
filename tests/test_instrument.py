"""The lock covers the instrument, records name the commit they ran at, and a run's raw output is sealed."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import commit, git

from lab_kit import __version__, records
from lab_kit.lab import load

EXP = "experiments/pi-error-scaling"
SLUG = "pi-error-scaling"
WORKER = ("import os, pathlib; w = pathlib.Path(os.environ['LAB_WORK']); (w / 'logs').mkdir(); "
          "(w / 'logs' / 'a.log').write_text('one'); (w / 'trace.jsonl').write_text('{}')")


def _relocked(make_lab, lab_kit) -> Path:
    """The example lab with its lock taken again by this lab-kit, committed."""
    root = make_lab(lambda r: (r / EXP / "lock.json").unlink())
    code, out = lab_kit("lock", SLUG)
    assert code == 0, out
    commit(root, "relock")
    return root


def test_lock_records_the_instrument_the_commit_and_the_version(make_lab, lab_kit) -> None:
    root = make_lab(lambda r: (r / EXP / "lock.json").unlink())
    head = git(root, "rev-parse", "HEAD").strip()
    assert lab_kit("lock", SLUG)[0] == 0
    data = json.loads((root / EXP / "lock.json").read_text(encoding="utf-8"))
    assert data["instrument"] == records.instrument_hash(root / EXP / "bin")
    assert len(data["instrument"]) == 64
    assert data["commit"] == head
    assert data["lab-kit"] == __version__


def test_instrument_hash_reads_paths_and_contents(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.py").write_text("x")
    (tmp_path / "y.sh").write_text("y")
    first = records.instrument_hash(tmp_path)
    (tmp_path / "a" / "__pycache__").mkdir()
    (tmp_path / "a" / "__pycache__" / "x.pyc").write_bytes(b"\0")
    assert records.instrument_hash(tmp_path) == first  # bytecode is not the instrument
    (tmp_path / "y.sh").rename(tmp_path / "z.sh")
    assert records.instrument_hash(tmp_path) != first  # a rename changes it
    (tmp_path / "z.sh").rename(tmp_path / "y.sh")
    (tmp_path / "y.sh").write_text("y2")
    assert records.instrument_hash(tmp_path) != first  # an edit changes it


def test_lock_intact_fails_when_the_instrument_changes(make_lab, lab_kit) -> None:
    root = _relocked(make_lab, lab_kit)
    code, out = lab_kit("check", "--only", "lab-lock-intact")
    assert code == 0, out
    with (root / EXP / "bin" / "fold.py").open("a", encoding="utf-8") as handle:
        handle.write("\n# an edit after the lock\n")
    code, out = lab_kit("check", "--only", "lab-lock-intact")
    assert code == 1 and "bin/ changed since its lock" in out, out
    (root / EXP / "bin" / "extra.py").write_text("print(1)\n", encoding="utf-8")
    git(root, "checkout", "--", f"{EXP}/bin/fold.py")
    code, out = lab_kit("check", "--only", "lab-lock-intact")
    assert code == 1 and "bin/ changed since its lock" in out, out


def test_a_lock_without_the_new_fields_still_passes(make_lab, lab_kit) -> None:
    root = make_lab()
    assert "instrument" not in json.loads((root / EXP / "lock.json").read_text(encoding="utf-8"))
    (root / EXP / "bin" / "extra.py").write_text("print(1)\n", encoding="utf-8")
    code, out = lab_kit("check", "--only", "lab-lock-intact")
    assert code == 0, out


def test_run_records_its_commit_and_seals_work(make_lab, lab_kit) -> None:
    root = make_lab()
    head = git(root, "rev-parse", "HEAD").strip()
    code, out = lab_kit("run", SLUG, "--wait", "--", "python3", "-c", WORKER)
    assert code == 0, out
    newest = records.runs(load(root), SLUG)[-1]
    assert newest.data["commit"] == head and newest.data["lab-kit"] == __version__
    sealed = (newest.folder / records.WORK_MANIFEST).read_text(encoding="utf-8")
    assert sealed == records.format_hashes(records.tree_hashes(newest.folder / "work", newest.folder / "work"))
    assert sealed.splitlines()[0].endswith("  logs/a.log") and sealed.splitlines()[1].endswith("  trace.jsonl")
    assert lab_kit("check", "--only", "lab-evidence-sealed", "--only", "lab-append-only")[0] == 0


def test_run_refuses_a_changed_instrument(make_lab, lab_kit) -> None:
    root = _relocked(make_lab, lab_kit)
    (root / EXP / "bin" / "extra.py").write_text("print(1)\n", encoding="utf-8")
    code, out = lab_kit("run", SLUG, "--wait", "--", "python3", "-c", "pass")
    assert code == 2 and "bin/ changed since its lock" in out, out
