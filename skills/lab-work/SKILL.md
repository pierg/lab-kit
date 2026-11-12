---
name: lab-work
description: >-
  Carry the lab's work forward on your own: propose a question, plan and run its experiments, build
  what they need, record what was found. Use at the start of every working session, after any
  restart, and when the operator says "go", "proceed", "continue", "run it", or states something
  they want to find out.
---

# lab-work

You do the work and take the decisions. The operator reads the site and talks to you. Two things are
theirs: direction (the goals and the questions) and resources. They settle those with you in a
discussion, recorded as a decision. What a decision settled needs no further yes.

## Start, and after any restart

`lab now`. If something is under **To discuss with the operator** and they are here, bring it to them
first (the lab-talk skill). Otherwise take the first line under **Yours next**: it says what to do.
`lab show <id>` before you touch anything.

Then say what you are on, before the first edit: `lab log <id> doing "<what you are starting on>"
"<why now>"`. Do it again each time you move to another card. This line is the top of the operator's
front page: it is how they know the lab is alive without asking you. It ends by itself when you log a
result, a stuck line or a choice about the same card.

## Writing a card

The operator reads every card on the site, usually days later and without you. Write for that reader.

- The `title:` is a short name, fit for a list: "The fixed attack". The paragraph under the front
  matter is the description: what it is and why it is there.
- A page stands on its own. Never point at something the page does not explain: not "the seven-arm
  run", but what that run was; not "our loop", but "KNA's own agent loop, the one the gate plugs
  into". Explain a term in the sentence that first uses it, even when the glossary has it.
- A paper, a method or a tool the reader may not know gets a few words saying what it is, and a
  link where it is first named: `[PISmith](pier-folio:/content/readings/...)` for a page of a
  library the charter names, or a web address. Put the same page under `see:`.
- Use the goal's vocabulary. The goal's card pins the few words the lab uses for its own things;
  use those words, the same way, on every card, and add a word there before you use a new one.
- Say the design before the approximation: what the idea wants, then how this lab builds it and
  where it knowingly differs. A shortcut of the implementation is never the definition.
- Say what is measured and what is your reading of it, in so many words.
- Use a list when the content is a list (arms, options, steps), and a second paragraph when one
  sentence is carrying too much. The word budgets are ceilings, not targets: short is good only
  while nothing is missing.
- Read the card as someone who was not there. If a question comes to mind, the card answers it.

## When to open a decision

Open one when a question is answered or an experiment refutes what was expected, when a result
changes what the next question should be, when you want to add, reword or drop a goal or a question,
or when the resources do not cover the settled work. Not for anything else.

1. `lab new decision "<what it is about>" --about <the goals, questions or experiments it concerns>`.
2. On its card write **Seen** (what was observed, naming results), **Options** (a list of two or
   three, each item an option with what it costs and what it changes) and **Recommendation**. Put under `holds:` only the
   experiments that should not start before it is settled.
3. Keep working on everything it does not hold. The lab-talk skill takes it to the operator and
   records what was decided.

A goal or a question is made out of a decision: `lab new question <goal> "<short name>" --asks "<the
question, in full>" --from <decision>`. Its description is the motivation: why we ask, and what
depends on the answer. **How we would know** is the idea of the test in plain words, before any
experiment exists. **Example** is one case, step by step, as a numbered list saying who does what:
a real episode once there is one, and until then the flow, said to be only that. Then **We expect**
and **Wrong if**. Nothing under it is locked or run
until that decision is settled; after that it needs no further yes.

## An experiment

1. `lab new experiment <question> "<title>"`. On the card, after its description:
   - **Compares**: the comparison in one sentence, and what is the only thing that differs.
   - **Arms**: one line per thing compared, `- <name>: <what it is>`, each complete enough for
     someone who has never seen it. A baseline or a published row that is not run is an arm too.
   - **Cases**: what it is run on, how many, and how many passes.
   - **Confirmed if** and **Refuted if**: one line per bar, each a sentence and its test:

     ```
     - attack success with the gate is under 5% (`attack-success < 0.05`)
     ```

     A test is a result's name, a comparison and a number. A bar that is not a number is not a line.
     A bar that decides it either way is written on both sides (`x >= 0.90` to confirm, `x < 0.90`
     to refute): the page shows it once. A bar written only under Confirmed if leaves the outcome
     unclear when it is missed, which is often what you mean.
     Open a confirmed-if line with what it is for: `answer:` on the one comparison the experiment
     exists to make, `readable:` on a bar without which that comparison says nothing, `counts:` on
     a bar without which a good answer is not credited.
   - **Outcomes**: a list of each outcome the bars allow, with what it would mean and what you
     would do next. **Limits**: the two or three things it cannot show that a reader would assume.
   - `needs:` the builds and experiments it depends on. `uses:` the resources it runs on. `cost:`
     one or two sentences on how large the run is and why it needs that resource.
   - `override: {<resource>: <cap>}` only when one run should use less than the lab allows. More
     than the lab allows takes a decision about that experiment.
2. Put the configuration and the code the run executes in `plan/`, as files: a link is refused,
   because what it points at would not be pinned. Test the code on a case with a known answer.
3. If it uses a metered resource, send a reviewer for the plan: a separate session with the
   reviewer role, given only the id and the stage. Nothing runs on a metered resource before that
   review has passed, a trial included.
4. To check that the apparatus starts: `lab run <experiment> --trial -- <command>`. A trial never
   gives a result. Do not measure the lines' numbers in a trial.
5. `lab lock <experiment>`. If it refuses, it says what is missing. The lock records `plan/` as it
   is, and the resources under `uses:`: if you change `plan/` before the first run, that run says
   what changed and why (`--changed`). **Commit the lock now**, with the card and `plan/`. Git holds
   a lock only from the commit that first has it.
6. `lab run <experiment> -- <command>`. It starts detached and returns. The command starts in the
   lab's root with `LAB_RUN` set to the run's own folder, and writes everything there. If it uses a
   metered resource it writes `$LAB_RUN/used.json`: `{"<resource>": <amount>}`. `lab runs` shows it.
   The run is listed in `runs.tsv` in the experiment's folder. **Commit that file as soon as
   `lab run` returns**, before the run ends, and again when it has ended, with the results.
   `lab now` says which locks and lists of runs are not committed yet.
7. When it has finished, write `results.tsv` in the experiment's folder, tab-separated, with the
   columns `name`, `label`, `value`, `reads`, `versus`, `command`: one row for each number a line
   tests, and any other number worth citing. `label` says in plain words what the number is, and stands on its own: what is counted, out of
   what, under which arm ("share of attacked cases in which the injection wins, with the gate"),
   never "the same" or "that difference".
   `value` is a plain number. `reads` is `percent` for a share, `points` for a difference between
   two shares, or empty. `command` is run from the lab's root with `RUN` set to the run's folder,
   and prints `value` exactly. Name the ends of a number's interval `<name>.low` and `<name>.high`:
   the page then shows them with the number.
8. Send a reviewer for the results.
9. Once the review has passed, write **Found** and **Means** on the card. Name each result instead
   of typing its number: `{attack-success}`. It is shown the way its row says it reads. Rewrite the
   question's **So far** the same way, with full names: `{G1.Q1.2:attack-success}`.
10. `lab log <experiment> result "<what was found, in a sentence, without numbers>" "<so what>"`.

The outcome is worked out from the lines: you never write it.

## When a run fails

An experiment is run until one run finishes. Read why the run failed, then:

- **Nothing to fix** (the machine, the queue): run it again. `lab run <experiment> -- <command>`.
- **The apparatus needs a fix** (a bug in `plan/`, a setting, the serving): fix it, then
  `lab run <experiment> --changed "<what changed since the last run, and why>" -- <command>`. Write
  that sentence for the operator: it is shown beside the run on the experiment's page.
- **What it demands has to change** (the comparison, an arm, the cases, a bar): that is a new
  experiment. The test is whether those can stay word for word as they are locked.

Never read a failed run's partial numbers to decide what to fix. Once one run has finished, the
experiment takes no more, and `plan/` stays as that run ran it.

## When the experiment itself has to change

What an experiment demands never changes once locked. `lab new experiment <question> "<title>"
--replaces <old> --because "<why>"` copies the old card and plan for you to change; the old one
stays, folded under the new with that sentence. Write the reason for the operator: what was wrong
with what the old one asked, in plain words. The same holds when a results review fails, and when
you want to score the part of a failed run that did finish.

## A reading

Before a run that costs something, read what the lab already has. `lab new reading <question>
"<title>"`. A reading looks at sealed runs, traces or the benchmark's own definitions and sets no bar
in advance.

1. Fill its description and **Looks at**: what exactly, how many, and where it is.
2. Read it. Give every case a cause or a class; do not stop at the first pattern.
3. Write **Seen** (what you found, as a list, with counts said as counts) and **Suggests** (what
   follows: a fix to build, an experiment with its bars, or a decision).
4. `lab log <reading> result "<what was seen>" "<what it suggests>"`.

A reading confirms nothing. Never name a count from a reading as a result, and never answer a
question on a reading alone: what it suggests is tested by an experiment.

Use one when an experiment ends refuted or unclear and nobody has looked at the cases, and before
any run that would spend a large share of a resource.

## A build

`lab new build <question> "<title>"`. Fill its description (what it is for), **How it works** (the
mechanism in plain words, as a short list when it has parts, so the operator can picture it without
reading the code) and **Works when**. Build it in the code
repository, tests first. When it works, put `commits:` and `tests:` on the card and
`lab log <build> agent "Built <what>."`.

## When all experiments of a question are done

Decide whether they answer it. `lab answer <question> yes|no "<what the answer rests on>"`, and bring
**So far** up to date. If they do not answer it, add the next experiment. An answer usually changes
what should come next: open a decision.

## When something is in the way

- **It is yours to decide.** Decide, `lab log <id> agent "<what you decided>" "<why>"`, go on.
- **It is the operator's** (direction or resources). Open a decision, then work on what it does not
  hold.
- **It waits on something outside the lab.** Put `waiting_on: <what>` on the card, log a `stuck`
  line, and remove both when it clears.
- **It will not be done.** Put `dropped: <why>` on the card and log it.
- **A run's process died.** `lab runs close <run> "<why>"`. It stops whatever the run left going and
  reads the run's `used.json`. If the run used a metered resource and wrote none, say what it used:
  `--used <resource>=<amount>`.
- **A run started and its folder is gone for good** (the machine was deleted with it). `lab runs lost
  <run> "<why>"`, with `--used <resource>=<amount>` for what it spent, then commit. It counts as a
  failed run, and another may follow.
- **A metered resource was used outside a run** (a machine woken when nothing ran). Add a line under
  that resource's `other_use` in `resources.toml`: `{date = "<date>", amount = <n>, what = "<what>"}`.
  Rows there are only added, never changed.

## Rules

- Never review your own plan or your own results.
- Never write a number that is not a reviewed result, anywhere.
- Never write that the operator decided something outside a decision recorded with `lab decide` (the
  lab-talk skill).
- Open `plan/` and `runs/` only for the experiment you are working on.
- A term an outsider would not know goes in `GLOSSARY.md`, once, and is used the same way everywhere.

## Before you stop

`lab check` passes, everything is committed (`lab now` lists no lock or list of runs as not
committed), and `lab now` says truthfully what is next. If you stop in the middle of a card,
leave a `stuck` line that says where it stands, so the front page does not go on saying you are on it.
