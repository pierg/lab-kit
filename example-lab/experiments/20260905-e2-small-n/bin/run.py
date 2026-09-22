#!/usr/bin/env python3
"""E2 — comparison counts of insertion sort and merge sort on small random arrays.

Deterministic: seeds 0..199 per size, sizes 4 to 64, uniformly shuffled distinct keys.
Writes out/summary.tsv (one row per size).

    python3 experiments/20260905-e2-small-n/bin/run.py
"""
import random
from pathlib import Path

HERE = Path(__file__).resolve()
SIZES, SEEDS = (4, 8, 12, 16, 24, 32, 48, 64), range(200)
OUT = HERE.parent.parent / "out"


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


summary = []
for n in SIZES:
    ins, mer = [], []
    for s in SEEDS:
        a = list(range(n))
        random.Random(1000 + s).shuffle(a)
        ins.append(insertion(a)); mer.append(merge(a))
    wins = sum(x < y for x, y in zip(ins, mer))
    summary.append(f"{n}\t{sum(ins) / len(ins):.1f}\t{sum(mer) / len(mer):.1f}\t{wins}\t{len(ins)}")
OUT.mkdir(exist_ok=True)
(OUT / "summary.tsv").write_text("n\tmean_insertion\tmean_merge\tinsertion_wins\tseeds\n" + "\n".join(summary) + "\n")
print((OUT / "summary.tsv").read_text(), end="")
