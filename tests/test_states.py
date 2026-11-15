"""One set of states for every kind of card, and the rules that keep a card from saying something the record does not."""
import glob, os, subprocess

from lab_kit import record

from test_flow import describe, experiment, fill, folder, front, lab, open_question, results
from test_integrity import WRITES, commit, done
from test_parked import park

PAST = "2000-01-01T00:00:00+00:00"


def git_out(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def git_env(root, *args, **env):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, check=True, capture_output=True, env={**os.environ, **env})


def test_waiting_on_is_for_what_is_outside_the_lab(tmp_path):
    root = str(tmp_path)
    open_question(root)
    lab(root, "new", "reading", "G1.Q1", "Which sizes to compare")
    card = f"{folder(root, 'G1.Q1.1')}/reading.md"
    describe(card, "Reads what the sampler already wrote.")
    front(card, waiting_on='"The cluster account, which the department opens on Monday"')
    assert "G1.Q1.1 reading (waiting)" in lab(root, "show", "G1.Q1.1") and "the record is sound" in lab(root, "check", "--no-rederive")
    front(card, waiting_on='"Whatever Does the error halve (G1.Q1) finds first"')  # the lab's own work: refused, since it would never clear
    assert "`waiting_on:` names G1.Q1, which is part of the lab" in lab(root, "check", "--no-rederive", ok=False)


def test_so_far_says_what_was_learned_and_never_where_a_step_stands(tmp_path):
    root = str(tmp_path)
    qdir = open_question(root)
    fill(f"{qdir}/question.md", So_far="The error at 400 flips is about half the error at 100, on one seed.")
    assert "the record is sound" in lab(root, "check", "--no-rederive")
    fill(f"{qdir}/question.md", So_far="Error at 100 and at 400 flips (G1.Q1.1) is running, and there is no result yet.")
    assert "So far says 'is running'" in lab(root, "check", "--no-rederive", ok=False)


def test_a_time_in_utc_written_with_z_is_read():  # git 2.56 writes UTC as Z; Python 3.10 reads only +00:00
    assert record.moment("2000-01-01T00:00:00Z") == record.moment("2000-01-01T00:00:00+00:00") is not None


def test_so_far_older_than_a_result_under_it_is_stale(tmp_path):
    root = str(tmp_path)
    qdir = open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    fill(f"{qdir}/question.md", So_far="Nothing has been measured.")
    git_env(root, "init", "-q")
    git_env(root, "add", "-A")
    git_env(root, "commit", "-qm", "the question", GIT_AUTHOR_DATE=PAST, GIT_COMMITTER_DATE=PAST)  # well before the result
    assert git_out(root, "log", "-1", "--format=%cI").startswith("2000-01-01")
    out = lab(root, "log", ident, "result", "The error halves.", "It converges as the theory says.")
    assert "So far of G1.Q1" in out  # the command reminds the agent
    commit(root, "the result")
    assert f"So far was last committed before the result of {ident}" in lab(root, "check", "--no-rederive", ok=False)
    fill(f"{qdir}/question.md", So_far="The error at 400 flips is {G1.Q1.1:ratio} of the error at 100.")
    commit(root, "So far brought up to date")
    assert "the record is sound" in lab(root, "check", "--no-rederive")


def test_an_answer_is_yes_no_or_mixed_and_never_rests_on_a_void_experiment(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    results(d)
    lab(root, "review", ident, "results", "fail", "The seed was fixed after a first look.")
    assert f"{ident} experiment (done, void)" in lab(root, "show", ident)
    assert "has no finished experiment to rest an answer on" in lab(root, "answer", "G1.Q1", "yes", "It halves.", ok=False)
    assert "void: its results review failed, so it never runs again" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    again, d2, command2 = experiment(root, title="The same, with the seed fixed first", command=WRITES % "0.5")
    lab(root, "lock", again)
    lab(root, "run", again, "--wait", "--", *command2)
    done(root, again, d2)
    lab(root, "answer", "G1.Q1", "mixed", "It halves at 400 flips and not at 1600.")
    assert "G1.Q1 (done, mixed)" in lab(root, "show", "G1.Q1")


def test_a_decision_drops_what_it_names_once_it_is_settled(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, _ = experiment(root)
    card, dn = park(root, ident, "Drop the two sizes", "", key="drops")
    front(card, about=f"[{ident}]")
    assert f"{ident} experiment (open)" in lab(root, "show", ident)  # an open decision drops nothing yet
    lab(root, "decide", dn, "--with", "Ada", "Drop it: one size answers the question.")
    assert f"{ident} experiment (dropped)" in lab(root, "show", ident)
    front(card, about="[G1.Q1]")
    assert f"drops names {ident}, which is not under `about:`" in lab(root, "check", "--no-rederive", ok=False)
    front(card, about="[G1.Q1]", drops="[G1.Q9.9]")
    assert "drops names 'G1.Q9.9', which is not a question or a step of the lab" in lab(root, "check", "--no-rederive", ok=False)


def test_a_need_is_met_by_what_a_replaced_experiment_made(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    lab(root, "new", "experiment", "G1.Q1", "The same, with the seed fixed first", "--replaces", ident, "--because", "The seed was fixed after a first look.")
    lab(root, "new", "reading", "G1.Q1", "What the first run wrote")
    reading = f"{folder(root, 'G1.Q1.3')}/reading.md"
    describe(reading, "Reads the files the first run left.")
    front(reading, needs=f"[{ident}]")
    assert f"{ident} experiment (replaced)" in lab(root, "show", ident) and "G1.Q1.3 reading (open)" in lab(root, "show", "G1.Q1.3")
    front(f"{d}/experiment.md", dropped='"Dropped too: the seed is fixed in the next one."')
    assert f"{ident} experiment (dropped)" in lab(root, "show", ident) and "G1.Q1.3 reading (open)" in lab(root, "show", "G1.Q1.3")  # dropped, with a finished run: still met
    never = glob.glob(f"{root}/goals/G1-*/Q1-*/2-*/experiment.md")[0]
    front(reading, needs="[G1.Q1.2]")
    front(never, dropped='"Not needed after all."')  # dropped with no finished run: what needs it waits for ever
    assert "which is dropped: remove the need or replace it" in lab(root, "show", "G1.Q1.3")


def test_a_test_is_answered_yes_no_or_mixed_and_an_estimate_with_what_was_found(tmp_path):
    root = str(tmp_path)
    qdir = open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    assert "is a test: it is answered yes, no or mixed" in lab(root, "answer", "G1.Q1", "found", "The ratio is 0.5.", ok=False)
    front(f"{qdir}/question.md", kind="estimate")
    assert "is an estimate: it is answered `found`" in lab(root, "answer", "G1.Q1", "yes", "It halves.", ok=False)
    lab(root, "answer", "G1.Q1", "found", "The error at 400 flips is 0.5 of the error at 100, on one seed.")
    assert "G1.Q1 (done, found)" in lab(root, "show", "G1.Q1") and "the record is sound" in lab(root, "check", "--no-rederive")
    front(f"{qdir}/question.md", kind="test")
    assert "is a test and is answered found" in lab(root, "check", "--no-rederive", ok=False)
    front(f"{qdir}/question.md", kind="guess")
    assert "`kind:` is test or estimate" in lab(root, "check", "--no-rederive", ok=False)
    front(f"{qdir}/question.md", kind="[estimate]")
    assert "`kind:` holds one value, not a list" in lab(root, "check", "--no-rederive", ok=False)  # reported, not a crash


def test_a_question_with_nothing_left_under_it_is_the_agents_next_step(tmp_path):
    root = str(tmp_path)
    open_question(root)
    yours = lambda: lab(root, "now").split("Yours next")[1].split("Not yours")[0]
    assert "G1.Q1" in yours() and "nothing under it yet: plan its first experiment" in yours()
    ident, d, command = experiment(root, command=WRITES % "0.5")
    assert "G1.Q1 " not in yours().replace(ident, "")  # a step under it can move: the step is listed, not the question
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    results(d)
    lab(root, "review", ident, "results", "fail", "The seed was fixed after a first look.")
    assert "no experiment finished that is not void" in yours()  # a void experiment answers nothing
    again, d2, command2 = experiment(root, title="The same, with the seed fixed first", command=WRITES % "0.5")
    lab(root, "lock", again)
    lab(root, "run", again, "--wait", "--", *command2)
    done(root, again, d2)
    assert f"{again} finished: answer it (lab answer G1.Q1 ...)" in yours()
    card, dn = park(root, "G1.Q1", "Whether to go on", "", key="holds")
    assert "G1.Q1" not in yours()  # what an open decision holds waits on the decision
    lab(root, "decide", dn, "--with", "Ada", "Go on.")
    lab(root, "answer", "G1.Q1", "yes", "It halves at 400 flips.")
    assert "G1 " in yours() and "bring closing it (reached or dropped) to the operator" in yours()
