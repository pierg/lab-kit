"""The operator's site for a lab: every page drawn from the record when it is asked for, inside folio's shell.

folio names this module under `views:` in the library's charter. It never stores a page: the cards, the
results and the runs are read at each request, so the site cannot fall behind the record. It changes nothing.
"""
from __future__ import annotations

import datetime, glob, hashlib, html, os, re

from . import record as L

GENERIC = {"model", "field", "source", "group", "stop", "case", "score", "port", "step", "pass", "run", "result"}
e = html.escape
TONES = {"active": "info", "reached": "ok", "under discussion": "warn", "open": "info", "yes": "ok", "no": "warn", "decided": "ok",
         "confirmed": "ok", "refuted": "bad", "unclear": "warn", "running": "info", "waiting": "warn", "in progress": "info", "built": "ok",
         "review failed": "bad", "finished": "ok", "failed": "bad", "pass": "ok", "fail": "bad", "done": "ok", "parked": "plain"}


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


def label(n):
    """A node's state as the operator reads it: a finished experiment shows its outcome."""
    if n["type"] == "experiment" and n["state"] == "done":
        return n["outcome"]
    if n["type"] == "question" and n["state"] in ("yes", "no"):
        return f"answered {n['state']}"
    if n["type"] == "question" and n["state"] == "open" and not n["items"]:
        return "not started"
    return n["state"]


def tone(n):
    if n.get("type") == "decision":
        return "ok" if n["state"] == "decided" else "warn"
    if n.get("type") == "question" and n["state"] == "open" and not n["items"]:
        return "plain"
    return TONES.get(n["outcome"] if n.get("type") == "experiment" and n["state"] == "done" else n["state"], "plain")


def you(text):
    """What the record says of the operator, said to the operator."""
    return str(text).replace("the operator's", "your").replace("the operator", "you")


def pill(text, t="plain"):
    return f'<span class="pill t-{t}">{e(str(text))}</span>'


def dot(n):
    return f'<i class="dot t-{tone(n)}"></i>'


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
    if not n:
        return e(ident)
    return f'<a class="ref" href="/{ident}" data-tip="{e(n["title"])} ({e(label(n))})">{e(text or ident)}</a>'


def named(lab, ident):
    """An id with its title beside it, which is how every page says which node it means."""
    n = lab.nodes.get(ident)
    return f'{ref(lab, ident)} <a href="/{ident}">{e(n["title"])}</a>' if n else e(ident)


class Text:
    """Card prose to HTML: ids become links, a named result becomes its value, glossary terms get their definition."""

    def __init__(self, lab):
        self.lab = lab
        terms = [g for g in lab.glossary if g["term"].lower() not in GENERIC]
        self.defs = {g["term"].lower(): g for g in terms}
        alt = "|".join(re.escape(g["term"]) for g in sorted(terms, key=lambda g: -len(g["term"]))) or r"(?!x)x"
        self.seen = set()
        self.rx = re.compile(
            r"(?P<link>\[[^\]\n]+\]\([^)\s]+\))|(?P<code>`[^`]+`)|(?P<strong>\*\*[^*\n]+\*\*)|(?P<em>\*[^*\n]+\*)|(?P<named>\{(?:G\d+\.Q\d+\.\d+:)?[A-Za-z][\w.-]*?\})|(?P<id>\b(?:G\d+(?:\.Q\d+(?:\.\d+)?)?|D\d+)\b)"
            r"|(?P<term>(?i:\b(?:" + alt + r")s?\b))")

    def __call__(self, text, home=None):
        lab, seen = self.lab, self.seen

        def one(m):
            if m.group("code"):
                return f"<code>{m.group('code')[1:-1]}</code>"
            if m.group("link"):
                text, target = m.group("link")[1:-1].split("](", 1)
                url = outside(lab, target)
                return f'<a href="{e(url)}">{text}</a>' if url else text
            if m.group("strong"):
                return f"<b>{m.group('strong')[2:-2]}</b>"
            if m.group("em"):
                return f"<em>{m.group('em')[1:-1]}</em>"
            if m.group("named"):
                (written, row), = lab.named(m.group("named"), home)
                if not row or not row["usable"]:
                    return f'<span class="num off" data-tip="Not a reviewed result">{e(written)}</span>'
                tip = f"{row.get('label') or row['name']}. Compared with: {row.get('versus', '')}"
                return f'<a class="num" href="/{row["experiment"]}#r-{e(row["name"])}" data-tip="{e(tip)}">{e(L.shown(row))}</a>'
            if m.group("id"):
                return ref(lab, m.group("id")) if m.group("id") in lab.nodes else m.group("id")
            word = m.group("term")
            key = word.lower() if word.lower() in self.defs else word.lower()[:-1]
            if key in seen or key not in self.defs:
                return word
            seen.add(key)
            return f'<span class="term" data-tip="{e(self.defs[key]["definition"])}">{word}</span>'

        return self.rx.sub(one, e(L.flat(text), quote=False))


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
.lv .term{border-bottom:1px dotted var(--ink-3);cursor:help}
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
.lv svg.graph text{font-family:var(--sans)}
.lv svg.graph a{text-decoration:none}
.lv svg.graph a:hover rect{stroke:var(--accent);stroke-width:2}
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


def own(text, default):
    """A slot's heading: the card's own first line when it is a heading (## ...), else the template's name."""
    t = str(text or "").strip()
    m = re.match(r"^#{2,3} (.+)\n?", t)
    return (m.group(1).strip(), t[m.end():]) if m else (default, t)


def section(T, text, default, home=None, extra=""):
    if not L.flat(text) and not extra:
        return ""
    head, body = own(text, default)
    return f'<h2>{T(head, home)}</h2>{block(T, body, home)}{extra}'


def picture(lab, n):
    """The node's picture: picture.svg beside its card, drawn inline at the top of its page."""
    p = os.path.join(lab.root, n["dir"], "picture.svg")
    if not os.path.isfile(p):
        return ""
    svg = L.read(p)
    svg = re.sub(r"<\?xml[^>]*>", "", svg)
    return f'<figure class="pic">{svg}</figure>'


def decided_notes(lab, T, n):
    """The decisions about a node that are settled and change how it is read: one line each, at the top."""
    out = []
    for d in lab.decisions:
        if d["state"] == "decided" and n["id"] in d["about"] and L.flat(d["slots"].get("Note", "")):
            out.append(f'<p><b>Decided in <a href="/{d["id"]}">{e(d["title"])} ({d["id"]})</a>:</b></p>{block(T, d["slots"]["Note"])}')
    return "".join(out)


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
        kind_tone = {"result": "ok", "stuck": "bad", "decision": "info", "agent": "plain", "doing": "plain"}.get(l["kind"], "plain")
        who = {"decision": "decided", "agent": "agent", "doing": "started"}.get(l["kind"], l["kind"])
        so = f'<span class="so">{T(l["so"])}</span>' if l["so"] else ""
        about = ref(lab, l["about"]) if with_about else ""
        out.append(f'<li><span class="d">{clock(l["at"])}</span><span>{pill(who, kind_tone)}</span><span>{about}</span><span>{T(l["what"])}{so}</span></li>')
    return "".join(out) + "</ul>"


def happened(lines):
    """A page's log: what happened, without the lines that only said what the agent was starting on."""
    return [l for l in lines if l["kind"] != "doing"]


def decision_box(lab, T, d, link=True, title=True):
    """One decision as the operator reads it: what there is to discuss, or what was decided and why."""
    done = d["state"] == "decided"
    about = ", ".join(named(lab, i) if i in lab.nodes else f'the resource <a href="/resources#{e(i)}">{e(i)}</a>' for i in d["about"] if i in lab.nodes or i in lab.resources)
    head = f'{ref(lab, d["id"]) if link else e(d["id"])} · raised {nice(d["date"])}' + (f" · about {about}" if about else "")
    rows = []
    if done:
        rows.append((f'Decided {nice(d["decided"].get("date"))}', block(T, d["slots"].get("Decided", ""))))
    rows += [(verb if done else f"Would {verb.lower()}", "<br>".join(named(lab, i) if i in lab.nodes else e(i) for i in d[key])) for key, verb in (("parks", "Parks"), ("unparks", "Brings back")) if d[key]]
    if d["order"]:
        rows.append(("Orders the work" if done else "Would order the work", "<ol>" + "".join(f"<li>{named(lab, i) if i in lab.nodes else e(i)}</li>" for i in d["order"]) + "</ol>"))
    rows += [(k, block(T, d["slots"][k])) for k in ("Seen", "Options", "Recommendation") if L.flat(d["slots"].get(k, ""))]
    if not done:
        held = lab.held_by(d)
        rows.append(("Held until it is settled", "<br>".join(named(lab, h["id"]) for h in held) if held else "Nothing: the work goes on."))
    return (f'<div class="box decision{" closed" if done else ""}"><div class="decisionhead">{head}</div>'
            + (f'<p class="decisionq">{T(d["title"])}</p>' if title else "")
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
        out.append("<h4>Needed by</h4><ul>" + "".join(f"<li>{dot(x)} {named(lab, x['id'])}</li>" for x in by) + "</ul>")
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
    done = sum(x["state"] in ("done", "built") for x in live)
    asks = f'<p class="asks">{e(q["asks"])}</p>' if q["asks"] != q["title"] else ""
    body = asks + (block(T, q["slots"].get("So far", "")) if live else f'<p class="muted">{T(q["description"])}</p>')
    count = f"{done} of {len(live)} steps done" if live else ""
    return (f'<div class="qrow"><div><h3>{dot(q)} <a href="/{q["id"]}">{e(q["title"])}</a></h3>{body}</div>'
            f'<div class="side">{pill(label(q), tone(q))}<br>{count}</div></div>')


def right_now(lab, T):
    """The top of the front page: what is going on at this moment, as far as the record says, and how fresh the record is."""
    rows = []
    for x in lab.experiments:
        for r in x["runs"] + x["trials"]:
            if r["state"] == "running" and not r["orphan"]:
                rows.append(f'<p class="what">{pill("running", "info")} {named(lab, x["id"])}, since {clock(r["started"])}' + (f' on {e(", ".join(x["uses"]))}' if x["uses"] else "") + ".</p>")
    d = lab.doing()
    if d:
        rows.append(f'<p class="what">{pill("the agent is on", "info")} {named(lab, d["about"])}</p><p>{T(d["what"])} <span class="muted">Why now:</span> {T(d["so"])} <span class="muted">Since {clock(d["at"])}.</span></p>')
    if not rows:
        mine = lab.yours()
        if mine:
            x = mine[0]
            rows.append(f'<p class="what">{pill("nobody is on it", "warn")} Nothing is running, and no agent has said it is working.</p>'
                        f'<p>The next step is the agent\'s: {named(lab, x["id"])}: {T(you(x["next"]))}.</p>')
        else:
            waits = [x for x in lab.pursued() if x["state"] == "waiting" or (x["state"] == "planned" and x["next"])]
            rows.append(f'<p class="what">{pill("idle", "plain")} Nothing is running and nothing is the agent\'s to move.</p>'
                        + (f'<p>{named(lab, waits[0]["id"])} waits on {T(you(waits[0]["next"]))}.</p>' if waits else ""))
    last = lab.last_record()
    stamp = f'<p class="stamp">Last recorded activity: {clock(last.isoformat())} UTC, {ago(last)}.</p>' if last else ""
    return f'<div class="nowbox{"" if d or len(rows) > 1 or "running" in rows[0][:60] else " quiet"}">{"".join(rows)}{stamp}</div>'


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
    out = [right_now(lab, T)]
    talk = [decision_box(lab, T, d) for d in lab.open_decisions()]
    out.append("<h2>To discuss with you</h2>" + ("".join(talk) or '<p class="muted">Nothing.</p>'))
    busy = lab.doing()["about"] if lab.doing() else None
    nxt = [x for x in lab.yours() if x["id"] != busy]
    held = [x for x in lab.pursued() if x["state"] == "waiting" or (x["state"] == "planned" and not x["mine"] and x["next"])]
    if nxt or held:
        by = lab.ordered_by()
        out.append('<h2>Next</h2>' + (f'<p class="muted" style="font:.84rem var(--sans)">In the order of the work set by {named(lab, by["id"])}.</p>' if by else "") + '<table class="t"><tr><th>What</th><th>Who moves it</th><th>What happens next</th></tr>' + "".join(
            f'<tr><td>{named(lab, x["id"])}</td><td>{"the agent" if x["mine"] else "waits"}</td><td>{("" if x["mine"] else "on ") + T(you(x["next"]))}</td></tr>' for x in nxt + held) + "</table>")
    out.append("<h2>Where each question stands</h2>")
    for g in lab.live(lab.goals):
        out.append(f'<div class="goalhead">{dot(g)}<a href="/{g["id"]}">{e(g["title"])}</a></div><p class="goalwhy">{T(g["description"])}</p>'
                   + "".join(qcard(lab, T, q) for q in lab.live(g["questions"])))
    out.append(set_aside_html(lab, T))
    latest = happened(lab.lines)[-5:]
    out.append('<h2>Latest</h2>' + log_html(lab, T, latest) + '<p style="font:.85rem var(--sans)"><a href="/log">The whole log</a></p>')
    if lab.resources:
        out.append('<h2>Resources</h2>' + resources_table(lab))
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
            f'<p>{named(lab, g["id"])}: {e(label(g))}{". " + T(str(g["dropped"])) if g.get("dropped") else ""}</p>' for g in aside["goals"]) + "</details>")
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
    body = [f'<h1>{e(g["title"])}</h1>']
    if L.flat(g["slots"].get("Claim", "")):
        body.append('<div class="slots">' + slot("What we would claim, and against what", T(g["slots"]["Claim"]), "full key") + "</div>")
    pairs = lambda name: [tuple(p.strip() for p in (i.split(": ", 1) + [""])[:2]) for i in L.items(g["slots"].get(name, ""))]
    extra = [(title, block(T, g["slots"][k]), cls) for k, title, cls in (("Example", "The idea in one case", "full example"), ("Approach", "The design, and how this lab approximates it", "full")) if L.flat(g["slots"].get(k, ""))]
    if extra:
        body.append('<div class="slots">' + "".join(slot(*x) for x in extra) + "</div>")
    if pairs("Roles"):
        body.append('<h2>Who plays what</h2><table class="t roles"><tr><th>Role</th><th>Played by, and what it does</th></tr>' + "".join(f"<tr><td>{T(a)}</td><td>{T(b)}</td></tr>" for a, b in pairs("Roles")) + "</table>")
    words = lab.vocabulary(g)
    if words:  # the names are the card's; what each means is the glossary's, whatever the card says after a colon
        rows = "".join(f'<tr><td>{e(w["entry"]["term"] if w["entry"] else w["name"])}</td><td>' + (e(w["entry"]["definition"]) + avoid_note(w["entry"]) if w["entry"] else '<span class="muted">not in the glossary</span>') + "</td></tr>" for w in words)
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
    return (f'<details class="row"><summary>{dot(x)}<b>{e(x["title"])}{tag}</b><span>{pill(label(x), tone(x))}</span><span>{item_line(lab, T, x) or T(x["description"])}</span></summary>'
            f'<div class="in"><p class="desc">{T(x["description"])}</p>{slot_text(lab, T, x)}{earlier(lab, T, x) if x["type"] == "experiment" else ""}<a href="/{x["id"]}" style="font:.85rem var(--sans)">Open {x["id"]}</a></div></details>')


def question_page(lab, T, q):
    """A question's briefing, in the order the operator asks: where we come from, what we ask and why, how it works,
    where each step stands, what it costs, what it cannot show, what is needed from them, where to look."""
    s = q["slots"]
    live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
    gone = [x for x in q["items"] if x["state"] == "dropped" or (x["state"] == "replaced" and not lab.replaced_by(x["id"]))]
    body = [f'<h1>{e(q["title"])}</h1>']
    if q["state"] == "parked":
        d = lab.parked_by(q["id"])
        body.append(f'<div class="box"><b>Parked</b> by {named(lab, d["id"])}: nothing under it moves until a decision brings it back. {T(L.flat(d["slots"].get("Decided", "")))}</div>')
    before = [lab.nodes[i] for i in q["needs"] if i in lab.nodes]
    if before:
        body.append('<div class="slots">' + slot("Where we are coming from", "".join(f'<p>{named(lab, n["id"])} ({e(label(n))}).</p>{block(T, n["slots"].get("So far", ""))}' for n in before), "full") + "</div>")
    body.append('<div class="slots">' + slot("What we know so far", block(T, s.get("So far", "")), "full key")
                + slot("Why we ask", block(T, q["description"]), "full")
                + (slot("How it works", block(T, s["How we would know"]), "full") if L.flat(s.get("How we would know", "")) else "")
                + (slot("One real case, step by step", block(T, s["Example"]), "full example") if L.flat(s.get("Example", "")) else "")
                + "".join(slot(k, block(T, s.get(k, ""))) for k in ("We expect", "Wrong if")) + "</div>")
    talk = [d for d in lab.open_decisions() if any(a == q["id"] or a.startswith(q["id"] + ".") for a in d["about"] + d["holds"])]
    if talk:
        body.append("<h2>What is needed from you</h2>" + "".join(decision_box(lab, T, d) for d in talk))
    body.append("<h2>The steps, and where each stands</h2>")
    for x in live:
        body.append(step_row(lab, T, x))
    if not q["items"]:
        body.append('<p class="muted">Not started: no experiment is planned yet.</p>')
    if gone:
        body.append(f'<details class="old"><summary>Dropped ({len(gone)})</summary>' + "".join(f'<p>{named(lab, x["id"])}: {T(str(x.get("dropped") or ""))}</p>' for x in gone) + "</details>")
    tests = [x for x in live if x["type"] == "experiment"]
    body.append(cost_box(lab, T, tests, [x.get("cost") or "" for x in tests if x["state"] != "done"]))
    limits = [(x, x["slots"].get("Limits", "")) for x in tests if L.flat(x["slots"].get("Limits", ""))]
    if limits:
        body.append("<h2>What it cannot show</h2>" + "".join(f'<p class="lbl">{e(x["title"])}</p><div class="limits">{block(T, text)}</div>' for x, text in limits))
    body.append(where_to_look(lab, live))
    body.append("<h2>Log</h2>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == q["id"] or l["about"].startswith(q["id"] + ".")])))
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


def experiment_page(lab, T, x):
    q = lab.nodes[x["question"]]
    body = [f'<h1>{e(x["title"])}</h1>', f'<p class="lead">{T(x["description"])}</p>', ran(lab, x)]
    by = lab.replaced_by(x["id"])
    if by:
        why = L.flat(by.get("because") or "")
        body.append(f'<div class="box"><b>Replaced by</b> {named(lab, by["id"])}' + (f": {T(why)}" if why else ".") + " Its plan and its results stay as they were.</div>")
    failed = next((r for r in x["reviews"] if r.get("stage") == "results" and r.get("verdict") == "fail"), None)
    if failed:
        body.append(f'<div class="box bad"><b>Its results failed their review.</b> {plain(failed.get("note", ""))} No outcome is shown, and no page uses its numbers.</div>')
    body.append(where_box(lab, T, x))
    body += [decision_box(lab, T, d) for d in lab.open_decisions() if x["id"] in d["about"] or x["id"] in d["holds"]]
    if x["state"] == "done":
        body.append('<div class="slots">' + slot("What it means", block(T, x["slots"].get("Means", ""), x["id"]), "full key") + slot("What was found", block(T, x["slots"].get("Found", ""), x["id"]), "full") + "</div>")
        body.append(f'<p class="outcome-line">{pill(x["outcome"], tone(x))} {e(decided_by(lab, x))}</p>')
    body.append('<h2>What it compares</h2><div class="slots">' + slot("In one sentence", block(T, x["slots"].get("Compares", "")), "full") + "</div>" + arms_table(lab, T, x)
                + ('<div class="slots">' + slot("Run on", block(T, x["slots"]["Cases"]), "full") + "</div>" if L.flat(x["slots"].get("Cases", "")) else "")
                + "<h2>How the answer is read</h2>" + '<p class="muted" style="font:.86rem var(--sans)">Set before the run, and locked with it.</p>' + tick_rows(lab, x)
                + ('<div class="slots">' + slot("What each outcome would mean", block(T, x["slots"]["Outcomes"]), "full") + "</div>" if L.flat(x["slots"].get("Outcomes", "")) else "")
                + ('<div class="slots">' + slot("What it cannot show", block(T, x["slots"]["Limits"]), "full") + "</div>" if L.flat(x["slots"].get("Limits", "")) else ""))
    if x["state"] != "done":
        body.append(cost_box(lab, T, [x], [x.get("cost") or ""]))
    if x["results"] and x["reviewed"]:
        body.append(results_tables(lab, T, x))
    elif x["results"] and not failed:
        body.append('<h2>Results</h2><p class="muted">Written, and waiting for their review.</p>')
    runs = x["trials"] + x["runs"]
    if runs or x["reviews"]:
        body.append("<h2>How it was run and checked</h2>")
    if runs:
        rows, n = [], 0
        for r in runs:
            used = ", ".join(f'{num(v)} {e(str(lab.resources.get(k, {}).get("unit", k)))}' for k, v in (r.get("used") or {}).items() if L.amount(v))
            how = {"running": "Still running.", "finished": "Finished.", "failed": "Stopped with an error" + (f": {e(r['closed'])}" if r.get("closed") else ".")}[r["state"]]
            if r["state"] != "running" and r.get("ended"):
                mins = max(1, round((L.moment(r["ended"]) - L.moment(r["started"])).total_seconds() / 60))
                how += f' <span class="muted">After {mins} minute{"s" if mins != 1 else ""}' + (f", using {used}" if used else "") + ".</span>"
            n += r["kind"] != "trial"
            label_ = f'<code>{e(r["id"])}</code>' + (' <span class="kind">trial run, before the lock</span>' if r["kind"] == "trial" else "")
            folder = f'<br><span class="lbl">Folder</span> <span data-folio-copy="{e(r["dir"])}/"><code>{e(r["dir"])}/</code></span>'
            since = "the run before" if any(k["kind"] != "trial" and k is not r for k in runs[:runs.index(r)]) else "the lock"
            changed = f'<br><span class="lbl">Changed since {since}</span> {T(r["changed"])}' if r.get("changed") else ""
            if r["missing"] and not r["lost"]:
                how += ' <span class="muted">It is listed in the experiment\'s record of runs, and its folder is not in the store here.</span>'
            rows.append(f'<li><b>{label_}</b> <span class="muted">{clock(r["started"])} UTC' + (f' on {e(", ".join(x["uses"]))}' if x["uses"] else "") + f'</span><br>{pill(r["state"], TONES.get(r["state"], "plain"))} {how}{changed}{folder}</li>')
        note = ('<p class="muted" style="font:.84rem var(--sans)">An experiment is run until one run finishes. Between runs the apparatus may be fixed, and each run says what changed; '
                "what the experiment demands stays as it was locked. The first run that finishes is the only source of its results. "
                "A run's folder is in the lab's store, outside git.</p>") if n > 1 else ""
        body.append(f'{note}<ul class="runs">{"".join(rows)}</ul>')
    if x["reviews"]:
        body.append('<table class="t"><tr><th>Reviewed</th><th>What</th><th>Verdict</th><th>By</th><th>Note</th></tr>' + "".join(
            f'<tr><td>{nice(r["date"])}</td><td>the {e(r["stage"])}</td><td>{pill(r["verdict"], TONES.get(r["verdict"], "plain"))}</td><td>{e(r["by"])}</td><td>{review_note(r["note"])}</td></tr>' for r in x["reviews"]) + "</table>")
    body.append(earlier(lab, T, x))
    body.append(where_to_look(lab, [x]))
    body.append("<h2>Log</h2>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == x["id"]]), False))
    return frame(lab, x["title"], "".join(body), edges_panel(lab, x), [("/", "Now"), ("/" + q["id"], q["title"])])


def build_page(lab, T, b):
    q = lab.nodes[b["question"]]
    body = [f'<h1>{e(b["title"])}</h1>', f'<p class="lead">{T(b["description"])}</p>', where_box(lab, T, b)]
    body.append('<div class="slots">' + (slot("How it works", block(T, b["slots"]["How it works"]), "full") if L.flat(b["slots"].get("How it works", "")) else "")
                + slot("We know it works when", block(T, b["slots"].get("Works when", "")), "full key") + "</div>")
    if b["commits"]:
        url = code_url(lab)
        commits = " ".join((f'<a href="{url}/commit/{e(str(c))}"><code>{e(str(c))}</code></a>' if url else f"<code>{e(str(c))}</code>") for c in b["commits"])
        tests = ", ".join((f'<a href="{url}/blob/main/{e(str(t))}"><code>{e(str(t))}</code></a>' if url else f"<code>{e(str(t))}</code>") for t in b["tests"])
        body.append(f'<h2>Built in</h2><p style="font:.9rem var(--sans)">{commits}</p><p style="font:.9rem var(--sans)">Checked by {tests}</p>')
    body.append("<h2>Log</h2>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == b["id"]]), False))
    return frame(lab, b["title"], "".join(body), edges_panel(lab, b), [("/", "Now"), ("/" + q["id"], q["title"])])


def reading_page(lab, T, r):
    """A reading: a look at what already exists, with no bar set in advance. The page says so before anything else."""
    q = lab.nodes[r["question"]]
    body = [f'<h1>{e(r["title"])}</h1>', f'<p class="lead">{T(r["description"])}</p>',
            '<div class="box explore"><b>This looked at data the lab already had.</b> Nothing here was set as a test in advance, so it can point to what to test next and cannot confirm anything. '
            "A number on this page is a count made while looking, not a reviewed result.</div>", where_box(lab, T, r)]
    s = r["slots"]
    body.append('<div class="slots">' + (slot("What it suggests", block(T, s["Suggests"]), "full key") if L.flat(s.get("Suggests", "")) else "")
                + (slot("What was seen", block(T, s["Seen"]), "full") if L.flat(s.get("Seen", "")) else "")
                + slot("What it looks at", block(T, s.get("Looks at", "")), "full") + "</div>")
    body.append("<h2>Log</h2>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == r["id"]]), False))
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
    for title, group in (("To discuss", lab.open_decisions()), ("Decided", sorted([d for d in lab.decisions if d["state"] == "decided"], key=lambda d: str(d["decided"].get("date")), reverse=True))):
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
    """Every term, by group, each group closed until it is opened or the filter finds something in it."""
    url = code_url(lab)
    groups = {}
    for g in lab.glossary:
        groups.setdefault(g["group"] or "Terms", []).append(g)
    body = ["<h1>Glossary</h1>"]
    if not lab.glossary:
        body.append('<p class="muted">No term is defined yet.</p>')
        return frame(lab, "Glossary", "".join(body))
    body.append('<p class="muted" style="font:.86rem var(--sans)">A term is explained where it is used: hover a dotted word on any page. This page is the whole list.</p>')
    body.append('<input class="gfilter" type="search" placeholder="Find a term" aria-label="Find a term" oninput="'
                "var q=this.value.toLowerCase();document.querySelectorAll('.ggroup').forEach(function(g){var n=0;g.querySelectorAll('dt').forEach(function(t){"
                "var d=t.nextElementSibling,hit=!q||(t.textContent+' '+d.textContent).toLowerCase().indexOf(q)>=0;t.hidden=d.hidden=!hit;if(hit)n++;});g.hidden=!n;g.open=!!q&&n>0;});"
                '">')
    for name, terms in groups.items():
        rows = []
        for g in terms:
            code = (f' · <a href="{url}/blob/main/src/{e(g["code"].split(":")[0].replace(".", "/"))}.py"><code>{e(g["code"])}</code></a>' if url else f' · <code>{e(g["code"])}</code>') if g["code"] else ""
            more = f' · See: {see_link(lab, g["see"])}' if g["see"] else ""
            rows.append(f'<dt id="{e(g["term"].lower().replace(" ", "-"))}">{e(g["term"])}</dt><dd>{e(g["definition"])}{code}{more}{avoid_note(g)}</dd>')
        body.append(f'<details class="ggroup"><summary>{e(name)}<span>{len(terms)} terms</span></summary><dl class="gloss">{"".join(rows)}</dl></details>')
    body.append("<script>(function(){var h=decodeURIComponent(location.hash.slice(1));var t=h&&document.getElementById(h);if(t){t.closest('details').open=true;t.scrollIntoView();}})();</script>")
    return frame(lab, "Glossary", "".join(body))


def graph_page(lab, T):
    W, colw, y0, row = 266, 232, 156, 66
    cols = lab.live(lab.questions)
    width = max(len(cols) * W, 600)
    fill = {"ok": "var(--ok-soft)", "warn": "var(--warn-soft)", "bad": "var(--bad-soft)", "info": "var(--info-soft)", "plain": "var(--sunk)"}
    ink = {"ok": "var(--ok)", "warn": "var(--warn)", "bad": "var(--bad)", "info": "var(--info)", "plain": "var(--ink-3)"}
    pos, out, col_of = {}, [], {}

    def box(n, x, y, sub=None, h=50):
        pos[n["id"]] = (x, y)
        t = tone(n)
        title = n["title"] if len(n["title"]) <= 30 else n["title"][:28] + "…"
        return (f'<a href="/{n["id"]}"><title>{e(n["title"])}. {e(L.bare(n.get("description") or ""))}</title><rect x="{x}" y="{y}" width="{colw}" height="{h}" rx="8" fill="{fill[t]}" stroke="{ink[t]}" stroke-width="1"/>'
                f'<text x="{x + 12}" y="{y + 20}" font-size="12.5" font-weight="600" fill="var(--ink)">{e(title)}</text>'
                f'<text x="{x + 12}" y="{y + 38}" font-size="11" fill="{ink[t]}">{e(sub or n["id"] + " · " + label(n))}</text></a>')

    centre = {}  # each goal sits above the middle of its own questions
    for g in lab.live(lab.goals):
        mine = [i for i, q in enumerate(cols) if q["goal"] == g["id"]]
        centre[g["id"]] = ((mine[0] + mine[-1] + 1) / 2 * W if mine else width / 2) - colw / 2
        out.append(box(g, centre[g["id"]], 10))
    shown = {q["id"]: [x for x in q["items"] if x["state"] not in ("replaced", "dropped")] for q in cols}
    for i, q in enumerate(cols):
        x = i * W + (W - colw) / 2
        gx = centre[q["goal"]]
        col_of[q["id"]] = i
        out.append(box(q, x, 84))
        out.append(f'<path d="M{gx + colw / 2} 60 C{gx + colw / 2} 76,{x + colw / 2} 68,{x + colw / 2} 84" fill="none" stroke="var(--rule-strong)"/>')
        for j, s in enumerate(shown[q["id"]]):
            col_of[s["id"]] = i
            out.append(box(s, x, y0 + j * row, f'{s["id"]} · {s["type"]} · {label(s)}'))
            py = 134 if j == 0 else y0 + (j - 1) * row + 50
            out.append(f'<line x1="{x + colw / 2}" y1="{py}" x2="{x + colw / 2}" y2="{y0 + j * row}" stroke="var(--rule-strong)"/>')
    k = 0
    for n in cols + lab.items:
        for need in n.get("needs") or []:
            if need not in pos or n["id"] not in pos:
                continue
            a, b = pos[need], pos[n["id"]]
            ca, cb = col_of[need], col_of[n["id"]]
            if ca == cb and 0 < b[1] - a[1] <= row:
                continue  # the one just above: the grey line already says it
            k += 1
            off = (k % 4) * 4
            sy, ty, gut = a[1] + 30 + off / 2, b[1] + 18 + off / 2, (W - colw) / 2
            if ca == cb:
                gx2 = a[0] + colw + 6 + off
                d = f"M{a[0] + colw} {sy} H{gx2} V{ty} H{b[0] + colw + 1}"
            elif cb == ca + 1:
                gx2 = a[0] + colw + gut - 4 + off
                d = f"M{a[0] + colw} {sy} H{gx2} V{ty} H{b[0] - 1}"
            else:
                g1, g2, lane = a[0] + colw + gut - 4 + off, b[0] - gut + 4 - off, b[1] - 8 + off / 2
                d = f"M{a[0] + colw} {sy} H{g1} V{lane} H{g2} V{ty} H{b[0] - 1}"
            out.append(f'<path d="{d}" fill="none" stroke="var(--accent)" stroke-width="1.1" stroke-dasharray="4 3" marker-end="url(#arr)"/>')
    height = y0 + max([len(v) for v in shown.values()] or [0]) * row + 20
    svg = (f'<svg class="graph" viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="The goal, its questions, and their experiments and builds"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           f'<path d="M1 1L9 5L1 9" fill="none" stroke="var(--accent)" stroke-width="1.5"/></marker></defs>{"".join(out)}</svg>')
    legend = (f'<p style="font:.85rem var(--sans)">{pill("confirmed, built or answered yes", "ok")} {pill("unclear, waiting or under discussion", "warn")} {pill("refuted or failed", "bad")} {pill("open or running", "info")} {pill("planned", "plain")}'
              " &nbsp; A dashed arrow points from what is needed to what needs it.</p>")
    return frame(lab, "Graph", f"<h1>Graph</h1>{legend}{svg}")


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
        T = Text(lab)
        parts = inner.split("/")
        genre, status, description, page, path = "", "", "", None, ""
        if inner == "":
            page = home(lab, T)
        elif inner == "graph":
            page = graph_page(lab, T)
        elif parts[0] == "log" and (len(parts) == 1 or (len(parts) == 2 and parts[1] in L.KINDS)):
            page, path = log_page(lab, T, parts[1] if len(parts) == 2 else ""), "log.md"
        elif inner == "decisions":
            page = decisions_page(lab, T)
        elif inner == "resources":
            page, path = resources_page(lab, T), "resources.toml"
        elif inner == "glossary":
            page, path = glossary_page(lab, T), "GLOSSARY.md"
        elif inner in lab.nodes:
            n = lab.nodes[inner]
            page = {"goal": goal_page, "question": question_page, "experiment": experiment_page, "build": build_page, "reading": reading_page, "decision": decision_page}[n["type"]](lab, T, n)
            genre, status, path = n["type"], label(n), n["path"]
            description = n["asks"] if n["type"] == "question" and n["asks"] != n["title"] else "" if n["type"] in L.STEPS else L.bare(n.get("description") or "")
        if page is None:
            return None
        body = re.sub(r"<h1>.*?</h1>", "", page["body"], count=1, flags=re.S)
        panels = [(title, _links(f'<div class="lv panelbox">{block}</div>')) for title, block in re.findall(r"<h4>(.*?)</h4>(.*?)(?=<h4>|$)", page["panel"], flags=re.S)]
        return View(title=page["title"], main=_links(f'<div class="lv">{body}</div>'), description=L.flat(description),
                    genre=genre, status=status, head=f"<style>{CSS}</style>", panels=panels, path=path)

    def rail(self):
        lab = self.lab()
        out = [{"title": t, "url": f"/lab/{p}"} for t, p in (("Now", ""), ("Graph", "graph/"), ("Decisions", "decisions/"), ("Log", "log/"), ("Resources", "resources/"), ("Glossary", "glossary/"))]
        for g in lab.live(lab.goals):
            out.append({"title": g["title"], "url": f"/lab/{g['id']}/", "status": g["state"], "tone": tone(g)})
            for q in lab.live(g["questions"]):
                items = [{"title": x["title"], "url": f"/lab/{x['id']}/", "status": label(x), "tone": tone(x)} for x in q["items"] if x["state"] not in ("replaced", "dropped")]
                out.append({"title": q["title"], "url": f"/lab/{q['id']}/", "status": label(q), "tone": tone(q), "open": q["state"] == "open" and bool(items), "items": items})
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
        return ["", "graph", "decisions", "log", "resources", "glossary"] + [f"log/{k}" for k in L.KINDS] + list(lab.nodes)

    def backlinks(self):
        lab = self.lab()
        out = {}
        for n in lab.goals + lab.questions + lab.items:
            for page in n.get("see") or []:
                out.setdefault(f"content/{str(page).split('#')[0]}/index.html", []).append({"title": f"{n['id']} {n['title']}", "url": f"/lab/{n['id']}/", "status": label(n)})
        return out


def provider(library_root):
    return Provider(library_root)


# ---- page style 2: a picture at the top, results kept apart from the plan, the record folded ----

def boxed(T, label, text, cls="full", home=None, extra=""):
    """One slot in its box, under the template's fixed label. A heading line the card starts with is dropped:
    the label is the heading, the same on every page."""
    t = str(text or "").strip()
    t = re.sub(r"^#{2,3} .+\n?", "", t).strip()
    if not L.flat(t) and not extra:
        return ""
    return slot(label, block(T, t, home) + extra, cls)


def record_box(lab, T, x, runs_html="", reviews_html=""):
    inner = runs_html + reviews_html + earlier(lab, T, x) + where_to_look(lab, [x]) + "<h3>Log</h3>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == x["id"]]), False)
    return f'<details class="record"><summary>The record: runs, reviews, files and log</summary>{inner}</details>'


_old_experiment_page = experiment_page


def experiment_page(lab, T, x):
    q = lab.nodes[x["question"]]
    s = x["slots"]
    body = [f'<h1>{e(x["title"])}</h1>', f'<p class="lead">{T(x["description"])}</p>', ran(lab, x)]
    by = lab.replaced_by(x["id"])
    if by:
        why = L.flat(by.get("because") or "")
        body.append(f'<div class="box"><b>Replaced by</b> {named(lab, by["id"])}' + (f": {T(why)}" if why else ".") + "</div>")
    body.append(where_box(lab, T, x))
    body += [decision_box(lab, T, d) for d in lab.open_decisions() if x["id"] in d["about"] or x["id"] in d["holds"]]
    body.append(picture(lab, x))
    # results and what changed since the lock: apart from the plan, above it
    after = ""
    if x["state"] == "done":
        after += boxed(T, "What it means", s.get("Means", ""), "full key", x["id"]) + boxed(T, "What was found", s.get("Found", ""), "full key", x["id"])
    after += boxed(T, "Since the plan was locked", s.get("Since the lock", ""), "full key", x["id"], "" if L.flat(s.get("Since the lock", "")) else decided_notes(lab, T, x))
    if after:
        body.append('<div class="slots">' + after + "</div>")
    # the plan, as locked
    body.append('<h2>The plan, as locked</h2><div class="slots">'
                + boxed(T, "What it compares", s.get("Compares", ""), extra=arms_table(lab, T, x))
                + boxed(T, "Run on", s.get("Cases", ""))
                + boxed(T, "How the answer is read", s.get("Outcomes", ""), extra=tick_rows(lab, x))
                + boxed(T, "What it cannot show", s.get("Limits", "")) + "</div>")
    if x["state"] != "done":
        body.append(cost_box(lab, T, [x], [x.get("cost") or ""]))
    if x["results"] and x["reviewed"]:
        body.append(results_tables(lab, T, x))
    old = _old_experiment_page(lab, T, x)["body"]
    m = re.search(r'(<ul class="runs">.*?</ul>)', old, flags=re.S)
    runs_html = ("<h3>Runs</h3>" + m.group(1)) if m else ""
    m = re.search(r'(<table class="t"><tr><th>Reviewed</th>.*?</table>)', old, flags=re.S)
    reviews_html = ("<h3>Reviews</h3>" + m.group(1)) if m else ""
    body.append(record_box(lab, T, x, runs_html, reviews_html))
    return frame(lab, x["title"], "".join(body), edges_panel(lab, x), [("/", "Now"), ("/" + q["id"], q["title"])])


def question_page(lab, T, q):
    s = q["slots"]
    live = [x for x in q["items"] if x["state"] not in ("replaced", "dropped")]
    body = [f'<h1>{e(q["title"])}</h1>']
    if q["state"] == "parked":
        d = lab.parked_by(q["id"])
        body.append(f'<div class="box"><b>Set aside</b> by {named(lab, d["id"])}: nothing under it moves until a decision brings it back.</div>')
    body.append(picture(lab, q))
    before = [lab.nodes[i] for i in q["needs"] if i in lab.nodes]
    head = ""
    if before:
        head += slot("Where we are coming from", "".join(f'<p>{named(lab, n["id"])} ({e(label(n))}).</p>' for n in before), "full")
    head += boxed(T, "What we know so far", s.get("So far", ""), "full key", extra=decided_notes(lab, T, q))
    body.append('<div class="slots">' + head + "</div>")
    body.append('<h2>The question, as asked</h2><div class="slots">'
                + boxed(T, "Why we ask", q["description"])
                + boxed(T, "How it works", s.get("How we would know", ""))
                + boxed(T, "One real case, step by step", s.get("Example", ""), "full example")
                + boxed(T, "We expect", s.get("We expect", ""), "")
                + boxed(T, "Wrong if", s.get("Wrong if", ""), "") + "</div>")
    talk = [d for d in lab.open_decisions() if any(a == q["id"] or a.startswith(q["id"] + ".") for a in d["about"] + d["holds"])]
    if talk:
        body.append("<h2>What is needed from you</h2>" + "".join(decision_box(lab, T, d) for d in talk))
    body.append("<h2>The steps, and where each stands</h2>" + ("".join(step_row(lab, T, x) for x in live) if live else '<p class="muted">Not started: no experiment is planned yet.</p>'))
    tests = [x for x in live if x["type"] == "experiment"]
    body.append(cost_box(lab, T, tests, [x.get("cost") or "" for x in tests if x["state"] != "done"]))
    inner = where_to_look(lab, live) + "<h3>Log</h3>" + log_html(lab, T, happened([l for l in lab.lines if l["about"] == q["id"] or l["about"].startswith(q["id"] + ".")]))
    body.append(f'<details class="record"><summary>The record: files and log</summary>{inner}</details>')
    return frame(lab, q["title"], "".join(body), edges_panel(lab, q), [("/", "Now"), ("/" + q["goal"], lab.nodes[q["goal"]]["title"])])

def glossary_page(lab, T):
    """Every term, by group, all open; each with its definition, its example and where it is explained."""
    groups = {}
    for g in lab.glossary:
        groups.setdefault(g["group"] or "Terms", []).append(g)
    body = ["<h1>Glossary</h1>"]
    intro = getattr(lab, "glossary_intro", "")
    if intro:
        body.append(f'<div class="why">{block(T, intro)}</div>')
    body.append('<input class="gfilter" type="search" placeholder="Find a term" aria-label="Find a term" oninput="'
                "var q=this.value.toLowerCase();document.querySelectorAll('.ggroup').forEach(function(g){var n=0;g.querySelectorAll('dt').forEach(function(t){"
                "var d=t.nextElementSibling,hit=!q||(t.textContent+' '+d.textContent).toLowerCase().indexOf(q)>=0;t.hidden=d.hidden=!hit;if(hit)n++;});g.hidden=!n;});"
                '">')
    for name, terms in groups.items():
        rows = []
        for g in terms:
            ex = f'<span class="gex">{T(g["example"])}</span>' if g.get("example") else ""
            more = f' <span class="gsee">See: {see_link(lab, g["see"])}</span>' if g["see"] else ""
            rows.append(f'<dt id="{e(g["term"].lower().replace(" ", "-"))}">{e(g["term"])}</dt><dd>{e(g["definition"])}{ex}{more}{avoid_note(g)}</dd>')
        body.append(f'<details class="ggroup" open><summary>{e(name)}<span>{len(terms)} terms</span></summary><dl class="gloss">{"".join(rows)}</dl></details>')
    body.append("<style>.lv .gex{display:block;margin-top:.3rem;font-size:.93rem;color:var(--ink-2)}.lv .gex::before{content:'For example: ';font-weight:600}.lv .gsee{display:block;font:.82rem var(--sans);margin-top:.2rem}.lv .why{max-width:48rem}</style>")
    body.append("<script>(function(){var h=decodeURIComponent(location.hash.slice(1));var t=h&&document.getElementById(h);if(t){t.scrollIntoView();}})();</script>")
    return frame(lab, "Glossary", "".join(body))
