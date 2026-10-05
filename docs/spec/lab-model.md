# The lab-kit model

This is the contract the method, the skills, the agent roles and the `lab-kit` command build on. When one of them disagrees with this file, this file wins and the other is fixed. Read folio's `model.md` first: this file assumes it.

## 1. What lab-kit is

lab-kit runs a research lab worked by coding agents. A lab asks questions, tests them against evidence, and says only what the evidence licenses.

lab-kit owns what the lab does and when a result counts. It brings the method, the operating loop, the agent roles, the lab's files outside the library, and its own gate checks.

lab-kit owns no documents. Every document a lab produces is written through folio: the write skill, or a workflow that folio's run skill follows.

## 2. The split with folio

| folio owns | lab-kit owns |
| --- | --- |
| How a document looks, sounds, links and is checked | Whether a result counts |
| The lab pack: question, protocol, result, claim and report genres | When each of those documents may be written |
| The workflows `record-a-result` and `write-a-report` | The skills set-up-lab, plan-mission, run-mission, experiment and review, which run them |
| The journal and its kinds, the paper, maps, concepts, the front door | The method: `DISCIPLINE.md` and `LADDER.md` |
| The rule that every number on a page cites a result | The rule that every result re-derives from evidence |
| `folio check` | `lab-kit check`, which runs `folio check` first |

lab-kit depends on folio and switches the lab pack on. It adds no genres and no document skills. folio's seven skills stay fixed. lab-kit's five skills sit beside them and call them. Their names never take one of folio's: folio's `set-up` makes a library, lab-kit's `set-up-lab` makes a lab around one.

A file is a **document** when it lives in the library's `content/`. A file is a **lab file** when it lives anywhere else in the lab: evidence, run records, lock records, score files, state and missions. Lab files hold pointers and data, never an argument. An argument goes in a document.

## 3. A lab's layout

A lab is a repository. Its folio library sits at the root or in a folder such as `docs/`. lab-kit's files sit beside it.

```
<lab>/
  AGENTS.md                  the lab's operating guide: its question, frozen surfaces, local rules
  lab.yaml                   lab-kit's settings (below)
  docs/                      the folio library (or the root itself)
    folio.yaml               the charter, with the lab pack on
    content/
      questions/Q-{n}.md     what is open, ranked, with what would settle it
      protocols/{slug}.md    one experiment's plan; draft, then locked (frozen)
      results/R-{n}.md       one measured number, with its evidence and re-derive command; permanent
      claims/C-{n}.md        what may be said, and how strongly
      reports/{slug}/        one experiment's outcome in plain English; frozen once live
      journal/{yyyy}/        the library's one journal: one permanent file per entry, {date}-{slug}.md
      ...                    maps, concepts, the front door, papers
  experiments/{slug}/        one per protocol, same slug
    bin/                     the lab's own scripts for this experiment, each with --selftest
    lock.json                the lock record: protocol id, its sha256 with the status field set aside, the lock time (UTC)
    runs/{run-id}/
      run.json               protocol hash, frozen configuration, mission, start, end, exit code
      out/                   the evidence, committed at the end of the run, never edited
      MANIFEST.sha256        a hash of every file in out/, written when the run ends
      work/  run.log         scratch and log, gitignored
    score.yaml               the review's scorecard against the lock, and the results to record
  ops/
    STATE.md                 what is true now and what is next; a pointer, never a record
    missions/{date}-{slug}.md  one per operator objective; its log is append-only
  .lab/
    method/                  DISCIPLINE.md and LADDER.md, copied by lab-kit, never hand-edited
    frozen.sha256            the hashes of the surfaces lab.yaml declares frozen
  .agents/skills/            folio's seven skills and lab-kit's five
  .agents/agents/            the four agent roles
  .claude/skills, .claude/agents   links to the two folders above, where Claude Code looks
```

`lab.yaml`:

```yaml
lab-kit: 0.1.0               # the version this lab is checked with
library: docs                # where folio.yaml is; "." for the root
front: lab                   # the front door's id: a project document
frozen:                      # surfaces never edited in place
  - substrate/
tools: [tools/fold.py]       # lab-wide scripts; each must pass --selftest
rederive_timeout: 120        # seconds per re-derive command
```

Paths in `lab.yaml`, `run.json`, `score.yaml`, and a result's `evidence` and `rederive` fields, are relative to the lab root. folio resolves a result's paths from the charter's `root`, so a lab whose library is in `docs/` sets `root: ..` in `folio.yaml`. Both tools then read the same path the same way.

`score.yaml` names its `protocol` and the lock's hash (`lock`), and has three parts. `review` holds the independent reviewer's `verdict` (`pass` or `fail`) and `record`, the path of the file where that verdict is recorded, usually the mission file. `scores` holds one entry per prediction and decision rule the lock names, keyed by its id (`P1`, `D1`): a verdict, the value and the evidence it came from. A prediction's verdict is `HIT`, `MISS` or `INDETERMINATE`; a rule's is `FIRED`, `NOT FIRED` or `INDETERMINATE`. `record` holds one entry per number to record, keyed by a short name, with the result's field names: `title`, `protocol`, `number`, `baseline`, `bound`, `evidence`, `rederive`. The review hands one entry to `record-a-result` as `from: experiments/<slug>/score.yaml#<name>`.

`run.json` holds `protocol`, `lock` (the hash the run was checked against), `config` (the pinned configuration, copied from the protocol), `mission`, `spend`, `command`, `started`, `ended`, `exit`, `pid` and `spent`. Times are UTC, to the second. A run's command finds its folders in the environment: `LAB_RUN_DIR`, `LAB_OUT` and `LAB_WORK`. A run that spends writes `out/spend.json` with `{"spent": <number>}`, in the unit of its mission's cap, and `lab-kit run` copies it into `spent` when the command exits.

A mission file starts with YAML front matter: `title`, `status` (`draft`, `active` or `concluded`), `rests_on` (the ids it rests on), `approved` (who approved the mission, and when, with the date as `YYYY-MM-DD`) and `cap` (a number, in the unit its runs report spend; `0` when nothing spends). A mission is `draft` until the operator approves it; `approved` is required from `active` on. Its log is everything under its `## Log` heading; entries are only added at the bottom. `ops/STATE.md` has one line `Active mission: <path>` or `Active mission: none`, and never names a draft.

A mission has two phases, one skill each. **plan-mission** is interactive: the operator states an objective, the agent reads the lab and asks only what it cannot look up (the questions served, the milestones and their observables, the scope, the spend, what is never touched, the stops), writes the file as `draft`, and revises it until the operator approves. It then records `approved`, sets `status: active`, and adds a journal entry of kind `decision`. It never starts work. **run-mission** is autonomous: it refuses a mission that is a draft or records no approval, carries out the rest without asking, and stops only at the stops the mission names and the method's own.

## 4. How a result flows

```
question --> protocol (draft) --> review of the draft --> lock --> run --> evidence
                                                                             |
   journal <-- report <-- claim <-- result R-n <-- reviewer pass <-- score <-+
```

1. **Question.** The write skill adds or revises a question `Q-n`. It is ranked, and it says what would settle it.
2. **Protocol.** The write skill drafts `protocols/{slug}.md`. `lab-kit experiment {slug}` creates `experiments/{slug}/`. The protocol names its question, the intuition, the one variable and its arms, the pinned configuration, the allowed moves, the measures, the decision rules `D1`... with the kill rule marked, and the predictions `P1`... with confidences.
3. **Draft review.** A reviewer reads the draft before the lock. The commander records the verdict in the mission log.
4. **Lock.** The write skill sets the protocol's status to `locked`. The protocol's card lists `locked` in `frozen_in`, so folio's `frozen` check holds it from here: nothing changes but its status field. `lab-kit lock {slug}` writes `lock.json` with the file's hash, taken with the status field set aside, so the one change folio allows (to `abandoned`) does not break it. `folio journal add --title .. --description .. --body .. --kind lock --about {slug}` records it. The commit that holds the protocol, `lock.json`, that journal entry and `.folio/` is the lock; folio's `frozen` check compares with the first commit that set `locked`. From here lab-kit also checks the protocol's bytes.
5. **Run.** `lab-kit run {slug} -- <command>` refuses unless the lock is intact. It writes `run.json`, starts the lab's own command in the background, and logs it. A run under a mission names it with `--mission`, and the mission must be approved and `active`. A run that spends tokens or money also needs a mission that records a cap. Launch, checkpoints and terminations each go in a journal entry of kind `run` about the protocol.
6. **Evidence.** When the command exits, `lab-kit run` writes `MANIFEST.sha256` and the exit code. `out/` is committed once, at the end, in one commit. A run whose tool failed is invalid, and is recorded as invalid.
7. **Score.** The review skill reads the lock first. It folds `out/` with a selftested script. `lab-kit score {slug}` creates `score.yaml` with every prediction and rule id the lock names. The review fills each with a verdict, a value and the evidence it came from, and lists the numbers to record under `record`.
8. **Reviewer pass.** An independent reviewer re-derives the scored numbers and returns a verdict. The commander records it, and `score.yaml` points to it.
9. **Result.** For each number worth citing, folio's run skill follows `record-a-result` with `from: experiments/{slug}/score.yaml#<name>`, and writes `R-n`. Its number, baseline, bound, evidence path, re-derive command and protocol come from that entry; its date is the day it is recorded. A result is permanent and writes no status. folio derives it: `live` until a newer result supersedes it or a retraction names it. A null or a fired kill rule is a result too.
10. **Claim.** If the lab wants to say something, the write skill adds or revises a claim `C-n` citing its results.
11. **Report.** The run skill follows `write-a-report`, which writes the report citing its results. Misses sit as prominently as hits. Once the report is `live` it is frozen. A result it cites that changes later shows as a banner on it; nobody edits it.
12. **Journal.** `folio journal add` writes an entry about the protocol and its results: kind `lesson` for what was learned, `kill` when a kill rule fired. The question is revised: its status becomes `answered` or `narrowed`, or its rank moves. Its protocols and results show on it through the generated link panels. The reporter updates the front door.
13. **Gate.** `lab-kit check` passes before anything lands on the main branch.

A result that is not promoted is recorded too: a journal entry about the protocol says which number was left out, and why.

**Corrections.** A result is never edited. A wrong number is corrected by a new result, through `record-a-result`, with `supersedes: R-n`; it meets every check a new result meets. A result that should not have been recorded, with nothing to replace it, is retracted: `folio journal add --title .. --description .. --body "<the reason>" --kind retraction --about R-n`. folio derives the old result's status and shows the banner on it and on every frozen report that cites it. A claim citing it is revised by the write skill.

## 5. The lab gate

`lab-kit check` runs `folio check`, then the checks below. It runs offline, names every problem in one pass, and never changes a file. CI runs the same command. Each check is an error unless marked as a warning.

| Id | What it requires |
| --- | --- |
| `lab-lock-recorded` | Every protocol with status `locked` has a `lock.json` naming it, and every `lock.json` names a protocol whose status is `locked` or `abandoned`. |
| `lab-lock-intact` | A locked protocol's bytes, with its status field set aside, hash to the value in its `lock.json`. Nothing but the status changes after the lock. |
| `lab-run-after-lock` | Every run belongs to a locked experiment, records the lock's hash, and started after the lock date. |
| `lab-roster-frozen` | Every run's configuration in `run.json` equals the `yaml` block under its locked protocol's `## Pinned configuration`. |
| `lab-evidence-sealed` | Every finished run's `out/` matches its `MANIFEST.sha256`. A run with no end and no live process is reported as orphaned (warning). |
| `lab-rederive` | Every result whose derived status is `live` has a `rederive` command that, run from the lab root within the timeout, exits 0 and prints the result's `number` exactly, after trimming whitespace. |
| `lab-result-grounded` | Every result whose derived status is `live` names a locked protocol. Its evidence path is inside a finished run of that experiment. The experiment's score records a reviewer pass. |
| `lab-score-exact` | A `score.yaml` names the lock's hash. Its `scores` list exactly the locked protocol's prediction ids (`P1`...) and decision-rule ids (`D1`...), no more and no fewer. Each has an allowed verdict and an existing evidence path. |
| `lab-ids-resolve` | Every id cited in a lab file (state, missions, lock records, runs, scores) resolves to a document in the library. |
| `lab-frozen-intact` | Every surface listed under `frozen:` matches its hash in `.lab/frozen.sha256`. |
| `lab-selftest` | Every script in `experiments/*/bin/` and under `tools:` passes `--selftest`. |
| `lab-mission-approved` | Every mission file has status `draft`, `active` or `concluded`. An `active` or `concluded` mission records `approved`, naming who and a date. No run names a draft mission, and `ops/STATE.md` names no draft as the active mission. |
| `lab-spend-recorded` | A run marked as spending names a mission that records the operator's approval and a cap, and its recorded spend is within the cap. |
| `lab-append-only` | Lab files only: committed mission log entries, lock records and run records are unchanged in later commits. Journal entries and results are folio's `permanent` check. |
| `lab-method-current` | `.lab/method/`, the five skills and the four roles match the lab-kit version in `lab.yaml`. |
| `lab-state-pointer` | `ops/STATE.md` names an active mission file or "none", stays under 300 words, and cites ids for any number (warning). |
| `lab-scored-reported` | Every scored experiment has a report citing its results, or a journal entry about its protocol saying why not (warning). |

The gate checks that the record is consistent. It does not check that the record is honest. That is the reviewer's job.

lab-kit runs every selftest, re-derive command and run from the lab root with `PYTHONDONTWRITEBYTECODE=1`, so no bytecode lands in a frozen surface. A run counts as ended for `lab-evidence-sealed` whatever its exit code; for `lab-result-grounded` it must have exited 0.

## 6. The `lab-kit` command

Only skills call it, the way an agent calls git. Every command that changes files prints what it changed.

| Command | Does |
| --- | --- |
| `lab-kit init [--library <dir>]` | Writes `lab.yaml`, `ops/`, `experiments/`, `.lab/`, the five skills and the four roles, and links `.claude/skills` to `.agents/skills` and `.claude/agents` to `.agents/agents`. With no `--library`, no `lab.yaml` and no `folio.yaml` at the root, it installs only the method, the skills and the roles, so the set-up-lab skill can be read before the library exists. With `--library`, the folder must hold a `folio.yaml`. In the library it only switches the lab pack on, if set-up has not. It refuses a library whose `root` is not the lab root. Run again in a lab, it restores the method, the skills and the roles to this version's, and sets `lab-kit:` in `lab.yaml` to it. |
| `lab-kit check [--only <id>] [--json]` | The lab gate: `folio check`, then the checks above. `--only` runs one check, and may repeat; `folio` names folio's gate. Exit 0 only when there is no error. |
| `lab-kit experiment <slug>` | Creates `experiments/<slug>/` with `bin/`, `runs/` and the gitignore for scratch. |
| `lab-kit lock <slug>` | Writes `lock.json` for a protocol whose status is `locked` and whose gate is green, hashing the file with its status field set aside. Refuses otherwise. |
| `lab-kit run <slug> [--mission <file>] [--spend] [--wait] -- <command>` | Checks the lock, writes `run.json`, starts the command in the background from the lab root, and writes `MANIFEST.sha256` for `out/` when it exits. With `--mission`, it refuses a mission whose status is not `active` or that records no approval. `--wait` waits for the end, for a short token-free stage. |
| `lab-kit runs [--live]` | Lists runs and their state: running, finished, failed, orphaned. |
| `lab-kit score <slug>` | Creates `score.yaml` from the locked protocol's prediction and rule ids, with empty verdicts. |
| `lab-kit rederive <R-n>` | Runs one result's re-derive command and compares its output with the number. |
| `lab-kit freeze <path>` | Records a frozen surface's hash. Only the operator asks for this. |
| `lab-kit status` | Prints the state, the active mission, live and orphaned runs, and draft and locked protocols. |
| `lab-kit version` | The lab-kit version. |

## 7. What lab-kit does not do

- It does not write documents. folio does, through its skills and workflows.
- It adds no genres, states or journal kinds. The lab pack holds them all, and lab-kit uses its names exactly.
- It does not wrap an experiment in an agent. A run is the lab's own command.
- It does not decide a question. The locked protocol's rules and the reviewer do.
- It does not spend. The operator does, and the mission records it.
