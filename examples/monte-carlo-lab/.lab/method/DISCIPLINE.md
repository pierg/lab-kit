# Discipline

This is the operating contract of every lab lab-kit runs. A lab's own `AGENTS.md` says to read it, then adds only what is local: its question, its frozen surfaces, its rules. Every rule below says what checks it, or says it is judged.

These rules exist because each one is cheap to keep and expensive to break. Restating them elsewhere is how they drift, so other files point here.

## 1. Every document goes through folio

Questions, protocols, results, claims, reports, journal entries, papers and pages are documents. Each is written by folio's write skill, or by a workflow that folio's run skill follows. An agent never writes one by hand. Checked by `folio check`: a document that breaks its genre's card fails.

Lab files are not documents. State, missions, lock records, run records, scores and evidence are lab files. They hold pointers and data, never an argument. Judged, not checked.

## 2. The record is never edited

A journal entry and a result are permanent: once committed, never edited or deleted. Each journal entry is its own file, written with `folio journal add`. Checked by folio's `permanent` check. Every mission log grows at the bottom, and lock records and run records never change. Checked by `lab-append-only`.

A wrong record is corrected by a new document that points back. A new result names the old one in `supersedes`. A retraction is a journal entry of kind `retraction` whose `about` names the result. The old result stays at its address, and folio derives its status, `superseded` or `retracted`, and shows the banner. Checked by folio's `fields` and `permanent` checks.

A null, a fired kill rule, a contaminated arm or a failed run is a result. It is recorded at the same length as a win. Judged, not checked.

## 3. Two lanes

- **Records** go to the main branch with the gate green: documents, lab files, evidence. Checked by `lab-kit check` in CI.
- **Instruments** go through a pull request with a what-and-why, after a reviewer pass. Instruments are the lab's harness, the scripts that produce or fold evidence, and the gate. Judged, not checked.

This is the firewall on autonomy. Proposing is cheap. Changing how the lab judges is rigorous. An agent that could edit the judge could fake progress.

When the remote is unreachable, keep the lane locally: a branch, the gate green, a merge commit. Disclose it in a journal entry of kind `instrument`. Judged, not checked.

Commit the files you touched and what the tools regenerated. Never stage everything at once. Judged, not checked.

## 4. Pre-register before you measure

Every experiment has a protocol, locked before any run. It states the question, the one variable and an intuition in plain words. It names the arms, the pinned configuration, the allowed moves, the measures, the decision rules `D1`... with the kill rule marked, and blind predictions `P1`... with confidences. Checked by `lab-lock-recorded`, `lab-lock-intact` and `lab-run-after-lock`; the parts by the protocol genre.

A protocol with no kill rule cannot produce a null worth publishing. Checked by the protocol genre's `rule_ids` check.

Score against the locked rules exactly. A rule that proves badly chosen is still the rule. Record the flaw as a lesson; never rescore under a better rule. Checked in part by `lab-score-exact`; the rest is judged.

## 5. One variable

Arms differ in exactly the thing under test. If you cannot name the one variable in a sentence, the design is not ready. Judged, not checked.

## 6. Every number re-derives

A number enters a page, a report, a claim or a paper only by citing a result. Checked by the lab pack's rule in `folio check`.

Every result carries its evidence path and the command that reproduces it. That command runs in the gate and must print the number. Checked by `lab-rederive` and `lab-result-grounded`.

Re-derive at promotion time, from the evidence, never from the entry that announced the number. A number quoted forward from a summary is a rumour. Judged, not checked.

## 7. Fail loud

No defensive fallbacks. No silent degradation. An arm whose tool fails is invalid, never quietly downgraded. Exit codes count. Undecidable is not a pass. Judged, not checked, except that `lab-kit run` records every exit code.

An apparatus failure is a result to report, not a thing to patch around. Judged, not checked.

Every script ships a `--selftest`, and the gate runs it. Checked by `lab-selftest`.

Every fold is tested against a planted case with a known answer. A fold that looks fine can still be blind to a renamed field. Judged, not checked.

## 8. Frozen surfaces

A lab names its frozen surfaces in `lab.yaml`: the substrate it tests on, pinned images, judge-owned files. They are never edited or reformatted. Checked by `lab-frozen-intact`.

A locked protocol and its evidence are frozen too. Checked by folio's `frozen` check, `lab-lock-intact` and `lab-evidence-sealed`.

A known defect in a frozen surface is recorded, not fixed. Fixing it breaks comparison with results already taken. Judged, not checked.

Work is additive. If a frozen surface must change, stop and put the case to the operator. Judged, not checked.

## 9. The roster is frozen per run

Models, tools, settings and image digests are pinned in the protocol's pinned configuration. A run uses exactly them. Checked by `lab-roster-frozen`.

On failure, end the run and start a fresh one with the same configuration. Disclose it in a journal entry of kind `run` about the protocol. Never swap a model mid-run. Judged, not checked.

## 10. The reviewer gates

Before a protocol locks, a result is recorded, or an instrument change merges, an independent reviewer reads the artefact before the story about it. The reviewer has fresh context and writes nothing. Checked for results by `lab-result-grounded`; otherwise judged.

The reviewer's verdict goes to the commander, never into a worker's files. The implementer never certifies its own work. Judged, not checked.

## 11. Documents say whether they are true

Every document has a status from the states its genre declares. An absent status means `live`, and a result's status is derived, never written. A protocol is `draft`, `locked` or `abandoned`. A question is `draft`, `live`, `narrowed`, `answered` or `dropped`. Checked by folio's `status` check.

A result writes no status. folio derives it: `superseded` when a newer result supersedes it, `retracted` when a retraction names it, `live` otherwise. Nobody edits a result to change what it says about itself. Checked by folio's `fields` check.

## 12. Git is the archive

The working tree holds what should be read today. A superseded page is retired through folio's organise skill, which redirects its address. Checked by `folio check`.

Two things survive being wrong in place: a result, superseded or retracted and never redirected, and a claim that already circulated, marked `withdrawn`. A frozen report stays too, and shows a banner for each result it cites that changed. Checked by folio's result and claim genres.

## 13. Spend is the operator's

No live spend without the operator's word, recorded in a mission with a cap. Checked by `lab-spend-recorded`, which checks the record, not the word.

Prefer token-free stages first, to de-risk a live run. Use cheap models for mechanical work. Keep the expensive seat for synthesis. Judged, not checked.

Provider keys are never exported to a child process, written to a file, or committed. Judged, not checked.

No deadline drives the science. Never trim or rush a result to meet a date. Judged, not checked.

## 14. The operator approves the mission

A mission has two phases. It is planned with the operator, then it runs on its own. The plan names the questions it serves, what counts as done, its scope, its spend, what it never touches and where it stops. It stays a draft until the operator approves it, and the mission file records who approved it and when. Nothing runs under a draft. Checked by `lab-mission-approved`, which checks the record, not the word.

A running mission comes back to the operator only at the stops its plan names and at the method's own: a frozen surface, a lock, spend past the cap, publishing outside the lab. Everything else it decides and records. Judged, not checked.
