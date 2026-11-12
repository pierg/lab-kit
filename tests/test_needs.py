"""A step may need a step anywhere in the tree, before it or after it, and every view says the same of it."""
import glob, re

from test_flow import describe, experiment, fill, folder, front, lab, open_question


def reading(root, question, title, done=True):
    ident = re.search(r"made (\S+):", lab(root, "new", "reading", question, title)).group(1)
    card = f"{folder(root, ident)}/reading.md"
    describe(card, "Reads what the sampler already wrote, to say what the next step should be.")
    fill(card, Looks_at="The sampler's own log.")
    if done:
        fill(card, Seen="- Nine estimates used the short sample.", Suggests="Fix the seed, then measure again.")
    return ident, card


def across(root):
    """Two questions. Under the first: a reading, a build and an experiment, each needing a reading under the second."""
    open_question(root)
    lab(root, "new", "question", "G1", "Does it hold further out?", "--from", "D1")
    describe(glob.glob(f"{root}/goals/G1-*/Q2-*/question.md")[0], "What follows once the first sizes are measured.")
    first, card = reading(root, "G1.Q1", "Which sizes to compare", done=False)
    lab(root, "new", "build", "G1.Q1", "A sampler with a fixed seed")
    describe(f"{folder(root, 'G1.Q1.2')}/build.md", "The sampler, with its seed set once.")
    ident, d, command = experiment(root)
    later, later_card = reading(root, "G1.Q2", "Every estimate that missed, by cause")
    assert (first, ident, later) == ("G1.Q1.1", "G1.Q1.3", "G1.Q2.1")
    for path in (card, f"{folder(root, 'G1.Q1.2')}/build.md", f"{d}/experiment.md"):
        front(path, needs=f"[{later}]")
    return ident, d, later_card


def mine(root):
    """The ids `lab now` lists as the agent's to move, and those it lists as waiting."""
    out = lab(root, "now")
    ids = lambda text: re.findall(r"^- (G\d+\.Q\d+\.\d+) ", text, flags=re.M)
    return ids(out.split("Yours next")[1].split("Not yours to move yet")[0]), ids(out.split("Not yours to move yet")[1].split("Questions")[0])


def test_a_step_may_need_one_that_sits_later_in_the_tree(tmp_path):
    root = str(tmp_path)
    ident, d, later_card = across(root)

    # what is needed is done, under a later question: all three are the agent's to move, and every view says so
    assert mine(root) == (["G1.Q1.1", "G1.Q1.2", "G1.Q1.3"], [])
    assert "Next: read it" in lab(root, "show", "G1.Q1.1") and "Needs: G1.Q2.1 (done)" in lab(root, "show", "G1.Q1.1")
    assert "Next: build it" in lab(root, "show", "G1.Q1.2") and "Next: lock it" in lab(root, "show", ident)
    under = lab(root, "show", "G1.Q1").split("Under it")[1]
    assert under.count(". Next: ") == 3 and "waiting on" not in lab(root, "brief", "G1.Q1") and lab(root, "brief", "G1.Q1").count("Next, for the agent: ") == 3
    assert "the record is sound" in lab(root, "check")
    assert "locked" in lab(root, "lock", ident)

    # a chain that goes forward and back again: Q1.1 needs Q2.1, which needs Q2.2, which needs Q1.2
    _, last = reading(root, "G1.Q2", "What the fixed seed changes", done=False)
    front(later_card, needs="[G1.Q2.2]")
    front(last, needs="[G1.Q1.2]")
    front(f"{folder(root, 'G1.Q1.2')}/build.md", needs="[]")
    fill(later_card, Suggests="")
    assert mine(root) == (["G1.Q1.2"], ["G1.Q1.1", ident, "G1.Q2.1", "G1.Q2.2"])  # only the build at the end of the chain moves
    front(f"{folder(root, 'G1.Q1.2')}/build.md", commits="[abc1234]", tests="[tests/test_seed.py]")
    assert mine(root) == (["G1.Q2.2"], ["G1.Q1.1", ident, "G1.Q2.1"])
    fill(last, Seen="- The spread halves.", Suggests="Measure at two sizes.")
    assert mine(root) == (["G1.Q2.1"], ["G1.Q1.1", ident])
    fill(later_card, Suggests="Fix the seed, then measure again.")
    assert mine(root) == (["G1.Q1.1", ident], []) and "the record is sound" in lab(root, "check")


def test_a_step_waits_while_what_it_needs_is_not_done_wherever_that_sits(tmp_path):
    root = str(tmp_path)
    ident, d, later_card = across(root)
    fill(later_card, Suggests="")  # the reading under the second question is not done yet
    assert mine(root) == (["G1.Q2.1"], ["G1.Q1.1", "G1.Q1.2", "G1.Q1.3"])
    assert "G1.Q1.1 Which sizes to compare: on G1.Q2.1 Every estimate that missed, by cause" in lab(root, "now")
    assert "Waiting on: G1.Q2.1 Every estimate that missed, by cause" in lab(root, "show", "G1.Q1.1") and "Needs: G1.Q2.1 (planned)" in lab(root, "show", ident)
    assert lab(root, "brief", "G1.Q1").count("Waiting on G1.Q2.1") == 3
    assert f"{ident} waits on G1.Q2.1" in lab(root, "lock", ident, ok=False)
    assert f"{ident} waits on G1.Q2.1" in lab(root, "run", ident, "--trial", "--wait", "--", "true", ok=False)
    assert not glob.glob(f"{d}/lock.json") and not glob.glob(f"{root}/runs/*") and not glob.glob(f"{root}/.lab/running/2*")


def test_steps_that_need_each_other_stay_where_they_are_and_say_why(tmp_path):
    root = str(tmp_path)
    ident, d, later_card = across(root)

    # the reading that is done needs, in turn, the experiment that needs it: a circle, with one of its steps done
    front(later_card, needs=f"[{ident}]")
    out = lab(root, "check", ok=False)
    assert f"{d[len(root) + 1:]}/experiment.md: needs itself, directly or through what it needs" in out
    assert mine(root) == (["G1.Q1.1", "G1.Q1.2"], [ident])  # what only needs the done reading still moves; what is in the circle does not
    why = "G1.Q2.1 Every estimate that missed, by cause, which needs G1.Q1.3 in turn: no step in a circle of needs can move"
    assert f"{ident} Error at 100 and at 400 flips: on {why}" in lab(root, "now") and f"Waiting on: {why}" in lab(root, "show", ident)
    assert f"{ident} waits on {why}" in lab(root, "lock", ident, ok=False) and not glob.glob(f"{d}/lock.json")
    assert "Waiting on G1.Q2.1" in lab(root, "brief", "G1.Q1") and "reading (done)" in lab(root, "show", "G1.Q2.1")

    # a longer circle with nothing done, and a step that needs itself: nothing loops, and each says which need leads back
    fill(later_card, Suggests="")
    front(later_card, needs="[G1.Q1.1]")
    front(f"{folder(root, 'G1.Q1.1')}/reading.md", needs="[G1.Q1.2]")
    front(f"{folder(root, 'G1.Q1.2')}/build.md", needs="[G1.Q2.1]")
    front(f"{d}/experiment.md", needs=f"[{ident}]")
    assert mine(root) == ([], ["G1.Q1.1", "G1.Q1.2", ident, "G1.Q2.1"])
    out = lab(root, "now")
    assert "G1.Q1.2 A sampler with a fixed seed, which needs G1.Q1.1 in turn" in out and "G1.Q2.1 Every estimate that missed, by cause, which needs G1.Q1.2 in turn" in out
    assert f"on {ident}, which is itself: a step cannot need itself" in out and "G1.Q1.1 Which sizes to compare, which needs G1.Q2.1 in turn" in out
    assert lab(root, "check", ok=False).count("needs itself, directly or through what it needs") == 4
    assert "which is itself" in lab(root, "lock", ident, ok=False)

    # the circle broken, everything moves again in the order of what needs what
    front(later_card, needs="[]")
    front(f"{d}/experiment.md", needs="[G1.Q1.2]")
    assert mine(root) == (["G1.Q2.1"], ["G1.Q1.1", "G1.Q1.2", ident]) and "needs itself" not in lab(root, "check")


def test_a_need_that_can_never_be_met_says_so_and_holds_the_step(tmp_path):
    root = str(tmp_path)
    ident, d, later_card = across(root)

    # the reading they need is dropped: nothing would ever end the wait, so what they wait on says what to do
    front(later_card, dropped='"The log was not kept."')
    why = "G1.Q2.1 Every estimate that missed, by cause, which is dropped: remove the need or replace it"
    assert mine(root) == ([], ["G1.Q1.1", "G1.Q1.2", ident])
    assert f"{ident} Error at 100 and at 400 flips: on {why}" in lab(root, "now") and f"Waiting on: {why}" in lab(root, "show", "G1.Q1.2")
    assert f"{ident} waits on {why}" in lab(root, "lock", ident, ok=False) and not glob.glob(f"{d}/lock.json")

    # an experiment that was replaced is the same: the need names the one that replaced it, or goes
    old, d_old, _ = experiment(root, title="A first pair of sizes")
    new, d_new, _ = experiment(root, title="A second pair of sizes")
    front(f"{d_new}/experiment.md", replaces=old, because='"The first pair was too close."')
    front(f"{d}/experiment.md", needs=f"[{old}]")
    assert f"{ident} waits on {old} A first pair of sizes, which is replaced: remove the need or replace it" in lab(root, "lock", ident, ok=False)

    # a need that names nothing in the lab, or a question, holds the step in the commands as the check reports it
    front(f"{d}/experiment.md", needs="[G1.Q9.9]")
    assert "needs G1.Q9.9, which is not an experiment, a build or a reading" in lab(root, "check", "--no-rederive", ok=False)
    assert f"{ident} waits on G1.Q9.9, which does not exist: correct the need or remove it" in lab(root, "lock", ident, ok=False)
    assert f"{ident} waits on G1.Q9.9, which does not exist" in lab(root, "run", ident, "--trial", "--wait", "--", "true", ok=False)
    assert f"{ident} Error at 100 and at 400 flips: on G1.Q9.9, which does not exist" in lab(root, "now")
    front(f"{d}/experiment.md", needs="[G1.Q2]")
    assert f"{ident} waits on G1.Q2, which is not an experiment, a build or a reading" in lab(root, "lock", ident, ok=False)
    assert not glob.glob(f"{d}/lock.json") and not glob.glob(f"{root}/runs/*") and not glob.glob(f"{root}/.lab/running/2*")

    # locked while its needs were met, and a need that does not exist written after: `lab run` holds it too
    front(f"{d}/experiment.md", needs="[]")
    lab(root, "lock", ident)
    front(f"{d}/experiment.md", needs="[G1.Q9.9]")
    assert f"{ident} waits on G1.Q9.9, which does not exist" in lab(root, "run", ident, "--wait", "--", "true", ok=False)
    front(f"{d}/experiment.md", needs="[]")
    assert ident in mine(root)[0]
