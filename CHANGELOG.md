# Changelog

## 1.12.0

- **Papers drive the work; the record names no paper** (method rule 8, model section 4). A lab that writes
  papers keeps one overview page of the whole trail and one page per active paper, written as that paper's
  argument and opening with a scope table: audience, thesis, experiments included, excluded or superseded, and
  open. The papers' open rows and their reviewers' criticisms say what is proposed, ordered, parked or dropped,
  and a result revises the overview and every paper it touches. So far gives the current finding, never the
  story of the bugs on the way. Adding, merging or retiring a paper is direction.
- **`[papers]` in `lab.toml`** names the overview and the active paper pages, as library paths. It is optional:
  a lab without it is unchanged. With it, each paper page marks its scope cells `data-scope="included"`,
  `"excluded"` and `"open"`, and `lab check` refuses an id that is not in the lab, a step under included that is
  not done or is void, a step under open that is finished, a parked or dropped question in either, and a step or
  a question listed in two rows of one page. It notes a paper page committed before a result about something it
  lists.
- **`lab now` lists the papers**: each active paper with the open work its scope names, then the live steps
  that no paper lists, by themselves or by their question or goal.
- The skills `lab-set-up`, `lab-work`, `lab-talk` and `lab-review` and the method changed: run `lab init` in a lab
  after upgrading.

## 1.11.1

- **A run in progress in another checkout no longer fails `lab check`.** A run stays in the `.lab/running` of the
  checkout that started it until it ends, so every other checkout of the same lab saw a run listed as started and
  not in the store, and `lab check` failed there with "a run is never removed": with several sessions running
  experiments in their own worktrees, the gate was red everywhere but in each run's own checkout. A run listed as
  started and not ended, whose folder is in the `.lab/running` of another git worktree of the lab on this machine,
  is now a note. A run listed as started whose folder is nowhere is still a problem, the prompt to declare it lost.

## 1.11.0

- **An ended run that did not record what it used can be amended.** A run stopped before its machines' files came
  back seals with no amount for a resource it ran on, and `lab check` says it "did not record what it used"; `lab
  runs close` refused it, since it had ended. `lab runs close <run> "<why>" --used <resource>=<amount>...
  --evidence <folder>` now writes a sealed amendment, `<run>.amended.json`, beside the run's folder in the store,
  never inside it: the run's seal, the amounts, why, and every file of the evidence with its hash. `runs.tsv`
  lists it on an `amended` row with its seal. It covers only resources the run ran on and did not record, once.
  `lab check` counts the amounts, and checks the amendment's seal, its row, the run's seal and the evidence's
  hashes.
- The skill `lab-work` changed: run `lab init` in a lab after upgrading.

## 1.10.1

- **A fold, once committed, ends what can lock the folded decision.** `lab check` refused a draft folded into another
  as soon as a run started under an order the draft once held, even when the run started after the fold was
  committed. Only what acted before the commit that removed the folded decision's file now locks it; what acts later
  acts on the decision that took it in. A run that started before that commit still locks it, even when its line in
  `runs.tsv` is committed with the fold.

## 1.10.0

- **A settled decision is a draft until something acts on it.** A mission that carries it is launched, or a run or a
  trial starts of a step its `order:` names, of a step under a goal or a question that came out of it, or of a step
  that uses a resource whose amounts it set: from then it is locked, and a change of mind is a new decision. Until
  then it may be revised, so a talk that refines yesterday's plan changes yesterday's decision instead of stacking a
  new one on it. `lab check` holds a locked decision as it was committed when it was acted on, and lets a draft change, though a settled decision is never reopened.
  `lab show` and the decision's page say which it is.
- **A draft decision may be folded into another draft** with `folds: [D<n>, ...]`: its file is removed, its number is
  never used again, its log lines are read as about the decision that took it in, and an old link to it opens that
  decision. A locked decision cannot be folded. A resource whose `from` named the draft names the decision that
  took it in.
- `lab mission launch` writes a line in the lab's log about the decision it carries (`Mission launched:`), which
  locks it. What locks a decision is read from what the record holds: the log, the lists of runs, and every `order:`
  it was committed with. A goal's or a question's `from:` no longer changes once committed, and a resource's `from`
  changes only with its amounts, save in both cases to the decision that folded the one it named.
- What git holds about a lab's decisions is read once per commit and kept in `~/.cache/lab-kit/held/`, outside the
  lab. If it cannot be read, `lab check` fails and says why. A mission launched before 1.10.0 wrote no line in the
  log: its own file is read instead, so pointing it at another decision moves its lock with it.
- The skills `lab-talk` and `lab-mission` and the method changed: run `lab init` in a lab after upgrading.

## 1.9.0

- **A Missions page** on the site, compact like Decisions: the current first, then the next, then the closed.
  Each mission shows its status mark, the decision it carries, what it is for, its steps as marks with how many
  are closed, its last log line, and its rules and log folded. The rail lists the page with how many are current,
  and Now's mission line links to it.

## 1.8.0

- **A question with nothing left under it is the agent's next step.** `lab now` ("Yours next") and Now's "Next for
  the agent" list every open question that no open decision holds and that has no step open, waiting or running
  under it: answer it, add the next experiment, or bring parking it to the operator. An open goal whose questions are
  all answered, parked or dropped is listed too, to be closed in a decision, and so is an open goal with no question yet. Before, such a question was listed
  nowhere, and stayed open in silence once its last experiment finished or a decision dropped its last step. The
  skill `lab-work` changed: run `lab init` in a lab after upgrading.
- **An answer is written as itself, in a box:** yes, no, mixed or found, in the ink's colour, on Now and in the lists
  of a lab's pages; the page header says "answered no" in the same box. Where only a sign fits, as in the rail and the
  rows of marks, it is the word's first letter in a small box. It was a bare letter followed by "answered yes".
- **No key** on Now or in the rail: every mark names its state on hover.

## 1.7.0

Two kinds of question, and the site draws every state with one mark, the same on every page.

- **A question is a test or an estimate** (`kind:` on its card; test is the default). A test asks whether something
  holds and is answered yes, no or mixed. An estimate asks how much, which or what, and is answered `found`, with
  the finding itself: `lab answer <question> found "<the finding, with its range, and what it rests on>"`. `lab
  answer` and `lab check` refuse the other kind's answers. Its mark is F. The skill `lab-work` changed: run `lab
  init` in a lab after upgrading.
- **One mark per state and label,** on Now, in the rail, in the page header, in the lists of steps, runs and reviews:
  the shape carries the meaning and the colour follows it. Waiting is ‖, parked ◇, a decision to discuss ◆; a run or a
  review that failed is ✗. Where a page writes a state out, it shows the mark and the word together, in its colour.
- **A goal or a question with a step running under it shows as running,** its mark pulsing, on Now and in the rail.
- **Now has the key** above the map of the lab, grouped by the kind of card; the rail's key is the same.
- A log line's kind is drawn without colour: colour is kept for states.

## 1.6.0

One set of states for every card, and the checks that keep a card from saying what the record does not. The site's
Now page is a dashboard and its rail is the tree of goals, questions and steps; the Graph page is gone. It needs
folio 0.7.0, whose rail draws the tree. The skill `lab-work` and the method changed: run `lab init` in a lab after
upgrading.

- **Seven states, the same for every kind of card:** open, waiting, running, parked, done, replaced, dropped. What
  was `planned`, `active` or `in progress` is open or running; `built` and `reached` are done; `under discussion`
  is waiting. A done card may carry a label: a question's answer (yes, no or mixed) and an experiment's outcome
  (confirmed, refuted, unclear, or void when its results review failed). `lab show` and `lab now` print
  `done, confirmed`. A decision is open or done.
- **A failed results review makes an experiment done and void,** not a step to replace. No page uses its numbers,
  and what it made may still be used.
- **`lab answer <question> yes|no|mixed`.** An answer rests on a done experiment that is not void.
- **A need is met by a done step, and by a replaced or dropped experiment whose run finished:** a later step may
  use what such an experiment made (a frozen program), and says so with `needs:`.
- **`drops:` on a decision** drops the questions and steps it names once it is settled, like `parks:`. It is frozen
  with the rest of what a settled decision says.
- **`waiting_on:` is for what is outside the lab.** `lab check` refuses one that names a goal, question, step or
  decision: that wait never clears by itself. Builds and readings may carry it too.
- **So far says what was learned.** `lab check` refuses a question's So far with words that say where a step
  stands ("is running", "is next", "no result yet"), and reports a So far last committed before a `result` line
  about a step under the question, or one it names. `lab log <step> result` says so.
- **The site.** Now shows what is live with a pulsing sign (runs, the current mission, what the agent is on), what
  needs the operator, what is next for the agent in the agreed order, a tile per question with one sign per step,
  the resources and the latest events. The rail nests goal, question and step, opens on the current page, marks each
  with a sign for its state, folds what was replaced, dropped or set aside, and ends with a key.

## 1.5.0

A closed mission is kept. In 1.4.0 `lab mission close` removed the mission's file, and with it the only account of
how its decision was carried out: which sessions started, what stalled, what was restarted. The skill `lab-mission`
changed: run `lab init` in a lab after upgrading, and add `status: next` (or `status: current`, for one already
launched) under the `title:` of every mission 1.4.0 wrote, or `lab check` reports it.

- **`status:`** on a mission, written by the commands: `next` when saved, `current` when launched, `done` or
  `stopped` when closed. `lab check` asks for it. A file 1.4.0 wrote is still read (current once its log says
  `launched`), and `lab check` asks for the status to be written.
- **`lab mission close [<id>] [--stopped] "<what>"`** sets the status, adds a last line to the mission's log, writes
  one line about the decision in `log.md` (`Mission done:` or `Mission stopped:`), and keeps the file.
- **`lab mission`** lists the open missions and counts the closed; `--all` lists them all. `lab now` names only the
  open ones.

## 1.4.0

Missions: a working note for carrying out a settled decision across many sessions. Before, starting or restarting
the work on a decision meant pasting a long prompt that copied the decision's steps and the state of the machines,
and went stale within hours. The method (rule 5), the skills `lab-work` and `lab-talk` changed and `lab-mission` is new: run `lab init`
in a lab after upgrading, or `lab check` reports that they differ from the installed kit.

- **A mission** is `missions/M<n>-<name>.md`: a title, the decision it carries (`carries:`), what it is for, its
  Rules (what holds for this mission only) and a Log that only grows. It copies nothing the record holds: not the
  steps, the order, the amounts, or which machine is free.
- **`lab mission`**: `new "<title>" --carries <decision>` saves one as next; `launch [<id>]` makes one current
  (with no id, the one saved last), and refuses while its decision is open; `log [<id>] "<what>"` adds a line;
  `close [<id>] "<what it did>"` writes one `agent` line about the decision into `log.md` and removes the file.
  Several missions may be current at once. `lab mission <id>` shows one with the steps its decision orders and
  where each stands, and the other current missions. `lab now` names every mission.
- **`lab check`** checks a mission's form and that it carries a decision, and that a current one's decision is
  settled. A mission is not part of the record: it is not held against history and the site does not draw it.

## 1.3.1

- **A log line's end spaces are not part of it.** `lab log` wrote a line ending in `| ` when the so what was
  empty, which a lab's own whitespace check may refuse, while `lab check` refused the line once the space was
  removed, as a committed line changed. `lab log` now ends a line with no space, and `lab check` compares the
  committed lines of `log.md` with the spaces at their ends left out. Other files of the record are compared as
  they were.

## 1.3.0

A new page style, and a lock that holds what a plan demands rather than its words. Before, every page of a card
mixed what was observed with the plan, a term was linked only the first time it was used, and a locked card
could not be made clearer by one word without becoming a new experiment. The method and the skills `lab-work`,
`lab-review` and `lab-talk`, and the reviewer role, changed: run `lab init` in a lab after upgrading, or
`lab check` reports that they differ from the installed kit.

- **The page style.** A goal, question, experiment, build or reading page reads: the title and the lead (a
  question's `asks:` line), its picture, a tinted **What we know so far**, then the plan under one heading ("The
  plan, as locked", "The question, as asked") with every slot in its box under a fixed label, then the steps,
  the cost and the results, and the record (runs, reviews, earlier plans, files, log) folded at the bottom. A
  done experiment shows What it means and What was found above the plan.
- **A picture.** A `picture.svg` beside a card is drawn inline at the top of its page, in the site's colours,
  scrolling sideways on a narrow screen. It is parsed and written again from an allowlist of drawing elements and
  attributes, with links only inside the picture and its style sheet kept to it; a file that does not parse as
  one `<svg>` is not drawn, and the page says so.
- **So far on an experiment.** An experiment card may carry `## So far`, outside the plan: it may change after
  the lock. `lab new experiment` writes it. When it is empty, the Notes of settled decisions about the node
  are shown there; a decision may carry `## Note`.
- **Links in prose.** A node's exact title of two words or more, with its id in brackets or not, becomes one
  link to its page. Every use of a glossary term, inside bold and italic too, links to its entry with the
  definition on hover. `check` is no longer left out as generic. A slot draws pipe tables and `### ` heading
  lines; a heading the card starts a slot with is dropped, since the label is the heading.
- **The glossary** takes `- example:` (one concrete case, nothing observed) and `- also:` (other names that
  link to the same entry). Its page shows every group open, each entry with its example and its other names.
- **The lock holds machine terms.** `lab lock` writes `terms` in `lock.json`: a hash of each bar's role,
  result, comparison and number, by side, and each arm's name. The lock holds while those and `uses:` are as locked;
  the words around them may be made clearer, and a reviewer reads that. A lock made before 1.3.0 reads its
  terms from the version of the card that git holds with the locked hash; where git has none, the whole plan
  is held word for word as before. `lock.json` is never written again, so every run stays under its lock.
- **Word budgets.** Raised where a slot holds a table or a numbered list, or where cards sat exactly at the
  ceiling: an experiment's description 80, Compares 300, Cases 120, Outcomes 260, Limits 160, So far 300; a
  question's description 150, How we would know 180, So far 220; a reading's Looks at 120, Seen 360; a
  decision's Seen 150, Decided 150, Note 60. `docs/model.md` says why.

## 1.2.0

The order of the work can be agreed with the operator and recorded by a decision. Before, `lab now` and the
site listed next steps in the order of the tree, and an agreed order lived only as prose in a lab's
`AGENTS.md`, where a new session could miss it. The skills `lab-work` and `lab-talk` changed: run `lab init` in
a lab after upgrading, or `lab check` reports that they differ from the installed kit.

- A decision card may carry `order: [<ids>]`: goals, questions and steps, first to last. Once the decision is
  settled, "Yours next" and "Not yours to move yet" in `lab now`, and Next and the idle line on the site's Now
  page, list steps in that order. A step takes its own place if the order names it, else its question's, else
  its goal's; steps sharing a place, and steps not named, keep the tree's order, the unnamed after the named.
  The last settled decision, by number, that carries an `order:` has the say. An open decision orders nothing.
- `lab now` says which decision set the order; `lab show <decision>` and the decision's page list the order.
- `lab check` reports an `order:` that names something other than a goal, a question or a step, or names one
  twice. A settled decision's `order:` is held against the lab's history, like its `about:`.

## 1.1.0

A question can be parked: set aside by a decision, not dropped, and brought back only by another. Before, a
question the lab chose not to pursue now stayed open, with nothing to say it was set aside on purpose, or was
dropped for good. The skills `lab-work` and `lab-talk` changed: run `lab init` in a lab after upgrading, or
`lab check` reports that they differ from the installed kit.

- A decision card may carry `parks: [<question>]` and `unparks: [<question>]`. Each question named is also
  under `about:`. Once the decision is settled, the question is parked; a later settled decision that lists
  it under `unparks:` brings it back. The last settled decision, by number, that names it has the say.
- A parked question leaves Now, the rail and the graph. `lab new` refuses a step under it, and `lab lock` and
  `lab run` refuse its experiments, each naming the decision that parked it.
- `lab now` has a Set aside section: each parked question in one line with the decision that parked it, and a
  count of the dropped questions and the closed goals. The site's front page has the same section, with the
  first sentence of what was decided; a goal's page folds its parked questions; a parked question's page says
  at the top which decision parked it and why; a decision shows what it parks or brings back.
- Steps under a parked or dropped question, or a goal that is not active, no longer show under "Not yours to
  move yet" or as what the idle front page names next.
- `lab check` reports a `parks:` or `unparks:` that names something other than a question, a question not
  under `about:`, and a question both parked and brought back by one decision. What a settled decision parks
  or brings back is held against the lab's history, like its `about:`.

## 1.0.3

A word is now defined in one place, `GLOSSARY.md`. Before, the glossary and the goal's Vocabulary
both said what a word means, and the two could drift. The skills `lab-work` and `lab-set-up` changed:
run `lab init` in a lab after upgrading, or `lab check` reports that they differ from the installed
kit. Change the goal's Vocabulary to names, too: see below.

- A glossary entry may carry two more lines beside `- code:`. `- avoid: gate, filter, policy` lists
  the words not to use for the thing; `- see: entries/kna-gate` (or a page of a library the charter
  names, such as `pier-folio:/content/concepts/lora/`) names a page that explains the concept.
  `lab define` prints both, and the glossary page shows the avoid words in small type and the page as a
  link. The hover on a term stays the definition alone. `lab check` checks a `see` as it checks a
  card's `see:`. It does not flag avoid words used in cards: a word to avoid for one thing is often right
  for another.
- The goal's Vocabulary is a list of names only (`- field`). The goal's page and `lab show` draw
  each with its glossary definition. `lab check` reports a name that is not a glossary term. A goal
  written the old way (`- word: meaning`) still shows the glossary's definition, never the card's, and
  `lab check` reports it: list the name only, and add the term to the glossary if it is missing there.
  An existing lab must change its goal's Vocabulary to names.

## 1.0.2

One defect found while rehearsing a real lab, four follow-ups from 1.0.1, and three larger word
budgets. The skill `lab-work` changed with the budgets: run `lab init` in a lab after upgrading, or
`lab check` reports that the skill differs from the installed kit.

- A step may need a step that sits later in the tree, such as a build under the second question
  that needs a reading under the third. States used to be worked out in the order of the cards, so
  the earlier step never saw that the later one was done: it stayed under "Not yours to move yet",
  waiting on a step that was done, and `lab lock` and `lab run` refused it. Each step's state is now
  worked out after everything it needs, wherever that sits. `lab now`, `lab show`, `lab brief` and
  the site agree, since they read the same states.
- Steps that need each other in a circle were already a problem in `lab check`. Now none of them
  moves until the circle is broken, even when one of them is done, and each says which need leads
  back to it.
- Rows that a committed review passed stay. A reviewed `results.tsv` could be emptied together with
  the card's Found and Means, committed, and later filled with other rows and reviewed again, with
  `lab check` sound at every step. Once a results review that passed is committed with the rows it
  read, those rows are held, whatever the card and the file say later. A draft row committed after
  a review, which that review never read, may still be corrected.
- A step that needs one that is dropped or replaced says so in what it waits on, with what to do:
  remove the need or replace it. A need that names nothing in the lab, or something that is not a
  step, now holds the step in `lab lock` and `lab run`, as `lab check` already reported it.
- A `.pyc` file in `plan/` outside `__pycache__` is refused by `lab lock` and `lab run` and reported
  by `lab check`, as a link is: Python would import it, and the plan's hash does not cover it.
- `lab check` says in a note when the repository is a shallow clone, and fails with `--strict`: the
  history check needs every commit, and CI should fetch all of the history (`fetch-depth: 0`). The
  model also says that the history read is that of the record under the lab's root as it is now,
  so moving the root inside the repository starts again what is held.
- A plan that 1.0.0 locked or ran while a `__pycache__` sat in `plan/` verifies again. 1.0.0 counted
  those files in the plan's hash and 1.0.1 does not, so such a record could never match. When a
  hash of `plan/` does not match and the experiment's lock was made by 1.0.0, the folder is hashed
  once more the way 1.0.0 did before a change is reported. It applies to no other lock, and only
  while the cache files are still there as they were.
- `lab show <experiment>` says of each run how many files it holds, how many at the top of its
  folder and how many under each folder there. It used to list ten files and leave out `work/`, so
  a run whose output was all in `work/` looked nearly empty.
- Three word budgets are larger, because real cards were hitting them and ending in fragments: an
  experiment's Found goes from 130 words to 180 and its Means from 90 to 150, and a question's So
  far from 120 to 180. A budget is a ceiling against sprawl. If a card needs its last words cut
  into fragments to fit, it is saying too much for one slot or the budget is wrong, and full
  sentences win.

## 1.0.1

Three defects found by moving a real repository to 1.0.0, and one message.

- `lab check` reads the history of the lab's own record only: `log.md`, `resources.toml`,
  `decisions/`, and each experiment's lock, runs, results and reviews under `goals/`. It used to
  read every file with one of those names anywhere in the repository, so a repository that once held
  an older layout, since removed, failed for ever with "was committed and is gone".
- A file of the record is known by the numbers in its path. A folder or a decision renamed after a
  reworded title is the same record: the rename is no longer reported as a removal, and what was
  committed under the old name is still held under the new one. A file moved to another number, or
  out of the record's places, is reported as gone.
- The hash of `plan/` leaves out `__pycache__` folders and `*.pyc` files, as it always meant to.
  Importing a script from `plan/` no longer makes `lab check` say the plan changed after the run.
  The hash of a folder that holds neither is what it was, in both formats, so every existing lock,
  run and review still verifies.
- A card's `see:` that names a page of another library is a note, not a problem, when that
  library's folder is not on the machine, as in CI. With `--strict` it is a failure. When the folder
  is there and the page is not, it is still a problem.
- `lab run` says that the resources changed when `uses:` is not what was locked. It used to say the
  demand had changed.

## 1.0.0

A rewrite from first principles. Nothing of 0.6 carries over: a lab kept with 0.6 is not read by 1.0,
and no command converts one. `docs/model.md` is the contract, and its section 8 sets the old model
beside the new.

What a lab is

- One tree. A goal holds questions. A question holds its steps, of three kinds: an experiment (a
  comparison with its bars set in advance), a build (something an experiment needs that has to be
  made first) and a reading (a look at what already exists, which suggests and never confirms). An
  experiment holds its runs and its results. Every id spells the path: `G1.Q2.3`, and a result is
  `G1.Q2.3:attack-success`.
- Decisions beside the tree. A decision is something discussed with the operator: what was seen, two
  or three options, a recommendation, then what was decided and why, in the lab's words. Every goal
  and question names the decision it came from.
- Cards. Each of these is one small Markdown file: front matter, a description, and named slots with
  word budgets. A card never holds an id, a state or an outcome; all three are worked out from the
  record when asked for. Nothing computed is kept in a lab.
- The files: `lab.toml`, `resources.toml`, `log.md`, `GLOSSARY.md`, `goals/`, `decisions/`, and
  `runs/` outside git. Missions, protocols, attempts, budgets, ledgers and the folio documents that
  held the record are gone.

How a number counts

- write the card, lock, run, result, review. Each step is a command that refuses when the one before
  it is missing.
- An experiment says what it compares, each arm, its cases, and its confirmed-if and refuted-if
  lines, each a sentence and the one result it tests (`attack-success < 0.05`). The outcome
  (confirmed, refuted, unclear) is worked out from those lines and the results, never written.
- The lock holds what the experiment demands: the comparison, the arms, the cases, the lines, what
  each outcome would mean, and the limits. That never changes. A changed demand, a failed results
  review or a partial score is a new experiment that replaces the old one and says why. The lock
  also records `plan/` as it was locked.
- An experiment is run until one run finishes. Each run pins the `plan/` folder it ran (the
  configuration and the code, as files and no links). When `plan/` is not what the run before ran,
  or for the first run what was locked, the run says what changed and why: `lab run --changed`.
  The first run that finishes is the only source of results, nothing more runs under that
  experiment, and its `plan/` stays as it ran.
- A run is detached, sealed when its command exits (every file's hash, and one over the record) and
  moved into the store. A trial run comes before the lock and never gives a result.
- Every run is listed in `runs.tsv`, in git beside the lock: a row when it starts, a row with its
  seal when it ends. The store is outside git, so this list is what says a run existed: a run
  removed from the store, or a record rewritten, fails `lab check`, and a clone without the store
  still knows what ran. A run that started and whose folder is gone for good is declared lost,
  with the reason: `lab runs lost`.
- What git holds is tamper-evident from the commit that first holds it, not before: the lock is
  committed when it is made and a run's row when it starts. `lab now` and `lab check` say what is
  not committed yet.
- A result is a row in `results.tsv`: a name, a plain label, a value, how it reads, what it is
  compared with, and the command that prints it again from the sealed run. `lab check` runs every
  command again. A card names a result (`{attack-success}`) and never types its number.
- One review, after the results, by a session that did not do the work. A second, of the plan, only
  before a run that uses a metered resource. A failed results review is final for that experiment.

Who decides

- The operator decides direction (the goals and the questions) and resources, in a discussion
  recorded as a decision, not by approving requests. What a decision settles needs no further yes.
  The agent decides everything else and records each choice in the log. A settled decision is
  never reworded. A question is answered with `lab answer`, on a finished experiment.
- Resources are set once for the lab in `resources.toml`: what each is, where its key is kept, for a
  metered one its unit, grant and amount for one run, and its rules as plain sentences. `lab run`
  refuses a run that would pass the amounts; an experiment may carry an override, which is a
  resource and a cap. A metered resource names the settled decision that set its amounts (`from`),
  which lists it under `about:`, and an amount changes only together with it. A resource is never
  removed, only retired, and use outside a run is a list that only grows.

The command, the method and the site

- One command, `lab` (`lab-kit` still starts it), with fifteen commands: `now`, `show`, `brief`,
  `since` and `define` to look; `new`, `log`, `decide` and `answer` to write; `lock`, `run`, `runs`,
  `review` and `check` for evidence; `init` once.
- One log, `log.md`, with five kinds of line: a decision recorded, a choice of the agent's, a
  result, something stuck, and what the agent is starting on now (`doing`). The `doing` line is how
  the operator sees that the lab is alive without asking.
- `lab check` holds what can be held mechanically: ids and links, card budgets and front matter,
  a test on every line, unchanged locks, listed and sealed runs, results that re-derive and were
  reviewed, use inside the resources' amounts, a decision behind every goal, question and amount,
  the installed method and skills, and a history that only grows. It runs the commands in
  `results.tsv`, so it is for a lab you trust. `--strict` fails when history or the store could not
  be checked, which is what CI wants.
- A lab that is not written as the model says (a mistyped folder, a list written as one value, a
  file that is not text) is reported by `lab check`, and stops no command and no page. Commands
  validate everything before they write, and one writes at a time.
- The method is seven rules in one file, `method/METHOD.md`. Four skills (lab-set-up, lab-work,
  lab-review, lab-talk) and one role (the reviewer). `lab init` installs them into a lab.
- The site is drawn by `lab_kit.site` inside folio, from the record, at each request. It needs
  `folio-kb` 0.5.0 or later, as the optional extra `lab-kit-cli[site]`. The command itself depends
  only on `pyyaml` (and `tomli` on Python 3.10), and needs Python 3.10 or later.

## 0.6.4

- `lab-append-only` accepts a recorded correction. `.lab/corrections.tsv` lists `path<TAB>commit<TAB>reason` for a commit that edited a mission log, a budget or a lock record in place and was later put right. That commit's version is left out of the file's history, so the versions before and after it must still show the file only growing, and the file's current version is never a listed one. The list is committed, so every waiver keeps its reason on the record.
- `lab-roster-frozen` compares a run's `config` with its protocol's pinned configuration as the run records it, through JSON. YAML reads a key such as `1:` as an integer and `run.json` holds it as the string `"1"`, so a run that used exactly its pinned configuration was reported as differing.

## 0.6.3

- A mission runs to its conclusion with no further input from the operator. The approval launches it: plan-mission hands it to run-mission at once, with no separate "go". A running mission never waits for an answer. A few lines it never crosses (new money, a credential, publishing outside the lab, a change to a frozen surface, anything irreversible outside git) unless its approved plan names the exact step; work that reaches one is recorded as blocked, and the mission carries on and concludes with it open for the next mission. plan-mission settles those lines in the plan instead of naming points where the run comes back to the operator.
- The commander settles what used to go back to the operator mid-mission: a reviewer disagreement (on the evidence, with a second reviewer), a protocol that must change after its lock (a new protocol), and a correction or retraction of a recorded result (a new record through the review skill, reported afterwards). Reports say what was decided, never ask. The reporter leaves pushing to the commander, and the reviewer's verdict no longer escalates past the commander. DISCIPLINE §8 and §14 and the spec say the same.

## 0.6.2

- The operator's words authorize; they are not the text of the record. The plan-mission skill writes a mission's objective in the lab's own words, as what it will establish inside a clear bound, and the operator approves that text; a vague prompt is interpreted, never pasted. The operator's sentence of approval is kept once, in one log line with its time. The run-mission skill keeps decisions in the log in the lab's words, never quoting the message that prompted them. DISCIPLINE §14 and the spec say the same. Missions already written are left as they are.

## 0.6.1

- `lab-kit migrate` rewrites a run's `config` with the same names it rewrites in its protocol's pinned configuration, so `lab-roster-frozen` holds after the move.
- The plan-mission skill points `ops/STATE.md` at `missions/`.

## 0.6.0

- One folder per run, outside git. A run is `runs/<experiment>/<YY-MM-DD-HHMM>-r_<4 characters>/` and holds everything it produced. lab-kit writes only `run.json` and `run.log` there; the rest is the experiment's own. `LAB_RUN` names the folder. `LAB_OUT`, `LAB_WORK` and `LAB_RUN_DIR` still work for one release.
- The seal. When the command exits, `run.json` records every file's sha256 in `files`, and one hash over the whole record in `seal`. `MANIFEST.sha256`, `work.sha256` and `store.json` are gone. `lab-evidence-sealed` checks a run's folder and its record against the seal.
- The store holds the runs. With `store:`, `runs/` is a committed link to `<store>/runs`. A run is written on local disk in `.lab/running/`, then moves into the store when it ends: copied, verified against its seal, renamed into place, made read-only, and only then deleted locally. `lab-kit publish --pending` retries a failed move, `lab-kit fetch` copies a run into `.lab/fetched/` on a machine without the store, and `lab-kit verify` checks a run against its seal. Where `runs/` does not resolve, as in CI, the gate skips the checks that read runs and says so once. `lab-work-stored` becomes `lab-run-stored`.
- Dated ids. Missions are `missions/<YY-MM-DD>-m_<slug>.md` (they were in `ops/missions/`), and experiments are `experiments/<YY-MM-DD>-e_<slug>/`. A protocol keeps its slug.
- `lab-kit migrate [--apply]` moves a lab from the 0.5.0 layout. It takes each experiment's date from its lock and each run's from its start. Each run's `out/`, `work/` and `run.log` go into one sealed folder in `runs/`. Every old path and id in git-tracked text is rewritten, and the lock hashes are taken again where a protocol's text changed with it. The rewritten documents are listed in the library's `baseline.sha256`, folio 0.3.6's `baseline`, so their permanence holds from the rewrite on, and every old name is kept in `.lab/migration.tsv`. Run it again after old runs land from machines on an older lab-kit.
- Run records are no longer append-only lab files in git: the seal holds them.

## 0.5.0

- lab-kit no longer runs a lab's code to check it. The `lab-selftest` check is gone, and with it the `tools:` key in `lab.yaml`: a lab that still has the key gets an error saying to delete it. lab-kit checks the record; the lab tests its code in its own test suite, which its gate runs beside `lab-kit check`.
- The method (DISCIPLINE §7) and the experiment and review skills say so: an experiment's command calls the lab's own tested code, `bin/` holds only what is particular to one experiment and may be empty, and a fold is tested on a planted case in the lab's suite. The lock still hashes `bin/` and records the commit, which says which version of the lab's code a run used.
- Locks and run records are unchanged.

## 0.4.0

- The run store. `store:` in `lab.yaml` names one shared filesystem, such as `/labs/<lab>`, where every finished run's raw output goes. When a run ends, `lab-kit run` publishes `work/` and `run.log` to the store at the run folder's own path: a copy into `.incoming/`, checked against `work.sha256` (nothing missing, extra or changed), renamed into place, made read-only. It then writes `store.json` beside `run.json` and deletes the local copy. A run in the store is never overwritten. A failed publish is noted in `run.log`, keeps the local copy and never changes the run's exit code.
- `lab-kit publish <slug>/<run id>... | --pending [--keep]`, `lab-kit fetch <slug>/<run id>` and `lab-kit verify <slug>/<run id>`. A machine that does not mount the store sets `LAB_STORE_HOST` to one that does (rsync over ssh, `sha256sum` there).
- `lab-work-stored` (warning): with a store set, every ended run with a `work.sha256` has a `store.json`.
- The experiment skill says to commit `store.json` with the run, and never to mount the store where the system under test runs.
- A lab without `store:` works as before.

## 0.3.0

- The lock covers the instrument. `lab-kit lock` records, beside the protocol's hash, `instrument` (one sha256 over the files in the experiment's `bin/`, sorted by path, each fed as its path and its bytes, `__pycache__` left out), `commit` (the git head) and `lab-kit` (the version). `lab-lock-intact` fails when `bin/` no longer hashes to `instrument`, and `lab-kit run` refuses to start on such a lock, as it already did for a changed protocol.
- Records name their commit. `lab-kit run` writes `commit` and `lab-kit` into `run.json` when it starts.
- Raw output is sealed. When the command exits, `lab-kit run` writes `work.sha256` beside `MANIFEST.sha256`, one line per file under `work/`, when that folder exists. `work/` stays out of git; its hashes go in, so a copy kept elsewhere can be verified.
- A lock or a run record without the new fields predates them and passes: records are never edited. The example lab's records are unchanged and are that test.
- The experiment skill says to commit `bin/` before the lock and to commit `work.sha256` with the run.

## 0.2.0

- Standing budgets. The operator can grant money once for many missions: `ops/budgets/<name>.yaml` lists grants, each with an amount and who granted it and when. A mission names the budget it draws on in `budget:`. `lab-mission-approved` checks that what the missions under a budget commit (an active mission's cap, or its spend when that is more; a concluded mission's spend) fits inside its grants; `lab-append-only` keeps grants append-only and the unit fixed. `lab-kit status` shows each budget's granted, committed and left amounts.
- A run record committed while its run was still going may be committed again once the run ends. `lab-append-only` accepts a later version of a `run.json` that differs from its first committed one only by `ended`, `exit` and `spent` filled in, each once; any other change, a closing field changed after it was set, and a deleted run record still fail.
- The method (DISCIPLINE §13, §14) and the plan-mission and run-mission skills: under a standing budget the commander may approve a mission that fits inside it and needs nothing that stays the operator's, decide the stops its own plan names and set mission caps inside the budget, recording each call in the mission log and reporting it afterwards. New money, credentials, publishing outside the lab and frozen surfaces stay the operator's.

## 0.1.0

The first release.

- The method: `DISCIPLINE.md` and `LADDER.md`, copied into each lab's `.lab/method/`.
- Five skills, set-up-lab, plan-mission, run-mission, experiment and review, and four agent roles, scout, runner, reviewer and reporter. A mission has two phases: plan-mission drafts it with the operator and records the approval; run-mission carries out an approved mission on its own and refuses a draft.
- The `lab-kit` command: `init`, `check`, `experiment`, `lock`, `run`, `runs`, `score`, `rederive`, `freeze`, `status` and `version`.
- The lab gate: `folio check`, then seventeen lab checks, in one report. `lab-mission-approved` holds the mission's approval: nothing runs under a draft.
- An example lab, `examples/monte-carlo-lab`, that passes the gate: does the error of a Monte Carlo estimate of pi shrink as 1/sqrt(n)?
- Built on folio 0.1.0 and its lab pack.
