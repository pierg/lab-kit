# lab-kit: the model

The contract. When the code, a skill or the method disagrees with this page, this page wins. The
example in section 2 is an illustration, not a result.

## 1. What you read

A lab is a tree, and the decisions that shaped it.

| Thing | What it says | States |
| --- | --- | --- |
| **Goal** | A short name, what the lab wants to be able to say, and the claim: what we would report if the questions come out as expected, and against whose work. | active, reached, dropped |
| **Question** | A short name, and a yes-or-no question under a goal, written in full: why we ask it, how we would know, what we expect, what would prove us wrong, what we know so far. | under discussion, open, yes, no, dropped |
| **Experiment** | One thing tried to answer a question. What it is for. Before the run: what is compared, each arm by name with what it is, the cases it runs on, what would confirm, what would refute. After: what was found, what it means. | planned, running, waiting, done (confirmed, refuted or unclear), review failed, replaced, dropped |
| **Build** | One thing an experiment needs that has to be made first: what it is for, how it works in plain words, and how we know it works. | planned, in progress, built, dropped |
| **Reading** | One look at what already exists: sealed runs, traces, the benchmark's own definitions. What it looks at; then what was seen and what that suggests. It sets no bar in advance, so it can suggest and never confirm. | planned, in progress, done, dropped |
| **Run** | One try at producing what an experiment demands: when, on which resource, what changed since the run before, how it ended, what it used. An experiment has one or more, until one finishes. | running, finished, failed |
| **Result** | One number from a finished run: a plain label, how it reads, and the command that prints it again. | |
| **Decision** | One thing discussed with you and settled: first what there is to discuss, then what was decided and why. | open, decided |

Goal, question, experiment, run, result: each sits inside the one before it. Ids spell the path: `G1`,
`G1.Q2`, `G1.Q2.3`, and a result is `G1.Q2.3:attack-success`. Decisions are `D1`, `D2`.

**Every goal, question, experiment, build and reading has a title and a description.** The title is a name, short
enough for a list and for the rail: "The fixed attack", not the question itself. A question carries the
question in full beside it (`asks:`), and that sentence is shown wherever the title is. The description
says what the thing is and why it is there. A question's description is its motivation, and has room
for it.

**Every page stands on its own.** The reader was not there. A list is short, and the page a list
leads to is complete: it never points at something it does not explain ("the seven-arm run", "the
reproduction's setting", "our loop") without saying what that is in the same place. An experiment
names each arm and says what it is. A term is explained in the sentence that first uses it; the
glossary is a second chance, not the explanation. A slot may hold paragraphs and a list when that
is clearer than one long sentence. The word budgets are ceilings against sprawl, not targets. If a
card needs its last words cut into fragments to fit, the card is saying too much for one slot or
the budget is wrong, and full sentences win.

A run's id is `<date>-<time>_<experiment>_<four random characters>`, for example
`20261110-1432_G1.Q2.3_k7f2`. It sorts by time, and two machines starting runs in the same minute cannot
collide. It carries the experiment's id and not its title: a run's folder is sealed, and a title gets
reworded.

## 2. An example

> **G1. Security: a gate outside the model**
> An agent can read injected instructions without harm when a gate outside the model decides every
> consequential action. Most defences ask the model to notice the attack; this one assumes it is fooled.
>
> **G1.Q2. Does the gate stop a fixed attack?** (from D1)
> The first test of the gate, against the attack the benchmark ships. If it fails here, nothing later
> matters.
> *We expect* fewer than 1 attack in 20 to succeed with the gate.
> *Wrong if* more than 1 in 5 still succeed.
> *So far* nothing has been run.
>
> **G1.Q2.1. Build: the gate**
> The check that sees every tool call before it runs. Every experiment of this question needs it.
> *Works when* it refuses ten planted attacks and lets ten clean calls through.
>
> **G1.Q2.2. Experiment: the fixed attack, with and without the gate** (needs G1.Q2.1)
> Measures what the gate changes, on the same tasks, with nothing else different.
> *Compares* the same 200 attacked tasks, once with no defence and once with the gate.
> *Confirmed if*
> - attack success with the gate is under 5% (`attack-success < 0.05`)
> - clean tasks finished drop by less than 3 points (`utility-drop < 0.03`)
>
> *Refuted if*
> - attack success with the gate is over 20% (`attack-success > 0.20`)
>
> *Found* and *Means* are written after the run.
>
> **D2. What to do after the fixed attack** (open, about G1.Q2)
> *Seen* The gate cut attack success, but fewer than nine in ten of its wins show a refusal by one of
> its checks, so by our own rule the win does not count yet.
> *Options* (a) Three more passes that separate the checks from chance, about 330 SU. (b) Accept the
> win and move to the adaptive attacker. (c) Rework the checks first.
> *Recommendation* (a). It is the cheapest way to know whether the gate or chance did it.
> *Decided*, once we have talked: what was decided and why, in the lab's words.

Each confirmed-if or refuted-if line is a sentence and its test: a result's name, a comparison, a
number. The lock refuses a line without a test. A bar that is not a number is not a line: it goes in
*Means*, or it is a build's *Works when*.

A bar may decide the outcome either way: written as a confirmed-if line and again, from the other
side, as a refuted-if line (`x >= 0.90` and `x < 0.90`). The page shows such a pair once, as one bar
that confirms when met and refutes when missed. A bar written on one side only leaves the outcome
unclear when it is missed.

The outcome is worked out, never written: confirmed when every confirmed-if line holds and no
refuted-if line does, refuted when any refuted-if line holds, unclear in between. The page leads with
what it means and what was found, then says how many bars were met and names the one that decided the
outcome. There are no confidence numbers, no score sheet and no "what it cannot show" section; a caveat
that matters goes in *Means*.

A build has no lock, no lines and no result. It ends as built, naming its commits and its tests.

A reading has no lock, no lines, no run and no review. It exists because much of what a lab learns
comes from reading what it already has: why each failure failed, which tasks a defence costs, what
a benchmark's cases actually ask. It is cheap, and it comes before the expensive run it shapes. It
is exploratory and its page says so: a count made while reading is not a result, is never named on
a card as one, and confirms nothing. What a reading suggests becomes an experiment with its bars
set in advance, a build, or a decision.

## 3. How a number becomes a result

```
write the card -> lock -> run -> result -> review -> the number may be used on a card
```

Each arrow is a command that refuses when the step before it is missing. You see none of it.

- **Trial run.** A run before the lock, to test that the apparatus works. It is sealed like any run,
  listed when the plan is locked, and never gives a result. On a metered resource it comes after the
  review of the plan, like the run itself.
- **Lock.** What the experiment demands is hashed: what it compares, each arm, the cases, the bars,
  what each outcome would mean, and its limits. That never changes. To change it, the agent starts a
  new experiment that replaces the old one and says why in one sentence (`because:`). The replaced
  one stays in the tree with its results, folded under the new one with that sentence, and off the
  Now page. The lock also records the hash of `plan/` as it was locked, which is the plan the
  reviewer read: the first run is held against it as every later run is held against the run before.
  And it records the resources the experiment uses: `uses:` does not change after the lock. `lab run`
  refuses an experiment whose `uses:` is not what was locked, and says that it is the resources that
  changed; `lab check` reports it.
- **Run.** One try at producing what the experiment demands. An experiment is run until one run
  finishes. Each run pins the apparatus it ran, the configuration and the code in `plan/`, and is
  detached, so it outlives the session; its output is sealed and kept outside git. A run that fails
  is kept, and another may follow. Between runs the apparatus may be fixed, and the next run says in
  one sentence what changed and why (`lab run --changed`); `lab run` refuses a changed `plan/`
  without it, for the first run too, whose "before" is the plan that was locked. `plan/` holds files
  and no links: what a link points at would not be pinned. The test for "another run or a new
  experiment" is whether the comparison, the arms, the cases and the bars can stay word for word as
  they are locked.
  **Every run is listed.** The store is outside git, so the experiment's folder keeps `runs.tsv`, in
  git: one row when a run or a trial starts, and one when it ends, with how it ended and its seal.
  Rows are only added. `lab run` reads that list as well as the store, so a clone without the store
  still knows what ran. `lab check` asks that every listed run is in the store with the seal that
  was listed, and that every run in the store is listed. Where the store is not mounted the check
  says so and checks no run.
  **A run that is lost.** A run can start and never report back: the machine dies with its folder on
  it. Its `started` row stays. `lab runs lost <run> "<why>"` adds a row that says so, with the reason
  and, by `--used`, what it spent. A lost run counts as a run that failed: another may follow, and it
  stays in the experiment's list and on its page with the reason. The command refuses a run whose
  folder is here, which is closed or published instead.
  **What git holds, and from when.** The list of runs, the lock, the reviews, the log, the decisions
  and the amounts of the resources are tamper-evident, not tamper-proof: `lab check` compares them
  with the lab's git history, so a change shows from the commit that first holds them, and not
  before. A lock that was never committed can be rewritten, and a run whose rows were never
  committed can be removed, with nothing to show it. So the lock is committed when it is made, the
  `started` row as soon as `lab run` returns, and the end row with the results when the run ends.
  `lab now` and `lab check` say which locks and lists of runs are not committed yet. With no commit
  at all nothing is held, and `lab check` says that too; `--strict` turns each of these into a
  failure.
  **Reviewed rows stay.** The rows of `results.tsv` may change until a review passes them. Once a
  results review that passed is committed together with the rows it read, those rows stay, each as
  it was, whatever happens to the card and to the reviews after it. Emptying the file or removing it
  together with Found and Means, and filling it later with other rows for a new review, is a
  problem `lab check` reports at every step: a different result is a new experiment. A review is
  bound to the rows it read by its `of`, so only those are held: a draft row committed after a
  review, which that review never read, may still be corrected before the next review reads it.
  **The history that is read.** The check reads the history of the record under the lab's root as
  that root is now. Moving the lab's root inside its repository, or to another repository, starts
  again what is held: what was committed under the old root is not compared. And it needs the
  repository's full history. A shallow clone holds only its last commits, so against it almost
  nothing is held: `lab check` says so in a note, and fails with `--strict`. CI fetches all of the
  history before it checks (`fetch-depth: 0` in `actions/checkout`).
  **Where the record is.** The check reads the history of the lab's own record and of nothing else:
  `log.md` and `resources.toml` at the lab's root, `decisions/D<n>-<name>.md`, and each experiment's
  `lock.json`, `runs.tsv`, `results.tsv` and `reviews.tsv` in its folder,
  `goals/G<n>-<name>/Q<n>-<name>/<n>-<name>/`. The lab's root may be a folder inside a larger
  repository. What that repository holds or once held anywhere else, such as the folders of a lab
  kept with an earlier kit, or a file with one of these names inside `plan/`, is not the lab's
  record: its history is not read, and removing it is not a problem.
  **A rename.** A file of the record is known by the numbers in its path and not by the words:
  `goals/G1-<any name>/Q2-<any name>/3-<any name>/lock.json` is the lock of `G1.Q2.3`, and
  `decisions/D4-<any name>.md` is `D4`. When a title is reworded, the folder or the file named after
  it may be renamed to match. That is a rename and nothing else: what was committed under the old
  name is held under the new one, so the lock is still the lock first committed, every committed
  row is still there, and a settled decision still says what it said. A number never changes. A file
  that is under another number, or outside these places, is not that file: the one that was
  committed is gone, and `lab check` says so, as it does for a file deleted outright.
  Two things keep this honest. The first run that finishes is the only source of results, and
  nothing more runs under that experiment, so nobody chooses which numbers count; a different try
  after that is a new experiment, because the numbers have been seen. And the apparatus of the run
  that finished stays as it ran: `lab check` fails when `plan/` changes after it. `lab run` also
  refuses to start a run while another of the same experiment is going, and two `lab run` commands
  given at once start one run. Three passes of one plan
  are one run that loops three times. Scoring the part of a failed run that did finish is a new
  experiment, with its own bars.
- **Result.** A row with the number, what it is compared with, and a command that prints it from the
  sealed run. `lab check` re-runs every command. The ends of a result's interval are rows named
  `<name>.low` and `<name>.high`; a page shows them with the result, not as rows of their own.
- **Review.** A separate session that did not do the work. One review, after the results; a second,
  of the plan, only before a run that uses a metered resource. It fails the experiment when:
  1. a number is not what its line says it is;
  2. more than one thing varied between the arms;
  3. a tool failed and its arm was kept;
  4. a line was written when its number was already known, from an earlier run of the same comparison
     or from a trial run that measured it. A trial that only showed the apparatus starts does not count.
  5. a failed run's partial numbers were read before the apparatus was changed for the next run.

  A plan review that fails is fixed before the lock, and read again. A results review that fails does
  not finish the experiment: its outcome is not shown and no card may name its results. The plan and
  the rows stay as they are. The remedy is a new experiment that names the one it replaces; the site
  folds the old one under it, and the old results keep re-deriving.

A card never types a result's number. It names the result, and the value is filled in when the card is
shown, written the way its row says it reads: a share as a percentage, a difference between two shares
in points. When a named result belongs to a replaced experiment, the page says so and `lab check` fails.

## 4. Who decides

You decide two things: **direction** and **resources**. You decide them in a discussion with the agent,
not by approving requests.

- **Direction.** The goals and the questions.
- **Resources.** Everything outside the lab that it may touch: what it may use, how much, and what it
  may do there.

**A decision** is how either is settled. The agent opens one when:

- a question is answered, or an experiment refutes what we expected;
- a result changes what the next question should be;
- it wants to add, reword or drop a goal or a question;
- the resources do not cover what the settled work needs.

While it is open, a decision says what was **seen**, two or three **options** with what each costs and
changes, and a **recommendation**. It may list what it **holds**: the experiments that should not start
until it is settled. Everything else keeps moving.

You talk it through in chat. The agent then writes what was **decided** and why, in the lab's words,
shows you that text, and records it. Your messages are not stored and not shown. A decision is recorded
only out of a conversation with you.

**What a decision settles is approved.** The goals and questions it adds, the experiments it names and
the resources it sets need no further yes. Every goal and question names the decision it came from, and
nothing under a question is locked or run while that decision is still open. Nothing else asks for your
approval: an experiment added later under a settled question is the agent's to plan and run.

You may also decide something nobody raised: add, change or drop an experiment or a build, reorder the
work, stop a run. Say it, and the agent records it as a decision and follows it. Two things hold for
you as for the agent: a locked plan is changed by a new experiment that replaces it, and an outcome is
worked out from the results, not decided.

**A settled decision stays as it was settled.** Its `decided:`, its `about:` and its Decided text never
change once committed; a change of mind is a new decision. `lab check` holds this against the lab's
history. So a decision cannot be made, afterwards, to be about something it never discussed.

The agent decides everything else and records each choice in the log. It drops an experiment or a
build that will not be done, saying why. It marks a question yes or no itself, with `lab answer`, and
the command refuses while an experiment of that question is neither done, replaced nor dropped, and
when no experiment of it is done: a reading alone answers nothing. `lab check` asks the same of every
answered question, and that the log holds the line `lab answer` wrote. It never asks you to check
its work, which is the review's job, and it never opens a decision for something that is its own to
decide.

**Resources** are set once, for the whole lab, in `resources.toml`. Each machine, cloud allocation, API,
repository and place the lab publishes to has:

- what it is, and where its key is kept (never the key);
- where it is metered, its unit, how much is granted, and how much one run may use. These amounts are
  enforced: `lab run` refuses a run that would pass them, and `lab check` adds up what every run used;
- for a metered resource, the decision that set those amounts (`from`). It is a settled decision
  that lists the resource under `about:`, so a resource that appears later needs a decision of its
  own. An amount, or its unit, changes only together with `from`, which then names the later
  decision that changed it. A resource is never removed: one that is no longer used says so
  (`retired = "<why>"`) and takes no run. Use outside a run is a row added under `other_use`, and
  rows are only added. `lab check` holds all of this against the lab's history, and `lab run`
  refuses a metered resource whose amounts, or the decisions behind them, are not as git holds
  them, before anything is spent;
- its rules, as plain sentences: what the agent may do there, such as "shelved as soon as a run ends"
  or "opens pull requests, never merges". The agent follows them; nothing checks them.

The lab touches nothing outside itself that is not listed there. Every experiment may use every resource
under these, without asking. An experiment may carry an override, and by default has none. An override
is a resource and a cap, nothing else. A lower cap is the agent's to write. A higher cap, a waiver of a
rule, a new resource or a larger grant comes out of a decision: one that lists that experiment, or
that resource, under `about:`.

## 5. What the agent uses

- **To look:** `lab now`, `lab show <id or path>`, `lab brief <question>`, `lab since`, `lab define <term>`. Each shows one level,
  so the agent reads a card before it opens a file. Of each run, `lab show <experiment>` says how
  many files it holds and where: how many at the top of its folder, and how many under each folder
  there, `work/` included. It lists none of them, so a run whose output is all in `work/` does not
  look empty.
- **To write:** `lab new` (a goal, a question, an experiment, a build, a reading, a decision),
  `lab log`, `lab decide`, `lab answer`.
- **To be seen:** `lab log <id> doing "<what>" "<why now>"` whenever it starts on a card. It is the
  one line the operator reads to know what the agent is on.
- **For evidence:** `lab lock`, `lab run`, `lab runs`, `lab review`, `lab check`. `lab runs` lists
  every run; it also closes a run whose process died (`lab runs close`), moves an ended run into
  the store (`lab runs publish`) and copies one from a store this machine does not mount
  (`lab runs fetch`). Closing a run stops whatever its command left running, reads what it said it
  used, and takes `--used <resource>=<amount>` for a run that said nothing; that amount is recorded
  as stated by hand. Where the system gives no way to tell that a process is the run's, nothing is
  stopped and the command says so. `lab runs lost` records a run that started and whose folder is
  gone for good.
- **Once:** `lab init`. Run again, it restores the method, the skills and the reviewer role.

That is fifteen commands. `lab --help` lists them the same way.

The log is one file. Every line carries its time. A line is one of five kinds: a decision was
recorded, the agent decided, a result, something is stuck, and what the agent is starting on now.

**The present.** The operator's first question is whether anything is happening. The record answers
it: the front page opens with the runs still going, the agent's last `doing` line (what, why now,
since when), and the time of the last recorded activity. A `doing` line stands until a later line
about the same card, or the card being finished, ends it. When there is none, the page says that
nobody is on anything and names the next step. Nothing is inferred from a session being open.

Four skills: `lab-set-up`, `lab-work`, `lab-review`, and `lab-talk` (tell you where things stand, bring
a decision to you, record what was decided). One role: the reviewer.

Seven rules:

1. Say what would refute it before you run.
2. A number counts only as a reviewed result of a locked plan.
3. A miss is recorded like a hit, and nothing locked or recorded is edited.
4. Write for a reader who was not there: every page stands on its own, in plain words and the
   glossary's terms, and a number is said once.
5. Decide everything that is not direction or resources, and never wait idle. For those two, open a
   decision with options and a recommendation, and work on what it does not hold.
6. Record what was decided and why, in the lab's words, and show the operator the text as recorded.
   Never record a decision that was not discussed with them.
7. Say what you are on. When you start on a card, log what you are doing and why now.

`lab check` holds what can be held mechanically: ids and links, the goal's vocabulary being terms of the glossary, a title and a description on every
card, short cards that write only their own front matter, a test on every line, a reason on every
replacement, unchanged locks, sealed runs, results that still re-derive and were reviewed, use inside
the resources' amounts, a decision behind every goal, question and metered amount, an experiment
behind every answer, the method and the skills as the kit installed them, and a history that only
grows. What it cannot read as this page describes (a mistyped folder, a list written as one value, a
file that is not text) is a problem it reports; no command stops on it.

`lab check` runs the command of every row in every `results.tsv`, as a shell command, each for at
most `rederive_timeout` seconds (`lab.toml`, 120 unless set). Run it only on a lab you trust, as
you would its code; `--no-rederive` runs none of them. Where the lab has no commit or its repository is a shallow clone, the store
is not mounted, or another library that a card's `see:` points into is not on the machine, the check
says in a note what it could not check and still passes; with `--strict` that is a failure, which is
what CI wants.

Every command that writes validates everything first, so that a refusal leaves nothing half
written, and only one of them writes at a time.

## 6. The files

```
lab.toml  AGENTS.md  GLOSSARY.md  resources.toml  log.md
decisions/D1-<slug>.md    what was discussed and decided
goals/G1-<slug>/
  goal.md
  Q1-<slug>/
    question.md
    1-<slug>/
      build.md            a build's card (or reading.md, a reading's card)
    2-<slug>/
      experiment.md       an experiment's card, with its override if it has one
      plan/               the configuration and the code the run executes
      lock.json  runs.tsv  results.tsv  reviews.tsv
runs/<run id>/            sealed output, outside git
docs/                     the folio library: explanatory pages, and the site
.agents/  .lab/METHOD.md  the skills, the reviewer role and the method, installed by `lab init`
.ignore                   keeps plan/ and runs/ out of default searches
```

A folder is named after its card's title, so a short title gives a short path.

## 7. The site

Now, Graph, a page per goal, question, experiment, build, reading and decision, Decisions, Log,
Resources, Glossary. Every page has the copy-path control.

**A question's page is its briefing.** The question is the unit the operator follows, so its page
joins everything under it, in the order they ask: where we are coming from (what the questions it
needs established), what we know so far, why we ask, how it works, what is needed from you, the steps
and where each stands, what it costs, what it cannot show, where to look. Half of it is worked out
(the steps, the numbers, the spend, the files) and half is written once. `lab brief <question>` gives
the same briefing as text, which is what the agent says in chat when asked what is going on: the page
and the answer in chat cannot differ. An experiment's page is the evidence behind one step.

**Now** is read top to bottom in the order the operator asks: what is happening at this moment and
how fresh the record is; what there is to discuss with you; what is next and who moves it; where each
question stands (what is known so far, and nothing else); the latest events; what is left of each
resource. Nothing on it is static text except one line per goal.

**An example on every question.** A question's page carries one case, step by step, as a numbered
list that says who does what: the user, the agent, the tools, the gate, the scorer. A real episode
where one exists, and said to be only the flow where none does. The goal's page says once who plays
each role, states the design before the approximation, and lists its vocabulary: the words every card
uses the same way, each drawn with the glossary's definition.

**What was dropped** stays in the record: a dropped goal or question keeps its card and its page,
and leaves Now, the rail and the graph.

**A goal's page** holds its claim and its story: one list, oldest first, of what was found, what got
stuck, what the agent chose and what was decided with you, each decision with its text. It is the
answer to "what happened, and why are we here".

The pages are written for a reader, and the agent's detail stays in the files and in `lab show`:

- a result shows its label, its value as it reads with its interval, and what it is compared with. Its
  command is not shown. The results a bar tests or the card names are listed; the others are folded;
- a reviewer's note shows its first sentence and folds the rest. Nothing in it is turned into a link;
- a line shows its sentence, the value and whether it holds. Its test is a tooltip;
- an outcome names the line that decided it;
- an experiment says near the top when it ran, on what, and what it used. Its runs are a list in
  order further down: its id, when it started, how it ended and what it used, what changed since
  the run before, and its folder. Its reviews follow;
- a replaced or dropped experiment is folded under its question, not listed beside the live ones. The
  one that replaced it says which plan it is (second, third) and why each earlier one was replaced;
- a run is named by its id, with its folder beside it to copy, in the list of runs on its
  experiment's page and nowhere else: no sentence of a card carries a run's id.

## 8. What changed from lab-kit 0.6

| Gone | Instead |
| --- | --- |
| Attempts a, b, c | The demand is locked once; an experiment is run until one run finishes, and each run says what changed in the apparatus. A changed demand is a new experiment that replaces the old |
| Predictions with confidence, decision rules, score sheet, limits | Confirmed-if and refuted-if lines, each testing one result and saying what it is for; what each outcome would mean; two or three limits; the outcome is worked out |
| A protocol document of several thousand words | The card for the reader, and `plan/` (the configuration and the code) for the reviewer |
| An outcome written by hand on an experiment | Worked out from its lines and its results |
| Missions approved one by one, and a review memo before a change of direction | A decision: something discussed with you, with options and a recommendation, closed by what was decided and why |
| Two audits per experiment | One review; a second only before a run that uses a metered resource |
| Budgets, allowance per question, grant history, ledger | One resources file for the lab, an optional override per experiment; each run records what it used |
| Local rules about machines and keys in `AGENTS.md` | The rules of each resource, in the resources file |
| Question status plus strength | One state |
| "What the operator reserves", and reach as its own kind of decision | You decide direction and resources, by discussion. What the agent may do outside the lab is a rule of the resource it touches |
| The operator's sentence of approval kept as the record | What was decided and why, in the lab's words; the operator's messages are not stored |
| `rests_on` lists and number matching | A card names the result instead of typing the number |
| A log per goal and per question, ten kinds of line | One log, five kinds of line |
| Everything under a question is an experiment | Three kinds of step: an experiment (bars set in advance), a build, and a reading (a look at what exists, which suggests and never confirms) |
| Sixteen rules, six skills, twenty-one commands | Seven rules, four skills, fifteen commands |
| Asking the agent in chat whether it is working | The front page says what is running, what the agent is on and since when, and when the record last moved |
| `lab.yaml`, and the record kept as folio documents: questions, claims, results, protocols, a journal | `lab.toml`, and cards in `goals/` and `decisions/`. folio draws the site from them through `lab_kit.site` and stores no page |
| folio as a requirement of the command | The command needs no folio; only the site does |
| The `lab-kit` command | `lab`. `lab-kit` still starts it |

A lab kept with 0.6 is not read by 1.0, and no command converts one. Its questions and experiments are
written again as cards. `tools/import_run.py`, in the kit's repository, brings an old experiment's lock
and its sealed runs across as what they were.

## 9. Formats

**A card** is front matter, then its description as a paragraph, then `## Slot` sections. It never
holds an id, a state or an outcome. Every file of a lab is UTF-8 text; line ends of either kind
read the same, and so hash the same where a review is bound to a file. The front matter sits between
the first two lines that are exactly `---`. A key that holds a list (`needs`, `uses`, `see`, `about`, `holds`, `commits`,
`tests`) is written as one, `[a, b]`; every other key holds one value.

| Card | Front matter | Slots (word budget) |
| --- | --- | --- |
| `goal.md` | `title:`, `from:` (its decision); `reached: true`; `dropped: <why>` | description (70), Claim (90), Example: the idea in one case, from the reader's own domain (260), Approach: the design, how this lab approximates it, and where it knowingly differs (340), Roles: a list, `- <role>: <who plays it and what it does>` (170), Vocabulary: a list of names only, `- <term>`, the few words every card uses the same way; each is a term of `GLOSSARY.md`, which defines it (260) |
| `question.md` | `title:` (a short name), `asks:` (the question in full), `from:`, `needs:`; `dropped: <why>`; `answer:` and `answered:` are written by `lab answer` | description: why we ask (130), How we would know (150), Example: one case step by step, a numbered list (380), We expect (70), Wrong if (70), So far (180) |
| `experiment.md` | `title:`, `needs:`, `uses:` (resources), `override: {resource: cap}`, `cost:`, `replaces:` with `because:` (one sentence), `waiting_on:`, `dropped: <why>` | description (70), Compares: the comparison in a sentence (80), Arms (260), Cases (100), Confirmed if (150), Refuted if (110), Outcomes (200), Limits (120), Found (180), Means (150) |
| `reading.md` | `title:`, `needs:`, `dropped: <why>` | description (70), Looks at: what, and where it is (110), Seen (320), Suggests (150) |
| `build.md` | `title:`, `needs:`, `commits:`, `tests:`, `dropped: <why>` | description (60), How it works (200), Works when (80) |
| `D<n>-<slug>.md` | `title:`, `about:` (the goals, questions, experiments or resources it concerns), `date:`, `holds:`; `decided: {date, with}` is written by `lab decide` | Seen (120), Options: a list, one option an item (200), Recommendation (80), Decided (120) |

Any card may carry `see:`, a list of pages that explain it: pages of the lab's own library, and pages
of another library its charter names, written as folio writes them (`pier-folio:/content/readings/...`),
for background the lab rests on and did not write. A card's prose may link the same way, as
`[the words](target)`: a name the reader may not know, such as a paper or a method, is linked where
it is first used.

`lab check` asks that every page under `see:` is there. A page of another library is looked for in
that library's folder, where the charter says it is. When the folder itself is not on the machine,
as in CI, which checks out the lab alone, the page cannot be looked for: that is a note, and a
failure only with `--strict`. When the folder is there and the page is not, or the charter names no
such library, it is a problem.

**The glossary** is `GLOSSARY.md`, the only place a word is defined. A group is a `# Group` heading
and a term a `## Term` heading under it, followed by its definition as a paragraph and these optional
lines, each `- key: value`:

```
## Guard
The part that reads every call and refuses the ones the contract forbids.
- code: kna.gate:Guard
- avoid: gate, filter, policy
- see: entries/kna-gate
```

`code:` is where the term is in the code. `avoid:` lists, separated by commas, the words not to use
for this thing. `see:` names a page that explains the concept: a page of the lab's own library
(`entries/kna-gate`) or of a library the charter names (`pier-folio:/content/concepts/lora/`), the
same targets a card's `see:` takes. `lab define <term>` prints all of it. The glossary page shows the
definition, the code, the page as a link and the avoid words in small type; the hover on a term in
prose is the definition alone.

A word is defined once, in the glossary. A card that needs a word adds it there first, then uses it;
no card defines a word of its own. A concept that is not this lab's own (a method, a paper's idea) gets
a one-line entry and a `see:` link to the page that explains it, not a new explanation. The goal's
Vocabulary lists terms by name, and the goal's page and `lab show` draw each with the glossary's
definition and avoid words. `lab check` holds this: a name in Vocabulary that is not a term of the
glossary is a problem, and so is an item written with a meaning (`- word: what it means`): the part
before the colon is taken as the name, the glossary's text is what is shown, and the card must list the
name only. It checks an entry's `see:` as it checks a card's, including the note, and no failure, when
the other library is not on the machine. It does not look for avoid words in cards: a word to avoid for
one thing is often the right word for another, so `avoid:` is for the writer and the reviewer to read.

**An arm** is a list item under Arms: its name, a colon, and what it is, so that a reader who has
never seen it knows what was run.

```
- contract only: the gate's planning request, then a guard that reads every call and refuses nothing
```

The lock holds Compares, Arms, Cases, the lines, Outcomes and Limits, and refuses an experiment with
no arm or no cases.

**What a bar is for.** A confirmed-if line may open with its role: `answer:` for the one comparison
the experiment exists to make, `readable:` for a bar without which that comparison says nothing (the
training worked, the instrument kept its form), `counts:` for a bar without which a good answer is
not credited (the mechanism shows in the traces). The page groups the bars under those three heads,
so the reader sees which line is the answer. The outcome is worked out as before, from all of them.

**Outcomes** is a list: each outcome the bars allow, what it would mean, and what would be done
next. **Limits** is a list of the two or three things the experiment cannot show that a reader
would otherwise assume. Both are written before the run and held by the lock. `cost:` in the front
matter is one or two sentences on how large the run is and why it needs the resource it uses; the
amounts used and still allowed are worked out beside it.

**A line** of Confirmed if or Refuted if is a list item: a sentence, then its test in backticks inside
brackets.

```
- attack success with the gate is under 5% (`attack-success < 0.05`)
```

A test is a result's name, one of `<`, `<=`, `>`, `>=`, and a number. At most six lines on each side.

**A named result** on a card is `{name}` inside its own experiment and `{G1.Q1.2:name}` elsewhere.

**`results.tsv`** is tab-separated: `name`, `label` (what the number is, as a phrase that stands on its
own: what is counted, out of what, under which arm, with no "that" or "the same" pointing at another row), `value` (a
plain number), `reads` (`percent` for a share, `points` for a difference between two shares, or empty),
`versus` (what it is compared with), `command` (run from the lab's root with `RUN` set to the finished
run's folder; prints `value` exactly, and reads `$RUN`, or it would not be printing from the sealed
run). A value is a number in plain digits, with a sign, a point and an exponent if
it needs them. A field is the text between two tabs on one line. One wrapped in double quotes
with each quote inside written twice, as a spreadsheet writes it, is read without them; any other
quote is a character like any other.

**`reviews.tsv`** is written by `lab review`: `date`, `stage` (plan, results), `verdict` (pass, fail),
`by`, `of` (a hash of what was read), `note`.

**`resources.toml`** has one table per resource: `what`, `key` (where it is kept), `rules` (a list of
sentences), `retired` (why, once it is no longer used), and for a metered resource `unit`, `granted`,
`per_run` and `from` (the settled decision that set the amounts and lists the resource, as `"D1"`). Use of a metered resource
outside any run, such as a machine woken when nothing ran, is a line the agent adds under
`other_use`: `{date, amount, what}`. What is used is the runs' use plus these lines.

**A run's record**, `run.json`, holds the hash of `plan/` as it ran (`plan`) and what changed since
the run before, or for the first run since the lock (`changed`). Its seal is one hash over that
record, which lists the hash of every other file in the run's folder. `lock.json` holds the version of
the kit that made it (`kit`), when the experiment was locked, the hash of the demand (`card`), the
hash of `plan/` as it was locked (`plan`), the resources it uses (`uses`) and the trial runs that
existed. A lock that names its kit and lacks one of these is not a lock the kit wrote, and
`lab check` says so.

**How a folder is hashed.** `plan/` is hashed file by file: the length of its path, the path, the
length of its content, the content. A lock or a run made this way says `"hash": 2`. One with no such
marker was made by an earlier kit, which wrote the path, a newline and the content; it is verified
the way it was made, and never hashed again. Either way the hash leaves out what Python writes when
it imports a script, which is no part of the plan: a folder named `__pycache__` with everything in
it, and any file whose name ends in `.pyc`, wherever it sits. Nothing else is left out; a hidden
file is hashed like any other.

One exception, for what lab-kit 1.0.0 made. That version did hash those files, so a plan locked or
run while a `__pycache__` sat in `plan/` holds a hash that counts them. When a hash of `plan/` held
by a lock or a run does not match and the experiment's lock says `"kit": "1.0.0"`, the folder is
hashed once more the way 1.0.0 did, those files included, before a change is reported. It applies
to no other lock, and it verifies only while those files are still there as they were.

A `.pyc` file in `plan/` that is not inside a `__pycache__` is refused, as a link is: Python would
import it in place of a script, and no hash covers it. `lab lock` and `lab run` refuse the plan and
`lab check` reports it. Under a lock that 1.0.0 made, whose hash did count such a file, it stays.

**`runs.tsv`**, beside the lock and in git, is written by `lab run` and by the run as it ends: `run`
(its id), `kind` (run, trial), `what` (started, ended, lost), `at`, on the ended row `exit` and `seal`,
and on a lost row `used` (`{"<resource>": <amount>}`, or empty) and `note` (why it is lost). When a
run ends on a machine that cannot write the lab, `lab runs publish`, `lab runs fetch` or
`lab runs close` adds its ended row.

**A run** writes into the folder `LAB_RUN` names. If it uses a metered resource it writes
`used.json` there: `{"<resource>": <amount>}`, each amount a number, finite and not negative;
anything else is refused when the run is sealed and reported by `lab check`. Its record is `run.json`.

**A log line** is `- time | about | kind | what happened | so what`, under a `## <date>` heading, both
in UTC. The file holds no other heading, and a line no other `|`. The kinds are `decision`, `agent`, `result`, `stuck` and `doing`. `lab decide` writes the
`decision` lines, each with the opening of what was decided. A `doing` line holds what the agent is
starting on and why now. A line written before the kit kept the time has none.

**Worked-out states.** A question is under discussion while the decision it came from is open, then
open, then yes or no; a page calls an open question with nothing under it "not started". A build is in
progress once the log has a line about it, and built once it names its commits. An experiment whose
results review failed shows as review failed until it is replaced or dropped.

**What a step needs.** `needs:` on an experiment, a build or a reading names other steps, anywhere in
the tree: under its own question or another, before it or after it. A step is not the agent's to move
while one it needs is neither done nor built, and `lab lock` and `lab run` refuse it until then. Each
step's state is worked out after the state of everything it needs, wherever that sits, so the order
of the cards changes nothing: a build under the second question that needs a reading under the third
moves as soon as that reading is done. Every view says the same: `lab now`, `lab show`, `lab brief`,
and the site's pages and rail. Steps that need each other in a circle are a problem `lab check`
reports. Until the circle is broken none of them moves, whatever the others' states, and each says
which of its needs leads back to it. A step that needs one that is dropped or replaced would wait
for ever, so what it waits on says so, and says what to do: remove the need or replace it. A need
that names nothing in the lab, or something that is not a step, holds the step in `lab lock` and
`lab run` as `lab check` reports it. A question's `needs:` names the questions it builds on, for its
briefing; it changes no state.
