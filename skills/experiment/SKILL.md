---
name: experiment
description: >-
  Take one experiment in a lab from a pre-registered protocol to a finished run: draft the protocol,
  have it reviewed, lock it, launch the lab's own command, watch it, and record what happened.
  Use when the user says "new experiment", "pre-register", "lock the protocol", "launch", "run",
  "start the token-free stage", "babysit the run", or "what happened to the run".
---

# experiment

You take one question from a draft protocol to a finished run with its evidence committed. You never improvise the protocol mid-run.

## Start

1. Find the lab: the nearest `lab.yaml`. Read it and the lab's `AGENTS.md`.
2. Read `.lab/method/DISCIPLINE.md`.
3. Find the library named in `lab.yaml` and read its charter. Run `folio genres` and `folio workflows`.
4. Read the cards for the protocol and journal genres: `folio genre protocol`, `folio genre journal`.
5. Run `lab-kit status`. Read the question this experiment serves.

## Rules

1. Pre-register before you measure. No run starts before the protocol is locked. Checked by `lab-run-after-lock`; `lab-kit run` refuses otherwise.
2. A locked protocol never changes, except its status. Checked by folio's `frozen` check and `lab-lock-intact`.
3. One variable. Arms differ in exactly the thing under test. Judged, not checked.
4. Every protocol has decision rules `D1`... with one marked `(kill)`, and blind predictions `P1`... with confidences. Checked by the protocol genre's `rule_ids` and `prediction_ids`.
5. Every protocol has an intuition in plain words: why it should work, and what failure would look like. Checked by the protocol genre's required parts.
6. The roster is frozen per run. A run uses exactly the protocol's pinned configuration. Checked by `lab-roster-frozen`.
7. Fail loud. An arm whose tool fails is invalid, never downgraded. Undecidable is not a pass. Judged, not checked.
8. Name every move the agent under test may make, under the protocol's allowed moves. A move the list does not name is one it may never use. The section is checked by the protocol genre's required parts; its completeness is judged.
9. No live spend without the operator's word, recorded in a mission with a cap. Checked by `lab-spend-recorded`.
10. Every script in `bin/` has a `--selftest`. Checked by `lab-selftest`.
11. Evidence is committed once, at the end of the run. Scratch and logs stay out of git. Checked by `lab-evidence-sealed`; the rest is judged.
12. Every document goes through the write skill. You never write one by hand. Checked by `folio check`.

## Steps

1. **Draft.** Through the write skill, create the protocol: `folio new protocol <slug>`, then fill it. In the protocol genre's words, it states:
   - `question`: the question's id, and `carries`: the earlier protocol whose mechanics it copies, if any;
   - the hypothesis and the intuition;
   - the one variable and its arms, and what is held fixed;
   - the pinned configuration, budget included, and the allowed moves;
   - the measures, each with its denominator;
   - the decision rules `D1`..., with the kill rule marked `(kill)`;
   - the predictions `P1`..., each with a confidence;
   - what it cannot show.
2. **Make its folder.** Run `lab-kit experiment <slug>`. Put the lab's scripts in `experiments/<slug>/bin/`, each with a `--selftest`. Run `lab-kit check --only lab-selftest`.
3. **Review the draft.** Send a reviewer with fresh context. Fold its points into the draft through the write skill. A protocol is cheap to fix before the lock and impossible to fix after.
4. **Lock.** Through the write skill, set the protocol's status to `locked`. Run `lab-kit lock <slug>`. Record it: `folio journal add --title .. --description .. --body .. --kind lock --about <slug>,<Q-n>`. Run `folio index`, then `lab-kit check`. Commit exactly the protocol, `lock.json`, the `lock` journal entry and `.folio/` together; that commit is the lock. From here folio's `frozen` check and `lab-lock-intact` hold it.
5. **De-risk.** Run the token-free stages first, with `lab-kit run`. Fix the apparatus only before the lock. After it, an apparatus fault ends the run as invalid.
6. **Launch.** Run `lab-kit run <slug> -- <command>`. Add `--spend --mission <file>` for a run that spends. Watch it at once: arm one watcher on its log that fires on the end marker or an error signature. A silent launch failure can waste a whole night.
7. **Supervise.** Write a journal entry of kind `run` about the protocol for each launch, checkpoint, surprise and termination, with `folio journal add`. Keep each entry to what changed. Record a deviation the moment you see it. Commit each entry with `.folio/` after `folio index`; never stage the run's working files.
8. **On failure.** End the run. Start a fresh one with the same configuration. Disclose it in a `run` entry. Never swap a model or a tool mid-run.
9. **Conclude.** When the run ends, `lab-kit run` writes the manifest of `out/`. Commit `out/`, `MANIFEST.sha256` and `run.json` in one commit. Run `lab-kit check`. Hand the experiment to the review skill. Do not score your own run.

## Stops

- The one variable will not fit in a sentence. The design is not ready; say so.
- The protocol must change after the lock. It cannot. Put the case to the operator; a new protocol is the usual answer.
- A run would spend with no recorded approval, or past the cap.
- A frozen surface seems to need a change.

## Done when

- The protocol is locked, and its lock record matches it.
- Every run is finished or recorded as invalid, and none is orphaned.
- Each finished run's evidence is committed and matches its manifest.
- Journal entries about the protocol record the lock, the launch, every surprise and the end.
- `lab-kit check` passes.

## Commands

- `folio new protocol <slug>`: run by the write skill to start a protocol.
- `folio journal add --title ".." --description ".." --body ".." --kind <kind> --about <id>,..`: writes one journal entry, a new file each time.
- `lab-kit experiment <slug>`: the experiment's folder.
- `lab-kit lock <slug>`: the lock record.
- `lab-kit run <slug> [--spend --mission <file>] -- <command>`: a run, checked against the lock, its evidence hashed at the end.
- `lab-kit runs [--live]`: run states.
- `lab-kit check [--only <id>]`: the lab gate.
