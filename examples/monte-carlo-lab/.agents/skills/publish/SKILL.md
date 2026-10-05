---
name: publish
description: >-
  Export a folio library as a static site, and build a paper or freeze a version of it. Runs the
  gate first and never deploys anywhere unless the user asks and names where. Use
  when the user says "publish", "build the site", "export the site", "make a static
  site", "get this ready for Pages", "build the paper", "compile the paper", "make the
  PDF", "freeze the paper", "freeze it for submission", "snapshot this version", or
  "preview the library".
---

# publish

Write the library as a static site, or build a paper and freeze a version of it, from a library that passes the gate.

## Start

1. Find the library: the nearest `folio.yaml` at or above the working folder.
2. Read the charter: `folio config get`.
3. List what is available: `folio genres` and `folio workflows`.
4. For a paper, read its genre's card: `folio genre <name>`.

## Rules

1. The gate passes before anything is published. A broken link on the site is a broken link for every reader.
2. Publishing writes files. It never uploads, pushes or deploys unless the user asks and names the place.
3. Exported files are build products. Never edit them; fix the source and export again.
4. A paper's source, `main.tex`, stays revised. A frozen version, `versions/<name>/`, is never edited once committed: a change goes into the source and is frozen as a new version. A mistake found in a version is a journal entry of kind `correction` about the paper, through write.
5. Status decides what shows. Drafts stay off the home page, and retired documents redirect to their replacements.

## Steps

1. **Run the gate.** `folio index`, then `folio check`. If it fails, stop, report the problems, and offer the skill that fixes each.
2. **Preview, if asked.** `folio up` serves the library locally in the background. `folio down` stops it.
3. **Export the site.**
   - `folio export --out <dir>`. The default folder is fine unless the user names one.
   - For a site served under a sub-path (for example, a project page on a static host), add `--base /<path>/`.
   - Export prints the number of pages and the folder. Report both, and how to open the home page.
   - Export leaves out kept originals (`original.*` in a source's folder) and annotation files. Never copy them into the site by hand: a kept original is a private copy.
   - An exported site takes no comments. When others should comment, serve the library instead: `folio serve --host <address> --push` behind a sign-in proxy, with `comments.identity_header` in the charter (set through configure).
   - A result's evidence is not exported with it. The result page shows the evidence path, and the evidence stays in the repository, where `rederive` reads it. Only a file that sits under `assets/` reaches the site, as any asset does.
4. **Build a paper.** `folio paper build <slug>`. It compiles with latexmk in `.folio/build/<slug>/` and prints the PDF's path; report it. Every `\fcite` must resolve and every figure must come from `assets/figures/`. If latexmk is missing, say so and stop: the user installs a TeX distribution. `folio up` and `folio export` then publish the build as the paper's current PDF.
5. **Freeze a version,** only when the user asks. Confirm the version name first (`folio paper versions <slug>` lists the earlier ones), then `folio paper freeze <slug> --version <v>`. It builds the paper and copies `main.tex` and the PDF into `content/papers/<slug>/versions/<v>/`. It writes no journal entry, so record it here: `folio journal add --title "Froze <paper> <version>" --description "<one line: what was frozen and for what>" --body ".." --kind decision --about <slug>`. Then `folio index`, `folio check`, and commit exactly the version's folder, the journal entry and `.folio/` (the indices; `.folio/build/` stays out of git). The version is permanent from that commit on.
6. **Deploy, only if asked and the place is named.** Use the user's own tool for that place. Report the address it is live at.

## Stops

- `folio check` fails. Report and stop.
- The user asks to deploy but names no place. Ask where.
- The version name is taken. `folio paper freeze` refuses it; ask for a new name.
- latexmk is not installed. Say so and stop.
- The paper does not compile. Report the first error and stop.

## Done when

- `folio check` passed before the export or build.
- The site is in the export folder, or the paper's output file exists.
- A frozen version's folder holds `main.tex` and `paper.pdf`, is committed, and a journal entry about the paper records the freeze.
- Nothing left the machine unless the user asked and named the place.

## Commands

- `folio check` runs the gate.
- `folio index` regenerates the indices.
- `folio up` / `folio down` serve and stop a local preview.
- `folio export [--out dir] [--base /path/]` writes the static site.
- `folio paper build <slug>` compiles a paper.
- `folio paper freeze <slug> --version <v>` freezes a version of a paper.
- `folio paper versions <slug>` lists a paper's versions.
- `folio journal add --title ".." --description ".." --body ".." --kind decision --about <slug>` records a freeze.
