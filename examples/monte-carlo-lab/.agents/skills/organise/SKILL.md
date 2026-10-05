---
name: organise
description: >-
  Reorganise a folio library without breaking it: move, rename, merge, promote and
  retire documents and maps, keep maps current, tidy tags, and run health passes,
  with every link, comment, id and date kept. Use when the user says "organise",
  "reorganise", "tidy", "clean up", "tidy the maps", "merge these", "merge these topics",
  "split this map", "rename this page", "move this", "promote this note", "retire this",
  "this is a duplicate", "fold this into that", "clean up the tags", "what is on no map",
  "is the library healthy?", "health check", or "fix what the new pack flagged".
---

# organise

Change where documents live and how the maps reach them, with every link, comment and date intact.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get`, especially the home maps and packs.
3. List what is available: `folio genres` and `folio workflows`.
4. Look before acting: `folio maps`, `folio tags` and `folio check`.
5. When a document changes genre, read the target card: `folio genre <name>`.

## Rules

1. Move, promote and retire only through `folio mv`, `folio promote` and `folio rm`. A plain file move breaks links, comments and dates.
2. Never move a document with a version-control move command, for the same reason. `folio mv` and `folio promote` stage the rename in git themselves.
3. Settle open questions on a document before you move, merge or retire it. Use the address skill.
4. Prose changes go through the write skill. This skill changes places, not words.
5. A map row links a document. Give it a one-line reason only when this map's reader needs one; without it, the row shows the document's description.
6. Tags are facets for filtering, never structure. Structure lives in maps.
7. Structural changes are the owner's call: a new top-level map, a merge, a retirement of their own writing. Propose, say why, and act when asked.
8. Record every reorganisation as a journal entry of kind `decision`, old names to new, about the documents and maps it touched.

## Steps

Pick the change, then follow its line.

1. **Move or rename a document:** `folio mv <doc> <to>`. Links are rewritten and dates kept. A committed document keeps its id, and its old address redirects. A document never committed takes the new slug as its id, with no redirect, so a move is how to fix a slug before the first commit.
2. **Promote a document** that has outgrown its genre (for example, a short note that grew sections): `folio promote <doc> <genre>`. Then revise it in the new genre's voice through write.
3. **Merge two documents:** pick the one to keep. Fold the other's surviving content into it through write. Then `folio rm <other> --to <kept>`.
4. **Fold a thin definition** into the document that uses it: same as a merge. A term earns its own definition document only when it is transferable, non-trivial and cited.
5. **Retire a document:** `folio rm <doc> --to <replacement>`. Its links and address go to the replacement. It prints a `review:` line for every link whose text still names the retired document's title. Review each one, and reword through write any that no longer fits. Only a genre whose card lists `retired` can be retired. A record that was wrong stays at its address under its own states instead: a result is superseded or retracted through write.
6. **Maps.**
   - A new map: create it through write. Rows go in with `folio map add <map> <doc> [--reason ".."] [--group "<heading>"] [--after <doc>]`, in the order a newcomer reads them.
   - Merge two maps: add the other map's rows to the one you keep with `folio map add`, then `folio rm <other> --to <kept>`.
   - Split a map: create the new map through write, add the rows that move with `folio map add`, and remove them from the old one with `folio map rm <map> <doc>`.
   - Home maps change only through the configure skill.
7. **Tags:** `folio tags` lists them. Merge spellings that look alike with `folio tags rename <old> <new>`. A tag on one document earns a second or goes.
8. **Pack fixes:** after a pack is switched on, `folio check` names what its rules flag. Propose one fix per document, and apply each the owner approves through this skill or write.
9. **Health pass**, when asked or after a large change:
   1. `folio check` passes.
   2. Orphans: `folio maps` lists documents on no map. Add each to a map, or link it from one.
   3. Thin documents: fold them into the document they belong to.
   4. Duplicates: `folio search` for each key term. Two homes for one fact become one.
   5. Stale maps: a map whose opening take predates most of its rows gets a revision through write.
   6. Drafts left for weeks: finish them through write, or propose retiring them.
   7. Open comments: `folio annotations list`. Hand them to the address skill.
   8. Report what you found, what you changed, and what is left for the owner.
10. **Record it.** `folio journal add --title "<change>" --description "<one line: what moved and why>" --body "<old names and new>" --kind decision --about <id>,..`.
11. **Run the gate.** `folio index`, then `folio check`.
12. **Commit.** `folio mv`, `folio promote` and `folio rm` stage in git every file they moved or changed, annotation files included. Add only the new journal entry and `.folio/` (which holds the redirects), then commit. Never `git add -A`.

## Stops

- A retirement or merge would remove the owner's own writing. Ask first.
- A move would change a top-level map. Hand it to configure.
- Two documents look like duplicates but disagree on a fact. Show both and ask which holds.
- A document has an open question you cannot answer. Leave it in place and report it.

## Done when

- Every moved, promoted or retired document keeps its id, comments and dates, and its old address redirects.
- Every document except a journal entry is on a map, or linked from one that is.
- Every row links a document that exists, and every top-level map is reachable from home.
- The journal records each reorganisation.
- `folio check` passes, and the change is committed.

## Commands

- `folio maps` lists the maps, their rows, and documents on none.
- `folio map add <map> <doc> [--reason ".."] [--group ".."] [--after <doc>|<heading>]` adds a map row (`--after <heading>` with a new `--group` puts the group after that one); `folio map rm <map> <doc>` removes one.
- `folio mv <doc> <to>` moves a document and rewrites its links.
- `folio promote <doc> <genre>` changes a document's genre.
- `folio rm <doc> --to <doc>` retires a document into another, and names the links whose text to review.
- `folio tags [rename <old> <new>]` lists or renames tags.
- `folio search <words>` finds duplicates.
- `folio annotations list` shows open comments.
- `folio journal add --title ".." --description ".." --body ".." --kind decision --about <id>,..` records the change.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
