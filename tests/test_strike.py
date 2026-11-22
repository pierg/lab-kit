"""A decision is about the research. One about how the lab works is struck from the record with `lab strike`: its file
and its log lines go, `struck.tsv` says which and why, and only one that never steered the research may go."""
import glob, os

from test_flow import fill, front, git, lab, open_question
from test_integrity import commit
from test_mission import saved


def about_the_lab(root, title="How the pages read"):
    out = lab(root, "new", "decision", title)
    ident = out.split("made ", 1)[1].split(":", 1)[0]
    card = glob.glob(f"{root}/decisions/{ident}-*.md")[0]
    fill(card, Seen="The pages were hard to follow.")
    lab(root, "decide", ident, "--with", "Ada", "Every page opens with its claim.")
    return ident, card


def test_a_decision_about_how_the_lab_works_is_struck_and_its_number_is_never_used_again(tmp_path):
    root = str(tmp_path)
    open_question(root)
    d2, card = about_the_lab(root)
    commit(root)
    assert f"| {d2} | decision |" in open(f"{root}/log.md").read()

    out = lab(root, "strike", d2, "Its rule is in AGENTS.md, under How the pages read.")
    assert f"struck {d2}" in out and "1 line in log.md" in out
    assert not os.path.exists(card)
    assert f"| {d2} |" not in open(f"{root}/log.md").read()
    assert open(f"{root}/struck.tsv").read().startswith(f"decision\ttitle\tdate\twhy\n{d2}\tHow the pages read\t")
    assert "was struck from the record" in lab(root, "show", d2)
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    commit(root, "struck")
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    # its number is never used again, and it is struck once
    assert "made D3" in lab(root, "new", "decision", "Something else", "--about", "G1")
    assert f"{d2} is already struck" in lab(root, "strike", d2, "again", ok=False)
    assert "no decision D9" in lab(root, "strike", "D9", "nothing", ok=False)
    assert "say why it is struck" in lab(root, "strike", "D3", " ", ok=False)

    # struck.tsv only grows
    text = open(f"{root}/struck.tsv").read()
    open(f"{root}/struck.tsv", "w").write("decision\ttitle\tdate\twhy\n")
    assert "a line committed in" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{root}/struck.tsv", "w").write(text)


def test_a_decision_that_steered_the_research_is_never_struck(tmp_path):
    root = str(tmp_path)
    open_question(root)
    # the goal and the question came out of D1
    assert "G1, G1.Q1 came out of D1" in lab(root, "strike", "D1", "it is about the lab", ok=False)
    # what it orders, parks or holds
    d2, card = about_the_lab(root, "The question first")
    front(card, order="[G1.Q1]")
    assert "under `order:`" in lab(root, "strike", d2, "x", ok=False)
    front(card, order="[]")
    commit(root)
    # a mission that carries it
    saved(root, "Carry it", d2)
    assert "M1 carries" in lab(root, "strike", d2, "x", ok=False)
    for path in glob.glob(f"{root}/missions/*.md"):
        os.remove(path)
    # `about:` alone does not keep it
    front(card, about="[G1.Q1]")
    assert f"struck {d2}" in lab(root, "strike", d2, "Its rule is in AGENTS.md.")


def test_history_refuses_a_struck_decision_that_steered_the_research_and_a_removal_without_a_strike(tmp_path):
    root = str(tmp_path)
    open_question(root)
    d2, card = about_the_lab(root)
    front(card, order="[G1.Q1]")
    commit(root)
    # removed by hand: gone, and its line gone too
    text, log = open(card).read(), open(f"{root}/log.md").read()
    os.remove(card)
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "was committed and is gone" in out and "struck with `lab strike`" in out
    # listed in struck.tsv by hand, around the command's refusal: history still sees its order
    open(f"{root}/struck.tsv", "w").write(f"decision\ttitle\tdate\twhy\n{d2}\tHow the pages read\t2026-01-01\tby hand\n")
    open(f"{root}/log.md", "w").write("".join(l for l in log.splitlines(True) if f"| {d2} |" not in l))
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "is struck, and it steered the research (order)" in out
    # a struck id whose file is still here
    open(card, "w").write(text)
    assert "is struck and its file is still in decisions/" in lab(root, "check", "--no-rederive", ok=False)
    os.remove(f"{root}/struck.tsv")
    open(f"{root}/log.md", "w").write(log)
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    git(root, "status")
