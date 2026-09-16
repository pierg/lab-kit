# Migrating an existing repo onto the ladder

Measured against `design-space-lab` on 2026-08-25, so the numbers below are real rather than estimated.

## What already works, unchanged

A repo that cites a shared numbers file by section number is **already on the ladder**; it just spells the ids differently. Set this in `lab.json`:

```json
{ "citation_alias": "section" }
```

and existing citations are read as findings: the markdown `§12`, the LaTeX `\S12`, ranges like `§§10-21`, and `## 12 · Title` / `### 21.1 · Title` headings. Measured on DSL's live corpus:

- **30 of 30 sections recognised** as findings, including sub-numbered rows.
- **51 of 51 citations in `report/main.tex` resolve** to a finding.
- **One warning** across the whole corpus: `claim-map.md:69` cites `§4.5`, which is a reference to a *folio page's* section rather than to a numbers row.

That last one is the honest limit of the alias, and it is why alias citations **warn rather than fail**: a bare `§4.5` in prose can mean a finding, this document's own section, or a section of some third document. Two of those three are handled — a reference to one of the file's own numbered headings is skipped, and ranges expand — but the third cannot be resolved by any rule, only by reading. Canonical `F-<n>` citations stay hard errors. **Full enforcement is what a lab buys by moving to canonical ids**; the alias is for getting there without a mass rewrite.

That matters because ~3,200 `§n` references exist across the four repos. Rewriting them up front would be a large, risky sed.

## What the migration actually costs

The one real gap, and it is the same gap in every section: **anchors and re-derivation commands live inside tables and prose, not as structured fields.** The information is all there — every row already carries "anchor · re-derive" — it just is not in a place a tool can check.

### Point the gate at the ledger you already have

The convention is `record/findings.md`, and it stays the default. But a migrating repo usually holds its ledger somewhere else with live by-path references into it, and making the file move a *precondition* for running the gate is how a migration gets abandoned. So `lab.json` takes an optional path:

```json
{ "citation_alias": "section", "findings": "docs/papers/proofs-rot/numbers.md" }
```

`claims` works the same way. The gate then reads the real file, and the ledger's own directory is scanned for citing documents so the lab loses no coverage by not having moved `record/` yet. Move the file later, deliberately, as its own change — not as the price of admission.

### Hoist the fields

So for each finding, hoist three fields to the top of its section:

```markdown
## 12 · Poison-cluster attribution
**Status:** BANKED · **Tier:** reviewer-gated
**Anchor:** `experiments/<slug>/out/<file>`
**Re-derive:** `<the exact command>`

<the existing prose and tables, unchanged>
```

On DSL's `numbers.md` that is **30 sections**, mechanical, and reviewable in one pass. Nothing else in the file needs to change.

Those three fields are the minimum the gate needs, and they are what this step is measured on; they are not the whole row. The shape a row settles into — a plain headline, Number, Bound, Why it matters, Date, and a `Defense:` link to `record/findings/F-<n>.md` where the long form lives — is in `LADDER.md` ("The row is the interface") and in `templates/record/findings.md`. Hoist first, layer second: each is a pass you can review on its own.

## Order of work

1. **Vendor the kit** (`install.sh`), keep `"ladder": "warn"`. The gate reports and does not block.
2. **Set `citation_alias`** if the repo cites by `§n`. Confirm the finding count matches what you expect.
3. **Hoist the three fields**, section by section. Re-derive each number as you go — that is the point of the pass, not a side effect of it.
4. **Fix what the citation check reports.** These are real: a citation to a finding that does not exist is a claim resting on nothing.
5. **Flip to `"ladder": "strict"`** once clean. Until then the gate is advisory, which is the honest state — a check that fails from day one gets disabled, and a disabled check is worse than no check.

## What does not move

**Evidence never moves.** Probe `out/` trees and run directories stay in the repo that produced them; their paths are what re-derivation commands name, and moving them breaks every anchor at once. A lab that cites evidence it does not own declares it in `record/pins.json` with a repo and a commit SHA, and writes the anchor as `<pin>:<path>`.
