"""The background half of `lab-kit run`: run the lab's command, then seal its folder.

`lab-kit run` starts this module as a detached process with the run's folder, and writes its pid
into `run.json`. This process waits for that, runs the command from the lab root with its output in
`run.log`, and when the command exits records the exit code, the end time and every file's hash
(the seal) in `run.json`. When `lab.yaml` names a `store:`, it then moves the run's folder into the
store (lab_kit.store); a move that fails is noted in `run.log` and leaves the run here for
`lab-kit publish --pending`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import records

ENV_RUN = "LAB_RUN"          # the run's folder: everything the run writes goes in it
ENV_RUN_DIR = "LAB_RUN_DIR"  # the same, by its name before 0.6.0
ENV_OUT = "LAB_OUT"          # <run>/out, kept for scripts written before 0.6.0
ENV_WORK = "LAB_WORK"        # <run>/work, kept for scripts written before 0.6.0
LEGACY = ("out", "work")


def _spent(run_dir: Path) -> float | None:
    for path in (run_dir / records.SPEND, run_dir / "out" / records.SPEND):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8")).get("spent")
        except (json.JSONDecodeError, AttributeError):
            return None
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return None


def _wait_for_pid(run_json: Path) -> dict:
    """Wait until `lab-kit run` has written this process's pid, so the two never write run.json at once."""
    deadline = time.monotonic() + 10
    while True:
        data = records.read_json(run_json, str(run_json))
        if data.get("pid") == os.getpid():
            return data
        if time.monotonic() > deadline:
            data["pid"] = os.getpid()
            records.write_json(run_json, data)
            return data
        time.sleep(0.02)


def supervise(run_dir: Path, lab_root: Path) -> int:
    run_json = run_dir / records.RUN
    data = _wait_for_pid(run_json)
    env = records.script_env()
    env[ENV_RUN] = env[ENV_RUN_DIR] = str(run_dir)
    for name, key in zip(LEGACY, (ENV_OUT, ENV_WORK)):
        (run_dir / name).mkdir(exist_ok=True)
        env[key] = str(run_dir / name)
    with (run_dir / records.LOG).open("a", encoding="utf-8") as log:
        log.write(f"lab-kit: started {data['started']}: {' '.join(data['command'])}\n")
        log.flush()
        try:
            code = subprocess.run(data["command"], cwd=lab_root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, check=False).returncode
        except OSError as exc:
            log.write(f"lab-kit: the command could not start: {exc}\n")
            code = 127
        ended = records.now()
        log.write(f"lab-kit: ended {ended} with exit code {code}\n")
    for name in LEGACY:  # an unused out/ or work/ leaves no trace
        folder = run_dir / name
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
    data = records.read_json(run_json, str(run_json))
    data["ended"] = ended
    data["exit"] = code
    if data.get("spend"):
        data["spent"] = _spent(run_dir)
    records.write_json(run_json, records.seal(run_dir, data))
    _publish(run_dir, lab_root)
    return code


def _publish(run_dir: Path, lab_root: Path) -> None:
    """Move the sealed run into the lab's store, if it names one. Never changes the run's exit code."""
    import yaml

    from . import lab as lab_mod
    from . import store
    try:
        raw = yaml.safe_load((lab_root / lab_mod.LAB_YAML).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict) or not raw.get("store"):
            return  # a lab without a store: the run was written in runs/ and stays there
        lab = lab_mod.load_at(lab_root)
        run = next(r for r in records.runs(lab, run_dir.parent.name) if r.run_id == run_dir.name)
        store.publish(lab, run)
    except Exception as exc:  # noqa: BLE001 - a failed move never changes the run's outcome
        if (run_dir / records.LOG).exists():
            store_note = f"lab-kit: not moved to the store: {exc}; `lab-kit publish --pending` retries\n"
            from . import store as store_mod
            store_mod.writable(run_dir)
            with (run_dir / records.LOG).open("a", encoding="utf-8") as log:
                log.write(store_note)
            data = records.read_json(run_dir / records.RUN, str(run_dir / records.RUN))
            records.write_json(run_dir / records.RUN, records.seal(run_dir, data))  # run.log grew: seal again


if __name__ == "__main__":
    raise SystemExit(supervise(Path(sys.argv[1]), Path(sys.argv[2])))
