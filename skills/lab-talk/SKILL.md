---
name: lab-talk
description: >-
  Talk with the operator about the lab: tell them where it stands, explain something, bring a
  decision to them, and record what was decided. Use when they ask "what's going on", "where are
  we", "what's new", "what's next", "explain this", "what do you want to discuss", when they paste
  an id or a path from the lab, when `lab now` shows something under "To discuss with the operator",
  and when they decide something ("let's do X", "drop that", "use the other machine").
---

# lab-talk

The operator reads the site and decides direction and resources in conversation with you. You answer
from the record, shortest first. A decision is a discussion, not a request for a yes.

## Telling them where things stand

| They ask | Run |
|---|---|
| where are we, what's going on, what's next, are you working | `lab now` |
| what's new, the latest results | `lab since` |
| what are we doing on X, why, what does it cost, where are the files | `lab brief <question>` |
| why are we doing this at all | `lab show <goal>` |
| what is this (an id or a pasted path) | `lab show <id or path>` |
| what does a word mean | `lab define <term>` |

- The answer first, in one or two sentences, then what it rests on: the result, by its label and value.
- Plain words. No id without its title. A glossary term is used as the glossary defines it.
- For "where are we": each goal in a line, each open question with what is known so far, what is
  running, what is next, what there is to discuss. No more than a screen.
- `lab brief` is the question's page as text. Give it as it is, cut to what they asked. If what you
  want to say is not in it, the card is missing something: fix the card, then answer.
- If the record does not say, say so. Never fill a gap from memory.
- Change nothing while you brief.

## Bringing a decision to them

`lab now` prints every open decision in full. Take them one at a time, oldest first.

1. Say what was seen and why it matters now, with the numbers, shown here in the conversation.
2. Lay out the options, each with what it costs and what it changes, and say which you recommend
   and why.
3. Discuss. Answer their questions from the record. Take their ideas seriously: an option they add
   is an option. If the discussion changes the options, rewrite the card's Options before deciding.
4. When it is settled, write what was decided and why, in the lab's words, in two to four sentences:
   `lab decide <decision> --with <their name> "<what was decided and why>"`.
5. Show them the sentence you recorded. If they correct it, the correction is a new decision.
6. Make what follows: `lab new goal|question ... --from <decision>`, a change to `resources.toml`,
   an override on an experiment. Then go on with the lab-work skill.

A decision that will change an amount, add a resource or allow one experiment a higher cap lists
that resource or that experiment under `about:` before it is decided: `lab new decision "<title>"
--about <resource or id>`. What a settled decision is about cannot be changed afterwards, and a
resource's new amount names the decision in `from`.

## When they decide something nobody raised

`lab new decision "<what it is about>" --about <id>`, fill **Seen** with what prompted it, then
`lab decide` as above, and do it.

When they set a question aside: "not now, maybe later" parks it, "never" drops it. Ask which, if it is not
clear. To park, list the question under `parks:` and `about:` on the decision before `lab decide`, and say in
the Decided text why and what would bring it back. To bring one back, a new decision lists it under
`unparks:`. To close a goal, put `reached: true` or `dropped: <why>` on its card, out of a decision.

## Rules

- Never copy the operator's messages into the lab. The record says what was decided and why.
- Never record a decision that was not discussed with them in this conversation, and never read
  silence or a general "go on" as a decision on something they have not been shown.
- Never bring them something that is yours to decide, and never ask them to check your work, to
  confirm a plan already settled, or to run a command.
- A decision holds only what its card lists under `holds:`. Keep working on everything else.
- Two things hold for them as for you: a locked plan is changed by a new experiment that replaces
  it, and an outcome is worked out from the results.
