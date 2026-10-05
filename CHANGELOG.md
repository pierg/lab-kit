# Changelog

## 0.1.0

The first release.

- The method: `DISCIPLINE.md` and `LADDER.md`, copied into each lab's `.lab/method/`.
- Five skills, set-up-lab, plan-mission, run-mission, experiment and review, and four agent roles, scout, runner, reviewer and reporter. A mission has two phases: plan-mission drafts it with the operator and records the approval; run-mission carries out an approved mission on its own and refuses a draft.
- The `lab-kit` command: `init`, `check`, `experiment`, `lock`, `run`, `runs`, `score`, `rederive`, `freeze`, `status` and `version`.
- The lab gate: `folio check`, then seventeen lab checks, in one report. `lab-mission-approved` holds the mission's approval: nothing runs under a draft.
- An example lab, `examples/monte-carlo-lab`, that passes the gate: does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)?
- Built on folio 0.1.0 and its lab pack.
