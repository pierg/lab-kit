"""Permanence: what was committed is still there. Git is the only witness to an edit that leaves the files consistent.

What is held is held from the commit that first holds it: the record is tamper-evident through git, not tamper-proof.
Before that commit nothing is held, and `lab check` says so.

Only the lab's own record is read, at its places under the lab's root: `log.md`, `resources.toml`,
`decisions/D<n>-<name>.md`, and each experiment's `lock.json`, `runs.tsv`, `results.tsv` and `reviews.tsv` under
`goals/G<n>-<name>/Q<n>-<name>/<n>-<name>/`. What the repository holds or once held anywhere else is not the lab's.
A file is known by the numbers in its path and not by the words, so a folder renamed after a reworded title is the
same place: what was committed under the old name is held under the new one.

- A committed `lock.json` is byte for byte its first committed version.
- `log.md`, `reviews.tsv` and `runs.tsv` only grow: no committed line is removed or changed.
- A `results.tsv` that a review has passed keeps every committed row. Once a results review that passed is committed
  together with the rows it read, those rows stay, whatever the card and the file say later. Rows committed while
  the last passed review was of other rows, such as a draft row added after it, were never reviewed and are not held.
- A settled decision keeps its `decided:`, its `about:` and its Decided text as first committed.
- A resource, once committed, is never removed. A metered resource's `granted`, `per_run` and `unit` change only together
  with `from`, which then names another settled decision that lists the resource. Its `other_use` rows only grow.
- None of these files is deleted, and none changes its number.
"""
from __future__ import annotations

import glob, os, re, subprocess

from . import record as R

GROW = ("log.md", "reviews.tsv", "results.tsv", "runs.tsv")
STEP = re.compile(r"goals/G(\d+)-[^/]+/Q(\d+)-[^/]+/(\d+)-[^/]+/(lock\.json|reviews\.tsv|results\.tsv|runs\.tsv)")
DECISION = re.compile(r"decisions/D(\d+)-[^/]+\.md")


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


def place(path):
    """Where a path, from the lab's root, sits in the lab's record: `log.md`, `D4`, `G1.Q2.3/lock.json`. None when it is
    not a file of the record. The numbers place a file and the words do not, so a renamed folder is the same place."""
    if path == "log.md":
        return path
    m = STEP.fullmatch(path)
    if m:
        return f"G{int(m.group(1))}.Q{int(m.group(2))}.{int(m.group(3))}/{m.group(4)}"
    m = DECISION.fullmatch(path)
    return f"D{int(m.group(1))}" if m else None


def held(root, *where):
    """Every committed version of the lab's record under these paths, by place: {place: [(commit, path)]}, oldest
    first. A rename is read as what it is in git, the old path leaving and the new one arriving, so both names of
    one place are in its list whether or not git would have paired them."""
    out = git(root, "-c", "core.quotepath=off", "log", "--topo-order", "-m", "--no-renames", "--format=commit %H", "--name-status", "--relative", "--", *where) or ""
    found, commit = {}, None
    for line in out.split("\n"):
        if line.startswith("commit "):
            commit = line[7:].strip()
        elif "\t" in line and not line.startswith("D"):  # a path that left in this commit has no version in it
            path = line.split("\t", 1)[1]
            if place(path) and (commit, path) not in found.setdefault(place(path), []):
                found[place(path)].append((commit, path))
    return {k: v[::-1] for k, v in found.items()}


def present(root):
    """The files of the record that are in the lab now, by place: {place: [path]}."""
    found = {}
    for pattern in ("log.md", "decisions/*", "goals/*/*/*/*"):
        for full in sorted(glob.glob(os.path.join(glob.escape(root), pattern))):
            path = os.path.relpath(full, root).replace(os.sep, "/")
            if place(path) and os.path.isfile(full):
                found.setdefault(place(path), []).append(path)
    return found


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


def decisions(lab, versions=None, now=None):
    """The settled decisions that are no longer as they were first committed settled."""
    root, problems = lab.root, []
    if not committed(root):
        return problems
    bad = lambda where, what: problems.append(f"history: {where}: {what}")
    versions = held(root, "decisions") if versions is None else versions
    now = present(root) if now is None else now

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

    for where, commits in sorted(versions.items()):
        if not DECISION.fullmatch(commits[-1][1]):
            continue
        if where not in now:
            bad(commits[-1][1], "was committed and is gone; nothing recorded is removed")
            continue
        for c, path in commits:  # oldest first, under whichever name it had then
            was = settled(git(root, "show", f"{c}:./{path}") or "")
            if was:
                mine = path if path in now[where] else now[where][0]
                if settled(R.read(os.path.join(root, mine))) != was:
                    bad(mine, f"was settled in {c[:8]}" + ("" if mine == path else f", as {path}") + ", and its `decided:`, its `about:` or its Decided text has changed since; a change of mind is a new decision")
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
    notes = []
    if (git(root, "rev-parse", "--is-shallow-repository") or "").strip() == "true":
        notes.append("this repository is a shallow clone: the history check needs every commit, and compared the record with the few that are here. "
                     "Fetch the full history (`git fetch --unshallow`; in CI, `fetch-depth: 0`)")
    versions, now = held(root, "log.md", "decisions", "goals"), present(root)
    reviewed = {os.path.join(x["dir"], "results.tsv") for x in lab.experiments if x["reviewed"]}
    for where, commits in sorted(versions.items()):
        name = os.path.basename(commits[-1][1])
        if name not in GROW + ("lock.json",):
            continue  # a decision, held below
        if where not in now:
            bad(commits[-1][1], "was committed and is gone; nothing recorded is removed")
            continue
        mine = lambda path: path if path in now[where] else now[where][0]  # the same file, under the name it has now
        named = lambda path: "" if mine(path) == path else f", as {path}"
        if name == "lock.json":
            c, path = commits[0]
            if git(root, "show", f"{c}:./{path}") != R.read(os.path.join(root, mine(path))):
                bad(mine(path), f"differs from the lock first committed in {c[:8]}{named(path)}; a changed plan is a new experiment")
            continue
        if name == "results.tsv":  # rows may change until a review passes them
            commits = commits[-1:] if mine(commits[-1][1]) in reviewed else []
        for c, path in reversed(commits):
            lost = subsequence((git(root, "show", f"{c}:./{path}") or "").splitlines(), R.read(os.path.join(root, mine(path))).splitlines())
            if lost is not None:
                bad(mine(path), f"a line committed in {c[:8]}{named(path)} is gone or changed: {lost[:70]!r}")
                break

    # A results review that passed, once committed with the rows it read, holds those rows: emptying the file with
    # Found and Means leaves the experiment unreviewed now, and the rows are held all the same. The review is bound to
    # what it read by its `of`, the hash `lab review` wrote: of results.tsv and of the seal of the finished run, both
    # as that commit has them. Rows in a commit whose last passed review is of other rows were never reviewed.
    for where, commits in sorted(versions.items()):
        if os.path.basename(commits[-1][1]) != "reviews.tsv":
            continue
        rows, read = where.rsplit("/", 1)[0] + "/results.tsv", set()
        if rows not in now:
            continue  # never committed, so nothing is held; or committed and gone, which is said above
        for c, path in reversed(commits + versions.get(rows, [])):  # every commit that touched the reviews or the rows
            folder = os.path.dirname(path)
            if c in read:
                continue
            read.add(c)
            passed = [r for r in R.table(git(root, "show", f"{c}:./{folder}/reviews.tsv") or "", R.COLUMNS["reviews.tsv"]) if r.get("stage") == "results" and r.get("verdict") == "pass"]
            was = git(root, "show", f"{c}:./{folder}/results.tsv") if passed else None
            if was is None:
                continue
            listed = [l.split("\t") for l in (git(root, "show", f"{c}:./{folder}/runs.tsv") or "").split("\n")]
            seals = [l[5] for l in listed if len(l) >= 6 and l[1] == "run" and l[2] == "ended" and l[4] == "0"]  # the finished run, as that commit lists it
            if passed[-1].get("of") not in {R.text_hash(R.text_hash(was) + str(seal))[:16] for seal in seals}:
                continue  # the last review that passed there read other rows than these
            lost = subsequence(was.splitlines(), R.read(os.path.join(root, now[rows][0])).splitlines())
            if lost is not None:
                bad(now[rows][0], f"a row that a review had passed in {c[:8]} is gone or changed: {lost[:70]!r}. Reviewed rows stay; a different result is a new experiment")
                break

    problems += decisions(lab, versions, now)
    problems += resources(lab)
    return sorted(set(problems)), notes
