# AGENTS.md: lab-kit

This file is the only copy of the operating rules for this checkout. `CLAUDE.md` is the one line `@AGENTS.md`.

## Read

- `README.md`: what lab-kit is and how it uses folio.
- `docs/spec/lab-model.md`: the contract. When code, a skill or the method disagrees with it, it wins.
- `method/`: `DISCIPLINE.md` and `LADDER.md`, the operating contract every lab inherits.
- `skills/`: set-up-lab, plan-mission, run-mission, experiment, review. `agents/`: scout, runner, reviewer, reporter.
- `src/lab_kit/`: the `lab-kit` command and the lab checks.
- `examples/monte-carlo-lab/`: a small lab that passes the gate.

## The gate

```bash
python -m pytest -q
(cd examples/monte-carlo-lab && lab-kit check)
```

The tests, then `lab-kit check` on the example lab. CI runs the same two commands.

## Rules

- folio owns documents. lab-kit writes none, adds no genres and no journal kinds, and uses the lab pack's names exactly.
- A check is added to `docs/spec/lab-model.md` §5, the registry in `src/lab_kit/checks/run.py` and a failing test in the same change.
- The example lab's run evidence, lock record and run record are never edited by hand.
- Never `git add -A`. Add the files you touched.

<!-- ops:lanes:start (generated from the owner's central rules; change them there, not here) -->
## How changes reach main

`main` is the only source of truth and is always clean: every commit on it passes the gate below.
Every change goes through a pull request; `main` accepts nothing else.

1. Branch from the latest `origin/main` in a separate worktree, named after the task (its tracker
   issue, for example `pie-142-fix-login`).
2. Push early and open a draft pull request.
3. When the work is done and the gate passes, squash-merge it with a clear title and description,
   then delete the branch and the worktree.

**Gate:** `python -m pytest -q`, then `cd examples/monte-carlo-lab && lab-kit check`.

**Authorship.** Every commit is authored with the repository owner's git identity. No co-author
line, tool or agent name, "generated with" footer or session link appears in a commit message, a
branch name or a pull request. A required check on every pull request enforces it.
<!-- ops:lanes:end -->
