# The logbook — LIVE

The operational journal: what happened, and what is next. This is the layer the machine record cannot derive — intent, live observation, judgement calls, lessons, and the backlog.

| File | Register | Scope |
|---|---|---|
| `experiments.md` | record | append-only run console: every experiment's lifecycle |
| `lab.md` | record | infra lessons, bugs, corrections, retractions — read before trusting any surface |
| `agenda.md` | **agenda** | the one mutable file: what to do next |

**Records are append-only.** Add entries at the bottom; never edit or delete a past one. Evolving state is captured as "as of this entry, X"; a later entry supersedes it and the old one stays. A null result or a saturated run is a finding, not a failure — log it plainly.

```
## YYYY-MM-DDThh:mmZ — <short title>
<2–4 sentences: what happened · why it matters · what I did / next.
Anchored to the machine record: run id and/or commit SHA.>
```

Stamp the time with `date -u +%Y-%m-%dT%H:%MZ`.

**The agenda is the deliberate exception** — edited freely, items added, reordered and removed as they land. Its history is preserved in `lab.md`, so nothing is lost.

**Promotion.** Whenever an entry lands here, ask: *is this a citable fact?* If yes, promote it to `record/findings.md` with a number, an anchor and a re-derivation command — re-derived at promotion time, not copied from the entry that claimed it. That is the ladder's load-bearing move; see `kit/LADDER.md`.
