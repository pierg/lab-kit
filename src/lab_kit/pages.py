"""Pages: the library's pages kept in step with the record (docs/model.md, section 9, Pages).

The question cards are the facts, and no page repeats one. A lab opts in with `pages.toml` in its library, which
gives every page a kind: `storyline` pages carry the argument and are revised when a question they cite is answered,
`stable` pages explain how the method works and are only corrected, `reference` pages hold the trail, the appendices
and the maps, and `retiring` pages wait to be merged. Then `lab check` holds that:

- every page under the listed sections has a kind, and every listed page is there;
- a number a page quotes inside `data-result="<step>:<result>"` is the value that result has, from results that were
  reviewed and not replaced or dropped; a storyline page carries `<meta name="numbers" content="tagged">` and shows
  no other number;
- no page but a retiring one uses a phrase `pages.toml` drops, or claims to be first without "to our knowledge";
- a storyline or stable page has passed a page reviewer as it now stands (`page-reviews.tsv`, by fingerprint);
- a question answered on or after `since` records that its answer reached its pages (`answers-in-pages.tsv`);
- each active storyline page links every storyline page;
- a link to a glossary term names a term the glossary has, and carries its definition as hover text.

A lab without `pages.toml` in its library has none of this.
"""
from __future__ import annotations

import csv, hashlib, html, os, re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html.parser import HTMLParser

from . import record as R, storylines
from .runs import stop

KINDS = ("storyline", "stable", "reference", "retiring")
REVIEWED = ("storyline", "stable")
FILE = "pages.toml"
REVIEWS, REVIEW_COLS = "page-reviews.tsv", ("page", "fingerprint", "date", "note")
ANSWERS, ANSWER_COLS = "answers-in-pages.tsv", ("question", "answered", "date", "note")
SETTINGS = {"since", "dropped", "first", "names", "sections", "pages"}
SECTIONS = ("entries", "concepts", "guides")
NAMES = ("Result", "Step", "Figure", "Table", "Section", "Part", "Version")  # a number right after one of these is not a result
GLOSSARY_URL = "/lab/glossary/#"
TERM_LINK = re.compile(r"""<a\b[^>]*\bhref=(?:"/lab/glossary/#([^"]*)"|'/lab/glossary/#([^']*)')[^>]*>""")
TITLE = re.compile(r"""\s+title=(?:"[^"]*"|'[^']*'|[^\s>]+)""")
FIRST = (r"for the first time", r"\bfirst[- ]ever\b", r"\bnever before\b", r"\bhad not been done\b",
         r"\bnever been (?:\w+ )?(?:done|shown|proved|measured)\b")  # a claim to be first, unless `pages.toml` says otherwise
SPLIT = re.compile(r"(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bvs\.)(?<!\bcf\.)(?<=[.!?])\s")
LOOSE = re.compile(r"(?<![\w.−-])[−-]?(?:\d(?:[\d,]*\d)?(?:\.\d+)?|\.\d+)(?![\d,]*\d|\.\d)")  # a unit after it ("3.5x", "40ms") still makes it a number
NUMBER = re.compile(r"[-−]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)")
STEP_LINK = re.compile(r"^/lab/(G\d+(?:\.Q\d+(?:\.\d+)?)?)/")
PAGE_LINK = re.compile(r"^/content/([^#?]+?)/?(?:index\.html)?(?:[#?].*)?$")


def anchor(term):
    """Where a term's entry is on the glossary page, as the site writes it."""
    return term.lower().replace(" ", "-")


# ------------------------------------------------------------------ the settings

def library(lab):
    return os.path.join(lab.root, lab.cfg.get("library", "docs"))


def on(lab):
    """Whether the lab keeps its pages: its library has `pages.toml`."""
    return os.path.exists(os.path.join(library(lab), FILE))


def settings(lab):
    """(settings, problems): what `pages.toml` says, with the defaults filled in. Cached on the lab."""
    if getattr(lab, "_pages", None) is not None:
        return lab._pages
    problems, raw = [], {}
    try:
        import tomllib
    except ImportError:  # Python 3.10
        import tomli as tomllib
    try:
        raw = tomllib.loads(R.read(os.path.join(library(lab), FILE)))
    except Exception as err:
        problems.append(f"cannot be read as TOML: {err}")
    where = lab.rel(os.path.join(library(lab), FILE))
    for k in sorted(set(raw) - SETTINGS):
        problems.append(f"holds `{k}`; it holds {', '.join(sorted(SETTINGS - {'pages'}))} and the table [pages]")
    kinds = raw.get("pages", {})
    if not isinstance(kinds, dict):
        problems.append("[pages] is a table: one line `\"<page>\" = \"<kind>\"` for each page")
        kinds = {}
    for page, kind in sorted(kinds.items()):
        if kind not in KINDS:
            problems.append(f"gives {page} the kind {kind!r}; a kind is {', '.join(KINDS)}")
        if str(page).startswith("/") or ".." in str(page).split("/"):
            problems.append(f"lists {page}; a page is a path inside the library's content, without `..`")
    since = None
    if "since" not in raw:
        problems.append("names no `since = \"<date>\"`: the day from which every answered question records that its answer reached its pages")
    else:
        import datetime
        try:
            since = (raw["since"] if isinstance(raw["since"], datetime.date) else datetime.date.fromisoformat(str(raw["since"]))).isoformat()
        except ValueError:
            problems.append(f"`since` is {raw['since']!r}, not a date such as \"2026-01-31\"")

    def patterns(key, default):
        found, given = [], raw.get(key, list(default))
        if not isinstance(given, list):
            problems.append(f"`{key}` lists phrases, each a regular expression")
            given = []
        for p in given:
            try:
                found.append(re.compile(p, re.I)) if isinstance(p, str) and p else problems.append(f"`{key}` lists phrases, each a regular expression")
            except re.error as err:
                problems.append(f"`{key}` holds {p!r}, which is not a regular expression: {err}")
        return found

    dropped, first = patterns("dropped", ()), patterns("first", FIRST)
    names = raw.get("names", [])
    if not isinstance(names, list) or not all(isinstance(n, str) and n.strip() for n in names):
        problems.append("`names` lists words, such as [\"Model\", \"Trial\"], after which a number is not a result")
        names = []
    sections = raw.get("sections", list(SECTIONS))
    if not isinstance(sections, list) or not all(isinstance(s, str) and s.strip() and "/" not in s for s in sections):
        problems.append("`sections` lists the folders under content/ whose pages each have a kind, such as [\"entries\", \"concepts\"]")
        sections = list(SECTIONS)
    words = sorted({*NAMES, *(n.strip() for n in names)}, key=len, reverse=True)
    lab._pages = ({"kinds": {str(p).strip("/"): k for p, k in kinds.items() if k in KINDS}, "since": since, "dropped": dropped, "first": first,
                   "names": re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\s+$", re.I), "sections": sections, "where": where},
                  problems)
    return lab._pages


# ------------------------------------------------------------------ reading a page

class _Page(HTMLParser):
    """What a page cites: its `data-result` elements with their text, its `/lab/<id>/` links, its links to other pages
    and to glossary terms, and (on a tagged page) every number shown outside a result."""

    VOID = {"br", "img", "hr", "input", "meta", "link", "wbr", "source", "col", "area", "base", "embed", "param", "track"}
    PLAIN = {"code", "svg", "figure", "style", "script", "title", "head"}

    def __init__(self, names):
        super().__init__(convert_charrefs=True)
        self.names, self.results, self.links, self.pages, self.terms = names, [], set(), set(), []
        self.loose, self.unclosed, self.tagged = [], [], False
        self._stack, self._text, self._recent = [], {}, ""  # (tag, data-result, plain)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "numbers" and a.get("content") == "tagged":
            self.tagged = True
        href = a.get("href") or ""
        m = STEP_LINK.match(href)
        if m:
            self.links.add(m.group(1))
        if href.startswith(GLOSSARY_URL):
            titles = [v or "" for k, v in attrs if k == "title"]
            self.terms.append((href[len(GLOSSARY_URL):], " ".join(titles[0].split()) if len(titles) == 1 else "\0several" if titles else ""))
        p = PAGE_LINK.match(href)
        if p:
            self.pages.add(p.group(1).strip("/"))
        self.handle_data(" ")
        if tag in self.VOID:
            return
        self._stack.append((tag, a.get("data-result"), tag in self.PLAIN or "data-plain" in a or bool(m)))
        self._text[len(self._stack)] = ""

    def handle_endtag(self, tag):
        self.handle_data(" ")
        if tag in self.VOID or not any(t == tag for t, _, _ in self._stack):
            return
        while self._stack:  # an element whose end tag is left out ends where its parent ends, as HTML reads it
            open_tag, spec, _ = self._stack.pop()
            text = self._text.pop(len(self._stack) + 1, "")
            if spec:
                self.results.append((spec, text))
            if open_tag == tag:
                break

    def handle_data(self, data):
        for depth in self._text:
            self._text[depth] += data
        if not any(spec or plain for _, spec, plain in self._stack):
            for m in LOOSE.finditer(data):
                before, after = self._recent + data[:m.start()], data[m.end():]
                year = re.fullmatch(r"(19|20)\d\d", m.group(0)) and not re.match(r"\s*[a-z]", after)
                if not (year or self.names.search(before) or re.search(r"\d[\d,]*\s+of\s*$", before)):
                    self.loose.append(m.group(0))
        self._recent = (self._recent + data)[-60:]

    def close(self):
        super().close()
        self.unclosed += [spec for _, spec, _ in self._stack if spec]  # still open when the page ends: what it shows is unclear


def read_page(lab, files):
    p = _Page(settings(lab)[0]["names"])
    for f in files:
        p.feed(R.read(f))
    p.close()
    return p


def _plain_text(page):
    page = re.sub(r"<(style|script)\b.*?</\1>", " ", page, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def content(lab):
    return os.path.join(library(lab), "content")


def files(lab, page):
    """The HTML files of a page: every one under `content/<page>/`, or `content/<page>.html` (the home page, a map)."""
    base = os.path.join(content(lab), page)
    if os.path.isdir(base):
        return sorted(os.path.join(d, f) for d, _, fs in os.walk(base) for f in fs if f.endswith(".html"))
    return [base + ".html"] if os.path.isfile(base + ".html") else []


def present(lab):
    """The pages of the sections `pages.toml` names: each folder under `content/<section>/`."""
    out = []
    for s in settings(lab)[0]["sections"]:
        d = os.path.join(content(lab), s)
        out += [f"{s}/{n}" for n in sorted(os.listdir(d)) if os.path.isdir(os.path.join(d, n))] if os.path.isdir(d) else []
    return out


def fingerprint(lab, page):
    """The first 16 hex digits of the SHA-256 of the page's HTML files, each with its path under content/, in path order.
    A glossary link's hover text is left out, so a changed definition asks for no new review."""
    h = hashlib.sha256()
    for f in files(lab, page):
        body = open(f, "rb").read()
        if GLOSSARY_URL.encode() in body:
            body = TERM_LINK.sub(lambda m: TITLE.sub("", m.group(0)), body.decode()).encode()
        h.update(os.path.relpath(f, content(lab)).encode() + b"\0" + body + b"\0")
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ the two records

def _rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def passes(lab):
    """Each page's fingerprints that a page reviewer passed."""
    out = {}
    for r in _rows(os.path.join(library(lab), REVIEWS)):
        out.setdefault(r.get("page"), set()).add(r.get("fingerprint"))
    return out


def unreviewed(lab, kinds=REVIEWED):
    """The pages of these kinds whose fingerprint matches no recorded pass."""
    passed, s = passes(lab), settings(lab)[0]
    return [p for p, k in sorted(s["kinds"].items()) if k in kinds and files(lab, p) and fingerprint(lab, p) not in passed.get(p, set())]


def answered(lab):
    """{question: the date on its `answered:` line} for every answered question."""
    return {q["id"]: str(q["answered"])[:10] for q in lab.questions if q.get("answered")}


def due(lab):
    """[(question, date)]: the questions answered on or after `since` that no row says reached their pages."""
    since = settings(lab)[0]["since"]
    if not since:
        return []
    done = {(r.get("question"), r.get("answered")) for r in _rows(os.path.join(library(lab), ANSWERS))}
    return [(q, d) for q, d in sorted(answered(lab).items()) if d >= since and (q, d) not in done]


def _note(note):
    note = " ".join(str(note).split())
    if not note or any(c in note for c in '\t"'):
        stop("the note is one line, with no tab and no double quote")
    return note


def _append(path, cols, row):
    old = R.read(path) if os.path.exists(path) else ""
    with open(path, "w" if not old.strip() else "a", newline="") as f:
        if not old.strip():
            f.write("\t".join(cols) + "\n")
        elif not old.endswith("\n"):
            f.write("\n")
        f.write("\t".join(row) + "\n")


def _require(lab):
    if not on(lab):
        stop(f"the library keeps no {FILE}: the lab does not keep its pages this way (docs/model.md, section 9, Pages)")
    s, problems = settings(lab)
    if problems:
        stop(f"{s['where']}: " + "; ".join(problems))
    return s


def record_pass(lab, page, note):
    """The page reviewer's pass of a page as it now stands. Only the reviewer runs it, and only on a pass."""
    from .write import today
    s = _require(lab)
    page = page.strip("/")
    if page not in s["kinds"]:
        stop(f"{page} has no kind in {s['where']}")
    if not files(lab, page):
        stop(f"{page} has no HTML file under {lab.rel(content(lab))}")
    path = os.path.join(library(lab), REVIEWS)
    _append(path, REVIEW_COLS, (page, fingerprint(lab, page), today(), _note(note)))
    return lab.rel(path)


def record_answer(lab, question, note):
    """That a question's answer reached the pages it touches. Refused while a storyline or stable page waits for a pass."""
    from .write import today
    _require(lab)
    when = answered(lab).get(question)
    if not when:
        stop(f"{question} is not an answered question")
    note = _note(note)
    waiting = unreviewed(lab)
    if waiting:
        stop(f"these pages wait for a page reviewer's pass first: {', '.join(waiting)}")
    path = os.path.join(library(lab), ANSWERS)
    if any(r.get("question") == question and r.get("answered") == when for r in _rows(path)):
        stop(f"{question}'s answer of {when} is already recorded")
    _append(path, ANSWER_COLS, (question, when, today(), note))
    return lab.rel(path)


def definitions(lab):
    """{anchor: definition} for every glossary entry, its other names (`- also:`) included, as one line."""
    out = {}
    for g in lab.glossary:
        for name in [g["term"]] + g.get("also", []):
            out.setdefault(anchor(name), " ".join(g["definition"].split()))
    return out


def sync_terms(lab):
    """Write each glossary link's hover text from the glossary, on every page of the library. Returns the files changed."""
    _require(lab)
    defs, changed = definitions(lab), []

    def fix(m):
        a = html.unescape(m.group(1) if m.group(1) is not None else m.group(2))
        if a not in defs:
            return m.group(0)
        return TITLE.sub("", m.group(0))[:-1].rstrip() + f' title="{html.escape(defs[a], quote=True)}">'

    for d, _, fs in sorted(os.walk(content(lab))):
        for name in sorted(fs):
            f = os.path.join(d, name)
            if not name.endswith(".html"):
                continue
            old = R.read(f)
            new = TERM_LINK.sub(fix, old)
            if new != old:
                open(f, "w").write(new)
                changed.append(lab.rel(f))
    return changed


def cites(lab, ident):
    """The storyline pages that cite a question or a step, by a `data-result` or a `/lab/<id>/` link."""
    out = []
    for page, kind in sorted(settings(lab)[0]["kinds"].items()):
        if kind == "storyline" and files(lab, page):
            p = read_page(lab, files(lab, page))
            if any(i == ident or i.startswith(ident + ".") for i in p.links | {spec.partition(":")[0].strip() for spec, _ in p.results}):
                out.append(page)
    return out


# ------------------------------------------------------------------ what `lab check` holds

def _number(lab, spec, shown):
    """What is wrong with the number a `data-result` element shows, or None."""
    step, _, names = spec.partition(":")
    step = step.strip()
    n = lab.nodes.get(step)
    if not n or n["type"] != "experiment" or not names.strip():
        return f"data-result={spec!r} names no result of an experiment of the record (<step>:<result>)"
    rows = {r.get("name"): r for r in n["results"]}
    terms = [[x.strip() for x in t.split("*")] for t in names.split("+")]
    total, scaled_reads = Decimal(0), set()
    for t in terms:
        product = Decimal(1)
        for name in t:
            if name not in rows:
                return f"data-result={spec!r}: {step} has no result {name!r}"
            if rows[name].get("num") is None:
                return f"data-result={spec!r}: {name} is {rows[name].get('value')!r}, not a number"
            product *= Decimal(str(rows[name]["value"]).strip())
            scaled_reads.add(rows[name].get("reads") or "")
        total += product
    single = rows[terms[0][0]] if len(terms) == 1 and len(terms[0]) == 1 else None
    if not single and scaled_reads & {"percent", "points"} and any(len(t) == 1 and rows[t[0]].get("reads") in ("percent", "points") for t in terms):
        return f"data-result={spec!r} adds a percentage or a difference in points to other results"
    if not all(rows[x].get("usable") for t in terms for x in t):
        return f"data-result={spec!r}: the results of {step} are not reviewed, or {step} was replaced or dropped, so no page quotes them"
    m = NUMBER.search(shown)
    if not m:
        return f"data-result={spec!r} shows no number: {' '.join(shown.split())!r}"
    text = m.group(0).replace(",", "").replace("\u2212", "-")
    scaled = total * 100 if single and single.get("reads") in ("percent", "points") else total
    places = len(text.split(".")[1]) if "." in text else 0
    try:
        expected = scaled.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return f"data-result={spec!r}: the card's value {scaled} cannot be shown as a number"
    if Decimal(text) == expected:
        return None
    card = NUMBER.search(R.shown(single)) if single else None  # the card's own way of showing it is right too
    if card and Decimal(card.group(0).replace(",", "").replace("\u2212", "-")) == Decimal(text):
        return None
    return f"shows {m.group(0)} for {spec}, but the card says {expected}"


def check(lab, bad, notes):
    """What `lab check` holds about the library's pages, when the library keeps `pages.toml`."""
    if not on(lab):
        return
    s, problems = settings(lab)
    for p in problems:
        bad("pages", s["where"], p)
    kinds, where = s["kinds"], s["where"]
    here = present(lab)
    for page in sorted(set(here) - set(kinds)):
        bad("pages", where, f"{page} has no kind: give it one of {', '.join(KINDS)}")
    for page in sorted(kinds):
        if not files(lab, page):
            bad("pages", where, f"lists {page}, which is not a page of the library")
    for q, when in due(lab):
        bad("pages", q, f"answered {when}, and no row of {ANSWERS} says its answer reached its pages: revise the pages that cite it "
            f"(`lab pages cites {q}`), have a page reviewer pass them, then `lab pages answered {q} \"<the pages revised>\"`")
    for page in unreviewed(lab):
        bad("pages", page, f"no page reviewer has passed it as it now stands; a {kinds[page]} page lands only on a pass, which the reviewer "
            f"records with `lab pages passed {page} \"<one line>\"`")
    _, active, _ = storylines.config(lab)
    for scope in active:
        if files(lab, scope):
            linked = read_page(lab, files(lab, scope)).pages
            for page, kind in sorted(kinds.items()):
                if kind == "storyline" and page != scope and page not in linked:
                    bad("pages", scope, f"the scope page does not link the storyline page {page}: list it, with the cards it cites")
    defs = definitions(lab)
    targets = [(p, kinds.get(p)) for p in sorted(set(here) | set(kinds))]
    for page, kind in targets:
        for f in files(lab, page):
            rel, text = lab.rel(f), R.read(f)
            p = read_page(lab, [f])
            for spec, shown in p.results:
                wrong = _number(lab, spec, shown)
                if wrong:
                    bad("pages", rel, wrong)
            for spec in p.unclosed:
                bad("pages", rel, f"the element with data-result={spec!r} is still open where the page ends")
            for a, title in p.terms:
                a = html.unescape(a)
                if a not in defs:
                    bad("pages", rel, f"links the glossary term {a!r}, which GLOSSARY.md has no entry for: add the entry or fix the link")
                elif title != defs[a]:
                    bad("pages", rel, f"the hover text of the link to {a!r} is not its glossary definition: run `lab pages terms`")
            if kind == "storyline" and not p.tagged:
                bad("pages", rel, "is a storyline page without `<meta name=\"numbers\" content=\"tagged\">`: a storyline page quotes every "
                    "number beside the result it comes from")
            if kind == "storyline" and p.tagged and p.loose:
                bad("pages", rel, f"shows numbers outside a data-result element ({', '.join(p.loose[:8])}): tag each with the result it "
                    "comes from, or mark a number that is not a result (a definition, a count of what is studied) with data-plain")
            if kind == "retiring":
                continue
            for sentence in SPLIT.split(_plain_text(text)):
                for pattern in s["dropped"]:
                    hit = pattern.search(sentence)
                    if hit:
                        bad("pages", rel, f"says {hit.group(0)!r}, a phrase {where} drops")
                for pattern in s["first"]:
                    hit = pattern.search(sentence)
                    if hit and "to our knowledge" not in sentence.lower():
                        bad("pages", rel, f"claims to be first ({hit.group(0)!r}) without \"to our knowledge\"")


# ------------------------------------------------------------------ what the agent sees

def now_lines(lab):
    """The lines `lab now` gives the pages: answers that have not reached their pages, and pages waiting for a reviewer."""
    if not on(lab):
        return []
    if settings(lab)[1]:
        return ["", "Pages", f"- {settings(lab)[0]['where']} needs fixing before the pages can be checked: `lab pages check` says what"]
    late, waiting = due(lab), unreviewed(lab)
    if not late and not waiting:
        return []
    out = ["", "Pages (revise what an answer touches, then a page reviewer passes it: lab-pages)"]
    out += [f"- {q} answered {d}: its pages are not revised yet (`lab pages cites {q}`)" for q, d in late]
    out += [f"- {p}: waits for a page reviewer" for p in waiting]
    return out


def listing(lab):
    """`lab pages`: every page with its kind and whether its last change was passed, then the answers due."""
    s = _require(lab)
    passed = passes(lab)
    out = []
    for kind in KINDS:
        pages = [p for p, k in sorted(s["kinds"].items()) if k == kind]
        if not pages:
            continue
        out += ["", f"{kind.capitalize()} ({len(pages)})"]
        for p in pages:
            state = "not there" if not files(lab, p) else "passed" if fingerprint(lab, p) in passed.get(p, set()) else \
                "waits for a page reviewer" if kind in REVIEWED else "changed since its last reading" if p in passed else "never read"
            out.append(f"- {p}: {state}")
    late = due(lab)
    out += ["", "Answers not yet in the pages"] + ([f"- {q} answered {d}" for q, d in late] or ["- none"])
    return "\n".join(out).strip()
