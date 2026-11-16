"""A settled decision is a draft until something acts on it: a mission that carries it is launched, or a run starts of
a step its `order:` names. A draft may be revised, or folded into a later decision; a locked one may not."""
import glob, os, re, sys

from test_flow import experiment, fill, front, git, lab, open_question
from test_integrity import commit
from test_order import order
from test_mission import saved


def settled_order(root, ids, title, text):
    card, ident = order(root, ids, title)
    lab(root, "decide", ident, "--with", "Ada", text)
    return card, ident


def test_a_draft_is_revised_until_a_run_of_a_step_it_orders_starts(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root)
    card, d2 = settled_order(root, [ident], "The first experiment first", "The error experiment first: it is the cheapest check of the law.")
    commit(root)
    text = open(card).read()
    # nothing has run since it was settled: its order and its Decided text may still change
    open(card, "w").write(text.replace("the cheapest check", "the quickest check").replace(f"order: [{ident}]", "order: [G1.Q1]"))
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    commit(root, "the order, revised")
    # a run of a step it orders acts on it: from then it is locked
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    commit(root, "the run")
    assert "Locked: acted on at" in lab(root, "show", d2)
    revised = open(card).read()
    open(card, "w").write(revised.replace("the quickest check", "the fastest check"))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert f"{os.path.relpath(card, root)}: was locked when" in out and "a change of mind is a new decision" in out
    commit(root, "reworded after the run")  # committed in the same second as the run's, it is still after it
    assert "was locked when" in lab(root, "check", "--no-rederive", ok=False)
    git(root, "revert", "--no-edit", "HEAD")
    open(card, "w").write(revised)
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_a_draft_is_folded_into_a_later_decision_and_its_number_is_never_used_again(tmp_path):
    root = str(tmp_path)
    open_question(root)
    card2, d2 = settled_order(root, ["G1.Q1"], "The first question first", "The first question first: it is the only one.")
    card3, d3 = settled_order(root, ["G1"], "The goal first", "The goal first, with its first question at the top.")
    _, mission = saved(root, "The first question", d3)
    commit(root)
    assert (d2, d3) == ("D2", "D3")

    # D2 is folded into D3: its file goes, and D3 says it took it in
    os.remove(card2)
    front(card3, folds="[D2]")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    assert "Folds in the drafts: D2" in lab(root, "show", "D3")
    # its log line stays, read as about D3; a new decision does not take its number
    assert "| D2 | decision | Decided: The first question first" in open(f"{root}/log.md").read()
    out = lab(root, "new", "decision", "Something else", "--about", "G1")
    assert "made D4" in out
    os.remove(glob.glob(f"{root}/decisions/D4-*.md")[0])
    commit(root, "D2 folded into D3")
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    # what it may fold: an earlier decision that is gone, once
    front(card3, folds="[D1]")
    assert "folds D1, which is still here" in lab(root, "check", "--no-rederive", ok=False)
    front(card3, folds="[D2, D2]")
    assert "also folds" in lab(root, "check", "--no-rederive", ok=False)
    front(card3, folds="[D2, x]")
    assert "folds names 'x', which is not a decision's id" in lab(root, "check", "--no-rederive", ok=False)
    front(card3, folds="[D2]")

    # a decision gone without a fold is still a removal
    text3 = open(card3).read()
    os.remove(card3)
    assert "was committed and is gone" in lab(root, "check", "--no-rederive", ok=False)
    open(card3, "w").write(text3)

    # a locked decision is not folded: D3 is launched on, then folded into a later one
    lab(root, "mission", "launch")
    commit(root, "launched")
    card4, d4 = settled_order(root, ["G1"], "The goal, again", "The goal first, again.")
    assert d4 == "D4"  # the D4 made above was never committed or logged, so its number is free
    os.remove(card3)
    front(card4, folds="[D2, D3]")  # what D3 took in moves with it
    text = open(mission).read()
    open(mission, "w").write(text.replace(f"carries: {d3}", f"carries: {d4}"))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "is folded into D4, and something acted on it" in out


def test_the_site_opens_a_folded_decision_where_it_went(tmp_path):
    import pytest
    pytest.importorskip("folio")
    from lab_kit import record, site
    root = str(tmp_path)
    open_question(root)
    card2, d2 = settled_order(root, ["G1.Q1"], "The first question first", "The first question first: it is the only one.")
    card3, d3 = settled_order(root, ["G1"], "The goal first", "The goal first, with its first question at the top.")
    os.remove(card2)
    front(card3, folds="[D2]")
    lab_ = record.Lab(root)
    assert lab_.folded == {"D2": "D3"}
    assert 'href="/D3"' in site.ref(lab_, "D2")
    box = site.decision_box(lab_, site.Text(lab_, "D3"), lab_.nodes["D3"])
    assert "Folds in" in box and "Draft" in box


def test_a_settled_decision_is_never_reopened_even_as_a_draft(tmp_path):
    root = str(tmp_path)
    open_question(root)
    card, d2 = settled_order(root, ["G1.Q1"], "The first question first", "The first question first: it is the only one.")
    commit(root)
    text = open(card).read()
    open(card, "w").write(re.sub(r"decided: .*\n", "", text).split("## Decided")[0])
    assert "no longer says what was decided: a settled decision is never reopened" in lab(root, "check", "--no-rederive", ok=False)
    open(card, "w").write(text)
    front(card, folds="[D99]")
    assert "folds D99, which the log never says was decided" in lab(root, "check", "--no-rederive", ok=False)


def test_what_acted_on_a_decision_cannot_be_taken_back_to_unlock_it(tmp_path):
    from test_mission import saved
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root)
    card, d2 = settled_order(root, [ident], "The first experiment first", "The error experiment first: it is the cheapest check of the law.")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)  # under G1.Q1, which came out of D1, and named by D2's order
    commit(root)
    d1 = glob.glob(f"{root}/decisions/D1-*.md")[0]
    question = glob.glob(f"{root}/goals/G1-*/Q1-*/question.md")[0]
    texts = {p: open(p).read() for p in (card, d1, question, f"{root}/resources.toml")}

    # D2 is locked by the run of the step it orders: emptying its order does not unlock it
    open(card, "w").write(texts[card].replace(f"order: [{ident}]", "order: []").replace("the cheapest check", "the quickest check"))
    assert "was locked when" in lab(root, "check", "--no-rederive", ok=False)
    open(card, "w").write(texts[card])

    # D1 is locked by a run under the question that came out of it: pointing the question elsewhere is refused
    front(question, **{"from": d2})
    open(d1, "w").write(texts[d1].replace("It runs on the laptop.", "It runs on the GPU."))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "`from:` was D1 when first committed" in out and "D1-" in out and "was locked when" in out
    open(question, "w").write(texts[question])
    open(d1, "w").write(texts[d1])

    # a resource's `from` does not move without its amounts
    open(f"{root}/resources.toml", "w").write(texts[f"{root}/resources.toml"].replace('from = "D1"', f'from = "{d2}"'))
    commit(root, "the gpu's from moved")
    assert "`from` changed in " in lab(root, "check", "--no-rederive", ok=False)
    git(root, "revert", "--no-edit", "HEAD")

    # a mission's launch is in the lab's log: pointing the mission elsewhere afterwards does not unlock its decision
    card3, d3 = settled_order(root, ["G1"], "The goal first", "The goal first, with its first question at the top.")
    _, mission = saved(root, "The goal", d3)
    lab(root, "mission", "launch")
    assert f"| {d3} | agent | Mission launched: M1 The goal |" in open(f"{root}/log.md").read()
    commit(root, "launched")
    text = open(mission).read()
    open(mission, "w").write(text.replace(f"carries: {d3}", f"carries: {d2}"))
    text3 = open(card3).read()
    open(card3, "w").write(text3.replace("at the top", "first of all"))
    assert f"{os.path.relpath(card3, root)}: was locked when" in lab(root, "check", "--no-rederive", ok=False)
    open(mission, "w").write(text)
    open(card3, "w").write(text3)

    # a decision locked by a run is not folded away
    os.remove(card)
    front(card3, folds=f"[{d2}]")
    assert f"is folded into {d3}, and something acted on it" in lab(root, "check", "--no-rederive", ok=False)


def test_a_lock_is_read_from_history_by_lab_show_and_lab_check_alike(tmp_path):
    from test_mission import saved
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root)
    card, d2 = settled_order(root, [ident], "The first experiment first", "The error experiment first: it is the cheapest check of the law.")
    commit(root)
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    text = open(card).read()
    open(card, "w").write(text.replace("the cheapest check", "the quickest check"))
    commit(root, "the run, and the decision reworded with it")  # an edit committed with the act is already a change of mind
    assert "was locked when" in lab(root, "check", "--no-rederive", ok=False)
    git(root, "revert", "--no-edit", "HEAD")

    # its order emptied: lab show still says locked, as lab check holds it
    root = str(tmp_path / "order")
    os.makedirs(root)
    open_question(root)
    ident, d, command = experiment(root)
    card, d2 = settled_order(root, [ident], "The first experiment first", "The error experiment first: it is the cheapest check of the law.")
    commit(root)
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    commit(root, "the run")
    front(card, order="[]")
    assert "Locked: acted on at" in lab(root, "show", d2)

    # D1 folded away in two commits: first pointed elsewhere and named under `folds:`, then removed
    d1 = glob.glob(f"{root}/decisions/D1-*.md")[0]
    front(card, order=f"[{ident}]", folds="[D1]")
    for path in glob.glob(f"{root}/goals/G1-*/goal.md") + glob.glob(f"{root}/goals/G1-*/Q1-*/question.md"):
        front(path, **{"from": d2})
    commit(root, "D1 folded into D2")
    os.remove(d1)
    commit(root, "D1 removed")
    assert "is folded into D2, and something acted on it" in lab(root, "check", "--no-rederive", ok=False)

    # a mission launched for one decision and pointed at another later does not lock the other
    root = str(tmp_path / "mission")
    os.makedirs(root)
    open_question(root)
    card2, d2 = settled_order(root, ["G1"], "The goal first", "The goal first, with its first question at the top.")
    _, mission = saved(root, "The goal", d2)
    lab(root, "mission", "launch")
    card3, d3 = settled_order(root, ["G1.Q1"], "The question first", "The first question first: it is the only one.")
    text = open(mission).read()
    open(mission, "w").write(text.replace(f"carries: {d2}", f"carries: {d3}"))
    assert "A draft: nothing has acted on it yet" in lab(root, "show", d3)
    assert "Locked: acted on at" in lab(root, "show", d2)
