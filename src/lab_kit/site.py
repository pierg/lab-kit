"""The operator's site for a lab: every page drawn from the record when it is asked for, inside folio's shell.

folio names this module under `views:` in the library's charter. It never stores a page: the cards, the
results and the runs are read at each request, so the site cannot fall behind the record. It changes nothing.
"""
from __future__ import annotations

import datetime, glob, hashlib, html, os, re

from . import record as L

GENERIC = {"model", "field", "source", "group", "stop", "case", "score", "port", "step", "pass", "run", "result"}
e = html.escape
# How every state and label is drawn, on every page, on Now and in the rail: its tone (the colour) and its sign (the
# shape), so that colour is never the only signal. On done the label decides, and an answer is a finding, never good or
# bad: yes, no and mixed share one neutral tone.
LOOK = {"open": ("plain", "\u25cb"), "waiting": ("warn", "\u2016"), "parked": ("plain", "\u25c7"), "running": ("info", "\u25cf"),
        "done": ("ok", "\u2713"), "confirmed": ("ok", "\u2713"), "unclear": ("warn", "?"), "refuted": ("bad", "\u2717"), "void": ("bad", "!"),
        "yes": ("ink", "Y"), "no": ("ink", "N"), "mixed": ("ink", "M"), "found": ("ink", "F"), "replaced": ("gone", "\u2013"), "dropped": ("gone", "\u2013"),
        "to discuss": ("warn", "\u25c6"), "decided": ("ok", "\u2713"),
        "finished": ("ok", "\u2713"), "failed": ("bad", "\u2717"), "pass": ("ok", "\u2713"), "fail": ("bad", "\u2717")}
ORDER = ("running", "waiting", "open", "done", "confirmed", "yes", "no", "mixed", "found", "unclear", "refuted", "void", "parked", "replaced", "dropped")  # how counts are listed
MARK = {"goal": "G", "question": "Q", "experiment": "E", "build": "B", "reading": "R", "decision": "D"}
MEANS = {"running": "running", "waiting": "waiting", "open": "open", "done": "done", "confirmed": "confirmed", "yes": "answered yes", "no": "answered no",
         "mixed": "answered mixed", "found": "found", "unclear": "unclear", "refuted": "refuted", "void": "void", "parked": "parked",
         "replaced": "replaced", "dropped": "dropped", "to discuss": "to discuss", "decided": "decided",
         "finished": "finished", "failed": "failed", "pass": "passed", "fail": "failed"}
HINT = {"running": "work under way; on a goal or a question, a step under it is running", "waiting": "held by a step it needs, a decision or something outside the lab",
        "parked": "set aside by a decision", "void": "its results review failed: its numbers are never used", "replaced": "redone by a newer experiment",
        "dropped": "will not be done", "to discuss": "open: waits for you", "found": "an estimate, answered with what was found", "failed": "a run that stopped with an error, or a review that did not pass"}


def nice(day):
    """A recorded day as a page shows it. What is not a day is shown as it was written: `lab check` reports it."""
    try:
        d = datetime.date.fromisoformat(str(day)[:10])
    except ValueError:
        return e(str(day or "no date"))
    return f"{d.day} {d.strftime('%b')}"


def clock(at):
    """A recorded moment as a page shows it: the day, and the time when the record has one. Every time is UTC."""
    return nice(at) + (f" {str(at)[11:16]}" if len(str(at)) > 10 else "")


def ago(then, now=None):
    """How long ago a moment was, in the largest unit that fits."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    mins = max(0, int((now - then).total_seconds() // 60))
    if mins < 2:
        return "just now"
    if mins < 90:
        return f"{mins} minutes ago"
    if mins < 36 * 60:
        return f"{round(mins / 60)} hours ago"
    return f"{round(mins / 1440)} days ago"


def num(x):
    if not L.amount(x) and not (isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float("inf")):
        return e(str(x))  # not a number: shown as written, and `lab check` reports it
    return f"{int(x):,}" if x == int(x) else f"{x:,.2f}".rstrip("0").rstrip(".")


def plain(text):
    """Text that is not card prose, such as a reviewer's note: shown as written, with nothing in it turned into a link."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", e(L.flat(text), quote=False))


def ordinal(n):
    return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth"}.get(n, f"{n}th")


def running_under(n):
    """The steps running under a goal or a question, in tree order."""
    if n.get("type") == "question":
        return [x for x in n.get("items") or [] if x["state"] == "running"]
    if n.get("type") == "goal":
        return [x for q in n.get("questions") or [] for x in running_under(q)]
    return []


def key(n):
    """The word a node's look is read from: its label on done (an answer, an outcome), else its state. A goal or a
    question that is open or waiting with a step running under it reads as running, so that the work shows at every
    level of the tree; its state in the record is unchanged."""
    if n.get("type") == "decision":
        return "decided" if n["state"] == "done" else "to discuss"
    if n.get("state") in ("open", "waiting") and running_under(n):
        return "running"
    return n["label"] if n.get("state") == "done" and n.get("label") else n["state"]


def label(n):
    """A node's state as the operator reads it, in the words every page uses: on done, a question shows its answer and an
    experiment its outcome."""
    return MEANS.get(key(n), key(n))


def hint(n):
    """What a mark says on hover: the word, and for a goal or a question shown as running, what runs under it."""
    under = running_under(n) if n.get("type") in ("goal", "question") and key(n) == "running" else []
    return label(n) + (": " + ", ".join(x["id"] for x in under) + " running" if under else "")


def tone(n):
    return LOOK.get(key(n), ("plain", ""))[0]


def sign(n):
    return LOOK.get(key(n), ("plain", "\u25cb"))[1]


def you(text):
    """What the record says of the operator, said to the operator."""
    return str(text).replace("the operator's", "your").replace("the operator", "you")


def pill(text, t="plain"):
    return f'<span class="pill t-{t}">{e(str(text))}</span>'


def mark(k, title=""):
    """The mark of a state or a label: its sign in its tone, the same shape and colour on every page and in the rail.
    Running pulses."""
    t, g = LOOK.get(k, ("plain", "\u25cb"))
    return f'<span class="sg t-{t}{" live" if k == "running" else ""}" title="{e(title or MEANS.get(k, k))}">{g}</span>'


def dot(n, title=""):
    """A node's mark."""
    return mark(key(n), title or hint(n))


def status(n):
    """A node's mark and its word, in its tone: how a state is written out wherever a page names it."""
    h = hint(n)
    return word(key(n), h if h != label(n) else "")


def word(k, title=""):
    """A state or a label written out: its mark and the word, in its tone. An answer is written as itself, in a box
    (yes, no, mixed, found): the box is its mark, and the word is the finding."""
    t = LOOK.get(k, ("plain", ""))[0]
    if t == "ink":
        return f'<span class="ans" title="{e(title or HINT.get(k, MEANS.get(k, k)))}">{e(k)}</span>'
    return f'<span class="stw t-{t}" title="{e(title or HINT.get(k, MEANS.get(k, k)))}">{mark(k, title)}{e(MEANS.get(k, k))}</span>'


def header_css():
    """folio's page header shows the view's status as a pill: draw it with the same mark and tone as everywhere else."""
    soft = {"ok": "ok-soft", "warn": "warn-soft", "bad": "bad-soft", "info": "info-soft"}
    # The rail's answers: the letter boxed, as in a row of marks on a lab page.
    out = ['.f-vsign[data-t="ink"]{border:1px solid var(--ink-3);border-radius:3px;padding:0 .2em;min-width:0;font-size:.62rem;line-height:1.2}']
    for k, (t, g) in LOOK.items():
        fg = {"plain": "ink-3", "gone": "ink-3", "ink": "ink"}.get(t, t)
        sel = f'.f-status[data-s="{MEANS.get(k, k)}"]'
        if t == "ink":  # an answer: the words alone, boxed, as on every lab page
            out.append(f'{sel}{{background:none;color:var(--ink);border:1px solid var(--ink-3)}}{sel}::before{{display:none}}')
            continue
        out.append(f'{sel}{{background:var(--{soft.get(t, "sunk")});color:var(--{fg})}}'
                   f'{sel}::before{{content:"{g}";width:auto;height:auto;border-radius:0;background:none;opacity:1;font-weight:700}}')
        if k == "running":
            out.append(f"@media (prefers-reduced-motion:no-preference){{{sel}::before{{animation:lv-pulse 1.6s ease-in-out infinite}}}}")
    return "".join(out)


# A mission's status reads as a card's state: next as open, current as running, done as done, stopped as dropped.
MISSION_KEY = {"next": "open", "current": "running", "done": "done", "stopped": "dropped"}


def mission_mark(m):
    return mark(MISSION_KEY.get(m["state"], "open"), m["state"])


def mission_box(lab, T, m):
    """One mission, compact: what it carries and where it stands, its steps as marks, its last line, and its log folded."""
    d = lab.nodes.get(m["carries"])
    carries = named(lab, d["id"]) if d and d["type"] == "decision" else '<span class="muted">no decision: lab check says why</span>'
    started = next((l for l in m["log"] if l.get("what") == "launched"), None)
    head = (f'{e(m["id"])} · {mission_mark(m)} {e(m["state"])} · carries {carries}'
            + (f' · launched {nice(started["day"])}' if started else ""))
    rows = []
    if L.flat(m["description"]):
        rows.append(("For", T(L.flat(m["description"]))))
    steps = lab.mission_steps(m)
    if steps:
        done = sum(x["state"] in L.CLOSED for x in steps)
        rows.append(("Steps", f'{done} of {len(steps)} closed <span class="marks">' + "".join(dot(x, f'{x["id"]} {x["title"]}: {label(x)}') for x in steps) + "</span>"))
    lines = [l for l in m["log"] if l.get("what")]
    if lines:
        last = lines[-1]
        rows.append(("Last", f'<span class="muted">{nice(last["day"])} {e(last["time"])}</span> {T(last["what"])}'))
    if L.flat(m["slots"].get("Rules", "")):
        rows.append(("Rules", f'<details><summary>the rules of this mission</summary>{block(T, m["slots"]["Rules"])}</details>'))
    if len(lines) > 1:
        rows.append(("Log", f'<details><summary>{len(lines)} lines</summary><ul class="mlog">'
                     + "".join(f'<li><span class="muted">{nice(l["day"])} {e(l["time"])}</span> {T(l["what"])}</li>' for l in lines) + "</ul></details>"))
    return (f'<div class="box mission m-{e(m["state"])}" id="{e(m["id"])}"><div class="decisionhead">{head}</div>'
            f'<p class="decisionq">{e(m["title"] or m["path"])}</p>'
            '<dl class="decisionrows">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl></div>")


def missions_page(lab, T):
    """Every mission: the current first, then the next, then the closed, the latest first."""
    body = ["<h1>Missions</h1>", '<p class="lead">A mission carries out a settled decision across sessions: its rules, and a log a later session resumes from.</p>']
    closed = sorted([m for m in lab.missions if m["state"] in ("done", "stopped")], key=lambda m: m["n"], reverse=True)
    for title, group in (("Current", [m for m in lab.missions if m["state"] == "current"]), ("Next", [m for m in lab.missions if m["state"] == "next"]), ("Closed", closed)):
        if group:
            body.append(f"<h2>{title}</h2>" + "".join(mission_box(lab, T, m) for m in group))
    if not lab.missions:
        body.append('<p class="muted">None yet.</p>')
    return frame(lab, "Missions", "".join(body))


def libraries(lab):
    """The other libraries this lab's charter names, each with where it is on disk and where it is served."""
    if not hasattr(lab, "_libraries"):
        import yaml
        base = os.path.join(lab.root, lab.cfg.get("library", "docs"))
        try:
            found = (yaml.safe_load(open(os.path.join(base, "folio.yaml"))) or {}).get("libraries") or {}
        except OSError:
            found = {}
        lab._libraries = {name: {"path": os.path.normpath(os.path.join(base, str(v.get("path", "")))), "url": str(v.get("url", "")).rstrip("/")} for name, v in found.items() if isinstance(v, dict)}
    return lab._libraries


def outside(lab, target):
    """Where a link out of a card leads: a web address, a page of this lab's library (`/docs/...`), or a page of a
    library the charter names (`pier-folio:/content/...`). None when it is none of these."""
    target = html.unescape(str(target))
    if re.match(r"https?://", target):
        return target
    if target.startswith("/docs/"):
        return target
    name, _, path = target.partition(":")
    lib = libraries(lab).get(name)
    return lib["url"] + path if lib and lib["url"] and path.startswith("/") else None


def page_title(lab, target):
    """The title of a page a card points at in another library, read from the page itself."""
    name, _, path = str(target).partition(":")
    lib = libraries(lab).get(name)
    try:
        m = re.search(r'<meta name="title" content="([^"]*)"', L.read(os.path.join(lib["path"], path.lstrip("/")))) if lib else None
    except OSError:
        m = None
    return html.unescape(m.group(1)) if m else str(target)


def ref(lab, ident, text=None):
    n = lab.nodes.get(ident)
    if not n and ident in lab.folded:  # a draft decision folded into a later one is read there
        into = lab.folded[ident]
        return f'<a class="ref" href="/{into}" data-tip="folded into {e(into)}">{e(text or ident)}</a>'
    if not n:
        return e(ident)
    return f'<a class="ref" href="/{ident}" data-tip="{e(n["title"])} ({e(label(n))})">{e(text or ident)}</a>'


def named(lab, ident):
    """An id with its title beside it, which is how every page says which node it means."""
    n = lab.nodes.get(ident)
    return f'{ref(lab, ident)} <a href="/{ident}">{e(n["title"])}</a>' if n else e(ident)


class Text:
    """Card prose to HTML. An id becomes a link, and a named result its value. A page's exact title becomes a link to
    that page, an id in brackets after it included, before any glossary term inside it. Every glossary term, and every
    other name its entry lists, links to its entry with the definition as its tooltip, wherever it is written."""

    def __init__(self, lab, here=None):
        self.lab, self.here = lab, here
        terms = [g for g in lab.glossary if g["term"].lower() not in GENERIC]
        self.defs = {g["term"].lower(): g for g in terms}
        for g in terms:  # a term's other names (- also: ...) point at the same entry
            for other in g.get("also") or []:
                self.defs.setdefault(other.lower(), g)
        self.titles = {}  # a title of two words or more, as it reads in escaped prose
        for n in lab.nodes.values():
            t = str(n.get("title") or "")
            if len(t.split()) >= 2 and t.lower() not in self.defs:
                self.titles.setdefault(e(t, quote=False).lower(), n["id"])
        either = lambda words: "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) or r"(?!x)x"
        ident = r"(?:G\d+(?:\.Q\d+(?:\.\d+)?)?|D\d+)"
        self.rx = re.compile(
            r"(?P<link>\[[^\]\n]+\]\([^)\s]+\))|(?P<code>`[^`]+`)|(?P<strong>\*\*[^*\n]+\*\*)|(?P<em>\*[^*\n]+\*)|(?P<named>\{(?:G\d+\.Q\d+\.\d+:)?[A-Za-z][\w.-]*?\})"
            r"|(?P<title>(?i:(?<!\w)(?:" + either(self.titles) + r")(?!\w))(?: \(" + ident + r"\))?)"
            r"|(?P<id>\b" + ident + r"\b)"
            r"|(?P<term>(?i:\b(?:" + either(self.defs) + r")s?\b))")

    def term(self, word):
        """A glossary term as written in prose: a link to its entry, its definition as the tooltip."""
        key = word.lower() if word.lower() in self.defs else word.lower()[:-1]
        if key not in self.defs:
            return word
        return f'<a class="term" href="/glossary#{e(anchor(self.defs[key]["term"]))}" data-tip="{e(self.defs[key]["definition"])}">{word}</a>'

    def __call__(self, text, home=None):
        lab = self.lab

        def one(m):
            if m.group("code"):
                return f"<code>{m.group('code')[1:-1]}</code>"
            if m.group("link"):
                text, target = m.group("link")[1:-1].split("](", 1)
                url = outside(lab, target)
                return f'<a href="{e(url)}">{text}</a>' if url else text
            if m.group("strong"):
                return f"<b>{self.rx.sub(one, m.group('strong')[2:-2])}</b>"
            if m.group("em"):
                return f"<em>{self.rx.sub(one, m.group('em')[1:-1])}</em>"
            if m.group("title"):
                said = re.sub(r" \([GDQ\d.]+\)$", "", m.group("title"))
                nid = self.titles.get(said.lower())
                if nid == self.here:  # a page does not link to itself
                    return said
                return f'<a class="page" href="/{nid}" data-tip="{e(nid)}: {e(lab.nodes[nid]["title"])}">{said}</a>'
            if m.group("named"):
                (written, row), = lab.named(m.group("named"), home)
                if not row or not row["usable"]:
                    return f'<span class="num off" data-tip="Not a reviewed result">{e(written)}</span>'
                tip = f"{row.get('label') or row['name']}. Compared with: {row.get('versus', '')}"
                return f'<a class="num" href="/{row["experiment"]}#r-{e(row["name"])}" data-tip="{e(tip)}">{e(L.shown(row))}</a>'
            if m.group("id"):
                return ref(lab, m.group("id")) if m.group("id") in lab.nodes else m.group("id")
            return self.term(m.group("term"))

        return self.rx.sub(one, e(L.flat(text), quote=False))


def anchor(term):
    """Where a term's entry is on the glossary page."""
    return term.lower().replace(" ", "-")


CSS = """
.lv figure.pic{margin:1.2rem 0 1.6rem;padding:1rem;background:var(--surface);border:1px solid var(--rule);border-radius:10px;overflow-x:auto}
.lv figure.pic svg{display:block;width:100%;height:auto;min-width:560px}
.lv .tw{overflow-x:auto;margin:.6rem 0 1rem}
.lv table.t.card th{text-transform:none;letter-spacing:0;font:650 .82rem var(--sans);color:var(--ink-2)}
.lv .box.note{border-left:3px solid var(--ink-3);background:var(--sunk)}
.lv .box.note p{display:inline}
.lv .lv-h3,.lv h3{font:650 1.02rem var(--sans)}
.lv details.record{margin-top:2rem}
.lv details.record>summary{font:650 1.1rem var(--sans);cursor:pointer;padding:.6rem 0}
.lv{font:400 1rem/1.6 var(--serif)}
.lv h3{margin:1.2em 0 .3em}
.lv .crumbs{font:500 .8rem var(--sans);color:var(--ink-3)}
.lv .crumbs a{color:var(--ink-3)}
.lv .avoid{display:block;font:.78rem var(--sans);color:var(--ink-3)}
.lv .lead{font-size:1.1rem;color:var(--ink-2);max-width:48rem}
.lv .pill{display:inline-block;padding:.08rem .55rem;border-radius:999px;font:600 .72rem/1.5 var(--sans);white-space:nowrap;background:var(--sunk);color:var(--ink-2)}
.lv .t-ok{background:var(--ok-soft);color:var(--ok)}
.lv .t-warn{background:var(--warn-soft);color:var(--warn)}
.lv .t-bad{background:var(--bad-soft);color:var(--bad)}
.lv .t-info{background:var(--info-soft);color:var(--info)}
.lv .t-plain{background:var(--sunk);color:var(--ink-3)}
.lv .dot{display:inline-block;flex:none;width:.55rem;height:.55rem;border-radius:50%;background:currentColor}
.lv i.dot.t-ok{background:var(--ok)}
.lv i.dot.t-warn{background:var(--warn)}
.lv i.dot.t-bad{background:var(--bad)}
.lv i.dot.t-info{background:var(--info)}
.lv i.dot.t-plain{background:var(--rule-strong)}
.lv .slots{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.9rem;margin:1rem 0}
.lv .slot{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:.8rem 1rem}
.lv .slot.full{grid-column:1/-1}
.lv .slot h5{margin:0 0 .3rem;font:650 .68rem var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.lv .slot p{margin:0}
.lv .slot.key{border-left:3px solid var(--accent);background:var(--accent-soft)}
.lv .slot .tw,.lv .slot table.t{margin:.6rem 0 .2rem}
.lv .slot ul,.lv .slot ol{margin:.3rem 0;padding-left:1.3rem}
.lv .slot p+p{margin-top:.5rem}
.lv .box{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:.9rem 1.1rem;margin:0 0 1rem}
.lv .box.decision{border-left:3px solid var(--warn);background:var(--warn-soft);margin:0 0 .8rem}
.lv .box.mission{border-left:3px solid var(--rule-strong);margin:0 0 .8rem}.lv .box.mission.m-current{border-left-color:var(--info);background:var(--info-soft)}
.lv .box.mission .marks{margin-left:.4rem}.lv .mlog{margin:.3rem 0 0;padding-left:1.1rem;font-size:.86rem}.lv .box.mission summary{cursor:pointer;color:var(--ink-3);font-size:.86rem}
.lv .box.decision.closed{border-left-color:var(--ok);background:var(--ok-soft)}
.lv .decisionhead{font:500 .78rem var(--sans);color:var(--muted);margin:0 0 .3rem}
.lv .decisionq{font-size:1.08rem;line-height:1.45;margin:0 0 .6rem;font-weight:600}
.lv .decisionrows{display:grid;grid-template-columns:max-content 1fr;gap:.3rem .9rem;margin:0;font-size:.93rem}
.lv .decisionrows dt{font:650 .68rem var(--sans);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);padding-top:.22rem}
.lv .decisionrows dd{margin:0}
.lv .unsaid{display:block;font:500 .72rem var(--sans);color:var(--warn)}
.lv q.said{display:block;quotes:"“" "”";font-style:italic;color:var(--muted);margin:.15rem 0}
.lv table.t{border-collapse:collapse;width:100%;font:400 .88rem/1.45 var(--sans);margin:0 0 1rem}
.lv table.t th{text-align:left;font:650 .68rem var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);padding:.35rem .6rem;border-bottom:1px solid var(--rule-strong)}
.lv table.t td{padding:.45rem .6rem;border-bottom:1px solid var(--rule);vertical-align:top}
.lv table.t td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
.lv table.t tr:target td{background:var(--mark)}
.lv details.row{border-bottom:1px solid var(--rule)}
.lv details.row>summary{display:grid;grid-template-columns:1rem 13.5rem 8.5rem 1fr;gap:.7rem;align-items:baseline;padding:.55rem .2rem;cursor:pointer;list-style:none;font:400 .9rem/1.4 var(--sans)}
.lv details.row>summary::-webkit-details-marker{display:none}
.lv details.row>summary b{font-weight:600}
.lv details.row[open]>summary{background:var(--sunk)}
.lv details.row .in{padding:.2rem 0 1rem 1.7rem}
.lv .strip{display:flex;gap:.6rem;flex-wrap:wrap;align-items:stretch;margin:.4rem 0 1rem}
.lv .att{flex:1 1 11rem;max-width:17rem;background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:.6rem .8rem;text-decoration:none;color:var(--ink);font:400 .82rem/1.4 var(--sans)}
.lv .att:hover{border-color:var(--accent)}
.lv .att b{display:flex;justify-content:space-between;font:650 .9rem var(--sans);margin-bottom:.25rem}
.lv .att.cur{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.lv .arrow{align-self:center;color:var(--ink-3)}
.lv .log{list-style:none;padding:0;margin:0;font:400 .9rem/1.5 var(--sans)}
.lv .log li{display:grid;grid-template-columns:6.4rem 5.2rem 6.2rem 1fr;gap:.6rem;padding:.5rem 0;border-bottom:1px solid var(--rule)}
.lv .log .d{color:var(--ink-3)}
.lv .log .saw,.lv .log .so{display:block;color:var(--ink-2)}
.lv .log .so{color:var(--ink)}
.lv .log .saw::before{content:"Saw  ";font:650 .66rem var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.lv .log .so::before{content:"So  ";font:650 .66rem var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lv [data-tip]{position:relative}
.lv [data-tip]:hover::after{content:attr(data-tip);position:absolute;left:0;top:1.5em;z-index:40;width:max-content;max-width:23rem;padding:.5rem .7rem;border-radius:6px;background:var(--ink);color:var(--paper);font:400 .8rem/1.4 var(--sans);white-space:normal;box-shadow:var(--shadow)}
.lv a.term{color:inherit;text-decoration:none;border-bottom:1px dotted var(--ink-3)}
.lv a.page{color:var(--link,var(--accent));text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2px}
.lv a.term:hover{color:var(--accent);border-bottom-color:var(--accent)}
.lv a.num{font-variant-numeric:tabular-nums;font-family:var(--sans);font-size:.92em;padding:0 .22em;margin:0 -.05em;border-radius:4px;background:var(--info-soft);color:var(--info);text-decoration:none}
.lv a.ref{font:500 .88em var(--sans);text-decoration:none;white-space:nowrap}
.lv .chg{background:var(--mark);border-radius:3px;padding:0 .25em;font:650 .64rem var(--sans);letter-spacing:.06em;text-transform:uppercase;margin-left:.4em;color:var(--ink)}
.lv details.old{font-size:.84rem;color:var(--ink-3);margin:.2rem 0 0}
.lv details.old summary{cursor:pointer}
.lv .bar{display:flex;height:.5rem;border-radius:999px;overflow:hidden;background:var(--sunk);width:9rem}
.lv .bar i{display:block}
.lv .bar .ok{background:var(--ok)}
.lv .bar .warn{background:var(--warn)}
.lv .bar .info{background:var(--info)}
.lv .qcard{display:grid;grid-template-columns:1fr 9.5rem;gap:1rem;padding:.9rem 0;border-bottom:1px solid var(--rule)}
.lv .qcard h3{margin:0 0 .25rem;font:600 1.08rem var(--serif);text-transform:none;letter-spacing:0;color:var(--ink)}
.lv .qcard p{margin:0;color:var(--ink-2);font-size:.95rem}
.lv .qcard .side{font:400 .78rem var(--sans);color:var(--ink-3);text-align:right}
.lv pre.f{font:.78rem/1.45 var(--mono);background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:.8rem 1rem;overflow:auto;max-height:70vh}
.lv .muted{color:var(--ink-3)}
.lv .kv{display:grid;grid-template-columns:8.5rem 1fr;gap:.25rem .8rem;font:400 .88rem/1.45 var(--sans)}
.lv .kv dt{color:var(--ink-3)}
.lv .kv dd{margin:0;overflow-wrap:anywhere}
.lv .sg{display:inline-block;min-width:.95em;text-align:center;font:700 .82em/1 var(--sans);color:var(--ink-3);background:none;text-decoration:none}
.lv .sg.t-ok{color:var(--ok)}.lv .sg.t-warn{color:var(--warn)}.lv .sg.t-bad{color:var(--bad)}.lv .sg.t-info{color:var(--info)}.lv .sg.t-ink{color:var(--ink)}.lv .sg.t-gone{color:var(--ink-3)}
.lv .t-ink{background:var(--sunk);color:var(--ink)}
.lv .t-gone{background:none;color:var(--ink-3);text-decoration:line-through}
.lv .sg.t-ink{min-width:0;padding:.1em .28em;border:1px solid var(--ink-3);border-radius:3px;font-size:.62em;line-height:1.1;vertical-align:.12em}
.lv .ans{display:inline-block;padding:0 .45rem;border:1px solid var(--ink-3);border-radius:4px;font:650 .74rem/1.45 var(--sans);color:var(--ink);background:var(--surface);white-space:nowrap}
.lv .live{animation:lv-pulse 1.6s ease-in-out infinite}
.lv .stw{display:inline-flex;gap:.25rem;align-items:baseline;background:none;font:600 .78rem/1.4 var(--sans);white-space:nowrap}
.lv .stw.t-plain,.lv .stw.t-gone{color:var(--ink-3);text-decoration:none}.lv .stw.t-ink{color:var(--ink)}
@keyframes lv-pulse{0%,100%{opacity:1}50%{opacity:.3}}
@media (prefers-reduced-motion:reduce){.lv .live{animation:none}}
.lv .dash-live{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--info);border-radius:8px;padding:.7rem 1rem;margin:.2rem 0 1rem;font:400 .95rem/1.5 var(--sans)}
.lv .dash-live.quiet{border-left-color:var(--rule-strong)}
.lv .dash-live p{margin:.15rem 0}
.lv .dash-live .who{display:inline-block;min-width:5.2rem;color:var(--ink-3);font-size:.8rem;text-transform:uppercase;letter-spacing:.06em}
.lv .dash-live .stamp{color:var(--ink-3);font-size:.8rem;margin-top:.4rem}
.lv .dash-lines{display:grid;grid-template-columns:1fr 1fr;gap:.6rem 1.2rem;margin:0 0 1.2rem;font:400 .9rem/1.45 var(--sans)}
.lv .dash-lines>div{border:1px solid var(--rule);border-radius:8px;padding:.55rem .8rem;background:var(--surface)}
.lv .dash-lines>div.ask{border-color:var(--warn);background:var(--warn-soft)}
.lv .dash-lines ol{margin:.25rem 0 0;padding-left:1.3rem}.lv .dash-lines li{margin:.1rem 0}
.lv .dash-lines b{display:block;font:650 .72rem var(--sans);text-transform:uppercase;letter-spacing:.08em;color:var(--ink-3);margin-bottom:.15rem}
.lv .goalrow{display:flex;gap:.6rem;align-items:baseline;margin:1.3rem 0 .45rem;font:600 1.05rem var(--sans)}
.lv .goalrow a{color:inherit;text-decoration:none}
.lv .goalrow .n{margin-left:auto;font:400 .8rem var(--sans);color:var(--ink-3)}
.lv .tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(13.5rem,1fr));gap:.6rem}
.lv .tile{display:block;border:1px solid var(--rule);border-radius:8px;padding:.5rem .7rem .55rem;background:var(--surface);font:400 .86rem/1.4 var(--sans);color:var(--ink-2);text-decoration:none}
.lv .tile:hover{border-color:var(--accent)}
.lv .tile.t-done{background:var(--sunk)}
.lv .tile .top{display:flex;gap:.4rem;align-items:baseline}
.lv .tile .id{font:500 .74rem var(--mono);color:var(--ink-3);white-space:nowrap}
.lv .tile .ttl{font-weight:600;color:var(--ink)}
.lv .tile .st{margin:.15rem 0 .3rem;font-size:.78rem;color:var(--ink-3)}
.lv .tile .marks{display:flex;flex-wrap:wrap;gap:.15rem .3rem;font-size:.95rem}
.lv .tile .marks .gone{font:500 .75rem var(--sans);color:var(--ink-3);margin-left:.2rem}
.lv .aside{margin:.4rem 0 0;font:400 .82rem var(--sans);color:var(--ink-3)}
@media (max-width:640px){.lv .dash-lines{grid-template-columns:1fr}}
.lv .filters{display:flex;gap:.4rem;flex-wrap:wrap;margin:0 0 1rem;font:500 .8rem var(--sans)}
.lv .filters a{text-decoration:none}
.lv h2{font:600 1.2rem/1.3 var(--serif);margin:2.1rem 0 .6rem}
.lv.panelbox{font:400 .84rem/1.45 var(--sans)}
.lv .panelbox ul,.lv.panelbox ul{list-style:none;margin:0;padding:0}.lv .goal-title{font:600 1.35rem/1.25 var(--serif);margin:.1rem 0 .4rem}
.lv .lbl{font:650 .7rem var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lv table.lines th{padding-top:.8rem}
.lv table.lines code{font-size:.8em;color:var(--ink-3);margin-left:.3em}
.lv .tick{font:600 .74rem var(--sans);color:var(--ink-3);white-space:nowrap}
.lv .tick.yes{color:var(--ok)}
.lv .tick.no{color:var(--bad)}
.lv .box.bad{border-left:3px solid var(--bad);background:var(--bad-soft)}
.lv .box.outcome{border-left:3px solid currentColor;font-family:var(--sans)}
.lv .desc{color:var(--ink-2);margin:.1rem 0 .5rem;max-width:48rem}
.lv .ran{font:400 .86rem var(--sans);color:var(--ink-3);margin:0 0 .8rem}
.lv .qcard .lbl{margin-right:.3rem}
.lv .decisionrows dd{white-space:normal}
.lv .num.off{font-family:var(--mono);font-size:.85em;color:var(--warn)}
.lv .nowbox{background:var(--surface);border:1px solid var(--rule);border-left:3px solid var(--info);border-radius:8px;padding:.8rem 1.1rem;margin:.2rem 0 1.2rem}
.lv .nowbox.quiet{border-left-color:var(--rule-strong)}
.lv .nowbox p{margin:0 0 .25rem}
.lv .nowbox .what{font-size:1.05rem}
.lv .nowbox .stamp{font:400 .8rem var(--sans);color:var(--ink-3);margin:.4rem 0 0}
.lv .goalhead{display:flex;gap:.6rem;align-items:baseline;margin:1.4rem 0 .1rem;font:600 1.08rem var(--serif)}
.lv .goalhead a{color:inherit;text-decoration:none}
.lv .goalwhy{color:var(--ink-3);font:400 .86rem/1.45 var(--sans);margin:0 0 .2rem;max-width:44rem}
.lv .qrow{display:grid;grid-template-columns:1fr 8.5rem;gap:1rem;padding:.6rem 0;border-bottom:1px solid var(--rule)}
.lv .qrow h3{margin:0 0 .15rem;font:600 1rem var(--sans);text-transform:none;letter-spacing:0}
.lv .qrow p{margin:0;color:var(--ink-2);font-size:.94rem}
.lv .qrow ul{margin:.2rem 0;padding-left:1.1rem;color:var(--ink-2);font-size:.94rem}
.lv .qrow li{margin:.15rem 0}
.lv .qrow p+p,.lv .qrow ul+p{margin-top:.3rem}
.lv .qrow .side{font:400 .78rem var(--sans);color:var(--ink-3);text-align:right}
.lv .story{list-style:none;margin:0;padding:0 0 0 1rem;border-left:2px solid var(--rule)}
.lv .story .day{font:650 .7rem var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin:1rem 0 .3rem -1rem;padding-left:1rem}
.lv .story li.ev{position:relative;margin:0 0 .65rem;font:400 .92rem/1.5 var(--sans)}
.lv .story li.ev::before{content:"";position:absolute;left:-1.32rem;top:.5em;width:.5rem;height:.5rem;border-radius:50%;background:var(--rule-strong)}
.lv .story li.k-result::before{background:var(--ok)}
.lv .story li.k-stuck::before{background:var(--bad)}
.lv .story li.k-decision::before{background:var(--info);width:.65rem;height:.65rem;left:-1.4rem}
.lv .story li.k-decision{background:var(--info-soft);border-radius:6px;padding:.45rem .7rem}
.lv .story li.k-open{background:var(--warn-soft);border-radius:6px;padding:.45rem .7rem}
.lv .story li.k-open::before{background:var(--warn)}
.lv .story .so{display:block;color:var(--ink-2)}
.lv .story .so::before{content:"\\2192  ";color:var(--accent)}
.lv .story .who{font:650 .66rem var(--sans);letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);margin-right:.4rem}
.lv .earlier{font:400 .84rem/1.45 var(--sans);color:var(--ink-2);margin:.2rem 0 .6rem}
.lv .earlier li{margin:.15rem 0}
.lv .tries{font:500 .72rem var(--sans);color:var(--ink-3);margin-left:.4rem;white-space:nowrap}
.lv details.more{margin:0 0 1rem;font:400 .86rem var(--sans)}
.lv details.more>summary{cursor:pointer;color:var(--ink-3);padding:.2rem 0}
.lv details.note>summary{cursor:pointer;color:var(--ink-3)}
.lv .slot ul,.lv .decisionrows ul,.lv .slot ol{margin:.2rem 0 0;padding-left:1.3rem}
.lv .slot li,.lv .decisionrows li{margin:.25rem 0}
.lv .slot p+p,.lv .decisionrows p+p{margin-top:.5rem}
.lv .decisionrows p{margin:0}
.lv table.arms td:first-child{width:11.5rem}
.lv .asks{font:italic 400 .96rem/1.45 var(--serif);color:var(--ink-2);margin:0 0 .25rem}
.lv .limits ul{margin:.1rem 0 .7rem;padding-left:1.1rem;font:400 .9rem/1.5 var(--sans);color:var(--ink-2)}
.lv .limits p{margin:.1rem 0 .7rem;font:400 .9rem/1.5 var(--sans);color:var(--ink-2)}
.lv .box.explore{border-left:3px solid var(--warn);background:var(--warn-soft);font:400 .9rem/1.5 var(--sans)}
.lv .kind{font:650 .62rem var(--sans);letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);margin-left:.4rem;white-space:nowrap}
.lv table.roles td:first-child{width:9rem;font-weight:600}
.lv .slot.example{background:var(--sunk)}
.lv ul.runs{list-style:none;margin:0 0 1rem;padding:0;font:400 .9rem/1.5 var(--sans)}
.lv ul.runs li{padding:.55rem 0;border-bottom:1px solid var(--rule)}
.lv .outcome-line{font:400 .9rem/1.5 var(--sans);margin:0 0 1rem}
.lv .gfilter{width:100%;max-width:24rem;padding:.4rem .7rem;border:1px solid var(--rule-strong);border-radius:6px;background:var(--surface);color:var(--ink);font:400 .9rem var(--sans);margin:0 0 .8rem}
.lv details.ggroup{border-bottom:1px solid var(--rule)}
.lv details.ggroup>summary{cursor:pointer;padding:.55rem 0;font:600 1rem var(--serif)}
.lv details.ggroup>summary span{font:400 .78rem var(--sans);color:var(--ink-3);margin-left:.5rem}
.lv dl.gloss{display:grid;grid-template-columns:13rem 1fr;gap:.35rem 1rem;margin:.2rem 0 1rem;font:400 .88rem/1.45 var(--sans)}
.lv dl.gloss dt{font-weight:600}
.lv dl.gloss dd{margin:0;color:var(--ink-2)}
.lv dl.gloss :target{background:var(--mark)}
.lv .gex{display:block;margin-top:.3rem;font-size:.93rem;color:var(--ink-2)}
.lv .gex::before{content:"For example: ";font-weight:600}
.lv .gsee{display:block;font:.82rem var(--sans);margin-top:.2rem}
@media (max-width:640px){.lv dl.gloss{grid-template-columns:1fr}.lv .qrow{grid-template-columns:1fr}}
"""


def code_url(lab):
    """Where the code repository is on the web, ready to stand in an href; nothing when it is not a web address."""
    url = str(lab.cfg.get("code_url", "")).rstrip("/")
    return e(url) if re.match(r"https?://", url) else ""


def frame(lab, title, body, panel="", crumbs=()):
    """What a page function hands back: the provider turns it into a view in folio's shell."""
    crumb = '<div class="crumbs">' + " › ".join(f'<a href="{h}">{e(t)}</a>' for h, t in crumbs) + "</div>" if crumbs else ""
    return {"title": title, "body": crumb + body, "panel": panel}


def pages(lab):
    """The library's pages, by path, with their titles."""
    out = {}
    base = os.path.join(lab.root, lab.cfg.get("library", "docs"), "content")
    for index in glob.glob(os.path.join(base, "*", "*", "index.html")):
        m = re.search(r'<meta name="title" content="([^"]*)"', L.read(index))
        rel = os.path.relpath(os.path.dirname(index), base)
        out[rel] = html.unescape(m.group(1)) if m else rel
    return out


def slot(name, inner, cls=""):
    return f'<div class="slot {cls}"><h5>{e(name)}</h5>{inner if inner.startswith(("<p>", "<ul>", "<ol>")) else "<p>" + inner + "</p>"}</div>'


def table_html(T, lines, home=None):
    """A pipe table as the card writes it: the first row is the header, a row of dashes under it is skipped."""
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r if c)]
    if not rows:  # only a rule, or a bare pipe: there is no table, so the text is shown as written
        return f"<p>{T(' '.join(lines), home)}</p>"
    head, body = rows[0], rows[1:]
    return ('<div class="tw"><table class="t card">' + "<tr>" + "".join(f"<th>{T(c, home)}</th>" for c in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{T(c, home)}</td>" for c in r) + "</tr>" for r in body) + "</table></div>")


def block(T, text, home=None):
    """A slot's prose as written: its paragraphs as paragraphs, its lists as lists, numbered when the card numbers them,
    its tables as tables, and a heading line (### ...) as a heading."""
    out = []
    mark = re.compile(r"^(- |\d+\. )")
    for part in re.split(r"\n\s*\n", str(text or "").strip()):
        lines = [l.strip() for l in part.splitlines() if l.strip()]
        while lines and lines[0].startswith("### "):
            out.append(f"<h3>{T(lines.pop(0)[4:], home)}</h3>")
        if lines and all(l.startswith("|") for l in lines):
            out.append(table_html(T, lines, home))
            continue
        first = next((i for i, l in enumerate(lines) if mark.match(l)), None)
        if lines and first is None:
            out.append(f"<p>{T(' '.join(lines), home)}</p>")
        elif lines:
            if first:
                out.append(f"<p>{T(' '.join(lines[:first]), home)}</p>")
            rows = []
            for l in lines[first:]:
                m = mark.match(l)
                if m:
                    rows.append(l[m.end():])
                else:
                    rows[-1] += " " + l
            tag = "ul" if lines[first].startswith("- ") else "ol"
            out.append(f"<{tag}>" + "".join(f"<li>{T(r, home)}</li>" for r in rows) + f"</{tag}>")
    return "".join(out)


def boxed(T, name, text, cls="full", home=None, extra=""):
    """One slot in its box, under the template's fixed label: the label is the heading, the same on every page, so a
    heading line the card starts the slot with is dropped. Nothing when the slot is empty and nothing goes with it."""
    t = re.sub(r"^#{2,3} .+\n?", "", str(text or "").strip()).strip()
    if not L.flat(t) and not extra:
        return ""
    return slot(name, block(T, t, home) + extra, cls)


def slots(*boxes):
    inner = "".join(boxes)
    return f'<div class="slots">{inner}</div>' if inner else ""


SVG_TAGS = {"svg", "g", "defs", "marker", "rect", "circle", "ellipse", "line", "path", "polygon", "polyline", "text", "tspan", "title", "desc", "style"}
SVG_ATTRS = {"id", "class", "style", "viewBox", "xmlns", "role", "aria-label", "aria-hidden", "width", "height", "x", "y", "x1", "y1", "x2", "y2",
             "cx", "cy", "r", "rx", "ry", "dx", "dy", "d", "points", "transform", "opacity", "refX", "refY", "markerWidth", "markerHeight",
             "markerUnits", "orient", "text-anchor", "dominant-baseline", "alignment-baseline", "letter-spacing", "word-spacing",
             "preserveAspectRatio", "vector-effect", "visibility", "display", "clip-rule", "pathLength", "textLength", "lengthAdjust",
             "href", "xlink:href"}
SVG_PREFIXES = ("font-", "fill", "stroke", "marker-")


def safe_css(css):
    """CSS that cannot reach outside a picture or fetch anything: no at-rule, no url() but a reference inside the
    picture, no markup, no expression, no script."""
    flat = re.sub(r"\s+", "", html.unescape(css)).lower()
    if "@" in flat or "<" in flat or "expression" in flat or "javascript:" in flat or "\\" in flat:
        return False
    return all(u.startswith("#") for u in re.findall(r"url\(['\"]?([^)]*)", flat))


def scoped_style(css):
    """A picture's own style sheet, every rule kept to the picture: each selector is a class selector, and is
    prefixed with `figure.pic`, so no rule restyles the site. None when it is anything else."""
    if not safe_css(css):
        return None
    out = []
    for sel, body in re.findall(r"([^{}]*)\{([^{}]*)\}", css):
        sels = [s.strip() for s in sel.split(",")]
        if not all(re.fullmatch(r"\.[A-Za-z_][\w-]*(?:[\s>]*\.?[A-Za-z_][\w-]*)*", s) for s in sels):
            return None
        out.append(",".join(f"figure.pic {s}" for s in sels) + "{" + body.strip() + "}")
    if re.sub(r"[^{}]*\{[^{}]*\}", "", css).strip():  # text outside any rule
        return None
    return "".join(out)


def safe_svg(text):
    """A picture.svg parsed as XML and written again from what it holds that is allowed: drawing elements only, their
    geometry and presentation attributes only, links only inside the picture. None when it does not parse as one
    svg element, or carries a document type, whose entities could be anything."""
    import xml.etree.ElementTree as ET
    if re.search(r"<!DOCTYPE|<!ENTITY", text, flags=re.I):
        return None
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except ET.ParseError:
        return None
    local = lambda name: name.rsplit("}", 1)[-1]

    def attr_name(name):
        if name.startswith("{http://www.w3.org/1999/xlink}"):
            return "xlink:" + local(name)
        return None if name.startswith("{") else name

    def ok(name, value):
        if name is None or not (name in SVG_ATTRS or name.startswith(SVG_PREFIXES)) or name.lower().startswith("on"):
            return False
        flat = re.sub(r"[\s\x00-\x1f]+", "", html.unescape(value)).lower()
        if "javascript:" in flat or "data:" in flat or "vbscript:" in flat:
            return False
        if name in ("href", "xlink:href"):
            return flat.startswith("#")
        if name == "style":
            return safe_css(value)
        return all(u.startswith("#") for u in re.findall(r"url\(['\"]?([^)]*)", flat))

    def write(el):
        tag = local(el.tag)
        if tag not in SVG_TAGS:
            return ""
        if tag == "style":
            css = scoped_style(el.text or "")
            return f"<style>{css}</style>" if css else ""
        attrs = "".join(f' {n}="{e(v)}"' for n, v in ((attr_name(k), v) for k, v in el.attrib.items()) if ok(n, v))
        if tag == "svg":
            attrs = ' xmlns="http://www.w3.org/2000/svg"' + attrs.replace(' xmlns="http://www.w3.org/2000/svg"', "")
        inner = e(el.text or "", quote=False) + "".join(write(c) + e(c.tail or "", quote=False) for c in el)
        return f"<{tag}{attrs}>{inner}</{tag}>"

    return write(root) if local(root.tag) == "svg" else None


def picture(lab, n):
    """The picture beside a card (`picture.svg`), drawn inline at the top of its page. It is the lab's own drawing, so it
    may use the site's colours. It is parsed and written again from an allowlist, so nothing in it can run or reach
    outside it; a file that does not parse as an SVG is not drawn, and the page says so."""
    if n["type"] == "decision":
        return ""
    p = os.path.join(lab.root, n["dir"], "picture.svg")
    if not os.path.isfile(p):
        return ""
    svg = safe_svg(L.read(p))
    if svg is None:
        return '<p class="muted pic-note">The picture beside this card (picture.svg) is not an SVG drawing that can be shown here, and is not drawn.</p>'
    return f'<figure class="pic">{svg}</figure>'


def decided_notes(lab, T, n):
    """The settled decisions about a node that carry a Note: what changes how the node is read, each with its decision."""
    out = []
    for d in lab.decisions:
        if d["state"] == "done" and n["id"] in d["about"] and L.flat(d["slots"].get("Note", "")):
            out.append(f'<p><b>Decided in {named(lab, d["id"])}:</b></p>{block(T, d["slots"]["Note"])}')
    return "".join(out)


def so_far(lab, T, n, home=None):
    """What we know so far: the card's So far, or, while it says nothing, the notes of the decisions settled about it."""
    text = n["slots"].get("So far", "")
    return boxed(T, "What we know so far", text, "full key", home, "" if L.flat(re.sub(r"^#{2,3} .+\n?", "", str(text).strip())) else decided_notes(lab, T, n))


def record_html(summary, inner):
    """The record behind a page, folded at its bottom: runs, reviews, earlier plans, files and log."""
    return f'<details class="record"><summary>{e(summary)}</summary>{inner}</details>'


def arms_table(lab, T, x):
    """Each thing an experiment compares, by name, with what it is."""
    if not x["arms"]:
        return ""
    return ('<table class="t arms"><tr><th>Arm</th><th>What it is</th></tr>'
            + "".join(f'<tr><td><b>{T(name)}</b></td><td>{T(what)}</td></tr>' for name, what in x["arms"]) + "</table>")


def log_html(lab, T, lines, with_about=True):
    if not lines:
        return '<p class="muted">Nothing yet.</p>'
    out = ['<ul class="log">']
    for l in reversed(lines):
        who = {"decision": "decided", "agent": "agent", "doing": "started"}.get(l["kind"], l["kind"])
        so = f'<span class="so">{T(l["so"])}</span>' if l["so"] else ""
        about = ref(lab, l["about"]) if with_about else ""
        out.append(f'<li><span class="d">{clock(l["at"])}</span><span>{pill(who)}</span><span>{about}</span><span>{T(l["what"])}{so}</span></li>')
    return "".join(out) + "</ul>"


def happened(lines):
    """A page's log: what happened, without the lines that only said what the agent was starting on."""
    return [l for l in lines if l["kind"] != "doing"]


def decision_box(lab, T, d, link=True, title=True):
    """One decision as the operator reads it: what there is to discuss, or what was decided and why."""
    done = d["state"] == "done"
    about = ", ".join(named(lab, i) if i in lab.nodes else f'the resource <a href="/resources#{e(i)}">{e(i)}</a>' for i in d["about"] if i in lab.nodes or i in lab.resources)
    head = f'{ref(lab, d["id"]) if link else e(d["id"])} · raised {nice(d["date"])}' + (f" · about {about}" if about else "")
    rows = []
    if done:
        rows.append((f'Decided {nice(d["decided"].get("date"))}', block(T, d["slots"].get("Decided", ""))))
    rows += [(verb if done else f"Would {verb.lower()}", "<br>".join(named(lab, i) if i in lab.nodes else e(i) for i in d[key])) for key, verb in (("parks", "Parks"), ("unparks", "Brings back")) if d[key]]
    if d["folds"]:
        rows.append(("Folds in", ", ".join(e(str(i)) for i in d["folds"]) + ": earlier drafts, revised into this one before anything acted on them"))
    if done:
        rows.append(("Locked", f'since {clock(d["acted"])}: something acted on it, so a change of mind is a new decision') if d["locked"]
                    else ("Draft", "Nothing has acted on it yet: it is revised here, not replaced by a new decision"))
    if d["order"]:
        rows.append(("Orders the work" if done else "Would order the work", "<ol>" + "".join(f"<li>{named(lab, i) if i in lab.nodes else e(i)}</li>" for i in d["order"]) + "</ol>"))
    if done and L.flat(d["slots"].get("Note", "")):
        rows.append(("What it changes for the reader", block(T, d["slots"]["Note"])))
    rows += [(k, block(T, d["slots"][k])) for k in ("Seen", "Options", "Recommendation") if L.flat(d["slots"].get(k, ""))]
    if not done:
        held = lab.held_by(d)
        rows.append(("Held until it is settled", "<br>".join(named(lab, h["id"]) for h in held) if held else "Nothing: the work goes on."))
    return (f'<div class="box decision{" closed" if done else ""}"><div class="decisionhead">{head}</div>'
            + (f'<p class="decisionq">{e(d["title"])}</p>' if title else "")
            + '<dl class="decisionrows">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl></div>")


def decisions_about(lab, n):
    """Links to the decisions a node came out of or is discussed in."""
    ids = ([n["from"]] if n.get("from") in lab.nodes else []) + [d["id"] for d in lab.decisions if n["id"] in d["about"] and d["id"] != n.get("from")]
    return "<h4>Decisions</h4><ul>" + "".join(f"<li>{dot(lab.nodes[i])} {named(lab, i)}</li>" for i in ids) + "</ul>" if ids else ""


def edges_panel(lab, n):
    out = [decisions_about(lab, n)]
    if n.get("needs"):
        out.append("<h4>Needs</h4><ul>" + "".join(f"<li>{dot(lab.nodes[i])} {named(lab, i)}</li>" for i in n["needs"] if i in lab.nodes) + "</ul>")
    by = [x for x in lab.questions + lab.items if n["id"] in (x.get("needs") or []) and x["state"] not in ("replaced", "dropped")]
    if by:
        out.append(f"<h4>{'Used by' if n.get('state') in L.CLOSED else 'Needed by'}</h4><ul>" + "".join(f"<li>{dot(x)} {named(lab, x['id'])}</li>" for x in by) + "</ul>")
    if n.get("uses"):
        rows = []
        for r in n["uses"]:
            res = lab.resources.get(r) or {}
            cap = lab.cap(n, r)
            rows.append(f'<li><a href="/resources#{e(r)}">{e(r)}</a>' + (f'<br><span class="muted">at most {num(cap)} {e(str(res.get("unit", "")))} a run'
                        + (", its own cap" if r in n["override"] else "") + "</span>" if lab.metered(r) and isinstance(cap, (int, float)) else "") + "</li>")
        out.append("<h4>Uses</h4><ul>" + "".join(rows) + "</ul>")
    if n.get("see"):
        titles = pages(lab)
        own = [str(p) for p in n["see"] if ":" not in str(p)]
        other = [str(p) for p in n["see"] if ":" in str(p) and outside(lab, p)]
        if own:
            out.append("<h4>Explained on</h4><ul>" + "".join(f'<li><a href="/docs/{e(p)}/">{e(titles.get(p, p))}</a></li>' for p in own) + "</ul>")
        if other:
            out.append("<h4>Background</h4><ul>" + "".join(f'<li><a href="{e(outside(lab, p))}">{e(page_title(lab, p))}</a></li>' for p in other) + "</ul>")
    return "".join(out)


def decided_by(lab, x):
    """The outcome of a finished experiment as a sentence: how many bars were met, and which one decided it."""
    t = lab.ticks(x)
    bars = t["confirmed"]
    held = sum(bool(l["holds"]) for l in bars)
    met = f'{held} of {len(bars)} bar{"s" if len(bars) != 1 else ""} met'
    if x["outcome"] == "refuted":
        return f"{met[0].upper() + met[1:]}. Refuted by: " + next(l["say"] for l in t["refuted"] if l["holds"]) + "."
    if x["outcome"] == "confirmed":
        return "Confirmed: every bar is met, and nothing that would refute it holds."
    return f"Unclear: {met}, and nothing that would refute it holds. Not met: " + "; ".join(l["say"] for l in bars if not l["holds"]) + "."


def tick_rows(lab, x):
    """The bars, grouped by what each is for, each ticked once the results are reviewed. A line's test is its tooltip.
    A bar written on both sides (confirmed if at least, refuted if under) is shown once, and says that missing it refutes."""
    t = lab.ticks(x)
    roled = any(l.get("role") for l in t["confirmed"])
    groups = {}
    for l in t["confirmed"]:
        key = l.get("role") or ("needed" if roled or not l["twice"] else "either")
        groups.setdefault(key, []).append((l, "met", "missed: this refutes it" if l["twice"] else "not met", True))
    for r in t["refuted"]:
        if not any(L.complement(c, r) for c in t["confirmed"]):
            groups.setdefault("refute", []).append((r, "holds: this refutes it", "does not hold", False))
    plain = not roled and "either" not in groups
    heads = {**L.ROLES, "either": "Decides it either way: met confirms, missed refutes", "needed": "Confirmed if all of these hold" if plain else "Also needed to confirm",
             "refute": "Refuted if any of these holds" if plain else "Would refute it"}
    out = ['<table class="t lines">']
    for key in ("answer", "readable", "counts", "either", "needed", "refute"):
        rows = groups.get(key) or ([({"say": "No line yet.", "test": None, "holds": None, "row": None}, "", "", True)] if plain and key in ("needed", "refute") else [])
        if not rows:
            continue
        out.append(f'<tr><th colspan="3">{heads[key]}</th></tr>')
        for l, yes, no, wanted in rows:
            known = x["reviewed"] and l["holds"] is not None
            good = l["holds"] if wanted else not l["holds"]
            mark = f'<span class="tick {"yes" if good else "no"}">{yes if l["holds"] else no}</span>' if known else '<span class="tick">not known yet</span>'
            value = f'<a class="num" href="/{x["id"]}#r-{e(l["row"]["name"])}">{e(L.shown(l["row"]))}</a>' if known and l["row"] else ""
            say = f'<span data-tip="{e(l["test"])}">{e(l["say"])}</span>' if l["test"] else e(l["say"])
            out.append(f'<tr><td>{say}</td><td class="n">{value}</td><td>{mark}</td></tr>')
    return "".join(out) + "</table>"


def cost_rows(lab, xs):
    """What experiments have used and may still use of each metered resource: one row per experiment and resource."""
    rows = []
    for x in xs:
        for name in x["uses"]:
            if not lab.metered(name):
                continue
            unit, cap, used = e(str(lab.resources[name].get("unit", ""))), lab.cap(x, name), lab.spent(x, name)
            may = f"up to {num(cap)} {unit}" if isinstance(cap, (int, float)) and not x["finished"] else "nothing more: it has run" if x["finished"] else ""
            rows.append(f'<tr><td>{named(lab, x["id"])}</td><td><a href="/resources#{e(name)}">{e(name)}</a></td><td class="n">{num(used)} {unit}</td><td>{may}</td></tr>')
    return rows


def cost_box(lab, T, xs, why=()):
    rows = cost_rows(lab, xs)
    if not rows:
        return ""
    left = " ".join(f'{e(n)}: {num(lab.left(n))} of {num(lab.resources[n]["granted"])} {e(str(lab.resources[n].get("unit", "")))} left.' for n in dict.fromkeys(r for x in xs for r in x["uses"] if lab.metered(r)))
    said = "".join(f"<p>{T(w)}</p>" for w in why if L.flat(w))
    return (f'<h2>What it costs</h2>{said}<table class="t"><tr><th>Step</th><th>Resource</th><th>Used so far</th><th>One more run may use</th></tr>{"".join(rows)}</table>'
            f'<p class="muted" style="font:.86rem var(--sans)">{left}</p>')


def where_to_look(lab, items):
    """The files behind a page: each card, each plan's files, each build's tests. Paths are from the lab's root."""
    out = []
    for x in items:
        files = [x["path"]]
        plan = os.path.join(lab.root, x["dir"], "plan")
        if x["type"] == "experiment" and os.path.isdir(plan):
            files += sorted(os.path.relpath(os.path.join(top, f), lab.root) for top, _, fs in os.walk(plan) for f in fs if not f.startswith(("original-", ".")) and "__pycache__" not in top)
        url = code_url(lab)
        tests = [(f'<a href="{url}/blob/main/{e(str(t))}"><code>{e(str(t))}</code></a>' if url else f"<code>{e(str(t))}</code>") + " (in the code repository)" for t in x.get("tests") or []]
        out.append(f'<p class="lbl">{e(x["title"])}</p><ul class="earlier">' + "".join(f"<li><code>{e(f)}</code></li>" for f in files) + "".join(f"<li>{t}</li>" for t in tests) + "</ul>")
    return f'<details class="more"><summary>Where to look: the files behind this page</summary>{"".join(out)}</details>' if out else ""


def item_line(lab, T, x):
    """One sentence on where an experiment or a build stands."""
    if x["type"] == "experiment" and x["state"] == "done":
        return T(x["slots"].get("Means", ""), x["id"])
    if x["type"] == "reading" and x["state"] == "done":
        return T(re.split(r"\n\s*\n", x["slots"].get("Suggests", "").strip())[0])
    if x.get("dropped"):
        return "Dropped: " + T(str(x["dropped"]))
    if x["next"]:
        return ("Next: " if x["mine"] else "Waiting on ") + T(you(x["next"]))
    return ""


def qcard(lab, T, q):
    """A question in a list: its title and what is known so far. Why we ask it is shown only until something is known."""
    live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
    done = sum(x["state"] == "done" for x in live)
    asks = f'<p class="asks">{e(q["asks"])}</p>' if q["asks"] != q["title"] else ""
    body = asks + (block(T, q["slots"].get("So far", "")) if live else f'<p class="muted">{T(q["description"])}</p>')
    count = f"{done} of {len(live)} steps done" if live else ""
    return (f'<div class="qrow"><div><h3>{dot(q)} <a href="/{q["id"]}">{e(q["title"])}</a></h3>{body}</div>'
            f'<div class="side">{status(q)}<br>{count}</div></div>')


def live_box(lab, T):
    """The top of Now: everything live at this moment, each with a pulsing sign, and how fresh the record is."""
    rows = []
    for x in lab.experiments:
        for r in x["runs"] + x["trials"]:
            if r["state"] == "running" and not r["orphan"]:
                rows.append(f'<p><span class="who">running</span>{mark("running")} {named(lab, x["id"])}, since {clock(r["started"])}'
                            + (f' on {e(", ".join(x["uses"]))}' if x["uses"] else "") + ".</p>")
    for m in [m for m in lab.missions if m["state"] == "current"]:
        last = next((l for l in reversed(m["log"]) if l.get("what")), None)
        rows.append(f'<p><span class="who">mission</span>{mark("running")} <a href="/missions#{e(m["id"])}">{e(m["id"])} {e(m["title"])}</a>'
                    + (f' <span class="muted">last, {nice(last["day"])} {e(last["time"])}: {T(last["what"])}</span>' if last else "") + "</p>")
    d = lab.doing()
    if d:
        rows.append(f'<p><span class="who">the agent</span>{mark("running")} on {named(lab, d["about"])}: {T(d["what"])} <span class="muted">Why now:</span> {T(d["so"])} <span class="muted">Since {clock(d["at"])}.</span></p>')
    elif rows:
        rows.append('<p><span class="who">the agent</span><span class="muted">has not said it is on anything.</span></p>')
    if not rows:
        rows.append('<p><span class="who">quiet</span>Nothing is running and nobody is on anything.</p>')
    last = lab.last_record()
    stamp = f'<p class="stamp">Last recorded activity: {clock(last.isoformat())} UTC, {ago(last)}.</p>' if last else ""
    quiet = "" if d or any("live" in r for r in rows) else " quiet"
    return f'<div class="dash-live{quiet}">{"".join(rows)}{stamp}</div>'


def ask_and_next(lab, T):
    """Two short lines under what is live: what needs the operator, and what is next for the agent."""
    talk = lab.open_decisions()
    ask = ("".join(f'<p>{dot(d)} {named(lab, d["id"])}</p>' for d in talk)) if talk else '<p class="muted">Nothing.</p>'
    busy = lab.doing()["about"] if lab.doing() else None
    nxt = [x for x in lab.yours() if x["id"] != busy]
    waits = [x for x in lab.pursued() if x["state"] == "waiting"]
    by = lab.ordered_by()
    if nxt:
        then = (f'<p class="muted">In the order of the work set by {named(lab, by["id"])}.</p>' if by and len(nxt) > 1 else "") + "<ol>" + "".join(
            f'<li>{dot(x)} {named(lab, x["id"])}: {T(you(x["next"]))}</li>' for x in nxt) + "</ol>"
    else:
        then = '<p class="muted">Nothing is the agent\'s to move.</p>'
    if waits:
        then += f'<p class="muted">{len(waits)} step{"s" if len(waits) != 1 else ""} wait{"" if len(waits) != 1 else "s"}: ' + "; ".join(f'{named(lab, x["id"])} on {T(you(x["next"]))}' for x in waits[:3]) + (f"; and {len(waits) - 3} more" if len(waits) > 3 else "") + ".</p>"
    return f'<div class="dash-lines"><div class="{"ask" if talk else ""}"><b>Needs you</b>{ask}</div><div><b>Next for the agent</b>{then}</div></div>'


def counts(steps):
    """How many steps are in each state, in a fixed order: [(key, n)]."""
    seen = {}
    for x in steps:
        seen[key(x)] = seen.get(key(x), 0) + 1
    return [(k, seen[k]) for k in ORDER if k in seen] + [(k, n) for k, n in seen.items() if k not in ORDER]


def tile(lab, T, q):
    """A question on Now: its state and answer, and one sign per step in tree order; what was replaced or dropped is a count."""
    live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
    gone = len(q["items"]) - len(live)
    marks = "".join(dot(x, f'{x["id"]} {x["title"]}: {label(x)}') for x in live)
    marks += f'<span class="gone" title="replaced or dropped">\u2013{gone}</span>' if gone else ""
    marks = marks or '<span class="muted" style="font-size:.78rem">nothing under it yet</span>'
    return (f'<a class="tile t-{q["state"]}" href="/{q["id"]}" title="{e(q["asks"])}"><div class="top"><span class="id">{e(q["id"].split(".")[-1])}</span>'
            f'<span class="ttl">{e(q["title"])}</span></div><div class="st">{status(q)}</div><div class="marks">{marks}</div></a>')


def lab_map(lab, T):
    """The lab at a glance: one row per goal, with how many of its questions are answered, and one tile per question."""
    out = []
    for g in lab.live(lab.goals):
        qs = lab.live(g["questions"])
        answered = sum(q["state"] == "done" for q in qs)
        out.append(f'<div class="goalrow">{dot(g)}<a href="/{g["id"]}">{e(g["id"])} {e(g["title"])}</a><span class="n">{answered} of {len(qs)} question{"s" if len(qs) != 1 else ""} answered</span></div><p class="goalwhy">{T(g["description"])}</p>')
        out.append('<div class="tiles">' + "".join(tile(lab, T, q) for q in qs) + "</div>")
    return "".join(out)


def story(lab, T, g):
    """A goal's history as one list, the latest first: what was found, what got stuck, what the agent chose, and what was decided with the operator."""
    under = lambda i: i == g["id"] or i.startswith(g["id"] + ".")
    mine = {d["id"] for d in lab.decisions if any(under(a) for a in d["about"]) or d["id"] == g.get("from") or any(q.get("from") == d["id"] for q in g["questions"])}
    events = []
    who = {"result": "found", "stuck": "stuck", "agent": "the agent"}
    for l in lab.lines:
        if l["kind"] == "decision" and l["about"] in mine:
            d = lab.nodes[l["about"]]
            text = f'<span class="who">decided with you</span>{ref(lab, d["id"])} <a href="/{d["id"]}">{e(d["title"])}</a><span class="so">{T(d["slots"].get("Decided", ""))}</span>'
            kind = "decision"
        elif l["kind"] in who and under(l["about"]):
            n = lab.nodes.get(l["about"])
            text = f'<span class="who">{who[l["kind"]]}</span>{T(l["what"])} <a class="ref" href="/{l["about"]}" data-tip="{e(n["title"]) if n else ""}">{e(l["about"])}</a>' + (f'<span class="so">{T(l["so"])}</span>' if l["so"] else "")
            kind = l["kind"]
        else:
            continue
        events.append((l["day"], f'<li class="ev k-{kind}">{text}</li>'))
    out, day = ['<ul class="story">'], None
    waiting = [d for d in lab.open_decisions() if d["id"] in mine]
    if waiting:
        out.append('<li class="day">Now</li>')
    for d in reversed(waiting):
        out.append(f'<li class="ev k-open"><span class="who">to discuss with you</span>{ref(lab, d["id"])} <a href="/{d["id"]}">{e(d["title"])}</a><span class="so">{T(d["slots"].get("Seen", ""))}</span></li>')
    for when, item in reversed(events):
        if when != day:
            day = when
            out.append(f'<li class="day">{nice(day)}</li>')
        out.append(item)
    return "".join(out) + "</ul>" if len(out) > 1 else '<p class="muted">Nothing has happened yet.</p>'


# ---------------------------------------------------------------- pages

def home(lab, T):
    """Now, the dashboard: what is live, what needs the operator and what is next, the map of the lab, the resources,
    the latest events. All of it is worked out from the record."""
    out = [live_box(lab, T), ask_and_next(lab, T)]
    talk = [decision_box(lab, T, d) for d in lab.open_decisions()]
    if talk:
        out.append("<h2>To discuss with you</h2>" + "".join(talk))
    out.append("<h2>The lab</h2>" + lab_map(lab, T))
    if lab.resources:
        out.append('<h2>Resources</h2>' + resources_table(lab))
    latest = happened(lab.lines)[-5:]
    out.append('<h2>Latest</h2>' + log_html(lab, T, latest) + '<p style="font:.85rem var(--sans)"><a href="/log">The whole log</a></p>')
    out.append(set_aside_html(lab, T))
    return frame(lab, lab.cfg.get("title", lab.cfg["name"]), "".join(out))


def parked_line(lab, T, q):
    d = lab.parked_by(q["id"])
    return f'<p>{named(lab, q["id"])}: parked by {named(lab, d["id"])}. {T(L.first_sentence(L.flat(d["slots"].get("Decided", ""))))}</p>'


def set_aside_html(lab, T):
    """What was set aside, apart from the work: each parked question with the decision that parked it, then what was
    dropped and the goals that were closed, folded."""
    aside = lab.set_aside()
    if not any(aside.values()):
        return ""
    out = ["<h2>Set aside</h2>"]
    if aside["parked"]:
        out.append('<p class="muted" style="font:.84rem var(--sans)">Parked by a decision; each comes back only by another.</p>' + "".join(parked_line(lab, T, q) for q in aside["parked"]))
    if aside["dropped"]:
        out.append(f'<details class="old"><summary>Dropped questions ({len(aside["dropped"])})</summary>' + "".join(
            f'<p>{named(lab, q["id"])}: {T(str(q.get("dropped") or lab.nodes[q["goal"]].get("dropped") or ""))}</p>' for q in aside["dropped"]) + "</details>")
    if aside["goals"]:
        out.append(f'<details class="old"><summary>Closed goals ({len(aside["goals"])})</summary>' + "".join(
            f'<p>{named(lab, g["id"])}: {status(g)}{". " + T(str(g["dropped"])) if g.get("dropped") else ""}</p>' for g in aside["goals"]) + "</details>")
    return "".join(out)


def resources_table(lab):
    per = any(isinstance(r.get("per_run"), (int, float)) for r in lab.resources.values() if isinstance(r, dict))  # the column is there only when a resource sets it
    out = ['<table class="t"><tr><th>Resource</th><th>Used</th><th>Granted</th>' + ("<th>One run may use</th>" if per else "") + "</tr>"]
    for name, r in lab.resources.items():
        if lab.metered(name):
            unit = e(str(r.get("unit", "")))
            share = min(100, 100 * lab.used(name) / r["granted"]) if r["granted"] else 0
            used = f'<span class="bar"><i class="info" style="width:{share:.0f}%"></i></span> {num(lab.used(name))} {unit}'
            out.append(f'<tr><td><a href="/resources#{e(name)}">{e(name)}</a><br><span class="muted">{e(str(r.get("what", "")))}</span></td><td class="n">{used}</td><td class="n">{num(r["granted"])} {unit}</td>'
                       + (f'<td class="n">{num(r["per_run"]) + " " + unit if isinstance(r.get("per_run"), (int, float)) else ""}</td>' if per else "") + "</tr>")
        else:
            out.append(f'<tr><td><a href="/resources#{e(name)}">{e(name)}</a><br><span class="muted">{e(str(r.get("what", "")))}</span></td><td colspan="{3 if per else 2}" class="muted">not metered</td></tr>')
    return "".join(out) + "</table>"


def goal_page(lab, T, g):
    """A goal: what it wants to be able to say and a picture of it; its claim, its idea in one case and its design, each
    in its box; who plays what and the words it uses; its questions; its story."""
    body = [f'<h1>{e(g["title"])}</h1>', f'<p class="lead">{T(g["description"])}</p>' if L.flat(g["description"]) else "", picture(lab, g)]
    body.append(slots(boxed(T, "What we would claim, and against what", g["slots"].get("Claim", ""), "full key"),
                      boxed(T, "The idea in one case", g["slots"].get("Example", ""), "full example"),
                      boxed(T, "The design, and how this lab approximates it", g["slots"].get("Approach", ""))))
    pairs = [tuple(p.strip() for p in (i.split(": ", 1) + [""])[:2]) for i in L.items(g["slots"].get("Roles", ""))]
    if pairs:
        body.append('<h2>Who plays what</h2><table class="t roles"><tr><th>Role</th><th>Played by, and what it does</th></tr>' + "".join(f"<tr><td>{T(a)}</td><td>{T(b)}</td></tr>" for a, b in pairs) + "</table>")
    words = lab.vocabulary(g)
    if words:  # the names are the card's; what each means is the glossary's, whatever the card says after a colon
        rows = "".join(f'<tr><td>{T.term(w["entry"]["term"]) if w["entry"] else e(w["name"])}</td><td>' + (e(w["entry"]["definition"]) + avoid_note(w["entry"]) if w["entry"] else '<span class="muted">not in the glossary</span>') + "</td></tr>" for w in words)
        body.append('<h2>The words this lab uses</h2><table class="t roles"><tr><th>Word</th><th>What it means here, everywhere</th></tr>' + rows + "</table>")
    body.append("<h2>Questions</h2>" + "".join(qcard(lab, T, q) for q in lab.live(g["questions"])))
    parked = [q for q in g["questions"] if q["state"] == "parked"]
    if parked:
        body.append(f'<details class="old"><summary>Parked questions ({len(parked)})</summary>' + "".join(parked_line(lab, T, q) for q in parked) + "</details>")
    gone = [q for q in g["questions"] if q["state"] == "dropped"]
    if gone:
        body.append(f'<details class="old"><summary>Dropped questions ({len(gone)})</summary>' + "".join(f'<p>{named(lab, q["id"])}: {T(str(q.get("dropped") or g.get("dropped") or ""))}</p>' for q in gone) + "</details>")
    body.append('<h2>The story so far</h2><p class="muted" style="font:.84rem var(--sans)">The latest first.</p>' + story(lab, T, g))
    return frame(lab, g["title"], "".join(body), edges_panel(lab, g), [("/", "Now")])


def earlier(lab, T, x):
    """The plans an experiment replaced, each with the sentence that says why it was replaced."""
    chain = lab.chain(x)
    if not chain:
        return ""
    newer, rows = x, []
    for old in chain:
        why = L.flat(newer.get("because") or "")
        rows.append(f'<li>{named(lab, old["id"])}' + (f': {T(why)}' if why else "") + "</li>")
        newer = old
    return f'<p class="lbl">Earlier plans, replaced</p><ul class="earlier">{"".join(rows)}</ul>'


def step_row(lab, T, x):
    tries = len(lab.chain(x)) + 1 if x["type"] == "experiment" else 1
    tag = f'<span class="tries">{ordinal(tries)} plan</span>' if tries > 1 else ""
    tag = f'<span class="kind">{x["type"]}</span>' + tag
    return (f'<details class="row"><summary>{dot(x)}<b>{e(x["title"])}{tag}</b><span>{status(x)}</span><span>{item_line(lab, T, x) or T(x["description"])}</span></summary>'
            f'<div class="in"><p class="desc">{T(x["description"])}</p>{slot_text(lab, T, x)}{earlier(lab, T, x) if x["type"] == "experiment" else ""}<a href="/{x["id"]}" style="font:.85rem var(--sans)">Open {x["id"]}</a></div></details>')


def question_page(lab, T, q):
    """A question's briefing, in the order the operator asks: the question and a picture of it; where we come from
    and what we know so far; the question as it was asked, slot by slot; what is needed from them; where each step
    stands; what it costs and what it cannot show; the record, folded."""
    s = q["slots"]
    live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
    gone = [x for x in q["items"] if x["state"] == "dropped" or (x["state"] == "replaced" and not lab.replaced_by(x["id"]))]
    body = [f'<h1>{e(q["title"])}</h1>']
    if q.get("asks") and q["asks"] != q["title"]:
        body.append(f'<p class="lead">{T(q["asks"])}</p>')
    kind = ("An estimate: answered with what was found, a number with its range or a description." if L.question_kind(q) == "estimate"
            else "A test: answered yes, no or mixed, against what we expect and what would prove us wrong.")
    body.append(f'<p class="muted" style="font:.84rem var(--sans);margin-top:-.4rem">{kind}</p>')
    if q["state"] == "parked":
        d = lab.parked_by(q["id"])
        body.append(f'<div class="box"><b>Set aside</b> by {named(lab, d["id"])}: nothing under it moves until a decision brings it back. {T(L.flat(d["slots"].get("Decided", "")))}</div>')
    body.append(picture(lab, q))
    before = [lab.nodes[i] for i in q["needs"] if i in lab.nodes]
    body.append(slots(slot("Where we are coming from", "".join(f'<p>{named(lab, n["id"])} {status(n)}</p>' for n in before), "full") if before else "",
                      so_far(lab, T, q)))
    body.append("<h2>The question, as asked</h2>" + slots(
        boxed(T, "Why we ask", q["description"]),
        boxed(T, "How it works", s.get("How we would know", "")),
        boxed(T, "One real case, step by step", s.get("Example", ""), "full example"),
        boxed(T, "We expect", s.get("We expect", ""), ""),
        boxed(T, "Wrong if", s.get("Wrong if", ""), "")))
    talk = [d for d in lab.open_decisions() if any(a == q["id"] or a.startswith(q["id"] + ".") for a in d["about"] + d["holds"])]
    if talk:
        body.append("<h2>What is needed from you</h2>" + "".join(decision_box(lab, T, d) for d in talk))
    body.append("<h2>The steps, and where each stands</h2>" + ("".join(step_row(lab, T, x) for x in live) if live else '<p class="muted">Not started: no experiment is planned yet.</p>'))
    if gone:
        body.append(f'<details class="old"><summary>Dropped ({len(gone)})</summary>' + "".join(f'<p>{named(lab, x["id"])}: {T(str(x.get("dropped") or ""))}</p>' for x in gone) + "</details>")
    tests = [x for x in live if x["type"] == "experiment"]
    body.append(cost_box(lab, T, tests, [x.get("cost") or "" for x in tests if x["state"] != "done"]))
    limits = [(x, x["slots"].get("Limits", "")) for x in tests if L.flat(x["slots"].get("Limits", ""))]
    if limits:
        body.append("<h2>What it cannot show</h2>" + "".join(f'<p class="lbl">{e(x["title"])}</p><div class="limits">{block(T, text)}</div>' for x, text in limits))
    inner = where_to_look(lab, live) + "<h3>Log</h3>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == q["id"] or l["about"].startswith(q["id"] + ".")]))
    body.append(record_html("The record: files and log", inner))
    return frame(lab, q["title"], "".join(body), edges_panel(lab, q), [("/", "Now"), ("/" + q["goal"], lab.nodes[q["goal"]]["title"])])


def slot_text(lab, T, x):
    """An experiment's or a build's card, in short, for the question's page."""
    if x["type"] == "reading":
        return "".join(f'<div><b class="lbl">{name}</b>{block(T, x["slots"][k])}</div>' for k, name in (("Looks at", "Looks at"), ("Seen", "What was seen"), ("Suggests", "What it suggests")) if L.flat(x["slots"].get(k, "")))
    if x["type"] == "build":
        how = f'<div><b class="lbl">How it works</b>{block(T, x["slots"]["How it works"])}</div>' if L.flat(x["slots"].get("How it works", "")) else ""
        return how + f'<p><b class="lbl">Works when</b><br>{T(x["slots"].get("Works when", ""))}</p>'
    out = f'<p><b class="lbl">Compares</b><br>{T(x["slots"].get("Compares", ""))}</p>' + arms_table(lab, T, x) + tick_rows(lab, x)
    return out + "".join(f'<p><b class="lbl">{k}</b><br>{T(x["slots"][k], x["id"])}</p>' for k in ("Found", "Means") if L.flat(x["slots"].get(k, "")))


def where_box(lab, T, x):
    """What an experiment or a build waits on, or what the agent does next on it."""
    if x.get("dropped"):
        return f'<div class="box"><b>Dropped.</b> {T(str(x["dropped"]))}</div>'
    if not x["next"]:
        return ""
    return f'<div class="box"><b>{"Next, for the agent:" if x["mine"] else "Waiting on"}</b> {T(you(x["next"]))}</div>'


def ran(lab, x):
    """When an experiment ran, on what, and what it used: one line near the top of its page."""
    r = x["finished"] or (x["runs"][-1] if x["runs"] else None)
    lock = f'Locked {nice(x["lock"]["locked"])}.' if x["lock"] else "Not locked yet."
    if not r:
        return f'<p class="ran">{lock} Not run yet.</p>'
    used = ", ".join(f'{num(v)} {e(str(lab.resources.get(k, {}).get("unit", k)))}' for k, v in (r.get("used") or {}).items() if L.amount(v))
    tries = sum(k["kind"] != "trial" for k in x["runs"])
    how = {"finished": "Ran" if tries < 2 else f"Finished on its {ordinal(tries)} run,", "failed": "Its last run failed", "running": "Running since"}[r["state"]]
    on = f' on {e(", ".join(x["uses"]))}' if x["uses"] else ""
    return f'<p class="ran">{lock} {how} {nice(r["started"])}{on}' + (f", using {used}" if used else "") + ".</p>"


def results_tables(lab, T, x):
    """The numbers the bars test and the card names, each with its interval; every other number is one click away."""
    rows = x["results"]
    base = lambda name: next((name[: -len(end)] for end in (".low", ".high") if name.endswith(end) and any(r["name"] == name[: -len(end)] for r in rows)), name)
    wanted = {base(l["name"]) for side in x["lines"].values() for l in side if l["test"]}
    wanted |= {base(row["name"]) for k in ("Found", "Means") for _, row in lab.named(x["slots"].get(k, ""), x["id"]) if row and row["experiment"] == x["id"]}

    def tr(r):
        anchors = "".join(f'<span id="r-{e(end["name"])}"></span>' for end in L.ends(rows, r) if end)
        return (f'<tr id="r-{e(r["name"])}"><td>{anchors}<span data-tip="{e(r["name"])} = {e(r["value"])}">{e(r.get("label") or r["name"])}</span></td>'
                f'<td class="n">{e(L.shown_with_interval(rows, r))}</td><td>{e(r.get("versus") or "")}</td></tr>')
    head = '<table class="t"><tr><th>What was measured</th><th>Value, with its interval</th><th>Compared with</th></tr>'
    own = [r for r in rows if not L.is_end(rows, r)]
    main, rest = [r for r in own if r["name"] in wanted], [r for r in own if r["name"] not in wanted]
    if not main:
        main, rest = own, []
    out = "<h2>Results</h2>" + head + "".join(tr(r) for r in main) + "</table>"
    if rest:
        out += f'<details class="more"><summary>{len(rest)} more number{"s" if len(rest) != 1 else ""} this run gave, which no bar tests</summary>' + head + "".join(tr(r) for r in rest) + "</table></details>"
    return out


def review_note(note):
    """A reviewer's note: its first sentence when that is short, the rest one click away. Nothing in it becomes a link."""
    first = L.first_sentence(note, least=4)
    if len(L.flat(note).split()) <= 30:
        return plain(note)
    if len(first.split()) <= 30:
        return f'<details class="note"><summary>{plain(first)}</summary>{plain(L.flat(note)[len(first):])}</details>'
    return f'<details class="note"><summary>What the reviewer read and found</summary>{plain(note)}</details>'


def runs_html(lab, T, x):
    """An experiment's runs, in order: each by its id, when it started, how it ended and what it used, what changed
    since the run before, and its folder to copy."""
    runs = x["trials"] + x["runs"]
    if not runs:
        return ""
    rows, n = [], 0
    for r in runs:
        used = ", ".join(f'{num(v)} {e(str(lab.resources.get(k, {}).get("unit", k)))}' for k, v in (r.get("used") or {}).items() if L.amount(v))
        how = {"running": "Still running.", "finished": "Finished.", "failed": "Stopped with an error" + (f": {e(r['closed'])}" if r.get("closed") else ".")}[r["state"]]
        if r["state"] != "running" and r.get("ended"):
            mins = max(1, round((L.moment(r["ended"]) - L.moment(r["started"])).total_seconds() / 60))
            how += f' <span class="muted">After {mins} minute{"s" if mins != 1 else ""}' + (f", using {used}" if used else "") + ".</span>"
        n += r["kind"] != "trial"
        name = f'<code>{e(r["id"])}</code>' + (' <span class="kind">trial run, before the lock</span>' if r["kind"] == "trial" else "")
        folder = f'<br><span class="lbl">Folder</span> <span data-folio-copy="{e(r["dir"])}/"><code>{e(r["dir"])}/</code></span>'
        since = "the run before" if any(k["kind"] != "trial" and k is not r for k in runs[:runs.index(r)]) else "the lock"
        changed = f'<br><span class="lbl">Changed since {since}</span> {T(r["changed"])}' if r.get("changed") else ""
        if r["missing"] and not r["lost"]:
            how += ' <span class="muted">It is listed in the experiment\'s record of runs, and its folder is not in the store here.</span>'
        rows.append(f'<li><b>{name}</b> <span class="muted">{clock(r["started"])} UTC' + (f' on {e(", ".join(x["uses"]))}' if x["uses"] else "") + f'</span><br>{word(r["state"])} {how}{changed}{folder}</li>')
    note = ('<p class="muted" style="font:.84rem var(--sans)">An experiment is run until one run finishes. Between runs the apparatus may be fixed, and each run says what changed; '
            "what the experiment demands stays as it was locked. The first run that finishes is the only source of its results. "
            "A run's folder is in the lab's store, outside git.</p>") if n > 1 else ""
    return f'<h3>Runs</h3>{note}<ul class="runs">{"".join(rows)}</ul>'


def reviews_html(x):
    if not x["reviews"]:
        return ""
    return ('<h3>Reviews</h3><table class="t"><tr><th>Reviewed</th><th>What</th><th>Verdict</th><th>By</th><th>Note</th></tr>' + "".join(
        f'<tr><td>{nice(r["date"])}</td><td>the {e(r["stage"])}</td><td>{word(r["verdict"])}</td><td>{e(r["by"])}</td><td>{review_note(r["note"])}</td></tr>' for r in x["reviews"]) + "</table>")


def experiment_page(lab, T, x):
    """An experiment: what it is and a picture of the whole work; what we know so far, apart from the plan; the plan as
    it was locked, slot by slot; what it costs and its results; the record, folded."""
    q = lab.nodes[x["question"]]
    s = x["slots"]
    body = [f'<h1>{e(x["title"])}</h1>', f'<p class="lead">{T(x["description"])}</p>', ran(lab, x)]
    by = lab.replaced_by(x["id"])
    if by:
        why = L.flat(by.get("because") or "")
        body.append(f'<div class="box"><b>Replaced by</b> {named(lab, by["id"])}' + (f": {T(why)}" if why else ".") + " Its plan and its results stay as they were.</div>")
    failed = next((r for r in x["reviews"] if r.get("stage") == "results" and r.get("verdict") == "fail"), None)
    if failed:
        body.append(f'<div class="box bad"><b>Void: its results failed their review.</b> No outcome is shown, and no page uses its numbers; what it made may still be used '
                    f'by later steps, listed beside this page. The reviewer: {review_note(failed.get("note", ""))}</div>')
    body.append(where_box(lab, T, x))
    body += [decision_box(lab, T, d) for d in lab.open_decisions() if x["id"] in d["about"] or x["id"] in d["holds"]]
    body.append(picture(lab, x))
    if x["state"] == "done" and x["label"] != "void":  # what was observed comes first, apart from the plan
        body.append(slots(boxed(T, "What it means", s.get("Means", ""), "full key", x["id"]), boxed(T, "What was found", s.get("Found", ""), "full key", x["id"])))
        body.append(f'<p class="outcome-line">{status(x)} {e(decided_by(lab, x))}</p>')
    body.append(slots(so_far(lab, T, x, x["id"])))
    body.append(("<h2>The plan, as locked</h2>" if x["lock"] else "<h2>The plan, not locked yet</h2>") + slots(
        boxed(T, "What it compares", s.get("Compares", ""), extra=arms_table(lab, T, x)),
        boxed(T, "Run on", s.get("Cases", "")),
        boxed(T, "How the answer is read", s.get("Outcomes", ""), extra=tick_rows(lab, x)),
        boxed(T, "What it cannot show", s.get("Limits", ""))))
    if x["state"] != "done":
        body.append(cost_box(lab, T, [x], [x.get("cost") or ""]))
    if x["results"] and x["reviewed"]:
        body.append(results_tables(lab, T, x))
    elif x["results"] and not failed:
        body.append('<h2>Results</h2><p class="muted">Written, and waiting for their review.</p>')
    inner = (runs_html(lab, T, x) + reviews_html(x) + earlier(lab, T, x) + where_to_look(lab, [x])
             + "<h3>Log</h3>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == x["id"]]), False))
    body.append(record_html("The record: runs, reviews, files and log", inner))
    return frame(lab, x["title"], "".join(body), edges_panel(lab, x), [("/", "Now"), ("/" + q["id"], q["title"])])


def build_page(lab, T, b):
    q = lab.nodes[b["question"]]
    body = [f'<h1>{e(b["title"])}</h1>', f'<p class="lead">{T(b["description"])}</p>', where_box(lab, T, b), picture(lab, b)]
    body.append(slots(boxed(T, "How it works", b["slots"].get("How it works", "")), slot("We know it works when", block(T, b["slots"].get("Works when", "")), "full key")))
    if b["commits"]:
        url = code_url(lab)
        commits = " ".join((f'<a href="{url}/commit/{e(str(c))}"><code>{e(str(c))}</code></a>' if url else f"<code>{e(str(c))}</code>") for c in b["commits"])
        tests = ", ".join((f'<a href="{url}/blob/main/{e(str(t))}"><code>{e(str(t))}</code></a>' if url else f"<code>{e(str(t))}</code>") for t in b["tests"])
        body.append(f'<h2>Built in</h2><p style="font:.9rem var(--sans)">{commits}</p><p style="font:.9rem var(--sans)">Checked by {tests}</p>')
    body.append(record_html("The record: log", log_html(lab, T, happened([l for l in lab.lines if l["about"] == b["id"]]), False)))
    return frame(lab, b["title"], "".join(body), edges_panel(lab, b), [("/", "Now"), ("/" + q["id"], q["title"])])


def reading_page(lab, T, r):
    """A reading: a look at what already exists, with no bar set in advance. The page says so before anything else."""
    q = lab.nodes[r["question"]]
    body = [f'<h1>{e(r["title"])}</h1>', f'<p class="lead">{T(r["description"])}</p>',
            '<div class="box explore"><b>This looked at data the lab already had.</b> Nothing here was set as a test in advance, so it can point to what to test next and cannot confirm anything. '
            "A number on this page is a count made while looking, not a reviewed result.</div>", where_box(lab, T, r), picture(lab, r)]
    s = r["slots"]
    body.append(slots(boxed(T, "What it suggests", s.get("Suggests", ""), "full key"), boxed(T, "What was seen", s.get("Seen", "")),
                      slot("What it looks at", block(T, s.get("Looks at", "")), "full")))
    body.append(record_html("The record: log", log_html(lab, T, happened([l for l in lab.lines if l["about"] == r["id"]]), False)))
    return frame(lab, r["title"], "".join(body), edges_panel(lab, r), [("/", "Now"), ("/" + q["id"], q["title"])])


def decision_page(lab, T, d):
    body = f'<h1>{e(d["title"])}</h1>' + decision_box(lab, T, d, link=False, title=False)
    made = [n for n in lab.goals + lab.questions if n.get("from") == d["id"]]
    if made:
        body += "<h2>What came out of it</h2><ul>" + "".join(f'<li>{dot(n)} {named(lab, n["id"])} <span class="muted">({n["type"]})</span><br><span class="muted">{T(n["description"])}</span></li>' for n in made) + "</ul>"
    panel = "<h4>About</h4><ul>" + "".join(f"<li>{dot(lab.nodes[i])} {named(lab, i)}</li>" for i in d["about"] if i in lab.nodes) + "</ul>" if d["about"] else ""
    return frame(lab, d["title"], body, panel, [("/", "Now"), ("/decisions", "Decisions")])


def decisions_page(lab, T):
    """Every decision: what is open first, then what was decided, the latest first."""
    body = ["<h1>Decisions</h1>"]
    for title, group in (("To discuss", lab.open_decisions()), ("Decided", sorted([d for d in lab.decisions if d["state"] == "done"], key=lambda d: str(d["decided"].get("date")), reverse=True))):
        if group:
            body.append(f"<h2>{title}</h2>" + "".join(decision_box(lab, T, d) for d in group))
    if not lab.decisions:
        body.append('<p class="muted">None yet.</p>')
    return frame(lab, "Decisions", "".join(body))


def log_page(lab, T, only=""):
    """The whole log, or only one kind of line."""
    lines = [l for l in lab.lines if not only or l["kind"] == only]
    names = {"decision": "decided with you", "agent": "decided by the agent", "result": "results", "stuck": "stuck", "doing": "what the agent started on"}
    f = ['<div class="filters"><a href="/log">' + pill("all", "info" if not only else "plain") + "</a>"]
    f += [f'<a href="/log/{k}">{pill(names[k], "info" if only == k else "plain")}</a>' for k in L.KINDS if any(l["kind"] == k for l in lab.lines)]
    return frame(lab, "Log", f"<h1>Log</h1>{''.join(f)}</div>{log_html(lab, T, lines)}")


def resources_page(lab, T):
    body = ["<h1>Resources</h1>"]
    if not lab.resources:
        body.append('<p class="muted">None is listed.</p>')
    for name, r in lab.resources.items():
        rows = [("What", e(str(r.get("what", ""))))]
        if r.get("key"):
            rows.append(("Its key", e(str(r["key"]))))
        if lab.metered(name):
            unit = e(str(r.get("unit", "")))
            rows.append(("Granted", f'{num(r["granted"])} {unit}'))
            rows.append(("Used", f'{num(lab.used(name))} {unit}' + (f', and {num(lab.committed(name))} held by runs still going' if lab.committed(name) else "")))
            if isinstance(r.get("per_run"), (int, float)):
                rows.append(("One run may use", f'{num(r["per_run"])} {unit}'))
        if lab.other_use(name):
            rows.append(("Used outside a run", "<br>".join(f'{nice(o["date"]) + ": " if o.get("date") else ""}{num(o["amount"])} {e(str(r.get("unit", "")))}, {e(str(o.get("what", "")))}' for o in lab.other_use(name))))
        if r.get("rules"):
            rows.append(("Rules", "<br>".join(T(str(x)) for x in r["rules"])))
        users = [x for x in lab.experiments if name in x["uses"] and x["state"] not in ("replaced", "dropped")]
        if users:
            rows.append(("Used by", "<br>".join(named(lab, x["id"]) + (f' <span class="muted">(its own cap: {num(x["override"][name])})</span>' if name in x["override"] else "") for x in users)))
        body.append(f'<h2 id="{e(name)}">{e(name)}</h2><dl class="kv">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>")
    return frame(lab, "Resources", "".join(body))


def avoid_note(g):
    """The words not to use for a term, in small type; nothing when there are none."""
    return f' <span class="avoid">Avoid: {e(", ".join(g["avoid"]))}</span>' if g["avoid"] else ""


def see_link(lab, page):
    """A link to the page that explains a term, a page of the lab's own library or of a library the charter names."""
    page = str(page)
    if ":" not in page:
        return f'<a href="/docs/{e(page)}/">{e(pages(lab).get(page, page))}</a>'
    url = outside(lab, page)
    return f'<a href="{e(url)}">{e(page_title(lab, page))}</a>' if url else e(page)


def glossary_page(lab, T):
    """Every term, by group, every group open: each with its definition, an example, where it is in the code, the page
    that explains it, its other names and the words to avoid. A link to a term lands on its entry."""
    url = code_url(lab)
    groups = {}
    for g in lab.glossary:
        groups.setdefault(g["group"] or "Terms", []).append(g)
    body = ["<h1>Glossary</h1>"]
    if not lab.glossary:
        body.append('<p class="muted">No term is defined yet.</p>')
        return frame(lab, "Glossary", "".join(body))
    body.append('<input class="gfilter" type="search" placeholder="Find a term" aria-label="Find a term" oninput="'
                "var q=this.value.toLowerCase();document.querySelectorAll('.ggroup').forEach(function(g){var n=0;g.querySelectorAll('dt').forEach(function(t){"
                "var d=t.nextElementSibling,hit=!q||(t.textContent+' '+d.textContent).toLowerCase().indexOf(q)>=0;t.hidden=d.hidden=!hit;if(hit)n++;});g.hidden=!n;});"
                '">')
    for name, terms in groups.items():
        rows = []
        for g in terms:
            example = f'<span class="gex">{T(g["example"])}</span>' if g.get("example") else ""
            code = (f'<a href="{url}/blob/main/src/{e(g["code"].split(":")[0].replace(".", "/"))}.py"><code>{e(g["code"])}</code></a>' if url else f'<code>{e(g["code"])}</code>') if g["code"] else ""
            more = " · ".join(x for x in (code, f"See: {see_link(lab, g['see'])}" if g["see"] else "") if x)
            also = f' <span class="avoid">Also: {e(", ".join(g["also"]))}</span>' if g.get("also") else ""
            rows.append(f'<dt id="{e(anchor(g["term"]))}">{e(g["term"])}</dt><dd>{e(g["definition"])}{example}'
                        + (f'<span class="gsee">{more}</span>' if more else "") + f"{also}{avoid_note(g)}</dd>")
        body.append(f'<details class="ggroup" open><summary>{e(name)}<span>{len(terms)} terms</span></summary><dl class="gloss">{"".join(rows)}</dl></details>')
    body.append("<script>(function(){var h=decodeURIComponent(location.hash.slice(1));var t=h&&document.getElementById(h);if(t){t.scrollIntoView();}})();</script>")
    return frame(lab, "Glossary", "".join(body))


# ---------------------------------------------------------------- the provider folio loads

def _links(text):
    """Page functions link by short paths; the site serves them under this provider's prefix."""
    def fix(m):
        url = m.group(2)
        if url.startswith(("/content/", "/lab/", "/shell/", "/.folio", "//", "#")) or not url.startswith("/"):
            return m.group(0)
        if url.startswith("/docs/"):
            return f'{m.group(1)}"/content/{url[6:]}"'
        path, _, anchor = url.partition("#")
        return f'{m.group(1)}"/lab{path.rstrip("/")}/{"#" + anchor if anchor else ""}"'
    return re.sub(r'(<a\s[^<>]*?href=)"([^"]*)"', fix, text)  # the href of a tag, never the same letters in a card's prose


class Provider:
    prefix, title, home = "lab", "Lab", True

    def __init__(self, library_root):
        self.root = L.find_root(str(library_root))
        self._lab, self._at = None, None

    def stamp(self):
        """Changes when a card, a decision, the log, the resources or any run's record changes."""
        h = hashlib.sha1()
        files = [p for pat in ("goals/**/*", "decisions/*", "runs/*/run.json", ".lab/running/*/run.json", "*.md", "*.toml")
                 for p in glob.glob(os.path.join(self.root, pat), recursive=True)]
        for p in sorted(set(files)):
            try:
                st = os.stat(p)
            except OSError:
                continue
            if os.path.isfile(p):
                h.update(f"{p}\0{st.st_mtime_ns}\0{st.st_size}\n".encode())
        return h.hexdigest()

    def lab(self):
        stamp = self.stamp()
        if self._lab is None or stamp != self._at:
            self._lab, self._at = L.Lab(self.root), stamp
        return self._lab

    def get(self, inner):
        from folio.views import View
        lab = self.lab()
        T = Text(lab, inner)
        inner = lab.folded.get(inner, inner)  # an old link to a folded draft opens the decision that took it in
        parts = inner.split("/")
        genre, status, description, page, path = "", "", "", None, ""
        if inner == "":
            page = home(lab, T)
        elif parts[0] == "log" and (len(parts) == 1 or (len(parts) == 2 and parts[1] in L.KINDS)):
            page, path = log_page(lab, T, parts[1] if len(parts) == 2 else ""), "log.md"
        elif inner == "decisions":
            page = decisions_page(lab, T)
        elif inner == "missions":
            page = missions_page(lab, T)
        elif inner == "resources":
            page, path = resources_page(lab, T), "resources.toml"
        elif inner == "glossary":
            page, path = glossary_page(lab, T), "GLOSSARY.md"
        elif inner in lab.nodes:
            n = lab.nodes[inner]
            page = {"goal": goal_page, "question": question_page, "experiment": experiment_page, "build": build_page, "reading": reading_page, "decision": decision_page}[n["type"]](lab, T, n)
            genre, status, path = n["type"], label(n), n["path"]
            description = "" if n["type"] in ("goal", "question") or n["type"] in L.STEPS else L.bare(n.get("description") or "")  # drawn as the page's lead, with its links
        if page is None:
            return None
        body = re.sub(r"<h1>.*?</h1>", "", page["body"], count=1, flags=re.S)
        panels = [(title, _links(f'<div class="lv panelbox">{block}</div>')) for title, block in re.findall(r"<h4>(.*?)</h4>(.*?)(?=<h4>|$)", page["panel"], flags=re.S)]
        return View(title=page["title"], main=_links(f'<div class="lv">{body}</div>'), description=L.flat(description),
                    genre=genre, status=status, head=f"<style>{CSS}{header_css()}</style>", panels=panels, path=path)

    def rail(self):
        """The lab as a tree: each goal, its questions, each question's steps. Each row has the mark of its kind, its short
        id, its title and its state as a sign; a closed group counts what is under it by state. What was replaced or
        dropped folds into one line at the end of its question, and what was set aside at the end of its goal."""
        lab = self.lab()

        def row(n, short):
            return {"title": n["title"], "url": f"/lab/{n['id']}/", "id": short, "kind": n["type"], "status": label(n), **({"mark": MARK[n["type"]]} if n["type"] in L.STEPS else {}),
                    "tone": tone(n), "sign": sign(n), "pulse": key(n) == "running", "gone": n["state"] in ("replaced", "dropped")}

        def summary(steps):
            out = {}  # done and confirmed share a sign: one count
            for k, n in counts(steps):
                look = LOOK.get(k, ("plain", ""))
                was = out.get(look, (0, []))
                out[look] = (was[0] + n, was[1] + [f"{n} {MEANS.get(k, k)}"])
            return [{"sign": look[1], "tone": look[0], "count": n, "title": ", ".join(words)} for look, (n, words) in out.items()]

        talk = len(lab.open_decisions())
        out = [{"title": "Now", "url": "/lab/"}, {"title": "Decisions", "url": "/lab/decisions/", **({"status": f"{talk} to discuss", "tone": "warn"} if talk else {})}]
        current = sum(m["state"] == "current" for m in lab.missions)
        out += [{"title": "Missions", "url": "/lab/missions/", **({"status": f"{current} current", "tone": "info"} if current else {})}] if lab.missions else []
        out += [{"title": t, "url": f"/lab/{p}"} for t, p in (("Log", "log/"), ("Resources", "resources/"), ("Glossary", "glossary/"))]
        for g in lab.live(lab.goals):
            questions, under = [], []
            for q in lab.live(g["questions"]):
                live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
                gone = [x for x in q["items"] if x["state"] in ("replaced", "dropped")]
                under += live
                items = [row(x, x["id"].split(".")[-1]) for x in live]
                if gone:
                    items.append({"title": f"replaced and dropped ({len(gone)})", "key": f"{q['id']}:gone", "fold": True, "items": [row(x, x["id"].split(".")[-1]) for x in gone]})
                questions.append({**row(q, q["id"].split(".")[-1]), **({"items": items, "summary": summary(live)} if items else {})})
            aside = [q for q in g["questions"] if q["state"] in ("parked", "dropped")]
            if aside:
                questions.append({"title": f"set aside ({len(aside)})", "key": f"{g['id']}:aside", "fold": True, "items": [row(q, q["id"].split(".")[-1]) for q in aside]})
            out.append({**row(g, g["id"]), "items": questions, "summary": summary(under)})
        return out

    def search(self):
        lab = self.lab()
        out = []
        for n in lab.goals + lab.questions + lab.items + lab.decisions:
            slots = n.get("slots") or {}
            home = n["id"] if n["type"] == "experiment" else None
            out.append({"id": n["id"], "genre": n["type"], "part": None, "path": f"lab/{n['id']}", "url": f"/lab/{n['id']}/", "title": n["title"],
                        "description": L.bare(n.get("description") or lab.fill(L.flat(slots.get("Decided") or slots.get("Seen") or ""), home)), "tags": [], "status": label(n),
                        "text": L.bare(lab.fill(" ".join(L.flat(v) for v in slots.values()), home))})
        for g in lab.glossary:
            anchor = g["term"].lower().replace(" ", "-")
            out.append({"id": "", "genre": "term", "part": None, "path": f"lab/glossary#{anchor}", "url": f"/lab/glossary/#{anchor}", "title": g["term"],
                        "description": g["definition"], "tags": [], "status": "", "text": g["definition"]})
        return out

    def paths(self):
        lab = self.lab()
        return ["", "decisions", "log", "resources", "glossary"] + [f"log/{k}" for k in L.KINDS] + list(lab.nodes)

    def backlinks(self):
        lab = self.lab()
        out = {}
        for n in lab.goals + lab.questions + lab.items:
            for page in n.get("see") or []:
                out.setdefault(f"content/{str(page).split('#')[0]}/index.html", []).append({"title": f"{n['id']} {n['title']}", "url": f"/lab/{n['id']}/", "status": label(n)})
        return out


def provider(library_root):
    return Provider(library_root)

