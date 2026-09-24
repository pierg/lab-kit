# AGENTS.md — lab-kit

This file is the only copy of the operating rules for this checkout. `CLAUDE.md` is the one line `@AGENTS.md`.

## Read

- `README.md` — what a lab is and how `install.sh` vendors this layer.
- `DISCIPLINE.md` — the operating contract every lab inherits. Read it now.
- `LADDER.md` — where each kind of fact lives. Read it now.
- `skills/` — `/mission`, `/experiment`, `/review`. `agents/` — scout, reviewer, runner, reporter.

## The gate

```bash
make check
```

Selftests, the example lab's gate, and an install into a fresh lab and a copy of the example.

## Skills

The body of a skill in this checkout is `skills/<name>/`. `.agents/skills/<name>` is a relative symlink to it. `.claude/skills` is a relative symlink to `../.agents/skills`.

## Frozen surfaces

A lab's vendored `kit/` is updated by `install.sh` or `make kit-sync`, not by hand.
