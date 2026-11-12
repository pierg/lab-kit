"""What the commands and `lab check` refuse, beyond the refusals the flow in test_flow.py already meets."""
import glob, os, subprocess, sys

from test_flow import RESOURCES, SAMPLE, SRC, describe, experiment, fill, folder, front, lab, locked, open_question, results


def test_what_the_writing_commands_refuse(tmp_path):
    root = str(tmp_path)
    open_question(root)

    # a card goes where the tree says, under a name, and a decision is about something that exists
    assert "a title is a name" in lab(root, "new", "decision", " ", ok=False)
    assert "--about G9" in lab(root, "new", "decision", "A second goal", "--about", "G9", ok=False)
    assert "goes under a question" in lab(root, "new", "experiment", "G1", "Under a goal", ok=False)
    assert "goes under a goal" in lab(root, "new", "question", "G1.Q1", "Under a question", "--from", "D1", ok=False)
    assert not glob.glob(f"{root}/decisions/D2-*") and len(glob.glob(f"{root}/goals/G1-*/*/")) == 1  # nothing was written

    # a log line is one of the kinds, about a card that exists, and holds no column mark
    assert "kind is one of" in lab(root, "log", "G1.Q1", "note", "Looked at it.", ok=False)
    assert "no goal, question" in lab(root, "log", "G1.Q9", "agent", "Looked at it.", ok=False)
    assert "holds no |" in lab(root, "log", "G1.Q1", "agent", "Chose a | b.", ok=False)
    assert open(f"{root}/log.md").read().count("\n- ") == 1  # only the decision's line

    # an answer is yes or no
    assert "an answer is yes or no" in lab(root, "answer", "G1.Q1", "maybe", "It depends.", ok=False)

    # a plan is reviewed before its lock, never after
    ident, d, command = experiment(root)
    lab(root, "lock", ident)
    assert "reviewed before its lock" in lab(root, "review", ident, "plan", "pass", "Read it.", ok=False)
    assert not os.path.exists(f"{d}/reviews.tsv")

    # an experiment is replaced once, and a replaced one takes no run
    lab(root, "new", "experiment", "G1.Q1", "Other sizes", "--replaces", ident, "--because", "Two sizes were too close to tell.")
    assert "already replaced by G1.Q1.2" in lab(root, "new", "experiment", "G1.Q1", "Again", "--replaces", ident, "--because", "Again.", ok=False)
    assert f"{ident} is replaced" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "--replaces names an experiment of the same question" in lab(root, "new", "build", "G1.Q1", "A build", "--replaces", "G1.Q1.2", "--because", "No.", ok=False)

    # a dropped experiment is neither locked nor run
    new = folder(root, "G1.Q1.2")
    front(f"{new}/experiment.md", dropped="The first pair was enough after all.")
    assert "G1.Q1.2 is dropped" in lab(root, "lock", "G1.Q1.2", ok=False)
    assert "G1.Q1.2 is dropped" in lab(root, "run", "G1.Q1.2", "--trial", "--wait", "--", *command, ok=False)
    assert not os.listdir(f"{root}/runs")


def test_a_run_stays_inside_what_is_left_of_a_resource(tmp_path):
    root = str(tmp_path)
    open_question(root)
    used = SAMPLE + "open(os.path.join(os.environ['LAB_RUN'], 'used.json'), 'w').write('{\"gpu\": 1}')\n"
    ident, d, command = experiment(root, uses="[gpu]", command=used)
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    lab(root, "lock", ident)

    # use outside a run counts: nine of the ten hours are gone, and one run may use two
    open(f"{root}/resources.toml", "w").write(RESOURCES + 'other_use = [{date = "2026-01-01", amount = 9, what = "the machine was left on overnight"}]\n')
    assert "more than the 1 left" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert not os.listdir(f"{root}/runs") and "gpu: 9 of 10 hours used" in lab(root, "now")

    # a lower cap is the agent's to write, and a run inside what is left starts
    front(f"{d}/experiment.md", override="{gpu: 1}")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)
    lab(root, "check", "--no-rederive")

    # more used than granted is a problem, however it was used
    open(f"{root}/resources.toml", "w").write(RESOURCES + 'other_use = [{date = "2026-01-01", amount = 12, what = "the machine was left on for a day"}]\n')
    assert "gpu: 13 hours used, 10 granted" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{root}/resources.toml", "w").write(RESOURCES + 'other_use = [{date = "2026-01-01", what = "no amount"}]\n')
    assert "each `other_use` entry" in lab(root, "check", "--no-rederive", ok=False)


def broken(root, path, change, *expect, rederive=False):
    """Change one file, see `lab check` name each problem, and put the file back."""
    text = open(path).read()
    os.chmod(path, 0o644)
    open(path, "w").write(change(text))
    out = lab(root, "check", *([] if rederive else ["--no-rederive"]), ok=False)
    open(path, "w").write(text)
    for e in expect:
        assert e in out, out


def test_what_the_check_refuses(tmp_path):
    root, ident, d, command = locked(tmp_path)
    lab(root, "run", ident, "--wait", "--", *command)
    results(d, "0.5")
    lab(root, "review", ident, "results", "pass", "Re-ran the command; it prints the row's value.")
    card = f"{d}/experiment.md"
    fill(card, Found="The error at 400 flips was {ratio} of the error at 100.", Means="It converges as the theory says.")
    assert "the record is sound" in lab(root, "check")

    # a card stays short, and writes only what is its to write: never a state, never a key the model does not give it
    broken(root, card, lambda t: t.replace("It converges as the theory says.", "word " * 151), "Means is 151 words, budget 150")
    broken(root, card, lambda t: t.replace("Measures the error", "word " * 71 + "Measures the error"), "its description is ", "budget 70")
    broken(root, card, lambda t: t.replace("\n---\n", "\nstatus: done\n---\n", 1), "writes `status:`, which is worked out from the record")
    broken(root, card, lambda t: t.replace("\n---\n", "\nowner: someone\n---\n", 1), "`owner:` is not something a experiment card holds")
    broken(root, card, lambda t: t.replace("## Means", "## Meaning"), "missing slot Means")

    # at most six lines on a side, and one answer
    seven = "".join(f"\n- and bar {n} holds (`ratio < 0.{n}`)" for n in range(1, 6))
    broken(root, card, lambda t: t.replace("(`ratio > 0.4`)", "(`ratio > 0.4`)" + seven), "confirmed-if has 7 lines", "changed after the lock")
    broken(root, card, lambda t: t.replace("- the error at 400", "- answer: the error at 400").replace("- and over", "- answer: and over"), "more than one confirmed-if line is marked `answer:`")

    # a result still prints from the sealed run, is the one the review read, and the run is as it was sealed
    rows = f"{d}/results.tsv"
    broken(root, rows, lambda t: t.replace("\t0.5\t", "\t0.4\t"), "its command prints '0.5', the row says '0.4'", "changed after the review that passed them", rederive=True)
    broken(root, rows, lambda t: t.replace("\tpercent\t", "\tratio\t"), "reads 'ratio'; it is percent, points or empty")
    sealed = glob.glob(f"{root}/runs/*/ratio.txt")[0]
    broken(root, sealed, lambda t: "0.4\n", "ratio.txt does not match its hash")
    os.chmod(sealed, 0o444)

    # the method and the skills are the kit's: an edited copy is a problem, and `lab init` restores it
    broken(root, f"{root}/.lab/METHOD.md", lambda t: t + "\n8. A local rule.\n", ".lab/METHOD.md: differs from the installed kit")
    open(f"{root}/.agents/skills/lab-work/SKILL.md", "a").write("\nA local habit.\n")
    assert ".agents/skills/lab-work/SKILL.md: differs from the installed kit" in lab(root, "check", "--no-rederive", ok=False)
    lab(root, "init")
    assert "the record is sound" in lab(root, "check")

    # a trial run never gives a result
    second, d2, command2 = experiment(root, title="Error at 1600 flips")
    lab(root, "run", second, "--trial", "--wait", "--", *command2)
    results(d2, "0.5")
    assert "has results with no locked plan and finished run behind them" in lab(root, "check", "--no-rederive", ok=False)
    assert "no finished run with results" in lab(root, "review", second, "results", "pass", "The trial printed it.", ok=False)
    os.remove(f"{d2}/results.tsv")
    describe(f"{d2}/experiment.md", "Measures the error at a third sample size.")
    lab(root, "check", "--no-rederive")

    # a result of a replaced experiment is no longer named on a card
    qcard = f"{os.path.dirname(d)}/question.md"
    fill(qcard, So_far="The error at 400 flips is {G1.Q1.1:ratio} of the error at 100.")
    lab(root, "check", "--no-rederive")
    lab(root, "new", "experiment", "G1.Q1", "The same, with more estimates", "--replaces", ident, "--because", "Two hundred estimates were too few to trust.")
    assert "So far names {G1.Q1.1:ratio}, whose experiment is replaced" in lab(root, "check", "--no-rederive", ok=False)


def test_a_reader_that_closes_the_pipe_ends_the_command_quietly(tmp_path):
    root = str(tmp_path)
    open_question(root)
    for entry, quiet in (("run", True), ("main", False)):  # `run` is what the `lab` command starts
        p = subprocess.Popen([sys.executable, "-c", f"import sys; from lab_kit import cli; sys.argv = ['lab', 'now']; sys.exit(cli.{entry}())"],
                             cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "PYTHONPATH": SRC})
        p.stdout.close()  # as `lab now | head -1` does once it has its line
        code, said = p.wait(), p.stderr.read().decode()
        p.stderr.close()
        assert ((code, said) == (0, "")) == quiet, (entry, code, said)
