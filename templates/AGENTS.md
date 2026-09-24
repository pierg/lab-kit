# AGENTS.md — operating guide for agents in <lab>

**The question this lab exists to answer:** <one sentence. If you cannot state it in one sentence, the lab is not ready to be a lab.>

<Two or three sentences: why the question is open, what makes it answerable here, what the deliverable is.>

## Read in this order

1. `README.md` — the question, the apparatus, the state.
2. `ops/STATE.md` — what is true right now, and what is next.
3. `record/findings.md` — every citable number, its anchor, and how to re-derive it.
4. `record/claims.md` — what may be said, at what strength.
5. `record/logbook/lab.md` — infra lessons, bugs, corrections, retractions. Read this before you trust any surface; it records what has already bitten.
6. As needed: `record/logbook/{experiments,agenda}.md`, the per-experiment `PROBE.md` files.

## The shared discipline

Read `kit/DISCIPLINE.md` now. Read `kit/LADDER.md` now.

`DISCIPLINE.md` is the operating contract every lab inherits: append-only records, two git lanes, pre-register before you measure, every number re-derives, fail loud, frozen surfaces, the review gate. `LADDER.md` is where each kind of fact lives and how it is promoted.

Everything in those two files binds every lab. What follows is local to this one.

## Frozen surfaces — do not touch

- <the vendored substrate / exam artifact — never reformat or edit>
- <a locked `experiments/*/PROBE.md` and everything under `experiments/*/out/`>
- <pinned image digests, judge-owned paths, load-bearing env prefixes>
- `kit/` — vendored; change it upstream and re-sync, never edit in place.

Work is **additive**. If you believe a frozen surface must change, stop and put the case to the operator; do not edit it silently.

## The gate

```bash
make check
```

<What it runs, how long it takes, and the standing rule that CI runs the identical target so local and CI cannot diverge.>

## Skills

The body of a kit skill is `kit/skills/<name>/`. `.agents/skills/<name>` links to it. `.claude/skills` links to `.agents/skills`. A skill this lab owns is a real directory at `.agents/skills/<name>` with its own `SKILL.md`, and its name is not a kit skill's name.

`/mission` (commander loop) · `/experiment` (pre-register → lock → launch → supervise → record) · `/review` (fold → score → promote → propose) · `/present` (author a page or a paper).
