# Changelog — LIVE

In a lab, a kit re-sync is an instrument change: it lands as a pull request, never straight on `main`. Each release says what it changes for a lab and how to move across.

## 0.2.0 — 2026-09-22

lab-kit becomes a proper layer: it needs only content-kit's engine, and everything it adds to a lab's pages arrives through content-kit 0.4's extension points instead of being built into the engine. A lab renders exactly as before.

### Changed

- **Needs content-kit 0.4** (`ckit` ≥ 0.4.0, checked by `install.sh`). The engine is found through `--content-kit <checkout>`, `$CONTENT_KIT`, the `ckit` on PATH, or a sibling `../content-kit` — a sibling checkout is no longer required. `CONTENT_KIT_PIN` names the release this version is checked against.
- **`kit.json`**: the tools read it first and `lab.json` second; `$CKIT_ROOT` is honoured alongside `$LAB_ROOT`. The templates scaffold `kit.json`.
- **The lab's vocabulary moved here from content-kit** and is registered in `kit.json` by `install.sh`:
  - `genres` → `kit/lab/genres/genres_lab.json` — the `story` genre (after `project` in the sidebar, as before), the lab's front-door `project`, and a lab's sharper `concept` and `entry`; its voice in `kit/lab/genres/GENRES.md`
  - `checks` → `kit/tools/checks_lab.py` — `bound_ids`, `defn_no_findings`, `no_findings`, with planted fixtures
  - `refs` → `F-<n>` and `C-<n>` link into the ledger and anchor the record viewer's headings
  - `theme` → `kit/lab/shell/lab.css` (the story badge)
  - with `"dashboard": true` (on by default for a new lab): `generators` → `kit/tools/ladder.py` writes `content/ladder.json`; `shell_pages` → `/shell/dashboard.html`; `links` → the sidebar's Dashboard
- **The chronicle extractor declares its vocabulary**: `KINDS` (experiment · finding · claim · mission, in the hues the timeline always drew them) and `CARDS` (the Experiments tab, `?view=experiments`). It no longer imports the engine, so it runs standalone however content-kit is installed.
- **`kit/PIN`** records the kit's git URL and commit rather than a local path.

### Added

- **`example-lab/`**: a small synthetic lab — two locked pre-registrations, three finding rows with defense files, a claim, two sealed stories, a front door as home, a tagged logbook — green in strict mode. `make example` installs both kits into it and runs its gate; the e2e suite runs against it; `pages.yml` publishes it.
- The ladder lint and the chronicle extractor gain planted cases for `kit.json` (53 and 35).
- LICENSE (MIT), CONTRIBUTING, CODE_OF_CONDUCT, CI (`check.yml`, `pages.yml`).

### Migrating a lab from 0.1

On a branch — this is an instrument change:

```bash
git mv lab.json kit.json
bash /path/to/lab-kit/install.sh .          # re-vendors both kits and registers lab-kit in kit.json
ckit lint                                   # regenerate the indices
make check
```

If the lab's pages use content-kit 0.3's colour names (`--reach`, `sw-judge`, …), add content-kit's migration theme (see its CHANGELOG, 0.4.0) — `install.sh` keeps a theme the lab declares, after lab-kit's own stylesheet.

### Known limitation, recorded not fixed

The claims parser reads a claim's body up to the next `F-`/`C-` heading, so the last claim in `record/claims.md` also collects ids cited in any section after it (a "Gap list"). Changing it would change existing labs' dashboards, so it waits for a deliberate instrument change.

## 0.1.x — 2026-08-25 to 2026-09-16

The shared lab operating system, then a layer on content-kit: the discipline and the ladder, the ladder lint (`H1`–`H7`, `S1`–`S7`), cross-lab pinned citations and library mode, the chronicle extractor, the record-layering migration tool, the story pattern, and the agents and skills.
