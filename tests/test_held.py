"""Where the lab's record is, what a rename is, what a plan's hash leaves out, and a page that cannot be looked for here."""
import glob, json, os, shutil, subprocess, sys

from test_flow import SRC, experiment, fill, front, git, lab, open_question
from test_integrity import WRITES, commit, done, under

# A fixed folder, hashed by the released 1.0.0 in both ways. A lock, a run or a review made by 1.0.0 holds a hash like
# these, so they must not move: the same folder gives the same hash for ever.
FIXED = {"a.py": b"print(1)\n", "b/c.txt": b"x\n", "a-b/d.cfg": b"k = 1\n", "b/e/f.json": b"{}\n", "Z.md": b"\xef\xbb\xbfcr\r\n", "b.py": b""}
FIRST_WAY = "11376786fde57ae78bf9a099b1a8f1e4085e40640489f90acafac5f48654119f"
AS_NOW = "9b4bebefd67a0699c57b4b5c2a431326b634f4d9a7a4d6f11a8087b34ee1d2fb"


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
    shutil.copy(glob.glob(f"{d}/plan/__pycache__/sample.*.pyc")[0], f"{d}/plan/sample.pyc")
    put(d, {"plan/__pycache__/more.cpython-312.pyc": b"\x00"})
    out = lab(root, "check")
    assert "the record is sound" in out and "plan/ changed" not in out
    open(f"{d}/plan/sample.py", "a").write("# after the fact\n")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)


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
