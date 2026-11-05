"""The background half of `lab-kit run`: run the lab's command, then seal its evidence.

`lab-kit run` starts this module as a detached process with the run's folder,
and writes its pid into `run.json`. This process waits for that, runs the command from the lab root with its output in
`run.log`, and when the command exits writes `MANIFEST.sha256` for `out/`,
`work.sha256` for `work/` when it exists, and the exit code and the end time into `run.json`.
When `lab.yaml` names a `store:`, it then publishes the run's raw output there (lab_kit.store); a
publish that fails is noted in `run.log` and leaves the run here for `lab-kit publish --pending`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import records

ENV_RUN = "LAB_RUN_DIR"
ENV_OUT = "LAB_OUT"
ENV_WORK = "LAB_WORK"


def _spent(out: Path) -> float | None:
    path = out / records.SPEND
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("spent")
    except (json.JSONDecodeError, AttributeError):
        return None
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


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
    env[ENV_RUN] = str(run_dir)
    env[ENV_OUT] = str(run_dir / "out")
    env[ENV_WORK] = str(run_dir / "work")
    with (run_dir / "run.log").open("a", encoding="utf-8") as log:
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
    run = records.RunRecord(data["protocol"], run_dir.name, run_dir, data)
    records.write_manifest(run)
    records.write_work_manifest(run)
    data = records.read_json(run_json, str(run_json))
    data["ended"] = ended
    data["exit"] = code
    if data.get("spend"):
        data["spent"] = _spent(run_dir / "out")
    records.write_json(run_json, data)
    _publish(run_dir, lab_root)
    return code


def _publish(run_dir: Path, lab_root: Path) -> None:
    """Publish the sealed run to the lab's store, if it names one. Never changes the run's exit code."""
    from . import lab as lab_mod
    from . import store
    from .errors import LabError
    try:
        lab = lab_mod.load_at(lab_root)
        if not lab.settings.store:
            return
        run = next(r for r in records.runs(lab, run_dir.parent.parent.name) if r.run_id == run_dir.name)
        store.publish(lab, run)
    except (LabError, OSError, StopIteration) as exc:
        if (run_dir / "run.log").exists():
            with (run_dir / "run.log").open("a", encoding="utf-8") as log:
                log.write(f"lab-kit: not published to the store: {exc}; `lab-kit publish --pending` retries\n")


if __name__ == "__main__":
    raise SystemExit(supervise(Path(sys.argv[1]), Path(sys.argv[2])))
