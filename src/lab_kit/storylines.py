"""Storylines: the library's pages that each argue one line of the lab's findings, above a record that names no storyline.

A storyline is what a paper, a talk or a report will be written from; it is the argument, not the artifact.

A lab opts in with `[storylines]` in `lab.toml`: `overview`, the page that keeps the whole trail, and `active`, the page
of each storyline being written. Each storyline page opens with a scope table whose cells are marked
`data-scope="included"`, `"excluded"` and `"open"`; the `/lab/<id>/` links inside a cell are what it lists.
`lab check` holds what a cell may list, and `lab now` says what each storyline still has open and which live steps
serve no storyline.
"""
from __future__ import annotations

import os, re
from html.parser import HTMLParser

from . import record as R

ROWS = ("included", "excluded", "open")
LINK = re.compile(r"^/lab/(G\d+(?:\.Q\d+(?:\.\d+)?)?|D\d+)/?(?:[#?].*)?$")
LIVE = ("open", "waiting", "running")


class _Scope(HTMLParser):
    """The page's title and, for each marked cell, the ids its links name, in order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.cells, self.marked, self.unknown = "", {r: [] for r in ROWS}, set(), []
        self._title, self._row, self._tag, self._depth, self._tables = False, None, None, 0, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._title = True
        if self._row and ("data-scope" in a or (self._depth == 1 and not self._tables and self._tag in ("td", "th") and tag in ("td", "th", "tr"))):
            self._row = None  # a cell whose closing tag is left out ends where the next cell or row begins
        if self._row:
            self._depth += tag == self._tag
            self._tables += tag == "table"  # a table inside the cell has rows and cells of its own
            m = LINK.match(a.get("href") or "") if tag == "a" else None
            if m and m.group(1) not in self.cells[self._row]:
                self.cells[self._row].append(m.group(1))
            return
        row = a.get("data-scope")
        if row is None:
            return
        if row not in ROWS:
            self.unknown.append(row)
            return
        self._row, self._tag, self._depth, self._tables = row, tag, 1, 0
        self.marked.add(row)

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
        if self._row and tag == "table" and self._tables:
            self._tables -= 1
        if self._row and tag == self._tag:
            self._depth -= 1
            if not self._depth:
                self._row = None

    def handle_data(self, data):
        if self._title:
            self.title += data


def page_file(lab, path):
    return os.path.join(lab.root, lab.cfg.get("library", "docs"), "content", path.strip("/"), "index.html")


def config(lab):
    """(overview, active pages, problems). (None, [], []) when the lab keeps no storylines."""
    p = lab.cfg.get("storylines")
    if p is None:
        return None, [], []
    if not isinstance(p, dict):
        return None, [], ["`[storylines]` is a table that names `overview` and `active`"]
    problems = [f"`[storylines]` holds `{k}`; it names only `overview` and `active`" for k in sorted(set(p) - {"overview", "active"})]
    overview, active = p.get("overview"), p.get("active", [])
    if not isinstance(overview, str) or not overview.strip():
        problems.append("`[storylines]` names its `overview`: the library page that keeps the whole trail, such as \"entries/where-the-results-stand\"")
        overview = None
    if not isinstance(active, list) or not all(isinstance(a, str) and a.strip() for a in active):
        problems.append("`[storylines]` lists its `active` storyline pages as library paths, such as [\"entries/storyline-a\"]")
        active = []
    active = [a.strip("/") for a in active]
    for path in ([overview] if overview else []) + active:
        if ".." in path.split("/"):
            problems.append(f"`[storylines]` names {path}; a page is a path inside the library's content, without `..`")
    for a in sorted({a for a in active if active.count(a) > 1}):
        problems.append(f"`[storylines]` lists {a} more than once")
    return (overview.strip("/") if overview else None), list(dict.fromkeys(active)), problems


def read(lab):
    """Each active storyline page as read: path, title, its cells' ids, the rows it marks; `missing` when not there."""
    if getattr(lab, "_storylines", None) is not None:
        return lab._storylines
    _, active, _ = config(lab)
    out = []
    for path in active:
        f = page_file(lab, path)
        if not os.path.exists(f):
            out.append({"path": path, "title": path, "cells": {r: [] for r in ROWS}, "marked": set(), "unknown": [], "missing": True})
            continue
        s = _Scope()
        s.feed(R.read(f))
        out.append({"path": path, "title": " ".join(s.title.split()) or path, "cells": s.cells, "marked": s.marked, "unknown": s.unknown, "missing": False})
    lab._storylines = out
    return out


def _covered(lab, ident):
    """The ids a cell's id stands for: itself, and every question and step under a goal or a question."""
    n = lab.nodes.get(ident)
    if not n:
        return {ident}
    if n["type"] == "goal":
        return {ident} | {q["id"] for q in n.get("questions", [])} | {x["id"] for q in n.get("questions", []) for x in q["items"]}
    if n["type"] == "question":
        return {ident} | {x["id"] for x in n["items"]}
    return {ident}


def serving(lab):
    """The live steps that no active storyline lists under included or open, by themselves or by their question or goal."""
    named = set()
    for p in read(lab):
        for row in ("included", "open"):
            for i in p["cells"][row]:
                named |= _covered(lab, lab.folded.get(i, i))
    return [x for x in lab.items if x["state"] in LIVE and not {x["id"], x["question"], x.get("goal")} & named]


def _say(n):
    return "void: its results review failed, so no page uses its numbers" if n.get("label") == "void" else n["state"]


def check(lab, bad, notes):
    """What `lab check` holds about the storylines: the table in `lab.toml`, each page's scope, and what each row lists."""
    overview, active, problems = config(lab)
    for p in problems:
        bad("storylines", "lab.toml", p)
    if overview is None and not active:
        return
    if overview and not os.path.exists(page_file(lab, overview)):
        bad("storylines", "lab.toml", f"`overview` names {overview}, which is not a page of the library")
    if overview and overview in active:
        bad("storylines", "lab.toml", f"{overview} is the overview and an active storyline: the overview keeps the whole trail, a storyline only what it argues")
    for p in read(lab):
        where = lab.rel(page_file(lab, p["path"]))
        if p["missing"]:
            bad("storylines", "lab.toml", f"`active` names {p['path']}, which is not a page of the library")
            continue
        for row in ROWS:
            if row not in p["marked"]:
                bad("storylines", where, f"has no scope cell marked data-scope=\"{row}\": a storyline page opens with its scope table, and each of included, excluded and open is a marked cell, empty if it lists nothing")
        for row in p["unknown"]:
            bad("storylines", where, f"marks a cell data-scope=\"{row}\"; a scope cell is included, excluded or open")
        rows = {row: [lab.folded.get(i, i) for i in p["cells"][row]] for row in ROWS}
        for row, ids in rows.items():
            for i in ids:
                n = lab.nodes.get(i)
                if not n:
                    bad("storylines", where, f"lists {i} under {row}, which is not a goal, a question, a step or a decision of the lab")
                    continue
                if row == "included":
                    if n["type"] in R.STEPS and (n["state"] != "done" or n.get("label") == "void"):
                        to = "open" if n["state"] in LIVE else "excluded"
                        bad("storylines", where, f"lists {i} under included, which is {_say(n)}: a storyline includes only finished work that is not void, replaced or dropped; list it under {to}")
                    elif n["type"] in ("question", "goal") and n["state"] in ("parked", "dropped"):
                        bad("storylines", where, f"lists {i} under included, which is {n['state']}: list it under excluded")
                elif row == "open":
                    if n["type"] in R.STEPS and n["state"] not in LIVE:
                        to = "included or excluded" if n["state"] == "done" and n.get("label") != "void" else "excluded"
                        bad("storylines", where, f"lists {i} under open, which is {_say(n)}: open holds only work still to do; list it under {to}")
                    elif n["type"] in ("question", "goal") and n["state"] in ("done", "parked", "dropped"):
                        bad("storylines", where, f"lists {i} under open, which is {n['state']}: open holds only work still to do")
        for a, b in (("included", "excluded"), ("included", "open"), ("open", "excluded")):
            for i in sorted(i for i in set(rows[a]) & set(rows[b]) if lab.nodes.get(i, {}).get("type") != "decision"):  # a decision may be cited wherever it explains a row
                bad("storylines", where, f"lists {i} under both {a} and {b}: a step or a question has one row; where another row needs it, name it in words, without its link")
    for q, step, at in stale(lab):
        notes.append(f"storylines: {q} was last committed before the result of {step} ({at}): bring the storyline's argument up to date with it")


def stale(lab):
    """[(page, step, when)]: an active storyline page last committed before the newest `result` line about a step it lists
    under included or open, or under a question or goal it lists there. Nothing where git cannot tell."""
    from . import history
    root, out = lab.root, []
    if not history.committed(root):
        return out
    for p in read(lab):
        if p["missing"]:
            continue
        f = os.path.relpath(page_file(lab, p["path"]), root)
        if (history.git(root, "status", "--porcelain", "--", f) or "").strip():
            continue  # being brought up to date now
        last = R.moment((history.git(root, "log", "-1", "--format=%cI", "--", f) or "").strip())
        if not last:
            continue
        mine = set()
        for row in ("included", "open"):
            for i in p["cells"][row]:
                mine |= _covered(lab, lab.folded.get(i, i))
        newer = [l for l in lab.lines if l["kind"] == "result" and l["about"] in mine and l["time"] and (R.moment(l["at"]) or last) > last]
        if newer:
            out.append((p["path"], newer[-1]["about"], f"{newer[-1]['day']} {newer[-1]['time']}"))
    return out


def now_lines(lab):
    """The lines `lab now` gives the storylines: each active storyline with what it has open, then the steps no storyline serves."""
    _, active, _ = config(lab)
    if not active:
        return []
    out = ["", "Storylines (direction comes from their open rows and their criticisms)"]
    for p in read(lab):
        if p["missing"]:
            out.append(f"- {p['path']}: not in the library")
            continue
        left = [lab.nodes[i] for i in (lab.folded.get(i, i) for i in p["cells"]["open"]) if i in lab.nodes and lab.nodes[i]["type"] != "decision"]
        todo = ", ".join(f"{n['id']} {n['title']} ({n['state']})" for n in left) or "nothing"
        out.append(f"- {p['title']} ({p['path']}): open {todo}")
    idle = serving(lab)
    if idle:
        out += ["", "Serving no active storyline (add to a storyline's open row, or bring parking or dropping it to the operator)"]
        out += [f"- {x['id']} {x['title']} ({x['state']})" for x in idle]
    return out
