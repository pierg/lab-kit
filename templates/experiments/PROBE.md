# <ID> — <one-line question this experiment answers>

**Date:** YYYY-MM-DD · **Status: DRAFT** → set to **LOCKED <sha>** at the lock commit.

> Everything below is written **before** any output exists. After the lock, this file is a frozen surface: corrections go on the record as new commits, never as edits here. A prediction is never edited to match an outcome.

## 0 · Provenance

Precedent probe whose mechanics this copies: `experiments/<slug>/`. What is carried verbatim vs authored here, stated explicitly — never blended.

**Lock-time component checklist.** Components carried from the predecessor that the executing session must verify present before launch:

- [ ] <component — and how to verify it>

## 1 · Question and the one variable

**Question:** <what is genuinely unknown>

**The one variable:** <the single thing that differs between arms. If this takes more than a sentence, the design is not ready.>

**Held fixed:** <everything else — substrate, roster, budget, templates, image digests>

## 2 · Arms

| Arm | The one variable | n | Everything else |
|---|---|---|---|

## 3 · Metric definitions

Each metric defined precisely enough that two people folding the same `out/` tree get the same number. Name the denominator explicitly.

## 4 · Decision rules

- **<Rule>:** if <observable> then <conclusion>.
- **Kill rule:** if <observable> then this arm is abandoned and reported as killed. <A pre-registration without a kill rule cannot produce a publishable null.>

## 5 · Predictions (blind, with confidence)

| # | Prediction | Confidence | Scored |
|---|---|---|---|
| P1 | <what you expect, stated so it can be wrong> | <%> | |

## 6 · Instruments and frozen configuration

Roster, CLI, effort, image digests, budget caps — pinned here, never swapped mid-run. On failure: terminate and rerun fresh, disclosed.

## 7 · Legal action space

The explicit list of moves the agent may make. **An affordance not named here is one the agent may never use.**

## 8 · Budget and launch

Cost estimate, the launch command, and the watcher armed in the same turn.

## 9 · What this experiment cannot show

<Stated in advance, so it is not discovered defensively afterwards.>
