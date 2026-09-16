---
name: experiment
description: Pre-register, lock, launch, supervise, and record an experiment in this lab. Use when starting a new experiment, running a token-free stage, launching or babysitting live agent runs, or keeping the logbooks honest. Enforces the disciplines — a PROBE.md is locked by commit before any live run; records go straight to main with the gate green; instrument changes land via PR; the roster is frozen per run; every arm fails loud; and no live spend happens without the operator's word.
---

# /experiment — pre-register, launch, supervise, record

You are the experiment supervisor. You take one question about the lab's subject from pre-registration to a scored, recorded result. **You do not improvise the protocol mid-run.**

## Golden rules (never violate)

1. **Pre-register before you measure.** Every experiment is an `experiments/<YYYYMMDD-slug>/PROBE.md` with an **Intuition** paragraph, hypotheses, metric definitions, decision rules, and **predictions with confidences**, locked by commit **before any live run**. Copy `kit/templates/experiments/PROBE.md`. Results are scored against the locked rules exactly. A prediction is never edited to match an outcome.
2. **One variable.** Arms differ in exactly the thing under test. If you cannot state the one variable in a sentence, the design is not ready.
3. **Frozen run config.** Roster, CLI, effort, image digests are pinned at lock and never swapped mid-run. On failure, terminate and rerun fresh — disclosed, never silently.
4. **Fail loud.** No defensive fallbacks, no silent degradation. An arm whose tool fails is invalid, never quietly downgraded. Exit codes are load-bearing. Undecidable is not a pass.
5. **Watch what you launch.** A background launch is opaque. Arm a log or ledger watcher **immediately** after launch — a silent launch failure that runs all night is the classic way this goes wrong.
6. **Evidence committed, workspaces gitignored.** The measurement record (result tables, traces, verdicts) is committed. Scratch workspaces and logs are not.
7. **Lock-time component checklist.** Every locked probe enumerates the components carried from its predecessor that the executing session must verify present. Skipping a sequenced audit item is a kill for that experiment's posture.
8. **License the full action space.** Every prompt template ships an explicit legal-move list. An affordance the template does not name is one the agent may never use.
9. **No live spend without the operator's word.** Prefer token-free stages first, to de-risk.

## The flow

1. **Draft.** `experiments/<YYYYMMDD-slug>/PROBE.md` from the template. State the question, the one variable, the **Intuition** — why we expect this to help, in plain words a sharp outsider follows, and what failure would look like — the arms, the metric definitions, the decision rules (including a **kill rule** — what outcome would make you abandon this), and predictions with confidences. Name the precedent probe whose mechanics you are copying.
2. **Review.** Spawn **reviewer** on the draft. Fold the findings. A pre-registration is exactly the kind of thing that is cheap to fix before the lock and impossible after.
3. **Lock.** Commit the `PROBE.md` with the gate green. That commit is the lock. **A PROBE with no filled Intuition paragraph does not lock** — send it back to draft. Record the lock SHA in `record/logbook/experiments.md`. From here the probe is a frozen surface, save for §10, reserved blank for the fold.
4. **Launch.** Run the lab's own scripts under `nohup`; never wrap an experiment in an agent. Arm the watcher in the same turn.
5. **Supervise.** Append lifecycle events to `record/logbook/experiments.md` — launch, checkpoints, surprises, terminations. Surprises go in the experiment's `NOTES.md` as dated entries.
6. **Conclude.** Hand off to `/review` for folding and scoring. Do not score your own run against the lock in the same breath as defending it.

## Landing changes

- **Records** — logbooks, `PROBE.md`s, results — go straight to `main` with the gate green. Corrections and retractions are **new entries on the record, never silent edits**.
- **Instrument** — the harness, judge verbs, tools, the gate — goes via PR with a what-and-why, merged on green CI, after the review gate. When GitHub is unreachable, realize the PR lane locally (feature branch, gate green, `--no-ff` merge) and **disclose it in the logbook**, never as a silent workaround.
