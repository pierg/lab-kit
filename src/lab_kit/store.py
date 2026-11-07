"""The run store: where every run's folder lives once its run ends.

`lab.yaml` names it with `store:`, an absolute path such as `/labs/<lab>`. The lab's `runs/` is a link
to `<store>/runs`, so every machine that mounts the store reads every run at the same path. A run is
written on local disk, under `.lab/running/<experiment>/<run id>/`, and sealed when its command
exits (run.json records every file's hash). It then moves into the store: a copy into
`<store>/.incoming/`, checked file by file against run.json, renamed into
`<store>/runs/<experiment>/<run id>/` in one step and made read-only; only then is the local copy
deleted. A run already in the store is never overwritten: a copy there that verifies counts as
moved, one that does not is refused.

Where the store is not mounted, set `LAB_STORE_HOST` to a host that mounts it: lab-kit then copies with
rsync over ssh and verifies on that host with `sha256sum`. `lab-kit fetch` copies a run back from it
into `.lab/fetched/`, verified, for a machine without the mount.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import stat
import subprocess
from pathlib import Path

from . import records
from .errors import LabError
from .lab import FETCHED, RUNNING, RUNS, Lab

ENV_HOST = "LAB_STORE_HOST"   # a host that mounts the store, for a machine that does not


def root(lab: Lab) -> Path:
    if not lab.settings.store:
        raise LabError("lab.yaml names no `store:`; set it to the store's path, such as /labs/<lab>")
    return Path(lab.settings.store)


def runs_root(lab: Lab) -> Path:
    return root(lab) / RUNS


def ensure_link(lab: Lab) -> list[str]:
    """Make `runs/` a link to `<store>/runs` when the lab names a store and `runs/` is not there yet."""
    if not lab.settings.store:
        return []
    link = lab.runs_dir
    target = runs_root(lab)
    if link.is_symlink():
        if Path(os.readlink(link)) == target:
            return []
        raise LabError(f"runs/ links to {os.readlink(link)}, not {target}; fix the link by hand")
    if link.exists():
        raise LabError(f"runs/ is a folder here, but lab.yaml names the store {lab.settings.store}: "
                       "move its runs into the store (`lab-kit migrate`), then remove it")
    link.symlink_to(target, target_is_directory=True)
    return [f"linked runs/ to {target}"]


def _read_only(folder: Path) -> None:
    for path in sorted(folder.rglob("*"), reverse=True):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    folder.chmod(folder.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def writable(folder: Path) -> None:
    for path in [folder, *folder.rglob("*")]:
        if not path.is_symlink():
            path.chmod(path.stat().st_mode | stat.S_IWUSR)


def remove(folder: Path) -> None:
    if folder.exists():
        writable(folder)
        shutil.rmtree(folder)


def _incoming_name(slug: str, run_id: str) -> str:
    return f"{slug}--{run_id}--{socket.gethostname()}--{os.getpid()}"


def _verify(folder: Path, data: dict) -> list[str]:
    """What is wrong with a copy of a run in `folder` against the sealed run.json `data`."""
    copy = folder / records.RUN
    if not copy.is_file():
        return ["missing run.json"]
    try:
        theirs = json.loads(copy.read_text(encoding="utf-8"))
    except ValueError:
        return ["run.json is not valid JSON"]
    if theirs.get("seal") != data.get("seal"):
        return ["its run.json records another seal"]
    return records.seal_problems(folder, data)


def place(store_runs: Path, slug: str, run_id: str, source: Path, data: dict) -> str:
    """Copy a sealed run's folder into `<store_runs>/<slug>/<run_id>/`, verified, read-only. The source stays."""
    dest = store_runs / slug / run_id
    if dest.exists():
        wrong = _verify(dest, data)
        if wrong:
            raise LabError(f"{dest} exists and does not match the run's seal ({'; '.join(wrong[:3])}); "
                           "a run in the store is never overwritten")
        return "already in the store, verified"
    incoming = store_runs.parent / ".incoming" / _incoming_name(slug, run_id)
    remove(incoming)
    incoming.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source, incoming, symlinks=False)  # a link's bytes, never the link
        writable(incoming)
        wrong = _verify(incoming, data)
        if wrong:
            raise LabError(f"the copy in {incoming} does not match the run's seal ({'; '.join(wrong[:3])}); "
                           "nothing was moved")
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(incoming, dest)  # a directory's own write bit is needed to rename it, so lock after
        except OSError:
            if dest.is_dir() and not _verify(dest, data):
                remove(incoming)
                return "already in the store, verified"
            raise
        _read_only(dest)
    except BaseException:
        remove(incoming)
        raise
    return "copied and verified"


def _ssh(host: str, script: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, script], input=stdin, capture_output=True, text=True)


def _remote_check(folder: str, files: dict[str, str]) -> tuple[str, str]:
    """A shell line that verifies a run's folder against its file list (on stdin): every file, none extra."""
    q = shlex.quote
    count = len(files) + 1  # and run.json
    line = (f"cd {q(folder)} && sha256sum --quiet --strict -c - >/dev/null && test -f {records.RUN} && "
            f"test \"$(find . -type f | wc -l)\" -eq {count} && test -z \"$(find . ! -type f ! -type d)\"")
    return line, records.format_hashes(files)


def _place_remote(lab: Lab, run: records.RunRecord, host: str) -> str:
    dest = (runs_root(lab) / run.slug / run.run_id).as_posix()
    incoming = (root(lab) / ".incoming" / _incoming_name(run.slug, run.run_id)).as_posix()
    q = shlex.quote
    check, manifest = _remote_check(dest, run.data["files"])
    if _ssh(host, f"test -e {q(dest)}").returncode == 0:
        if _ssh(host, check, manifest).returncode == 0:
            return f"already in the store on {host}, verified"
        raise LabError(f"{host}:{dest} exists and does not match the run's seal; a run in the store is never overwritten")
    if _ssh(host, f"rm -rf {q(incoming)} && mkdir -p {q(incoming)}").returncode:
        raise LabError(f"cannot reach the store on {host} (ssh {host})")
    copied = subprocess.run(["rsync", "-aL", f"{run.folder}/", f"{host}:{incoming}/"], capture_output=True, text=True)
    if copied.returncode:
        raise LabError(f"rsync to {host}:{incoming} failed: {copied.stderr.strip()[-200:]}")
    check, manifest = _remote_check(incoming, run.data["files"])
    if _ssh(host, check, manifest).returncode:
        _ssh(host, f"chmod -R u+w {q(incoming)}; rm -rf {q(incoming)}")
        raise LabError(f"the copy on {host} does not match the run's seal; nothing was moved")
    done = _ssh(host, f"mkdir -p {q(str(Path(dest).parent))} && mv -T {q(incoming)} {q(dest)} && chmod -R a-w {q(dest)}")
    if done.returncode:
        _ssh(host, f"chmod -R u+w {q(incoming)}; rm -rf {q(incoming)}")
        raise LabError(f"cannot move the copy into place on {host}: {done.stderr.strip()[-200:]}")
    return f"copied to {host} and verified"


def mounted(store: Path) -> bool:
    """The store is here: its folder exists, or one of its ancestors (not `/`) is a mount point.

    An empty mount point left by a mount that failed is not taken for the store, so nothing is
    ever written onto the local disk under it.
    """
    try:
        if store.is_dir():
            return True
        return any(os.path.ismount(p) for p in store.parents if p != Path(p.anchor))
    except OSError:
        return False


def publish(lab: Lab, run: records.RunRecord, keep: bool = False) -> list[str]:
    """Move one ended, sealed run from `.lab/running/` into the store; unless `keep`, delete the local copy."""
    if not run.ended:
        raise LabError(f"{run.base} has not ended; only a sealed run moves to the store")
    if not run.base.startswith(RUNNING + "/"):
        return [f"{run.base}: already in the store"]
    wrong = records.seal_problems(run.folder, run.data)
    if wrong:
        raise LabError(f"{run.base} does not match its own seal ({'; '.join(wrong[:3])}); nothing was moved")
    store = root(lab)
    host = os.environ.get(ENV_HOST, "").strip()
    if not host and mounted(store):
        how = place(runs_root(lab), run.slug, run.run_id, run.folder, run.data)
        where = str(runs_root(lab) / run.slug / run.run_id)
    elif host:
        how = _place_remote(lab, run, host)
        where = f"{host}:{runs_root(lab) / run.slug / run.run_id}"
    else:
        raise LabError(f"the store {store} is not mounted here; set {ENV_HOST} to a host that mounts it")
    out = [f"{run.base}: {how} at {where}"]
    if not keep:
        remove(run.folder)
        parent = run.folder.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
        out.append(f"deleted the local {run.base}/")
    return out


def pending(lab: Lab) -> list[records.RunRecord]:
    """Ended runs still on local disk, under `.lab/running/`."""
    return [r for r in records.runs(lab) if r.ended and r.base.startswith(RUNNING + "/")]


def fetch(lab: Lab, ref: str) -> list[str]:
    """Copy a run from the store into `.lab/fetched/`, verified, on a machine that does not mount the store."""
    slug, sep, run_id = ref.strip("/").removeprefix("runs/").partition("/")
    if not sep:
        raise LabError(f"name the run as <experiment>/<run id>, not `{ref}`")
    if lab.runs_here() and (lab.runs_dir / slug / run_id / records.RUN).is_file():
        return [f"runs/{slug}/{run_id} is here already: the store is mounted"]
    host = os.environ.get(ENV_HOST, "").strip()
    if not host:
        raise LabError(f"runs/ does not resolve here; set {ENV_HOST} to a host that mounts the store")
    src = (runs_root(lab) / slug / run_id).as_posix()
    dest = lab.root / FETCHED / slug / run_id
    tmp = dest.with_name(dest.name + ".part")
    remove(tmp)
    tmp.parent.mkdir(parents=True, exist_ok=True)
    got = subprocess.run(["rsync", "-a", f"{host}:{src}/", f"{tmp}/"], capture_output=True, text=True)
    if got.returncode:
        remove(tmp)
        raise LabError(f"rsync from {host}:{src} failed: {got.stderr.strip()[-200:]}")
    writable(tmp)
    data = records.read_json(tmp / records.RUN, f"{src}/{records.RUN}")
    wrong = records.seal_problems(tmp, data)
    if wrong:
        remove(tmp)
        raise LabError(f"the copy from the store does not match its seal ({'; '.join(wrong[:3])})")
    remove(dest)
    os.rename(tmp, dest)
    return [f"fetched runs/{slug}/{run_id} into {FETCHED}/{slug}/{run_id}, verified against its seal"]


def verify(lab: Lab, ref: str) -> list[str]:
    """Check a run against its seal: here when runs/ resolves, else on LAB_STORE_HOST. Raises when it fails."""
    host = os.environ.get(ENV_HOST, "").strip()
    try:
        run = records.find_run(lab, ref)
    except LabError:
        if not host or not lab.settings.store:
            raise
        slug, _, run_id = ref.strip("/").removeprefix("runs/").partition("/")
        folder = (runs_root(lab) / slug / run_id).as_posix()
        got = _ssh(host, f"cat {shlex.quote(folder)}/{records.RUN}")
        if got.returncode:
            raise LabError(f"{host}:{folder}/{records.RUN} does not exist")
        data = json.loads(got.stdout)
        check, manifest = _remote_check(folder, data.get("files") or {})
        if data.get("seal") != records.seal_of(data) or _ssh(host, check, manifest).returncode:
            raise LabError(f"{host}:{folder} does not match its seal")
        return [f"runs/{slug}/{run_id}: the store's copy on {host} matches its seal"]
    wrong = records.seal_problems(run.folder, run.data)
    if wrong:
        raise LabError(f"{run.base} does not match its seal: {'; '.join(wrong[:5])}")
    return [f"{run.base}: matches its seal ({len(run.data['files'])} files)"]
