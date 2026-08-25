# lab-kit

**The shared operating system for a research lab repo.** One question per lab; everything a lab needs to answer it — the record ladder, the agent fleet, the gate, and the reader-facing pages — vendored into the lab folder so an agent session opened there has every capability and every rule locally, with no sibling repo to resolve first.

## What a lab looks like

```
<lab>/
  README.md          the question, in one screen
  CLAUDE.md          the operating contract — imports @kit/DISCIPLINE.md + @kit/LADDER.md
  lab.json           name, question, content dir, port, ladder mode
  kit/               ← vendored, pinned, verified by the gate; never edited in place
  .claude/           skills + agents, symlinked into kit/
  ops/               STATE.md (what is true now) · missions/ (append-only chronicle)
  lab/               the apparatus: substrate, harness, instruments, frozen tools
  experiments/<id>/  PROBE.md (locked) · bin/ · out/ · RESULTS.md
  record/            logbook/ · findings.md · claims.md · RETIRED.md · pins.json
  content/           the reader path — pages in the shared shell, served on this lab's port
  assets/paper/      shared LaTeX machinery: preamble · references.bib · figures + generators
  Makefile           make check (the gate) · make serve (the port)
```

## Install

```bash
bash install.sh /path/to/lab --name "Harness Lab" --port 5182
cd /path/to/lab
make check     # the gate
make serve     # this lab's pages, on this lab's port
```

`install.sh` is idempotent: it re-vendors `kit/` and pins it, and scaffolds only what is missing — it never overwrites a file the lab already has.

## What's in it

| Path | What |
|---|---|
| `DISCIPLINE.md` | the shared operating contract — imported by each lab's `CLAUDE.md` |
| `LADDER.md` | the record ladder: evidence → probe → logbook → finding → claim → page/paper/post |
| `shell/` | the HTML presentation form: `lib.css`, `lib.js`, `math.js`, `COMPONENTS.md`, skeletons, KaTeX |
| `engine/` | `serve.py` (per-lab port) · `lint.py` (form) · `book_nav.py` · `verify_book.mjs` · `check.sh` · `ctl.sh` |
| `tools/ladder_lint.py` | **the ladder lint** — every published number traces to a finding |
| `tools/kit_hash.py` | the content hash a lab pins, so a vendored kit cannot drift silently |
| `skills/` | `/mission` · `/experiment` · `/review` · `/present` |
| `agents/` | `scout` · `reviewer` · `runner` · `reporter` |
| `templates/` | what `install.sh` scaffolds: `CLAUDE.md`, `PROBE.md`, `STATE.md`, the record files |

## The two ideas worth knowing

**The ladder converges, then fans out.** Evidence, probes and logbooks converge into findings, findings into claims — and claims fan out into a living page, a paper frozen at submission, and a post. Those three are siblings, not derivations: their prose is written independently, and what they share is the **finding ids they cite**, the figure sources, and the bibliography. You never sync a number between artifacts; you cite one, and `make check` verifies it. See `LADDER.md`.

**The kit is a frozen surface.** `make check` recomputes the vendored tree's hash and fails loud if it differs from `kit/PIN`. To change the kit you change it here and run `make kit-sync` in each lab. Editing `kit/` in place is how a shared kit becomes several different kits with the same name.

## Develop

```bash
make check     # selftests for the ladder lint and the kit hash, plus an end-to-end install
```
