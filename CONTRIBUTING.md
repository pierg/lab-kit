# Contributing — LIVE

lab-kit is small, strict and slow to change on purpose: labs vendor it, and in a lab a kit re-sync is an instrument change that can move the judgment of results already taken.

## The rules

- **A check ships with a fixture designed to break it, or it is not a check.** Every tool has a `--selftest` with planted cases; `tests/e2e.sh` plants a violation for each check the lab registers and expects it reported by name. Break your change on purpose before you open the PR.
- **Never change the judgment of a result already taken.** A change to the ladder lint or the chronicle extractor that would flip an existing lab's verdict needs its own PR, a CHANGELOG entry saying which verdicts move and why, and a migration path.
- **Mechanisms belong in content-kit.** If what you want makes sense in any repo's docs, propose it to [content-kit](https://github.com/pierg/content-kit); lab-kit only adds the conventions of a lab, through content-kit's extension points.
- **The example lab is part of the contract.** A change that alters what a lab looks like shows up in `example-lab/`, which must stay green in strict mode.

## The gate

```bash
make check    # selftests · the example lab (strict) · an end-to-end install into a fresh lab and a copy of the example
```

It needs content-kit's engine: `uv tool install git+https://github.com/pierg/content-kit@$(cat CONTENT_KIT_PIN)`, or a checkout beside this one. CI runs the same target.

## Pull requests

Small and single-purpose; an imperative subject that says what changed and why; breaking changes in `CHANGELOG.md` with the migration step. Never `git add -A`.

Bugs: an issue with the smallest lab that shows it (`bash install.sh /tmp/x` plus the one file that trips it). Security problems: GitHub's private vulnerability reporting on this repository.
