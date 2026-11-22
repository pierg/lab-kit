---
name: lab-mission
description: >-
  Save, launch, resume and close a mission: the working note for carrying out a settled decision
  across many sessions. Use when the operator says "save it as a mission", "save it as a new
  mission", "launch the mission", "launch the latest mission", "resume the mission", "resume M3",
  "how is the mission going", "close the mission", or when `lab now` lists a current mission and
  you are the session that runs it.
---

# lab-mission

A decision says what the lab does and why: the questions, the order of the work, the resources. A
mission says how that is being carried out right now: which decision it carries, the rules of
running it that hold for this mission only, and a log of what has happened. It is the note a
session reads to pick the work up where the last one stopped, so the operator never has to paste
a long prompt to start or restart the work.

A mission is a file, `missions/M<n>-<name>.md`. It is **next** from when it is saved, and
**current** once it is launched, and **done** or **stopped** once it is closed; its `status:` says
which, and the commands write it. A closed mission stays in `missions/`: its log is the only account
of how the decision was carried out. Several may be current at once. `lab mission` lists the open
ones (`--all` the closed too), and
`lab mission <id>` shows one whole: what it is for, its rules, the steps its decision orders with
where each stands now, the other current missions, and its log.

## What a mission holds, and what it never holds

It holds:

- `carries:`, the settled decision it carries out;
- one or two sentences on what it is for;
- **Rules**: only what holds for this mission and is not already a rule of the lab, such as how
  many machines it may take at once and which ones, how many sessions may run side by side, or
  what each session is given to read first;
- **Log**: one line per event, only added.

It never copies what the record already holds: not the steps, not their order, not the amounts of
any resource, not a result. And it never holds what is true only for a moment, such as which run
is going or which machine is free: `lab now`, `lab runs` and the machines themselves say that when
it is needed. A rule that holds for every mission belongs in the lab's `AGENTS.md`, not here.

## Save: "save it as a mission"

After a discussion with the operator has settled a decision (the lab-talk skill records it):

1. `lab mission new "<title>" --carries <decision>`. The title is a short name, such as "The
   two waves of D10".
2. Write the description under the front matter: what this mission is for, in the operator's
   terms. Write **Rules** from what you agreed about how to run it, and nothing else.
3. Read it back to the operator as written, then commit the file.

A mission may carry a decision that is still open, while you finish discussing it; it cannot be
launched until that decision is settled. One decision may be carried by two missions when the
operator wants its parts run separately, such as one wave each.

## Launch: "launch the mission", "launch the latest mission"

1. `lab mission launch` launches the mission saved last; `lab mission launch <id>` a given one.
   The command refuses while the decision is open or the mission does not say what it is for.
   Launching acts on the decision: from then it is locked, and the lab's log says so. Revise the
   decision before you launch, and commit it before the launch is committed.
2. `lab mission <id>`. Read its rules, then the rules of every other current mission it lists:
   they share the lab's resources, so never take a machine or a slot another current mission
   holds. When two missions' rules would collide, bring that to the operator before you start.
3. Start the work: for each step listed as yours, in the order shown, that the rules leave room
   for, start a session of its own (in the way the lab's `AGENTS.md` says sessions and runs are
   started) and give it the step's id and the lab-work skill. Each session follows lab-work as
   usual: it logs `doing`, plans, locks, runs, gets its review, and records.
4. Log each start: `lab mission log <id> "started G1.Q2.3 in its own session"`. Commit the
   mission file each time you add lines.
5. Watch the sessions. When one ends a step, or is stuck, log it in the mission, and start the
   next step the rules leave room for. When the library keeps `pages.toml`, the session whose result
   passes review, or that answers a question, revises the pages that cite it with the lab-pages skill
   before it pushes: give each session that rule with its step.

## Resume: "resume the mission", "resume M3", "how is the mission going"

1. `lab mission` to find it; with several current, take the one the operator named, or ask.
2. `lab mission <id>`, and read its log against what it lists as the steps and where each stands.
   The record is the truth: a step the log says was started and the record shows as done is done;
   one started and showing no new log line in the lab, no live session and no running run has
   stalled.
3. Log what you found (`lab mission log <id> "resumed: G1.Q2.3 had stalled, restarted"`), restart
   what stalled, and carry on from step 3 of Launch.

When asked how it is going, answer from `lab mission <id>` and `lab now`, as lab-talk says.

## Close: when every step is finished, or the operator stops it

1. Check `lab mission <id>`: every step it lists is finished, or the operator said to stop.
2. `lab mission close <id> "<what it did>"`, or `lab mission close <id> --stopped "<why it
   stopped>"` when the operator ended it before its work was done. Its status becomes done or
   stopped, its log gets a last line, and the lab's `log.md` one line about the decision. The file
   stays: never remove it.
3. Commit, and tell the operator in a sentence what was carried out. If another mission is next,
   say so; it is launched when they say to.

## Rules

- A mission approves nothing. It carries out what a settled decision already settled. Direction
  and resources still come out of a decision with the operator.
- Never edit or remove a line of a mission's log; add a new one.
- Keep it thin. If you are about to write a list of steps, an amount or a result into a mission,
  it belongs on a card or in the decision instead.
