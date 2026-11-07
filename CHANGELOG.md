# Changelog

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
