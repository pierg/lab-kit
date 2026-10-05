# AGENTS.md: the Monte Carlo lab

This lab asks one question: does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)? It is `Q-1` in the library.

## Read first

- `.lab/method/DISCIPLINE.md` and `.lab/method/LADDER.md`, before any work.
- `ops/STATE.md`: what is true now, and the active mission.
- The library in `docs/`: start at its home page and the research map.

## Frozen surfaces

- `substrate/`: the estimator under test. Never edited or reformatted. A defect is recorded, not fixed.

## The gate

`lab-kit check` passes before anything lands on the main branch. It runs `folio check` first.

## Local rules

- Every run is token-free, pure Python with no third-party package, and seeded. No run spends.
- Never `git add -A`. Add the files you touched.
