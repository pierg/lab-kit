---
name: address
description: >-
  Work through the comments readers left on rendered pages of a folio library, on
  the page each was left on. Questions get a reply and a state; flags rest until the
  owner acts; nothing is deleted; a decline gives its reason. Use when the user says
  "go through my comments", "address the comments", "answer my questions", "work
  through the feedback", "I left notes on the page", "resolve the annotations",
  "what is waiting for me", "review queue", or when `folio annotations list` shows
  open threads. Also used by write and organise before they edit, move or retire a
  document that has open questions.
---

# address

Answer each open comment on the document it was left on, and leave a reply that says what was done.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get`.
3. List what is available: `folio genres` and `folio workflows`.
4. List what is open: `folio annotations list`.
5. For each document with open threads, read its genre's card: `folio genre <name>`.

## Rules

1. Two kinds of thread exist. A question is a reader's ask and waits for you. A flag marks text an agent added beyond its sources and rests as `noted`.
2. Act on open threads only. Flags are the owner's to keep or change, including your own from earlier.
3. A flag the owner reopened with Change is an open thread. Its last reply is the instruction; follow it. A flag the owner kept is closed; leave it.
4. Never delete a thread, and never edit a comment file by hand. State moves only through `folio annotations`.
5. Every thread ends in one of two states: `addressed` or `declined`. Never mark a partial fix as addressed.
6. A decline gives its reason. The genre forbids it, the sources do not support it, or you believe it is wrong.
7. Read the whole document, not just the quote. The fix must stay in the genre's voice and shape.
8. A thread with no quote is about the whole document: its shape, genre or status. Answer it at that level.
9. A number in a reply cites its home. If nothing holds it yet, say so, and the thread stays open.
10. Reply as yourself, with `--author agent:<name>`, so the record shows who acted.

## Steps

1. **Show the queue.** If the library is served with comments, pull first: the server commits each comment, and a deployed one pushes it. If the request named nothing specific, tell the owner how many questions wait and how many flags rest, by document and label. The served Review page (`/content/review/`) shows the same list.
2. **For each open thread:** `folio annotations show <doc>`. Find the quoted passage in context.
3. **Decide.**
   - **Address it:** edit the document through the write skill. Then reply with what changed, precisely enough to check without a diff:
     `folio annotations reply <doc> <id> --author agent:<name> --state addressed --body "<what changed>"`.
   - **The document is permanent, or frozen in a `frozen_in` state:** never edit it. Through write, add a document that supersedes it, or a journal entry of kind `correction` or `retraction` about it. Reply with what you added, and mark the thread `addressed`.
   - **Decline it:** reply with the reason:
     `folio annotations reply <doc> <id> --author agent:<name> --state declined --body "<why>"`.
4. **Check other threads on the same document.** If your edit rewrote text another open question quotes, address that one too. The gate fails while an open question quotes text that is gone.
5. **Withdraw stale flags.** If your edit rewrote a passage under one of your own noted flags, withdraw it with `folio annotations reply <doc> <id> --author agent:<name> --state withdrawn --body "<the passage changed>"`. Flag the new passage if it still goes beyond the sources.
6. **Run the gate.** `folio index`, then `folio check`.
7. **Commit.** Add exactly: the documents edited or added, their annotation files (`<stem>.annotations.json`), and `.folio/`. Never `git add -A`. Commit each edited document together with its annotation file: the page's "What changed" compares the document at the commit that opened the thread with the commit that recorded your reply.
8. **Report** each thread in one line: the document, the question, and what you did.

## Stops

- A question asks for a fact you cannot source. Reply saying so and leave it open.
- A question asks for a change to the library's structure, a genre or the charter. Reply that it needs organise or configure, and ask the owner.
- Two questions ask for opposite changes. Reply to both and ask the owner which wins.

## Done when

- Every open question is `addressed` or `declined`, or left open with a reply that says why.
- Every flag is untouched, except your own stale ones, which are withdrawn.
- No thread was deleted.
- `folio check` passes, and the replies are committed.

## Commands

- `folio annotations list` shows open threads across the library.
- `folio annotations show <doc>` shows every thread on one document.
- `folio annotations reply <doc> <id> --author <who> [--state <state>] --body ".."` replies, and moves the thread to a new state.
- `folio genre <name>` prints the card for the document's genre.
- `folio index` regenerates the indices.
- `folio check` runs the gate.
