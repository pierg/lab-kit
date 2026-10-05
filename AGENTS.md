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
