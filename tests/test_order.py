"""The order of the work, agreed with the operator: set by a settled decision's `order:`, worked out into the order
`lab now` and the site list the steps in, and never edited once settled."""
import glob, re

from test_flow import describe, fill, front, git, lab, open_question


def three_steps(root):
    """A build under the first question, then a second question with two builds: G1.Q1.1, G1.Q2.1, G1.Q2.2."""
    lab(root, "new", "build", "G1.Q1", "A fair sampler")
    lab(root, "new", "question", "G1", "Does the error fall on a biased coin?", "--from", "D1")
    describe(glob.glob(f"{root}/goals/G1-*/Q2-*/question.md")[0], "The law for a coin that is not fair, which the sampler can also draw.")
    lab(root, "new", "build", "G1.Q2", "A biased sampler")
    lab(root, "new", "build", "G1.Q2", "A weight on heads")
    for card in glob.glob(f"{root}/goals/G1-*/Q*/*/build.md"):
        describe(card, "A sampler the questions need before anything is measured.")


def order(root, ids, title="The order of the work"):
    out = lab(root, "new", "decision", title, "--about", "G1")
    card = sorted(glob.glob(f"{root}/decisions/D*.md"))[-1]
    fill(card, Seen="Both questions have work the agent can move.", Options="(a) The biased coin first. (b) The tree's order.", Recommendation="(a).")
    front(card, order=f"[{', '.join(ids)}]")
    return card, out.split()[1].rstrip(":")


def listed(text, section):
    """The ids a section of `lab now` lists, in its order."""
    body = text.split(section, 1)[1].split("\n\n", 1)[0]
    return re.findall(r"^- (G\d+\.Q\d+\.\d+) ", body, flags=re.M)


def test_steps_are_listed_in_the_order_a_settled_decision_sets(tmp_path):
    root = str(tmp_path)
    open_question(root)
    three_steps(root)
    assert listed(lab(root, "now"), "Yours next") == ["G1.Q1.1", "G1.Q2.1", "G1.Q2.2"]
    # a step named on its own takes its own place; its question's place holds the rest of the question
    card, d2 = order(root, ["G1.Q2.2", "G1.Q1", "G1.Q2"])
    assert listed(lab(root, "now"), "Yours next") == ["G1.Q1.1", "G1.Q2.1", "G1.Q2.2"]  # an open decision orders nothing yet
    assert "Would order the work, first to last: G1.Q2.2, G1.Q1, G1.Q2" in lab(root, "show", d2)
    lab(root, "decide", d2, "--with", "Ada", "The weight on heads first, then the fair coin, then the rest of the biased coin.")
    now = lab(root, "now")
    assert f"Yours next (in the order {d2} set)" in now
    assert listed(now, "Yours next") == ["G1.Q2.2", "G1.Q1.1", "G1.Q2.1"]
    assert "Orders the work, first to last" in lab(root, "show", d2)
    # the last settled decision that sets an order has the say; what it does not name follows in the tree's order
    _, d3 = order(root, ["G1.Q2.1"], "The biased sampler first")
    lab(root, "decide", d3, "--with", "Ada", "The biased sampler first; the rest as the tree has it.")
    assert listed(lab(root, "now"), "Yours next") == ["G1.Q2.1", "G1.Q1.1", "G1.Q2.2"]
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_the_order_names_what_it_orders_once_and_stays_as_settled(tmp_path):
    root = str(tmp_path)
    open_question(root)
    three_steps(root)
    card, d2 = order(root, ["G1.Q2", "G1.Q9", "G1.Q2", "gpu"])
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "order names 'G1.Q9', which is not a goal, a question or a step" in out and "order names 'gpu'" in out
    assert "order names G1.Q2 more than once" in out
    front(card, order="[G1.Q2, G1.Q1]")
    lab(root, "decide", d2, "--with", "Ada", "The biased coin first.")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-qm", "settled")
    front(card, order="[G1.Q1, G1.Q2]")  # a settled order is changed by a new decision, not by editing this one
    assert "the order it sets" in lab(root, "check", "--no-rederive", ok=False)


def test_the_site_lists_next_in_the_agreed_order(tmp_path):
    import pytest
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root = str(tmp_path)
    open_question(root)
    three_steps(root)
    _, d2 = order(root, ["G1.Q2.2", "G1.Q1", "G1.Q2"])
    lab(root, "decide", d2, "--with", "Ada", "The weight on heads first, then the fair coin, then the rest of the biased coin.")
    site = Provider(root)
    home = site.get("").main
    nxt = home.split("<h2>Next</h2>", 1)[1].split("</table>", 1)[0]
    assert "In the order of the work set by" in nxt
    assert nxt.index("A weight on heads") < nxt.index("A fair sampler") < nxt.index("A biased sampler")
    assert "Orders the work" in site.get(d2).main
