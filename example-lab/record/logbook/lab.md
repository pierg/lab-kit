# Lab — LIVE

Append-only. Decisions, turns, and what bit us.

### 2026-09-01T08:30Z — [decision] count comparisons, not seconds

Wall-clock time depends on the machine and would need a pinned host to re-derive. Comparisons re-derive exactly anywhere, so the lab measures comparisons and says so in every bound.

### 2026-09-03T14:00Z — [result] the crossover sits between 1% and 2% displaced

E1 folded: insertion sort wins 18 of 20 seeds at 1% and 4 of 20 at 2% (F-1, F-2). Q1 is answered.

### 2026-09-04T09:00Z — [pivot] from disorder to size

With disorder settled, the other half of the folklore — small arrays — is the next question. E2 is drafted against it.

### 2026-09-06T10:00Z — [kill] no win on small random arrays

E2's kill rule fired: 27 of 200 seeds at 8 elements (F-3). Q2 is killed on comparisons.

### 2026-09-06T10:30Z — [lesson] a folklore claim names its measure before it is tested

The small-array rule of thumb is about time; this lab measures comparisons. Recorded in `record/LESSONS.md`.
