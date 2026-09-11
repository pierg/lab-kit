# The ladder — one fact, one home, everything else cites it

Every lab records on the same ladder. It converges, then fans out:

```
evidence -> probe -> logbook -> finding -> claim -+-> page   (living)
                                                  +-> paper  (frozen at submission)
                                                  +-> post   (frozen at publication)
```

| Level | Home | Owns | Mutability |
|---|---|---|---|
| **Evidence** | `experiments/<slug>/out/`, ledgers, run trees | immutable raw measurement | never edited; never moved (moving breaks the anchors) |
| **Probe** | `experiments/<slug>/PROBE.md` | the pre-registered contract: question, one variable, metrics, decision rules, kill rule, blind predictions | frozen at the lock commit |
| **Logbook** | `record/logbook/` | what happened, what it means, what bit us | append-only |
| **Finding** | `record/findings.md` | every citable number + anchor + re-derivation + scope bound | append; a wrong row is struck through, not deleted |
| **Claim** | `record/claims.md` | what may be *said*, at what strength, and what must not be said alongside | revised deliberately |
| **Page** | `content/**` | the living reader-facing explanation | updated when a finding changes |
| **Paper** | `content/papers/<slug>/main.tex` | the venue artifact | frozen at submission |
| **Ops** | `ops/STATE.md` (now) · `ops/missions/` (chronicle) | what is happening and what is next | STATE is a pointer; missions are append-only |

## The two moves that make it work

**Promotion.** A fact starts local and only what recurs or generalizes moves up. The load-bearing step is logbook → finding: **re-derive the number from the evidence at promotion time**, never copy it from the entry that claimed it. A finding carries its scope bound in the same breath as its number.

Non-promotion is recorded too. A triage nobody can audit gets re-litigated in three weeks by someone who cannot tell whether you missed it or rejected it.

**Citation.** Everything above `finding` cites by **id**, never by path or by value. That is what lets a document move between directories, or a lab reorganize entirely, without breaking anything — and it is what `kit/tools/ladder_lint.py` checks:

- every `F-<n>` carries Status, Anchor and Re-derive — status is one of BANKED · PROVISIONAL · RETRACTED · SUPERSEDED · **MOVED**, the last for a row a by-question split relocated to another lab (correct, not superseded, and not wrong)
- every anchor resolves to real evidence, or to a pin declared in `record/pins.json` — this is what makes a cited repo renamable: the path lives in one declaration, not in every row
- every cited `F-<n>` exists — including cross-lab `<pin>:F-<n>`, checked against the pinned lab itself whenever its `local` checkout is reachable. A citation that names a real pin but no real row is otherwise invisible to every other check
- every `C-<n>` cites at least one finding
- every record, ops and paper document declares its status
- no markdown/HTML twin of the same authored document

A lab arriving from a `numbers.md §n` convention keeps its existing citations — see `MIGRATION.md`.

## Why the fan-out is not a pipeline

The page, the paper and the post are **siblings**, not derivations. They serve different readers under different contracts: the page is living and updates when a finding changes; the paper is frozen at submission and must read linearly; the post is frozen at publication. Generating one from another forces you to either freeze the page or mutate the paper.

So their **prose is written independently, three times**. What they share is not prose:

- the **finding ids** they cite
- the **figure sources** (SVG + generator) in `assets/figures/` (format-agnostic — the same SVG is inlined in an HTML entry or rendered to PDF for a paper)
- the **bibliography**

You never sync a number between artifacts. You cite one, and the gate checks it. That is what makes hand-syncing safe rather than a slow-motion drift.

## The chronicle — the ladder as a timeline, generated

`content/` shows the current direction. How it got there is the record — logbooks, missions, locked pre-registrations, findings — and the **chronicle** is a generated index over that record (`content/chronicle.json`, rendered by `/shell/chronicle.html`, with every event linking back into `/shell/record.html`, which renders the markdown file itself). Nobody writes it: `ckit lint` regenerates it, `ckit check` fails if it is stale, and `kit/tools/chronicle_lab.py` adds the ladder's vocabulary (PROBE locks with their question and kill rule, findings anchored into each experiment, claims, missions) to the generic dated headings.

The one convention it asks of the record: a dated heading may carry a **kind tag**, and the tag is what lets the timeline say *why* rather than only *that* —

    ### 2026-09-11T08:41Z — [pivot] the substrate changes
    ### 2026-08-26 — [decision] folio becomes a library

`pivot` · `kill` · `decision` · `lesson` · `instrument` · `result`; an untagged dated heading is a plain entry, so nothing written before this convention needs rewriting.
