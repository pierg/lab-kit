---
name: present
description: Author a reader-facing artifact for this lab — an HTML page in the library shell (note, entry, concept, hub, project, chapter) or a LaTeX paper. Use when a session's output is a document rather than a chat answer. Enforces the presentation contract — the repo copy is the source of truth, one format per document with no markdown/HTML twins, every number cites a finding id, pages use the shared shell vocabulary, and the gate is green before it lands.
---

# /present — author a reader-facing artifact

You are producing a **document**, not a chat reply. Chat gets the TL;DR and the repo path. The repo copy is the source of truth.

## Where a document sits on the ladder

    evidence -> probe -> logbook -> finding -> claim -+-> page   (living)
                                                      +-> paper  (frozen at submission)
                                                      +-> post   (frozen at publication)

Everything converges at `claim`, then **fans out**. The page, the paper and the post are siblings — none is generated from another, and their prose is written independently. What they share is not prose: it is the **finding ids they cite**, the figure sources, and the bibliography. That is the whole reason hand-syncing is safe — you never sync a number, you cite one, and the gate checks it.

**One format per document.** A markdown draft *and* an HTML page of the same document is a twin, and twins drift. The gate flags them. The one legitimate `main.md` + `index.html` pair is an imported external paper, where `main.md` holds someone else's text and `index.html` holds your reading of it — that case declares itself with `source.json`.

## Golden rules

1. **Every number cites a finding.** No number enters a page, a paper or a post except by citing an `F-<n>` row from `record/findings.md`. What may be *said* about it, and at what strength, is bounded by `record/claims.md`. If you want to write a sentence that no claim licenses, stop and go promote the finding first — do not write the sentence and reconcile later.
2. **Misses at the same volume as wins.** A page that reports only what worked is an advertisement, not a record.
3. **Status in the first three lines.** LIVE, HISTORICAL, PARKED, RETIRED or FROZEN, plus a supersedes/superseded-by pointer. A reader must be able to tell in three lines whether a document is still true.
4. **One paragraph per line.** Never hard-wrap prose to a column. Lists, tables, headings and code keep their natural breaks.

## Authoring an HTML page

Pick a genre — do not invent one:

| Genre | When | Path |
|---|---|---|
| **Note** | one atomic claim, a few sentences | `content/notes/<slug>.html` |
| **Entry** | dense one-page read (deep dive, paper reading) | `content/entries/<slug>/index.html` |
| **Concept** | canonical definition-of-record for a reused term | `content/concepts/<slug>/index.html` |
| **Chapter** | ordered teaching step inside a book | `content/books/<slug>/NN-name.html` |
| **Hub** | orientation and stance over a cluster | `content/hubs/<slug>.html` |
| **Project** | active-work hub with status | `content/projects/<slug>/index.html` |
| **Paper** | a document with a LaTeX twin's landing page | `content/papers/<slug>/index.html` |

Promotion: note → entry → chapter as scope grows. **Define once, link everywhere** — the second time a term needs prose explanation, promote it to `content/concepts/<slug>/` and reference it with `<a class="defn-link" href="/content/concepts/<slug>/">TERM</a>`; the shell pops the target's `blockquote.defn` on hover.

Mechanics: copy the matching skeleton from `kit/shell/skeletons/`. Every page loads `/shell/lib.css` and `/shell/lib.js`. Use the shell vocabulary in `kit/shell/COMPONENTS.md` — `.hb` tokens only, **no new hex colors or type stacks**. Page-specific widget CSS goes in a `<style>` block on that page only; promote into the shell only when it is universal, and update `COMPONENTS.md`. Add `<ul data-backlinks></ul>` to show who cites the page — lint populates it. Math is opt-in: add `/shell/math.js` and write `$…$` / `$$…$$`. Never hand-edit `nav.json`, `catalog.json`, `search-index.json` or `backlinks.json`.

## Authoring a paper

`content/papers/<slug>/main.tex`, with `figures/` beside it. Shared machinery — the preamble, the bibliography, and figure sources with their generators — lives in `assets/paper/` and is not duplicated per paper. Figures are SVG sources plus a generator; built PDFs are derived bytes and are **not tracked**. Every number in the prose cites a finding id in a comment or a footnote so the gate can see it.

## Before finishing

```bash
make check     # form lint (shell contract) + ladder lint (citations resolve) + book verify
make serve     # read it in the browser before you call it done
```

Fix everything both lints report. Then commit — records lane, only the files you touched plus what lint regenerated. Never `git add -A`.
