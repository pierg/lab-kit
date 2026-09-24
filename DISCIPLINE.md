# Discipline — the shared operating contract

Every lab that vendors this kit inherits this file. A lab's own `AGENTS.md` names it in plain text — read `kit/DISCIPLINE.md` now — and then adds only what is genuinely local: its question, its frozen surfaces, its gate. `CLAUDE.md` is the one line `@AGENTS.md`.

It exists because these rules were each learned by being broken, and because restating them in five places is how they drift apart.

## 1 · The record is append-only

Records are added to at the bottom; a past entry is never edited or deleted. Evolving state is captured as "as of this entry, X"; a later entry supersedes it and the old one stays. **Corrections and retractions are new entries on the record, never silent edits.** The one deliberate exception is the agenda, which is mutable by design — its history survives in the logbook.

A null, a saturation, a contaminated cell or a fired kill rule is a **result**, and is recorded at the same length as a win. Several will have cost more to obtain.

## 2 · Two git lanes

- **Records** — logbooks, pre-registrations, results, pages — go straight to `main` with the gate green.
- **Instrument** — the apparatus, judge verbs, tools, the gate itself — goes via PR with a what-and-why, merged on green CI, after the review gate.

This is the firewall on autonomy: proposing is cheap, **changing judgment is rigorous**. An agent that could edit the judge could fake progress; one that must land it through a tripwired PR cannot. When GitHub is unreachable, realize the PR lane locally (branch, gate green, `--no-ff` merge) and **disclose it in the logbook** — never as a silent workaround.

Never `git add -A`. Commit the files you touched plus what lint regenerated, and verify that diff is attributable to your edit.

## 3 · Pre-register before you measure

Every experiment is a `PROBE.md` with hypotheses, metric definitions, decision rules, a kill rule, and predictions with confidences — **locked by commit before any live run**. Results are scored against the locked rules exactly. A rule that turns out to have been badly chosen is still the rule; record the flaw as a lesson rather than rescoring under a better one.

A pre-registration without a kill rule cannot produce a publishable null.

## 4 · Every number re-derives

No number enters a plan, a page, a paper or a post except by citing a row in `record/findings.md`, and every row carries an origin anchor and the command that reproduces it. **Re-derive at promotion time** — from the evidence, not from the logbook entry that claimed it. A number quoted forward from a summary is a rumour with a decimal point.

Tiers are never blurred: a reviewer-gated result and a lab finding under a locked pre-registration are both real and are not equal in weight.

## 5 · Fail loud

No defensive fallbacks, no silent degradation. An arm whose tool fails is invalid, never quietly downgraded. Exit codes are load-bearing. Undecidable is not a pass. An apparatus failure is a finding to report, not a thing to patch around.

Every script ships a `--selftest` wired into the gate. Every fold is validated against a case designed to break it — a planted fixture with a known answer. A fold that looks fine can still be, for instance, rename-blind, and produce a confident false finding.

## 6 · Frozen surfaces

A lab names its frozen surfaces in its own `AGENTS.md`: the vendored substrate, locked pre-registrations and their evidence, pinned image digests, judge-owned paths. These are never edited or reformatted in place — a known defect in a frozen surface is **recorded, not fixed**, because fixing it breaks comparability with results already taken against it.

Work is additive. If a frozen surface must change, stop and put the case to the operator.

Roster, CLI, effort and image digests are pinned per run and never swapped mid-run. On failure: terminate and rerun fresh, disclosed.

## 7 · The review gate

Before any PR merges, any result is promoted to a finding, or any pre-registration locks: an independent **reviewer** with fresh context and no write tools reads the artifact before the story about it. Reviewer findings go to the commander, never into worker state. **The implementer never self-certifies.**

## 8 · Documents declare their status

Every document states LIVE, HISTORICAL, PARKED, RETIRED or FROZEN in its first three lines, plus a supersedes / superseded-by pointer. A reader must be able to tell in three lines whether a document is still true.

## 9 · Git is the archive

The working tree holds only what should be read today. Superseded drafts are **deleted** and recorded in `record/RETIRED.md` with a recovery SHA — not moved to an `archive/` directory for the next reader to re-triage. Exactly two things survive being wrong in place: a row in `findings.md` (struck through, because it may already have been cited) and a claim on a page that already circulated.

## 10 · Content, not form

One paragraph per line. Never hard-wrap prose to a column — soft wrapping belongs in the editor. Lists, tables, headings and code keep their natural breaks. For code, use the project's formatter.

**One format per document.** A markdown draft and an HTML page of the same document are twins, and twins drift. The gate flags them.

## 11 · Spend is the operator's

No live token spend without the operator's word. Prefer token-free stages first, to de-risk. Subscription-only auth — provider API keys are never exported or hardcoded. Cheap models for mechanical work; the expensive seat is for synthesis.

**No deadline drives the science.** Never arrange, trim, or rush a result to meet a date.
