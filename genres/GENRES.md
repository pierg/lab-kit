# A lab's genres — LIVE

content-kit's `GENRES.md` (vendored at `kit/genres/GENRES.md`) is the voice of every core genre. A lab adds one genre and sharpens three, and this file is their voice. The machine spec is `genres_lab.json` beside it, registered in `kit.json` `genres` by lab-kit's `install.sh`; `bound_ids` and `defn_no_findings` come from `kit/tools/checks_lab.py`, registered under `checks`. `ckit genres` lists the merged table.

What binds all of it is the ladder (`kit/LADDER.md`): no number enters a page except by citing a row of `record/findings.md`, and what may be said about it is bounded by `record/claims.md`.

## story — `content/stories/<slug>/index.html`

**Register.** Plain, and sealed to its findings. One result told once, in the order a stranger needs it: the question in words, why it was expected to help, what was done, what happened, what was learned, what it does not show, where to go deeper. It is written after the result is scored and then it stops moving — if one of its rows changes status the story is revised deliberately; nothing else touches it.

**Reader.** A sharp outsider who has never seen the lab. So no code, path or internal name is ever the subject of a sentence: ids ride beside the number they license, as links.

**Shape.** Eight fixed `<h2>` sections in one order — `question`, `why`, `did`, `happened`, `learned`, `not`, `deeper`, `backlinks` — so two stories read alike and a reader who has read one can skim the next. The opening line carries the date it was written and the rows it is sealed to; a pinned cross-lab row (`dsl:F-3`) counts as one of them. A story is **one page**: assets may sit beside it in the folder, but a second page there is a story too and is held to the whole contract — an arc over several results takes its own slug instead. *Checked: `require_sections` (every id present, in that order) and `bound_ids` (the opening line names a row) — the date is not checked, and neither is what the prose does with either; a reviewer reads those.*

**Forbidden.** A rolling narrative — a page that keeps being updated is live state wearing a story's hat. A number without its row id. A bound the rows carry that is missing from what-it-does-not-show. *Checked: none of these — the two checks hold the shape, and what the prose owes its rows is the reviewer's.*

**Promotion.** An arc over several results is not a ninth section: it is its own story, with the same eight, and the front door links both.

## project — `content/projects/<slug>/index.html` (and pages beside it)

**Register.** The front door. Plain sentences and links: what is being asked, what has been learned — one sentence per result, each ending in the rows it rests on and a link to its story — the top-level bounds, where things stand today, and why the work turned when it did. It points; the book teaches, the stories argue, the ledger proves. Explicitly perishable, and it says when it was last true.

**Reader.** Arriving cold and deciding what to read next, not yet inside the vocabulary.

**Shape.** `<meta name="status" content="active|shipped|paused">` for the catalog; a dated opening line; then asking · frame · learned · not · now · path · screens · glossary · evidence. The `now` section is dated and is **the one place in the content library where state lives** — everything else that moves is a link to the generated board. Sub-pages under the project folder (an ops board, a plan) share the genre.

**Forbidden.** Undated state. Re-explaining what a concept page or a story already owns. Carrying one result's conditions instead of the scope they all share. *Checked: `require_meta_status`; the section list is the skeleton's and the reviewer's, not the lint's — a front door may legitimately drop a section it has nothing to put in.*

## concept — sharpened

A lab's concept pages carry the core register, and one more check: the `blockquote.defn` cites no finding. Findings may be cited *below* the defn (why it matters here) but never inside it — the defn must survive the findings changing. *Checked: `defn_no_findings`.*

## entry — sharpened

Analytical, takes a position, and cites the findings it rests on **by id** — every number an `F-<n>` row, never a value quoted from another page.

## paper — as in the core, bound to the record

Every number in the paper cites a finding id in a comment or footnote, so the record gate (`kit/tools/ladder_lint.py`) can see it in the `.tex`.
