# lab-kit — LIVE

**The shared operating system for a research lab repo.** One question per lab; everything a lab needs to answer it — the record ladder, the agent fleet, the gate, and the reader-facing pages — vendored into the lab folder so an agent session opened there has every rule locally, with no sibling repo to resolve first.

lab-kit is a layer **on top of [content-kit](../content-kit)**: content-kit owns the reader path (the shell, the genres and their voice, the craft playbooks, the `/present` and `/address` skills, the session-free annotation loop, the content gate); lab-kit adds what makes a repo a lab (the discipline, the record ladder and its lint, the fleet, the `/mission` `/experiment` `/review` skills). A library such as `folio` vendors content-kit alone. A lab vendors lab-kit and gets both.

## What a lab looks like

```
<lab>/
  README.md          the question, in one screen
  CLAUDE.md          the operating contract — imports @kit/DISCIPLINE.md + @kit/LADDER.md
  lab.json           name, question, content dir, port, ladder mode, engine pin, genre extensions
  kit/               ← vendored, pinned in kit/PIN (both kits), verified by the gate; never edited in place
    shell/ genres/ craft/ skills/{present,address}   from content-kit
    DISCIPLINE.md LADDER.md tools/ladder_lint.py agents/ skills/{mission,experiment,review}   from lab-kit
  .claude/           skills + agents, symlinked into kit/
  ops/               STATE.md (what is true now) · missions/ (append-only chronicle)
  lab/               the apparatus: substrate, harness, instruments, frozen tools
  experiments/<id>/  PROBE.md (locked) · bin/ · out/ · RESULTS.md
  record/            logbook/ · findings.md · claims.md · RETIRED.md · pins.json
  content/           the reader path — pages by genre in the shared shell, served on this lab's port
  assets/figures/    format-agnostic figure sources (SVG · generators · fonts · Makefile) — usable by pages, papers, or posts
  assets/paper/      LaTeX-only machinery: preamble.tex · references.bib
  Makefile           make check (the gate) · make docs (the port)
```

## Install

```bash
git clone … content-kit && git clone … lab-kit          # siblings
bash content-kit/install-engine.sh                        # `ckit` on PATH, once per machine
bash lab-kit/install.sh /path/to/lab --name "Harness Lab" --port 5182
cd /path/to/lab
make check     # the gate: content gate + ladder lint (warn mode at first)
make docs      # this lab's pages, on this lab's port
```

`install.sh` is idempotent: it re-vendors `kit/` from both kits and pins them, and scaffolds only what is missing — it never overwrites a file the lab already has. It finds content-kit beside this checkout, or at `CONTENT_KIT=…` / `--content-kit`.

## What's in it

| Path | What |
|---|---|
| `DISCIPLINE.md` | the shared operating contract — imported by each lab's `CLAUDE.md` |
| `LADDER.md` | the record ladder: evidence → probe → logbook → finding → claim → page/paper/post |
| `tools/ladder_lint.py` | **the ladder lint** — every published number traces to a finding |
| `skills/` | `/mission` · `/experiment` · `/review` (content-kit brings `/present` · `/address`) |
| `agents/` | `scout` · `reviewer` · `runner` · `reporter` |
| `templates/` | what `install.sh` scaffolds: `CLAUDE.md`, `PROBE.md`, `STATE.md`, the record files |

## The two ideas worth knowing

**The ladder converges, then fans out.** Evidence, probes and logbooks converge into findings, findings into claims — and claims fan out into a living page, a paper frozen at submission, and a post. Those three are siblings, not derivations: their prose is written independently, and what they share is the **finding ids they cite**, the figure sources, and the bibliography. You never sync a number between artifacts; you cite one, and `make check` verifies it. See `LADDER.md`.

**The kit is a frozen surface.** `make check` recomputes the vendored tree's hash and fails loud if it differs from `kit/PIN`. To change either kit you change it upstream and run `make kit-sync` in each lab. Editing `kit/` in place is how a shared kit becomes several different kits with the same name.

## Develop

```bash
make check     # the ladder lint's planted fixtures, plus an end-to-end install into a scratch lab (needs ../content-kit)
```
