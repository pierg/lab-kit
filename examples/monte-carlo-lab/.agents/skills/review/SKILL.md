---
name: review
description: >-
  Fold a finished experiment's evidence, score it exactly against its locked protocol, gate it
  through an independent reviewer, record what survives as results, claims and a report through
  folio, and propose the next move. Use when an experiment finishes, or when the user says
  "score this", "fold the run", "what did we learn", "record the result", "is this a result",
  or "write it up".
---

# review

You turn a finished experiment's evidence into a scorecard against its lock, then record what survives through folio. You score against the lock, not against hope.

## Start

1. Find the lab: the nearest `lab.yaml`. Read it and the lab's `AGENTS.md`.
2. Read `.lab/method/DISCIPLINE.md` and `.lab/method/LADDER.md`.
3. Find the library named in `lab.yaml` and read its charter. Run `folio genres` and `folio workflows`.
4. Read the cards in hand: `folio genre result`, `folio genre claim`, `folio genre report`, `folio genre journal`.
5. Read the locked protocol first, before any output. Note its hash in `lock.json`.

## Rules

1. Read the lock before the results. Judged, not checked.
2. Re-derive every number from the committed evidence by running the fold. Never take a number from a summary, a message or an earlier document. Checked by `lab-rederive`; the rest is judged.
3. Score exactly what the lock names: every prediction and every rule, no more and no fewer. Checked by `lab-score-exact`.
4. A badly chosen rule is still the rule. Record the flaw as a lesson; never rescore. Judged, not checked.
5. A miss is a result. Nulls, fired kill rules and invalid arms are recorded at the same length as wins. Checked in part by `lab-scored-reported`; the rest is judged.
6. Every fold script has a `--selftest` on a planted case with a known answer. Checked by `lab-selftest`.
7. You score; the reviewer gates. Nothing is recorded as a result before a reviewer pass. Checked by `lab-result-grounded`.
8. Every document goes through folio: results and reports through workflows that folio's run skill follows, the rest through the write skill. Checked by `folio check`.
9. A report is frozen once `live`, and a result is permanent. A new result earns a new report, never a rewrite of an old one. folio shows a banner on the old report when a result it cites is superseded or retracted. Checked by folio's `frozen` and `permanent` checks.
10. Never pool results of different standing in one sentence. Judged, not checked.
11. A wrong result is never edited. It is corrected by a new result with `supersedes: R-n`, or retracted by a journal entry of kind `retraction` about it. folio derives its status. Checked by folio's `permanent` check.

## Steps

1. **Fold.** Run the experiment's fold script over each finished run's `out/`. If none exists, write one in `bin/` with a `--selftest` on a planted case, and land it as an instrument change. Never fold by eye.
2. **Score.** Run `lab-kit score <slug>`. Under `scores`, for every prediction `P1`..., fill HIT, MISS or INDETERMINATE, with the value and the evidence file it came from. For every decision rule `D1`..., say whether it fired, the kill rule included. Run `lab-kit check --only lab-score-exact`.
3. **Gate.** Ask the commander for a reviewer pass, or send one yourself if you are the commander. The reviewer re-derives the scored numbers. Record its verdict where the mission keeps verdicts, and point `score.yaml` to it: `review.verdict` and `review.record`.
4. **Choose what to record.** For each scored number, ask: is this a citable fact? A null counts. Add each one to `score.yaml` under `record`, keyed by a short name. Give it the result's fields: `title`, `protocol`, `number`, `baseline`, `bound`, `evidence` and `rederive`. The `number` is exactly what the re-derive command prints, and the evidence lies inside the run. Name every number you leave out.
5. **Record results.** For each entry under `record`, follow the `record-a-result` workflow through folio's run skill, with `from: experiments/<slug>/score.yaml#<name>`. It asks only for what the entry lacks. Then run `lab-kit rederive <R-n>` for each new result.
6. **License claims.** If the lab wants to say something, revise or add a claim through the write skill. It cites its results and states its strength and what must not be said beside it.
7. **Report.** Follow the `write-a-report` workflow through folio's run skill. Give it the results by id and the map. Add what the record does not already hold: what was run, the scoring by `P` and `D` id, the lesson, and any bound beyond the results'. It reads the question, the intuition and the results' bounds itself. Misses go as prominently as hits.
8. **Journal.** With `folio journal add`, write an entry about the protocol, the results and the report, saying what was learned: kind `lesson`, or `kill` if a kill rule fired. Write a `lesson` entry about the protocol for anything learned about the apparatus. Write one entry naming any number left out, and why. Each entry is a new file; never edit an old one.
9. **Revise the question.** Through the write skill, set its status to `answered` or `narrowed` with an answer citing the results, or change its `rank`. Its protocols and results show on it through folio's generated link panels; never list them by hand. Add any new question the result opened.
10. **Propose.** Tell the commander which questions closed, which opened, and the next moves ranked by information value. Ask the reporter to update the front door.
11. **Gate.** Run `lab-kit check`. Fix what it names.

## Stops

- The evidence does not support any verdict the lock allows. Score INDETERMINATE and say why; do not invent a rule.
- The reviewer disagrees with your score. The commander decides, or the operator.
- A recorded result elsewhere must be corrected or retracted. Put it to the operator before writing the superseding result or the retraction entry.
- A frozen surface or the lock seems wrong. Record the flaw; do not change it.

## Done when

- `score.yaml` scores every prediction and rule in the lock, and points to a reviewer pass.
- Every citable number is a result whose re-derive command reproduces it.
- The report exists, cites its results, and is `live`, so it is frozen.
- Journal entries about the protocol hold the lessons, any fired kill rule, and every number left out.
- The question is revised.
- `lab-kit check` passes.

## Commands

- `lab-kit score <slug>`: the scorecard skeleton from the lock.
- `lab-kit rederive <R-n>`: re-runs one result's command against its number.
- `lab-kit check [--only <id>]`: the lab gate.
- folio's run skill, following `record-a-result`: writes one result through the write skill.
- folio's run skill, following `write-a-report`: writes one report through the write skill.
- `folio cite <id>`: the link markup for an id.
- `folio journal add --title ".." --description ".." --body ".." --kind <kind> --about <id>,..`: writes one journal entry, a new file each time.
