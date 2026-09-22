#!/usr/bin/env python3
"""E1 — comparison counts of insertion sort and merge sort on nearly-sorted arrays.

Deterministic: seeds 0..19, n = 1000, a fraction d of positions displaced by random swaps.
Writes out/comparisons.tsv (one row per d and seed) and out/summary.tsv (one row per d).

    python3 experiments/20260901-e1-nearly-sorted/bin/run.py
"""
import random
from pathlib import Path

N, SEEDS, FRACTIONS = 1000, range(20), (0.00, 0.01, 0.02, 0.05, 0.10, 0.20)
OUT = Path(__file__).resolve().parent.parent / "out"


def insertion(a):
    a, c = list(a), 0
    for i in range(1, len(a)):
        x, j = a[i], i - 1
        while j >= 0:
            c += 1
            if a[j] <= x:
                break
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = x
    return c


def merge(a):
    c = 0

    def sort(xs):
        nonlocal c
        if len(xs) <= 1:
            return xs
        m = len(xs) // 2
        left, right, out, i, j = sort(xs[:m]), sort(xs[m:]), [], 0, 0
        while i < len(left) and j < len(right):
            c += 1
            if left[i] <= right[j]:
                out.append(left[i]); i += 1
            else:
                out.append(right[j]); j += 1
        return out + left[i:] + right[j:]

    sort(list(a))
    return c


def nearly_sorted(n, d, rng):
    a = list(range(n))
    for _ in range(int(n * d / 2)):
        i, j = rng.randrange(n), rng.randrange(n)
        a[i], a[j] = a[j], a[i]
    return a


rows, summary = [], []
for d in FRACTIONS:
    ins, mer = [], []
    for s in SEEDS:
        a = nearly_sorted(N, d, random.Random(s))
        ins.append(insertion(a)); mer.append(merge(a))
        rows.append(f"{d:.2f}\t{s}\t{ins[-1]}\t{mer[-1]}")
    wins = sum(x < y for x, y in zip(ins, mer))
    summary.append(f"{d:.2f}\t{sum(ins) / len(ins):.1f}\t{sum(mer) / len(mer):.1f}\t{wins}\t{len(ins)}")
OUT.mkdir(exist_ok=True)
(OUT / "comparisons.tsv").write_text("displaced\tseed\tinsertion\tmerge\n" + "\n".join(rows) + "\n")
(OUT / "summary.tsv").write_text("displaced\tmean_insertion\tmean_merge\tinsertion_wins\tseeds\n" + "\n".join(summary) + "\n")
print((OUT / "summary.tsv").read_text(), end="")
