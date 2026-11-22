"""Permanence: what was committed is still there. Git is the only witness to an edit that leaves the files consistent.

What is held is held from the commit that first holds it: the record is tamper-evident through git, not tamper-proof.
Before that commit nothing is held, and `lab check` says so.

Only the lab's own record is read, at its places under the lab's root: `log.md`, `struck.tsv`, `resources.toml`,
`decisions/D<n>-<name>.md`, and each experiment's `lock.json`, `runs.tsv`, `results.tsv` and `reviews.tsv` under
`goals/G<n>-<name>/Q<n>-<name>/<n>-<name>/`. What the repository holds or once held anywhere else is not the lab's.
A file is known by the numbers in its path and not by the words, so a folder renamed after a reworded title is the
same place: what was committed under the old name is held under the new one.

- A committed `lock.json` is byte for byte its first committed version.
- `log.md`, `reviews.tsv` and `runs.tsv` only grow: no committed line is removed or changed. Spaces at the end of a
  line of `log.md` are not part of it.
- A `results.tsv` that a review has passed keeps every committed row. Once a results review that passed is committed
  together with the rows it read, those rows stay, whatever the card and the file say later. Rows committed while
  the last passed review was of other rows, such as a draft row added after it, were never reviewed and are not held.
- A settled decision is a draft until something acts on it: a mission that carries it is launched, or a run starts of a
  step its `order:` names, of a step under what came out of it, or of a step on a resource whose amounts it set. From
  then it is locked, and keeps its `decided:`, `about:`, `parks:`, `unparks:`, `drops:`,
  `order:`, `folds:` and Decided text as committed before the first commit that records the act (the last commit,
  while none does). What locks it is read from what git holds (`held_scope`), so no later edit takes it back. A draft may be revised, never
  reopened, or folded into another decision with `folds:`; then its file goes, and its number is never used again.
- A resource, once committed, is never removed. A metered resource's `granted`, `per_run` and `unit` change only together
  with `from`, which then names another settled decision that lists the resource. Its `other_use` rows only grow.
- `struck.tsv` only grows. A decision it lists was about how the lab works: its file and its lines in `log.md` may
  go, if its last committed version holds, parks, brings back, drops, orders and folds nothing, nothing came out of
  it and nothing acted on it.
- None of these files is deleted, save a draft decision folded into another and a struck one, and none changes its
  number.
"""
from __future__ import annotations

import glob, json, os, re, subprocess

from . import record as R

GROW = ("log.md", "reviews.tsv", "results.tsv", "runs.tsv", "struck.tsv")
STEP = re.compile(r"goals/G(\d+)-[^/]+/Q(\d+)-[^/]+/(\d+)-[^/]+/(lock\.json|reviews\.tsv|results\.tsv|runs\.tsv)")
DECISION = re.compile(r"decisions/D(\d+)-[^/]+\.md")


def git(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, errors="replace")
    return p.stdout.lstrip("﻿").replace("\r\n", "\n") if p.returncode == 0 else None


def committed(root):
    """Whether the lab is in git with at least one commit: without one, nothing is held."""
    return git(root, "rev-parse", "--is-inside-work-tree") is not None and git(root, "rev-parse", "HEAD") is not None


def subsequence(old, new, same=lambda a, b: a == b):
    """The first line of `old` that `new` no longer holds in order, or None."""
    it = iter(new)
    for line in old:
        if not any(same(line, x) for x in it):
            return line
    return None


def place(path):
    """Where a path, from the lab's root, sits in the lab's record: `log.md`, `D4`, `G1.Q2.3/lock.json`. None when it is
    not a file of the record. The numbers place a file and the words do not, so a renamed folder is the same place."""
    if path in ("log.md", "struck.tsv"):
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
    for pattern in ("log.md", "struck.tsv", "decisions/*", "goals/*/*/*/*"):
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
                d = lab.nodes.get(lab.folded.get(str(b.get("from")), str(b.get("from"))))  # a draft folded into another is read as that one
                if b.get("from") == a.get("from") or not d or d["type"] != "decision" or d["state"] != "done" or name not in d["about"]:
                    bad(f"{name}: `granted`, `per_run` or `unit` changed {when}, and `from` does not name another settled decision: an amount changes out of a decision")
            elif "from" in a and str(a.get("from")) != str(b.get("from")) and lab.folded.get(str(a.get("from"))) != str(b.get("from")):
                bad(f"{name}: `from` changed {when} from {a.get('from')} to {b.get('from')} with its amounts unchanged: it names the decision that set them, and changes only with them, or to the decision that folded it")
            lost = subsequence(rows(a), rows(b))
            if lost is not None:
                bad(f"{name}: an `other_use` row was removed or changed {when}: {lost[0]}, {lost[1]}, {lost[2][:40]!r}. Rows are only added")
    return sorted(set(problems))


def card(text):
    """A card's front matter and slots as a version in git has them, or (None, {})."""
    try:
        fm, slots, _ = R.parse(text)
    except Exception:
        return None, {}
    return (fm, slots) if isinstance(fm, dict) else (None, {})


def ids(v):
    return [str(i) for i in (v if isinstance(v, list) else [v] if v is not None else [])]


def held_scope(lab):
    """What git holds about where things came from, which no later edit takes back: each goal's and question's `from:`
    as first committed, each resource's every `from`, and each decision's every committed `order:`. Read once per lab;
    empty outside git."""
    root, out = lab.root, {"from": {}, "granted": {}, "orders": {}}
    if not committed(root):
        return out
    # It depends only on the commits, so it is kept per commit, outside the lab: reading it costs a git call per card.
    head = (git(root, "rev-parse", "HEAD") or "").strip()
    top = (git(root, "rev-parse", "--show-prefix") or "").strip()
    cache = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "lab-kit", "held",
                         R.text_hash(os.path.realpath(root) + "|" + top + "|" + head + "|" + str(sorted(n["path"] for n in lab.goals + lab.questions)))[:32] + ".json")
    try:
        kept = json.load(open(cache))
        return {"from": kept["from"], "granted": {k: set(v) for k, v in kept["granted"].items()}, "orders": {k: set(v) for k, v in kept["orders"].items()}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    for n in lab.goals + lab.questions:
        names = (git(root, "log", "--reverse", "--follow", "--name-only", "--format=%H", "--", n["path"]) or "").split()  # each commit, then the name it had there
        if len(names) >= 2:
            fm, _ = card(git(root, "show", f"{names[0]}:{names[1]}") or "")  # a name git prints is from the repository's top
            if fm and fm.get("from") is not None:
                out["from"][n["id"]] = str(fm.get("from"))
    for c in (git(root, "log", "--format=%H", "--relative", "--", "resources.toml") or "").split():
        for name, r in (tables(git(root, "show", f"{c}:./resources.toml")) or {}).items():
            if isinstance(r, dict) and r.get("from") is not None:
                out["granted"].setdefault(name, set()).add(str(r.get("from")))
    for where, commits in held(root, "decisions").items():
        m = DECISION.fullmatch(commits[-1][1])
        if m:
            for c, path in commits:
                fm, _ = card(git(root, "show", f"{c}:./{path}") or "")
                if fm and fm.get("decided") is not None:
                    out["orders"].setdefault(f"D{int(m.group(1))}", set()).update(ids(fm.get("order")))
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache + ".tmp", "w") as f:
            json.dump({"from": out["from"], "granted": {k: sorted(v) for k, v in out["granted"].items()}, "orders": {k: sorted(v) for k, v in out["orders"].items()}}, f)
        os.replace(cache + ".tmp", cache)
    except OSError:
        pass  # no place to keep it: it is read again next time
    return out


STEERS = ("holds", "parks", "unparks", "drops", "order", "folds")


def steered(lab, ident, versions=None):
    """How a decision ever steered the research, as git holds it: a key of `STEERS` that any committed version of its
    card filled, a goal or a question that came out of it, a resource whose amounts it set, a line about it in any
    committed `log.md` that is not its `decision` line (a mission that carried it). Empty when it never did, or when
    the lab is not in git."""
    root, found = lab.root, []
    if not committed(root):
        return found
    versions = held(root, "decisions") if versions is None else versions
    keys = set()
    for c, path in versions.get(ident, []):
        fm, _ = card(git(root, "show", f"{c}:./{path}") or "")
        keys |= {key for key in STEERS if fm and ids(fm.get(key))}
    if lab.held["orders"].get(ident):
        keys.add("order")
    found += [f"its `{key}:`" for key in STEERS if key in keys]
    found += [f"{i} came out of it" for i in sorted(i for i, f in lab.held["from"].items() if f == ident)]
    found += [f"the amounts of {name}" for name in sorted(n for n, froms in lab.held["granted"].items() if ident in froms)]
    other = "|".join(k for k in R.KINDS if k != "decision")
    if (git(root, "log", "-1", "--format=%H", "-G", rf"^- ([0-9]{{2}}:[0-9]{{2}} \| )?{ident} \| ({other}) \|", "--", "log.md") or "").strip():
        found.append("a line about it in log.md other than its decision (a mission that carried it)")
    return found


def decisions(lab, versions=None, now=None):
    """The locked decisions that are no longer as they were when something first acted on them, and the decisions that
    are gone without another decision folding them in while they were still drafts."""
    root, problems = lab.root, []
    if not committed(root):
        return problems
    bad = lambda where, what: problems.append(f"history: {where}: {what}")
    struck = {r["decision"] for r in lab.struck}
    versions = held(root, "decisions") if versions is None else versions
    now = present(root) if now is None else now

    def settled(text):
        """What a decision's card says was decided, and about what, or None while it says nothing."""
        fm, slots = card(text)
        if not fm or fm.get("decided") is None:
            return None
        s = lambda key: sorted(ids(fm.get(key)))
        return (str(fm.get("decided")), s("about"), s("parks"), s("unparks"), s("drops"), ids(fm.get("order")), s("folds"),  # its order is kept as written
                R.flat(slots.get("Decided", "")))

    def removed(path):
        """The commit that removed a file, or None while HEAD still has it and only the work tree lacks it."""
        if git(root, "cat-file", "-e", f"HEAD:./{path}") is not None:
            return None
        return (git(root, "log", "-1", "--diff-filter=D", "--format=%H", "--", path) or "").strip() or None

    def last(path):
        """The last commit that still had a file: HEAD while only the work tree lacks it, else the one before its removal."""
        gone = removed(path)
        return f"{gone}^" if gone else "HEAD"

    def launched(c, ident):
        """When a mission that carried a decision was launched, as the last commit that held the decision has the
        missions: once it is folded, whatever carried it carries the decision that took it in."""
        names = (git(root, "ls-tree", "--name-only", f"{c}:./missions") or "").split()
        for name in names:
            fm, slots = card(git(root, "show", f"{c}:./missions/{name}") or "")
            if fm and str(fm.get("carries") or "").strip() == ident:
                for raw in str(slots.get("Log", "")).split("\n"):
                    hit = R.MISSION_LINE.match(raw.rstrip())
                    if hit and hit.group(3).strip() == "launched":
                        return f"{hit.group(1)}T{hit.group(2)}:59+00:00"
                if str(fm.get("status") or "") in ("current", "done", "stopped"):
                    return "its mission's launch"
        return None

    def first(acts):
        """The earliest commit, in history's order, that records any of what acted, or None while none does yet."""
        found = []
        for _, path, text in acts:
            where_ = path if path.startswith("missions/") else path.split("/")[0]  # `log.md`, a mission, or `goals` as a whole: a renamed folder is the same place
            c = (git(root, "log", "--reverse", "--find-renames", "--format=%H", "-S", text, "--", where_) or "").split()
            if c:
                found.append((int((git(root, "rev-list", "--count", c[0]) or "0").strip() or 0), c[0]))
        return min(found)[1] if found else None

    for where, commits in sorted(versions.items()):
        if not DECISION.fullmatch(commits[-1][1]):
            continue
        ident = f"D{int(DECISION.fullmatch(commits[-1][1]).group(1))}"
        held_as = [(c, path, settled(git(root, "show", f"{c}:./{path}") or "")) for c, path in commits]  # oldest first
        held_as = [h for h in held_as if h[2]]
        orders = {i for _, _, h in held_as for i in h[5]}  # every order it was ever committed with: emptying it unlocks nothing
        if where not in now:
            into = lab.nodes.get(lab.folded.get(ident, ""))
            c = last(commits[-1][1])
            fm, _ = card(git(root, "show", f"{c}:./{commits[-1][1]}") or "")
            acted = None
            if fm and fm.get("decided") is not None:
                # Only what acted while it was still here locks it: an act after the commit that removed it acts on
                # the decision that took it in. While the removal is not committed yet, everything so far counts.
                gone = removed(commits[-1][1])
                until = R.moment((git(root, "log", "-1", "--format=%cI", gone) or "").strip()) if gone else None
                acts = [a for a in lab.acts(ident, orders | set(ids(fm.get("order"))), lab.settled_at(ident, fm.get("decided")))
                        if until is None or R.moment(a[0]) <= until]
                acted = acts[0][0] if acts else launched(c, ident)
            if ident in struck:  # about how the lab works, and taken out with `lab strike`: only one that never steered the research
                why = steered(lab, ident, versions) + ([f"something acted on it at {acted}"] if acted else []) + ([f"it is folded into {into['id']}"] if into else [])
                if why:
                    bad(commits[-1][1], f"is struck, and it steered the research ({'; '.join(why)}): only a decision about how the lab works is struck; restore it")
                continue
            if not into:
                bad(commits[-1][1], "was committed and is gone; nothing recorded is removed. A draft decision is folded into another with `folds:`. "
                    "One about how the lab works is struck with `lab strike`")
            elif acted:
                bad(commits[-1][1], f"is folded into {into['id']}, and something acted on it at {acted}: a locked decision stays")
            continue
        mine = lambda path: path if path in now[where] else now[where][0]
        if not held_as:
            continue  # never committed settled: what is committed now is held from then
        if settled(R.read(os.path.join(root, mine(held_as[0][1])))) is None:
            bad(mine(held_as[0][1]), f"was settled in {held_as[0][0][:8]} and no longer says what was decided: a settled decision is never reopened, even while it is a draft")
            continue
        d = lab.nodes.get(ident)
        if not d or d.get("type") != "decision":
            continue
        acts = lab.acts(ident, orders | set(d["order"]), d["settled_at"])
        if not acts:
            continue  # settled and still a draft: it may be revised until something acts on it
        # Held as the decision was committed before the first commit that records what acted on it; while no commit
        # records it yet, as the last commit has it. An edit committed with the act, or after it, is a change of mind.
        at = first(acts)
        before = (lambda c: git(root, "merge-base", "--is-ancestor", c, f"{at}^") is not None) if at else (lambda c: True)
        c, path, was = next(((c, p, w) for c, p, w in reversed(held_as) if before(c)), held_as[0])
        if settled(R.read(os.path.join(root, mine(path)))) != was:
            bad(mine(path), f"was locked when {acts[0][0][:16].replace('T', ' ')} acted on it, as committed in {c[:8]}" + ("" if mine(path) == path else f" as {path}")
                + ", and what it parks, drops, folds or brings back, the order it sets, its `decided:`, its `about:` or its Decided text has changed since; a change of mind is a new decision")

    # Where a goal or a question came from is held: once committed, its `from:` changes only to the decision that
    # folded the one it named. Else a decision could be unlocked by pointing what came out of it elsewhere.
    for n in lab.goals + lab.questions:
        was_, is_ = lab.held["from"].get(n["id"]), str(n.get("from"))
        if was_ is not None and was_ != is_ and lab.folded.get(was_) != is_:
            bad(n["path"], f"`from:` was {was_} when first committed and is {is_} now: where a {n['type']} came from does not change, save to the decision that folded the one it named")
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


def stale_so_far(lab):
    """The questions whose So far was last committed before the newest `result` line about a step under them, or about
    a step their So far names: [(question, step, when)]. Where git cannot tell (no history, or the card changed and not
    yet committed), nothing is reported."""
    root, out = lab.root, []
    if not committed(root):
        return out
    for q in lab.questions:
        if q["state"] in ("parked", "dropped"):
            continue
        if (git(root, "status", "--porcelain", "--", q["path"]) or "").strip():
            continue  # being brought up to date now
        last = R.moment((git(root, "log", "-1", "--format=%cI", "--", q["path"]) or "").strip())
        if not last:
            continue
        named = set(re.findall(r"\bG\d+\.Q\d+\.\d+\b", R.flat(q["slots"].get("So far", ""))))
        mine = {x["id"] for x in q["items"]} | {i for i in named if lab.nodes.get(i, {}).get("type") in R.STEPS}
        newer = [l for l in lab.lines if l["kind"] == "result" and l["about"] in mine and l["time"] and (R.moment(l["at"]) or last) > last]
        if newer:
            out.append((q, newer[-1]["about"], f"{newer[-1]['day']} {newer[-1]['time']}"))
    return out


def check(lab):
    root, problems = lab.root, []
    bad = lambda where, what: problems.append(f"history: {where}: {what}")
    if not committed(root):
        return [], ["this lab is not in git, or has no commit: permanence against history was not checked, and nothing recorded is held yet"]
    notes = []
    if (git(root, "rev-parse", "--is-shallow-repository") or "").strip() == "true":
        notes.append("this repository is a shallow clone: the history check needs every commit, and compared the record with the few that are here. "
                     "Fetch the full history (`git fetch --unshallow`; in CI, `fetch-depth: 0`)")
    versions, now = held(root, "log.md", "struck.tsv", "decisions", "goals"), present(root)
    struck = {r["decision"] for r in lab.struck}
    about = lambda line: (m.group(1).strip() if (m := re.match(r"^- (?:\d\d:\d\d \| )?([^|]*?) \|", line)) else None)
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
        same = (lambda a, b: a.rstrip(" ") == b.rstrip(" ")) if name == "log.md" else (lambda a, b: a == b)  # a log line's end spaces are not its
        for c, path in reversed(commits):
            was = (git(root, "show", f"{c}:./{path}") or "").splitlines()
            if name == "log.md":  # the lines of a struck decision went with it
                was = [line for line in was if about(line) not in struck]
            lost = subsequence(was, R.read(os.path.join(root, mine(path))).splitlines(), same)
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
        held_at = []  # (commit, the rows it holds, the last review that passed them there), newest first
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
            held_at.append((c, was, passed[-1]))
        # A passing results review that names an earlier one by its `of` (`lab review ... --supersedes`) supersedes it
        # only once it is committed together with the rows it read: then those rows are held instead of the earlier ones.
        gone = R.superseded([r for _, _, r in held_at])
        for c, was, review in held_at:
            if review.get("of") in gone:
                continue  # a later review, committed with the rows it read, superseded it and said why
            lost = subsequence(was.splitlines(), R.read(os.path.join(root, now[rows][0])).splitlines())
            if lost is not None:
                bad(now[rows][0], f"a row that a review had passed in {c[:8]} is gone or changed: {lost[:70]!r}. Reviewed rows stay; a different result is a new experiment")
                break

    problems += decisions(lab, versions, now)
    problems += resources(lab)
    return sorted(set(problems)), notes
