---
name: set-up
description: >-
  Install a folio library in an existing project or a new repository, once.
  Asks at most three questions, writes the charter, creates the home page and the
  first journal entry, and runs the gate. Use when the user says "set up folio",
  "install folio", "start a library", "create a knowledge base here", "start my notes",
  "set up docs for this project", "make this a lab notebook", "initialise folio",
  "folio init", or pastes the folio setup prompt. If a library already exists here,
  use the configure skill instead.
---

# set-up

Create a library, write its charter, and leave it passing the gate.

## Start

1. Look for a library: a `folio.yaml` at or above the working folder. If one exists and was not just made by `folio init` for this setup, stop and use the configure skill. If it was, skip step 2 below.
2. Confirm the engine runs: `folio version`.
3. List what folio ships: `folio pack list` and `folio genres`. Both work before a library exists. Once it exists, read its charter (`folio config get`) and `folio workflows`.

## Rules

1. Ask at most three questions, all in one message. Skip any the request already answered, so setup takes one round.
2. Offer a default with every question. The user can answer "defaults" and be done.
3. Only this skill and configure write the charter, and only through `folio config set`, so every change is visible.
4. Switch on only the packs the user asked for. A library with no pack is complete.
5. Record the setup in the journal, so the library's first decision is on the record.
6. Leave the gate passing. A new library starts clean.

## Steps

1. **Ask the questions.** In one message, ask only what you do not know yet:
   1. What is it called, what is it for, and who reads it? Default: the folder's name, the owner's own notes, for the owner.
   2. Where should it live? Default: `docs/` in an existing project, or the root of a new repository.
   3. Which packs? Run `folio pack list` and give each pack's purpose in one line. Default: none.
2. **Create it.** For a new repository, create the folder and initialise version control there. Then run `folio init <dir> --name "<name>" --purpose "<one sentence>"`. It writes the charter, `content/`, `assets/`, the home page and a `.gitignore`, and installs the skills. The home page takes its title from the charter's `name`.
3. **Write the rest of the charter.**
   - `folio config set reader "<who reads it and what they know>"`
   - `folio config set voice "<house voice>"` only if the user gave one. The default is plain and precise.
   - `folio config set root "<path>"` only when the library is a folder inside a larger project whose files its documents point to, such as a lab's evidence. The path is relative to the library's folder.
4. **Switch on packs.** `folio pack on <name>` for each pack chosen.
5. **Add top-level maps, if named.** If the user named topics, create one map each through the write skill, and keep each `live`: a `draft` map cannot be a home map (check `home-maps`). Then set them on the home page: `folio config set home.maps "<a>, <b>"`. The shell draws them there, so the home page never lists them by hand. Otherwise leave home maps empty until a few documents exist.
6. **Record the setup.** `folio journal add --title "Library set up" --description "<one line: what the library is for>" --body "<the purpose, the reader, the packs and the location>" --kind decision --about home`. The entry is its own file under `content/journal/`, and it shows on the home page. It records the choices made here; `folio init` writes no journal entry, so this is the library's first.
7. **Run the gate.** `folio index`, then `folio check`. Fix what it names.
8. **Commit.** Add exactly `folio.yaml`, `.gitignore`, `content/`, `assets/` (its empty folders hold a `.gitkeep`), `.folio/`, and the installed skills (`.agents/skills/`, and the `.claude/skills` link). Commit with one line saying the library was set up.
9. **Tell the user, in two lines,** what they can now ask for. Example: "Your library is in docs/. Ask me to add a note, a concept or a map, to tidy the library, or to build the site."

## Stops

- A library already exists here: use configure.
- The user wants it somewhere outside the project or the repository you can write to: confirm the path first.
- `folio version` fails: the engine is not installed. Say so and give the install line from the setup prompt.

## Done when

- `folio.yaml` holds the name, purpose and reader, and any packs chosen.
- The home page exists, and a `decision` journal entry about it records the setup.
- The skills are in `.agents/skills/`.
- `folio check` passes, and the setup is committed.

## Commands

- `folio version` confirms the engine.
- `folio init [dir] --name ".." --purpose ".."` creates the library and installs the skills.
- `folio config get|set <key> [value]` reads and writes the charter.
- `folio pack list|on <name>` lists packs (before a library exists too) and switches one on.
- `folio genres` and `folio workflows` list what the library offers.
- `folio journal add --title ".." --description ".." --body ".." --kind decision --about home` records the setup.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
