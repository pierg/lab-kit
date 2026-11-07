---
name: write
description: >-
  Add or revise any document in a folio library, in its genre's voice and format.
  It picks the genre, checks the fact has no home yet, writes from the sources,
  links concepts, cites by id, flags what goes beyond the sources, puts the document
  on a map, runs the gate and commits. Use when the user says "add", "write", "draft",
  "log", "record", "note down", "explain", "define", "revise", "rewrite", "update",
  "expand", "fix this page", "add a section", "write up", "turn this into a page",
  "add a concept for X", "log today's work", "revise section 3 of the paper", or names
  any document a genre in this library covers. Also used by every other skill and
  workflow that produces a document.
---

# write

Add a document to the library, or revise one in place, in its genre's voice and format.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get` (purpose, reader, house voice, packs, home maps, checks).
3. List what is available: `folio genres` and `folio workflows`.
4. Read the merged card for the genre in hand: `folio genre <name>`. Read it every time, even for a genre you have written before.

## Rules

1. The genre fixes the job, the voice, the format and the checks. A document never sets its own voice, so the library reads as one author.
2. The house voice in the charter sits under every genre's voice. Both apply.
3. One fact has one home. Search before you write, and cite the home instead of restating its value.
4. Write from the sources, never from another page, a summary or memory. A number quoted forward from a summary is a rumour.
5. Every number carries its source, as a citation by id. A reader can check it in one click.
6. Nulls are as prominent as wins. A failure, a drop or a dead end is stated as plainly, in the same place and voice.
7. Plain is not vague. "It did not help" is vague; "12 of 40 pass, against 14 yesterday" is plain and precise.
8. Codes are links, not content. An id, a path or a hash rides beside the sentence it supports and is never its subject.
9. Define a term once and link it everywhere. The second time a term needs explaining, it gets its own definition document, and every mention links to it with `class="defn-link"`.
10. Siblings share ids, figures and the bibliography, never sentences. A page, a report and a paper on the same fact each cite it in their own words.
11. Flag what goes beyond the sources. Your example, framing or general-knowledge claim gets a labelled flag, so the owner can review it at a glance.
12. Address open questions on a document before you edit it. An open question whose quoted text you rewrite fails the gate.
13. One paragraph per line. Never hard-wrap prose, because wrapped lines break quoting and diffs.
14. Use the shared shell's tokens only. No new colours, fonts or hex values, so pages work in light and dark.
15. Respect the card's `lives`. A `permanent` document, such as a journal entry or a result, is never edited once committed, and writes no `status`: the engine derives it. A `frozen` document is never edited once its status is in the card's `frozen_in`, except its `status` field.
16. Correct a record with a new document, never an edit. A newer record names the old one in `supersedes`. A retraction or a correction is a journal entry of kind `retraction` or `correction`, with the old document's id in `about`. The engine shows each as a banner on the document it names.
17. Metadata holds every fact the engine needs. Fill `title` and `description` (one line, in the genre's voice) in the metadata, and every field the card declares. Never write a fact into the body that the engine must read back out.
18. Never write what the shell draws or generates. The body has no `<h1>` and no subtitle: the shell draws the title, description, status, dates and tags. Never write a list of links that follows from the graph (what the document cites, what cites it, its journal entries, a guide's chapters, a record's status): the link panels show them.
19. Never write the charter, a generated index or a comment file by hand. Commands own them.
20. A new document is `live`. Skeletons write no status, except for a genre whose states have no `live` (it starts in its first state, such as a protocol's `draft`). Set `status` to `draft` only when the user asks to hold the document. A passage from general knowledge gets a flag (step 8); it never holds the document as a draft. To hold one, pass `--status draft` to `folio new`. Leaving `draft` means editing the `status` field.
21. Ids are unique across the library. `folio new` refuses a taken slug, so pick one that names this document, not its topic alone.
22. Commit each change. Lifecycles are checked against git, so a record is permanent only once committed.

## Steps

1. **Pick the genre.** Match the request to the genre whose job fits, using `folio genres` and each card's first line. Confirm it in one line. Ask only when two genres fit equally well.
2. **Check for a home.** Run `folio search <key words>` (add `--all` when the charter lists other libraries). If the fact or term already lives somewhere, revise that document or cite it. Do not create a second home.
3. **Gather the sources.** Read what the document will rest on: files, documents, data, the user's words. Note which claims each one supports.
4. **Open the document.**
   - New: `folio new <genre> <slug> --title "<title>" --description "<one line>" --tags <a,b> [--<field> <value>]`. `folio new --help` lists the fields a genre takes. A record genre with a prefix takes the next free id; give no slug. If the slug is taken, choose another. A new part of a multi-part document, such as a chapter: `folio new <genre> <slug> --part <part> <name>`.
   - Revise: open the file. First run `folio annotations show <doc>`. If a question is open, use the address skill on it before editing. If the card says `permanent`, or the document is in a `frozen_in` state, do not open it for editing: write a new document that supersedes it, or a journal entry that corrects or retracts it.
5. **Write it.** Follow the card's Reader, Voice and Shape. Fill the title, the description and every required field in the metadata, and every required part in the body. Start the body with content, never with its own title or subtitle. Replace every `{{...}}` placeholder, because the gate reports each one.
6. **Link and cite.**
   - Link each term that has a definition document with `class="defn-link"`.
   - Cite every other document by id. Run `folio cite <id>` to get its path and the right markup for this format.
   - A number cites the document that holds it. If nothing holds it yet, say so and leave the number out, or write its home first.
7. **Show it.** Ask what one figure carries the idea, and build the document around it. Lead with the figure, then the prose it cannot show.
   - A figure has one home in `assets/figures/`. Every document and paper embeds that same file.
   - Its alt text says what it shows. Its caption says what to look for, and carries the ids of what it draws.
   - One colour register per figure. Label every box, arrow and colour.
   - Nothing overflows at phone width. The words stay in the markup; a script may arrange them, never write them.
   - Use the reading column only when the material is a line of argument, not a structure.
8. **Flag additions.** For each passage that goes beyond its sources, add a flag:
   `folio annotations add <doc> --kind flag --label "<kind>" --quote "<passage>" --body "Added: <what and why>" --author agent:<name>`.
   Labels name the kind: "worked example", "framing", "general knowledge", "inference". A document drafted wholly from general knowledge stays `live`. It gets its flags and one document-level question asking the owner to check it: the same command with `--kind question`, without `--quote`.
9. **Ask only what needs an answer.** Open a question (`folio annotations add <doc> --kind question --quote "<passage>" --body "<question>" --author agent:<name>`) only where the owner's answer changes the document. More than three means one document-level question instead.
10. **Put it on a map.** Read the card's `on_map`. `required`: add a row. `optional`: add a row, or link the document from one that is already on a map. `never` and `exempt`: nothing to do. A row: `folio map add <map> <doc> [--reason "<why follow it>"] [--group "<heading>"] [--after <doc>]`. `folio maps` shows the maps. Place the row where a newcomer would want it. A reason is optional and one line, written for a reader choosing where to go; without one, the row shows the document's description.
11. **Record it.** When the change is worth a dated record, add a journal entry: `folio journal add --title "<title>" --description "<one line>" --body "<what changed, linking the documents touched>" [--kind <kind>] [--about <id>,..]`. Name the documents it concerns in `--about`, so it shows on each. Use a kind the library accepts. Each entry is a new file; never edit an old one.
12. **Check a long document.** Re-read it against its sources only. Check every number, id, verdict word and bound. Fix what does not match, then re-read.
13. **Run the gate.** `folio index`, then `folio check`. Fix everything it names and run it again.
14. **Commit.** Add exactly: the documents touched, their annotation files (`<stem>.annotations.json`), `.folio/`, and any assets or evidence the documents cite. Never `git add -A`. Commit with one line saying what changed.
15. **Report.** Tell the user, in a few lines, what changed, where it lives, and what flags or questions wait for them.

## Stops

- The request fits no genre, or two equally. Ask which, or offer the configure skill to add one.
- A number or claim has no source you can find. Ask for it; never invent one.
- The edit would rewrite a permanent document, or a frozen one in a `frozen_in` state. Say so and offer a new document that supersedes it, or a journal entry that corrects or retracts it.
- The fact already has a home that disagrees with the request. Show both and ask which is right.

## Done when

- The document meets its card: format, location, metadata and fields, required parts, limits, status words.
- Every number and fact cites its home, and every defined term links to its definition.
- Every addition beyond the sources carries a flag.
- The document is on a map, or linked from one, unless its card says it never is.
- `folio index` has run and `folio check` passes.
- The change is committed, with `.folio/`.

## Commands

- `folio config get` reads the charter.
- `folio genres` lists the genres and where each comes from.
- `folio genre <name>` prints the merged card.
- `folio workflows` lists the workflows.
- `folio search <words> [--all]` finds an existing home.
- `folio new <genre> <slug> [--part <part> <name>] [--title ..] [--description ..] [--tags ..] [--<field> ..]` creates a document, or a part, from its skeleton.
- `folio cite <id>` prints the path, title and citation markup.
- `folio maps` lists the maps and the documents on none.
- `folio map add <map> <doc> [--reason ".."] [--group ".."] [--after <doc>]` adds a map row.
- `folio annotations show|add <doc>` reads open comments and adds flags or questions; `add` without `--quote` is about the whole document.
- `folio journal add --title ".." --description ".." --body ".." [--kind <kind>] [--about <id>,..]` writes a new journal entry.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
