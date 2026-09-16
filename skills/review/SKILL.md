---
name: review
description: Fold a concluded experiment's raw output, score it against its LOCKED PROBE.md decision rules, promote what survives into the findings ledger, and propose the next move. Use when an experiment finishes, when importing a concluded result, or when asked to score, interpret, or promote a result. Enforces honest scoring — numbers are re-derived from committed files, never from a summary; predictions are scored hit/miss against the pre-registration exactly; misses are reported as misses; every promoted finding carries a number, an anchor, and a re-derivation command.
---

# /review — fold, score, promote, propose

You turn a concluded experiment's raw record into a scored verdict against its pre-registration, promote what survives, and set the next move. You **score against the lock, not against hope.**

## Golden rules

1. **Re-derive, never restate.** Every number comes out of the committed evidence files by running the fold yourself. A number quoted from a summary, a chat message, or a previous document is not a number — it is a rumour. This is not pedantry: the single most expensive class of error in this kind of work is a stale figure quoted forward through three revisions.
2. **Score the lock exactly.** Read the locked `PROBE.md` first, before the results. Each pre-registered prediction gets HIT, MISS, or INDETERMINATE by the rule as written. A rule that turns out to have been badly chosen is still the rule — record the flaw as a lesson, do not rescore under a better one.
3. **A miss is a result.** Nulls, saturations, contaminated cells and fired kill rules are reported at the same length and prominence as wins. Several will have cost more to obtain.
4. **Break-case folds.** Validate every fold against a case designed to break it — a planted fixture with a known answer. A rename-blind fold once produced a confident false finding; the fold looked fine.
5. **You are not the reviewer.** This skill scores; the independent **reviewer** agent gates. Both happen before anything is called banked.
6. **A story is sealed.** A promoted finding's story page (`content/stories/<slug>/`) changes only when a row it cites changes status — a correction, a retraction, a superseding finding. It is not a rolling narrative; a new result earns a new story, never a rewrite of an old one.

## The flow

1. **Read the lock.** The locked `PROBE.md`: hypotheses, metric definitions, decision rules, predictions with confidences. Note the lock SHA.
2. **Fold.** Run the fold script over `out/`. If none exists, write one — with a `--selftest` against a planted fixture, wired into the gate. Never fold by eye.
3. **Score.** Every prediction: HIT / MISS / INDETERMINATE, with the number and the file it came from. Then the decision rules, including whether any kill rule fired.
4. **Record.** Append to `record/logbook/experiments.md` (what happened) and `record/logbook/lab.md` (any infra lesson, bug, correction or retraction). Append-only, dated, anchored to the run id and SHA.
5. **Promote — the ladder move.** Ask of each result: *is this a citable fact?* If yes, add a row to `record/findings.md`:

   ```markdown
   ## F-<n> · <plain headline: the result and its number, ≤ 24 words, no ids>
   **Status:** BANKED | PROVISIONAL
   **Tier:** <reviewer-gated | lab finding>
   **Date:** <YYYY-MM-DD, the day it was banked>
   **Number:** <the number with its denominator and baseline>
   **Bound:** <one sentence: the conditions under which it holds, and what it does not license>
   **Why it matters:** <one sentence>
   **Anchor:** `experiments/<slug>/out/<file>`
   **Re-derive:** `<the exact command that reproduces the number>`
   **Defense:** `record/findings/F-<n>.md`
   ```

   **The row is the interface, and the defense is a separate file.** Everything that argues for the number — the predictions as scored, the reviewer's verdict, the anomalies, the disclosures, the long-form bound — goes to `record/findings/F-<n>.md`, never as prose inside the row.

   Rules that make this worth having: **re-derive the number at promotion time**, not from the logbook entry that claimed it. A finding carries its **scope bound** in the same breath as its number — the conditions under which it holds. Tiers are never blurred: a reviewer-gated result and a lab finding under a locked pre-registration are not equal in weight, and prose must not pool them.

   **The story, same pass.** A promoted finding is not only a row: it also earns a **story page**, `content/stories/<slug>/index.html` — one sealed page per result, made with `ckit new story <slug>` (a lab whose content-kit pin has not yet declared the `story` genre declares it once, under `genres` in `lab.json` — content-kit's `genres/GENRES.md` § "Extending the set" — `ckit new story` fails loud, not silently, until it is declared). Its sections are fixed, and each is filled from something that already exists rather than freshly argued: **question** (the PROBE's question, in plain words), **why** (the PROBE's **Intuition** paragraph, written at lock, before any output existed), **did** (what was actually run), **happened** (the numbers, each carrying its row id), **learned** (the PROBE's **Lesson** — its §10, filled now, at this fold, never before), **not** (every bound the promoted row or rows carry, restated for a reader — this section is not optional, and a story with nothing in it is overselling), **deeper** (links to the row, the defense, the pre-registration, the raw evidence), **backlinks** (auto-populated by lint, like every other page). A figure on the story that carries a number is generated from the record by a script with a `--check` that the gate runs, never hand-drawn — see content-kit's `craft/figure.md` and this lab's `figures-check` Makefile target.

   **Then the front door.** The lab's project page (`home` in `lab.json`) gains exactly one plain sentence under "what we've learned", citing the new row id(s), and its dated "where we are" section is refreshed to the day of the fold. This is **the one place state lives in content** — no other page carries a rolling status.

6. **License.** If the finding supports something you want to *say*, add or amend a `## C-<n>` section in `record/claims.md` citing its finding ids, with the exact wording bound — what may be said, at what strength, and what must never be said alongside it.
7. **Gate.** `make check`. The ladder lint verifies every citation resolves; it does not verify honesty, which is what the reviewer is for.
8. **Propose.** Update `record/logbook/agenda.md` with the next moves, ranked by information value. Say plainly which questions the result closed and which it opened.

## Non-promotion is a record too

When a candidate result is *not* promoted, say so and why, in the same place. A triage nobody can audit is a triage that will be re-litigated in three weeks by someone who cannot tell whether you missed it or rejected it.
