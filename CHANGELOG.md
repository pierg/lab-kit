# Changelog

## 0.2.0

- Standing budgets. The operator can grant money once for many missions: `ops/budgets/<name>.yaml` lists grants, each with an amount and who granted it and when. A mission names the budget it draws on in `budget:`. `lab-mission-approved` checks that what the missions under a budget commit (an active mission's cap, or its spend when that is more; a concluded mission's spend) fits inside its grants; `lab-append-only` keeps grants append-only and the unit fixed. `lab-kit status` shows each budget's granted, committed and left amounts.
- The method (DISCIPLINE §13, §14) and the plan-mission and run-mission skills: under a standing budget the commander may approve a mission that fits inside it and needs nothing that stays the operator's, decide the stops its own plan names and set mission caps inside the budget, recording each call in the mission log and reporting it afterwards. New money, credentials, publishing outside the lab and frozen surfaces stay the operator's.

## 0.1.0

The first release.

- The method: `DISCIPLINE.md` and `LADDER.md`, copied into each lab's `.lab/method/`.
- Five skills, set-up-lab, plan-mission, run-mission, experiment and review, and four agent roles, scout, runner, reviewer and reporter. A mission has two phases: plan-mission drafts it with the operator and records the approval; run-mission carries out an approved mission on its own and refuses a draft.
- The `lab-kit` command: `init`, `check`, `experiment`, `lock`, `run`, `runs`, `score`, `rederive`, `freeze`, `status` and `version`.
- The lab gate: `folio check`, then seventeen lab checks, in one report. `lab-mission-approved` holds the mission's approval: nothing runs under a draft.
- An example lab, `examples/monte-carlo-lab`, that passes the gate: does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)?
- Built on folio 0.1.0 and its lab pack.
