---
title: Test how the Monte Carlo error of pi scales with the sample size
status: concluded
opened: 2026-10-04
rests_on: [Q-1, lab]
cap: 0
approved: "The operator, 2026-10-04: token-free only, no stage spends."
---

## Objective

"Find out whether the error of our Monte Carlo estimate of pi falls as one over the square root of the sample size, and write it up."

## Workers

- runner: launches the run and folds it.
- reviewer: reviews the draft protocol, then the score.
- reporter: updates the front door.

## Milestones

- The protocol is locked: `experiments/pi-error-scaling/lock.json` exists and `lab-kit check` passes.
- The run is finished: `lab-kit runs` shows it finished, its evidence committed.
- The results are recorded and reported: Q-1 is revised and a report is live.

## Escalation

- Any spend: the cap is zero.
- A change to `substrate/`, a frozen surface.

## Conclusion

Landed: the protocol locked, one finished run, R-2 (superseding R-1), C-1 and the report. Not landed: nothing. Spend: none, against a cap of zero. Open: the error at each size against theory, with more seeds.

## Log

- 2026-10-04 Opened, for Q-1. Next: draft review of the pi-error-scaling protocol.
- 2026-10-04 Draft review of pi-error-scaling: no defect found; safe to lock. Locked.
- 2026-10-04 Run 20261004-231629 launched and finished, exit 0. Evidence committed.
- 2026-10-04 Reviewer pass on the pi-error-scaling score: pass. It re-derived every scored value from the run's estimates and found no defect. P2 and P4 missed, and are scored as misses.
- 2026-10-04 R-1 fitted the slope to the mean absolute error; the protocol names the RMS error. R-2 supersedes it, after the reviewer confirmed the RMS slope re-derives.
- 2026-10-04 Concluded. Q-1 answered; the reporter updated the front door.
