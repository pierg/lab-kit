"""The run store: where a finished run's raw output lives once it leaves the machine that ran it.

`lab.yaml` names it with `store:`, an absolute path such as `/labs/<lab>`. A run's raw output
(`work/` and `run.log`, which git ignores) is published to `<store>/<the run's folder from the lab
root>/`, so the record in git and its raw data share one path. Publishing copies into
`<store>/.incoming/`, checks every file against the committed `work.sha256` (no file missing, none
extra, none changed), renames the copy into place in one step, makes it read-only, writes
`store.json` beside `run.json`, and only then deletes the local copy. A run id already in the store
is never overwritten: a copy that verifies is accepted as published, one that does not is refused.

Where the store path is not mounted, set `LAB_STORE_HOST` to a host that mounts it: lab-kit then
copies with rsync over ssh and verifies on that host with `sha256sum`. The path is the same either way.
"""

from __future__ import annotations

import os
import shlex
import shutil
import socket
import stat
import subprocess
from pathlib import Path

from . import records
from .errors import LabError
from .lab import Lab

STORE_RECORD = "store.json"   # beside run.json: where the raw output went, and when; committed
ENV_HOST = "LAB_STORE_HOST"   # a host that mounts the store, for a machine that does not
RAW = ("work", "run.log")     # what is published: the gitignored half of a run


def root(lab: Lab) -> Path:
    if not lab.settings.store:
        raise LabError("lab.yaml names no `store:`; set it to the store's path, such as /labs/<lab>")
    return Path(lab.settings.store)


def find_run(lab: Lab, ref: str) -> records.RunRecord:
    """A run named `<slug>/<run id>`."""
    slug, sep, run_id = ref.strip("/").partition("/")
    if not sep or "/" in run_id:
        raise LabError(f"name a run as <slug>/<run id>, not `{ref}`")
    for run in records.runs(lab, slug):
        if run.run_id == run_id:
            return run
    raise LabError(f"experiments/{slug}/runs/{run_id}/ has no run.json")


def _rel(lab: Lab, run: records.RunRecord) -> str:
    return lab.rel(run.folder)


def _expected(run: records.RunRecord) -> dict[str, str]:
    path = run.folder / records.WORK_MANIFEST
    if not path.is_file():
        raise LabError(f"{run.path.rsplit('/', 1)[0]}/{records.WORK_MANIFEST} does not exist; "
                       "only a sealed run is published")
    return records.parse_hashes(path.read_text(encoding="utf-8"), records.WORK_MANIFEST)


def _problems(expected: dict[str, str], found: dict[str, str]) -> list[str]:
    out = [f"missing {p}" for p in sorted(set(expected) - set(found))]
    out += [f"extra {p}" for p in sorted(set(found) - set(expected))]
    out += [f"changed {p}" for p in sorted(set(expected) & set(found)) if expected[p] != found[p]]
    return out


def verify_local(run: records.RunRecord, dest: Path) -> list[str]:
    """What is wrong with the copy of `work/` under `dest`, against work.sha256: nothing when empty."""
    return _problems(_expected(run), records.tree_hashes(dest / "work", dest / "work"))


def _read_only(folder: Path) -> None:
    for path in sorted(folder.rglob("*"), reverse=True):
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    folder.chmod(folder.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def _writable(folder: Path) -> None:
    for path in [folder, *folder.rglob("*")]:
        path.chmod(path.stat().st_mode | stat.S_IWUSR)


def _incoming_name(run: records.RunRecord) -> str:
    return f"{run.slug}--{run.run_id}--{socket.gethostname()}--{os.getpid()}"


def _publish_local(lab: Lab, run: records.RunRecord, store: Path) -> str:
    dest = store / _rel(lab, run)
    if dest.exists():
        wrong = verify_local(run, dest)
        if wrong:
            raise LabError(f"{dest} exists and does not match work.sha256 ({'; '.join(wrong[:3])}); "
                           "a run in the store is never overwritten")
        return "already in the store, verified"
    incoming = store / ".incoming" / _incoming_name(run)
    if incoming.exists():
        _writable(incoming)
        shutil.rmtree(incoming)
    incoming.mkdir(parents=True)
    try:
        for name in RAW:
            src = run.folder / name
            if src.is_dir():
                shutil.copytree(src, incoming / name, symlinks=True)
            elif src.is_file():
                shutil.copy2(src, incoming / name)
        if not (incoming / "work").exists():
            (incoming / "work").mkdir()
        wrong = verify_local(run, incoming)
        if wrong:
            raise LabError(f"the copy in {incoming} does not match work.sha256 ({'; '.join(wrong[:3])}); "
                           "nothing was published")
        dest.parent.mkdir(parents=True, exist_ok=True)
        # A directory's own write bit is needed to rename it (its `..` changes), so lock after the move.
        os.rename(incoming, dest)
        _read_only(dest)
    except BaseException:
        if incoming.exists():
            _writable(incoming)
            shutil.rmtree(incoming, ignore_errors=True)
        raise
    return "copied and verified"


def _ssh(host: str, script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, script], capture_output=True, text=True)


def _publish_remote(lab: Lab, run: records.RunRecord, store: Path, host: str) -> str:
    dest = (store / _rel(lab, run)).as_posix()
    incoming = (store / ".incoming" / _incoming_name(run)).as_posix()
    q = shlex.quote
    manifest = q((run.folder / records.WORK_MANIFEST).read_text(encoding="utf-8"))
    # Verify on the host: every listed file hashes right, and no file is unlisted.
    check = (f"cd {{dir}}/work && printf %s {manifest} | sha256sum --quiet -c - >/dev/null && "
             f"test \"$(find . -type f | wc -l)\" -eq {len(_expected(run))}")
    if _ssh(host, f"test -e {q(dest)}").returncode == 0:
        if _ssh(host, check.format(dir=q(dest))).returncode == 0:
            return f"already in the store on {host}, verified"
        raise LabError(f"{host}:{dest} exists and does not match work.sha256; a run in the store is never overwritten")
    if _ssh(host, f"rm -rf {q(incoming)} && mkdir -p {q(incoming)}/work").returncode:
        raise LabError(f"cannot reach the store on {host} (ssh {host})")
    sources = [str(run.folder / n) for n in RAW if (run.folder / n).exists()]
    copied = subprocess.run(["rsync", "-a", *sources, f"{host}:{incoming}/"], capture_output=True, text=True)
    if copied.returncode:
        raise LabError(f"rsync to {host}:{incoming} failed: {copied.stderr.strip()[-200:]}")
    done = _ssh(host, f"{check.format(dir=q(incoming))} && mkdir -p {q(str(Path(dest).parent))} && "
                      f"mv -T {q(incoming)} {q(dest)} && chmod -R a-w {q(dest)}")
    if done.returncode:
        _ssh(host, f"chmod -R u+w {q(incoming)}; rm -rf {q(incoming)}")
        raise LabError(f"the copy on {host} does not match work.sha256; nothing was published")
    return f"copied to {host} and verified"


def publish(lab: Lab, run: records.RunRecord, keep: bool = False) -> list[str]:
    """Publish one finished run's raw output; then, unless `keep`, delete the local copy."""
    if not run.ended:
        raise LabError(f"{_rel(lab, run)} has not ended; only a sealed run is published")
    store = root(lab)
    host = os.environ.get(ENV_HOST, "").strip()
    if not (run.folder / "work").exists() and not (run.folder / STORE_RECORD).exists():
        raise LabError(f"{_rel(lab, run)}/work/ is not here to publish")
    if (run.folder / STORE_RECORD).exists() and not (run.folder / "work").exists():
        return [f"{_rel(lab, run)}: already published"]
    if store.is_dir() and not host:
        how = _publish_local(lab, run, store)
        where = str(store / _rel(lab, run))
    elif host:
        how = _publish_remote(lab, run, store, host)
        where = f"{host}:{store / _rel(lab, run)}"
    else:
        raise LabError(f"the store {store} is not mounted here; set {ENV_HOST} to a host that mounts it")
    records.write_json(run.folder / STORE_RECORD, {
        "store": str(store / _rel(lab, run)), "files": len(_expected(run)),
        "published": records.now(), "by": socket.gethostname(),
    })
    out = [f"{_rel(lab, run)}: {how} at {where}", f"wrote {_rel(lab, run)}/{STORE_RECORD}"]
    if not keep:
        for name in RAW:
            path = run.folder / name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
        out.append(f"deleted the local {_rel(lab, run)}/work/ and run.log")
    return out


def pending(lab: Lab) -> list[records.RunRecord]:
    """Ended runs whose raw output is still only here."""
    return [r for r in records.runs(lab) if r.ended and (r.folder / "work").exists()
            and (r.folder / records.WORK_MANIFEST).exists()]


def fetch(lab: Lab, run: records.RunRecord) -> list[str]:
    """Copy a published run's raw output back into its run folder, writable, and verify it."""
    store = root(lab)
    src = store / _rel(lab, run)
    host = os.environ.get(ENV_HOST, "").strip()
    if (run.folder / "work").exists() and not verify_local(run, run.folder):
        return [f"{_rel(lab, run)}/work/ is here and verifies"]
    tmp = run.folder / ".fetch"
    if tmp.exists():
        _writable(tmp)
        shutil.rmtree(tmp)
    tmp.mkdir()
    if store.is_dir() and not host:
        if not src.is_dir():
            raise LabError(f"{src} does not exist: this run was never published")
        for name in RAW:
            if (src / name).is_dir():
                shutil.copytree(src / name, tmp / name, symlinks=True)
            elif (src / name).is_file():
                shutil.copy2(src / name, tmp / name)
    elif host:
        got = subprocess.run(["rsync", "-a", f"{host}:{src.as_posix()}/", f"{tmp}/"], capture_output=True, text=True)
        if got.returncode:
            raise LabError(f"rsync from {host}:{src} failed: {got.stderr.strip()[-200:]}")
    else:
        raise LabError(f"the store {store} is not mounted here; set {ENV_HOST} to a host that mounts it")
    _writable(tmp)
    wrong = verify_local(run, tmp)
    if wrong:
        shutil.rmtree(tmp)
        raise LabError(f"the copy from the store does not match work.sha256 ({'; '.join(wrong[:3])})")
    for name in RAW:
        target = run.folder / name
        if target.is_dir():
            shutil.rmtree(target)
        if (tmp / name).exists():
            os.rename(tmp / name, target)
    shutil.rmtree(tmp)
    return [f"{_rel(lab, run)}: fetched from the store and verified against work.sha256"]


def verify(lab: Lab, run: records.RunRecord) -> list[str]:
    """Check the store's copy of a run against work.sha256. Raises when it does not match."""
    store = root(lab)
    host = os.environ.get(ENV_HOST, "").strip()
    dest = store / _rel(lab, run)
    if host:
        expected = _expected(run)
        q = shlex.quote
        manifest = q((run.folder / records.WORK_MANIFEST).read_text(encoding="utf-8"))
        script = (f"cd {q(dest.as_posix())}/work && printf %s {manifest} | sha256sum --quiet -c - >/dev/null && "
                  f"test \"$(find . -type f | wc -l)\" -eq {len(expected)}")
        if _ssh(host, script).returncode:
            raise LabError(f"{host}:{dest} is missing or does not match work.sha256")
        return [f"{_rel(lab, run)}: the store's copy on {host} matches work.sha256"]
    if not dest.is_dir():
        raise LabError(f"{dest} does not exist: this run was never published")
    wrong = verify_local(run, dest)
    if wrong:
        raise LabError(f"{dest} does not match work.sha256: {'; '.join(wrong[:5])}")
    return [f"{_rel(lab, run)}: the store's copy matches work.sha256"]
