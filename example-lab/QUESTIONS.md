# Questions — LIVE

What this lab set out to find, each with the observable that would make us stop asking it.

## Q1 · Below how much disorder does insertion sort need fewer comparisons than merge sort?

**Why it is open:** folklore says insertion sort is "good on nearly-sorted input", but not how nearly, and not on which measure.
**How it could be answered:** count comparisons on arrays with a controlled fraction of displaced positions, across seeds.
**Kill criterion:** insertion sort wins fewer than 10 of 20 seeds even at the least disorder tried.
**Status:** ANSWERED · F-1, F-2

## Q2 · Does insertion sort need fewer comparisons than merge sort on small random arrays?

**Why it is open:** libraries switch to insertion sort below a size threshold; whether that is about comparisons or about constant factors is rarely said.
**How it could be answered:** count comparisons on uniformly shuffled arrays of 4 to 64 elements.
**Kill criterion:** insertion sort wins fewer than half the seeds at 8 elements.
**Status:** KILLED · F-3

## Answered

| Question | Answer | Finding |
|---|---|---|
| Q1 | between 1% and 2% of positions displaced, for 1000 elements | F-1, F-2 |

## Killed

| Question | What fired the kill rule | Where it is recorded |
|---|---|---|
| Q2 | 27 of 200 seeds at 8 elements | F-3 · `record/logbook/lab.md` |

## Parked

| Question | Why parked | What would revive it |
|---|---|---|
