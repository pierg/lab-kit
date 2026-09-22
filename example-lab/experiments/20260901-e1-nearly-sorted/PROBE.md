# E1 — does insertion sort need fewer comparisons than merge sort on nearly-sorted arrays?

**Date:** 2026-09-01 · **Status: LOCKED 2026-09-01T09:00Z**

> Everything below through §9 was written before any output existed. §10 was filled at the fold.

## 0 · Provenance

The first experiment of the lab; nothing carried over.

## 1 · Question and the one variable

**Question:** at 1000 elements, below how much disorder does insertion sort make fewer comparisons than merge sort?

**The one variable:** the fraction of positions displaced by random swaps: 0%, 1%, 2%, 5%, 10%, 20%.

**Intuition:** insertion sort pays for each position an element has to move, and a nearly-sorted array has few such moves; merge sort pays about the same whatever the order. So insertion sort should win at little disorder and lose quickly as disorder grows. Failure would look like insertion sort losing even at 1%.

**Held fixed:** 1000 elements, seeds 0 to 19, the two routines in `bin/run.py`.

## 2 · Arms

| Arm | The one variable | n | Everything else |
|---|---|---|---|
| insertion | displaced fraction | 20 seeds × 6 levels | as above |
| merge | displaced fraction | 20 seeds × 6 levels | as above |

## 3 · Metric definitions

Comparisons: the number of times two keys are compared, counted inside each routine. A seed is a win when insertion sort's count is strictly lower.

## 4 · Decision rules

- **Answer:** the crossover is the lowest level at which insertion sort wins fewer than half the seeds.
- **Kill rule:** if insertion sort wins fewer than 10 of 20 seeds even at 1% displaced, the nearly-sorted line is killed.

## 5 · Predictions (blind, with confidence)

| # | Prediction | Confidence | Scored |
|---|---|---|---|
| P1 | insertion sort wins at least 15 of 20 seeds at 1% | 70% | hit (18) |
| P2 | the advantage survives to 5% | 40% | miss (0) |

## 6 · Instruments and frozen configuration

`bin/run.py`, Python 3, no dependencies; deterministic by seed.

## 7 · Legal action space

Run the script once; fold its output.

## 8 · Budget and launch

`python3 experiments/20260901-e1-nearly-sorted/bin/run.py` — seconds.

## 9 · What this experiment cannot show

Anything about time, about other sizes, or about other kinds of disorder.

## 10 · Lesson (filled at the fold, never before)

The window is narrow: a handful of swaps per hundred elements is enough to hand the win to merge sort.
