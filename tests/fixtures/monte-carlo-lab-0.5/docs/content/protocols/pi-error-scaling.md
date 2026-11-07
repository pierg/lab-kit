---
title: "How the error of the pi estimate scales with the sample size"
description: "Varies the number of points drawn, and measures the root mean square error over 100 seeds."
genre: "protocol"
status: locked
question: "Q-1"
tags: ["monte-carlo", "convergence"]
---

## Hypothesis

The root mean square error of the estimate falls as n to the power -0.5, where n is the number of points drawn.

## Intuition

Each point is an independent yes or no: inside the quarter circle with probability pi/4. The estimate is four times the share of yeses, so its standard deviation is sqrt(pi(4 - pi)/n), about 1.64 divided by sqrt(n). On a log-log plot the error should fall on a line of slope -0.5. If the hypothesis fails, it will be because the generator's points are not independent enough, or because the estimator is biased, so that the error stops falling.

## The one variable

The number of points drawn per estimate. Arms: 64, 256, 1,024, 4,096 and 16,384 points, each four times the last.

## Held fixed

The estimator in `substrate/estimator.py`, a frozen surface. Python's standard generator, seeded per estimate. 100 estimates per arm, each with its own seed: the arm's size times 1,000, plus the repeat's index from 0 to 99. The true value is `math.pi`.

## Pinned configuration

```yaml
language: python 3, standard library only
substrate: substrate/estimator.py
generator: random.Random, one per estimate
sizes: [64, 256, 1024, 4096, 16384]
repeats: 100
seed: size * 1000 + repeat
truth: math.pi
budget: none (token-free)
```

## Allowed moves

Nothing under test makes moves: the estimator is fixed code.

## Measures

- The error of one estimate: the estimate minus `math.pi`.
- The RMS error of an arm: the square root of the mean squared error over its 100 estimates.
- The slope: the least-squares slope of ln(RMS error) against ln(n) over the five arms, printed to three decimals.
- The scaled error of an arm: its RMS error times sqrt(n), against the theoretical sqrt(pi(4 - pi)), about 1.642.
- The mean estimate of an arm: the mean of its 100 estimates.

## Decision rules

- D1: keep the hypothesis if the slope lies between -0.6 and -0.4.
- D2: drop it if the slope is below -0.7 or above -0.3. A slope between the D1 and D2 bands is inconclusive.
- D3 (kill): if the RMS error at 16,384 points is not below the RMS error at 64 points, stop this line: the sampler or the estimator is broken, and no slope means anything.

## Predictions

- P1: the slope lies between -0.55 and -0.45. Confidence: 85%.
- P2: the scaled error lies within 10% of 1.642 in every arm. Confidence: 50%.
- P3: the RMS error at 16,384 points is below 0.015. Confidence: 90%.
- P4: the mean estimate at 16,384 points lies within 0.002 of pi. Confidence: 80%.

## What it cannot show

Anything about another estimator, another generator, sample sizes outside 64 to 16,384, or estimates in more than two dimensions. Running time was not measured.
