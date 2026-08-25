# Migrating an existing repo onto the ladder

Measured against `design-space-lab` on 2026-08-25, so the numbers below are real rather than estimated.

## What already works, unchanged

A repo that cites a shared numbers file by section number is **already on the ladder**; it just spells the ids differently. Set this in `lab.json`:

```json
{ "citation_alias": "section" }
```

and `§12` citations plus `## 12 · Title` / `### 21.1 · Title` headings are read as `F-12` and `F-21.1`. Measured on DSL's live `numbers.md` and its consumers:

- **30 of 30 sections recognised** as findings, including sub-numbered rows.
- **Zero citation errors** across `claim-map.md` and `report/main.tex` — every `§n` reference already resolves.

That matters because ~3,200 `§n` references exist across the four repos. Rewriting them would be a large, risky sed. Aliasing makes it a config flag, and the canonical id stays `F-<n>` for anything written from here on.

## What the migration actually costs

The one real gap, and it is the same gap in every section: **anchors and re-derivation commands live inside tables and prose, not as structured fields.** The information is all there — every row already carries "anchor · re-derive" — it just is not in a place a tool can check.

So for each finding, hoist three fields to the top of its section:

```markdown
## 12 · Poison-cluster attribution
**Status:** BANKED · **Tier:** reviewer-gated
**Anchor:** `experiments/<slug>/out/<file>`
**Re-derive:** `<the exact command>`

<the existing prose and tables, unchanged>
```

On DSL's `numbers.md` that is **30 sections**, mechanical, and reviewable in one pass. Nothing else in the file needs to change.

## Order of work

1. **Vendor the kit** (`install.sh`), keep `"ladder": "warn"`. The gate reports and does not block.
2. **Set `citation_alias`** if the repo cites by `§n`. Confirm the finding count matches what you expect.
3. **Hoist the three fields**, section by section. Re-derive each number as you go — that is the point of the pass, not a side effect of it.
4. **Fix what the citation check reports.** These are real: a citation to a finding that does not exist is a claim resting on nothing.
5. **Flip to `"ladder": "strict"`** once clean. Until then the gate is advisory, which is the honest state — a check that fails from day one gets disabled, and a disabled check is worse than no check.

## What does not move

**Evidence never moves.** Probe `out/` trees and run directories stay in the repo that produced them; their paths are what re-derivation commands name, and moving them breaks every anchor at once. A lab that cites evidence it does not own declares it in `record/pins.json` with a repo and a commit SHA, and writes the anchor as `<pin>:<path>`.
