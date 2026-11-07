"""Draw every estimate the protocol pins: each arm's size, 100 seeds each.

Run by `lab-kit run`, it reads the pinned configuration from the run's
`run.json` and writes `estimates.tsv` into the run's `out/`: one row per
estimate, with its size, repeat, seed and value. `--selftest` checks the
seeding and the estimator on planted cases.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "substrate"))

from estimator import estimate_pi  # noqa: E402

SEED_RULE = "size * 1000 + repeat"


def seed_of(size: int, repeat: int) -> int:
    return size * 1000 + repeat


def rows(config: dict) -> list[tuple[int, int, int, float]]:
    if config["seed"] != SEED_RULE:
        raise SystemExit(f"the pinned seed rule is {config['seed']!r}; this script implements {SEED_RULE!r}")
    out = []
    for size in config["sizes"]:
        for repeat in range(config["repeats"]):
            seed = seed_of(size, repeat)
            out.append((size, repeat, seed, estimate_pi(size, seed)))
    return out


def selftest() -> None:
    assert seed_of(64, 0) == 64000 and seed_of(16384, 99) == 16384099
    assert len({seed_of(s, r) for s in (64, 256, 1024) for r in range(100)}) == 300, "seeds must not repeat"
    value = estimate_pi(1000, 7)
    assert value == estimate_pi(1000, 7), "the same seed must give the same estimate"
    assert 0 <= value <= 4 and (value * 1000 / 4) == int(value * 1000 / 4), "4 x a count over n"
    assert abs(estimate_pi(20000, 1) - 3.14159) < 0.05
    table = rows({"sizes": [16], "repeats": 2, "seed": SEED_RULE})
    assert [r[:3] for r in table] == [(16, 0, 16000), (16, 1, 16001)]
    print("selftest passed")


def main() -> None:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return
    run_dir = Path(os.environ["LAB_RUN_DIR"])
    config = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))["config"]
    out = Path(os.environ["LAB_OUT"]) / "estimates.tsv"
    lines = ["size\trepeat\tseed\testimate"]
    lines += [f"{size}\t{repeat}\t{seed}\t{value!r}" for size, repeat, seed, value in rows(config)]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines) - 1} rows to {out.name}")


if __name__ == "__main__":
    main()
