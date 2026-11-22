---
name: lab-pages
description: >-
  Keep the library's pages in step with the record, when the library keeps `pages.toml`: the session that answers
  a question revises, in the same sitting, the storyline pages that cite it, corrects a stable page only when it is
  wrong, and lands nothing a page reviewer has not passed. Use whenever a question is answered (`lab answer`), when
  a mission's result passes review, and when the operator says "update the pages", "revise the storyline",
  "rewrite the top page", "fix this page" or names a page of the library.
---

# lab-pages

This skill applies only when the library keeps `pages.toml` (`lab pages` says so). Without it, lab-work's rules
for the overview and the storylines are all there is.

The library sits above the record. The question cards (`lab show <id>`, served at `/lab/<id>/`) are the facts, and
no page repeats one. Every page has a kind in `pages.toml`:

| Kind | What it holds | When it changes |
|---|---|---|
| `storyline` | the argument: the top page, the result pages, what is new, what is not shown yet | when a question it cites is answered, or on request |
| `stable` | how the method works, and the words and objects every page leans on | only to correct an error, or when the method itself changes |
| `reference` | the overview (the full trail), the storyline's scope page, the appendices, the guide, the maps | as lab-work's rules for the overview and the storylines say |
| `retiring` | a page waiting to be merged into another and retired | never; finish the merge instead |

`lab check` holds the rest (docs/model.md, section 9, Pages): every page has a kind; every number a page quotes in a
`data-result` element is its card's, from reviewed results; no page but a retiring one uses a phrase `pages.toml`
drops or claims to be first without "to our knowledge"; every storyline and stable page has passed a page reviewer
as it now stands; every answer since `since` has reached its pages; each active storyline page links every storyline
page; and every link to a glossary term names a term the glossary has, with its definition as hover text.

## When a question is answered

1. Pull. Read `lab show <question>` and each of its steps' Found, Means and result names.
2. List the pages to revise: `lab pages cites <question>`, plus the same for every question its answer
   supersedes. Add the overview and the active storyline pages that `lab.toml` names (lab-work, The storylines and
   the overview). Revise nothing else.
3. If no storyline page cites the question, decide whether the answer belongs in the argument: a new item on the
   top page, a limit under an existing item, or a line under what is not shown yet. If it would change the thesis
   or drop an item, bring it to the operator with lab-talk instead of writing it.
4. Revise each listed page (How a page reads, below). Change only what the answer changes. A number that changed
   is changed everywhere it is quoted; `lab pages check` finds the quotes that disagree.
5. If the answer shows a stable page wrong, correct that sentence and nothing else, and say so where the library
   keeps its log ("correction").
6. Review (below). Once every page has passed, record that the answer reached the pages:
   `lab pages answered <question> "<the pages revised, or why none needed it>"`. It is refused while any storyline
   or stable page waits for a pass. Until this row exists, `lab check` fails on the answered question: that failure
   is expected before this step.
7. Run the lab's gate.
8. Land the answer, the pages, `page-reviews.tsv` and `answers-in-pages.tsv` together, as the lab's AGENTS.md says
   content lands. If the push is refused because another session changed the same page, rebase, merge the two
   edits, and have the merged paragraph read again.

A new storyline page is also linked from the active scope page (`lab.toml`'s `[storylines] active`), with the cards
it cites under included and the runs it leaves out under excluded; `lab check` fails on a storyline page the scope
page does not link.

The record is keyed by the question and the date on its `answered:` line. A question re-answered on the same day
is not due again: the session that re-answers it revises the pages all the same.

## On request

The operator names a page, or asks to revise the storyline. Follow step 4, then the review, then steps 7 and 8 for
the pages named, with no answer to record. A new page: write it in the page shape, give it a kind in `pages.toml`
and one place on a map, then review. Moving, renaming, merging or retiring a page is proposed to the operator as a
table (page, from, to, why) and done with the library's own commands only after their yes.

## Review

Every page you wrote or revised is read by a page reviewer who did not write it: start the `page-reviewer` agent
with only the page's path and the ids it cites. It checks each number and claim against the cards, the units, the
glossary's words and the lab's writing rules, and returns pass or a list of fixes. A page lands only on a pass.
Never review a page you wrote.

Fix rounds converge; they do not start over:

- The reviewer marks each fix **blocks** or **nit**. Everything its checklist finds blocks: a number or claim the
  cards do not support, a running step given as a result, a count without "k of n" or a bare percentage, an
  unhedged "first", a dropped phrase, a figure before its words, a term used undefined or defined when the glossary
  has it, a broken sentence, and any `lab pages check` line about the page other than the expected one. A nit is wording
  only.
- After a fail, make the fixes and send the page back to **the same reviewer** (continue that agent; do not start a
  new one). It finds what changed itself, by diffing the page against the copy it kept of the version it read (in
  its scratch folder, outside the repository and the store), not from your list. It re-checks each changed spot
  against the cards, runs `lab pages check` again, and re-checks the page-wide order (each term linked at its first use,
  each figure after its words). A change it did not ask for means it reads the whole page again.
- Rounds are counted per page. Nits may still be listed as fixes in the first and second readings; from the third
  reading of the page on (the first reading plus two fix rounds), the reviewer passes once nothing blocks, and
  lists the remaining nits briefly in its reply.
- If the original reviewer cannot be continued, a fresh reviewer reads the whole page, with the earlier lists of
  fixes and the number of readings so far in hand; the count carries over. A pass is recorded only by a reviewer
  that has every earlier fix in hand.

The reviewer records its pass in `page-reviews.tsv` (`lab pages passed`), with a fingerprint of the page as it read
it; the writer never records one. `lab check` fails on a storyline or stable page that no recorded pass matches, so a
page is read again only when its text changes, and never when it has not. `lab pages` lists every page and whether
its last change was passed. Commit `page-reviews.tsv` with the page.

## How a page reads

Follow the lab's own writing rules (its AGENTS.md says where they are) and lab-work's page style. On top of them:

- **The top page**, in this order: the problem; the one contribution; a map of the results on one screen, each with
  its count; one short block per item with its claim, one figure, its count, its limit and one link to its page;
  what is not shown yet.
- **Every other page**, in this order: a title that states the claim; the question in one sentence; the answer in
  one bold sentence; one example worked by hand; one figure after the words that name its parts; the count and its
  honest limit; a record box at the foot with the ids, linked. Ids appear nowhere else on the page, except in an
  active storyline page's scope table, which lab-work fills with id links.
- **Numbers.** Write "k of n" with what n is, never a bare percentage. A storyline page carries
  `<meta name="numbers" content="tagged">`, and every number on it from a card sits in an element naming its result:
  `<span data-result="G1.Q1.4:proved+proved-late">96 of 96</span>`. Names joined by `+` are summed and by `*`
  multiplied, so a share times its total gives a count; a single result read as a percent is compared as one. The
  first number the element shows is compared, after rounding the card's value to as many decimals as the page shows.
  A number that is not a result (a definition, a count of what is studied) sits in an element marked `data-plain`;
  the total in "k of n", a year, and a number right after a word `pages.toml` lists under `names` need neither.
- **Definitions live in the glossary.** The lab defines each word once, in `GLOSSARY.md`, served at
  `/lab/glossary/`. A page never defines a term the glossary has: it links the term's first use on the page to its
  entry, `<a class="term" href="/lab/glossary/#error-ratio">error ratio</a>`, then runs `lab pages terms`, which
  writes the entry's definition into the link as hover text. The anchor is the entry's heading in lower case with
  spaces as hyphens; a word of the page that is not a heading is listed under the entry's `- also:`. A word the
  glossary lacks is added to `GLOSSARY.md` first, in the lab's words, then linked. A page explains only what is
  particular to it. The hover text is left out of a page's fingerprint, so a changed definition asks for no new
  review.
- **Words.** The glossary's terms as it defines them; none of the phrases `pages.toml` drops; "first" only as "to our
  knowledge", naming the closest published work.
- **Running work.** A step still running has no result on any page; it may appear under what is not shown yet.

## Never

- A page that repeats a question card.
- A number on a storyline page without its `data-result`.
- A stable page reframed to fit a new result.
- A card, a decision or a locked plan changed to fit a page.
- A pass recorded by the session that wrote the page.
