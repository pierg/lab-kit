# AGENTS.md — operating guide for agents in the example lab — LIVE

**The question this lab exists to answer:** below how much disorder does insertion sort need fewer comparisons than merge sort?

It is lab-kit's example: small enough to read in an afternoon, recorded exactly as a real lab records. Its answer is settled (F-1, F-2) and one line of it was killed (F-3); new work here is a demonstration, never a result about sorting.

## Read in this order

1. `README.md` — the question, the apparatus, the state.
2. `ops/STATE.md` — what is true right now.
3. `record/findings.md` — every citable number, its anchor, and how to re-derive it.
4. `record/claims.md` — what may be said, at what strength.
5. `record/logbook/lab.md` — the decisions and the turns.

## The shared discipline

Read `kit/DISCIPLINE.md` now. Read `kit/LADDER.md` now.

`DISCIPLINE.md` is the operating contract every lab inherits: append-only records, two git lanes, pre-register before you measure, every number re-derives, fail loud, frozen surfaces, the review gate. `LADDER.md` is where each kind of fact lives and how it is promoted.

## Frozen surfaces — do not touch

- A locked `experiments/*/PROBE.md` and everything under `experiments/*/out/`.
- `kit/` — vendored; change it upstream and re-sync, never edit in place.

## The gate

```bash
make check
```

The content gate (`ckit check`), the ladder lint in **strict** mode, and `kit-verify`. Seconds, no network.

## Skills

The body of a kit skill is `kit/skills/<name>/`. `.agents/skills/<name>` links to it. `.claude/skills` links to `.agents/skills`.

`/mission` · `/experiment` · `/review` · `/present` · `/address`.
