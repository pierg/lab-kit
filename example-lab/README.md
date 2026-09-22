# Sorting crossover — an example lab

**Below how much disorder does insertion sort need fewer comparisons than merge sort?**

**Status: LIVE** · synthetic, complete · record: [`record/findings.md`](record/findings.md) · state: [`ops/STATE.md`](ops/STATE.md)

This is lab-kit's example lab: a toy question with a real, deterministic apparatus, recorded on the ladder the way a research lab would record a hard one. It is a fixture (lab-kit's end-to-end test runs against it), a demo (its pages are published as lab-kit's example site), and documentation (every file is the shape a real lab's file takes). Nothing in it is anyone's research; the numbers are comparison counts from two twenty-line sorting routines.

## The apparatus

Each experiment is a seeded Python script under `experiments/<slug>/bin/` that writes its measurements to `out/`. The scripts count comparisons, not seconds, so every number re-derives exactly on any machine. A pre-registration (`PROBE.md`) fixed the question, the arms, the metric, a kill rule and blind predictions before the script ran; after the lock it is frozen.

## What is established

Every number below cites a row in [`record/findings.md`](record/findings.md), which carries each row's origin anchor and the command that reproduces it. What may be *said* about them is [`record/claims.md`](record/claims.md).

- With 1% of a 1000-element array displaced, insertion sort makes fewer comparisons than merge sort in 18 of 20 seeds (F-1).
- By 2% displaced the advantage is gone: 4 of 20 seeds, and none from 5% up (F-2).
- On small random arrays insertion sort never needs fewer comparisons on average, at any size from 8 to 64 — the small-size line's kill rule fired (F-3).

## Read in this order

1. This file — the question and the apparatus.
2. [`QUESTIONS.md`](QUESTIONS.md) — what was asked, each with its kill criterion.
3. [`record/findings.md`](record/findings.md) — every citable number.
4. [`record/claims.md`](record/claims.md) — what may be said.
5. [`record/logbook/lab.md`](record/logbook/lab.md) — the decisions and the turns.
6. [`CLAUDE.md`](CLAUDE.md) — the operating contract.

## Run it

```bash
make example   # from lab-kit's root: install both kits here and run the gate (strict)
make docs      # then, here: the pages on port 5189
```
