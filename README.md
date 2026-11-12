# lab-kit

lab-kit keeps a research lab that coding agents work in. It fixes what the lab's record looks like,
the method that makes a number count, and one command, `lab`, that both keeps the rules and shows
the lab to an agent a level at a time. [folio](https://github.com/pierg/folio) serves the same
record to the operator as a live site: `lab_kit.site` draws the pages, and nothing is generated.

## Two readers

- **The operator** decides direction and resources, in conversation with the agent, and reads the
  lab as a site. Nothing else reaches them.
- **The agent** plans, builds, runs and records, and decides everything else.

## One tree

```
Goal           what the lab wants to be able to say
  Question     a yes-or-no question: what we expect, what would prove us wrong, what we know so far
    Build      something an experiment needs that has to be made first
    Reading    a look at what already exists: it suggests, and never confirms
    Experiment what is compared, what would confirm, what would refute; then what was found
      Run      one try at producing what the experiment demands; the first that finishes counts
      Result   one number from that run, with the command that prints it again
Decision       something discussed with the operator: what was seen, the options, what was decided and why
```

Every id spells the path: `G1.Q2.3`. Cards are small and written for the operator. Nothing computed is
kept: every state, and an experiment's outcome, is worked out from the record when it is asked for.

## How a number counts

```
write the card -> lock -> run -> result -> review -> the number may be used on a card
```

Each arrow is a command that refuses when the step before it is missing. An experiment's lines, each
with the result it tests, are locked before its run. The first run that finishes is the only source
of its results. The reviewer is a separate session that did not do the work. Every run is listed in a file
that git keeps, so one cannot be removed or rewritten quietly.

## Install

```text
uv tool install lab-kit-cli
lab init
```

Then ask your agent to follow `.agents/skills/lab-set-up/SKILL.md`. `lab --help` lists the fifteen
commands.

The command needs Python 3.10 or later and nothing of folio. The site does: install `lab-kit-cli[site]`
where folio serves the lab, which brings `folio-kb` 0.5.0 or later, and list `lab_kit.site` under
`views:` in the charter of the lab's `docs/` library.

## Read more

- [docs/model.md](docs/model.md): the contract. What you read, how a number becomes a result, who decides, the commands, the files.
- [method/METHOD.md](method/METHOD.md): the seven rules every lab keeps.
- [skills/](skills/): lab-set-up, lab-work, lab-review and lab-talk. [agents/](agents/): the reviewer.
