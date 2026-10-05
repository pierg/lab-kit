# The ladder

Every fact in a lab has one home. Everything else cites it by id. The ladder says where each kind of fact lives, and how it moves up.

```
evidence -> protocol -> journal -> result -> claim -+-> report  (frozen once live)
                                                    +-> page    (living)
                                                    +-> paper   (frozen at submission)
```

## Where each fact lives

| Level | Home | Owns | Changes |
| --- | --- | --- | --- |
| Evidence | `experiments/{slug}/runs/{run-id}/out/` (lab file) | the raw measurement | never; hashed in its manifest (`lab-evidence-sealed`) |
| Protocol | `content/protocols/{slug}.md` (document) | the plan: one variable, measures, rules, kill rule, predictions | frozen at lock: status `locked` (folio's `frozen`, `lab-lock-intact`) |
| Score | `experiments/{slug}/score.yaml` (lab file) | each prediction and rule, scored against the lock | written once, at the review (`lab-score-exact`) |
| Journal | `content/journal/{yyyy}/{date}-{slug}.md`, one file per entry (document) | what happened, what it means, what went wrong | never edited; a new entry each time (folio's `permanent`) |
| Result | `content/results/R-{n}.md` (document) | one number, its baseline, bound, evidence path, re-derive command, protocol and date | never edited; status derived; corrected by a new result that supersedes it, or retracted by a journal entry (folio's `permanent`, `lab-rederive`) |
| Claim | `content/claims/C-{n}.md` (document) | what may be said, how strongly, and what must not be said beside it | revised deliberately (folio's claim genre) |
| Question | `content/questions/Q-{n}.md` (document) | what is open, ranked, what would settle it, and its protocols and results | revised; a narrowed, answered or dropped question stays, marked |
| Report | `content/reports/{slug}/index.html` (document) | one experiment's outcome in plain English | frozen once `live`; a result it cites that changes shows as a banner (folio's `frozen`) |
| Page | the library's maps, concepts and front door (documents) | the living explanation | updated when a result changes |
| Paper | the library's papers (documents) | the venue article | frozen at submission (folio's `frozen`) |
| State | `ops/STATE.md` (lab file) | what is true now and what is next | a pointer, rewritten freely (`lab-state-pointer`) |
| Missions | `ops/missions/` (lab files) | one operator objective, its approved plan and its log | approved before it runs (`lab-mission-approved`); the log is append-only (`lab-append-only`) |

## Promotion

A fact starts local. Only what recurs or generalises moves up.

The step that matters is journal to result. Re-derive the number from the evidence at that moment. Never copy it from the entry that announced it. Judged, not checked; the gate then re-runs the command forever after (`lab-rederive`).

A result carries its bound with its number: the conditions under which it holds, and what it does not license. Checked by the result genre's required parts.

Non-promotion is recorded too. A journal entry about the protocol names the number left out, and why. Otherwise someone re-argues it later without knowing it was rejected. Checked in part by `lab-scored-reported`.

## Citation

Everything above evidence cites by id, never by path or by value. That lets a document move without breaking anything.

- Every cited id resolves. Checked by `folio check` in the library and by `lab-ids-resolve` in lab files.
- Every claim cites at least one result. Checked by folio's claim genre.
- Every number on a page, report or paper cites a result. Checked by the lab pack's rule.
- Every result names its protocol, and its evidence lies inside one of that protocol's runs. Checked by `lab-result-grounded`.

An id is a link, never the subject of a sentence. Write "the cache cut median latency by a third (`R-7`)". Never write "`R-7` shows a third". Judged, not checked.

## The result is the interface

A result holds exactly what a citer needs. That is a plain headline, the number with its denominator and baseline, and the bound. It adds the evidence path, the re-derive command, the protocol and the date. Nothing in it is an argument.

The argument lives elsewhere. The score holds the predictions as scored. The report explains the outcome to a reader who was not there. The journal holds the anomalies and the disclosures. A reader loads the level they need: the result to cite, the report to understand, the evidence to re-derive.

## Siblings, not a pipeline

The report, the page and the paper are siblings. Each serves a different reader under a different contract. None is generated from another.

They share result ids, figure sources in `assets/figures/`, and the bibliography. They share no sentences. A number is never synced between them; each cites the same result, and the gate checks it.

## The kinds of page in a lab

- **The front door** is a project document. It says where the lab is, with its `reviewed` date, and adds one sentence per new result. It is the one page that carries rolling state.
- **A report** is frozen once `live`: one per experiment, written at the review. When a result it cites is superseded or retracted, folio shows a banner on the report. Nobody edits it.
- **Maps and concepts** hold what does not change week to week, so a report never re-explains it.
- **Generated indices** are never hand-written. folio regenerates them.

## Journal kinds

Every journal entry is its own dated file, written with `folio journal add`, and most carry one kind. The kinds are folio's: the core's four, `decision` · `lesson` · `correction` · `retraction`, and the lab pack's five, `lock` · `run` · `kill` · `instrument` · `pivot`. lab-kit adds none.

An entry names the documents it concerns in `about`, and shows on each of them. An entry with no kind is a plain entry. The kinds let a timeline say why, not only when.
