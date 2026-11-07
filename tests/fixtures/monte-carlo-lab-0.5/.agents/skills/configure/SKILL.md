---
name: configure
description: >-
  Change what a folio library is: its charter, genres, variants, workflows, packs,
  home maps and check severities. Shows every change as a diff and records it as a
  decision in the journal. Use when the user says "configure", "change the settings",
  "switch on the lab pack", "turn off a pack", "add a genre", "add a meeting-note type",
  "make concepts shorter", "entries should open with a verdict", "add a variant for
  newcomers", "papers follow this style", "add a workflow", "group these into a pack",
  "put these maps on the home page", "make this check an error", "only warn about that",
  "change the voice", "change the theme", "search my other library too", or "who is
  this library for".
---

# configure

Change the charter, or the genres, workflows and packs the library holds, and record each change.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get`.
3. List what is available: `folio genres`, `folio workflows`, `folio pack list`.
4. For a change to a genre, read its merged card: `folio genre <name>`.

## Rules

1. Change only what was asked. A smaller change is easier to review and to undo.
2. Show every change as a diff. If the request named the exact change, apply it and show the diff. Otherwise show the proposed diff and wait.
3. An override holds only what it changes. The card underneath still applies, so upgrades still reach the rest.
4. A variant extends a genre for a second audience. It states only what differs, usually voice, reader and limits.
5. Names stay unique across the core, every pack and the library. Nothing may shadow another genre by name.
6. A pack never redefines a core genre. If a pack needs a core genre to read differently, it ships a variant with its own name.
7. Never edit documents here. Documents a change affects go to the organise skill, which proposes the fixes.
8. Record every change as a journal entry of kind `decision`, so the library's history explains its shape.

## Steps

1. **Name the change** in one line and pick its kind below.
2. **Make it.**
   - **Purpose, reader, voice, theme, assets, root, other libraries to search:** `folio config set <key> "<value>"`.
   - **A journal kind:** `folio config set journal.kinds "<a>, <b>"`, the full list of the library's own kinds. The core's and the packs' kinds need no entry.
   - **Home maps:** `folio config set home.maps "<a>, <b>"`, in reading order. Each must be an existing map that is not a `draft`; run `folio maps` to check. If one is a draft, warn the user and set it live through the write skill first.
   - **The library's name:** `folio config set name "<name>"`. The home page takes its title from it, so nothing else changes.
   - **Check severity:** `folio config set checks.<check> error` or `warning`.
   - **A genre setting the charter holds** (switched off, a word limit): `folio config set genres.<name>.<key> <value>`.
   - **A change to a genre's card** (voice, shape, a required part, a step): run `folio genre override <name>` and edit `genres/<name>/GENRE.md` in the library. Put in it only the front matter keys and body sections that change. Then run `folio genre <name>` and show the merged card.
   - **A new genre:** run `folio genre add <name>` to scaffold it. Ask what the document is for, who reads it and how it sounds. Fill `genres/<name>/GENRE.md` in the full card shape, and a skeleton that is a valid document with placeholders. Set its format, path, id, lives, states, any `frozen_in` and `frozen_exits` states, any fields, checks and on_map. The skeleton writes `{genre}` for its genre and no status. Declare a field only when the engine renders, filters or checks it; everything else is body prose. Never require `h1` or a subtitle: the shell draws the header from metadata. Use only check names from the registry the engine ships (`checks.md`).
   - **A variant:** `folio genre add <variant> --extends <genre>`, then fill its `GENRE.md` with only what differs. A body section it states replaces the parent's section of that heading whole, so a changed `## Forbidden` restates every item it keeps. Give it a skeleton only if its shape differs. `folio new <variant>` writes the variant's name either way.
   - **An override:** `folio genre override <name>` scaffolds it; then fill in only what changes, as above.
   - **A workflow:** `folio workflow add <name>`, then fill `workflows/<name>.md` with its front matter (name, summary, inputs, produces) and its Steps, Stops and Done when. Every step that makes a document names the write skill.
   - **Switch a pack on:** `folio pack on <name>`. Then run `folio check`, report what its rules flag in existing documents, and offer the organise skill for the fixes.
   - **Switch a pack off:** `folio pack off <name>`. Its genres and workflows leave new work. Existing documents stay valid.
   - **Group genres into a pack:** `folio pack add <name> --genres <a,b> --workflows <c>`. It writes `packs/<name>/` with a `PACK.md` and moves the genres and workflows into it. Move any rules and journal kinds into it by hand. Then `folio pack on <name>`.
3. **Show the diff** of every file the change touched.
4. **Record it.** `folio journal add --title "<what changed>" --description "<one line: the change and why>" --body "<the old value, the new value and the reason>" --kind decision [--about <map or document touched>]`.
5. **Run the gate.** `folio index`, then `folio check`. A tighter check may now flag documents. Report them, and hand the fixes to organise or write.
6. **Commit.** Add exactly the files the change touched (`folio.yaml`, `genres/<name>/`, `workflows/<name>.md`, `packs/<name>/`), the new journal entry, and `.folio/`. Never `git add -A`.

## Stops

- The change would rename, remove or redefine a genre that existing documents use. Show the documents affected and ask first.
- A new genre's job overlaps an existing one. Show the overlap, and ask whether a variant or an override would do.
- A pack is pinned by URL. Confirm the source and the exact commit before adding it.
- Turning a check to `error` would fail many documents at once. Report the count and ask.

## Done when

- The charter, override, genre, variant, workflow or pack holds exactly the change asked for.
- `folio genre <name>` shows the merged card as intended, for any genre touched.
- A new journal entry of kind `decision` holds the old value, the new value and the reason.
- `folio check` passes, or every failure it names is reported with a proposed fix.
- The change is committed.

## Commands

- `folio config get|set <key> [value]` reads and changes the charter.
- `folio genres` lists genres and where each comes from.
- `folio genre <name>` prints the merged card.
- `folio workflows` lists workflows and where each comes from.
- `folio pack list|on|off [name]` lists and switches packs.
- `folio pack add <name> --genres .. --workflows ..` makes a pack from library genres.
- `folio genre add <name> [--extends <parent>]` scaffolds a genre or a variant; `folio genre override <name>` scaffolds an override.
- `folio workflow add <name>` scaffolds a workflow.
- `folio maps` lists the maps.
- `folio journal add --title ".." --description ".." --body ".." --kind decision [--about ..]` records the change.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
