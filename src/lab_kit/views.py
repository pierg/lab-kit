"""The agent's views: the lab one level at a time, as plain text. The site draws the same record for the operator."""
from __future__ import annotations

import os

from . import record as R


def num(x):
    return f"{int(x):,}" if x == int(x) else f"{x:,.2f}".rstrip("0").rstrip(".")


def state(n):
    return n["state"] + (f", {n['outcome']}" if n.get("outcome") and n["state"] == "done" else "")


def line(l):
    return f"- {l['day']}{' ' + l['time'] if l.get('time') else ''} {l['about']} {l['kind']}: {l['what']}" + (f" So: {l['so']}" if l["so"] else "")


def decision_text(lab, d):
    """One decision, complete: what there is to discuss, or what was decided and why."""
    about = ", ".join(f"{i} {lab.nodes[i]['title']}" if i in lab.nodes else f"the resource {i}" for i in d["about"] if i in lab.nodes or i in lab.resources)
    when = f"decided {d['decided'].get('date')} with {d['decided'].get('with')}" if d["decided"] else "open: to discuss with the operator"
    out = [f"{d['id']} {d['title']} (raised {d.get('date')}, {when})" + (f"\nAbout: {about}" if about else "")]
    out += [f"{slot}. {R.flat(d['slots'][slot])}" for slot in ("Seen", "Options", "Recommendation", "Decided") if R.flat(d["slots"].get(slot, ""))]
    if d["state"] == "open":
        held = lab.held_by(d)
        out += ["Held until it is settled: " + (", ".join(f"{h['id']} {h['title']}" for h in held) or "nothing")]
        out += [f"To record what was decided: lab decide {d['id']} --with <name> \"<what was decided and why, in the lab's words>\""]
    return "\n".join(out)


def since(lab, day=None):
    lines, mark = lab.since(day)
    start = day or mark
    raised = [d for d in lab.decisions if not start or str(d.get("date")) >= str(start)]
    head = f"Since {day}" if day else (f"Since the last decision was recorded ({mark})" if mark else "Since the lab opened")
    if not lines and not raised:
        return f"{head}: nothing new."
    out = [head]
    for kind, title in (("result", "Results"), ("stuck", "Stuck"), ("agent", "Decided by the agent")):
        mine = [l for l in lines if l["kind"] == kind]
        if mine:
            out += ["", title] + [line(l) for l in mine]
    if raised:
        out += ["", "Decisions"] + [f"- {d.get('date')} {d['id']} ({d['state']}): {d['title']}" for d in raised]
    return "\n".join(out)


def resource_line(lab, name):
    r = lab.resources[name]
    if not lab.metered(name):
        return f"- {name}: {r.get('what', '')}"
    per = f"; one run may use {num(r['per_run'])}" if isinstance(r.get("per_run"), (int, float)) else ""
    return f"- {name}: {num(lab.used(name))} of {num(r['granted'])} {r.get('unit', '')} used{per}. {r.get('what', '')}"


def _now(lab):
    out = [f"{lab.cfg.get('title', lab.cfg['name'])}"] + [f"Goal {g['id']} ({g['state']}): {g['title']}. {g['description']}" for g in lab.live(lab.goals)]
    d, last = lab.doing(), lab.last_record()
    out += ["", "Right now, as the operator sees it"]
    out += [f"- on {d['about']} {lab.nodes[d['about']]['title']} since {d['day']} {d['time']}: {d['what']} Why now: {d['so']}"] if d else ["- no `doing` line is open: the site says nobody is on anything. When you start: lab log <id> doing \"<what>\" \"<why now>\""]
    out += [f"- last recorded activity: {last.strftime('%Y-%m-%d %H:%M')} UTC"] if last else []
    waiting = lab.open_decisions()
    out += ["", "To discuss with the operator"] + (["- nothing"] if not waiting else [])
    for d in waiting:
        out += [decision_text(lab, d), ""]
    going = [f"- {x['id']} {x['title']}: {r['id']}, started {r['started']}" for x in lab.experiments for r in x["runs"] + x["trials"] if r["state"] == "running" and not r["orphan"]]
    out += ["" if not waiting else None, "Running"] + (going or ["- nothing"])
    out += ["", "Yours next"] + ([f"- {x['id']} {x['title']} ({x['type']}): {x['next']}" for x in lab.yours()] or ["- nothing"])
    held = [f"- {x['id']} {x['title']}: on {x['next']}" for x in lab.items if x["state"] == "waiting" or (x["state"] == "planned" and not x["mine"])]
    out += ["", "Not yours to move yet"] + (held or ["- nothing"])
    out += ["", "Questions"]
    for q in lab.live(lab.questions):
        counts = {}
        for x in q["items"]:
            key = x["outcome"] if x["state"] == "done" and x.get("outcome") else x["state"]
            counts[key] = counts.get(key, 0) + 1
        out += [f"- {q['id']} ({q['state']}): {q['title']} [{', '.join(f'{n} {k}' for k, n in counts.items()) or 'nothing under it'}]"]
    if lab.resources:
        out += ["", "Resources"] + [resource_line(lab, name) for name in lab.resources]
    stuck = [f"- {r['id']}: {r['unpublished'].splitlines()[0]}" for r in lab.runs if r["unpublished"]]
    if stuck:
        out += ["", "Ended runs not yet in the store (`lab runs publish`)"] + stuck
    from . import history
    loose = history.uncommitted(lab)
    if loose:
        out += ["", "Not committed yet (git holds nothing it has not been given)"] + [f"- {l}" for l in loose]
    out += ["", "Last events"] + ([line(l) for l in lab.lines if l["kind"] != "doing"][-4:] or ["- none"])
    return "\n".join([o for o in out if o is not None] + ["", "More: lab show <id or path>   lab since   lab runs   lab define <term>"])


def tick(l):
    mark = {True: "holds", False: "does not hold", None: "not known yet"}[l["holds"]]
    value = f" ({l['row']['name']} = {l['row']['value']})" if l["row"] else ""
    return f"- {l['say']} [{l['test'] or 'NO TEST'}]: {mark}{value}"


def held(r):
    """What a run's folder holds, in one line: how many files, how many of them at the top, and how many under each
    folder there. Nothing is listed, so no folder is hidden and no list is cut short."""
    here, under = r["present"], {}
    for p in here:
        top = p.split("/", 1)[0] + "/" if "/" in p else ""
        under[top] = under.get(top, 0) + 1
    count = lambda n: f"{n:,} file{'' if n == 1 else 's'}"
    parts = ([f"{under['']:,} at the top"] if under.get("") else []) + [f"{under[d]:,} under {d}" for d in sorted(under) if d]
    gone = len(r["files"]) - len(here)
    return (f"{count(len(here))}" + (": " + ", ".join(parts) if parts else "")
            + (f". {count(gone)} it sealed {'is' if gone == 1 else 'are'} not here" if gone else ""))


def _show(lab, ident):
    if ident not in lab.nodes:  # a path, as the site's pages give it, names the node it belongs to
        found = lab.at(ident) if ("/" in ident or "." in os.path.basename(ident)) else None
        if not found:
            raise SystemExit(f"no {ident} in this lab" + ("; terms are under `lab define <term>`" if ident.endswith("GLOSSARY.md") else ""))
        return f"{ident} belongs to {found['id']}.\n\n" + _show(lab, found["id"])
    n = lab.nodes[ident]
    if n["type"] == "decision":
        return decision_text(lab, n)
    came = lambda x: [f"Came out of {x['from']} {lab.nodes[x['from']]['title']}."] if x.get("from") in lab.nodes else []
    raised = [d for d in lab.decisions if ident in d["about"]]
    if n["type"] == "goal":
        out = [f"{n['id']} ({n['state']}): {n['title']}", n["description"]] + came(n) + ["", f"Claim. {R.flat(n['slots'].get('Claim', '')) or 'not written yet'}", "", "Questions"]
        out += [f"- {q['id']} ({q['state']}): {q['title']}. {q['description']}" for q in n["questions"]]
        return "\n".join(out + ["", "More: lab show <question id>"])
    about = [l for l in lab.lines if l["about"] == ident or l["about"].startswith(ident + ".")]
    decisions = ["", "Decisions about it"] + [f"- {d['id']} ({d['state']}): {d['title']}" for d in raised] if raised else []
    if n["type"] == "question":
        out = [f"{n['id']} ({n['state']}): {n['title']}", f"Asks: {n['asks']}", n["description"]] + came(n) + [""]
        out += [f"{slot}. {lab.fill(R.flat(n['slots'].get(slot, '')))}\n" for slot, _ in R.SLOTS["question"]]
        out += ["Under it"] + ([f"- {x['id']} {x['type']} ({state(x)}): {x['title']}" + (f". Next: {x['next']}" if x["mine"] else "") for x in n["items"]] or ["- nothing yet"])
        out += decisions
        out += ["", "Needs: " + (", ".join(n["needs"]) or "nothing"), "", "Latest in the log"] + ([line(l) for l in about[-5:]] or ["- nothing"])
        return "\n".join(out + ["", "More: lab show <experiment or build id>"])
    if n["type"] == "reading":
        out = [f"{n['id']} reading ({n['state']}): {n['title']}", n["description"], "", "A reading is exploratory: it can suggest, never confirm. Its numbers are not results.", ""]
        out += [f"{slot}. {R.flat(n['slots'].get(slot, '')) or 'not written yet'}\n" for slot, _ in R.SLOTS["reading"]]
        out += [("Waiting on: " if not n["mine"] else "Next: ") + n["next"], ""] if n["next"] else []
        out += ["Needs: " + (", ".join(f"{i} ({lab.nodes[i]['state']})" for i in n["needs"] if i in lab.nodes) or "nothing")]
        return "\n".join(out + ["", f"Card: {n['path']}"])
    if n["type"] == "build":
        out = [f"{n['id']} build ({n['state']}): {n['title']}", n["description"], ""]
        out += [f"{slot}. {R.flat(n['slots'].get(slot, ''))}\n" for slot, _ in R.SLOTS["build"]]
        out += [("Waiting on: " if not n["mine"] else "Next: ") + n["next"], ""] if n["next"] else []
        out += ["Needs: " + (", ".join(f"{i} ({lab.nodes[i]['state']})" for i in n["needs"] if i in lab.nodes) or "nothing")]
        if n["commits"]:
            out += [f"Built in commits: {', '.join(map(str, n['commits']))}. Checked by: {', '.join(n['tests']) or 'nothing named'}"]
        return "\n".join(out + ["", f"Card: {n['path']}"])
    x = n
    out = [f"{x['id']} experiment ({state(x)}): {x['title']}", x["description"]]
    if x.get("replaces"):
        out += [f"Replaces {x['replaces']}: {x.get('because') or 'no reason given'}"]
    by = lab.replaced_by(x["id"])
    if by:
        out += [f"Replaced by {by['id']} {by['title']}."]
    if x.get("dropped"):
        out += [f"Dropped: {x['dropped']}"]
    out += ["", f"Compares. {R.flat(x['slots'].get('Compares', ''))}", "", "Arms"] + ([f"- {name}: {what}" for name, what in x["arms"]] or ["- none written yet"])
    out += ["", f"Cases. {R.flat(x['slots'].get('Cases', ''))}", ""]
    t = lab.ticks(x)
    for side, label in (("confirmed", "Confirmed if"), ("refuted", "Refuted if")):
        out += [label] + ([tick(l) for l in t[side]] or ["- no line yet"]) + [""]
    if x["outcome"]:
        out += [f"Outcome: {x['outcome']}", ""]
    for slot in ("Found", "Means"):
        if R.flat(x["slots"].get(slot, "")):
            out += [f"{slot}. {lab.fill(R.flat(x['slots'][slot]), x['id'])}", ""]
    if x["next"]:
        out += [("Next: " if x["mine"] else "Waiting on: ") + x["next"], ""]
    out += ["Needs: " + (", ".join(f"{i} ({lab.nodes[i]['state']})" for i in x["needs"] if i in lab.nodes) or "nothing")]
    if x["uses"]:
        out += ["Uses: " + ", ".join(f"{r}" + (f" (at most {num(lab.cap(x, r))} {lab.resources[r].get('unit', '')} a run)" if lab.metered(r) and lab.cap(x, r) is not None else "") for r in x["uses"] if r in lab.resources)]
        out += [f"  rule for {r}: {rule}" for r in x["uses"] for rule in (lab.resources.get(r) or {}).get("rules", [])]
    out += [f"Locked {x['lock']['locked']} at commit {str(x['lock'].get('commit') or 'none')[:8]}." if x["lock"] else "Not locked.", f"Folder: {x['dir']}  (plan in plan/)"]
    if x["reviews"]:
        out += ["", "Reviews"] + [f"- {r['date']} {r['stage']} {r['verdict']} ({r['by']}): {r['note']}" for r in x["reviews"]]
    if x["results"]:
        out += ["", "Results" + ("" if x["reviewed"] else " (not reviewed: not to be used on a card yet)")] + [f"- {r['name']} = {r['value']}" + (f", shown as {R.shown(r)}" if R.shown(r) != r["value"] else "") + f"  ({r.get('label') or 'no label'}; against: {r.get('versus', '')})" for r in x["results"]]
    for r in x["trials"] + x["runs"]:
        used = "".join(f", used {num(v)} {lab.resources.get(k, {}).get('unit', k)}" + (" (stated by hand when it was closed)" if k in (r.get("used_by_hand") or []) else "") for k, v in (r.get("used") or {}).items() if R.amount(v))
        out += ["", f"{'Trial run' if r['kind'] == 'trial' else 'Run'} {r['id']}: {r['state']}" + (f" (exit {r['exit']})" if r["state"] == "failed" else "") + f"{used}, {r['dir']}"]
        out += [f"  declared lost: {r['lost']}"] if r["lost"] else ["  listed in runs.tsv; its folder is not in the store here"] if r["missing"] else []
        out += [f"  closed by hand: {r['closed']}"] if r.get("closed") and not r["lost"] else []
        out += [f"  changed since {'the run before' if x['runs'] and r is not x['runs'][0] else 'the lock'}: {r['changed']}"] if r.get("changed") else []
        out += [f"  {held(r)}"] if r["files"] else []
    return "\n".join(out + decisions)


def _brief(lab, ident):
    """A question's briefing as text, in the order the operator asks. It is the question's page, said in chat."""
    q = lab.nodes.get(ident) or lab.question_of(ident)
    if q and q["type"] in R.STEPS:
        q = lab.nodes[q["question"]]
    if not q or q["type"] != "question":
        raise SystemExit(f"lab brief <question>: {ident} is not a question, or something under one")
    fill = lambda text, home=None: lab.fill(str(text or "").strip(), home)
    live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
    out = [f"**{q['title']}** ({q['id']}, {state(q)}). {q['asks']}", ""]
    before = [lab.nodes[i] for i in q["needs"] if i in lab.nodes]
    if before:
        out += ["**Where we are coming from.**"] + [f"- {n['title']} ({state(n)}): {R.flat(fill(n['slots'].get('So far', ''))).replace(' - ', ' ')}" for n in before] + [""]
    out += ["**Why we ask.** " + q["description"], ""]
    if R.flat(q["slots"].get("How we would know", "")):
        out += ["**How it works.** " + fill(q["slots"]["How we would know"]), ""]
    out += ["**Where it stands.** " + fill(q["slots"].get("So far", "")), "", "**The steps.**"]
    for n, x in enumerate(live, 1):
        where = (fill(x["slots"].get("Means", ""), x["id"]) if x["type"] == "experiment" and x["state"] == "done" else fill(x["slots"].get("Suggests", "")) if x["type"] == "reading" and x["state"] == "done" else ("next, for the agent: " if x["mine"] else "waiting on ") + x["next"] if x["next"] else "")
        out += [f"{n}. **{x['title']}** ({x['type']}, {state(x)}). {x['description']}" + (f" {R.flat(where)[0].upper() + R.flat(where)[1:]}." if where and x["state"] != "done" else f" {R.flat(where)}" if where else "")]
    tests = [x for x in live if x["type"] == "experiment"]
    costs = []
    for x in tests:
        for name in x["uses"]:
            if lab.metered(name):
                unit, cap = lab.resources[name].get("unit", ""), lab.cap(x, name)
                costs.append(f"- {x['title']}: {num(lab.spent(x, name))} {unit} of {name} used" + (f", one more run may use up to {num(cap)}" if isinstance(cap, (int, float)) and not x["finished"] else "") + (f". {x['cost']}" if x.get("cost") and x["state"] != "done" else ""))
    if costs:
        left = "; ".join(f"{name}: {num(lab.left(name))} of {num(lab.resources[name]['granted'])} {lab.resources[name].get('unit', '')} left" for name in dict.fromkeys(r for x in tests for r in x["uses"] if lab.metered(r)))
        out += ["", "**What it costs.**"] + costs + [f"- {left}"]
    limits = [f"- {x['title']}: " + " ".join(R.items(x["slots"]["Limits"]) or [R.flat(x["slots"]["Limits"])]) for x in tests if R.flat(x["slots"].get("Limits", ""))]
    if limits:
        out += ["", "**What it cannot show.**"] + limits
    talk = [d for d in lab.open_decisions() if any(a == q["id"] or a.startswith(q["id"] + ".") for a in d["about"] + d["holds"])]
    if talk:
        out += ["", "**What is needed from you.**"] + [f"- {d['id']} {d['title']}: {R.flat(d['slots'].get('Seen', ''))} Recommendation: {R.flat(d['slots'].get('Recommendation', ''))}" for d in talk]
    out += ["", "**Where to look.**"] + [f"- {x['title']}: {x['dir']}/" + (" (plan in plan/)" if x["type"] == "experiment" else "") for x in live]
    return "\n".join(out)


def define(lab, term):
    hits = [g for g in lab.glossary if g["term"].lower() == term.lower()] or [g for g in lab.glossary if term.lower() in g["term"].lower()]
    if not hits:
        raise SystemExit(f"{term!r} is not in the glossary")
    return "\n\n".join(f"{g['term']}: {g['definition']}" + (f"\n  code: {g['code']}" if g["code"] else "") for g in hits)


def now(lab):
    return R.bare(_now(lab))


def show(lab, ident):
    return R.bare(_show(lab, ident))


def brief(lab, ident):
    """The briefing keeps its emphasis, which chat renders, and says each link as its words."""
    import re
    return re.sub(r"\[([^\]\n]+)\]\([^)\s]+\)", r"\1", _brief(lab, ident))
