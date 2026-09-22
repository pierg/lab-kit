# lab-kit — LIVE

**The record discipline for agent-run research labs.** One question per lab. A pre-registration locked by commit before any measurement. An append-only record. Finding rows as interfaces, each with a defense file. Claims that bound what may be said. A reviewer that is read-only by construction. A lint that fails when a published number has no row. And the pages a lab writes live beside the evidence they cite.

lab-kit is a layer on [content-kit](https://github.com/pierg/content-kit): content-kit writes the pages (genres, the shell, the gate, the review loop); lab-kit decides which numbers those pages are allowed to say. Its vocabulary — the story genre, the record-id checks, the dashboard, the chronicle's experiments — reaches content-kit only through its extension points, so the engine never learns what a finding is. A lab that writes only a paper can use lab-kit without a single HTML page.

**Example lab:** [`example-lab/`](example-lab/) — a small, complete, synthetic lab, green in strict mode, published at <https://pierg.github.io/lab-kit/>. It is the test fixture, the demo and the documentation at once.

## Install

```bash
uv tool install git+https://github.com/pierg/content-kit@v0.4.0   # the engine, ckit — the only requirement
git clone https://github.com/pierg/lab-kit
bash lab-kit/install.sh /path/to/lab --name "My lab" --port 5181
cd /path/to/lab
make check     # the gate: the content gate + the ladder lint (warn mode until you say strict)
make docs      # the lab's pages on its own port
```

`install.sh` is idempotent: it vendors both kits into the lab's `kit/`, pins them in `kit/PIN`, registers lab-kit in `kit.json`, and scaffolds only what the lab is missing. It finds content-kit's engine through `--content-kit <checkout>`, `$CONTENT_KIT`, the `ckit` on PATH, or a sibling `../content-kit` checkout — no sibling is required. `make kit-sync` re-vendors later (`LAB_KIT=/path/to/lab-kit` if the checkout is not beside the lab).

## What a lab looks like

```
<lab>/
  README.md          the question, in one screen
  CLAUDE.md          the operating contract — imports @kit/DISCIPLINE.md and @kit/LADDER.md
  kit.json           name · question · ladder mode · engine pin · the layer's registrations
  QUESTIONS.md       what is open, each question with its kill criterion
  ops/               STATE.md (what is true now) · missions/ (append-only)
  experiments/<id>/  PROBE.md (locked) · bin/ · out/ (the evidence, never edited)
  record/            findings.md · findings/F-<n>.md (each row's defense) · claims.md · logbook/ · LESSONS.md · pins.json
  content/           the reader's pages: stories/ (one sealed page per result) · projects/ (the front door) · …
  kit/               vendored, pinned, never edited in place — content-kit's shell and genres, plus:
    DISCIPLINE.md LADDER.md MIGRATION.md
    tools/           ladder_lint.py · chronicle_lab.py · checks_lab.py · ladder.py · layer_findings.py
    lab/             genres/ (the story genre, the front door) · shell/ (the dashboard, the lab's stylesheet)
    agents/ skills/  scout · reviewer · runner · reporter · /mission · /experiment · /review
```

## What lab-kit registers in content-kit

| Extension point | What |
|---|---|
| `genres` | `kit/lab/genres/genres_lab.json`: the `story` genre (eight fixed sections, sealed to its rows) and the lab's front door (`project`) |
| `checks` | `kit/tools/checks_lab.py`: `bound_ids`, `defn_no_findings`, `no_findings` |
| `chronicle.extractors` | `kit/tools/chronicle_lab.py`: experiment · finding · claim · mission events, and the Experiments cards |
| `refs` | `F-<n>` and `C-<n>` become links into the ledger (a pinned `<lab>:F-<n>` is left alone) |
| `theme` | `kit/lab/shell/lab.css`: the story badge |
| `generators` · `shell_pages` · `links` | with `"dashboard": true`: `kit/tools/ladder.py` writes `content/ladder.json`, served by `/shell/dashboard.html`, linked from the sidebar |

## The two ideas worth knowing

**The ladder converges, then fans out.** Evidence, probes and logbooks converge into findings, findings into claims — and claims fan out into a living page, a paper frozen at submission, and a post. Those three are siblings, not derivations: their prose is written independently, and what they share is the **finding ids they cite**, the figure sources, and the bibliography. You never sync a number between artifacts; you cite one, and `make check` verifies it. See [`LADDER.md`](LADDER.md).

**The kit is a frozen surface.** `make check` recomputes the vendored tree's hash and fails loud if it differs from `kit/PIN`. To change either kit you change it upstream and run `make kit-sync` in each lab — and in a lab, that re-sync is an instrument change, landed as a pull request. The ladder lint is an instrument: an upgrade must never change the judgment of results already taken.

## Develop

```bash
make check     # every tool's planted fixtures · the example lab's gate in strict mode · an end-to-end install
```

`CONTENT_KIT_PIN` names the content-kit release this version is checked against; CI installs exactly that. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CHANGELOG.md`](CHANGELOG.md). MIT licensed.
