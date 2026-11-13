---
name: lab-review
description: >-
  Review one experiment's plan or its results as someone who did not do the work, and record a
  verdict. Use when you are handed an experiment's id and a stage ("review the results of
  G1.Q1.2", "review the plan of G1.Q2.1"). Never use it on work you did in this session.
---

# lab-review

You read the artefact before any story about it, and you write nothing but your verdict.

## A plan (only before a run that uses a metered resource)

1. `lab show <experiment>`, then read every file in its `plan/` folder.
2. Fail it when:
   - more than one thing varies between the arms it compares;
   - a line's test does not measure what its sentence says;
   - no outcome of the run could make a refuted-if line hold;
   - the run would use more of a resource than it needs to answer the question.
3. `lab review <experiment> plan pass|fail "<what you read, and what you found>"`.

A failed plan is fixed by its author and read again.

## Results

1. `lab show <experiment>`. It lists the lines with their tests, the result rows, the run and its
   files, and any trial runs.
2. Read `results.tsv` in the experiment's folder, and the code in `plan/` that produced the
   numbers. Run each row's command yourself, from the lab's root, with `RUN` set to the run's folder.
3. Fail it when:
   1. a number is not what its line says it is: the command counts something else, over other cases,
      or from another run;
   2. more than one thing varied between the arms;
   3. a tool failed during the run and its arm was kept;
   4. a failed run's partial numbers were read before the apparatus was changed for the next run
      (each run says what changed and why: read those sentences against the runs' output);
   5. a line was written when its number was already known: from an earlier run of the same
      comparison, or from a trial run that measured it. A trial that only showed the apparatus
      starts does not count.
4. `lab review <experiment> results pass|fail "<note>"`. The note opens with one sentence the operator
   can read, saying what you conclude ("The numbers are what the rows say, and the bars were fixed
   before the run."). What you re-ran and what you could not verify comes after it: the page shows
   the first sentence and folds the rest.

A failed results review is final for that experiment. Say in the note what a replacement must do
differently.

When you read a plan, also read the card as someone who was not there. If an arm is named and not
explained, or the card points at something it does not say, say so in the note: it does not fail the
review, and the author fixes it before the lock.

## A rewording of a locked card

After the lock, the words of a plan may be made clearer; what it demands may not. `lab check` holds
the machine terms (each bar's result, comparison and number, each arm's name, `uses:`). You read the
rest. Compare the card as it was locked (`git log -p -- <card>`, from the commit that holds its lock)
with the card now:

1. Slot by slot, the meaning is unchanged: the same comparison, the same arms doing the same things,
   the same cases, the same outcomes and limits. A clearer sentence passes; a narrower or wider one
   fails.
2. Every number in a line's sentence matches its test, and its test is the one locked.
3. Nothing observed is in the plan or in the picture: no status, no result, no "since the lock".
   What was observed goes in So far.
4. The picture shows only what the card states.
5. Every dotted word on the page (a glossary link) means the lab's meaning where it is used. A word
   used in its everyday sense that links to a lab term is a fault.

Give the verdict, pass or fail, with one sentence per fault, to whoever asked. You write nothing in
the lab: the author logs the rewording with your verdict
(`lab log <experiment> agent "Reworded the locked card: <what>" "Reviewed by <you>: pass"`).

## A page's style

Open the page on the site and read it top to bottom as the operator would:

- the picture comes first, numbered, showing the whole work and only what the card states;
- What we know so far holds everything observed, and the plan below it holds nothing observed;
- each slot sits in its box under its fixed label, with no heading of the card's own above it;
- every other page is named by its exact title, so it is a link;
- every glossary word is a link and means the lab's meaning there, and no word is defined on the
  page that is not in the glossary;
- sentences are plain, one idea each; items compared are in a table; options are named in words,
  never letters.

Report each fault with where it is. Fix nothing yourself.

## Rules

- Do not fix anything. Do not edit a card, a picture, a plan or a row.
- Do not read the author's log lines or messages before you have read the files.
- If you cannot re-run a command or open the run's output, fail it and say why.
