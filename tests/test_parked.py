"""A question set aside by a decision: parked, off the working pages, with nothing under it moving until a later
decision brings it back; and a decision that parks or brings back cannot be edited afterwards."""
import glob

from test_flow import describe, fill, front, git, lab, open_question


def a_second_question(root):
    lab(root, "new", "question", "G1", "Does the error fall on a biased coin?", "--from", "D1")
    q = glob.glob(f"{root}/goals/G1-*/Q2-*/question.md")[0]
    describe(q, "The law for a coin that is not fair, which the sampler can also draw.")
    lab(root, "new", "build", "G1.Q2", "A biased sampler")
    describe(glob.glob(f"{root}/goals/G1-*/Q2-*/1-*/build.md")[0], "The sampler with a weight on heads.")
    return q


def park(root, ident, title, decided, key="parks"):
    out = lab(root, "new", "decision", title, "--about", ident)
    card = sorted(glob.glob(f"{root}/decisions/D*.md"))[-1]
    fill(card, Seen="The fair coin answers what the lab needs first.", Options="(a) Set it aside. (b) Keep it.", Recommendation="(a).")
    front(card, **{key: f"[{ident}]"})
    return card, out.split()[1].rstrip(":")


def test_a_parked_question_leaves_the_work_and_comes_back_only_by_a_decision(tmp_path):
    root = str(tmp_path)
    open_question(root)
    a_second_question(root)
    assert "G1.Q2.1 A biased sampler" in lab(root, "now")
    card, d2 = park(root, "G1.Q2", "Set the biased coin aside", "")
    # an open decision parks nothing yet: the card says what it would park
    assert "(open)" in lab(root, "show", "G1.Q2") and "Parks: G1.Q2" in lab(root, "show", d2)
    lab(root, "decide", d2, "--with", "Ada", "The biased coin is parked: the fair coin answers what the lab needs first. It comes back if the law holds.")
    now = lab(root, "now")
    assert "Set aside" in now and f"G1.Q2 (parked by {d2})" in now and "A biased sampler" not in now.split("Set aside")[0]
    assert f"Parked by {d2}" in lab(root, "show", "G1.Q2")
    refused = lab(root, "new", "reading", "G1.Q2", "What the biased runs said", ok=False)
    assert f"parked by {d2}" in refused and "unparks" in refused and not glob.glob(f"{root}/goals/G1-*/Q2-*/2-*")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    # a later decision brings it back
    _, d3 = park(root, "G1.Q2", "Bring the biased coin back", "", key="unparks")
    lab(root, "decide", d3, "--with", "Ada", "The law held on the fair coin, so the biased coin comes back.")
    assert "(open)" in lab(root, "show", "G1.Q2") and "Set aside" not in lab(root, "now")
    lab(root, "new", "reading", "G1.Q2", "What the biased runs said")


def test_the_site_shows_what_was_set_aside_apart_from_the_work(tmp_path):
    import pytest
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root = str(tmp_path)
    open_question(root)
    a_second_question(root)
    _, d2 = park(root, "G1.Q2", "Set the biased coin aside", "")
    lab(root, "decide", d2, "--with", "Ada", "The biased coin is parked: the fair coin answers what the lab needs first. It comes back if the law holds.")
    site = Provider(root)
    home = site.get("").main
    assert "Set aside" in home and "parked by" in home and "The biased coin is parked" in home and "A biased sampler" not in home.split("Set aside")[0]
    assert "Parked questions (1)" in site.get("G1").main
    page = site.get("G1.Q2").main
    assert "<b>Parked</b>" in page and "nothing under it moves" in page
    assert "Parks" in site.get(d2).main
    assert not any("biased coin?" in str(r) for r in site.rail())


def test_parking_names_a_question_the_decision_is_about_and_stays_as_settled(tmp_path):
    root = str(tmp_path)
    open_question(root)
    a_second_question(root)
    card, d2 = park(root, "G1.Q2", "Set the biased coin aside", "")
    front(card, parks="[G1.Q2.1, G1.Q1]", unparks="[G1.Q1]")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "parks names 'G1.Q2.1', which is not a question" in out and "parks names G1.Q1, which is not under `about:`" in out and "both parks and unparks G1.Q1" in out
    front(card, parks="[G1.Q2]", unparks="[]")
    lab(root, "decide", d2, "--with", "Ada", "The biased coin is parked: the fair coin answers what the lab needs first.")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-qm", "settled")
    front(card, parks="[]")  # what a settled decision parked cannot be taken back by editing it
    assert "and what it parks or brings back, the order it sets, its `decided:`" in lab(root, "check", "--no-rederive", ok=False)
