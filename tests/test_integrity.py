"""What cannot be done to a lab without `lab check` saying so, and what no command stops on."""
import concurrent.futures, glob, json, os, re, shutil, signal, subprocess, sys, time

from test_flow import RESOURCES, SRC, describe, experiment, fill, folder, front, git, lab, locked, open_question, results

WRITES = "import os\nopen(os.path.join(os.environ['LAB_RUN'], 'ratio.txt'), 'w').write('%s\\n')\n"
USES = "open(os.path.join(os.environ['LAB_RUN'], 'used.json'), 'w').write('{\"gpu\": %s}')\n"


def done(root, ident, d, value="0.5"):
    results(d, value)
    lab(root, "review", ident, "results", "pass", "Re-ran the command; it prints the row's value.")
    fill(f"{d}/experiment.md", Found="The error at 400 flips was {ratio} of the error at 100.", Means="It converges as the theory says.")


def under(tmp_path, name):
    os.makedirs(tmp_path / name)
    return str(tmp_path / name)


def commit(root, message="the lab"):
    if not os.path.isdir(f"{root}/.git"):
        git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)


def test_a_run_is_listed_and_is_never_removed_or_rewritten(tmp_path):
    # a run that refutes is removed from the store, to run again: the list in git still has it
    root = under(tmp_path, "removed")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.95")
    lab(root, "run", ident, "--trial", "--wait", "--", *command)
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    rows = [l.split("\t") for l in open(f"{d}/runs.tsv").read().splitlines()]
    assert rows[0] == ["run", "kind", "what", "at", "exit", "seal", "used", "note"] and [(r[1], r[2]) for r in rows[1:]] == [("trial", "started"), ("trial", "ended"), ("run", "started"), ("run", "ended")]
    trial, run = (glob.glob(f"{root}/runs/{r[0]}")[0] for r in (rows[1], rows[3]))
    assert rows[4][5] == json.load(open(f"{run}/run.json"))["seal"]
    done(root, ident, d, "0.95")
    assert "the record is sound" in lab(root, "check")
    kept = str(tmp_path / "kept")
    shutil.copytree(run, kept)
    shutil.rmtree(run)
    assert "takes no more" in lab(root, "run", ident, "--wait", "--", sys.executable, "-c", "pass", ok=False)  # the list says it ran and finished
    assert f"{os.path.basename(run)}: is listed in" in lab(root, "check", "--no-rederive", ok=False) and "a run is never removed" in lab(root, "check", "--no-rederive", ok=False)
    assert "listed in runs.tsv, and not here" in lab(root, "runs") and "its folder is not in the store here" in lab(root, "show", ident)
    shutil.copytree(kept, run)
    assert "the record is sound" in lab(root, "check")

    # a trial the lock lists is a run like any other
    shutil.rmtree(trial)
    assert f"{os.path.basename(trial)}: is listed in" in lab(root, "check", "--no-rederive", ok=False)

    # a failed run's record rewritten to say it finished, with its seal worked out again
    root = under(tmp_path, "forged")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5" + "raise SystemExit(3)\n")
    lab(root, "lock", ident)
    assert "failed (exit 3)" in lab(root, "run", ident, "--wait", "--", *command)
    rj = glob.glob(f"{root}/runs/*/run.json")[0]
    sys.path.insert(0, SRC)
    from lab_kit import record as R
    record = json.load(open(rj))
    record["exit"] = 0
    record["seal"] = R.seal_of(record)
    os.chmod(rj, 0o644)
    open(rj, "w").write(json.dumps(record, indent=1) + "\n")
    done(root, ident, d)
    assert "is not the run that runs.tsv recorded when it ended" in lab(root, "check", "--no-rederive", ok=False)

    # a run put in the store by hand, which no `lab run` listed
    os.remove(f"{d}/runs.tsv")
    assert "is not listed in" in lab(root, "check", "--no-rederive", ok=False)


def test_a_clone_without_the_store_knows_what_ran(tmp_path):
    root = under(tmp_path, "lab")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    commit(root)
    assert "the record is sound" in lab(root, "check", "--strict")
    clone = str(tmp_path / "clone")
    subprocess.run(["git", "clone", "-q", root, clone], check=True)
    out = lab(clone, "check")
    assert "the store is not here" in out and "the record is sound" in out
    assert "not everything could be checked" in lab(clone, "check", "--strict", ok=False)  # what CI asks
    assert "(done, confirmed)" in lab(clone, "show", ident)
    assert "takes no more" in lab(clone, "run", ident, "--wait", "--", sys.executable, "-c", "pass", ok=False)
    assert not os.path.exists(f"{clone}/runs") and not glob.glob(f"{clone}/.lab/running/2*")

    # with no commit the history cannot be checked: a note, and a failure when the check is strict
    fresh = under(tmp_path, "fresh")
    open_question(fresh)
    assert "permanence against history was not checked" in lab(fresh, "check", "--strict", ok=False)
    assert "the record is sound" in lab(fresh, "check")


def test_the_first_run_runs_the_plan_that_was_locked(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, uses="[gpu]", command=WRITES % "0.5" + USES % 1)

    # nothing runs on a metered resource before its plan is reviewed, a trial included
    assert "a trial too" in lab(root, "run", ident, "--trial", "--wait", "--", *command, ok=False)
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    assert "finished" in lab(root, "run", ident, "--trial", "--wait", "--", *command)

    # plan/ holds files: what a link points at is not pinned
    os.makedirs(f"{root}/code")
    os.symlink(f"{root}/code", f"{d}/plan/code")
    assert "plan/ holds a link, code" in lab(root, "lock", ident, ok=False)
    assert "plan/ holds a link" in lab(root, "check", "--no-rederive", ok=False)
    os.remove(f"{d}/plan/code")
    lab(root, "review", ident, "plan", "pass", "Read again.")
    lab(root, "lock", ident)
    assert json.load(open(f"{d}/lock.json"))["plan"]

    # the reviewed and locked plan is the "before" of the first run
    open(f"{d}/plan/sample.py", "a").write("# another apparatus\n")
    refused = lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "plan/ is not what was locked" in refused and "--changed" in refused and len(glob.glob(f"{root}/runs/*")) == 1
    assert "finished" in lab(root, "run", ident, "--wait", "--changed", "A comment was added to the sampler.", "--", *command)
    assert "changed since the lock: A comment was added to the sampler." in lab(root, "show", ident)
    lab(root, "check", "--no-rederive")

    # and a first run recorded with another plan and no reason is a problem
    two, d2, command2 = experiment(root, title="A second pair of sizes", command=WRITES % "0.5")
    lab(root, "lock", two)
    lock = json.load(open(f"{d2}/lock.json"))
    lab(root, "run", two, "--wait", "--", *command2)
    open(f"{d2}/lock.json", "w").write(json.dumps({**lock, "plan": "0" * 64}, indent=1) + "\n")
    assert "ran a plan/ that differs from the one that was locked" in lab(root, "check", "--no-rederive", ok=False)


def test_an_answer_rests_on_an_experiment_and_is_written_by_the_command(tmp_path):
    root = str(tmp_path)
    qdir = open_question(root)
    card = open(f"{qdir}/question.md").read()

    # by hand, with nothing under the question
    front(f"{qdir}/question.md", answer='"yes"', answered="2026-01-02")
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "is answered with no finished experiment" in out and "was not recorded by `lab answer`" in out
    open(f"{qdir}/question.md", "w").write(card)

    # by hand, on a reading alone
    lab(root, "new", "reading", "G1.Q1", "The estimates that missed")
    r = f"{folder(root, 'G1.Q1.1')}/reading.md"
    describe(r, "Reads the estimates that fell outside the band.")
    fill(r, Looks_at="The 12 estimates outside the band.", Seen="- Nine used the short sample.", Suggests="Fix the seed.")
    front(f"{qdir}/question.md", answer='"yes"', answered="2026-01-02")
    assert "a reading suggests and answers nothing" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{qdir}/question.md", "w").write(card)

    # by hand, on a done experiment, with no line from `lab answer`
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    front(f"{qdir}/question.md", answer='"yes"', answered="2026-01-02")
    assert "was not recorded by `lab answer`" in lab(root, "check", "--no-rederive", ok=False)
    assert "G1.Q1 is yes, not open" in lab(root, "answer", "G1.Q1", "yes", "The ratio is one half.", ok=False)
    open(f"{qdir}/question.md", "w").write(card)

    # the command validates before it writes: a refused log line leaves the card as it was
    assert "holds no |" in lab(root, "answer", "G1.Q1", "yes", "The ratio | is one half.", ok=False)
    assert open(f"{qdir}/question.md").read() == card
    lab(root, "answer", "G1.Q1", "yes", "The ratio is one half.")
    assert "the record is sound" in lab(root, "check")


def test_amounts_and_settled_decisions_change_only_out_of_a_decision(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, uses="[gpu]", command=WRITES % "0.5" + USES % 2)
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")

    # a metered resource names the settled decision that set its amounts
    open(f"{root}/resources.toml", "w").write(RESOURCES.replace('from = "D1"\n', ""))
    assert "whose amounts name no settled decision" in lab(root, "lock", ident, ok=False)
    assert "gpu: its amounts come out of a decision" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{root}/resources.toml", "w").write(RESOURCES.replace('from = "D1"', 'from = "D7"'))
    assert "gpu: its amounts come out of a decision" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{root}/resources.toml", "w").write(RESOURCES)
    lab(root, "lock", ident)
    open(f"{root}/resources.toml", "w").write(RESOURCES.replace('from = "D1"\n', ""))
    assert "its amounts come out of a decision" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    open(f"{root}/resources.toml", "w").write(RESOURCES)
    commit(root)
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    # the grant raised by hand: git saw the old amounts
    open(f"{root}/resources.toml", "w").write(RESOURCES.replace("granted = 10", "granted = 1000").replace("per_run = 2", "per_run = 500"))
    assert "`unit` changed since the last commit" in lab(root, "check", "--no-rederive", ok=False)
    commit(root, "more")
    assert "history: resources.toml: gpu: `granted`, `per_run` or `unit` changed in " in lab(root, "check", "--no-rederive", ok=False)

    # the same change out of a decision
    lab(root, "new", "decision", "A larger grant on the GPU", "--about", "gpu")
    card = glob.glob(f"{root}/decisions/D2-*.md")[0]
    fill(card, Seen="The settled work needs more hours than were granted.")
    open(f"{root}/resources.toml", "w").write(RESOURCES.replace("granted = 10", "granted = 1000").replace("per_run = 2", "per_run = 500").replace('from = "D1"', 'from = "D2"'))
    assert "its amounts come out of a decision" in lab(root, "check", "--no-rederive", ok=False)  # D2 is still open
    lab(root, "decide", "D2", "--with", "Ada", "A thousand hours, five hundred for one run: the full comparison needs them.")
    git(root, "reset", "-q", "--soft", "HEAD~1")  # the change is committed once, with the decision it came out of
    commit(root, "a larger grant, out of D2")
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    # a settled decision is not reworded, reopened or removed
    text = open(card).read()
    open(card, "w").write(text.replace("A thousand hours", "Ten thousand hours"))
    assert "its Decided text has changed since; a change of mind is a new decision" in lab(root, "check", "--no-rederive", ok=False)
    open(card, "w").write(text.replace('with: "Ada"', 'with: "Grace"'))
    assert "has changed since" in lab(root, "check", "--no-rederive", ok=False)
    os.remove(card)
    assert "was committed and is gone" in lab(root, "check", "--no-rederive", ok=False)
    open(card, "w").write(text)
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    # the list of runs only grows
    lab(root, "run", ident, "--wait", "--", *command)
    commit(root, "the run")
    rows = open(f"{d}/runs.tsv").read()
    open(f"{d}/runs.tsv", "w").write(rows.replace("\tended\t", "\tended \t"))
    assert "history: " in lab(root, "check", "--no-rederive", ok=False) and "runs.tsv: a line committed in" in lab(root, "check", "--no-rederive", ok=False)


def alive(pid):
    try:
        return open(f"/proc/{pid}/stat").read().split()[2] != "Z"
    except OSError:
        return False


def test_closing_a_dead_run_stops_what_it_left_and_records_what_it_used(tmp_path):
    root = str(tmp_path)
    open_question(root)
    sleeper = "import os, time\nopen(os.path.join(os.environ['LAB_RUN'], 'pid'), 'w').write(str(os.getpid()))\n%stime.sleep(60)\n"
    ident, d, command = experiment(root, uses="[gpu]", command=sleeper % (USES % 1))
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    lab(root, "lock", ident)

    def start_and_kill_the_supervisor():
        run_id = re.search(r"started (\S+):", lab(root, "run", ident, "--", *command)).group(1)
        rdir = f"{root}/.lab/running/{run_id}"
        for _ in range(100):
            if os.path.exists(f"{rdir}/pid") and open(f"{rdir}/pid").read():
                break
            time.sleep(0.05)
        child = int(open(f"{rdir}/pid").read())
        os.kill(json.load(open(f"{rdir}/run.json"))["pid"], signal.SIGKILL)  # the supervisor dies; the command is in a group of its own
        time.sleep(0.3)
        assert alive(child) and "its process is gone" in lab(root, "runs")
        return run_id, child

    # the run said what it used before it died: closing it stops the command and keeps that amount
    run_id, child = start_and_kill_the_supervisor()
    assert "is still going: its process is gone" in lab(root, "run", ident, "--", *command, ok=False)
    assert "is not a run's id" in lab(root, "runs", "close", "../../outside", "x", ok=False)
    lab(root, "runs", "close", run_id, "the machine was shut down")
    time.sleep(0.2)
    assert not alive(child)
    assert "used 1 hours" in lab(root, "runs") and "gpu: 1 of 10 hours used" in lab(root, "now")
    lab(root, "check", "--no-rederive")

    # a run that wrote nothing: the amount is stated by hand, and recorded as that
    open(f"{d}/plan/sample.py", "w").write(sleeper % "")
    time.sleep(1.1)
    run_id = re.search(r"started (\S+):", lab(root, "run", ident, "--changed", "The sampler no longer says what it used.", "--", *command)).group(1)
    rdir = f"{root}/.lab/running/{run_id}"
    for _ in range(100):
        if os.path.exists(f"{rdir}/pid") and open(f"{rdir}/pid").read():
            break
        time.sleep(0.05)
    child = int(open(f"{rdir}/pid").read())
    os.kill(json.load(open(f"{rdir}/run.json"))["pid"], signal.SIGKILL)
    time.sleep(0.3)
    assert "--used laptop=2" in lab(root, "runs", "close", run_id, "killed", "--used", "laptop=2", ok=False)  # not a metered resource
    assert "--used gpu=-1" in lab(root, "runs", "close", run_id, "killed", "--used", "gpu=-1", ok=False)
    assert alive(child)  # a refused close has done nothing
    lab(root, "runs", "close", run_id, "killed", "--used", "gpu=1.5")
    time.sleep(0.2)
    assert not alive(child) and "used 1.5 hours (stated by hand when it was closed)" in lab(root, "show", ident)
    assert "gpu: 2.5 of 10 hours used" in lab(root, "now")
    lab(root, "check", "--no-rederive")


def test_what_a_run_says_it_used_is_an_amount(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, uses="[gpu]", command=WRITES % "0.5" + USES % "NaN")
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    lab(root, "lock", ident)
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "used.json gives no amount for gpu" in out and "did not record what it used" in out
    assert "gpu: 0 of 10 hours used" in lab(root, "now") and "nan" not in lab(root, "now").lower()


def test_a_run_may_write_any_file_and_a_run_is_named_by_its_id(tmp_path):
    root = str(tmp_path)
    open_question(root)
    nested = WRITES % "0.5" + "os.makedirs(os.environ['LAB_RUN'] + '/sub')\nopen(os.environ['LAB_RUN'] + '/sub/run.json', 'w').write('{}')\n"
    ident, d, command = experiment(root, command=nested)
    lab(root, "lock", ident)
    out = lab(root, "run", ident, "--wait", "--", *command)
    assert "finished" in out and "not yet in the store" not in out and "in the store" in lab(root, "runs")
    assert "sub/run.json" in json.load(open(glob.glob(f"{root}/runs/*/run.json")[0]))["files"]
    done(root, ident, d)
    assert "the record is sound" in lab(root, "check")

    # a run's id is checked before any path is made from it
    env = {**os.environ, "PYTHONPATH": SRC, "LAB_STORE_HOST": "nowhere.invalid"}
    p = subprocess.run([sys.executable, "-m", "lab_kit.cli", "runs", "fetch", "../../../outside"], cwd=root, capture_output=True, text=True, env=env)
    assert p.returncode != 0 and "is not a run's id" in p.stderr and "Traceback" not in p.stderr and not os.path.exists(f"{root}/../outside")
    p = subprocess.run([sys.executable, "-m", "lab_kit.cli", "runs", "fetch", "20260102-0930_G1.Q1.1_abcd"], cwd=root, capture_output=True, text=True, env=env)
    assert p.returncode != 0 and "could not be copied from nowhere.invalid" in p.stderr and "Traceback" not in p.stderr and not os.path.exists(f"{root}/.lab/fetched/20260102-0930_G1.Q1.1_abcd")

    # a result's command reads the sealed run, and ends
    rows = open(f"{d}/results.tsv").read()
    open(f"{d}/results.tsv", "w").write(rows.replace("cat $RUN/ratio.txt", "echo 0.5"))
    assert "its command never reads `$RUN`" in lab(root, "check", "--no-rederive", ok=False)
    open(f"{d}/results.tsv", "w").write(rows.replace("cat $RUN/ratio.txt", "sleep 5; cat $RUN/ratio.txt"))
    open(f"{root}/lab.toml", "a").write("rederive_timeout = 0.5\n")
    assert "did not print the value within 0.5 seconds" in lab(root, "check", ok=False)


def test_a_command_validates_everything_before_it_writes_and_quotes_what_it_writes(tmp_path):
    root = str(tmp_path)
    open_question(root)

    # a title may hold anything a title holds
    assert "has a letter or a digit" in lab(root, "new", "decision", "---", ok=False)
    lab(root, "new", "decision", "A --- B: yes | no")
    card = glob.glob(f"{root}/decisions/D2-*.md")[0]
    assert "D2 A --- B: yes | no" in lab(root, "show", "D2")
    fill(card, Seen="Two options --- and a line of dashes below.\n\n---\n\nStill what was seen.")
    assert "Still what was seen." in lab(root, "show", "D2")

    # the one who decided is written so that the card reads back, and the log line is written too
    lab(root, "decide", "D2", "--with", "Ada: the operator", "It was decided.")
    assert 'with: "Ada: the operator"' in open(card).read() and "decided 2026-01-02 with Ada: the operator" in lab(root, "show", "D2")
    assert "| D2 | decision | Decided: A --- B: yes / no | It was decided." in open(f"{root}/log.md").read()
    assert "the record is sound" in lab(root, "check", "--no-rederive")

    # a decision already written on by hand is not decided over
    lab(root, "new", "decision", "A third")
    third = glob.glob(f"{root}/decisions/D3-*.md")[0]
    fill(third, Seen="Something was seen.")
    open(third, "a").write("\n## Decided\n\nBy hand.\n")
    before = open(third).read()
    assert "already holds a Decided" in lab(root, "decide", "D3", "--with", "Ada", "It was decided.", ok=False) and open(third).read() == before

    # a log line with a column mark too many is a problem, not a shorter line
    open(f"{root}/log.md", "a").write("- 10:00 | G1 | agent | a | b | c\n")
    assert "holds no other |" in lab(root, "check", "--no-rederive", ok=False)


def test_commands_given_at_once_do_not_take_the_same_number_or_start_two_runs(tmp_path):
    root = str(tmp_path)
    open_question(root)
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        made = list(pool.map(lambda i: lab(root, "new", "build", "G1.Q1", f"Build {i}"), range(6)))
    assert sorted(re.search(r"made (\S+):", m).group(1) for m in made) == [f"G1.Q1.{n}" for n in range(1, 7)]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: lab(root, "log", "G1.Q1", "agent", f"Line number {i}."), range(16)))
    text = open(f"{root}/log.md").read()
    assert text.count("Line number") == 16 and text.count("## ") == 1
    for n in range(1, 7):
        front(f"{folder(root, f'G1.Q1.{n}')}/build.md", dropped="Made only to take a number.")
        describe(f"{folder(root, f'G1.Q1.{n}')}/build.md", "A build made to take a number.")
    ident, d, command = experiment(root, command="import os, time\ntime.sleep(1.5)\n" + WRITES.split("\n", 1)[1] % "0.5")
    lab(root, "lock", ident)

    def start(i):
        p = subprocess.run([sys.executable, "-m", "lab_kit.cli", "run", ident, "--", *command], cwd=root, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": SRC})
        return p.stdout + p.stderr
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        out = list(pool.map(start, range(4)))
    assert sum("started " in o for o in out) == 1 and sum("is still going" in o for o in out) == 3
    for _ in range(100):
        if "running" not in lab(root, "runs"):
            break
        time.sleep(0.1)
    assert len(glob.glob(f"{root}/runs/*{ident}*")) == 1
    lab(root, "check", "--no-rederive")


def test_what_points_at_itself_is_reported_and_stops_nothing(tmp_path):
    root = str(tmp_path)
    qdir = open_question(root)
    a, da, _ = experiment(root, title="One pair of sizes")
    b, db, _ = experiment(root, title="Another pair of sizes")
    front(f"{da}/experiment.md", replaces=b, because='"The other pair was too close."')
    front(f"{db}/experiment.md", replaces=a, because='"The first pair was too close."')
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "which replaces it in turn" in out and "(replaced)" in lab(root, "show", a)
    front(f"{db}/experiment.md", replaces=b)
    assert "is not another experiment of its question" in lab(root, "check", "--no-rederive", ok=False)
    for card in (f"{da}/experiment.md", f"{db}/experiment.md"):
        text = re.sub(r"^(replaces|because):.*\n", "", open(card).read(), flags=re.M)
        open(card, "w").write(text)
    front(f"{da}/experiment.md", needs=f"[{b}]")
    front(f"{db}/experiment.md", needs=f"[{a}]")
    assert "needs itself, directly or through what it needs" in lab(root, "check", "--no-rederive", ok=False)
    assert "Not yours to move yet" in lab(root, "now") and "planned)" in lab(root, "brief", "G1.Q1")
    front(f"{da}/experiment.md", needs="[]")
    front(f"{db}/experiment.md", needs="[]")
    lab(root, "new", "question", "G1", "A second question", "--from", "D1")
    q2 = glob.glob(f"{root}/goals/G1-*/Q2-*")[0]
    describe(f"{q2}/question.md", "What follows from the first.")
    front(f"{qdir}/question.md", needs="[G1.Q2]")
    front(f"{q2}/question.md", needs="[G1.Q1]")
    assert "question.md: needs itself" in lab(root, "check", "--no-rederive", ok=False)
    assert "Where we are coming from" in lab(root, "brief", "G1.Q1")


def test_a_run_that_never_reports_back_is_declared_lost(tmp_path):
    sys.path.insert(0, SRC)
    from lab_kit import record as R
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, uses="[gpu]", command=WRITES % "0.5" + USES % 1)
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    lab(root, "lock", ident)
    gone = f"20260102-0931_{ident}_abcd"  # it started on a machine that died with its folder; only the row in git is left
    open(f"{d}/runs.tsv", "w").write("\t".join(R.LEDGER) + f"\n{gone}\trun\tstarted\t2026-01-02T09:31:00+00:00\t\t\n")
    commit(root)

    # until it is declared lost, the lab says where it stands and how to go on
    assert f"lab runs lost {gone}" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert f"lab runs lost {gone}" in lab(root, "runs", "close", gone, "the machine is gone", ok=False)
    assert f"lab runs lost {gone}" in lab(root, "check", "--no-rederive", ok=False)
    assert "no run 20260102-0931_G1.Q1.1_zzzz is listed" in lab(root, "runs", "lost", "20260102-0931_G1.Q1.1_zzzz", "gone", ok=False)
    assert "say why" in lab(root, "runs", "lost", gone, " ", ok=False)
    assert "--used laptop=1" in lab(root, "runs", "lost", gone, "The machine was deleted.", "--used", "laptop=1", ok=False)
    assert open(f"{d}/runs.tsv").read().count("\n") == 2  # a refusal wrote nothing

    # declared lost: a row with the reason and what it used, a failed run on the record, and the way is open again
    lab(root, "runs", "lost", gone, "The machine was deleted with the run on it.", "--used", "gpu=1.5")
    row = open(f"{d}/runs.tsv").read().splitlines()[-1].split("\t")
    assert row[:3] == [gone, "run", "lost"] and row[4:6] == ["", ""] and json.loads(row[6]) == {"gpu": 1.5} and row[7] == "The machine was deleted with the run on it."
    assert "lost (The machine was deleted with the run on it.)" in lab(root, "runs")
    shown = lab(root, "show", ident)
    assert "declared lost: The machine was deleted with the run on it." in shown and "used 1.5 hours (stated by hand" in shown
    assert "gpu: 1.5 of 10 hours used" in lab(root, "now") and "read why its last run failed" in lab(root, "now")
    lab(root, "check", "--no-rederive")
    assert "has already ended" in lab(root, "runs", "lost", gone, "Again.", ok=False)
    commit(root, "the run is lost")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)

    # a run whose folder is here is closed or published, never lost
    here = os.path.basename(glob.glob(f"{root}/runs/*")[0])
    assert f"{here} is here" in lab(root, "runs", "lost", here, "It is not.", ok=False)
    rows = open(f"{d}/runs.tsv").read()
    open(f"{d}/runs.tsv", "w").write(rows.replace(f"{here}\trun\tended", f"{here}\trun\tlost").rsplit("\t", 2)[0] + "\t\t\tSaid to be lost.\n")
    assert "was declared lost, and its folder is here" in lab(root, "check", "--no-rederive", ok=False)


def nine_of_ten_used(tmp_path, name):
    """A locked experiment on the GPU, with nine of the ten granted hours used outside a run, all committed."""
    root = under(tmp_path, name)
    open_question(root)
    ident, d, command = experiment(root, uses="[gpu]", command=WRITES % "0.5" + "import json\njson.dump({os.environ.get('RES', 'gpu'): 2}, open(os.path.join(os.environ['LAB_RUN'], 'used.json'), 'w'))\n")
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    lab(root, "lock", ident)
    spent = RESOURCES + 'other_use = [{date = "2026-01-01", amount = 9, what = "the machine was left on overnight"}]\n'
    open(f"{root}/resources.toml", "w").write(spent)
    commit(root)
    assert "more than the 1 left" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    return root, ident, d, command, spent


def test_there_is_no_way_around_a_decision_to_a_larger_amount(tmp_path):
    second = '\n[gpu-b]\nwhat = "the same GPU under a second name"\nunit = "hours"\ngranted = 1000\nper_run = 500\nfrom = "D1"\n'

    # the same machine listed again under another name, with a grant of its own
    root, ident, d, command, spent = nine_of_ten_used(tmp_path, "second")
    assert json.load(open(f"{d}/lock.json"))["uses"] == ["gpu"]
    open(f"{root}/resources.toml", "w").write(spent + second)
    front(f"{d}/experiment.md", uses="[gpu-b]")
    assert "changed after the lock" in lab(root, "run", ident, "--wait", "--", "env", "RES=gpu-b", *command, ok=False)  # the lock holds the resources it uses
    out = lab(root, "check", "--no-rederive", ok=False)
    assert "gpu-b: its amounts come out of a decision" in out and "or the resources it uses changed after the lock" in out
    front(f"{d}/experiment.md", uses="[gpu]")
    two, d2, command2 = experiment(root, title="The same on the other name", uses="[gpu-b]", command=open(f"{d}/plan/sample.py").read())
    assert "whose amounts name no settled decision that lists it" in lab(root, "lock", two, ok=False)  # D1 is settled, and is not about gpu-b
    card = glob.glob(f"{root}/decisions/D1-*.md")[0]
    front(card, about="[gpu, gpu-b]")  # so the settled decision is made to be about it
    assert "its `about:` or its Decided text has changed since" in lab(root, "check", "--no-rederive", ok=False)
    lab(root, "review", two, "plan", "pass", "As the first.")
    lab(root, "lock", two)
    refused = lab(root, "run", two, "--wait", "--", "env", "RES=gpu-b", *command2, ok=False)
    assert "the decisions behind them are not as git holds them" in refused and not glob.glob(f"{root}/runs/*")

    # use outside a run made smaller
    root, ident, d, command, spent = nine_of_ten_used(tmp_path, "other-use")
    open(f"{root}/resources.toml", "w").write(spent.replace("amount = 9", "amount = 1"))
    refused = lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "an `other_use` row was removed or changed since the last commit" in refused and not glob.glob(f"{root}/runs/*")  # before the hours are spent
    commit(root, "less")
    assert "an `other_use` row was removed or changed in " in lab(root, "check", "--no-rederive", ok=False)
    open(f"{root}/resources.toml", "w").write(spent.replace("]\n", ', {date = "2026-01-03", amount = 0.5, what = "a wake where nothing ran"}]\n') if False else spent[:-2] + ', {date = "2026-01-03", amount = 0.5, what = "a wake where nothing ran"}]\n')
    commit(root, "back, and one more row")
    assert "other_use" in lab(root, "check", "--no-rederive", ok=False)  # the commit that changed the row stays in the history
    root, ident, d, command, spent = nine_of_ten_used(tmp_path, "other-use-grows")
    open(f"{root}/resources.toml", "w").write(spent[:-2] + ', {date = "2026-01-03", amount = 0.5, what = "a wake where nothing ran"}]\n')
    commit(root, "one more row")
    lab(root, "check", "--no-rederive")  # rows may be added

    # the unit renamed, so that the same number reads as more
    root, ident, d, command, spent = nine_of_ten_used(tmp_path, "unit")
    open(f"{root}/resources.toml", "w").write(spent.replace('unit = "hours"', 'unit = "days"'))
    assert "`unit` changed since the last commit" in lab(root, "run", ident, "--wait", "--", *command, ok=False)

    # the resource removed in one commit and listed again, larger, in the next
    root, ident, d, command, spent = nine_of_ten_used(tmp_path, "removed")
    open(f"{root}/resources.toml", "w").write(spent.split("[gpu]")[0])
    assert "gpu was removed since the last commit: a resource is never removed" in lab(root, "check", "--no-rederive", ok=False)
    commit(root, "no gpu")
    open(f"{root}/resources.toml", "w").write(spent.replace("granted = 10", "granted = 1000").replace("amount = 9", "amount = 1"))
    refused = lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "gpu was removed in " in refused and not glob.glob(f"{root}/runs/*")
    commit(root, "gpu again")
    assert "gpu was removed in " in lab(root, "check", "--no-rederive", ok=False)

    # a resource that is no longer used is retired, and takes no run
    root, ident, d, command, spent = nine_of_ten_used(tmp_path, "retired")
    open(f"{root}/resources.toml", "w").write(spent.replace('unit = "hours"', 'retired = "The allocation ended."\nunit = "hours"'))
    assert "uses gpu, which is retired: The allocation ended." in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "which is retired" in lab(root, "check", "--no-rederive", ok=False)

    # a cap above what one run may use, covered by adding the experiment to a decision settled long ago
    root = under(tmp_path, "override")
    open_question(root)
    ident, d, command = experiment(root, uses="[gpu]", command=WRITES % "0.5" + USES % 5)
    commit(root)
    front(f"{d}/experiment.md", override="{gpu: 6}")
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    lab(root, "lock", ident)
    assert "takes a decision about" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    front(glob.glob(f"{root}/decisions/D1-*.md")[0], about=f"[gpu, {ident}]")
    refused = lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "its `about:` or its Decided text has changed since" in refused and not glob.glob(f"{root}/runs/*")


def test_git_holds_what_it_has_been_given_and_the_lab_says_what_it_has_not(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    commit(root)
    assert "the record is sound" in lab(root, "check", "--strict") and "Not committed yet" not in lab(root, "now")

    # a lock is committed when it is made: until then nothing witnesses it
    lab(root, "lock", ident)
    assert f"{ident}: its lock is not committed" in lab(root, "now")
    out = lab(root, "check")
    assert f"note: {ident}: its lock is not committed" in out and "the record is sound" in out
    assert "not everything could be checked" in lab(root, "check", "--strict", ok=False)
    commit(root, "the lock")
    assert "the record is sound" in lab(root, "check", "--strict")

    # so is the row a run adds when it starts, and the row it adds when it ends
    lab(root, "run", ident, "--wait", "--", *command)
    assert f"{ident}: its list of runs is not committed" in lab(root, "now")
    assert "not everything could be checked" in lab(root, "check", "--strict", ok=False)
    commit(root, "the run")
    assert "the record is sound" in lab(root, "check", "--strict") and "Not committed yet" not in lab(root, "now")

    # a lock this kit made holds the hash of plan/ and the resources: one without them is not that lock
    two, d2, command2 = experiment(root, title="A second pair of sizes", command=WRITES % "0.5")
    lab(root, "lock", two)
    lock = json.load(open(f"{d2}/lock.json"))
    assert lock["kit"] and lock["hash"] == 2 and lock["uses"] == ["laptop"] and len(lock["plan"]) == 64
    for key in ("plan", "uses", "hash"):
        open(f"{d2}/lock.json", "w").write(json.dumps({k: v for k, v in lock.items() if k != key}, indent=1) + "\n")
        assert "is not the lock `lab lock` wrote" in lab(root, "check", "--no-rederive", ok=False), key


def test_small_things_that_are_held(tmp_path):
    sys.path.insert(0, SRC)
    from lab_kit import record as R, runs

    # a value is a number in plain digits
    assert [R.number(v) for v in ("0.5", " 0.5 ", "5e-1", "+.5", "-2", "7.")] == [0.5, 0.5, 0.5, 0.5, -2.0, 7.0]
    assert all(R.number(v) is None for v in ("1_0", "０.５", "nan", "inf", "0,5", '0.5"', "0x10", "", "1 0", "١"))

    # two folders that are not the same do not hash the same
    a, b = under(tmp_path, "a"), under(tmp_path, "b")
    open(f"{a}/a.py", "w").write("print(1)\n#")
    open(f"{a}/b.py", "w").write("\nMODE = 'reviewed'\n")
    open(f"{b}/a.py", "w").write(open(f"{a}/a.py").read() + "b.py\n" + open(f"{a}/b.py").read())
    assert R.tree_hash(a, 1) == R.tree_hash(b, 1) and R.tree_hash(a) != R.tree_hash(b)  # the first way collided; what is made now does not

    # what was locked and run before the change is still verified the way it was hashed
    root = under(tmp_path, "lab")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    rj = glob.glob(f"{root}/runs/*/run.json")[0]
    record, lock = json.load(open(rj)), json.load(open(f"{d}/lock.json"))
    assert record["hash"] == 2 and record["plan"] == lock["plan"] == R.tree_hash(f"{d}/plan") != R.tree_hash(f"{d}/plan", 1)
    old = {k: v for k, v in record.items() if k != "hash"}  # as a run sealed by the kit before the marker existed
    old["plan"] = R.tree_hash(f"{d}/plan", 1)
    old["seal"] = R.seal_of(old)
    os.chmod(rj, 0o644)
    open(rj, "w").write(json.dumps(old, indent=1) + "\n")
    rows = open(f"{d}/runs.tsv").read()
    open(f"{d}/runs.tsv", "w").write(rows.replace(record["seal"], old["seal"]))
    open(f"{d}/lock.json", "w").write(json.dumps({k: v for k, v in lock.items() if k in ("locked", "commit", "card", "trials")}, indent=1) + "\n")
    lab(root, "review", ident, "results", "pass", "Read again after the record was put back as the first kit wrote it.")
    assert "the record is sound" in lab(root, "check")
    open(f"{d}/plan/sample.py", "a").write("# after the fact\n")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)

    # the same rows with other line ends are the same rows: the review still stands
    root = under(tmp_path, "crlf")
    open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    for path in (f"{d}/results.tsv", f"{d}/experiment.md", f"{d}/runs.tsv", f"{d}/reviews.tsv", f"{root}/log.md", f"{root}/resources.toml", glob.glob(f"{root}/decisions/D1-*.md")[0]):
        data = open(path, "rb").read()
        open(path, "wb").write(b"\xef\xbb\xbf" + data.replace(b"\n", b"\r\n"))
    assert "the record is sound" in lab(root, "check") and "(done, confirmed)" in lab(root, "show", ident)

    # where a process cannot be told to be the run's, closing the run stops nothing
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True, env={**os.environ, "LAB_RUN": "/the/run"})
    try:
        real = os.path.isdir
        os.path.isdir = lambda p: False if p == "/proc/self" else real(p)
        said = runs.stop_group({"child": child.pid}, "/the/run")
        os.path.isdir = real
        assert "was not stopped" in said and child.poll() is None
        assert runs.stop_group({"child": child.pid}, "/another/run") is None and child.poll() is None  # not this run's: left alone
        assert runs.stop_group({"child": child.pid}, "/the/run") is None
        assert child.wait(timeout=5) == -signal.SIGKILL
    finally:
        os.path.isdir = os.path.isdir if os.path.isdir.__name__ != "<lambda>" else real
        child.kill()


# ---------------------------------------------------------------- a lab that is not written as the model says

def a_base(tmp_path):
    """A lab with a done experiment, a build, a second question and a settled decision: (root, the paths a mutation needs)."""
    root = under(tmp_path, "base")
    qdir = open_question(root)
    ident, d, command = experiment(root, command=WRITES % "0.5")
    lab(root, "new", "build", "G1.Q1", "A build")
    bd = folder(root, "G1.Q1.2")
    describe(f"{bd}/build.md", "Something the experiment needs.")
    lab(root, "lock", ident)
    lab(root, "run", ident, "--wait", "--", *command)
    done(root, ident, d)
    lab(root, "new", "question", "G1", "A second question", "--from", "D1")
    q2 = glob.glob(f"{root}/goals/G1-*/Q2-*")[0]
    describe(f"{q2}/question.md", "What follows from the first.")
    assert "the record is sound" in lab(root, "check")
    rel = lambda p: os.path.relpath(p, root)
    return root, {"x": rel(d), "q": rel(qdir), "q2": rel(q2), "b": rel(bd), "d": rel(glob.glob(f"{root}/decisions/D1-*.md")[0]), "run": rel(glob.glob(f"{root}/runs/*")[0])}


def mutations(at):
    """(name, the change, whether `lab check` must report a problem). A change takes the lab's root."""
    def sub(path, a, b):
        def f(root):
            p = os.path.join(root, path)
            text = open(p).read()
            assert a in text, (path, a)
            os.chmod(p, 0o644)
            open(p, "w").write(text.replace(a, b, 1))
        return f

    def wr(path, data, mode="w"):
        def f(root):
            p = os.path.join(root, path)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if os.path.exists(p):
                os.chmod(p, 0o644)
            with open(p, mode) as out:
                out.write(data)
        return f

    def record(change):
        def f(root):
            p = os.path.join(root, at["run"], "run.json")
            was = json.load(open(p))
            os.chmod(p, 0o644)
            open(p, "w").write(json.dumps(change(was)))
        return f

    def card(folder, kind, text="---\ntitle: t\n---\n"):
        return lambda root: wr(os.path.join(folder, f"{kind}.md"), text)(root)

    def folder_at(path):
        def f(root):
            os.remove(os.path.join(root, path))
            os.makedirs(os.path.join(root, path))
        return f

    def link_at(path):
        def f(root):
            os.remove(os.path.join(root, path))
            os.symlink("nowhere", os.path.join(root, path))
        return f

    x, q, q2, b, d, run = (at[k] for k in ("x", "q", "q2", "b", "d", "run"))
    xc, qc, bc = f"{x}/experiment.md", f"{q}/question.md", f"{b}/build.md"
    head = "name\tlabel\tvalue\treads\tversus\tcommand\n"
    build = "---\ntitle: t\nneeds: []\ncommits: []\ntests: []\n---\n\nd\n\n## How it works\n\n## Works when\n"
    decided = 'decided: {date: 2026-01-02, with: "Ada"}'
    return [
        ("needs is a number", sub(xc, "needs: []", "needs: 5"), True),
        ("needs is one value", sub(xc, "needs: []", "needs: G1.Q1.2"), False),
        ("needs itself", sub(xc, "needs: []", "needs: [G1.Q1.1]"), True),
        ("questions need each other", lambda r: (sub(qc, "needs: []", "needs: [G1.Q2]")(r), sub(f"{q2}/question.md", "needs: []", "needs: [G1.Q1]")(r)), True),
        ("a question's needs is a number", sub(qc, "needs: []", "needs: 3"), True),
        ("uses is a number", sub(xc, "uses: [laptop]", "uses: 5"), True),
        ("uses holds a table", sub(xc, "uses: [laptop]", "uses: [{a: b}]"), True),
        ("override is a word", sub(xc, "uses: [laptop]", "uses: [gpu]\noverride: {gpu: lots}"), True),
        ("replaces is a list", sub(xc, "uses: [laptop]", "uses: [laptop]\nreplaces: [G1.Q1.1]\nbecause: x"), True),
        ("replaces itself", sub(xc, "uses: [laptop]", "uses: [laptop]\nreplaces: G1.Q1.1\nbecause: x"), True),
        ("commits is a number", sub(bc, "commits: []", "commits: 5"), True),
        ("see is a number", sub(bc, "commits: []", "commits: []\nsee: 5"), True),
        ("title is a list", sub(bc, 'title: "A build"', "title: [a, b]"), True),
        ("title is a date", sub(bc, 'title: "A build"', "title: 2026-01-01"), False),
        ("front matter is a list", sub(bc, 'title: "A build"\nneeds: []\ncommits: []\ntests: []', "- a\n- b"), True),
        ("a tab in the front matter", sub(bc, "needs: []", "\tneeds: []"), True),
        ("no front matter", wr(bc, "just text\n"), True),
        ("an empty card", wr(bc, ""), True),
        ("a card that is not UTF-8", wr(bc, b"---\ntitle: caf\xe9\n---\n\nx\n", "wb"), True),
        ("a log that is not UTF-8", wr("log.md", b"## 2026-01-02\n\n- 09:30 | G1 | agent | caf\xe9 | x\n", "wb"), True),
        ("a glossary that is not UTF-8", wr("GLOSSARY.md", b"# T\n\n## caf\xe9\nx\n", "wb"), True),
        ("results that are not UTF-8", wr(f"{x}/results.tsv", head.encode() + b"ratio\tcaf\xe9\t0.5\t\t\tcat $RUN/ratio.txt\n", "wb"), True),
        ("a heading in the log that is not a day", sub("log.md", "## 2026-01-02", "## Notes"), True),
        ("a day in the log that is no day", sub("log.md", "## 2026-01-02", "## 2026-13-45"), True),
        ("a log line with too many columns", wr("log.md", "\n- 10:00 | G1 | agent | a | b | c | d | e\n", "a"), True),
        ("a log line with too few", wr("log.md", "\n- hello there\n", "a"), True),
        ("a log line about nothing", wr("log.md", "\n- 10:00 | G9 | agent | a | b\n", "a"), True),
        ("about is a number", sub(d, "about: [gpu]", "about: 5"), True),
        ("a decision with no date", sub(d, "date: 2026-01-02\n", ""), True),
        ("a decision with a date that is none", sub(d, "date: 2026-01-02", "date: soon"), True),
        ("decided is a word", sub(d, decided, "decided: yes"), True),
        ("decided has no date", sub(d, decided, 'decided: {with: "Ada"}'), True),
        ("a decision opened again", sub(d, decided + "\n", ""), True),
        ("holds is a table", sub(d, "holds: []", "holds: {a: b}"), True),
        ("about holds a list", sub(d, "about: [gpu]", "about: [[G1]]"), True),
        ("a lock that is not JSON", wr(f"{x}/lock.json", "{not json"), True),
        ("a lock that is a list", wr(f"{x}/lock.json", "[]"), True),
        ("an empty lock", wr(f"{x}/lock.json", "{}\n"), True),
        ("a lock with no time", wr(f"{x}/lock.json", '{"card": "x"}\n'), True),
        ("a result row with columns missing", wr(f"{x}/results.tsv", head + "ratio\tthe label\t0.5\n"), True),
        ("a result row with columns too many", wr(f"{x}/results.tsv", head + "ratio\tthe label\t0.5\t\t\tcat $RUN/ratio.txt\textra\tmore\n"), True),
        ("results with no header", wr(f"{x}/results.tsv", "ratio\tthe label\t0.5\t\t\tcat $RUN/ratio.txt\n"), True),
        ("empty results", wr(f"{x}/results.tsv", ""), True),
        ("a label that opens with a quote", wr(f"{x}/results.tsv", head + "ratio\t\"the label\t0.5\t\t\tcat $RUN/ratio.txt\nother\tx\t1\t\t\techo 1 $RUN\n"), True),
        ("a result that is not a number", wr(f"{x}/results.tsv", head + "ratio\tthe label\tnan\tpercent\t\tcat $RUN/ratio.txt\n"), True),
        ("a result that is infinite", wr(f"{x}/results.tsv", head + "ratio\tthe label\tinf\tpercent\t\tcat $RUN/ratio.txt\n"), True),
        ("a review row with columns missing", wr(f"{x}/reviews.tsv", "date\tstage\tverdict\tby\tof\tnote\n2026-01-02\tresults\tpass\n"), True),
        ("a review with a date that is none", wr(f"{x}/reviews.tsv", "date\tstage\tverdict\tby\tof\tnote\nsoon\tresults\tpass\tme\tabc\tnote here\n"), True),
        ("a run's record that is a list", wr(f"{run}/run.json", "[]"), True),
        ("a run's record that is empty", wr(f"{run}/run.json", "{}"), True),
        ("a run's record with no kind", record(lambda r: {k: v for k, v in r.items() if k != "kind"}), True),
        ("a run's record with no start", record(lambda r: {**r, "started": None}), True),
        ("a run's record with no files", record(lambda r: {k: v for k, v in r.items() if k != "files"}), True),
        ("a run's record of another experiment", record(lambda r: {**r, "experiment": "G9.Q9.9"}), True),
        ("a run's record that used a word", record(lambda r: {**r, "used": {"gpu": "lots"}}), True),
        ("a run's file removed", lambda r: os.remove(os.path.join(r, run, "ratio.txt")), True),
        ("a run listed twice", lambda r: wr(f"{x}/runs.tsv", open(os.path.join(r, x, "runs.tsv")).read().splitlines()[1] + "\n", "a")(r), True),
        ("a row of the list of runs that is none", wr(f"{x}/runs.tsv", "nonsense\trun\tstarted\tsoon\t\t\n", "a"), True),
        ("a resource that is one value", wr("resources.toml", "\n[other]\nwhat = \"x\"\n", "a"), False),
        ("resources that are not TOML", wr("resources.toml", "\n[[[\n", "a"), True),
        ("a resource that is not a table", lambda r: wr("resources.toml", "spare = 1\n" + open(os.path.join(r, "resources.toml")).read())(r), True),
        ("a grant that is a word", sub("resources.toml", "granted = 10", 'granted = "ten"'), True),
        ("an amount for one run that is a word", sub("resources.toml", "per_run = 2", 'per_run = "two"'), True),
        ("other use that is a word", wr("resources.toml", 'other_use = "x"\n', "a"), True),
        ("other use on a day that is none", wr("resources.toml", 'other_use = [{date = "soon", amount = 1, what = "x"}]\n', "a"), True),
        ("rules that are one sentence", sub("resources.toml", 'rules = ["Shut down as soon as a run ends."]', 'rules = "Shut down"'), True),
        ("a lab.toml that is not TOML", wr("lab.toml", "\n[[[\n", "a"), True),
        ("a lab.toml with no name", wr("lab.toml", 'library = "docs"\n'), False),
        ("a lab.toml whose store is a number", wr("lab.toml", "store = 5\n", "a"), True),
        ("a question's folder with no number", card(f"{os.path.dirname(q)}/Qx-typo", "question"), True),
        ("a goal's folder with no number", card("goals/Gx-typo", "goal"), True),
        ("a step's folder with no number", card(f"{q}/3x-typo", "build"), True),
        ("a decision's file with no number", wr("decisions/D2x-typo.md", "---\ntitle: t\n---\n"), True),
        ("two steps with one number", card(f"{q}/1-other", "build", build), True),
        ("two cards in one folder", card(x, "build", build), True),
        ("two goals with one number", card("goals/G1-again", "goal"), True),
        ("two decisions with one number", wr("decisions/D1-again.md", "---\ntitle: t\ndate: 2026-01-02\n---\n\n## Seen\n\nx\n"), True),
        ("a glossary with markup in it", wr("GLOSSARY.md", '# T\n\n## gate\nA <b>gate</b> "quoted" & more.\n- code: x" onmouseover="alert(1)\n'), False),
        ("a line with two tests", sub(xc, "(`ratio > 0.9`)", "(`ratio > 0.9`) (`ratio > 0.1`)"), True),
        ("an answer that is not yes or no", sub(qc, "needs: []", "needs: []\nanswer: maybe"), True),
        ("from is a list", sub(qc, "from: D1", "from: [D1]"), True),
        ("used.json after the seal", wr(f"{run}/used.json", '{"gpu": NaN}'), True),
        ("a folder where the lock is", folder_at(f"{x}/lock.json"), True),
        ("a folder where the results are", folder_at(f"{x}/results.tsv"), True),
        ("a folder where the reviews are", folder_at(f"{x}/reviews.tsv"), True),
        ("a folder where the list of runs is", folder_at(f"{x}/runs.tsv"), True),
        ("a folder where the log is", folder_at("log.md"), True),
        ("a folder where a card is", folder_at(bc), True),
        ("a folder where the glossary is", folder_at("GLOSSARY.md"), True),
        ("a folder where the resources are", folder_at("resources.toml"), True),
        ("a broken link where the lock is", link_at(f"{x}/lock.json"), True),
        ("a broken link where the results are", link_at(f"{x}/results.tsv"), True),
        ("a broken link where the list of runs is", link_at(f"{x}/runs.tsv"), True),
        ("a broken link where the log is", link_at("log.md"), True),
        ("a broken link where a card is", link_at(bc), True),
        ("a run closed with a list", record(lambda r: {**r, "closed": ["x"], "changed": 5}), True),
        ("a run with odd fields", record(lambda r: {**r, "used": {"gpu": "lots", "laptop": None}, "cap": {"gpu": "x"}, "exit": "0", "pid": "abc", "host": 3}), True),
        ("a goal's folder with no card", card("goals/G2-empty/Q1-x", "question"), True),
        ("a question's folder with no card", card(f"{os.path.dirname(q)}/Q7-empty/1-x", "build", build), True),
        ("a stray file beside the goals", wr("goals/notes.md", "x"), False),
        ("line ends of another system, everywhere", lambda r: [wr(p, open(os.path.join(r, p), "rb").read().replace(b"\n", b"\r\n"), "wb")(r) for p in (xc, qc, d, "log.md", f"{x}/results.tsv", f"{x}/runs.tsv", "resources.toml", "lab.toml")], False),
        ("a byte-order mark, everywhere", lambda r: [wr(p, b"\xef\xbb\xbf" + open(os.path.join(r, p), "rb").read(), "wb")(r) for p in (xc, d, "log.md", f"{x}/results.tsv", f"{x}/runs.tsv", "resources.toml", "lab.toml")], False),
        ("a list that holds itself", sub(xc, "needs: []", "needs: &a [*a]"), True),
        ("odd values in the front matter", sub(xc, "uses: [laptop]", "uses: [yes, ~, 1.5, 2026-01-01]\noverride: {gpu: .inf, laptop: -1, 3: true}\nwaiting_on: {a: b}\ncost: [1]\n? [a, b]\n: c"), True),
        ("an answer that is a list", sub(qc, "needs: []", "needs: []\nanswer: [yes]\nanswered: 2026-13-45"), True),
        ("a slot twice, and headings with no name", lambda r: wr(xc, "\n## Means\n\nAgain.\n\n## \n\n##  \nx\n", "a")(r), None),
        ("odd resources", wr("resources.toml", '\n[laptop.sub]\nx = 1\n["we ird<b>"]\nwhat = "x"\ngranted = true\nper_run = -1\nunit = 5\nfrom = "D9"\nother_use = [1, {amount = "x"}, {date = 2026-01-01, amount = 1, what = 5}]\nrules = [1, [2]]\n', "a"), True),
        ("an odd lab.toml", wr("lab.toml", 'name = 5\ntitle = ["x"]\nlibrary = "../.."\nstore = 7\nrederive_timeout = "x"\ncode_url = "javascript:alert(1)"\ncode = "/nonexistent"\n'), True),
        ("a lock with odd fields", wr(f"{x}/lock.json", '{"locked": "2026-01-01T00:00:00+00:00", "card": "x", "plan": 5, "trials": [{}, null, 3], "commit": []}'), True),
        ("an odd glossary", wr("GLOSSARY.md", "## no group\n\n# \n\n## \n- code: \n\n## (a|b)[\ndef\n## (a|b)[\ndef\n### deeper\n"), True),
        ("odd reviews", wr(f"{x}/reviews.tsv", "date\tstage\tverdict\tby\tof\tnote\n2026-01-02\tresults\tPASS\t\t\t\n\t\t\t\t\t\n2026-01-02\tresults\tpass\tme\n"), True),
        ("a list of runs that is not text", wr(f"{x}/runs.tsv", b"run\tkind\twhat\tat\texit\tseal\n\xff\xfe\trun\tstarted\tx\t\t\n", "wb"), True),
        ("a run that ended with a word", lambda r: wr(f"{x}/runs.tsv", open(os.path.join(r, x, "runs.tsv")).read().replace("\t0\t", "\tzero\t"))(r), True),
        ("junk in the store", lambda r: (wr("runs/tmp/run.json", "{}")(r), wr("runs/20260101-0101_G9.Q9.9_abcd/run.json", json.dumps({"id": "20260101-0101_G9.Q9.9_abcd", "experiment": "G9.Q9.9", "kind": "run", "started": "2026-01-01T01:01:00+00:00"}))(r)), True),
    ]


COMMANDS = (["now"], ["check", "--no-rederive"], ["check"], ["show", "G1.Q1.1"], ["show", "G1.Q1"], ["show", "G1"], ["show", "D1"], ["brief", "G1.Q1"], ["runs"], ["since"], ["define", "gate"])


def raw(root, *args):
    p = subprocess.run([sys.executable, "-m", "lab_kit.cli", *args], cwd=root, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": SRC, "LAB_TESTING": "1", "LAB_TODAY": "2026-01-02"})
    return p.returncode, p.stdout + p.stderr


def mutated(tmp_path):
    """Each mutation applied to its own copy of the base lab: (name, root, whether the check must report it)."""
    base, at = a_base(tmp_path)
    for name, change, reported in mutations(at):
        root = str(tmp_path / "m")
        shutil.rmtree(root, ignore_errors=True)
        shutil.copytree(base, root, symlinks=True)
        change(root)
        yield name, root, reported


def test_no_command_stops_on_a_lab_that_is_not_written_as_the_model_says(tmp_path):
    for name, root, reported in mutated(tmp_path):
        for args in COMMANDS:
            code, out = raw(root, *args)
            assert "Traceback" not in out, f"{name}: lab {' '.join(args)}\n{out[-1500:]}"
            if args == ["check", "--no-rederive"]:
                assert reported is None or (code != 0) == reported, f"{name}: lab check {'passes' if code == 0 else 'fails'}\n{out[-1500:]}"
                assert code == 0 or "problem(s)" in out, f"{name}\n{out[-800:]}"
