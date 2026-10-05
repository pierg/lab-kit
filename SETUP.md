# Set up a lab

Paste everything below this line into your coding agent, in the repository that will hold the lab. The one-line prompt in the README does the same thing.

---

Set up a research lab here with lab-kit. lab-kit runs the lab's method on top of folio, which keeps the lab's documents. I will not run lab-kit or folio commands myself. You run them, through the skills they install.

1. Install the engines. The Python package `lab-kit-cli` provides the `lab-kit` command and depends on `folio-kb`, which provides `folio`:
   - If `lab-kit version` and `folio version` both print a version, go to step 2.
   - Otherwise: `uv tool install lab-kit-cli --with-executables-from folio-kb`, or `pipx install --include-deps lab-kit-cli`. Both also put `folio` on the path. `pip install lab-kit-cli` in the project's environment works too.
   - If none of these works, tell me and stop.
2. Run `lab-kit init` in the repository root. Before a library exists, it installs only lab-kit's method, skills and roles.
3. Read `.agents/skills/set-up-lab/SKILL.md` and follow it. It asks me at most three questions in one message: the lab's question, where the library lives, and which paths are frozen.
4. Finish with `lab-kit check` passing and the setup committed. Then tell me, in a few lines, where the library is and the question's id, and ask me for the first mission.

From then on a mission has two phases. First we plan it together with the plan-mission skill: I state the objective in plain words, you ask only what you cannot look up, and you write the plan as a draft until I approve it. Then the run-mission skill carries out the approved mission on its own, and comes back to me only at the stops the plan names. Between missions I may ask in plain words ("how is the mission going?", "what should we do next?"). Do not run an experiment, spend tokens on a live run, or push anything without my word.
