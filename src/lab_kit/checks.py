"""`lab check`: what can be held mechanically. Whether the record is honest is the review's job."""
from __future__ import annotations

import os, re

from . import history, record as R, runs as runs_, write

KEYS = {  # what a card's front matter may hold; a state is never among them
    "goal": {"title", "from", "reached", "dropped", "see"},
    "question": {"title", "asks", "from", "needs", "answer", "answered", "dropped", "see"},
    "experiment": {"title", "needs", "uses", "override", "replaces", "because", "cost", "waiting_on", "dropped", "see"},
    "build": {"title", "needs", "commits", "tests", "dropped", "see"},
    "reading": {"title", "needs", "dropped", "see"},
    "decision": {"title", "about", "date", "holds", "parks", "unparks", "order", "decided", "see"},
}


def run(lab, rederive=True):
    """Every problem, notes on what could not be checked here, and whether anything was left unchecked."""
    problems, notes, unchecked = list(lab.problems), [], False
    bad = lambda check, where, what: problems.append(f"{check}: {where}: {what}")
    nodes, root = lab.nodes, lab.root
    library = os.path.join(root, lab.cfg.get("library", "docs"), "content")
    here = os.path.isdir(lab.store)
    if not here:
        notes.append("the store is not here: runs and re-derivation were not checked")
        unchecked = True

    absent = {}  # the libraries the charter names whose folder is not on this machine

    def see(where, page, who=""):
        """A page a card's `see:` or a glossary entry's `- see:` names is there."""
        if ":" in str(page):  # a page of another library the charter names, such as background reading
            from . import site
            name, _, path = str(page).partition(":")
            lib = site.libraries(lab).get(name)
            if not lib:
                bad("links", where, f"{who}see names {page}, which is not a page of a library the charter names")
            elif not os.path.isdir(lib["path"]):  # the other library is not on this machine, as in CI: nothing to look in
                absent.setdefault(name, lib["path"])
            elif not os.path.exists(os.path.join(lib["path"], path.lstrip("/"))):
                bad("links", where, f"{who}see names {page}, and the library {name} holds no such page")
        elif not os.path.exists(os.path.join(library, str(page).split("#")[0], "index.html")):
            bad("links", where, f"{who}see names the page {page}, which is not in the library")

    # cards: each has its slots, stays short, and writes only what is its to write
    for n in lab.goals + lab.questions + lab.items + lab.decisions:
        try:
            fm_keys = {str(k) for k in R.card(os.path.join(root, n["path"]))[0]}
        except Exception:  # already reported when the lab was read
            fm_keys = set()
        for key in sorted(fm_keys - KEYS[n["type"]] - {"id", "status", "state", "outcome"}):
            bad("cards", n["path"], f"`{key}:` is not something a {n['type']} card holds")
        for slot, budget in R.SLOTS.get(n["type"], ()):
            if slot not in n["slots"] and (n["type"], slot) not in R.OPTIONAL:
                bad("cards", n["path"], f"missing slot {slot}")
            elif len(n["slots"].get(slot, "").split()) > budget:
                bad("cards", n["path"], f"{slot} is {len(n['slots'][slot].split())} words, budget {budget}")
        if not str(n.get("title") or "").strip() or n["title"] == n["id"]:
            bad("cards", n["path"], "has no title")
        if n["type"] in R.DESCRIPTION:
            words = len(str(n.get("description") or "").split())
            if not words:
                bad("cards", n["path"], "has no description: one or two sentences, under the front matter, on what it is and why it is there")
            elif words > R.DESCRIPTION[n["type"]]:
                bad("cards", n["path"], f"its description is {words} words, budget {R.DESCRIPTION[n['type']]}")
        if n["type"] in ("goal", "question") and nodes.get(str(n.get("from")), {}).get("type") != "decision":
            bad("links", n["path"], f"`from:` names the decision it came out of; {n.get('from')!r} is not one")
        for page in n.get("see") or []:
            see(n["path"], page)
        if n["type"] == "goal":  # the words a goal lists are names; GLOSSARY.md is the only place a word is defined
            for w in lab.vocabulary(n):
                if not w["entry"]:
                    bad("cards", n["path"], f"Vocabulary lists {w['name']!r}, which is not a term in GLOSSARY.md: add it there first, and list the name only")
                elif w["old"]:
                    bad("cards", n["path"], f"Vocabulary lists {w['name']!r} with a meaning: list the name only, `- {w['name']}`; GLOSSARY.md defines it")
    for g in lab.glossary:
        if g["see"]:
            see("GLOSSARY.md", g["see"], f"{g['term']}: ")
    for name, path in sorted(absent.items()):
        notes.append(f"the library {name} is not here ({path}): the pages cards and the glossary name in it under `see:` could not be checked here")
        unchecked = True
    for d in {os.path.dirname(x["path"]) for x in lab.items}:
        if sum(os.path.exists(os.path.join(root, d, f"{kind}.md")) for kind in R.STEPS) > 1:
            bad("tree", d, "holds more than one of an experiment, a build and a reading; a folder is one of them")

    # links: every edge lands
    for q in lab.questions:
        for need in q["needs"]:
            if nodes.get(need, {}).get("type") != "question":
                bad("links", q["path"], f"needs {need}, which is not a question")
        if q.get("answer") is not None and q.get("answer") not in ("yes", "no"):
            bad("cards", q["path"], "`answer:` is yes or no, written by `lab answer`")
        if q.get("answer") in ("yes", "no"):  # what `lab answer` requires holds for an answer however it got on the card
            waiting = [x["id"] for x in q["items"] if x["state"] not in ("done", "built", "replaced", "dropped")]
            if waiting:
                bad("questions", q["path"], f"is answered while {', '.join(waiting)} is not done")
            if not any(x["state"] == "done" and x["type"] == "experiment" for x in q["items"]):
                bad("questions", q["path"], "is answered with no finished experiment to rest the answer on; a reading suggests and answers nothing")
            if not R.day(q.get("answered")) or not any(l["about"] == q["id"] and l["kind"] == "agent" and l["what"].startswith(f"Answered {q['id']} {q['answer']}.") for l in lab.lines):
                bad("questions", q["path"], "its answer was not recorded by `lab answer`: the log holds no line for it, or the card no `answered:` day")
        elif q.get("answered") is not None:
            bad("cards", q["path"], "`answered:` is written by `lab answer`, with the answer")
    for x in lab.items:
        for need in x["needs"]:
            if nodes.get(need, {}).get("type") not in R.STEPS:
                bad("links", x["path"], f"needs {need}, which is not an experiment, a build or a reading")
    for n in lab.questions + lab.items:  # nothing needs itself, directly or through what it needs
        seen, todo = set(), list(n["needs"])
        while todo:
            i = todo.pop()
            if i == n["id"]:
                bad("links", n["path"], "needs itself, directly or through what it needs")
                break
            if i not in seen and i in nodes:
                seen.add(i)
                todo += nodes[i].get("needs") or []
    for b in lab.builds:
        if b["commits"] and not b["tests"]:
            bad("cards", b["path"], "is built with no test named: `tests:` says how we know it works")
    for d in lab.decisions:
        for key in ("about", "holds"):
            for i in d[key]:
                if nodes.get(i, {}).get("type") not in ("goal", "question") + R.STEPS and not (key == "about" and i in lab.resources):
                    bad("links", d["path"], f"{key} names {i!r}, which does not exist")
        for key in ("parks", "unparks"):  # only a question is parked, and a decision that parks it or brings it back is about it
            for i in d[key]:
                if nodes.get(i, {}).get("type") != "question":
                    bad("links", d["path"], f"{key} names {i!r}, which is not a question: only a question is parked")
                elif i not in d["about"]:
                    bad("links", d["path"], f"{key} names {i}, which is not under `about:`: a decision that parks a question or brings it back is about it")
        for i in sorted(set(d["parks"]) & set(d["unparks"])):
            bad("links", d["path"], f"both parks and unparks {i}")
        for i in d["order"]:  # the order of the work names what it orders: goals, questions and steps, each once
            if nodes.get(i, {}).get("type") not in ("goal", "question") + R.STEPS:
                bad("links", d["path"], f"order names {i!r}, which is not a goal, a question or a step of the lab")
        for i in sorted({i for i in d["order"] if d["order"].count(i) > 1}):
            bad("links", d["path"], f"order names {i} more than once: each has one place")
        done = d["decided"]
        if done and not ({"date", "with"} <= set(done) and R.flat(d["slots"].get("Decided", ""))):
            bad("cards", d["path"], "a settled decision holds when, with whom, and what was decided and why under Decided")
        if not done and d["slots"].get("Decided"):
            bad("cards", d["path"], "holds a Decided that `lab decide` did not record")
        if len(d["slots"].get("Decided", "").split()) > R.DECIDED:
            bad("cards", d["path"], f"Decided is {len(d['slots']['Decided'].split())} words, budget {R.DECIDED}")
        if not R.flat(d["slots"].get("Seen", "")):
            bad("cards", d["path"], "does not say what was seen")

    # experiments: lines, locks, runs, results
    for x in lab.experiments:
        p, d = x["path"], os.path.join(root, x["dir"])
        if x.get("replaces"):
            old = nodes.get(x["replaces"])
            if not old or old["type"] != "experiment" or old["question"] != x["question"] or old["id"] == x["id"]:
                bad("links", p, f"replaces {x['replaces']}, which is not another experiment of its question")
            elif x["id"] in [o["id"] for o in lab.chain(x)]:
                bad("links", p, f"replaces {x['replaces']}, which replaces it in turn: a replacement is newer than what it replaces")
            if not R.flat(x.get("because") or ""):
                bad("cards", p, f"replaces {x['replaces']} and does not say why: `because:` holds one sentence the operator can read")
        elif x.get("because"):
            bad("cards", p, "`because:` says why an experiment was replaced, and this one replaces none")
        for name in x["uses"]:
            if name not in lab.resources:
                bad("resources", p, f"uses {name}, which resources.toml does not list")
            elif lab.resources[name].get("retired") and x["state"] not in ("done", "replaced", "dropped") and not x["finished"]:
                bad("resources", p, f"uses {name}, which is retired: {lab.resources[name]['retired']}")
        for name, cap in x["override"].items():
            if name not in x["uses"]:
                bad("resources", p, f"override {name}: an override is a cap on a resource the experiment uses")
            elif lab.metered(name) and isinstance(lab.resources[name].get("per_run"), (int, float)) and cap > lab.resources[name]["per_run"] and not lab.settled_for(x["id"]) and x["lock"]:
                bad("resources", p, f"its cap on {name} is above what one run may use, with no settled decision about it")
        for side in ("confirmed", "refuted"):
            if len(x["lines"][side]) > 6:
                bad("cards", p, f"{side}-if has {len(x['lines'][side])} lines; more than six is more than one experiment")
        if sum(l.get("role") == "answer" for l in x["lines"]["confirmed"]) > 1:
            bad("cards", p, "more than one confirmed-if line is marked `answer:`; an experiment has one answer, and the other bars say when it can be read or when it counts")
        links = R.symlinks(os.path.join(d, "plan"))
        if links:
            bad("locks", p, f"plan/ holds a link, {links[0]}: what a link points at is not in plan/ and is not pinned")
        stray = R.compiled(os.path.join(d, "plan")) if (x["lock"] or {}).get("kit") != "1.0.0" else []  # 1.0.0 hashed such a file with the plan
        if stray:
            bad("locks", p, f"plan/ holds a compiled file outside __pycache__, {stray[0]}: Python would import it, and a `.pyc` is not pinned")
        if x["lock"]:
            if lab.nodes[x["question"]]["state"] == "under discussion":
                bad("locks", p, f"is locked under {x['question']}, whose decision is not settled")
            if not x["lock"].get("unreadable") and not lab.lock_holds(x):
                bad("locks", p, "what it demands (a bar's result, comparison or number, an arm's name) or the resources it uses changed after the lock; that is a new experiment")
            for l in x["lines"]["confirmed"] + x["lines"]["refuted"]:
                if not l["test"]:
                    bad("locks", p, f"the line {l['say']!r} has no test")
            if not x["lines"]["refuted"]:
                bad("locks", p, "is locked with no refuted-if line")
            if any(lab.metered(r) for r in x["uses"]) and not any(r.get("stage") == "plan" and r.get("verdict") == "pass" for r in x["reviews"]):
                bad("locks", p, "uses a metered resource and was locked with no passed review of its plan")
            if x["finished"] and x["finished"].get("plan") and not lab.plan_is(x, x["finished"]["plan"], x["finished"]["how"]):
                bad("locks", p, f"plan/ changed after {x['finished']['id']}, the run its results come from; the apparatus of a finished run stays as it ran")
            ran = [r for r in x["runs"] if not r["missing"]]
            if ran and x["lock"].get("plan") and ran[0]["how"] == x["lock"]["hash"] and lab.plans_differ(x, ran[0].get("plan"), x["lock"]["plan"], ran[0]["how"]) and not R.flat(ran[0].get("changed") or ""):
                bad("runs", ran[0]["dir"], "ran a plan/ that differs from the one that was locked and does not say what changed and why")
            for before, after in zip(ran, ran[1:]):
                if before["how"] == after["how"] and lab.plans_differ(x, before.get("plan"), after.get("plan"), after["how"]) and not R.flat(after.get("changed") or ""):
                    bad("runs", after["dir"], f"ran a plan/ that differs from {before['id']}'s and does not say what changed and why")
        finished = [r for r in x["runs"] if r["state"] == "finished"]
        if len(finished) > 1:
            bad("runs", p, f"has {len(finished)} finished runs; the first is the only source of results")
        for r in x["runs"] + x["trials"]:
            where = f"{r['dir']}"
            listed = x["listed"].get(r["id"])
            if r["missing"]:  # runs.tsv is in git and the store is not: a run the ledger lists stays where it was sealed
                if here and not r["lost"]:
                    bad("runs", where, f"is listed in {x['dir']}/runs.tsv and is not in the store: a run is never removed. If it started and its folder is gone for good, `lab runs lost {r['id']} \"<why>\"` records that")
                continue
            if listed and listed["lost"]:
                bad("runs", where, "was declared lost, and its folder is here: a run that is here is closed or published, not lost")
            if not listed or not listed["started"]:
                bad("runs", where, f"is not listed in {x['dir']}/runs.tsv: `lab run` lists every run when it starts")
            elif r["state"] != "running" and not listed["ended"]:
                bad("runs", where, "has ended, and runs.tsv does not hold its seal yet: `lab runs publish` records it")
            elif r["state"] != "running" and (listed["seal"] != r.get("seal") or listed["exit"] != r.get("exit") or listed["kind"] != r["kind"]):
                bad("runs", where, "is not the run that runs.tsv recorded when it ended: its seal or its exit differs")
            if r.get("used_refused"):
                bad("resources", where, str(r["used_refused"]))
            for name, v in (r.get("used") or {}).items():
                if not R.amount(v):
                    bad("resources", where, f"records {v!r} as what it used of {name}: an amount is a number, finite and not negative")
            if r["orphan"]:
                bad("runs", where, "its process is gone and it was never closed: `lab runs close`")
            if r["kind"] == "trial":
                if x["lock"] and r["id"] not in (x["lock"].get("trials") or []):  # the lock lists the trials that existed
                    bad("runs", where, "is a trial run started after the lock")
            elif not x["lock"] or (r.get("lock") or {}).get("card") != x["lock"]["card"] or r["started"] < x["lock"]["locked"]:
                bad("runs", where, "did not run under this experiment's lock")
            if r["state"] != "running":
                if not r["local"] or os.path.isdir(os.path.join(root, r["dir"])):
                    why = runs_.verify(os.path.join(root, r["dir"]))
                    if why:
                        bad("runs", where, why)
                for name, cap in (r.get("cap") or {}).items():
                    used = (r.get("used") or {}).get(name)
                    if used is None:
                        bad("resources", where, f"ran on {name} and did not record what it used (`$LAB_RUN/used.json`)")
                    elif R.amount(used) and R.amount(cap) and used > cap:
                        bad("resources", where, f"used {used:g} of {name}, above its cap of {cap:g}")
        for r in x["reviews"]:
            if r["stage"] not in ("plan", "results") or r["verdict"] not in ("pass", "fail") or not R.day(r["date"]) or not r["of"]:
                bad("reviews", p, f"a row of reviews.tsv is not one `lab review` wrote: {R.flat(' '.join(r.values()))[:60]!r}")
                break
        if x["results"]:
            if not x["lock"] or not x["finished"]:
                bad("results", p, "has results with no locked plan and finished run behind them")
            names = [r.get("name") for r in x["results"]]
            for r in x["results"]:
                if not r.get("name") or names.count(r["name"]) > 1:
                    bad("results", p, f"the result name {r.get('name')!r} is missing or used twice")
                if r["num"] is None:
                    bad("results", p, f"{r.get('name')}: its value {r.get('value')!r} is not a number")
                if not (r.get("command") or "").strip():
                    bad("results", p, f"{r.get('name')}: has no command that prints it")
                elif "RUN" not in re.findall(r"\$\{?(\w+)", r["command"]):
                    bad("results", p, f"{r.get('name')}: its command never reads `$RUN`, so it does not print the number from the sealed run")
                if not (r.get("label") or "").strip():
                    bad("results", p, f"{r.get('name')}: has no label saying in plain words what the number is")
                if (r.get("reads") or "") not in R.READS:
                    bad("results", p, f"{r.get('name')}: reads {r.get('reads')!r}; it is percent, points or empty")
            verdict, fresh = lab.reviewed(x, "results")
            if verdict == "pass" and not fresh:
                bad("results", p, "its results or its run changed after the review that passed them")
        elif any(R.flat(x["slots"].get(k, "")) for k in ("Found", "Means")):
            bad("cards", p, "says what was found with no result behind it")
        if x["state"] == "review failed" and (R.flat(x["slots"].get("Found", "")) or R.flat(x["slots"].get("Means", ""))):
            bad("cards", p, "its results failed their review, so the card says nothing was found: replace the experiment")
    for r in lab.runs:
        if r.get("experiment") not in nodes:
            bad("runs", r["dir"], f"belongs to {r.get('experiment')}, which does not exist")

    # names: a card names a result, and never types its number
    every = list(lab.results.values())
    for n in lab.questions + lab.experiments:
        home = n["id"] if n["type"] == "experiment" else None
        for slot in ("So far", "Found", "Means"):
            text = n["slots"].get(slot, "")
            for written, row in lab.named(text, home):
                if not row:
                    bad("names", n["path"], f"{slot} names {written}, which is not a result" + ("" if home or ":" in written else " (a question names it in full: {G1.Q1.2:name})"))
                elif not row["usable"]:
                    state = nodes[row["experiment"]]["state"]
                    bad("names", n["path"], f"{slot} names {written}, whose experiment is {state}" + ("" if state in ("replaced", "dropped", "review failed") else " and not yet reviewed"))
            typed = set(re.findall(r"(?<![\w.{:])\d+\.\d+%?", R.NAMED.sub("", text)))
            for row in every:
                forms = {row["value"], R.shown(row).split(" ")[0].lstrip("+\u2212")}
                if row["num"] is not None and typed & forms and (home is None or row["experiment"] == home):
                    bad("names", n["path"], f"{slot} types {sorted(typed & forms)[0]}, which is the result {row['ref']}: name it as {{{row['ref'] if home is None else row['name']}}}")

    # log
    for l in lab.lines:
        where = f"log.md line {l['line']}"
        if l["kind"] not in R.KINDS:
            bad("log", where, f"kind {l['kind']!r}; one of {', '.join(R.KINDS)}")
        kind = nodes.get(l["about"], {}).get("type")
        if l["kind"] == "doing" and not l["so"]:
            bad("log", where, "a `doing` line says why now, after what the agent is starting on")
        if kind is None or (kind == "decision") != (l["kind"] == "decision"):
            bad("log", where, f"is about {l['about']!r}: a decision line is about its decision, any other about a goal, a question, an experiment, a build or a reading")

    # resources
    for name, r in lab.resources.items():
        if not isinstance(r, dict) or not str(r.get("what") or "").strip():
            bad("resources", "resources.toml", f"{name}: says what it is, in `what`")
            continue
        if any(k in r for k in ("granted", "per_run", "unit")) and not (lab.metered(name) and str(r.get("unit") or "").strip()):
            bad("resources", "resources.toml", f"{name}: a metered resource has a `unit` and a `granted` amount")
        other = r.get("other_use") or []
        if not isinstance(other, list) or len(lab.other_use(name)) != len(other) or (other and not lab.metered(name)) or any(not R.day(o.get("date")) or not str(o.get("what") or "").strip() for o in lab.other_use(name)):
            bad("resources", "resources.toml", f"{name}: each `other_use` entry of a metered resource has a `date` (2026-01-02), an `amount` and `what` it was")
        if lab.metered(name) and not lab.granted_by(name):
            bad("resources", "resources.toml", f"{name}: its amounts come out of a decision: `from = \"D<n>\"` names the settled decision that set them, and that decision lists {name} under `about:`")
        elif "from" in r and not lab.metered(name) and nodes.get(r["from"], {}).get("type") != "decision":
            bad("resources", "resources.toml", f"{name}: `from` names a decision, and {r['from']!r} is not one")
        if lab.metered(name) and lab.used(name) > r["granted"]:
            bad("resources", "resources.toml", f"{name}: {lab.used(name):g} {r.get('unit', '')} used, {r['granted']:g} granted")

    # glossary
    terms = [g["term"].lower() for g in lab.glossary]
    for t in sorted({t for t in terms if terms.count(t) > 1}):
        bad("glossary", "GLOSSARY.md", f"{t!r} is defined twice")

    # clean: the plans and the store stay out of default searches
    ignore = R.read(f"{root}/.ignore") if os.path.exists(f"{root}/.ignore") else ""
    if "plan/" not in ignore or "runs/" not in ignore:
        bad("clean", ".ignore", "plan/ and runs/ are not kept out of default searches")

    # method: what the kit installed is still what the kit ships
    pairs = [("method/METHOD.md", ".lab/METHOD.md")] + [(f"agents/{a}", f".agents/agents/{a}") for a in sorted(os.listdir(os.path.join(write.DATA, "agents")))]
    pairs += [(f"skills/{s}/SKILL.md", f".agents/skills/{s}/SKILL.md") for s in sorted(os.listdir(os.path.join(write.DATA, "skills")))]
    for src, dst in pairs:
        mine, kit = os.path.join(root, dst), os.path.join(write.DATA, src)
        if not os.path.exists(mine) or R.read(mine) != R.read(kit):
            bad("method", dst, "differs from the installed kit: run `lab init` to restore it, and put local rules in AGENTS.md")

    waiting = [r for r in lab.runs if r["local"] and r["state"] != "running"]
    if waiting:
        notes.append(f"{len(waiting)} ended run(s) are still on this machine, not in the store: `lab runs publish`")
    found, said = history.check(lab)
    said += history.uncommitted(lab)  # not held by git yet: a note, and a failure when the check is strict
    problems += found
    notes += said
    unchecked = unchecked or bool(said)
    if rederive and here:
        again, n = write.rederive(lab)
        problems += again
        if n:
            notes.append(f"{n} result(s) re-derived")
    return sorted(set(problems)), notes, unchecked


def summary(lab):
    done = sum(x["state"] == "done" for x in lab.experiments)
    return (f"{len(lab.goals)} goals, {len(lab.questions)} questions, {len(lab.experiments)} experiments ({done} done), {len(lab.builds)} builds, {len(lab.readings)} readings, "
            f"{len(lab.results)} results, {len(lab.runs)} runs, {len(lab.decisions)} decisions, {len(lab.lines)} log lines")
