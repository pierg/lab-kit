# Findings — LIVE

**The single source every number re-derives from.** No number enters a page except by citing a row here; every row carries its anchor and the command that reproduces it. The long form of each row is its defense, at the `Defense:` path.

## F-1 · With 1% of positions displaced, insertion sort makes fewer comparisons than merge sort in 18 of 20 seeds
**Status:** BANKED
**Tier:** lab finding
**Date:** 2026-09-03
**Number:** 18 of 20 seeds; mean 4044.6 comparisons against merge sort's 5966.2, at 1000 elements
**Bound:** 1000 elements, displacement by random swaps, comparisons only — no claim about time or other sizes.
**Why it matters:** it puts a number on "good for nearly-sorted input".
**Anchor:** `experiments/20260901-e1-nearly-sorted/out/summary.tsv`
**Re-derive:** `awk -F'\t' '$1=="0.01"' experiments/20260901-e1-nearly-sorted/out/summary.tsv`
**Defense:** `record/findings/F-1.md`

## F-2 · By 2% displaced the advantage is gone, and from 5% insertion sort never wins
**Status:** BANKED
**Tier:** lab finding
**Date:** 2026-09-03
**Number:** 4 of 20 seeds at 2% (mean 7298.3 against 6374.4); 0 of 20 at 5%, 10% and 20%
**Bound:** the same 1000 elements and swaps as the row above; the crossover lies between 1% and 2%, not at a measured point.
**Why it matters:** the window is narrow — a few swaps per hundred elements closes it.
**Anchor:** `experiments/20260901-e1-nearly-sorted/out/summary.tsv`
**Re-derive:** `awk -F'\t' '$1=="0.02" || $1=="0.05"' experiments/20260901-e1-nearly-sorted/out/summary.tsv`
**Defense:** `record/findings/F-2.md`

## F-3 · On small random arrays insertion sort never needs fewer comparisons on average
**Status:** BANKED
**Tier:** lab finding
**Date:** 2026-09-06
**Number:** at 8 elements it wins 27 of 200 seeds (mean 19.0 against 15.8); from 16 elements, 0 of 200
**Bound:** uniformly shuffled distinct keys, comparisons only; the libraries' size threshold is about constant factors, which this does not measure.
**Why it matters:** the kill rule fired — the small-size line is closed on this measure.
**Anchor:** `experiments/20260905-e2-small-n/out/summary.tsv`
**Re-derive:** `awk -F'\t' '$1=="8" || $1=="16"' experiments/20260905-e2-small-n/out/summary.tsv`
**Defense:** `record/findings/F-3.md`
