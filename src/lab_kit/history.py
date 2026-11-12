"""Permanence: what was committed is still there. Git is the only witness to an edit that leaves the files consistent.

What is held is held from the commit that first holds it: the record is tamper-evident through git, not tamper-proof.
Before that commit nothing is held, and `lab check` says so.

- A committed `lock.json` is byte for byte its first committed version.
- `log.md`, `reviews.tsv` and `runs.tsv` only grow: no committed line is removed or changed.
- A `results.tsv` that a review has passed keeps every committed row.
- A settled decision keeps its `decided:`, its `about:` and its Decided text as first committed.
- A resource, once committed, is never removed. A metered resource's `granted`, `per_run` and `unit` change only together
  with `from`, which then names another settled decision that lists the resource. Its `other_use` rows only grow.
- None of these files is deleted.
"""
from __future__ import annotations

import os, re, subprocess

from . import record as R

GROW = ("log.md", "reviews.tsv", "results.tsv", "runs.tsv")


def git(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, errors="replace")
    return p.stdout.lstrip("﻿").replace("\r\n", "\n") if p.returncode == 0 else None


def committed(root):
    """Whether the lab is in git with at least one commit: without one, nothing is held."""
    return git(root, "rev-parse", "--is-inside-work-tree") is not None and git(root, "rev-parse", "HEAD") is not None


def subsequence(old, new):
    """The first line of `old` that `new` no longer holds in order, or None."""
    it = iter(new)
    for line in old:
        if not any(line == x for x in it):
            return line
    return None


def tables(text):
    try:
        return {k: v for k, v in R.tomllib.loads(text or "").items() if isinstance(v, dict)}
    except R.tomllib.TOMLDecodeError:
        return None


def resources(lab):
    """What changed in resources.toml that no decision covers, commit by commit and since the last one."""
    root, problems = lab.root, []
    if not committed(root):
        return problems
    bad = lambda what: problems.append(f"history: resources.toml: {what}")
    versions = [(f"in {c[:8]}", tables(git(root, "show", f"{c}:./resources.toml"))) for c in reversed((git(root, "log", "--format=%H", "--relative", "--", "resources.toml") or "").split())]
    if not versions:
        return problems
    now = tables(R.read(os.path.join(root, "resources.toml"))) if os.path.isfile(os.path.join(root, "resources.toml")) else {}
    versions = [v for v in versions + [("since the last commit", now)] if v[1] is not None]
    rows = lambda r: [(str(o.get("date")), o.get("amount"), str(o.get("what"))) for o in (r.get("other_use") if isinstance(r.get("other_use"), list) else []) if isinstance(o, dict)]
    for (_, old), (when, new) in zip(versions, versions[1:]):
        for name, a in old.items():
            b = new.get(name)
            if b is None:
                bad(f"{name} was removed {when}: a resource is never removed. One that is no longer used gets `retired = \"<why>\"`")
                continue
            if any(k in a for k in ("granted", "per_run")) and tuple(a.get(k) for k in ("granted", "per_run", "unit")) != tuple(b.get(k) for k in ("granted", "per_run", "unit")):
                d = lab.nodes.get(str(b.get("from")))
                if b.get("from") == a.get("from") or not d or d["type"] != "decision" or d["state"] != "decided" or name not in d["about"]:
                    bad(f"{name}: `granted`, `per_run` or `unit` changed {when}, and `from` does not name another settled decision: an amount changes out of a decision")
            lost = subsequence(rows(a), rows(b))
            if lost is not None:
                bad(f"{name}: an `other_use` row was removed or changed {when}: {lost[0]}, {lost[1]}, {lost[2][:40]!r}. Rows are only added")
    return sorted(set(problems))


def decisions(lab, added=None):
    """The settled decisions that are no longer as they were first committed settled."""
    root, problems = lab.root, []
    if not committed(root):
        return problems
    bad = lambda where, what: problems.append(f"history: {where}: {what}")
    if added is None:
        added = git(root, "log", "--format=", "--name-only", "--diff-filter=A", "--relative", "--", "decisions") or ""

    def settled(text):
        """What a decision's card says was decided, and about what, or None while it says nothing."""
        try:
            fm, slots, _ = R.parse(text)
        except Exception:
            return None
        if not isinstance(fm, dict) or fm.get("decided") is None:
            return None
        about = fm.get("about")
        return str(fm.get("decided")), sorted(str(i) for i in (about if isinstance(about, list) else [about] if about is not None else [])), R.flat(slots.get("Decided", ""))

    for path in sorted(p for p in added.split("\n") if re.fullmatch(r"decisions/D\d+-[^/]+\.md", p)):
        full = os.path.join(root, path)
        if not os.path.isfile(full):
            bad(path, "was committed and is gone; nothing recorded is removed")
            continue
        for c in reversed((git(root, "log", "--format=%H", "--relative", "--", path) or "").split()):  # oldest first
            was = settled(git(root, "show", f"{c}:./{path}") or "")
            if was:
                if settled(R.read(full)) != was:
                    bad(path, f"was settled in {c[:8]}, and its `decided:`, its `about:` or its Decided text has changed since; a change of mind is a new decision")
                break
    return problems


def uncommitted(lab):
    """The locks and the lists of runs that git does not hold yet as they are: until they are committed, nothing witnesses them."""
    root = lab.root
    if not committed(root):
        return []
    out = git(root, "status", "--porcelain", "--untracked-files=all", "--", ".") or ""
    paths = {line[3:].split(" -> ")[-1].strip('"') for line in out.splitlines() if len(line) > 3}
    top = (git(root, "rev-parse", "--show-prefix") or "").strip()
    paths = {p[len(top):] if top and p.startswith(top) else p for p in paths}
    found = []
    for x in lab.experiments:
        for name, what in (("lock.json", "its lock"), ("runs.tsv", "its list of runs")):
            if os.path.join(x["dir"], name) in paths:
                found.append(f"{x['id']}: {what} is not committed ({os.path.join(x['dir'], name)}): until it is, git does not hold it")
    return found


def check(lab):
    root, problems = lab.root, []
    bad = lambda where, what: problems.append(f"history: {where}: {what}")
    if not committed(root):
        return [], ["this lab is not in git, or has no commit: permanence against history was not checked, and nothing recorded is held yet"]
    added = git(root, "log", "--format=", "--name-only", "--diff-filter=A", "--relative", "--", ".") or ""
    reviewed = {os.path.join(x["dir"], "results.tsv") for x in lab.experiments if x["reviewed"]}
    for path in sorted({p for p in added.split("\n") if os.path.basename(p) in GROW + ("lock.json",)}):
        name, full = os.path.basename(path), os.path.join(root, path)
        commits = (git(root, "log", "--format=%H", "--relative", "--", path) or "").split()
        if not os.path.isfile(full):
            bad(path, "was committed and is gone; nothing recorded is removed")
            continue
        now = R.read(full)
        if name == "lock.json":
            first = git(root, "show", f"{commits[-1]}:./{path}")
            if first != now:
                bad(path, f"differs from the lock first committed in {commits[-1][:8]}; a changed plan is a new experiment")
        elif name != "results.tsv" or path in reviewed:
            for c in commits[:1] if name == "results.tsv" else commits:  # rows may change until a review passes them
                lost = subsequence((git(root, "show", f"{c}:./{path}") or "").splitlines(), now.splitlines())
                if lost is not None:
                    bad(path, f"a line committed in {c[:8]} is gone or changed: {lost[:70]!r}")
                    break

    problems += decisions(lab, added)
    problems += resources(lab)
    return sorted(set(problems)), []
