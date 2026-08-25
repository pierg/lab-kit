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

- every `F-<n>` carries Status, Anchor and Re-derive
- every anchor resolves to real evidence, or to a pin declared in `record/pins.json`
- every cited `F-<n>` exists
- every `C-<n>` cites at least one finding
- every record, ops and paper document declares its status
- no markdown/HTML twin of the same authored document

## Why the fan-out is not a pipeline

The page, the paper and the post are **siblings**, not derivations. They serve different readers under different contracts: the page is living and updates when a finding changes; the paper is frozen at submission and must read linearly; the post is frozen at publication. Generating one from another forces you to either freeze the page or mutate the paper.

So their **prose is written independently, three times**. What they share is not prose:

- the **finding ids** they cite
- the **figure sources** (SVG + generator) in `assets/paper/`
- the **bibliography**

You never sync a number between artifacts. You cite one, and the gate checks it. That is what makes hand-syncing safe rather than a slow-motion drift.
