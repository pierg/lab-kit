---
name: run
description: >-
  Follow a workflow from a pack or the library, step by step. Every document it
  produces goes through the write skill, and it stops where the workflow says. Use
  when the user says "run", "run the workflow", "what workflows are there", "add this
  paper", "ingest this", "file this link", "quiz me", "test me", "record this result",
  "write the report", "do the usual for this", or asks for any procedure a listed
  workflow covers.
---

# run

Carry out one workflow, step by step, producing every document through the write skill.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get`.
3. List what is available: `folio genres` and `folio workflows`.
4. For each genre the workflow produces, read its card: `folio genre <name>`.

## Rules

1. The workflow is the procedure. Follow its steps in order, and skip none.
2. Every document goes through the write skill, with its card and the gate. Never write one by hand.
3. Stop where the workflow says to stop, and ask the owner. Do not guess past a stop.
4. Take every input the request already gives, and any `from` file it names. Ask once, before starting, in one message, only for required inputs still missing. Never ask for an input marked optional.
5. The library's own workflow wins over a pack's, and a pack's over the core's. `folio workflows` shows which one is in force.
6. A request no workflow covers is not a run. Use write for one document, or offer configure to add a workflow.

## Steps

1. **Pick the workflow.** Match the request to a workflow's summary in `folio workflows`. Confirm it in one line. Ask only if two fit.
2. **Read it whole** before acting: `folio workflows --json` gives its path. Note its inputs, steps, stops and what it produces.
3. **Gather the inputs.** Take them from the request and any `from` file. Ask in one message only for required inputs still missing.
4. **Follow each step in order.**
   - A step that makes or revises a document: use the write skill.
   - A step that names a command: run it and check its output.
   - A step that names another skill: use that skill.
   - After each step, say in one line what it produced.
5. **Honour the stops.** When a stop applies, report where you are, what is done, and the question. Wait.
6. **Record it,** if the workflow says to: `folio journal add --title ".." --description ".." --body ".." [--kind <kind>] [--about <id>,..]`, through the write skill. Name the documents the run produced in `--about`.
7. **Run the gate.** `folio index`, then `folio check`.
8. **Commit,** last, unless the workflow commits in its own steps. Add exactly: the documents the run produced or touched, their annotation files (`<stem>.annotations.json`), `.folio/`, and any assets or evidence the documents cite. Never `git add -A`.
9. **Report** what the workflow produced, with each document's path, and any flags or questions left for the owner.

## Stops

- No workflow fits the request.
- An input is missing and the user has not given it.
- The workflow's own stops.
- A step fails and its fix is not obvious from the output.

## Done when

- Every step ran in order, or the run halted at a stop with a report.
- Every document produced went through write.
- The workflow's own "Done when" holds.
- `folio check` passes, and the run is committed.

## Commands

- `folio workflows [--json]` lists workflows, where each comes from, and its path.
- `folio genres` lists the genres.
- `folio genre <name>` prints a merged card.
- `folio journal add --title ".." --description ".." --body ".." [--kind <kind>] [--about <id>,..]` writes a new journal entry.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
