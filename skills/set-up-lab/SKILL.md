---
name: set-up-lab
description: >-
  Turn a repository into a research lab run by lab-kit, once: a folio library with the lab pack,
  the lab's files, its question as Q-1, its frozen surfaces, its operating guide, CI and a passing gate.
  Asks at most three questions in one message. Use when the user says "set up a lab", "make this a lab",
  "start a lab for <question>", "install lab-kit", "lab-kit init", or pastes the lab-kit install prompt.
  If `lab.yaml` already exists here, the lab is set up: use the plan-mission or run-mission skill instead.
---

# set-up-lab

Create the lab's library and files, record its question, and leave `lab-kit check` passing.

## Start

1. Look for `lab.yaml` at or above the working folder. If one exists, the lab is set up: stop. Use the plan-mission skill for a new objective, or the run-mission skill for an approved one.
2. Confirm both engines run: `lab-kit version` and `folio version`. Installing `lab-kit-cli` brings folio as a dependency, but a tool installer may not put the `folio` command on the path. If `folio version` fails, install it too: `uv tool install folio-kb` or `pipx install folio-kb`.
3. Confirm this skill is in `.agents/skills/set-up-lab/`. If it is not, run `lab-kit init` once with no arguments: before a library exists, it installs only lab-kit's method, skills and roles.
4. Look for a library: a `folio.yaml` in the repository root or in `docs/`. If one exists, reuse it: skip the location question, and in step 3 below run only the parts of folio's set-up skill it lacks.

## Rules

1. Ask at most three questions, all in one message, each with a default. Skip any the request already answered, so setup takes one round.
2. Every document goes through folio's skills: set-up for the charter, write for the front door and the question. Never write a document by hand.
3. The library's `root` is the repository root, so a result's paths and lab-kit's paths are read from the same place. `lab-kit init` refuses otherwise.
4. Only the operator names frozen surfaces. Never freeze a path the operator did not name.
5. Record the setup once, in one journal entry of kind `decision`, so the lab's first decision is on the record.
6. Do not run an experiment, spend tokens on a live run, or push anything. Setup ends at a passing gate and a commit.

## Steps

1. **Ask the questions.** In one message, ask only what you do not know yet:
   1. What is the lab's question, in one sentence? And its name? Default name: the repository's folder name.
   2. Where should the library live? Default: `docs/`, with the lab's files at the repository root. The other choice is the repository root itself.
   3. Which paths, if any, are frozen surfaces: inputs no one may edit in place, such as a vendored benchmark or a dataset? Default: none.
2. **Make sure it is a repository.** If the folder is not inside a git work tree, run `git init`. folio installs its skills at the work tree's root, beside lab-kit's.
3. **Create the library with folio.** Run `folio init <dir> --name "<name>" --purpose "<the question, in one sentence>"`. It writes the charter, the home page and folio's seven skills. Then read `.agents/skills/set-up/SKILL.md`, folio's set-up skill, and follow it for the rest of the charter, with these answers:
   - the reader: whoever will read the lab's results, and what they already know;
   - the pack: `lab`;
   - `root`: `..` when the library is in `docs/`, nothing when it is the repository root.

   Skip its journal entry and its commit: step 10 records and commits the whole setup once.
4. **Install the lab.** Run `lab-kit init --library <dir>`. It writes `lab.yaml`, `ops/STATE.md`, `ops/missions/`, `experiments/` and `.lab/`, restores the method, the skills and the roles to this version, links `.claude/agents` to `.agents/agents`, and switches the lab pack on if set-up did not.
5. **Add the front door.** Through folio's write skill, add a project document `lab`. Its description states the question. Its `reviewed` date is today, its state says the lab is set up and no mission is active, and its next step is the operator's first objective. Create a top-level map, `research`, through the write skill, keep it `live`, add the front door to it, and set it on the home page: `folio config set home.maps research`. Set `front: lab` in `lab.yaml`.
6. **Add the question.** Through the write skill, add the question as `Q-1`, with rank 1, why it matters, what would settle it, and what would make the lab drop it. Add it to the `research` map.
7. **Freeze the surfaces.** List each path the operator named under `frozen:` in `lab.yaml`, then run `lab-kit freeze <path>` for each. With none, leave `frozen: []`.
8. **Write the operating guide.** Write `AGENTS.md` at the repository root, and make `CLAUDE.md` the one line `@AGENTS.md`. `AGENTS.md` states the question and its id, says to read `.lab/method/DISCIPLINE.md` and `.lab/method/LADDER.md` before any work, says where the library is, names the frozen surfaces, and names `lab-kit check` as the gate. Keep it under a screen: the method holds the rules.
9. **Add CI.** Make CI run `lab-kit check` on every push and pull request. On GitHub, a workflow in `.github/workflows/` that installs `lab-kit` with pip and runs `lab-kit check` from the root.
10. **Record and check.** Run `folio journal add --title "Lab set up" --description "<the question, in one line>" --body "<where the library is, the frozen surfaces>" --kind decision --about lab,Q-1` in the library. Run `folio index` there, then `lab-kit check` from the root. Fix what it names until it reports no error.
11. **Commit.** Add exactly what setup wrote: the library (`folio.yaml`, `.gitignore`, `content/`, `assets/`, `.folio/`), `lab.yaml`, `ops/`, `experiments/.gitkeep`, `.lab/`, `.agents/`, `.claude/`, `AGENTS.md`, `CLAUDE.md`, the CI workflow, and any `.gitignore` setup changed. Never `git add -A`. Commit with one line saying the lab was set up.
12. **Tell the operator, in three lines,** where the library is, the question's id and the frozen surfaces, and end with "Tell me the first mission and we will plan it together." Example: "The lab is set up: the library is in docs/, the question is Q-1, nothing is frozen. Tell me the first mission and we will plan it together."

## Stops

- `lab.yaml` already exists: the lab is set up. Use the plan-mission or run-mission skill.
- `lab-kit version` or `folio version` fails and installing does not fix it. Say so and stop.
- A library exists but its `root` is not the repository root, and changing it would break its documents' paths. Ask the operator.
- The operator names a frozen surface that does not exist yet. Ask whether to freeze it once it does.

## Done when

- The library has the lab pack on and its `root` at the repository root.
- `lab.yaml` names the library, `front: lab`, and the frozen surfaces, each recorded in `.lab/frozen.sha256`.
- The front door `lab` and the question `Q-1` exist, on the `research` map.
- `AGENTS.md`, `CLAUDE.md` and the CI workflow exist.
- One `decision` journal entry records the setup.
- `lab-kit check` reports no error, and the setup is committed.

## Commands

- `lab-kit version` and `folio version` confirm the engines.
- `lab-kit init`: before a library exists, installs the method, the skills and the roles only.
- `folio init <dir> --name ".." --purpose ".."` creates the library and installs folio's skills.
- `folio config set <key> <value>` writes the charter: `reader`, `root`, `home.maps`.
- `folio pack on lab` switches the lab pack on.
- `lab-kit init --library <dir>` installs the lab.
- `lab-kit freeze <path>` records a frozen surface's hashes.
- `folio journal add --title ".." --description ".." --body ".." --kind decision --about lab,Q-1` records the setup.
- `folio index` regenerates the indices.
- `lab-kit check` runs the lab gate: `folio check`, then the lab checks.
