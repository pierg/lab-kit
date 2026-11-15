"""Missions: the working note for carrying out a settled decision. Saved as next, launched as current (several at
once), logged, and closed with one line in the lab's log. Checked for their form, never against history."""
import glob, os

from test_flow import fill, front, lab, open_question
from test_order import order, three_steps


def mission_file(root, ident):
    return glob.glob(f"{root}/missions/{ident}-*.md")[0]


def saved(root, title, carries, what="Carry out the order it settled, one session per step."):
    out = lab(root, "mission", "new", title, "--carries", carries)
    ident = out.split()[1].rstrip(":")
    path = mission_file(root, ident)
    text = open(path).read().replace("\n---\n\n\n\n", f"\n---\n\n{what}\n\n", 1)
    open(path, "w").write(text)
    return ident, path


def test_a_mission_is_saved_launched_logged_and_closed(tmp_path):
    root = str(tmp_path)
    open_question(root)
    three_steps(root)
    card, d2 = order(root, ["G1.Q2.2", "G1.Q1", "G1.Q2"])
    assert "no open mission" in lab(root, "mission")
    # a mission carries a decision; it may be saved while the decision is open, and not launched until it is settled
    assert "is not one" in lab(root, "mission", "new", "Nothing", "--carries", "G1.Q1", ok=False)
    m1, path = saved(root, "The weight first", d2)
    assert m1 == "M1" and path.endswith("missions/M1-the-weight-first.md")
    assert "M1 (next): The weight first" in lab(root, "mission")
    assert "still open" in lab(root, "mission", "launch", ok=False)
    lab(root, "decide", d2, "--with", "Ada", "The weight on heads first, then the fair coin, then the rest of the biased coin.")
    assert "launched M1" in lab(root, "mission", "launch")
    assert "there is no next mission" in lab(root, "mission", "launch", ok=False)
    shown = lab(root, "mission", "M1")
    assert "M1 (current)" in shown and f"It carries {d2}" in shown
    # the steps its decision orders, in that order, as they stand now; nothing about them is copied into the file
    steps = shown.split("Steps", 1)[1]
    assert steps.index("G1.Q2.2") < steps.index("G1.Q1.1") < steps.index("G1.Q2.1")
    assert "G1.Q2.2" not in open(path).read()
    assert "mission M1 (current): The weight first" in lab(root, "now")
    lab(root, "mission", "log", "started G1.Q2.2 in its own session")  # the only current mission: no id needed
    assert "| started G1.Q2.2 in its own session" in open(path).read()
    assert "- 2026-01-02 09:30 started G1.Q2.2" in lab(root, "mission", "M1")
    assert "holds no |" in lab(root, "mission", "log", "a | b", ok=False)
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    out = lab(root, "mission", "close", "M1", "The weight on heads is built; the rest moved to the next mission.")
    assert "missions/M1-the-weight-first.md (done, kept)" in out and os.path.exists(path)
    assert f"| {d2} | agent | Mission done: M1 The weight first | The weight on heads is built" in open(f"{root}/log.md").read()
    kept = open(path).read()
    assert "status: done" in kept and "| done: The weight on heads is built" in kept and "| launched" in kept
    assert "M1" not in lab(root, "mission").split("\n")[0] and "1 closed mission: lab mission --all" in lab(root, "mission")
    assert "M1 (done): The weight first" in lab(root, "mission", "--all") and "mission M1" not in lab(root, "now")
    assert "Closed (done)" in lab(root, "mission", "M1")
    assert "M1 is done, not current" in lab(root, "mission", "log", "M1", "more", ok=False)
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    # a number is never given twice, even once its file is gone
    assert saved(root, "The rest", d2)[0] == "M2"


def test_several_missions_may_be_current_and_a_command_never_guesses_between_them(tmp_path):
    root = str(tmp_path)
    open_question(root)
    three_steps(root)
    _, d2 = order(root, ["G1.Q1", "G1.Q2"])
    lab(root, "decide", d2, "--with", "Ada", "The fair coin first, then the biased one.")
    saved(root, "The fair coin", d2)
    saved(root, "The biased coin", d2)
    assert "launched M2" in lab(root, "mission", "launch")  # with no id: the one saved last
    assert "launched M1" in lab(root, "mission", "launch", "M1")
    assert "2 missions are current (M1, M2): name the one you mean" in lab(root, "mission", "log", "a line", ok=False)
    lab(root, "mission", "log", "M2", "started G1.Q2.1")
    assert "started G1.Q2.1" in open(mission_file(root, "M2")).read() and "started G1.Q2.1" not in open(mission_file(root, "M1")).read()
    assert "Also current" in lab(root, "mission", "M1") and "M2 (current): The biased coin" in lab(root, "mission", "M1")
    assert "M1 is current, not next" in lab(root, "mission", "launch", "M1", ok=False)
    assert "no mission M9" in lab(root, "mission", "close", "M9", "x", ok=False)


def test_lab_check_holds_a_missions_form(tmp_path):
    root = str(tmp_path)
    open_question(root)
    _, path = saved(root, "A mission", "D1")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    front(path, carries="D9", phase="active")
    open(path, "a").write("not a line\n")
    open(f"{root}/missions/notes.txt", "w").write("x")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "`phase:` is not something a mission holds" in out
    assert "'D9' is not one" in out
    assert "is not `- <date> <time> | <what happened>`" in out
    assert "missions/notes.txt: missions/ holds only the missions" in out
    # a current mission carries a settled decision
    front(path, carries="D2")
    os.remove(f"{root}/missions/notes.txt")
    lab(root, "new", "decision", "Another", "--about", "G1")
    fill(sorted(glob.glob(f"{root}/decisions/D2-*.md"))[0], Seen="Something to discuss.")
    text = open(path).read().replace("phase: active\n", "").replace("status: next", "status: current").replace("not a line\n", "- 2026-01-02 09:40 | launched\n")
    open(path, "w").write(text)
    assert "is current and carries D2, which is still open" in lab(root, "check", "--no-rederive", ok=False)


def test_the_site_draws_the_line_that_closes_a_mission(tmp_path):
    import pytest
    pytest.importorskip("folio.views")
    from lab_kit.site import Provider
    root = str(tmp_path)
    open_question(root)
    saved(root, "A mission", "D1")
    lab(root, "mission", "launch")
    lab(root, "mission", "close", "The first question is open and its work has started.")
    site = Provider(root)
    assert "Mission done: M1 A mission" in site.get("D1").main + site.get("log").main


def test_the_refusals_a_mission_command_holds(tmp_path):
    root = str(tmp_path)
    open_question(root)
    lab(root, "mission", "new", "No purpose yet", "--carries", "D1")
    assert "say what the mission is for" in lab(root, "mission", "launch", ok=False)  # a mission says what it is for before it is launched
    path = mission_file(root, "M1")
    text = open(path).read().replace("\n---\n\n\n\n", "\n---\n\nTo start the first question.\n\n", 1)
    open(path, "w").write(text)
    lab(root, "mission", "launch")
    # an id with no message is not taken as the message
    assert 'say what happened after the mission: lab mission close M1 "<what>"' in lab(root, "mission", "close", "M1", ok=False)
    assert "say what happened after the mission" in lab(root, "mission", "log", "M1", ok=False)
    assert os.path.exists(path) and "Mission done" not in open(f"{root}/log.md").read()
    # a mission ended before its work is stopped, not done
    lab(root, "mission", "close", "--stopped", "The operator ended it to free the machines.")
    assert "status: stopped" in open(path).read() and "Mission stopped: M1" in open(f"{root}/log.md").read()


def test_lab_check_holds_a_missions_slots(tmp_path):
    root = str(tmp_path)
    open_question(root)
    _, path = saved(root, "A mission", "D1", what=" ".join(["word"] * 81))
    text = open(path).read().replace("## Rules\n\n", "## Rules\n\nnot a list item\n\n## Notes\n\nextra\n\n", 1)
    open(path, "w").write(text + "\n## After\n\nx\n")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "its description is 81 words, budget 80" in out
    assert "Rules is a list" in out
    assert "holds the slot 'After'" in out or "holds the slot 'Notes'" in out
    assert "Log is the last slot" in out
    open(path, "w").write("---\ntitle: [unclosed\n---\n\nx\n")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "cannot be read as a mission" in out
    assert "cannot be read" in lab(root, "mission")
    open(path, "w").write("---\ntitle: Short\ncarries: D1\n---\n\nFor the first question.\n\n## Log\n\n- 2026-01-02 09:30 | saved, carrying D1\n")
    assert "missing slot Rules" in lab(root, "check", "--no-rederive", ok=False)


def test_a_mission_has_a_status_and_one_written_by_the_last_kit_is_still_read(tmp_path):
    root = str(tmp_path)
    open_question(root)
    _, path = saved(root, "A mission", "D1")
    assert "status: next" in open(path).read()
    lab(root, "mission", "launch")
    assert "status: current" in open(path).read()
    front(path, status="paused")
    assert "`status:` is one of next, current, done, stopped; it is 'paused'" in lab(root, "check", "--no-rederive", ok=False)
    # a file 1.4.0 wrote has no status: read as current from its log, and the check asks for the status
    text = open(path).read().replace("status: paused\n", "")
    open(path, "w").write(text)
    assert "M1 (current)" in lab(root, "mission")
    assert "`status:` is one of" in lab(root, "check", "--no-rederive", ok=False)
    lab(root, "mission", "close", "Done.")
    assert "status: done" in open(path).read() and "the record is sound" in lab(root, "check", "--no-rederive")
    # numbers count the closed missions, kept and removed alike
    assert saved(root, "Another", "D1")[0] == "M2"
