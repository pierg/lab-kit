# AGENTS.md: lab-kit

This file is the only copy of the operating rules for this checkout. `CLAUDE.md` is the one line `@AGENTS.md`.

## Read

- `README.md`: what lab-kit is.
- `docs/model.md`: the contract. When code, a skill or the method disagrees with it, it wins.
- `method/METHOD.md`: the rules every lab keeps.
- `skills/`: lab-set-up, lab-work, lab-review, lab-talk. `agents/`: the reviewer.
- `src/lab_kit/`: the `lab` command. `record.py` reads a lab and works out every state, `views.py` shows it to the agent, `site.py` draws it for the operator inside folio, `write.py` and `runs.py` change it, `checks.py` checks it.

## The gate

```bash
python -m pytest -q
```

The tests build a small lab with the command itself and take it from a question to a reviewed result.

## Rules

- The model wins. Change `docs/model.md` first, then the code, the method and the skills, in the same change.
- A rule a command holds is in `docs/model.md`, in the code and in a test together, with a case that it refuses.
- A command validates before it writes, and says what it wrote. No command writes a computed view into a lab.
- Never `git add -A`. Add the files you touched.

<!-- ops:lanes:start (generated from the owner's central rules; change them there, not here) -->
## How changes reach main

`main` is the only source of truth and is always clean: every commit on it passes the gate below.
Every change goes through a pull request; `main` accepts nothing else.

1. Branch from the latest `origin/main` in a separate worktree, named after the task, for example
   `fix-login`.
2. Push early and open a draft pull request.
3. When the work is done and the gate passes, squash-merge it with a clear title and description,
   then delete the branch and the worktree.

**Gate:** `python -m pytest -q`, then `cd examples/monte-carlo-lab && lab-kit check`.

**Authorship.** Every commit is authored with the repository owner's git identity. No co-author
line, tool or agent name, "generated with" footer or session link appears in a commit message, a
branch name or a pull request. A required check on every pull request enforces it.
<!-- ops:lanes:end -->
