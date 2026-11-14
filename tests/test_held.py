"""Where the lab's record is, what a rename is, what a plan's hash leaves out, and a page that cannot be looked for here."""
import glob, json, os, shutil, subprocess, sys

from test_flow import SRC, experiment, fill, front, git, lab, open_question
from test_integrity import WRITES, commit, done, under

# A fixed folder, hashed by the released 1.0.0 in both ways. A lock, a run or a review made by 1.0.0 holds a hash like
# these, so they must not move: the same folder gives the same hash for ever.
FIXED = {"a.py": b"print(1)\n", "b/c.txt": b"x\n", "a-b/d.cfg": b"k = 1\n", "b/e/f.json": b"{}\n", "Z.md": b"\xef\xbb\xbfcr\r\n", "b.py": b""}
FIRST_WAY = "11376786fde57ae78bf9a099b1a8f1e4085e40640489f90acafac5f48654119f"
AS_NOW = "9b4bebefd67a0699c57b4b5c2a431326b634f4d9a7a4d6f11a8087b34ee1d2fb"
# The same folder with what Python left in it, as the released 1.0.0 hashed it: 1.0.0 counted those files.
CACHE = {"__pycache__/a.cpython-312.pyc": b"\x00a", "b/__pycache__/c.cpython-310.pyc": b"\x00b", "b/stray.pyc": b"\x00c"}
FIRST_WAY_WITH_CACHE = "1aa294c663120a3b5b5e4448f1bb0d1e5bce9790403fe434002aa8e02e13c3c1"
AS_1_0_0_WITH_CACHE = "185df619bb23776ab90f0a0fb9a2be66882b7a7a73ee2a8d16c3c1f7009e381a"


def put(folder, files):
    for path, data in files.items():
        os.makedirs(os.path.dirname(f"{folder}/{path}"), exist_ok=True)
        open(f"{folder}/{path}", "wb").write(data)


def finished(root):
    """A lab with one experiment locked, run, reviewed and committed."""
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    commit(root)
    assert "the record is sound" in lab(root, "check", "--strict")
    return ident, d


def test_the_history_that_is_checked_is_the_labs_own_record(tmp_path):
    # a repository that held an older layout, since removed, with the lab in a folder of it
    repo = under(tmp_path, "repo")
    root = f"{repo}/lab"
    old = {"experiments/26-11-09-static/lock.json": b"{}\n", "experiments/26-11-09-static/log.md": b"- an old line\n", "experiments/26-11-09-static/results.tsv": b"a\tb\n",
           "reviews.tsv": b"x\n", "runs.tsv": b"y\n", "log.md": b"- the repository's own log\n", "resources.toml": b"[old]\nwhat = 'gone'\n", "decisions/D1-old.md": b"old\n",
           "lab/experiments/old/lock.json": b"{}\n", "lab/notes/log.md": b"- a note\n", "lab/goals/old-layout/lock.json": b"{}\n", "lab/goals/a/b/c/d/runs.tsv": b"z\n"}
    put(repo, old)
    commit(repo, "an older layout")
    for path in old:
        os.remove(f"{repo}/{path}")
    os.makedirs(root, exist_ok=True)
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    put(d, {"plan/results.tsv": b"what the apparatus reads\n", "plan/log.md": b"- its own notes\n"})  # the plan's files are the plan's
    commit(repo, "the lab")
    os.remove(f"{d}/plan/results.tsv")
    open(f"{d}/plan/log.md", "w").write("- rewritten\n")
    out = lab(root, "check", "--strict")
    assert "the record is sound" in out and "history:" not in out
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    commit(repo, "the run")
    assert "the record is sound" in lab(root, "check", "--strict")

    # and the lab's own record is still held, each file at its place
    def broken(path, change, *said):
        full = f"{root}/{path}"
        kept = open(full).read()
        change(full, kept)
        out = lab(root, "check", "--no-rederive", ok=False)
        assert all(f"history: {path}: {s}" in out for s in said), out
        open(full, "w").write(kept)

    x = os.path.relpath(d, root)
    rewrite = lambda full, kept: open(full, "w").write(kept.replace("\n", "\n\n", 1))
    drop = lambda full, kept: open(full, "w").write("".join(kept.splitlines(True)[:-1]))
    broken(f"{x}/lock.json", lambda full, kept: os.remove(full), "was committed and is gone")
    broken(f"{x}/lock.json", rewrite, "differs from the lock first committed in")
    for name in ("runs.tsv", "reviews.tsv", "results.tsv"):
        broken(f"{x}/{name}", lambda full, kept: os.remove(full), "was committed and is gone")
        if name != "results.tsv":  # its rows are held once a review has passed them, and a row dropped is a result gone
            broken(f"{x}/{name}", drop, "a line committed in")
    broken("log.md", lambda full, kept: os.remove(full), "was committed and is gone")
    broken("log.md", drop, "a line committed in")
    # the spaces at the end of a log line are not part of it: stripping or adding them is no change
    log = f"{root}/log.md"
    kept = open(log).read()
    for spaced in ("\n".join(l + "  " for l in kept.split("\n")), kept.replace(" \n", "\n")):
        open(log, "w").write(spaced)
        assert "the record is sound" in lab(root, "check", "--no-rederive"), spaced
    open(log, "w").write(kept.replace("- ", "-  ", 1))  # a space inside a line is still a change
    assert "history: log.md: a line committed in" in lab(root, "check", "--no-rederive", ok=False)
    open(log, "w").write(kept)
    lab(root, "log", ident, "agent", "a line with no so what")
    assert open(log).read().endswith("| a line with no so what |\n")  # `lab log` ends a line with no space
    open(log, "w").write(kept)
    broken(os.path.relpath(glob.glob(f"{root}/decisions/D1-*.md")[0], root), lambda full, kept: os.remove(full), "was committed and is gone")
    assert "the record is sound" in lab(root, "check", "--strict")


def test_a_rename_is_the_same_record_under_another_name(tmp_path):
    def renamed(name):
        """A finished lab whose goal, question, experiment and first decision are then renamed, as after a reworded title."""
        root = under(tmp_path, name)
        ident, d = finished(root)
        goal = glob.glob(f"{root}/goals/G1-*")[0]
        os.rename(d, f"{os.path.dirname(d)}/1-two-sample-sizes")
        os.rename(os.path.dirname(d), f"{goal}/Q1-the-square-root-law")
        os.rename(goal, f"{root}/goals/G1-the-law")
        os.rename(glob.glob(f"{root}/decisions/D1-*.md")[0], f"{root}/decisions/D1-where-the-lab-starts.md")
        return root, ident, f"{root}/goals/G1-the-law/Q1-the-square-root-law/1-two-sample-sizes", os.path.relpath(d, root)

    # the rename alone: nothing was removed and nothing was rewritten
    root, ident, d, was = renamed("renamed")
    out = lab(root, "check")
    assert "the record is sound" in out and "history:" not in out
    commit(root, "renamed after the titles")
    assert "the record is sound" in lab(root, "check", "--strict") and "(done, confirmed)" in lab(root, "show", ident)
    x = os.path.relpath(d, root)

    # what was committed under the old name is held under the new one, after the rename is committed too
    lock = open(f"{d}/lock.json").read()
    open(f"{d}/lock.json", "w").write(lock.replace("\n", "\n\n", 1))
    assert f"history: {x}/lock.json: differs from the lock first committed in" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{d}/lock.json", "w").write(lock)
    assert "the record is sound" in lab(root, "check", "--strict")

    # a rename is not a way to rewrite a lock, drop a row, remove a file or change what was decided
    def under_cover(name, change, said):
        root, ident, d, was = renamed(name)
        where = change(root, d, was)
        for committed in (False, True):  # before the rename is committed, and once it is, in the same commit
            out = lab(root, "check", "--no-rederive", ok=False)
            assert any(line.startswith(f"history: {where}: ") and said in line for line in out.splitlines()), out
            if not committed:
                commit(root, "renamed, and more")

    def relock(root, d, was):
        lock = json.load(open(f"{d}/lock.json"))
        open(f"{d}/lock.json", "w").write(json.dumps({**lock, "locked": "2026-01-01T00:00:00+00:00"}, indent=1) + "\n")
        return os.path.relpath(d, root) + "/lock.json"

    def unlist(root, d, was):
        rows = open(f"{d}/reviews.tsv").read().splitlines(True)
        open(f"{d}/reviews.tsv", "w").write("".join(rows[:-1]))
        return os.path.relpath(d, root) + "/reviews.tsv"

    def remove(root, d, was):
        os.remove(f"{d}/runs.tsv")
        return f"{was}/runs.tsv"

    def renumber(root, d, was):  # a number never changes: under another number it is another experiment's
        os.rename(d, f"{os.path.dirname(d)}/2-two-sample-sizes")
        return f"{was}/lock.json"

    def out_of_place(root, d, was):
        os.makedirs(f"{root}/attic")
        os.rename(d, f"{root}/attic/1-two-sample-sizes")
        return f"{was}/results.tsv"

    def redecide(root, d, was):
        card = f"{root}/decisions/D1-where-the-lab-starts.md"
        open(card, "w").write(open(card).read().replace("It runs on the laptop.", "It runs on the GPU."))
        return "decisions/D1-where-the-lab-starts.md"

    under_cover("relocked", relock, "differs from the lock first committed in")
    under_cover("unlisted", unlist, "is gone or changed")
    under_cover("removed", remove, "was committed and is gone; nothing recorded is removed")
    under_cover("renumbered", renumber, "was committed and is gone; nothing recorded is removed")
    under_cover("out-of-place", out_of_place, "was committed and is gone; nothing recorded is removed")
    under_cover("redecided", redecide, "its `decided:`, its `about:` or its Decided text has changed since")


def test_what_python_leaves_in_a_plan_is_not_the_plan(tmp_path):
    sys.path.insert(0, SRC)
    from lab_kit import record as R

    # a folder with nothing of Python's in it hashes as the released 1.0.0 hashed it, in both ways
    plan = under(tmp_path, "fixed")
    put(plan, FIXED)
    assert (R.tree_hash(plan, 1), R.tree_hash(plan, 2), R.tree_hash(plan)) == (FIRST_WAY, AS_NOW, AS_NOW)

    # what an import leaves is left out, wherever it sits and whatever is under it
    put(plan, {"__pycache__/a.cpython-312.pyc": b"\x00a", "b/__pycache__/c.cpython-310.pyc": b"\x00b", "b/e/__pycache__/kept/notes.txt": b"under it\n",
               "__pycache__/__pycache__/x.py": b"1\n", "b/stray.pyc": b"\x00c", "a-b/.hidden.pyc": b""})
    assert (R.tree_hash(plan, 1), R.tree_hash(plan, 2)) == (FIRST_WAY, AS_NOW)

    # and nothing else is: any other file is the plan's, a hidden one too
    for path in ("b/new.py", ".env", "b/__pycache__x/c.py", "b/pyc", "a.pyc.txt"):
        put(plan, {path: b""})
        assert R.tree_hash(plan, 1) != FIRST_WAY and R.tree_hash(plan, 2) != AS_NOW, path
        os.remove(f"{plan}/{path}")
    assert (R.tree_hash(plan, 1), R.tree_hash(plan, 2)) == (FIRST_WAY, AS_NOW)

    # a script of plan/ imported after the lock and again after the run: the plan did not change, and a change to it still shows
    root = under(tmp_path, "lab")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX")}
    subprocess.run([sys.executable, "-m", "compileall", "-q", f"{d}/plan"], check=True, env=env)
    assert glob.glob(f"{d}/plan/__pycache__/sample.*.pyc")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)  # no `--changed` is asked for: nothing changed
    done(root, ident, d)
    put(d, {"plan/__pycache__/more.cpython-312.pyc": b"\x00"})
    out = lab(root, "check")
    assert "the record is sound" in out and "plan/ changed" not in out

    # a compiled file outside __pycache__ is another matter: Python would import it, and no hash covers it
    shutil.copy(glob.glob(f"{d}/plan/__pycache__/sample.*.pyc")[0], f"{d}/plan/sample.pyc")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "plan/ holds a compiled file outside __pycache__, sample.pyc" in out and "plan/ changed" not in out
    os.remove(f"{d}/plan/sample.pyc")
    assert "the record is sound" in lab(root, "check")
    second, d2, command2 = experiment(root, title="Error at 1600 flips", command=WRITES % "0.5")
    put(d2, {"plan/lib/helper.pyc": b"\x00compiled, with no script beside it"})
    assert "plan/ holds a compiled file outside __pycache__, lib/helper.pyc" in lab(root, "lock", second, ok=False) and not os.path.exists(f"{d2}/lock.json")
    assert "plan/ holds a compiled file outside __pycache__, lib/helper.pyc" in lab(root, "run", second, "--trial", "--wait", "--", *command2, ok=False)
    os.remove(f"{d2}/plan/lib/helper.pyc")
    lab(root, "lock", second)
    put(d2, {"plan/lib/helper.pyc": b"\x00put there after the lock"})
    assert "plan/ holds a compiled file outside __pycache__" in lab(root, "run", second, "--wait", "--", *command2, ok=False)
    assert not glob.glob(f"{root}/runs/*{second}*") and not glob.glob(f"{root}/.lab/running/*{second}*")
    os.remove(f"{d2}/plan/lib/helper.pyc")
    assert "finished" in lab(root, "run", second, "--wait", "--", *command2)
    open(f"{d}/plan/sample.py", "a").write("# after the fact\n")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)


def test_a_plan_that_1_0_0_hashed_with_its_cache_files_still_verifies(tmp_path):
    sys.path.insert(0, SRC)
    from lab_kit import record as R

    # the 1.0.0 way of hashing, kept: a fixed folder with cache files gives what the released 1.0.0 gave
    plan = under(tmp_path, "fixed")
    put(plan, {**FIXED, **CACHE})
    assert (R.tree_hash(plan, 1, cache=True), R.tree_hash(plan, 2, cache=True)) == (FIRST_WAY_WITH_CACHE, AS_1_0_0_WITH_CACHE)
    assert (R.tree_hash(plan, 1), R.tree_hash(plan, 2)) == (FIRST_WAY, AS_NOW)

    # a lock as 1.0.0 wrote it while a __pycache__ sat in plan/: its hash of plan/ counts the cache file
    root = under(tmp_path, "lab")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    put(d, {"plan/__pycache__/sample.cpython-312.pyc": b"\x00left by an import"})
    lab(root, "lock", ident)
    with_cache = R.tree_hash(f"{d}/plan", 2, cache=True)
    lock = json.load(open(f"{d}/lock.json"))
    assert lock["plan"] == R.tree_hash(f"{d}/plan") != with_cache

    def relock(kit):
        open(f"{d}/lock.json", "w").write(json.dumps({**lock, "kit": kit, "plan": with_cache}, indent=1) + "\n")

    # only a lock that 1.0.0 made is read that way: the same hash under any other kit is a changed plan
    relock("1.0.1")
    assert "plan/ is not what was locked" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    relock("1.0.0")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)  # no `--changed` is asked for: nothing changed
    assert "the record is sound" in lab(root, "check", "--no-rederive")  # the run pins the plan as hashed now, the lock as 1.0.0 hashed it: one plan

    # the run as 1.0.0 would have recorded it: its hash of plan/ counts the cache file too
    rj = glob.glob(f"{root}/runs/*/run.json")[0]
    record = json.load(open(rj))
    old_seal = record["seal"]
    record["plan"] = with_cache
    record["seal"] = R.seal_of(record)
    os.chmod(rj, 0o644)
    open(rj, "w").write(json.dumps(record, indent=1) + "\n")
    listed = open(f"{d}/runs.tsv").read()
    open(f"{d}/runs.tsv", "w").write(listed.replace(old_seal, record["seal"]))
    done(root, ident, d)
    assert "the record is sound" in lab(root, "check")
    relock("1.0.1")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)
    relock("1.0.0")

    # it verifies only what was hashed: a cache file that changed, or went, is a plan that cannot be verified, and a changed script still shows
    cache = f"{d}/plan/__pycache__/sample.cpython-312.pyc"
    open(cache, "wb").write(b"\x00written again by a later import")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)
    os.remove(cache)
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)
    open(cache, "wb").write(b"\x00left by an import")
    assert "the record is sound" in lab(root, "check")
    open(f"{d}/plan/sample.py", "a").write("# after the fact\n")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)


ROWS = "name\tlabel\tvalue\treads\tversus\tcommand\n"
CLEARED = dict(Found="", Means="")


def test_rows_that_a_committed_review_passed_stay_whatever_the_card_says_later(tmp_path):
    kept = under(tmp_path, "kept")
    ident, d = finished(kept)  # locked, run, its results reviewed and passed, and all of it committed
    root = str(tmp_path / "lab")
    shutil.copytree(kept, root, symlinks=True)
    d = root + d[len(kept):]
    card, rows, was = f"{d}/experiment.md", f"{d}/results.tsv", open(f"{d}/results.tsv").read()
    written = open(card).read()
    held = "a row that a review had passed in"

    # the file emptied together with Found and Means: nothing on the card contradicts it, and git still holds the rows
    fill(card, **CLEARED)
    open(rows, "w").write(ROWS)
    out = lab(root, "check", ok=False)
    assert held in out and "Reviewed rows stay" in out and "ratio" in out
    open(rows, "w").write("")
    assert held in lab(root, "check", ok=False)
    os.remove(rows)
    assert "results.tsv: was committed and is gone" in lab(root, "check", ok=False)

    # the emptied file committed, then filled with other rows, reviewed again and committed: still held, at every step
    open(rows, "w").write(ROWS)
    commit(root, "emptied")
    assert held in lab(root, "check", ok=False)
    open(rows, "w").write(was.replace("the error at 400 flips as a share", "the error at 400 flips, read again, as a share"))
    assert held in lab(root, "check", ok=False)
    lab(root, "review", ident, "results", "pass", "Read the new rows; the command prints the value.")
    open(card, "w").write(written)
    assert "(done, confirmed)" in lab(root, "show", ident)  # everything in the files agrees
    assert held in lab(root, "check", ok=False)
    commit(root, "filled with other rows")
    out = lab(root, "check", ok=False)
    assert held in out and "ratio\\tthe error at 400 flips as a share" in out

    # in the lab as it was: a row added after the reviewed ones and read by a new review. Rows are only added
    root, d = kept, kept + d[len(root):]
    rows = f"{d}/results.tsv"
    open(rows, "w").write(was + "ratio.high\tthe upper end of that share\t0.5\tpercent\tone half\tcat $RUN/ratio.txt\n")
    lab(root, "review", ident, "results", "pass", "Read the added row.")
    assert "the record is sound" in lab(root, "check")
    commit(root, "a row added")
    assert "the record is sound" in lab(root, "check", "--strict")

    # a draft row committed after the review, which that review never read: it may be corrected, and then reviewed
    root = under(tmp_path, "draft")
    ident, d = finished(root)
    rows, was = f"{d}/results.tsv", open(f"{d}/results.tsv").read()
    open(rows, "w").write(was + "ratio.high\tthe uper end of taht share\t0.5\tpercent\tone half\tcat $RUN/ratio.txt\n")
    assert "its results or its run changed after the review that passed them" in lab(root, "check", ok=False)
    commit(root, "a draft row")
    open(rows, "w").write(was + "ratio.high\tthe upper end of that share\t0.5\tpercent\tone half\tcat $RUN/ratio.txt\n")
    lab(root, "review", ident, "results", "pass", "Read both rows; the label is corrected.")
    commit(root, "the row corrected, and reviewed")
    out = lab(root, "check", "--strict")
    assert "the record is sound" in out and held not in out
    open(rows, "w").write(was)  # the corrected row was read by a committed review: now it stays
    assert held in lab(root, "check", ok=False)

    # rows no review has passed yet may still change, committed or not
    root = under(tmp_path, "unreviewed")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    open(f"{d}/results.tsv", "w").write(ROWS + "ratio\ta first wording\t0.5\tpercent\tone half\tcat $RUN/ratio.txt\n")
    commit(root)
    open(f"{d}/results.tsv", "w").write(ROWS + "ratio\ta second wording\t0.5\tpercent\tone half\tcat $RUN/ratio.txt\n")
    assert "the record is sound" in lab(root, "check")
    open(f"{d}/results.tsv", "w").write(ROWS)
    assert "the record is sound" in lab(root, "check")


def test_a_shallow_clone_holds_almost_nothing_and_the_check_says_so(tmp_path):
    root = under(tmp_path, "lab")
    ident, d = finished(root)
    lab(root, "log", ident, "agent", "Read the result again.", "Nothing to add.")
    commit(root, "a second commit")
    shallow, full = str(tmp_path / "shallow"), str(tmp_path / "full")
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{root}", shallow], check=True)
    subprocess.run(["git", "clone", "-q", f"file://{root}", full], check=True)
    for clone in (shallow, full):
        shutil.copytree(f"{root}/runs", f"{clone}/runs")  # the store is there in both: only the history differs
    out = lab(shallow, "check")
    assert "this repository is a shallow clone" in out and "fetch-depth: 0" in out and "the record is sound" in out
    assert "not everything could be checked" in lab(shallow, "check", "--strict", ok=False)
    assert "shallow" not in lab(full, "check", "--strict")
    subprocess.run(["git", "fetch", "-q", "--unshallow"], cwd=shallow, check=True)
    assert "shallow" not in lab(shallow, "check", "--strict")


def test_a_page_of_another_library_is_looked_for_where_that_library_is(tmp_path):
    root = under(tmp_path, "lab")
    qdir = open_question(root)
    os.makedirs(f"{root}/docs")
    open(f"{root}/docs/folio.yaml", "w").write("title: lab\nlibraries:\n  notes:\n    path: ../../notes\n    url: https://notes.example\n")
    front(f"{qdir}/question.md", see="[notes:/content/readings/the-law.html]")
    commit(root)

    # the other library is not on this machine: the page could not be looked for, which is a note
    out = lab(root, "check")
    assert "note: the library notes is not here" in out and "could not be checked here" in out and "the record is sound" in out and "links:" not in out
    out = lab(root, "check", "--strict", ok=False)
    assert "not everything could be checked here" in out and "problem(s)" not in out

    # it is here, and the page is not: a problem
    os.makedirs(tmp_path / "notes" / "content")
    out = lab(root, "check", ok=False)
    assert "see names notes:/content/readings/the-law.html, and the library notes holds no such page" in out and "is not here" not in out
    assert "holds no such page" in lab(root, "check", "--strict", ok=False)

    # it is here with the page
    os.makedirs(tmp_path / "notes" / "content" / "readings")
    open(tmp_path / "notes" / "content" / "readings" / "the-law.html", "w").write("<p>the law</p>\n")
    out = lab(root, "check", "--strict")
    assert "the record is sound" in out and "note:" not in out

    # a library the charter does not name is a problem wherever the check runs
    front(f"{qdir}/question.md", see="[elsewhere:/content/readings/the-law.html]")
    assert "which is not a page of a library the charter names" in lab(root, "check", ok=False)
