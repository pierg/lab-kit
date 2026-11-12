# The method

Seven rules every lab keeps. Each says what holds it: a command that refuses, a check, or a reviewer's
judgement. The lab's own `AGENTS.md` adds only what is local.

1. **Say what would refute it before you run.** An experiment states what it compares, what would
   confirm and what would refute, each line with the one result it tests. It is locked before its
   run. *Held by `lab lock` and `lab run`.*
2. **A number counts only as a reviewed result of a locked plan.** It is a row whose command prints it
   again from the sealed output of the experiment's one finished run, read by a reviewer who did not
   do the work. Until then it is not written on a card, in a message or in the log. A count made
   in a reading is said as what it is, on the reading's own card, and confirms nothing. *Held by
   `lab check`; the review itself is judged.*
3. **A miss is recorded like a hit, and nothing locked or recorded is edited.** A failed run is kept. A
   refuted line is an outcome like any other. A changed plan, a failed review or a partial score is
   a new experiment that replaces the old one and says why in a sentence. What an experiment demands is
   locked once; it is run until one run finishes, and a run after a fix says what changed. Once a
   run has finished, nothing more runs under it. Every run is listed in the experiment's `runs.tsv`,
   which you commit when the run starts and again when it ends: git holds only what it has been
   given, and a run is never removed. *Held by `lab run`, `lab new` and
   `lab check`.*
4. **Write for a reader who was not there.** Every page stands on its own: it says what each thing it
   mentions is, names each arm of an experiment and what it is, and explains a term where it first
   uses it. A number is said once: it lives in its result row, and a card names it. A state is
   worked out, never written. *The numbers and the budgets are held by `lab check`; whether a page
   can be read cold is judged, and the reviewer reads for it.*
5. **Decide everything that is not direction or resources, and never wait idle.** Direction is the
   goals and the questions. Resources are what `resources.toml` lists and how much. For those two,
   open a decision that says what was seen, the options and what you recommend, and work on what it
   does not hold. What a decision settled needs no further yes. Everything else is yours: decide,
   record it, go on. Never ask the operator to check your work or to run a command. *Held by
   `lab new`, `lab lock` and `lab run`; otherwise judged.*
6. **Record what was decided and why, in the lab's words.** A decision is written out of a conversation
   with the operator, and you show them the text as recorded. Their messages are not copied into the
   lab. Never record a decision that was not discussed with them. *Held by `lab decide`; that the
   record is faithful is judged.*
7. **Say what you are on.** The operator reads the site to know whether anything is happening, and
   should never have to ask you. When you start on a card or move to another, log it:
   `lab log <id> doing "<what>" "<why now>"`. The line stands on the front page until a result, a
   stuck line or a choice about the same card ends it. *Judged.*
