"""The commands that change a lab: each validates first, writes the least it can, and says what it wrote."""
from __future__ import annotations

import datetime, json, os, re, shutil, subprocess

from . import __version__, record as R

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_data")
if not os.path.isdir(DATA):  # run from a checkout: the method, skills and roles sit at the repository root
    DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def today():
    if os.environ.get("LAB_TESTING") and os.environ.get("LAB_TODAY"):  # a test may fix the date; nothing else may
        return os.environ["LAB_TODAY"]
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def clock():
    """The time of day a log line is written at, in UTC like every time the lab records."""
    if os.environ.get("LAB_TESTING") and os.environ.get("LAB_CLOCK"):
        return os.environ["LAB_CLOCK"]
    return datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M")


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower().replace("'", "")).strip("-")[:48].strip("-")


def stop(msg):
    raise SystemExit(msg)


CARDS = {  # the description is the paragraph between the front matter and the first slot
    "goal": "---\ntitle: {title}\nfrom: {origin}\n---\n\n\n\n## Claim\n\n\n## Example\n\n\n## Approach\n\n\n## Roles\n\n\n## Vocabulary\n\n",
    "question": "---\ntitle: {title}\n{asks}from: {origin}\nneeds: []\n---\n\n\n\n## How we would know\n\n\n## Example\n\n\n## We expect\n\n\n## Wrong if\n\n\n## So far\n\nNothing has been run.\n",
    "experiment": "---\ntitle: {title}\nneeds: []\nuses: []\n{extra}---\n\n{description}\n\n## So far\n\n\n## Compares\n\n{Compares}\n\n## Arms\n\n{Arms}\n\n## Cases\n\n{Cases}\n\n## Confirmed if\n\n{Confirmed if}\n\n## Refuted if\n\n{Refuted if}\n\n## Outcomes\n\n{Outcomes}\n\n## Limits\n\n{Limits}\n\n## Found\n\n\n## Means\n\n",
    "build": "---\ntitle: {title}\nneeds: []\ncommits: []\ntests: []\n---\n\n\n\n## How it works\n\n\n## Works when\n\n",
    "reading": "---\ntitle: {title}\nneeds: []\n---\n\n\n\n## Looks at\n\n\n## Seen\n\n\n## Suggests\n\n",
    "decision": "---\ntitle: {title}\nabout: [{about}]\ndate: {today}\nholds: []\n---\n\n## Seen\n\n\n## Options\n\n\n## Recommendation\n\n",
}
RESOURCES = """# What the lab may touch outside itself, set by the operator. One table per resource.
#
# [gpu]
# what = "one GPU machine at the cloud provider"
# key = "CLOUD_TOKEN, kept in the secrets repository"    # where the key is kept, never the key
# unit = "GPU-hours"                                      # a metered resource has a unit, a grant and an amount for one run
# granted = 40
# per_run = 4
# from = "D1"                                             # the settled decision that set these amounts, and lists `gpu` under its `about:`
#
# An amount changes only together with `from`, which then names the later decision that changed it. A resource is never
# removed: one that is no longer used gets `retired = "<why>"`. Use outside a run is a row added under `other_use`, and
# rows are only added.
# rules = ["Shut down as soon as a run ends."]            # what the agent may do there; followed, not checked
"""
AGENTS = """# {name}

Run `lab now` first, then `lab show <id>` for what you work on. The method is `.lab/METHOD.md`. The skills are in
`.agents/skills/`: lab-work to move the work, lab-review to check someone else's, lab-talk whenever the operator
asks where things stand or what something is, and whenever there is a decision to bring to them.

## Local rules

"""


def init(root):
    """Install the method, the skills and the reviewer role; in an empty folder, also the files of a new lab."""
    wrote = []
    os.makedirs(root, exist_ok=True)
    name = os.path.basename(os.path.abspath(root))
    fresh = {
        "lab.toml": f'name = "{name}"\ntitle = "{name}"\nlibrary = "docs"\nkit = "{__version__}"\n',
        "AGENTS.md": AGENTS.format(name=name), "GLOSSARY.md": "# Terms\n\n", "resources.toml": RESOURCES, "log.md": "",
        ".ignore": "plan/\nruns/\n", ".gitignore": "runs/\n.incoming/\n.lab/running/\n.lab/fetched/\n",
        ".gitattributes": "log.md merge=union\nreviews.tsv merge=union\nruns.tsv merge=union\n",  # two sessions may add lines at once
    }
    new_lab = not os.path.exists(os.path.join(root, "lab.toml"))
    for rel, text in fresh.items():
        if not os.path.exists(os.path.join(root, rel)):
            open(os.path.join(root, rel), "w").write(text)
            wrote.append(rel)
    for d in ("goals", "decisions") + (("runs",) if new_lab else ()):  # in a clone, runs/ is the store and is not made empty here
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for src, dst in (("skills", ".agents/skills"), ("agents", ".agents/agents")):  # the kit's own only: other skills in the lab are left alone
        for item in sorted(os.listdir(os.path.join(DATA, src))):
            mine, theirs = os.path.join(DATA, src, item), os.path.join(root, dst, item)
            if os.path.isdir(theirs):
                shutil.rmtree(theirs)
            os.makedirs(os.path.dirname(theirs), exist_ok=True)
            shutil.copytree(mine, theirs) if os.path.isdir(mine) else shutil.copy(mine, theirs)
        wrote.append(dst + "/")
    os.makedirs(os.path.join(root, ".lab"), exist_ok=True)
    shutil.copy(os.path.join(DATA, "method", "METHOD.md"), os.path.join(root, ".lab", "METHOD.md"))
    wrote.append(".lab/METHOD.md")
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    for kind in ("skills", "agents"):  # the same folders, where one agent looks for them
        link = os.path.join(root, ".claude", kind)
        if not os.path.lexists(link):
            os.symlink(os.path.join("..", ".agents", kind), link)
    return wrote


def new(lab, kind, parent, title, replaces=None, origin=None, about=(), because="", asks=""):
    """Make the folder and the card of a goal, a question, an experiment, a build or a decision, under the next free id."""
    title = R.flat(title)
    if not title:
        stop("a title is a name, in a few words")
    if not slug(title):
        stop("a title has a letter or a digit in it: its folder is named after it")
    quoted = json.dumps(title, ensure_ascii=False)
    if kind in ("goal", "question"):  # direction comes out of a decision
        if not origin or lab.nodes.get(origin, {}).get("type") != "decision":
            stop(f"a {kind} comes out of a decision: `--from <decision>`. Open one with `lab new decision \"<title>\"`")
    if kind == "decision":
        for a in about:
            if lab.nodes.get(a, {}).get("type") not in ("goal", "question") + R.STEPS and a not in lab.resources:
                stop(f"--about {a}: no goal, question, experiment, build or reading has that id, and resources.toml lists no such resource")
        n = 1 + max([int(d["id"][1:]) for d in lab.decisions] or [0])
        ident, path = f"D{n}", f"decisions/D{n}-{slug(title)}.md"
        text = CARDS["decision"].format(title=quoted, about=", ".join(about), today=today())
    elif kind == "goal":
        n = 1 + max([int(g["id"][1:]) for g in lab.goals] or [0])
        ident, path = f"G{n}", f"goals/G{n}-{slug(title)}/goal.md"
        text = CARDS["goal"].format(title=quoted, origin=origin)
    else:
        p = lab.nodes.get(parent)
        want = "goal" if kind == "question" else "question"
        if not p or p["type"] != want:
            stop(f"a {kind} goes under a {want}; no {want} {parent}")
        if kind == "question":
            n = 1 + max([int(q["id"].split("Q")[-1]) for q in p["questions"]] or [0])
            ident, path = f"{p['id']}.Q{n}", f"{p['dir']}/Q{n}-{slug(title)}/question.md"
            text = CARDS["question"].format(title=quoted, origin=origin, asks=f"asks: {json.dumps(R.flat(asks), ensure_ascii=False)}\n" if R.flat(asks) else "")
        elif kind in R.STEPS:
            if p["state"] == "parked":  # set aside by a decision: work under it starts again only once a decision brings it back
                stop(f"{p['id']} is parked by {lab.parked_by(p['id'])['id']}: a decision that unparks it (`unparks: [{p['id']}]`) comes first")
            n = 1 + max([int(x["id"].split(".")[-1]) for x in p["items"]] or [0])
            ident, path = f"{p['id']}.{n}", f"{p['dir']}/{n}-{slug(title)}/{kind}.md"
            fill = {"title": quoted, "description": "", "extra": "", "Compares": "", "Arms": "- ", "Cases": "", "Confirmed if": "- ", "Refuted if": "- ", "Outcomes": "", "Limits": ""}
            old = None
            if replaces:
                old = lab.nodes.get(replaces)
                if kind != "experiment" or not old or old["type"] != "experiment" or old["question"] != p["id"]:
                    stop(f"--replaces names an experiment of the same question; {replaces} is not one")
                if lab.replaced_by(replaces):
                    stop(f"{replaces} is already replaced by {lab.replaced_by(replaces)['id']}")
                if not R.flat(because):
                    stop(f"say why {replaces} is replaced, in a sentence the operator can read: `--because \"<why>\"`")
                fill.update({k: old["slots"].get(k, "") for k in R.BEFORE}, extra=f"replaces: {replaces}\nbecause: {json.dumps(R.flat(because), ensure_ascii=False)}\n", description=old.get("description") or "")
            text = CARDS[kind].format(**fill) if kind == "experiment" else CARDS[kind].format(title=quoted)
            if old:  # the same needs, resources and override, so only what changes is written again
                for key in ("needs", "uses"):
                    text = text.replace(f"{key}: []", f"{key}: [{', '.join(old.get(key) or [])}]", 1)
                if old["override"]:
                    text = text.replace("replaces:", "override: {" + ", ".join(f"{k}: {v}" for k, v in old["override"].items()) + "}\nreplaces:", 1)
        else:
            stop("lab new goal|question|experiment|build|reading|decision")
    full = os.path.join(lab.root, path)
    try:  # never onto a card that is already there
        os.makedirs(os.path.dirname(full), exist_ok=kind == "decision")
        with open(full, "x") as f:
            f.write(text)
    except FileExistsError:
        stop(f"{path} is already there: another command made it; run this one again")
    if kind == "experiment":
        src = os.path.join(lab.root, lab.nodes[replaces]["dir"], "plan") if replaces else None
        if src and os.path.isdir(src):
            shutil.copytree(src, os.path.join(os.path.dirname(full), "plan"), ignore=shutil.ignore_patterns("__pycache__"))
        else:
            os.makedirs(os.path.join(os.path.dirname(full), "plan"))
    return ident, path


def log_line(lab, about, kind, what, so="", _by_command=False):
    """A log line, validated: (what, so) as they will be written. Nothing is written here."""
    if kind not in R.KINDS:
        stop(f"kind is one of: {', '.join(k for k in R.KINDS if k != 'decision')}")
    if kind == "decision" and not _by_command:
        stop("a decision is recorded with `lab decide`, on its card: what was decided and why")
    if about not in lab.nodes or (lab.nodes[about]["type"] == "decision") != (kind == "decision"):
        stop(f"no goal, question, experiment, build or reading {about}")
    what, so = R.flat(what), R.flat(so)
    if kind == "doing" and not so:
        stop("a `doing` line says what you are starting on, then why now: lab log <id> doing \"<what>\" \"<why now>\"")
    if not what or "|" in what or "|" in so:
        stop("a line says what happened, and holds no |")
    return what, so


def log(lab, about, kind, what, so="", _by_command=False):
    what, so = log_line(lab, about, kind, what, so, _by_command)
    path = os.path.join(lab.root, "log.md")
    text = R.read(path) if os.path.exists(path) else ""
    line = f"- {clock()} | {about} | {kind} | {what} | {so}"
    head = "" if re.findall(r"^## (\S+)", text, flags=re.M)[-1:] == [today()] else ("\n" if text.strip() else "") + f"## {today()}\n\n"
    with open(path, "a") as f:
        f.write(("" if not text or text.endswith("\n") else "\n") + head + line + "\n")
    return "log.md"


def decide(lab, ident, text, with_):
    """Close a decision: what was decided and why, in the lab's words, out of a conversation with the operator."""
    d = lab.nodes.get(ident)
    if not d or d["type"] != "decision":
        stop(f"no decision {ident}")
    if d["state"] != "open":
        stop(f"{ident} is already decided; a change of mind is a new decision")
    if not R.flat(text):
        stop("say what was decided and why, in the lab's words")
    if not with_:
        stop("--with <who>: a decision is recorded out of a conversation with the operator")
    if not R.flat(d["slots"].get("Seen", "")):
        stop(f"{ident} does not say what was seen: fill Seen on its card first, so the record says why this came up")
    if R.flat(d["slots"].get("Decided", "")) or d.get("decided_as_written") is not None:
        stop(f"{ident} already holds a Decided or a `decided:` that this command did not write: remove it from the card first")
    with_ = R.flat(with_)
    line = log_line(lab, ident, "decision", f"Decided: {d['title']}".replace("|", "/"), R.first_sentence(text).replace("|", "/"), _by_command=True)
    path = os.path.join(lab.root, d["path"])
    fm, body = R.split(R.read(path))  # everything is validated before the first write
    fm += f"decided: {{date: {today()}, with: {json.dumps(with_, ensure_ascii=False)}}}\n"
    open(path, "w").write(R.join(fm, body.rstrip("\n") + f"\n\n## Decided\n\n{R.flat(text)}\n"))
    log(lab, ident, "decision", *line, _by_command=True)
    return d["path"]


def answer(lab, target, verdict, text):
    """The agent's answer to a question, once its experiments are done."""
    n = lab.nodes.get(target)
    if verdict not in ("yes", "no"):
        stop("an answer is yes or no")
    if not n or n["type"] != "question":
        stop(f"no question {target}")
    if not R.flat(text):
        stop("an answer says what it rests on")
    if n["state"] != "open":
        stop(f"{target} is {n['state']}, not open")
    waiting = [x["id"] for x in n["items"] if x["state"] not in ("done", "built", "replaced", "dropped")]
    if waiting:
        stop(f"{target} cannot be answered while {', '.join(waiting)} {'is' if len(waiting) == 1 else 'are'} not done: finish, replace or drop {'it' if len(waiting) == 1 else 'them'}")
    if not any(x["state"] == "done" and x["type"] == "experiment" for x in n["items"]):  # a reading suggests; it answers nothing
        stop(f"{target} has no finished experiment to rest an answer on")
    if n.get("answer") is not None or n.get("answered") is not None:
        stop(f"{target} already holds an `answer:` or an `answered:` that this command did not write: remove it from the card first")
    line = log_line(lab, target, "agent", f"Answered {target} {verdict}.", text)  # everything is validated before the first write
    path = os.path.join(lab.root, n["path"])
    fm, body = R.split(R.read(path))
    open(path, "w").write(R.join(fm + f"answer: \"{verdict}\"\nanswered: {today()}\n", body))
    log(lab, target, "agent", *line)
    return n["path"]


def lock(lab, ident):
    x = lab.nodes.get(ident)
    if not x or x["type"] != "experiment":
        stop(f"no experiment {ident}")
    if x["lock"]:
        stop(f"{ident} is already locked. What an experiment demands never changes: `lab new experiment {x['question']} \"<title>\" --replaces {ident}`")
    if x["state"] in ("dropped", "replaced"):
        stop(f"{ident} is {x['state']}")
    why = lab._blocked(x)
    if why:
        stop(f"{ident} waits on {why}")
    held = lab.holding(ident)
    if held:
        stop(f"{ident} is held by the decision {held[0]['id']}, which is not settled")
    problems = []
    if not R.flat(x["slots"].get("Compares", "")):
        problems.append("Compares is empty")
    if not x["arms"] or any(not name or not what for name, what in x["arms"]):
        problems.append("Arms names each thing compared and says what it is, one per line: `- the gate: our loop with the gate checking every call`")
    if not R.flat(x["slots"].get("Cases", "")):
        problems.append("Cases is empty: say what it is run on, and how many")
    for side, label in (("confirmed", "Confirmed if"), ("refuted", "Refuted if")):
        if not x["lines"][side]:
            problems.append(f"{label} has no line" + (": say what result would refute it" if side == "refuted" else ""))
        problems += [f"{label}: the line {l['say']!r} has no test, such as (`name < 0.05`). A bar that is not a number goes in Means" for l in x["lines"][side] if not l["test"]]
    plan = os.path.join(lab.root, x["dir"], "plan")
    if not os.path.isdir(plan) or not os.listdir(plan):
        problems.append("plan/ is empty: it holds the configuration and the code the run executes")
    elif R.symlinks(plan):
        problems.append(f"plan/ holds a link, {R.symlinks(plan)[0]}: what a link points at is not in plan/ and is not pinned. Copy it in")
    elif R.compiled(plan):
        problems.append(f"plan/ holds a compiled file outside __pycache__, {R.compiled(plan)[0]}: Python would import it, and a `.pyc` is not pinned. Remove it, and keep the script")
    for r in x["uses"]:
        if r not in lab.resources:
            problems.append(f"uses {r}, which resources.toml does not list")
        elif lab.resources[r].get("retired"):
            problems.append(f"uses {r}, which is retired: {lab.resources[r]['retired']}")
        elif lab.metered(r) and not lab.granted_by(r):
            problems.append(f"uses {r}, whose amounts name no settled decision that lists it: `from = \"D<n>\"` in resources.toml, and {r} under that decision's `about:`")
    for r, cap in x["override"].items():
        if r not in x["uses"]:
            problems.append(f"override {r}: an override is a cap on a resource the experiment uses")
    if any(lab.metered(r) for r in x["uses"]) and lab.reviewed(x, "plan") != ("pass", True):
        verdict, fresh = lab.reviewed(x, "plan")
        problems.append("its run uses a metered resource, and " + ("the plan changed after its review" if verdict == "pass" and not fresh else "no review has passed the plan"))
    if problems:
        stop(f"{ident} cannot be locked:\n- " + "\n- ".join(problems))
    record = {"kit": __version__, "locked": now(), "commit": R.code_head(lab), "card": lab.before_hash(x), "terms": lab.terms_hash(x), "plan": lab.plan_hash(x), "hash": R.HASH, "uses": sorted(x["uses"]),
              "trials": [r["id"] for r in x["trials"]]}
    path = os.path.join(lab.root, x["dir"], "lock.json")
    open(path, "w").write(json.dumps(record, indent=1) + "\n")
    return lab.rel(path)


def review(lab, ident, stage, verdict, note, by=None):
    """One independent reading of a plan or of an experiment's results, bound to exactly what it read."""
    x = lab.nodes.get(ident)
    if not x or x["type"] != "experiment":
        stop(f"no experiment {ident}")
    if stage not in ("plan", "results") or verdict not in ("pass", "fail"):
        stop("lab review <experiment> plan|results pass|fail \"<note>\"")
    if not R.flat(note):
        stop("a review says what it read and what it found")
    if stage == "plan" and x["lock"]:
        stop(f"{ident} is locked: a plan is reviewed before its lock")
    if stage == "results":
        if not x["finished"] or not x["results"]:
            stop(f"{ident} has no finished run with results to review")
        if lab.reviewed(x, "results")[0] == "fail":
            stop(f"{ident} already failed its results review, and that is final: replace the experiment")
    path = os.path.join(lab.root, x["dir"], "reviews.tsv")
    if not os.path.exists(path):
        open(path, "w").write("date\tstage\tverdict\tby\tof\tnote\n")
    by = R.flat(by or os.environ.get("LAB_REVIEWER") or "reviewer").replace("\t", " ")
    with open(path, "a") as f:
        f.write("\t".join([today(), stage, verdict, by, lab.content(x, stage), R.flat(note).replace("\t", " ")]) + "\n")
    return lab.rel(path)


def rederive(lab, only=None):
    """Run each result row's command again and compare what it prints with the recorded value."""
    problems, n = [], 0
    limit = lab.cfg.get("rederive_timeout")
    limit = limit if R.amount(limit) and limit > 0 else 120
    for x in lab.experiments:
        if only and x["id"] != only:
            continue
        run = x["finished"]
        for row in x["results"]:
            if not run or run["missing"] or not row.get("command"):
                continue
            n += 1
            env = {**os.environ, "RUN": os.path.join(lab.root, run["dir"]), "PYTHONDONTWRITEBYTECODE": "1"}
            try:
                p = subprocess.run(row["command"], shell=True, cwd=lab.root, capture_output=True, text=True, errors="replace", env=env, timeout=limit)
            except subprocess.TimeoutExpired:
                problems.append(f"results: {row['ref']}: its command did not print the value within {limit:g} seconds (`rederive_timeout` in lab.toml)")
                continue
            got = p.stdout.strip()
            if p.returncode != 0:
                problems.append(f"results: {row['ref']}: its command failed: {(p.stderr.strip().splitlines() or ['no output'])[-1][:120]}")
            elif got != str(row["value"]).strip():
                problems.append(f"results: {row['ref']}: its command prints {got[:40]!r}, the row says {row['value']!r}")
    return problems, n
