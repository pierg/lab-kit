"""Fold a run's estimates into one number.

    fold.py <estimates.tsv> --stat slope [--error rms|mae]
    fold.py <estimates.tsv> --stat rms|scaled|mean --size <n>

`slope` prints the least-squares slope of ln(error) against ln(n) over every
size, to three decimals, where an arm's error is its RMS error (the default)
or its mean absolute error. `rms` prints one arm's RMS error to four decimals,
`scaled` its RMS error times sqrt(n) to three, and `mean` its mean estimate to
five. Errors are measured against math.pi. `--selftest` folds planted tables
with known answers.
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from pathlib import Path


def read(path: Path) -> dict[int, list[float]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines[0].split("\t") != ["size", "repeat", "seed", "estimate"]:
        raise SystemExit(f"{path}: unexpected header {lines[0]!r}")
    arms: dict[int, list[float]] = {}
    for line in lines[1:]:
        size, _, _, value = line.split("\t")
        arms.setdefault(int(size), []).append(float(value))
    if not arms:
        raise SystemExit(f"{path}: no estimates")
    return arms


def rms(values: list[float]) -> float:
    return math.sqrt(sum((v - math.pi) ** 2 for v in values) / len(values))


def mae(values: list[float]) -> float:
    return sum(abs(v - math.pi) for v in values) / len(values)


def slope(arms: dict[int, list[float]], error: str) -> float:
    measure = rms if error == "rms" else mae
    xs = [math.log(size) for size in sorted(arms)]
    ys = [math.log(measure(arms[size])) for size in sorted(arms)]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def fold(arms: dict[int, list[float]], stat: str, size: int | None, error: str) -> str:
    if stat == "slope":
        return f"{slope(arms, error):.3f}"
    if size not in arms:
        raise SystemExit(f"no estimates for size {size}")
    values = arms[size]
    if stat == "rms":
        return f"{rms(values):.4f}"
    if stat == "scaled":
        return f"{rms(values) * math.sqrt(size):.3f}"
    return f"{sum(values) / len(values):.5f}"


def selftest() -> None:
    # Errors of exactly 1/sqrt(n) in both signs: RMS and MAE are 1/sqrt(n), the slope is -0.5.
    rows = ["size\trepeat\tseed\testimate"]
    for size in (4, 16, 64):
        e = 1 / math.sqrt(size)
        rows += [f"{size}\t0\t0\t{math.pi + e!r}", f"{size}\t1\t1\t{math.pi - e!r}"]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "estimates.tsv"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        arms = read(path)
    assert fold(arms, "slope", None, "rms") == "-0.500", fold(arms, "slope", None, "rms")
    assert fold(arms, "slope", None, "mae") == "-0.500"
    assert fold(arms, "rms", 16, "rms") == "0.2500"
    assert fold(arms, "scaled", 64, "rms") == "1.000"
    assert fold(arms, "mean", 4, "rms") == f"{math.pi:.5f}"
    # RMS and MAE differ when the errors differ in size.
    assert rms([math.pi + 3, math.pi - 1]) != mae([math.pi + 3, math.pi - 1])
    print("selftest passed")


def main() -> None:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("estimates", type=Path)
    parser.add_argument("--stat", choices=["slope", "rms", "scaled", "mean"], required=True)
    parser.add_argument("--size", type=int)
    parser.add_argument("--error", choices=["rms", "mae"], default="rms")
    args = parser.parse_args()
    if args.stat != "slope" and args.size is None:
        parser.error(f"--stat {args.stat} needs --size")
    print(fold(read(args.estimates), args.stat, args.size, args.error))


if __name__ == "__main__":
    main()
