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
