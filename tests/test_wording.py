"""A lock holds what a plan demands in machine terms, and not its words: the words may be made clearer after the lock."""
import json, os, re

from test_flow import experiment, fill, front, lab, locked, open_question
from test_integrity import commit, under

CLEARER = dict(Compares="1. **Draw** 200 estimates at 100 flips.\n2. **Draw** 200 more at 400 flips.\n3. **Compare** their mean errors.",
               Arms="- 100 flips: two hundred estimates of a fair coin, each made from one hundred flips\n- 400 flips: as above, with four hundred flips each",
               Confirmed_if="- the error at 400 flips is less than 0.6 of the error at 100 (`ratio < 0.6`)\n- and more than 0.4 of it (`ratio > 0.4`)",
               Refuted_if="- the error hardly falls at all (`ratio > 0.9`)",
               Limits="- One coin, one sampler.")


def test_the_words_of_a_locked_plan_may_be_made_clearer_and_what_it_demands_may_not(tmp_path):
    root, ident, d, command = locked(tmp_path)
    card = f"{d}/experiment.md"
    lock = json.load(open(f"{d}/lock.json"))
    assert lock["terms"] and lock["card"]  # the machine terms and the whole plan, both as they were locked
    commit(root)
    fill(card, **CLEARER, So_far="Nothing has run yet.")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)  # the run is under the lock it was locked with
    assert json.load(open(f"{d}/lock.json")) == lock  # the lock is never written again
    run = json.load(open(next(os.path.join(root, "runs", r, "run.json") for r in os.listdir(f"{root}/runs"))))
    assert run["lock"]["card"] == lock["card"]
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    original = open(card).read()
    for what, change in (("a bar's number", lambda t: t.replace("`ratio > 0.9`", "`ratio > 0.8`")),
                         ("a bar's comparison", lambda t: t.replace("`ratio < 0.6`", "`ratio <= 0.6`")),
                         ("a bar's result", lambda t: t.replace("`ratio > 0.4`", "`share > 0.4`")),
                         ("a bar removed", lambda t: t.replace("- and more than 0.4 of it (`ratio > 0.4`)\n", "")),
                         ("a bar's test removed", lambda t: t.replace(" (`ratio > 0.9`)", "")),
                         ("a bar given a role", lambda t: t.replace("- and more than 0.4 of it", "- readable: and more than 0.4 of it")),
                         ("an arm renamed", lambda t: t.replace("- 400 flips:", "- four hundred flips:")),
                         ("an arm added", lambda t: t.replace("- 400 flips:", "- 1600 flips: more\n- 400 flips:")),
                         ("the resources", lambda t: re.sub(r"^uses: .*$", "uses: [laptop, gpu]", t, flags=re.M))):
        open(card, "w").write(change(original))
        out = lab(root, "check", "--no-rederive", ok=False)
        assert "changed after the lock" in out, what
    open(card, "w").write(original)
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_a_lock_made_before_the_terms_were_held_reads_them_from_git(tmp_path):
    # a lock with the hash of the whole plan and no `terms`, as a kit before 1.3.0 wrote it
    root, ident, d, command = locked(tmp_path)
    card = f"{d}/experiment.md"
    lock = json.load(open(f"{d}/lock.json"))
    lock.pop("terms")
    lock["kit"] = "1.2.0"
    open(f"{d}/lock.json", "w").write(json.dumps(lock, indent=1) + "\n")
    original = open(card).read()

    # with the locked card nowhere in git, the whole plan is held as it was locked
    fill(card, Limits="- One coin, one sampler.")
    assert "changed after the lock" in lab(root, "check", "--no-rederive", ok=False)
    assert "changed after the lock" in lab(root, "run", ident, "--wait", "--", *command, ok=False)

    # once git holds the card as it was locked, its terms are read from there, and only they are held
    open(card, "w").write(original)
    commit(root)
    fill(card, **CLEARER)
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    fill(card, Refuted_if="- the error hardly falls at all (`ratio > 0.8`)")
    assert "changed after the lock" in lab(root, "check", "--no-rederive", ok=False)
    assert "changed after the lock" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    fill(card, Refuted_if="- the error hardly falls at all (`ratio > 0.9`)")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)


def test_a_lab_inside_a_larger_repository_reads_its_old_locks_from_git_too(tmp_path):
    top = under(tmp_path, "repo")
    root = f"{top}/lab"
    os.makedirs(root)
    open_question(root)
    ident, d, command = experiment(root)
    lab(root, "lock", ident)
    lock = json.load(open(f"{d}/lock.json"))
    lock.pop("terms")
    open(f"{d}/lock.json", "w").write(json.dumps(lock, indent=1) + "\n")
    commit(top)
    fill(f"{d}/experiment.md", Limits="- One coin.")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    front(f"{d}/experiment.md", uses="[gpu]")
    assert "changed after the lock" in lab(root, "check", "--no-rederive", ok=False)


def test_swapping_what_bars_are_for_changes_what_the_plan_demands(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root)
    card = f"{d}/experiment.md"
    fill(card, Confirmed_if="- answer: the error at 400 flips is under 0.6 of the error at 100 (`ratio < 0.6`)\n- readable: and over 0.4 of it (`ratio > 0.4`)")
    lab(root, "lock", ident)
    fill(card, Confirmed_if="- answer: at 400 flips, the error is below 0.6 of the error at 100 (`ratio < 0.6`)\n- readable: and above 0.4 of it (`ratio > 0.4`)")
    assert "the record is sound" in lab(root, "check", "--no-rederive")  # the same roles, in other words
    fill(card, Confirmed_if="- readable: the error at 400 flips is under 0.6 of the error at 100 (`ratio < 0.6`)\n- answer: and over 0.4 of it (`ratio > 0.4`)")
    assert "changed after the lock" in lab(root, "check", "--no-rederive", ok=False)  # which bar is the answer is part of what was locked
    assert "changed after the lock" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
