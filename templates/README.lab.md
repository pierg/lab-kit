# <lab-name>

**<The question this lab exists to answer, in one sentence.>**

**Status: LIVE** · <phase in three words> · record: [`record/findings.md`](record/findings.md) · state: [`ops/STATE.md`](ops/STATE.md)

<Two or three paragraphs: why the question is open, what makes it answerable *here* specifically, and what the deliverable is. Write it for someone who has never seen this repo and does not know the field. If you cannot say why the question is open without naming another repo, the question is not yet this lab's own.>

## The apparatus

<What the lab measures with, and why its verdicts can be trusted. Name the frozen surfaces and what makes them frozen.>

## What is established

Every number below cites a row in [`record/findings.md`](record/findings.md), which carries each row's origin anchor and the command that reproduces it. What may be *said* about them, and at what strength, is [`record/claims.md`](record/claims.md).

- <headline finding> (F-n)
- <what did not work, at the same length> (F-n)

## Read in this order

1. This file — the question and the apparatus.
2. [`QUESTIONS.md`](QUESTIONS.md) — what is open, ranked, each with its kill criterion.
3. [`record/findings.md`](record/findings.md) — every citable number.
4. [`record/claims.md`](record/claims.md) — what may be said.
5. [`record/logbook/lab.md`](record/logbook/lab.md) — what has already bitten. Read before trusting any surface.
6. [`CLAUDE.md`](CLAUDE.md) — the operating contract, for anyone about to commit.

## Run it

```bash
make check     # the gate
make serve     # this lab's pages, on its own port
```
