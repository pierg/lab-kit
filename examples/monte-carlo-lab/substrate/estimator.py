"""The estimator under test: pi from points drawn uniformly in the unit square. Frozen: never edited in place."""

import random


def estimate_pi(n, seed):
    """Draw `n` points in [0, 1) x [0, 1) from a generator seeded with `seed`.

    Return 4 times the share that falls inside the quarter circle of radius 1.
    """
    rng = random.Random(seed)
    inside = 0
    for _ in range(n):
        x = rng.random()
        y = rng.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return 4 * inside / n
