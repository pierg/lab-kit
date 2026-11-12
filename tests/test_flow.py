"""One small lab, built with the command itself, taken from a decision to a reviewed result."""
import glob, json, os, re, signal, subprocess, sys, time

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
SAMPLE = ("import os, random\nrandom.seed(7)\nerr = lambda n: sum(abs(sum(random.random() < .5 for _ in range(n)) / n - .5) for _ in range(200)) / 200\n"
          "open(os.path.join(os.environ['LAB_RUN'], 'ratio.txt'), 'w').write(f'{err(400) / err(100):.3f}\\n')\n")
RESOURCES = ('[laptop]\nwhat = "this machine"\n\n[gpu]\nwhat = "a rented GPU"\nkey = "GPU_TOKEN, kept in the secrets repository"\nunit = "hours"\n'
             'granted = 10\nper_run = 2\nfrom = "D1"\nrules = ["Shut down as soon as a run ends."]\n')


def lab(cwd, *args, ok=True):
    p = subprocess.run([sys.executable, "-m", "lab_kit.cli", *args], cwd=cwd, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": SRC, "LAB_TESTING": "1", "LAB_TODAY": "2026-01-02", "LAB_CLOCK": "09:30", "LAB_REVIEWER": "second-session"})
    assert (p.returncode == 0) == ok, p.stdout + p.stderr
    return p.stdout + p.stderr


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True, capture_output=True)


def fill(path, **slots):
    text = open(path).read()
    for slot, words in slots.items():
        text = re.sub(rf"(## {slot.replace('_', ' ')}\n\n).*?(?=\n## |\Z)", lambda m: m.group(1) + words + "\n", text, flags=re.S)
    open(path, "w").write(text)


def front(path, **fields):
    text = open(path).read()
    for k, v in fields.items():
        text = re.sub(rf"^{k}:.*$", f"{k}: {v}", text, flags=re.M) if re.search(rf"^{k}:", text, flags=re.M) else text.replace("\n---\n", f"\n{k}: {v}\n---\n", 1)
    open(path, "w").write(text)


def describe(path, text):
    """Write a card's description: the paragraph between its front matter and its first slot."""
    _, fm, body = open(path).read().split("---", 2)
    rest = body[body.index("\n## "):] if "\n## " in body else "\n"
    open(path, "w").write("---" + fm + "---\n\n" + text + "\n" + rest)


def folder(root, ident):
    """The folder of an experiment or a build, from its id."""
    g, q, n = re.fullmatch(r"G(\d+)\.Q(\d+)\.(\d+)", ident).groups()
    return glob.glob(f"{root}/goals/G{g}-*/Q{q}-*/{n}-*")[0]


def open_question(root):
    """A lab with one goal and one question, both out of a decision settled with the operator."""
    lab(root, "init")
    open(f"{root}/resources.toml", "w").write(RESOURCES)
    lab(root, "new", "decision", "The lab's goal and its first question", "--about", "gpu")
    fill(glob.glob(f"{root}/decisions/D1-*.md")[0], Seen="The repository holds a coin sampler and no measurement of how its estimate converges.")
    lab(root, "decide", "D1", "--with", "Ada", "One goal, convergence, and one first question: whether the error halves when the sample quadruples. It runs on the laptop.")
    lab(root, "new", "goal", "Convergence", "--from", "D1")
    describe(glob.glob(f"{root}/goals/G1-*/goal.md")[0], "A coin estimate converges as the theory says: the error falls with the square root of the sample.")
    lab(root, "new", "question", "G1", "Does the error halve when the sample quadruples?", "--from", "D1")
    qdir = glob.glob(f"{root}/goals/G1-*/Q1-*")[0]
    describe(f"{qdir}/question.md", "The simplest check of the square-root law, and the first thing the sampler has to get right.")
    fill(f"{qdir}/question.md", We_expect="A ratio near one half.", Wrong_if="The ratio stays near one.")
    return qdir


def experiment(root, title="Error at 100 and at 400 flips", uses="[laptop]", command=SAMPLE):
    out = lab(root, "new", "experiment", "G1.Q1", title)
    ident = re.search(r"made (\S+):", out).group(1)
    d = folder(root, ident)
    front(f"{d}/experiment.md", uses=uses)
    describe(f"{d}/experiment.md", "Measures the error at two sample sizes, a factor of four apart.")
    fill(f"{d}/experiment.md", Compares="The mean error of 200 estimates at 100 flips and at 400 flips.",
         Arms="- 100 flips: 200 estimates of a fair coin, each from 100 flips\n- 400 flips: the same, each from 400 flips", Cases="200 estimates per arm, one pass.",
         Confirmed_if="- the error at 400 flips is under 0.6 of the error at 100 (`ratio < 0.6`)\n- and over 0.4 of it (`ratio > 0.4`)",
         Refuted_if="- the error barely falls (`ratio > 0.9`)")
    open(f"{d}/plan/sample.py", "w").write(command)
    return ident, d, [sys.executable, f"{os.path.relpath(d, root)}/plan/sample.py"]


def results(d, value=None):
    value = value or open(glob.glob(f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(d))))}/runs/*/ratio.txt")[-1]).read().strip()
    open(f"{d}/results.tsv", "w").write("name\tlabel\tvalue\treads\tversus\tcommand\n"
                                       f"ratio\tthe error at 400 flips as a share of the error at 100\t{value}\tpercent\tone half, which the theory gives\tcat $RUN/ratio.txt\n")
    return value


def shown(value):
    return f"{float(value) * 100:.1f}".rstrip("0").rstrip(".") + "%"


def test_how_a_value_reads():
    sys.path.insert(0, SRC)
    from lab_kit.record import shown as reads
    row = lambda value, how: {"value": value, "num": float(value), "reads": how}
    assert reads(row("0.0163", "percent")) == "1.6%" and reads(row("0.660", "percent")) == "66%"
    assert reads(row("-0.0947", "points")) == "\u22129.5 points" and reads(row("+0.0211", "points")) == "+2.1 points" and reads(row("+0.0000", "points")) == "0 points"
    assert reads(row("0.0586", "points")) == "5.9 points" and reads(row("0.0100", "points")) == "1 point" and reads(row("2066", "")) == "2066"


def test_from_a_decision_to_a_reviewed_result(tmp_path):
    root = str(tmp_path)
    assert ".lab/METHOD.md" in lab(root, "init")
    os.makedirs(f"{root}/.agents/skills/someone-elses")  # a skill the kit did not install is not the kit's to remove
    lab(root, "init")
    assert {"lab-set-up", "lab-work", "lab-review", "lab-talk", "someone-elses"} <= set(os.listdir(f"{root}/.agents/skills"))
    open(f"{root}/resources.toml", "w").write(RESOURCES)

    # direction comes out of a decision: something discussed with the operator, then recorded in the lab's words
    assert "comes out of a decision" in lab(root, "new", "goal", "Convergence", ok=False)
    lab(root, "new", "decision", "The lab's goal and its first question", "--about", "gpu")
    card = glob.glob(f"{root}/decisions/D1-*.md")[0]
    lab(root, "new", "goal", "Convergence", "--from", "D1")
    lab(root, "new", "question", "G1", "Does the error halve when the sample quadruples?", "--from", "D1")
    qdir = glob.glob(f"{root}/goals/G1-*/Q1-*")[0]
    fill(f"{qdir}/question.md", We_expect="A ratio near one half.", Wrong_if="The ratio stays near one.")
    lab(root, "new", "build", "G1.Q1", "The sampler")
    fill(f"{folder(root, 'G1.Q1.1')}/build.md", Works_when="It returns zero error for a coin that always lands heads.")
    ident, d, command = experiment(root)
    assert ident == "G1.Q1.2"
    front(f"{d}/experiment.md", needs="[G1.Q1.1]")
    assert "the decision D1 to be settled" in lab(root, "lock", ident, ok=False) and "(under discussion)" in lab(root, "show", "G1.Q1")
    assert "does not say what was seen" in lab(root, "decide", "D1", "--with", "Ada", "One goal.", ok=False)
    fill(card, Seen="The repository holds a coin sampler and no measurement of how its estimate converges.",
         Options="(a) Start with the square-root law. (b) Start with the bias of the sampler.", Recommendation="(a): it is the cheapest check that can fail.")
    seen = lab(root, "now")
    assert all(s in seen for s in ("To discuss with the operator", "D1 The lab's goal and its first question", "Options. (a) Start with", "Held until it is settled: nothing"))
    assert "--with" in lab(root, "decide", "D1", "One goal.", ok=False)
    lab(root, "decide", "D1", "--with", "Ada", "One goal, convergence, and one first question: whether the error halves when the sample quadruples.")
    assert "already decided" in lab(root, "decide", "D1", "--with", "Ada", "Something else.", ok=False)
    text = open(card).read()
    assert "decided: {date: 2026-01-02, with: \"Ada\"}" in text and text.rstrip().endswith("when the sample quadruples.")
    assert "- 09:30 | D1 | decision | Decided: The lab's goal and its first question | One goal, convergence" in open(f"{root}/log.md").read() and "G1.Q1 (open)" in lab(root, "now")
    assert "lab decide" in lab(root, "log", "G1.Q1", "decision", "Ada chose the large sample.", ok=False)  # a decision is never a bare log line

    # every card says what it is and why, beside its title
    assert "has no description" in lab(root, "check", ok=False)
    describe(glob.glob(f"{root}/goals/G1-*/goal.md")[0], "A coin estimate converges as the theory says.")
    describe(f"{qdir}/question.md", "The simplest check of the square-root law.")
    describe(f"{folder(root, 'G1.Q1.1')}/build.md", "A script that estimates the error at a number of flips. The experiment runs it.")

    # an experiment waits for the build it needs
    assert "G1.Q1.1 The sampler" in lab(root, "lock", ident, ok=False)
    assert "G1.Q1.1 The sampler (build): build it" in lab(root, "now")
    front(f"{folder(root, 'G1.Q1.1')}/build.md", commits="[abc1234]", tests="[tests/test_sampler.py]")
    assert "(built)" in lab(root, "show", "G1.Q1.1")

    # every line carries the result it tests, or the lock refuses
    fill(f"{d}/experiment.md", Refuted_if="- the error barely falls (`ratio > 0.9`)\n- the curve looks wrong")
    assert "has no test" in lab(root, "lock", ident, ok=False)
    fill(f"{d}/experiment.md", Refuted_if="- the error barely falls (`ratio > 0.9`)")
    assert "is not locked" in lab(root, "run", ident, "--wait", "--", *command, ok=False)

    # a trial run comes before the lock and never counts as the run
    assert "finished" in lab(root, "run", ident, "--trial", "--wait", "--", *command)
    assert "lock it" in lab(root, "now")
    lab(root, "lock", ident)
    assert len(json.load(open(f"{d}/lock.json"))["trials"]) == 1
    assert "comes before the lock" in lab(root, "run", ident, "--trial", "--wait", "--", *command, ok=False)
    assert "already locked" in lab(root, "lock", ident, ok=False)

    # what an experiment demands never changes once it is locked
    fill(f"{d}/experiment.md", Refuted_if="- the error barely falls (`ratio > 0.8`)")
    assert "changed after the lock" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    fill(f"{d}/experiment.md", Refuted_if="- the error barely falls (`ratio > 0.9`)")
    assert "run it" in lab(root, "now")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)
    assert "takes no more" in lab(root, "run", ident, "--wait", "--", *command, ok=False)  # the first finished run is the only source of results

    # a number is a result only once it is reviewed; until then no card may name it
    assert "write a result row" in lab(root, "now")
    assert "no finished run with results" in lab(root, "review", ident, "results", "pass", "fine", ok=False)
    value = results(d)
    assert "send the results to a reviewer" in lab(root, "now") and "not reviewed" in lab(root, "show", ident)
    fill(f"{d}/experiment.md", Found="At 400 flips the error was {ratio} of the error at 100.", Means="The estimate converges as the theory says.")
    assert "not yet reviewed" in lab(root, "check", ok=False)
    lab(root, "review", ident, "results", "pass", "Re-ran the command; the ratio is the one in the run's file.")
    out = lab(root, "show", ident)
    assert "(done, confirmed)" in out and f"the error was {shown(value)} of the error" in out and "ratio < 0.6]: holds" in out and "ratio > 0.9]: does not hold" in out

    # a card names a result and never types its number, in either form
    for typed in (value, shown(value)):
        fill(f"{d}/experiment.md", Found=f"At 400 flips the error was {typed} of the error at 100.")
        assert f"types {typed.rstrip('%')}" in lab(root, "check", ok=False)
    fill(f"{d}/experiment.md", Found="At 400 flips the error was {ratio} of the error at 100.")
    fill(f"{qdir}/question.md", So_far="The error at 400 flips is {G1.Q1.2:ratio} of the error at 100.")
    assert f"is {shown(value)} of the error" in lab(root, "show", "G1.Q1")
    assert "the record is sound" in lab(root, "check") and "1 result(s) re-derived" in lab(root, "check")

    # a path copied from a page of the site names its node
    assert "belongs to G1.Q1.2." in lab(root, "show", os.path.relpath(d, root) + "/experiment.md")
    assert "belongs to G1.Q1.2." in lab(root, "show", glob.glob(f"{root}/runs/*_G1.Q1.2_*")[-1] + "/")
    assert "belongs to D1" in lab(root, "show", card)

    # the agent answers the question, but not while an experiment of it is not done
    lab(root, "new", "experiment", "G1.Q1", "A third size")
    assert "G1.Q1.3 is not done" in lab(root, "answer", "G1.Q1", "yes", "The ratio is one half.", ok=False)
    describe(f"{folder(root, 'G1.Q1.3')}/experiment.md", "A third sample size.")
    front(f"{folder(root, 'G1.Q1.3')}/experiment.md", dropped="The two sizes already answer it.")
    lab(root, "answer", "G1.Q1", "yes", "The ratio is one half, as the theory gives.")
    assert "G1.Q1 (yes)" in lab(root, "now") and "the record is sound" in lab(root, "check")
    assert "Answered G1.Q1 yes" in lab(root, "since", "2026-01-01")

    # what was recorded stays: git is the witness
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "the lab")
    assert "the record is sound" in lab(root, "check")
    text = open(f"{root}/log.md").read()
    open(f"{root}/log.md", "w").write(text.replace("Answered G1.Q1 yes", "Answered G1.Q1 no"))
    assert "history: log.md" in lab(root, "check", ok=False)
    open(f"{root}/log.md", "w").write(text)
    lock = open(f"{d}/lock.json").read()
    open(f"{d}/lock.json", "w").write(lock.replace('"locked": "2', '"locked": "1'))
    assert "history: " in lab(root, "check", ok=False)


def test_resources_a_failed_review_and_a_replacement(tmp_path):
    root = str(tmp_path)
    open_question(root)
    used = SAMPLE + "open(os.path.join(os.environ['LAB_RUN'], 'used.json'), 'w').write('{\"gpu\": 1.5}')\n"
    ident, d, command = experiment(root, uses="[gpu]", command=used)

    # a run on a metered resource has its plan reviewed first, and stays inside the lab's amounts
    assert "metered resource" in lab(root, "lock", ident, ok=False)
    assert "send the plan to a reviewer" in lab(root, "now")
    lab(root, "review", ident, "plan", "pass", "One thing varies; the refuting line can hold.")
    front(f"{d}/experiment.md", override="{gpu: 5}")
    lab(root, "lock", ident)
    assert "takes a decision about G1.Q1.1" in lab(root, "run", ident, "--wait", "--", *command, ok=False)

    # more than the lab allows is settled in a decision, which holds only what it lists
    lab(root, "new", "decision", "A larger run on the GPU", "--about", ident)
    card = glob.glob(f"{root}/decisions/D2-*.md")[0]
    fill(card, Seen="At full size the run needs about five GPU hours; the lab allows two for one run.", Options="(a) Five hours, once. (b) A quarter of the size.", Recommendation="(a).")
    front(card, holds=f"[{ident}]")
    assert "is held by the decision D2" in lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "waiting" in lab(root, "show", ident) and "Held until it is settled: G1.Q1.1" in lab(root, "now")
    lab(root, "decide", "D2", "--with", "Ada", "Five hours for this one run: a smaller run could not tell the two sizes apart.")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)
    assert "gpu: 1.5 of 10 hours used; one run may use 2" in lab(root, "now") and "rule for gpu: Shut down" in lab(root, "show", ident)

    # a results review that fails is final: the experiment is replaced, and the old one stays
    results(d)
    lab(root, "review", ident, "results", "fail", "The command reads the right file, but the seed was fixed after a first look.")
    assert "(review failed)" in lab(root, "show", ident) and "replace it with a new experiment" in lab(root, "now")
    assert "that is final" in lab(root, "review", ident, "results", "pass", "on second thoughts", ok=False)
    out = lab(root, "new", "experiment", "G1.Q1", "Error at 100 and at 400 flips, seed fixed first", "--replaces", ident, "--because", "The seed was fixed after a first look at the numbers.")
    assert "made G1.Q1.2" in out
    new = folder(root, "G1.Q1.2")
    card = open(f"{new}/experiment.md").read()
    assert "replaces: G1.Q1.1" in card and "`ratio > 0.9`" in card and "uses: [gpu]" in card and "a factor of four apart" in card and os.path.exists(f"{new}/plan/sample.py")
    assert "(replaced)" in lab(root, "show", ident) and "Replaced by G1.Q1.2" in lab(root, "show", ident)
    assert "G1.Q1.2 is not done" in lab(root, "answer", "G1.Q1", "yes", "x", ok=False)
    assert "the record is sound" in lab(root, "check")

    # a run that does not say what it used of a metered resource is a problem
    lab(root, "review", "G1.Q1.2", "plan", "pass", "As before.")
    front(f"{new}/experiment.md", override="{gpu: 1}")  # a lower cap is the agent's to write
    open(f"{new}/plan/sample.py", "w").write(SAMPLE)
    lab(root, "review", "G1.Q1.2", "plan", "pass", "Read again after the change.")
    lab(root, "lock", "G1.Q1.2")
    lab(root, "run", "G1.Q1.2", "--wait", "--", sys.executable, f"{os.path.relpath(new, root)}/plan/sample.py")
    assert "did not record what it used" in lab(root, "check", ok=False)


def locked(tmp_path):
    """A lab with one open question and one locked experiment whose command sleeps, then writes a file."""
    root = str(tmp_path)
    open_question(root)
    ident, d, _ = experiment(root, command='import os, sys, time\ntime.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 0)\nopen(os.path.join(os.environ["LAB_RUN"], "ratio.txt"), "w").write("0.5\\n")\n')
    lab(root, "lock", ident)
    return root, ident, d, [sys.executable, f"{os.path.relpath(d, root)}/plan/sample.py"]


def test_a_run_is_detached_and_one_whose_process_died_can_be_closed(tmp_path):
    root, ident, d, command = locked(tmp_path)
    out = lab(root, "run", ident, "--", *command, "30")
    run_id = re.search(r"started (\S+):", out).group(1)
    assert re.fullmatch(r"\d{8}-\d{4}_G1\.Q1\.1_[a-z0-9]{4}", run_id)
    assert "running" in lab(root, "runs") and "the run to end" in lab(root, "show", ident)  # the command returned; the run goes on
    assert "is still going" in lab(root, "run", ident, "--", *command, ok=False)  # never two at once
    os.killpg(json.load(open(f"{root}/.lab/running/{run_id}/run.json"))["pid"], signal.SIGKILL)  # the machine dies under it
    time.sleep(0.3)
    assert "its process is gone" in lab(root, "runs") and "whose process is gone" in lab(root, "now")
    assert "runs: " in lab(root, "check", ok=False)
    lab(root, "runs", "close", run_id, "the machine was shut down")
    assert "failed (exit -1)" in lab(root, "runs") and "in the store" in lab(root, "runs")
    assert "run it again under the same lock" in lab(root, "now") and "the record is sound" in lab(root, "check")
    assert "finished" in lab(root, "run", ident, "--wait", "--", *command)  # a failed run may be repeated under the same lock


def test_a_failed_move_keeps_the_run_and_publish_retries(tmp_path):
    root, ident, d, command = locked(tmp_path)
    store = tmp_path.parent / (tmp_path.name + "-store")
    open(f"{root}/lab.toml", "a").write(f'store = "{store}"\n')  # a store that is not there: the move must fail, the run must survive
    out = lab(root, "run", ident, "--wait", "--", *command)
    assert ".lab/running/" in out and "not yet in the store" in out
    assert "not yet in the store" in lab(root, "runs") and "lab runs publish" in lab(root, "now")
    assert "not moved" in lab(root, "runs", "publish")
    os.makedirs(store / "runs")
    os.rmdir(f"{root}/runs")
    os.symlink(store / "runs", f"{root}/runs")
    assert "in the store" in lab(root, "runs", "publish")
    assert len(os.listdir(store / "runs")) == 1 and os.listdir(f"{root}/.lab/running") == [".lock"]
    assert not os.path.exists(store / ".incoming") or not os.listdir(store / ".incoming")
    assert "nothing to move" in lab(root, "runs", "publish")  # a second move does nothing, and never overwrites


def test_a_card_stands_on_its_own_a_replacement_says_why_and_the_agent_says_what_it_is_on(tmp_path):
    root = str(tmp_path)
    open_question(root)
    ident, d, command = experiment(root)

    # an experiment names each arm and says what it is, and says what it runs on, before it is locked
    fill(f"{d}/experiment.md", Arms="- 100 flips\n- 400 flips: the same, each from 400 flips", Cases="")
    refused = lab(root, "lock", ident, ok=False)
    assert "Arms names each thing compared and says what it is" in refused and "Cases is empty" in refused
    fill(f"{d}/experiment.md", Arms="- 100 flips: 200 estimates of a fair coin, each from 100 flips\n- 400 flips: the same, each from 400 flips", Cases="200 estimates per arm, one pass.")
    lab(root, "lock", ident)
    assert "- 400 flips: the same, each from 400 flips" in lab(root, "show", ident)

    # a question's briefing joins what is under it, as text for the chat: the same thing its page shows
    front(f"{d}/experiment.md", cost='"Two hundred estimates per arm, a minute on the laptop."')
    brief = lab(root, "brief", ident)
    assert all(x in brief for x in ("**Why we ask.** The simplest check of the square-root law", "**The steps.**", "1. **Error at 100 and at 400 flips** (experiment, planned)", "**Where to look.**"))

    # a question has a short name and the question in full
    lab(root, "new", "question", "G1", "Larger samples", "--asks", "Does the law still hold at ten thousand flips?", "--from", "D1")
    assert 'asks: "Does the law still hold at ten thousand flips?"' in open(glob.glob(f"{root}/goals/G1-*/Q2-larger-samples/question.md")[0]).read()
    assert "Asks: Does the law still hold at ten thousand flips?" in lab(root, "show", "G1.Q2")

    # a replacement says why, in a sentence the operator reads
    assert "--because" in lab(root, "new", "experiment", "G1.Q1", "The same at other sizes", "--replaces", ident, ok=False)
    lab(root, "new", "experiment", "G1.Q1", "The same at other sizes", "--replaces", ident, "--because", "Two sizes were too close to tell.")
    assert 'because: "Two sizes were too close to tell."' in open(f"{folder(root, 'G1.Q1.2')}/experiment.md").read()
    front(f"{folder(root, 'G1.Q1.2')}/experiment.md", because='""')
    assert "does not say why" in lab(root, "check", "--no-rederive", ok=False)
    front(f"{folder(root, 'G1.Q1.2')}/experiment.md", because='"Two sizes were too close to tell."')

    # what the agent is on: one line with its time, standing until a later line about the same card ends it
    assert "why now" in lab(root, "log", "G1.Q1.2", "doing", "Choosing the sizes.", ok=False)
    assert "no `doing` line is open" in lab(root, "now")
    lab(root, "log", "G1.Q1.2", "doing", "Choosing the sizes.", "The first pair could not tell the law from a flat line.")
    assert "- 09:30 | G1.Q1.2 | doing | Choosing the sizes. |" in open(f"{root}/log.md").read()
    now = lab(root, "now")
    assert "on G1.Q1.2 The same at other sizes since 2026-01-02 09:30: Choosing the sizes." in now and "last recorded activity" in now
    lab(root, "log", "G1.Q1.2", "stuck", "The laptop is busy.")
    assert "no `doing` line is open" in lab(root, "now")


def test_a_reading_looks_at_what_exists_and_is_done_when_it_says_what_it_suggests(tmp_path):
    root = str(tmp_path)
    open_question(root)
    out = lab(root, "new", "reading", "G1.Q1", "Every estimate that missed, by cause")
    assert "made G1.Q1.1:" in out
    card = f"{folder(root, 'G1.Q1.1')}/reading.md"
    describe(card, "Reads the estimates that fell outside the band, to say why each did.")
    assert "G1.Q1.1 Every estimate that missed, by cause (reading): say what it looks at" in lab(root, "now")
    fill(card, Looks_at="The 12 estimates of 200 outside the band, in the sampler's own log.")
    assert "read it; then write what was seen and what it suggests" in lab(root, "now")
    shown = lab(root, "show", "G1.Q1.1")
    assert "reading (planned)" in shown and "it can suggest, never confirm" in shown
    fill(card, Seen="- Nine used the short sample.\n- Three had the seed reset.", Suggests="Fix the seed, then measure again.")
    assert "reading (done)" in lab(root, "show", "G1.Q1.1") and "(reading)" not in lab(root, "now").split("Yours next")[1].split("Questions")[0]
    assert "has no finished experiment to rest an answer on" in lab(root, "answer", "G1.Q1", "yes", "The reading says so.", ok=False)  # a reading answers nothing
    lab(root, "new", "experiment", "G1.Q1", "With the seed fixed")
    front(f"{folder(root, 'G1.Q1.2')}/experiment.md", needs="[G1.Q1.1]")
    describe(f"{folder(root, 'G1.Q1.2')}/experiment.md", "Measures again, as the reading suggested.")
    lab(root, "check", "--no-rederive")  # an experiment may need a reading


def test_an_experiment_is_run_until_one_run_finishes_and_each_run_says_what_changed(tmp_path):
    root = str(tmp_path)
    open_question(root)
    broken = "import sys\nsys.exit(3)\n"
    ident, d, command = experiment(root, command=broken)
    lab(root, "lock", ident)
    assert "failed (exit 3)" in lab(root, "run", ident, "--wait", "--", *command)
    assert "read why its last run failed" in lab(root, "now")

    # the same apparatus may simply be run again; a fixed apparatus says what changed and why
    time.sleep(1.1)  # a run's start is recorded to the second
    assert "failed" in lab(root, "run", ident, "--wait", "--", *command)
    time.sleep(1.1)
    open(f"{d}/plan/sample.py", "w").write(SAMPLE)
    refused = lab(root, "run", ident, "--wait", "--", *command, ok=False)
    assert "Say what changed and why" in refused and "--changed" in refused
    assert "finished" in lab(root, "run", ident, "--wait", "--changed", "The sampler exited before drawing anything; it now draws.", "--", *command)
    shown = lab(root, "show", ident)
    assert shown.count("Run 2026") == 3 and "changed since the run before: The sampler exited before drawing anything; it now draws." in shown
    assert "takes no more" in lab(root, "run", ident, "--wait", "--changed", "Again.", "--", *command, ok=False)  # once one has finished, no more
    lab(root, "check", "--no-rederive")

    # the apparatus of the run that gave the results stays as it ran
    open(f"{d}/plan/sample.py", "a").write("# a tweak after the fact\n")
    assert "plan/ changed after" in lab(root, "check", "--no-rederive", ok=False)
