---
name: lab-set-up
description: >-
  Turn a repository into a lab: install the method and the skills, write the goal and the first
  question with the operator, list the resources, and leave the checks passing. Use once, when the
  operator says "set up a lab here", "make this a lab", or names a research goal in a repository
  that has no lab.toml.
---

# lab-set-up

You set the lab up in one discussion with the operator, so that everything it settles can then run without them.

1. `lab init`. It writes `lab.toml`, `AGENTS.md`, `GLOSSARY.md`, `resources.toml`, `log.md`, the
   folders, the method (`.lab/METHOD.md`), the skills and the reviewer role. Read the method.
2. Read the repository: its README, its code, any notes. Do not ask what you can look up.
3. `lab new decision "The lab's goals, first questions and resources"`. On its card write **Seen**:
   what the repository is and what prompts the lab.
4. Discuss with the operator, in one conversation, what is theirs:
   - the goals: what they want to be able to say at the end;
   - the first questions under each;
   - the resources: each machine, cloud allocation, API, repository and place to publish that the
     lab may touch; for a metered one its unit, how much they grant and how much one run may use;
     and any rule for it.
5. Fill `resources.toml` from what was agreed. It names where a key is kept, never the key. Each
   metered resource names the decision that sets its amounts, `from = "D1"`, and D1's card lists
   each of them under `about:` (`about: [gpu, api]`). Do this before the next step: what a settled
   decision is about does not change afterwards.
6. `lab decide D1 --with <their name> "<what was decided and why, in the lab's words>"`, and show them
   the text.
7. `lab new goal "<a short name>" --from D1` for each goal, and `lab new question <goal> "<a
   short name>" --asks "<the question, in full>" --from D1` for each question. Give each a description; give each question **We
   expect** and **Wrong if**.
8. Later, an amount changes only out of another decision that lists the resource, and `from` then
   names that one. A resource is never removed from `resources.toml`: one no longer used gets
   `retired = "<why>"`.
9. Fill `lab.toml` (`code` for the code repository, `store` if the runs live elsewhere) and the
   local rules in `AGENTS.md`.
10. Start `GLOSSARY.md`: each term the cards use that an outsider would not know, one sentence, with
   its name in the code when it has one.
11. The site: the lab's `docs/` folder is a folio library whose charter lists `lab_kit.site` under
    `views:`. Set it up with folio's own skill if it is not there.

12. Commit. Git is what holds the record: nothing is held before the first commit, and
    `lab check --strict` says so.

Done when `lab check --strict` passes and `lab now` shows each question as open.
