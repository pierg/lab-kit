# Changelog

## 1.2.0

The order of the work can be agreed with the operator and recorded by a decision. Before, `lab now` and the
site listed next steps in the order of the tree, and an agreed order lived only as prose in a lab's
`AGENTS.md`, where a new session could miss it. The skills `lab-work` and `lab-talk` changed: run `lab init` in
a lab after upgrading, or `lab check` reports that they differ from the installed kit.

- A decision card may carry `order: [<ids>]`: goals, questions and steps, first to last. Once the decision is
  settled, "Yours next" and "Not yours to move yet" in `lab now`, and Next and the idle line on the site's Now
  page, list steps in that order. A step takes its own place if the order names it, else its question's, else
  its goal's; steps sharing a place, and steps not named, keep the tree's order, the unnamed after the named.
  The last settled decision, by number, that carries an `order:` has the say. An open decision orders nothing.
- `lab now` says which decision set the order; `lab show <decision>` and the decision's page list the order.
- `lab check` reports an `order:` that names something other than a goal, a question or a step, or names one
  twice. A settled decision's `order:` is held against the lab's history, like its `about:`.

## 1.1.0

A question can be parked: set aside by a decision, not dropped, and brought back only by another. Before, a
question the lab chose not to pursue now stayed open, with nothing to say it was set aside on purpose, or was
dropped for good. The skills `lab-work` and `lab-talk` changed: run `lab init` in a lab after upgrading, or
`lab check` reports that they differ from the installed kit.

- A decision card may carry `parks: [<question>]` and `unparks: [<question>]`. Each question named is also
  under `about:`. Once the decision is settled, the question is parked; a later settled decision that lists
  it under `unparks:` brings it back. The last settled decision, by number, that names it has the say.
- A parked question leaves Now, the rail and the graph. `lab new` refuses a step under it, and `lab lock` and
  `lab run` refuse its experiments, each naming the decision that parked it.
- `lab now` has a Set aside section: each parked question in one line with the decision that parked it, and a
  count of the dropped questions and the closed goals. The site's front page has the same section, with the
  first sentence of what was decided; a goal's page folds its parked questions; a parked question's page says
  at the top which decision parked it and why; a decision shows what it parks or brings back.
- Steps under a parked or dropped question, or a goal that is not active, no longer show under "Not yours to
  move yet" or as what the idle front page names next.
- `lab check` reports a `parks:` or `unparks:` that names something other than a question, a question not
  under `about:`, and a question both parked and brought back by one decision. What a settled decision parks
  or brings back is held against the lab's history, like its `about:`.

## 1.0.3

A word is now defined in one place, `GLOSSARY.md`. Before, the glossary and the goal's Vocabulary
both said what a word means, and the two could drift. The skills `lab-work` and `lab-set-up` changed:
run `lab init` in a lab after upgrading, or `lab check` reports that they differ from the installed
kit. Change the goal's Vocabulary to names, too: see below.

- A glossary entry may carry two more lines beside `- code:`. `- avoid: gate, filter, policy` lists
  the words not to use for the thing; `- see: entries/kna-gate` (or a page of a library the charter
  names, such as `pier-folio:/content/concepts/lora/`) names a page that explains the concept.
  `lab define` prints both, and the glossary page shows the avoid words in small type and the page as a
  link. The hover on a term stays the definition alone. `lab check` checks a `see` as it checks a
  card's `see:`. It does not flag avoid words used in cards: a word to avoid for one thing is often right
  for another.
- The goal's Vocabulary is a list of names only (`- field`). The goal's page and `lab show` draw
  each with its glossary definition. `lab check` reports a name that is not a glossary term. A goal
  written the old way (`- word: meaning`) still shows the glossary's definition, never the card's, and
  `lab check` reports it: list the name only, and add the term to the glossary if it is missing there.
  An existing lab must change its goal's Vocabulary to names.

## 1.0.2

One defect found while rehearsing a real lab, four follow-ups from 1.0.1, and three larger word
budgets. The skill `lab-work` changed with the budgets: run `lab init` in a lab after upgrading, or
`lab check` reports that the skill differs from the installed kit.

- A step may need a step that sits later in the tree, such as a build under the second question
  that needs a reading under the third. States used to be worked out in the order of the cards, so
  the earlier step never saw that the later one was done: it stayed under "Not yours to move yet",
  waiting on a step that was done, and `lab lock` and `lab run` refused it. Each step's state is now
  worked out after everything it needs, wherever that sits. `lab now`, `lab show`, `lab brief` and
  the site agree, since they read the same states.
- Steps that need each other in a circle were already a problem in `lab check`. Now none of them
  moves until the circle is broken, even when one of them is done, and each says which need leads
  back to it.
- Rows that a committed review passed stay. A reviewed `results.tsv` could be emptied together with
  the card's Found and Means, committed, and later filled with other rows and reviewed again, with
  `lab check` sound at every step. Once a results review that passed is committed with the rows it
  read, those rows are held, whatever the card and the file say later. A draft row committed after
  a review, which that review never read, may still be corrected.
- A step that needs one that is dropped or replaced says so in what it waits on, with what to do:
  remove the need or replace it. A need that names nothing in the lab, or something that is not a
  step, now holds the step in `lab lock` and `lab run`, as `lab check` already reported it.
- A `.pyc` file in `plan/` outside `__pycache__` is refused by `lab lock` and `lab run` and reported
  by `lab check`, as a link is: Python would import it, and the plan's hash does not cover it.
- `lab check` says in a note when the repository is a shallow clone, and fails with `--strict`: the
  history check needs every commit, and CI should fetch all of the history (`fetch-depth: 0`). The
  model also says that the history read is that of the record under the lab's root as it is now,
  so moving the root inside the repository starts again what is held.
- A plan that 1.0.0 locked or ran while a `__pycache__` sat in `plan/` verifies again. 1.0.0 counted
  those files in the plan's hash and 1.0.1 does not, so such a record could never match. When a
  hash of `plan/` does not match and the experiment's lock was made by 1.0.0, the folder is hashed
  once more the way 1.0.0 did before a change is reported. It applies to no other lock, and only
  while the cache files are still there as they were.
- `lab show <experiment>` says of each run how many files it holds, how many at the top of its
  folder and how many under each folder there. It used to list ten files and leave out `work/`, so
  a run whose output was all in `work/` looked nearly empty.
- Three word budgets are larger, because real cards were hitting them and ending in fragments: an
  experiment's Found goes from 130 words to 180 and its Means from 90 to 150, and a question's So
  far from 120 to 180. A budget is a ceiling against sprawl. If a card needs its last words cut
  into fragments to fit, it is saying too much for one slot or the budget is wrong, and full
  sentences win.

## 1.0.1

Three defects found by moving a real repository to 1.0.0, and one message.

- `lab check` reads the history of the lab's own record only: `log.md`, `resources.toml`,
  `decisions/`, and each experiment's lock, runs, results and reviews under `goals/`. It used to
  read every file with one of those names anywhere in the repository, so a repository that once held
  an older layout, since removed, failed for ever with "was committed and is gone".
- A file of the record is known by the numbers in its path. A folder or a decision renamed after a
  reworded title is the same record: the rename is no longer reported as a removal, and what was
  committed under the old name is still held under the new one. A file moved to another number, or
  out of the record's places, is reported as gone.
- The hash of `plan/` leaves out `__pycache__` folders and `*.pyc` files, as it always meant to.
  Importing a script from `plan/` no longer makes `lab check` say the plan changed after the run.
  The hash of a folder that holds neither is what it was, in both formats, so every existing lock,
  run and review still verifies.
- A card's `see:` that names a page of another library is a note, not a problem, when that
  library's folder is not on the machine, as in CI. With `--strict` it is a failure. When the folder
  is there and the page is not, it is still a problem.
- `lab run` says that the resources changed when `uses:` is not what was locked. It used to say the
  demand had changed.

## 1.0.0

A rewrite from first principles. Nothing of 0.6 carries over: a lab kept with 0.6 is not read by 1.0,
and no command converts one. `docs/model.md` is the contract, and its section 8 sets the old model
beside the new.

What a lab is

- One tree. A goal holds questions. A question holds its steps, of three kinds: an experiment (a
  comparison with its bars set in advance), a build (something an experiment needs that has to be
  made first) and a reading (a look at what already exists, which suggests and never confirms). An
  experiment holds its runs and its results. Every id spells the path: `G1.Q2.3`, and a result is
  `G1.Q2.3:attack-success`.
- Decisions beside the tree. A decision is something discussed with the operator: what was seen, two
  or three options, a recommendation, then what was decided and why, in the lab's words. Every goal
  and question names the decision it came from.
- Cards. Each of these is one small Markdown file: front matter, a description, and named slots with
  word budgets. A card never holds an id, a state or an outcome; all three are worked out from the
  record when asked for. Nothing computed is kept in a lab.
- The files: `lab.toml`, `resources.toml`, `log.md`, `GLOSSARY.md`, `goals/`, `decisions/`, and
  `runs/` outside git. Missions, protocols, attempts, budgets, ledgers and the folio documents that
  held the record are gone.

How a number counts

- write the card, lock, run, result, review. Each step is a command that refuses when the one before
  it is missing.
- An experiment says what it compares, each arm, its cases, and its confirmed-if and refuted-if
  lines, each a sentence and the one result it tests (`attack-success < 0.05`). The outcome
  (confirmed, refuted, unclear) is worked out from those lines and the results, never written.
- The lock holds what the experiment demands: the comparison, the arms, the cases, the lines, what
  each outcome would mean, and the limits. That never changes. A changed demand, a failed results
  review or a partial score is a new experiment that replaces the old one and says why. The lock
  also records `plan/` as it was locked.
- An experiment is run until one run finishes. Each run pins the `plan/` folder it ran (the
  configuration and the code, as files and no links). When `plan/` is not what the run before ran,
  or for the first run what was locked, the run says what changed and why: `lab run --changed`.
  The first run that finishes is the only source of results, nothing more runs under that
  experiment, and its `plan/` stays as it ran.
- A run is detached, sealed when its command exits (every file's hash, and one over the record) and
  moved into the store. A trial run comes before the lock and never gives a result.
- Every run is listed in `runs.tsv`, in git beside the lock: a row when it starts, a row with its
  seal when it ends. The store is outside git, so this list is what says a run existed: a run
  removed from the store, or a record rewritten, fails `lab check`, and a clone without the store
  still knows what ran. A run that started and whose folder is gone for good is declared lost,
  with the reason: `lab runs lost`.
- What git holds is tamper-evident from the commit that first holds it, not before: the lock is
  committed when it is made and a run's row when it starts. `lab now` and `lab check` say what is
  not committed yet.
- A result is a row in `results.tsv`: a name, a plain label, a value, how it reads, what it is
  compared with, and the command that prints it again from the sealed run. `lab check` runs every
  command again. A card names a result (`{attack-success}`) and never types its number.
- One review, after the results, by a session that did not do the work. A second, of the plan, only
  before a run that uses a metered resource. A failed results review is final for that experiment.

Who decides

- The operator decides direction (the goals and the questions) and resources, in a discussion
  recorded as a decision, not by approving requests. What a decision settles needs no further yes.
  The agent decides everything else and records each choice in the log. A settled decision is
  never reworded. A question is answered with `lab answer`, on a finished experiment.
- Resources are set once for the lab in `resources.toml`: what each is, where its key is kept, for a
  metered one its unit, grant and amount for one run, and its rules as plain sentences. `lab run`
  refuses a run that would pass the amounts; an experiment may carry an override, which is a
  resource and a cap. A metered resource names the settled decision that set its amounts (`from`),
  which lists it under `about:`, and an amount changes only together with it. A resource is never
  removed, only retired, and use outside a run is a list that only grows.

The command, the method and the site

- One command, `lab` (`lab-kit` still starts it), with fifteen commands: `now`, `show`, `brief`,
  `since` and `define` to look; `new`, `log`, `decide` and `answer` to write; `lock`, `run`, `runs`,
  `review` and `check` for evidence; `init` once.
- One log, `log.md`, with five kinds of line: a decision recorded, a choice of the agent's, a
  result, something stuck, and what the agent is starting on now (`doing`). The `doing` line is how
  the operator sees that the lab is alive without asking.
- `lab check` holds what can be held mechanically: ids and links, card budgets and front matter,
  a test on every line, unchanged locks, listed and sealed runs, results that re-derive and were
  reviewed, use inside the resources' amounts, a decision behind every goal, question and amount,
  the installed method and skills, and a history that only grows. It runs the commands in
  `results.tsv`, so it is for a lab you trust. `--strict` fails when history or the store could not
  be checked, which is what CI wants.
- A lab that is not written as the model says (a mistyped folder, a list written as one value, a
  file that is not text) is reported by `lab check`, and stops no command and no page. Commands
  validate everything before they write, and one writes at a time.
- The method is seven rules in one file, `method/METHOD.md`. Four skills (lab-set-up, lab-work,
  lab-review, lab-talk) and one role (the reviewer). `lab init` installs them into a lab.
- The site is drawn by `lab_kit.site` inside folio, from the record, at each request. It needs
  `folio-kb` 0.5.0 or later, as the optional extra `lab-kit-cli[site]`. The command itself depends
  only on `pyyaml` (and `tomli` on Python 3.10), and needs Python 3.10 or later.

## 0.6.4

- `lab-append-only` accepts a recorded correction. `.lab/corrections.tsv` lists `path<TAB>commit<TAB>reason` for a commit that edited a mission log, a budget or a lock record in place and was later put right. That commit's version is left out of the file's history, so the versions before and after it must still show the file only growing, and the file's current version is never a listed one. The list is committed, so every waiver keeps its reason on the record.
- `lab-roster-frozen` compares a run's `config` with its protocol's pinned configuration as the run records it, through JSON. YAML reads a key such as `1:` as an integer and `run.json` holds it as the string `"1"`, so a run that used exactly its pinned configuration was reported as differing.

## 0.6.3

- A mission runs to its conclusion with no further input from the operator. The approval launches it: plan-mission hands it to run-mission at once, with no separate "go". A running mission never waits for an answer. A few lines it never crosses (new money, a credential, publishing outside the lab, a change to a frozen surface, anything irreversible outside git) unless its approved plan names the exact step; work that reaches one is recorded as blocked, and the mission carries on and concludes with it open for the next mission. plan-mission settles those lines in the plan instead of naming points where the run comes back to the operator.
- The commander settles what used to go back to the operator mid-mission: a reviewer disagreement (on the evidence, with a second reviewer), a protocol that must change after its lock (a new protocol), and a correction or retraction of a recorded result (a new record through the review skill, reported afterwards). Reports say what was decided, never ask. The reporter leaves pushing to the commander, and the reviewer's verdict no longer escalates past the commander. DISCIPLINE §8 and §14 and the spec say the same.

## 0.6.2

- The operator's words authorize; they are not the text of the record. The plan-mission skill writes a mission's objective in the lab's own words, as what it will establish inside a clear bound, and the operator approves that text; a vague prompt is interpreted, never pasted. The operator's sentence of approval is kept once, in one log line with its time. The run-mission skill keeps decisions in the log in the lab's words, never quoting the message that prompted them. DISCIPLINE §14 and the spec say the same. Missions already written are left as they are.

## 0.6.1

- `lab-kit migrate` rewrites a run's `config` with the same names it rewrites in its protocol's pinned configuration, so `lab-roster-frozen` holds after the move.
- The plan-mission skill points `ops/STATE.md` at `missions/`.

## 0.6.0

- One folder per run, outside git. A run is `runs/<experiment>/<YY-MM-DD-HHMM>-r_<4 characters>/` and holds everything it produced. lab-kit writes only `run.json` and `run.log` there; the rest is the experiment's own. `LAB_RUN` names the folder. `LAB_OUT`, `LAB_WORK` and `LAB_RUN_DIR` still work for one release.
- The seal. When the command exits, `run.json` records every file's sha256 in `files`, and one hash over the whole record in `seal`. `MANIFEST.sha256`, `work.sha256` and `store.json` are gone. `lab-evidence-sealed` checks a run's folder and its record against the seal.
- The store holds the runs. With `store:`, `runs/` is a committed link to `<store>/runs`. A run is written on local disk in `.lab/running/`, then moves into the store when it ends: copied, verified against its seal, renamed into place, made read-only, and only then deleted locally. `lab-kit publish --pending` retries a failed move, `lab-kit fetch` copies a run into `.lab/fetched/` on a machine without the store, and `lab-kit verify` checks a run against its seal. Where `runs/` does not resolve, as in CI, the gate skips the checks that read runs and says so once. `lab-work-stored` becomes `lab-run-stored`.
- Dated ids. Missions are `missions/<YY-MM-DD>-m_<slug>.md` (they were in `ops/missions/`), and experiments are `experiments/<YY-MM-DD>-e_<slug>/`. A protocol keeps its slug.
- `lab-kit migrate [--apply]` moves a lab from the 0.5.0 layout. It takes each experiment's date from its lock and each run's from its start. Each run's `out/`, `work/` and `run.log` go into one sealed folder in `runs/`. Every old path and id in git-tracked text is rewritten, and the lock hashes are taken again where a protocol's text changed with it. The rewritten documents are listed in the library's `baseline.sha256`, folio 0.3.6's `baseline`, so their permanence holds from the rewrite on, and every old name is kept in `.lab/migration.tsv`. Run it again after old runs land from machines on an older lab-kit.
- Run records are no longer append-only lab files in git: the seal holds them.

## 0.5.0

- lab-kit no longer runs a lab's code to check it. The `lab-selftest` check is gone, and with it the `tools:` key in `lab.yaml`: a lab that still has the key gets an error saying to delete it. lab-kit checks the record; the lab tests its code in its own test suite, which its gate runs beside `lab-kit check`.
- The method (DISCIPLINE §7) and the experiment and review skills say so: an experiment's command calls the lab's own tested code, `bin/` holds only what is particular to one experiment and may be empty, and a fold is tested on a planted case in the lab's suite. The lock still hashes `bin/` and records the commit, which says which version of the lab's code a run used.
- Locks and run records are unchanged.

## 0.4.0

- The run store. `store:` in `lab.yaml` names one shared filesystem, such as `/labs/<lab>`, where every finished run's raw output goes. When a run ends, `lab-kit run` publishes `work/` and `run.log` to the store at the run folder's own path: a copy into `.incoming/`, checked against `work.sha256` (nothing missing, extra or changed), renamed into place, made read-only. It then writes `store.json` beside `run.json` and deletes the local copy. A run in the store is never overwritten. A failed publish is noted in `run.log`, keeps the local copy and never changes the run's exit code.
- `lab-kit publish <slug>/<run id>... | --pending [--keep]`, `lab-kit fetch <slug>/<run id>` and `lab-kit verify <slug>/<run id>`. A machine that does not mount the store sets `LAB_STORE_HOST` to one that does (rsync over ssh, `sha256sum` there).
- `lab-work-stored` (warning): with a store set, every ended run with a `work.sha256` has a `store.json`.
- The experiment skill says to commit `store.json` with the run, and never to mount the store where the system under test runs.
- A lab without `store:` works as before.

## 0.3.0

- The lock covers the instrument. `lab-kit lock` records, beside the protocol's hash, `instrument` (one sha256 over the files in the experiment's `bin/`, sorted by path, each fed as its path and its bytes, `__pycache__` left out), `commit` (the git head) and `lab-kit` (the version). `lab-lock-intact` fails when `bin/` no longer hashes to `instrument`, and `lab-kit run` refuses to start on such a lock, as it already did for a changed protocol.
- Records name their commit. `lab-kit run` writes `commit` and `lab-kit` into `run.json` when it starts.
- Raw output is sealed. When the command exits, `lab-kit run` writes `work.sha256` beside `MANIFEST.sha256`, one line per file under `work/`, when that folder exists. `work/` stays out of git; its hashes go in, so a copy kept elsewhere can be verified.
- A lock or a run record without the new fields predates them and passes: records are never edited. The example lab's records are unchanged and are that test.
- The experiment skill says to commit `bin/` before the lock and to commit `work.sha256` with the run.

## 0.2.0

- Standing budgets. The operator can grant money once for many missions: `ops/budgets/<name>.yaml` lists grants, each with an amount and who granted it and when. A mission names the budget it draws on in `budget:`. `lab-mission-approved` checks that what the missions under a budget commit (an active mission's cap, or its spend when that is more; a concluded mission's spend) fits inside its grants; `lab-append-only` keeps grants append-only and the unit fixed. `lab-kit status` shows each budget's granted, committed and left amounts.
- A run record committed while its run was still going may be committed again once the run ends. `lab-append-only` accepts a later version of a `run.json` that differs from its first committed one only by `ended`, `exit` and `spent` filled in, each once; any other change, a closing field changed after it was set, and a deleted run record still fail.
- The method (DISCIPLINE §13, §14) and the plan-mission and run-mission skills: under a standing budget the commander may approve a mission that fits inside it and needs nothing that stays the operator's, decide the stops its own plan names and set mission caps inside the budget, recording each call in the mission log and reporting it afterwards. New money, credentials, publishing outside the lab and frozen surfaces stay the operator's.

## 0.1.0

The first release.

- The method: `DISCIPLINE.md` and `LADDER.md`, copied into each lab's `.lab/method/`.
- Five skills, set-up-lab, plan-mission, run-mission, experiment and review, and four agent roles, scout, runner, reviewer and reporter. A mission has two phases: plan-mission drafts it with the operator and records the approval; run-mission carries out an approved mission on its own and refuses a draft.
- The `lab-kit` command: `init`, `check`, `experiment`, `lock`, `run`, `runs`, `score`, `rederive`, `freeze`, `status` and `version`.
- The lab gate: `folio check`, then seventeen lab checks, in one report. `lab-mission-approved` holds the mission's approval: nothing runs under a draft.
- An example lab, `examples/monte-carlo-lab`, that passes the gate: does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)?
- Built on folio 0.1.0 and its lab pack.
