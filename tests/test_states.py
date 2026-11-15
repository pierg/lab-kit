"""One set of states for every kind of card, and the rules that keep a card from saying something the record does not."""
import glob, os, subprocess

from test_flow import describe, experiment, fill, folder, front, lab, open_question, results
from test_integrity import WRITES, commit, done
from test_parked import park

PAST = "2000-01-01T00:00:00+00:00"


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


def test_so_far_older_than_a_result_under_it_is_stale(tmp_path):
    root = str(tmp_path)
    qdir = open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    fill(f"{qdir}/question.md", So_far="Nothing has been measured.")
    commit(root, "the question")
    git_env(root, "commit", "-q", "--amend", "--no-edit", "--date", PAST, GIT_COMMITTER_DATE=PAST)  # well before the result
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
    never = glob.glob(f"{root}/goals/G1-*/Q1-*/2-*/experiment.md")[0]
    front(reading, needs="[G1.Q1.2]")
    front(never, dropped='"Not needed after all."')  # dropped with no finished run: what needs it waits for ever
    assert "which is dropped: remove the need or replace it" in lab(root, "show", "G1.Q1.3")
