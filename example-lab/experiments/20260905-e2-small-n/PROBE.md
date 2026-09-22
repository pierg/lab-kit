# E2 — does insertion sort need fewer comparisons than merge sort on small random arrays?

**Date:** 2026-09-05 · **Status: LOCKED 2026-09-05T09:00Z**

> Everything below through §9 was written before any output existed. §10 was filled at the fold.

## 0 · Provenance

The routines are copied from `experiments/20260901-e1-nearly-sorted/bin/run.py` verbatim; the arrays are new.

## 1 · Question and the one variable

**Question:** on uniformly shuffled arrays, below what size does insertion sort make fewer comparisons than merge sort?

**The one variable:** the array size: 4, 8, 12, 16, 24, 32, 48, 64.

**Intuition:** libraries switch to insertion sort for small arrays, so perhaps it also compares less there. Failure would look like merge sort comparing less at every size.

**Held fixed:** seeds 1000 to 1199, distinct keys, the two routines.

## 2 · Arms

| Arm | The one variable | n | Everything else |
|---|---|---|---|
| insertion | size | 200 seeds × 8 sizes | as above |
| merge | size | 200 seeds × 8 sizes | as above |

## 3 · Metric definitions

As in E1: comparisons counted inside each routine; a seed is a win when insertion sort's count is strictly lower.

## 4 · Decision rules

- **Answer:** the largest size at which insertion sort wins most seeds.
- **Kill rule:** if insertion sort wins fewer than half the seeds at 8 elements, the small-size line is killed on comparisons.

## 5 · Predictions (blind, with confidence)

| # | Prediction | Confidence | Scored |
|---|---|---|---|
| P1 | insertion sort wins most seeds below 16 elements | 60% | miss |

## 6 · Instruments and frozen configuration

`bin/run.py`, Python 3, no dependencies; deterministic by seed.

## 7 · Legal action space

Run the script once; fold its output.

## 8 · Budget and launch

`python3 experiments/20260905-e2-small-n/bin/run.py` — seconds.

## 9 · What this experiment cannot show

Anything about time — which is what the libraries' threshold is about.

## 10 · Lesson (filled at the fold, never before)

The rule of thumb is about time, not comparisons; on comparisons merge sort wins from 8 elements up.
