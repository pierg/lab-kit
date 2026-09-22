#!/usr/bin/env python3
"""Chronicle extractor for a lab — PROBEs, findings, claims and missions as timeline events.

The content-kit engine builds `content/chronicle.json` from every dated heading in the declared
record (generic), and loads this file through kit.json to add the lab's own vocabulary:

    "record": ["HISTORY.md", "QUESTIONS.md", "ops/", "record/", "experiments/*/PROBE.md"],
    "chronicle": { "extractors": ["kit/tools/chronicle_lab.py"] }

It declares its kinds (KINDS: experiment · finding · claim · mission, with the hues the timeline
draws them in) and its cards (CARDS: one per experiment, under the chronicle's Experiments tab).
The engine knows none of these words; they reach it only through this file.

What it emits, and from where:

  experiments    one per `experiments/<slug>/PROBE.md`: title (h1), question (the objective's
                 first paragraph, else the h1 after the dash), locked (`**Status: LOCKED <ts>**`,
                 else `**Date:**`, else the slug's date), status, kill rule (first line naming
                 a kill under a decision/kill heading), supersedes / superseded-by pointers from
                 the opening lines, and every finding whose Anchor points into the experiment.
  events[]       kind=experiment (the lock), kind=finding / kind=claim (a finding is dated by its
                 own `**Date:**` field, else by the commit that introduced the row, via git — by
                 the whole heading, then by the `## F-<n> ` prefix alone, which survives a
                 headline rewrite — else by its experiment's lock date; an undatable row is listed
                 on its experiment but not on the timeline), kind=mission (dated by the file name
                 `YYYYMMDD-…`).

A finding row is an interface: a plain headline plus Status · Tier · Date · Number · Bound ·
Why it matters · Anchor · Re-derive · Defense, with the long-form defense at the Defense path.
Every field is read here; the row's own Date is what keeps a rewritten headline from re-dating
the finding to the commit that rewrote it. **A field is canonical on its own line**; the inline
`**Status:** X · **Tier:** Y` spelling is accepted for Tier alone, because it is how every row
written before the layering spells it.

Dated headings *inside* missions and logbooks are the generic extractor's job, not this file's.

    python3 kit/tools/chronicle_lab.py --selftest    # planted fixtures, no lab needed
    python3 kit/tools/chronicle_lab.py [--root DIR]  # print what would be emitted
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date as _date  # `date` is a local variable in half the functions here
from pathlib import Path

# The three helpers this file shares with content-kit's chronicle, restated here so the tool runs
# standalone (--selftest, --root) whatever way the engine was installed. They must agree with
# ckit.chronicle.slugify / viewer_href and ckit.text.normalize: the record viewer computes the same
# anchors, so a link built here lands there.
_SLUG_BAD = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")


def slugify(text: str) -> str:
    return _SLUG_BAD.sub("-", text.lower()).strip("-")


def viewer_href(rel: str, anchor: str | None = None) -> str:
    return f"/shell/record.html?p={rel}" + (f"#{anchor}" if anchor else "")


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


# The vocabulary this extractor adds to the chronicle: its event kinds (drawn in these shell hues,
# all shown in the Story view) and its cards (the Experiments tab).
KINDS = [
    {"name": "experiment", "hue": "indigo"},
    {"name": "finding", "hue": "kept"},
    {"name": "claim", "hue": "blue"},
    {"name": "mission", "hue": "teal"},
]
CARDS = {"view": "experiments", "label": "Experiments", "kind": "experiment",
         "empty": "No experiments in this record — a lab pre-registers each one in experiments/<slug>/PROBE.md."}

H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
STATUS = re.compile(r"\*\*Status:\s*([A-Z][A-Z-]*)\b(?:\s+(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}Z)?))?")
DATE_FIELD = re.compile(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})")
SLUG_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})-")
ROW = re.compile(r"^##\s+((?:F|C)-\d+(?:\.\d+)*)\s*[·—–-]\s*(.+?)\s*$", re.M)
FIELD = re.compile(r"^\*\*(Status|Tier|Date|Number|Bound|Why it matters|Anchor|Re-derive|Defense):\*\*\s*(.+)$", re.M)
INLINE_TIER = "**Tier:**"  # the pre-layering spelling: `**Status:** BANKED · **Tier:** lab finding`
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUS_WORD = re.compile(r"[A-Z][A-Z-]+")  # first ALL-CAPS token, past any ~~/**/leading punctuation
SUPERSEDES = re.compile(r"\b[Ss]upersedes\b[:\s—–-]*`?([^`\n;]+?)(?:[.;]\s|`|$)")
SUPERSEDED_BY = re.compile(r"\b[Ss]uperseded[ -]by\b[:\s—–-]*`?([^`\n;]+?)(?:[.;]\s|`|$)")
MD_INLINE = re.compile(r"[`*_]+")
KILL_HEAD = re.compile(r"kill|decision", re.I)
KILL_LINE = re.compile(r"\bkill\b", re.I)
LEAD = re.compile(r"^\s*(?:[-*]\s*|\d+\.\s*)?(?:\*\*)?")
FINDING_ID = re.compile(r"\bF-\d+(?:\.\d+)*\b")
QHEAD = re.compile(r"^##\s+(Q(\d+)[^\n]*)$", re.M)
H2ANY = re.compile(r"^##\s+", re.M)
QSTATUS = re.compile(r"\*\*Status:\*\*\s*\**\s*([A-Z][A-Z-]+)")
QKILL = re.compile(r"\*\*Kill criterion[^*]*\*\*\s*(.+)")
SEP = re.compile(r"\s*[·:—–-]\s*")


def _plain(s: str, limit: int = 300) -> str:
    return normalize(MD_INLINE.sub("", s))[:limit]


def _iso_date(value: str) -> str | None:
    """`value` if it is a real calendar day spelled YYYY-MM-DD — `2026-13-45` is neither.

    The shape check comes first because date.fromisoformat also accepts `20260916` and full
    timestamps, and a chronicle event's date is a string the timeline compares literally.
    """
    if not ISO_DATE.match(value):
        return None
    try:
        _date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _git_env() -> dict[str, str]:
    """The environment minus git's own repository pointers.

    A hook, a `git rebase --exec` or a CI wrapper exports GIT_DIR / GIT_WORK_TREE /
    GIT_INDEX_FILE, and any git we run would then answer for *that* repository instead of the
    lab — reading the wrong history here, and, in the selftest, writing into the host repo.
    """
    return {k: v for k, v in os.environ.items()
            if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}


def _paragraph_after(lines: list[str], idx: int, limit: int = 300) -> str:
    buf: list[str] = []
    for ln in lines[idx + 1:]:
        s = ln.strip()
        if s.startswith("#"):
            break
        if not s:
            if buf:
                break
            continue
        buf.append(s)
    return _plain(" ".join(buf), limit)


def _git_first_date(root: Path, rel: str, needle: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--format=%cs", "-S", needle, "--", rel],
            cwd=root, env=_git_env(), capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    first = out.stdout.strip().splitlines()
    return first[0].strip() if first else None


def _git_first_date_by_id(root: Path, rel: str, ident: str) -> str | None:
    """The same pickaxe on the row's id prefix alone — `## F-7 ` outlives its headline.

    A ledger-wide rewrite (layering the rows, say) changes every heading text at once, so the
    whole-heading pickaxe would date every finding to the rewrite commit. The id prefix does not
    change, so it still finds the commit that first introduced the row. The needle stops at the
    space after the id rather than at a separator, because a ledger may punctuate its headings
    with any of `· — – -`; the trailing space is what keeps `## F-7 ` out of `## F-70 `.
    """
    return _git_first_date(root, rel, f"## {ident} ")


# ----------------------------------------------------------------------------- PROBEs

def _slug_date(slug: str) -> str | None:
    m = SLUG_DATE.match(slug)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def parse_probe(root: Path, probe: Path) -> dict:
    slug = probe.parent.name
    rel = probe.relative_to(root).as_posix()
    text = probe.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    h1 = H1.search(text)
    title = _plain(h1.group(1), 200) if h1 else slug
    head = "\n".join(lines[:15])
    st = STATUS.search(head)
    status = st.group(1) if st else ""
    locked = (st.group(2) if st and st.group(2) else None) or \
             (DATE_FIELD.search(head).group(1) if DATE_FIELD.search(head) else None) or _slug_date(slug)

    question = ""
    kill_rule = ""
    for i, ln in enumerate(lines):
        m = HEADING.match(ln)
        if not m:
            continue
        htext = m.group(2)
        if not question and re.search(r"objective|question", htext, re.I):
            question = _paragraph_after(lines, i)
        if not kill_rule and KILL_HEAD.search(htext):
            for ln2 in lines[i + 1:]:
                if HEADING.match(ln2):
                    break
                if KILL_LINE.search(ln2):
                    kill_rule = _plain(LEAD.sub("", ln2))
                    break
    if not question and h1 and " — " in h1.group(1):
        question = _plain(re.sub(r"\s*\((?:LOCKED|DRAFT)[^)]*\)\s*$", "", h1.group(1).split(" — ", 1)[1]))
    if not kill_rule:
        for ln in lines:
            if re.search(r"kill (rule|test|criterion)", ln, re.I):
                kill_rule = _plain(LEAD.sub("", ln))
                break

    sup = SUPERSEDES.search(head)
    supby = SUPERSEDED_BY.search(head)
    return {
        "slug": slug, "title": title, "question": question, "locked": locked or "",
        "status": status, "kill_rule": kill_rule, "href": viewer_href(rel),
        "supersedes": _plain(sup.group(1), 160) if sup else "",
        "superseded_by": _plain(supby.group(1), 160) if supby else "",
        "findings": [],
    }


# ----------------------------------------------------------------------------- rows

def parse_rows(root: Path, rel: str) -> list[dict]:
    p = root / rel
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    heads = list(ROW.finditer(text))
    rows = []
    for i, m in enumerate(heads):
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        fields = {f.group(1): f.group(2).strip() for f in FIELD.finditer(body)}
        status_raw = fields.get("Status") or ""
        sm = STATUS_WORD.search(status_raw.split("·")[0])
        # Line-anchored fields are canonical; every row written before the layering spells its
        # tier inline, at the end of the Status line, so read it from there when it is absent —
        # bounded and stripped of markup, because a legacy tier runs to a paragraph.
        tier = fields.get("Tier") or (
            _plain(status_raw.split(INLINE_TIER, 1)[1], 120) if INLINE_TIER in status_raw else "")
        rows.append({
            "id": m.group(1), "title": _plain(m.group(2), 200),
            "status": sm.group(0) if sm else "",
            "tier": tier,
            "date": fields.get("Date", ""),
            "number": fields.get("Number", ""),
            "bound": fields.get("Bound", ""),
            "why": fields.get("Why it matters", ""),
            "anchor": fields.get("Anchor", ""),
            # the long-form defense — predictions as scored, the review, the anomalies
            "defense": fields.get("Defense", ""),
            # F-/C- headings anchor on the bare id in shell/record.html (#F-7, #C-1) — not the slug
            "href": viewer_href(rel, m.group(1)),
            "line": text.count("\n", 0, m.start()) + 1,
            "heading": m.group(0),
        })
    return rows


# ----------------------------------------------------------------------------- missions

def parse_missions(root: Path, cfg: dict) -> list[dict]:
    d = root / "ops" / "missions"
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.md")):
        date = _slug_date(p.name)
        if not date:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        h1 = H1.search(text)
        title = _plain(h1.group(1), 200) if h1 else p.stem
        idx = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), 0)
        rel = p.relative_to(root).as_posix()
        out.append({"date": date, "kind": "mission", "title": title,
                    "summary": _paragraph_after(lines, idx, 240), "href": viewer_href(rel),
                    "source": rel, "links": []})
    return out


# ----------------------------------------------------------------------------- claims / questions (dashboard)

def _fids(body: str) -> list[str]:
    seen = dict.fromkeys(FINDING_ID.findall(body))  # first-seen order, de-duped
    return sorted(seen, key=lambda x: [int(n) for n in re.findall(r"\d+", x)])


def parse_claims(root: Path, rel: str) -> list[dict]:
    """Each `## C-<n>` row: id, title, the findings it rests on, its heading href."""
    p = root / rel
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    heads = list(ROW.finditer(text))
    out = []
    for i, m in enumerate(heads):
        if not m.group(1).startswith("C-"):
            continue
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        out.append({
            "id": m.group(1), "title": _plain(m.group(2), 200), "rests_on": _fids(body),
            # F-/C- headings anchor on the bare id in shell/record.html (#F-7, #C-1) — not the slug
            "href": viewer_href(rel, m.group(1)),
        })
    return out


def parse_questions(root: Path, rel: str) -> list[dict]:
    """Each `## Q<n>` section: id, title, first-order status word, kill criterion, href.

    Status is the first `**Status:**` word of the section — a question whose live meaning is
    carried in a later dated annotation (e.g. a fired conjunct) still reads at its first-order
    status here; the full nuance is one click away in QUESTIONS.md.
    """
    p = root / rel
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    h2s = [mm.start() for mm in H2ANY.finditer(text)]
    out = []
    for m in QHEAD.finditer(text):
        full = m.group(1).strip()
        end = next((s for s in h2s if s > m.start()), len(text))
        section = text[m.end():end]
        st = QSTATUS.search(section)
        kill = QKILL.search(section)
        parts = SEP.split(full, 1)
        title = parts[1] if len(parts) > 1 else full
        out.append({
            "id": "Q" + m.group(2), "title": _plain(title, 200),
            "status": st.group(1) if st else "",
            "kill": _plain(kill.group(1), 280) if kill else "",
            "href": viewer_href(rel, slugify(MD_INLINE.sub("", full))),
        })
    return out


def ladder(root: Path, cfg: dict) -> dict:
    """The status-board view (content-kit's ladder.py calls this): findings, claims, questions.

    Experiments, the "now" banner and the decisions feed are generic and come from the
    engine + extract(); this adds the lab's F-/C-/Q- vocabulary.
    """
    root = Path(root)
    findings = [
        {"id": r["id"], "title": r["title"], "status": r["status"], "href": r["href"]}
        for r in parse_rows(root, cfg.get("findings", "record/findings.md"))
        if r["id"].startswith("F-")
    ]
    return {
        "findings": findings,
        "claims": parse_claims(root, cfg.get("claims", "record/claims.md")),
        "questions": parse_questions(root, cfg.get("questions", "QUESTIONS.md")),
    }


# ----------------------------------------------------------------------------- entry point

def _collect(root: Path, cfg: dict) -> tuple[list[dict], list[dict]]:
    """(experiments with their anchored findings, timeline events)."""
    root = Path(root)
    findings_rel = cfg.get("findings", "record/findings.md")
    claims_rel = cfg.get("claims", "record/claims.md")
    experiments = [parse_probe(root, p) for p in sorted(root.glob("experiments/*/PROBE.md"))]
    by_slug = {x["slug"]: x for x in experiments}
    events: list[dict] = []

    for x in experiments:
        if x["locked"]:
            events.append({"date": x["locked"], "kind": "experiment",
                           "title": f"{x['title']} — locked" if x["status"] == "LOCKED" else f"{x['title']} — {x['status'].lower() or 'pre-registered'}",
                           "summary": x["question"], "href": x["href"], "source": f"experiments/{x['slug']}/PROBE.md",
                           "links": [{"label": f"experiments/{x['slug']}/", "href": x["href"]}],
                           "experiment": x["slug"]})

    for f in parse_rows(root, findings_rel):
        slug = next((s for s in by_slug if f"experiments/{s}/" in f["anchor"]), None)
        if slug:
            by_slug[slug]["findings"].append({"id": f["id"], "title": f["title"], "status": f["status"], "href": f["href"]})
        # The row's own Date is authoritative — git archaeology is the fallback for rows that
        # predate the field, and a ledger-wide headline rewrite must not re-date the finding.
        date = _iso_date(f["date"]) \
            or _git_first_date(root, findings_rel, f["heading"]) \
            or _git_first_date_by_id(root, findings_rel, f["id"]) \
            or (by_slug[slug]["locked"] if slug else None)
        if date:
            ev = {"date": date, "kind": "finding", "title": f"{f['id']} · {f['title']}",
                  "summary": f"{f['status']}" + (f" · anchored in experiments/{slug}/" if slug else ""),
                  "href": f["href"], "source": findings_rel, "links": []}
            if slug:
                ev["experiment"] = slug
                ev["links"].append({"label": f"experiments/{slug}/", "href": by_slug[slug]["href"]})
            events.append(ev)

    for c in parse_rows(root, claims_rel):
        date = _git_first_date(root, claims_rel, c["heading"])
        if date:
            events.append({"date": date, "kind": "claim", "title": f"{c['id']} · {c['title']}",
                           "summary": "", "href": c["href"], "source": claims_rel, "links": []})

    events.extend(parse_missions(root, cfg))
    experiments.sort(key=lambda x: (x.get("locked") or "", x["slug"]), reverse=True)
    return experiments, events


def experiments(root: Path, cfg: dict) -> list[dict]:
    """Every pre-registration, newest lock first, each with the findings anchored in it — the
    shape the dashboard's pipeline panel reads (tools/ladder.py)."""
    return _collect(root, cfg)[0]


def card(x: dict) -> dict:
    """One experiment as a chronicle card: the fields the Experiments tab has always shown."""
    fields: list[dict] = []
    if x["question"]:
        fields.append({"label": "Question", "text": x["question"]})
    if x["kill_rule"]:
        fields.append({"label": "Kill rule", "text": x["kill_rule"]})
    fields.append({"label": "Pre-registration", "link": {"label": f"{x['slug']}/PROBE.md", "href": x["href"]}})
    if x["supersedes"]:
        fields.append({"label": "Supersedes", "text": x["supersedes"]})
    if x["superseded_by"]:
        fields.append({"label": "Superseded by", "text": x["superseded_by"]})
    fields.append({"label": "Findings", "empty": "none anchored in this experiment yet",
                   "items": [{"chip": f["status"] or "finding", "kind": "finding", "label": f["id"],
                              "href": f["href"], "text": f["title"]} for f in x["findings"]]})
    return {"title": x["title"], "href": x["href"], "date": x["locked"], "status": x["status"],
            "slug": x["slug"], "fields": fields}


def extract(root: Path, cfg: dict) -> dict:
    exps, events = _collect(root, cfg)
    return {"events": events, "cards": [card(x) for x in exps]}


# ----------------------------------------------------------------------------- selftest

PROBE_FIXTURE = """# E9 — does the planted rule fire? (LOCKED)

**Status: LOCKED 2026-09-03T10:00Z** by the commander. Supersedes `experiments/20260901-e8-old/`.

## 1. Objective

Whether a planted fixture with a known answer is reported by name.

## 9. Decision Rules

- **Kill rule:** if fewer than 3 of 5 fire, the extractor is not a check.
"""

FINDINGS_FIXTURE = """# Findings — LIVE

## F-7 · the planted rule fires 5/5

**Status:** BANKED · **Tier:** lab finding
**Anchor:** `experiments/20260903-e9-planted/out/summary.tsv`
**Re-derive:** `cat experiments/20260903-e9-planted/out/summary.tsv`

## F-8 · an unanchored observation

**Status:** PROVISIONAL
**Anchor:** `record/logbook/lab.md`
**Re-derive:** `true`

## F-9 · the planted rule fires on a second substrate

**Status:** BANKED
**Tier:** reviewer-gated
**Date:** 2026-09-01
**Number:** 5 of 5 planted rules fire, against 0 of 5 for the control
**Bound:** one fixture, one extractor — it licenses nothing about a real ledger.
**Why it matters:** a row dated by git alone re-dates itself whenever its headline is rewritten.
**Anchor:** `experiments/20260903-e9-planted/out/summary.tsv`
**Re-derive:** `cat experiments/20260903-e9-planted/out/summary.tsv`
**Defense:** `record/findings/F-9.md`

## F-10 · a row whose date is not a day of any calendar

**Status:** BANKED
**Date:** 2026-13-45
**Anchor:** `experiments/20260903-e9-planted/out/summary.tsv`
**Re-derive:** `true`
"""

MISSION_FIXTURE = "# Mission 20260902-planted — LIVE (executing)\n\n**Objective:** prove the fixture.\n"

QUESTIONS_FIXTURE = """# Questions — LIVE

## Q1 · does the planted question parse?

**Status:** OPEN · the opening question.

**Kill criterion:** if the fixture does not parse, the extractor is wrong.

## Q2 · a killed question

**Status:** KILLED 2026-09-01 by the fixture.

## Answered

| Question | Answer | Finding |
|---|---|---|
| something | yes | F-7 |
"""

CLAIMS_FIXTURE = """# Claims — LIVE

## C-1 · the planted claim

**Licensed:** "something true."
Rests on F-7 and F-8. **Bound:** narrow.
"""


REWRITE_FIXTURE = """# Findings — LIVE

## F-3 — {headline}

**Status:** BANKED
**Anchor:** `record/findings.md`
**Re-derive:** `true`
"""


def _selftest_git_rewrite(root: Path) -> list[str]:
    """A real ledger: the row is planted, its headline is rewritten, then rewritten again in the
    working tree without being committed.

    This is the case the Date field exists for — the whole-heading pickaxe dates the row by
    whichever commit last wrote its current headline, and sees nothing at all while the rewrite is
    still uncommitted (which is exactly when the chronicle is regenerated). The row here carries no
    Date, so it exercises the id-prefix fallback instead; its heading is punctuated with an em dash
    rather than a middle dot, because the fallback must not depend on which separator a lab uses.

    It also runs under a deliberately bogus inherited GIT_DIR. Without the scrub in `_git_env`,
    these commits would land in whatever repository that variable names — the host's, when this
    runs from a git hook — while the selftest still printed ok.
    """
    rel = "record/findings.md"
    (root / "record").mkdir(parents=True)
    bogus = root / "not-the-repo" / ".git"
    keys = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
    prior = {k: os.environ.get(k) for k in keys}
    os.environ.update(GIT_DIR=str(bogus), GIT_WORK_TREE=str(bogus.parent),
                      GIT_INDEX_FILE=str(bogus / "index"))
    try:
        env = _git_env()  # the scrub under test: the pointers above must not survive it

        def git(*args: str, when: str | None = None) -> None:
            if when:
                env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
            subprocess.run(["git", "-c", "user.email=kit@example.org", "-c", "user.name=kit",
                            "-c", "commit.gpgsign=false", *args],
                           cwd=root, env=env, check=True, capture_output=True)

        return _rewrite_case(root, rel, bogus, git)
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _rewrite_case(root: Path, rel: str, bogus: Path, git) -> list[str]:
    git("init", "-q")
    (root / rel).write_text(REWRITE_FIXTURE.format(headline="the original headline"), encoding="utf-8")
    git("add", rel)
    git("commit", "--no-verify", "-q", "-m", "plant the row", when="2026-05-05T12:00:00+00:00")
    (root / rel).write_text(REWRITE_FIXTURE.format(headline="a rewritten headline"), encoding="utf-8")
    git("commit", "--no-verify", "-aq", "-m", "layer the ledger", when="2026-07-07T12:00:00+00:00")
    (root / rel).write_text(REWRITE_FIXTURE.format(headline="a headline not yet committed"), encoding="utf-8")

    failures = []
    if not (root / ".git").is_dir():
        failures.append("the inherited GIT_DIR was not scrubbed — git wrote somewhere else")
    if bogus.exists():
        failures.append(f"the bogus inherited GIT_DIR was written to: {bogus}")
    if _git_first_date(root, rel, "## F-3 — a rewritten headline") != "2026-07-07":
        failures.append("the whole-heading pickaxe does not date the rewrite (fixture is wrong)")
    if _git_first_date_by_id(root, rel, "F-3") != "2026-05-05":
        failures.append("the id-prefix pickaxe did not find the commit that introduced the row")
    ev = next((e for e in extract(root, {})["events"] if e["kind"] == "finding"), None)
    if not ev or ev["date"] != "2026-05-05":
        failures.append(f"an uncommitted headline rewrite re-dated the finding: {ev}")
    return failures


def selftest() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "experiments" / "20260903-e9-planted").mkdir(parents=True)
        (root / "experiments" / "20260903-e9-planted" / "PROBE.md").write_text(PROBE_FIXTURE, encoding="utf-8")
        (root / "experiments" / "20260830-draft-only").mkdir()
        (root / "experiments" / "20260830-draft-only" / "PROBE.md").write_text(
            "# D1 — a draft\n\n**Date:** 2026-08-30 · **Status: DRAFT**\n", encoding="utf-8")
        (root / "record").mkdir()
        (root / "record" / "findings.md").write_text(FINDINGS_FIXTURE, encoding="utf-8")
        (root / "record" / "claims.md").write_text(CLAIMS_FIXTURE, encoding="utf-8")
        (root / "QUESTIONS.md").write_text(QUESTIONS_FIXTURE, encoding="utf-8")
        (root / "ops" / "missions").mkdir(parents=True)
        (root / "ops" / "missions" / "20260902-planted.md").write_text(MISSION_FIXTURE, encoding="utf-8")
        (root / "ops" / "missions" / "TEMPLATE.md").write_text("# Mission <id>\n", encoding="utf-8")
        out = extract(root, {})
        ex = {x["slug"]: x for x in experiments(root, {})}
        e9 = ex.get("20260903-e9-planted")
        if not e9:
            failures.append("PROBE not found")
        else:
            if e9["locked"] != "2026-09-03T10:00Z" or e9["status"] != "LOCKED":
                failures.append(f"lock not parsed: {e9['locked']!r} {e9['status']!r}")
            if not e9["question"].startswith("Whether a planted fixture"):
                failures.append(f"question not taken from the objective: {e9['question']!r}")
            if "fewer than 3 of 5" not in e9["kill_rule"]:
                failures.append(f"kill rule not found: {e9['kill_rule']!r}")
            if "20260901-e8-old" not in e9["supersedes"]:
                failures.append(f"supersedes pointer not parsed: {e9['supersedes']!r}")
            if [f["id"] for f in e9["findings"]] != ["F-7", "F-9", "F-10"] or e9["findings"][0]["status"] != "BANKED":
                failures.append(f"anchored finding not attached: {e9['findings']}")
            if e9["findings"][0]["href"] != "/shell/record.html?p=record/findings.md#F-7":
                failures.append(f"finding href does not land on its bare-id anchor: {e9['findings'][0]['href']}")
        d1 = ex.get("20260830-draft-only")
        if not d1 or d1["locked"] != "2026-08-30" or d1["status"] != "DRAFT":
            failures.append(f"draft PROBE: Date field / status not parsed: {d1}")
        kinds = sorted(e["kind"] for e in out["events"])
        # no git in the temp dir: F-7 and F-10 (whose Date is not a real day) fall back to their
        # experiment's lock date, F-9 carries its own Date, F-8 has neither → listed nowhere
        if kinds != ["experiment", "experiment", "finding", "finding", "finding", "mission"]:
            failures.append(f"event kinds: {kinds}")
        f7 = next((e for e in out["events"] if e["kind"] == "finding"), None)
        if not f7 or f7["date"] != "2026-09-03T10:00Z" or f7.get("experiment") != "20260903-e9-planted":
            failures.append(f"finding event not dated by its experiment's lock: {f7}")
        mi = next((e for e in out["events"] if e["kind"] == "mission"), None)
        if not mi or mi["date"] != "2026-09-02" or "prove the fixture" not in mi["summary"]:
            failures.append(f"mission not parsed from its file name / objective: {mi}")
        if any("TEMPLATE" in e["title"] for e in out["events"]):
            failures.append("the mission TEMPLATE must not become an event")
        # --- the cards: one per experiment, newest lock first, the fields the tab has always shown
        cards = {c["slug"]: c for c in out["cards"]}
        c9 = cards.get("20260903-e9-planted", {})
        labels = [f["label"] for f in c9.get("fields", [])]
        if labels != ["Question", "Kill rule", "Pre-registration", "Supersedes", "Findings"]:
            failures.append(f"experiment card fields wrong: {labels}")
        elif [x["label"] for x in c9["fields"][-1]["items"]] != ["F-7", "F-9", "F-10"] \
                or c9["fields"][-1]["items"][0]["chip"] != "BANKED":
            failures.append(f"a card's findings must carry id, status chip and link: {c9['fields'][-1]}")
        if [c["slug"] for c in out["cards"]] != [x["slug"] for x in experiments(root, {})]:
            failures.append("cards must come in the experiments' order (newest lock first)")
        if {k["name"] for k in KINDS} != {"experiment", "finding", "claim", "mission"} or CARDS["view"] != "experiments":
            failures.append(f"KINDS / CARDS must declare the lab's vocabulary: {KINDS} {CARDS}")

        # --- the layered row: the interface fields are read, and the row dates itself
        rows = {r["id"]: r for r in parse_rows(root, "record/findings.md")}
        f9 = rows.get("F-9", {})
        layered = {k: f9.get(k) for k in ("tier", "date", "number", "bound", "why", "defense")}
        if layered != {"tier": "reviewer-gated", "date": "2026-09-01",
                       "number": "5 of 5 planted rules fire, against 0 of 5 for the control",
                       "bound": "one fixture, one extractor — it licenses nothing about a real ledger.",
                       "why": "a row dated by git alone re-dates itself whenever its headline is rewritten.",
                       "defense": "`record/findings/F-9.md`"}:
            failures.append(f"layered fields not parsed: {layered}")
        if rows.get("F-7", {}).get("defense") != "" or rows.get("F-7", {}).get("date") != "":
            failures.append(f"an unlayered row must read as empty strings, not None: {rows.get('F-7')}")
        # the pre-layering spelling — `**Status:** BANKED · **Tier:** lab finding` on one line
        if rows.get("F-7", {}).get("tier") != "lab finding" or rows.get("F-7", {}).get("status") != "BANKED":
            failures.append(f"an inline legacy Tier was not read: {rows.get('F-7')}")
        # git is never consulted here (no repo in the temp dir), and the row's Date must win over
        # the lock date of the experiment it is anchored in (2026-09-03).
        ev9 = next((e for e in out["events"] if e["title"].startswith("F-9 ")), None)
        if not ev9 or ev9["date"] != "2026-09-01":
            failures.append(f"the row's own **Date:** did not date its event: {ev9}")
        # 2026-13-45 is the right shape and no day at all: it must not reach the timeline
        ev10 = next((e for e in out["events"] if e["title"].startswith("F-10 ")), None)
        if not ev10 or ev10["date"] != "2026-09-03T10:00Z":
            failures.append(f"an impossible **Date:** was taken at face value: {ev10}")

        # --- ladder(): the status-board view — questions, findings, claims
        lad = ladder(root, {})
        qids = [q["id"] for q in lad["questions"]]
        qs = {q["id"]: q for q in lad["questions"]}
        if qids != ["Q1", "Q2"]:
            failures.append(f"questions not parsed in order: {qids}")
        elif qs["Q1"]["status"] != "OPEN" or not qs["Q1"]["kill"].startswith("if the fixture does not parse"):
            failures.append(f"Q1 status/kill wrong: {qs['Q1']}")
        elif qs["Q2"]["status"] != "KILLED":
            failures.append(f"Q2 first-order status wrong: {qs['Q2']}")
        elif not qs["Q1"]["href"].startswith("/shell/record.html?p=QUESTIONS.md#q1-"):
            failures.append(f"question href does not land on its heading: {qs['Q1']['href']}")
        fids = [f["id"] for f in lad["findings"]]
        if fids != ["F-7", "F-8", "F-9", "F-10"] or lad["findings"][0]["status"] != "BANKED":
            failures.append(f"ladder findings wrong: {lad['findings']}")
        # the status board takes four keys and no more — layering a row must not widen it
        elif sorted(lad["findings"][0]) != ["href", "id", "status", "title"]:
            failures.append(f"ladder finding projection widened: {sorted(lad['findings'][0])}")
        # F-/C- links must land on the bare-id anchor shell/record.html assigns (not the slug)
        elif not lad["findings"][0]["href"].endswith("#F-7"):
            failures.append(f"ladder finding href not a bare-id anchor: {lad['findings'][0]['href']}")
        if not lad["claims"] or lad["claims"][0]["id"] != "C-1" or lad["claims"][0]["rests_on"] != ["F-7", "F-8"]:
            failures.append(f"claim rests_on not parsed: {lad['claims']}")
        elif not lad["claims"][0]["href"].endswith("#C-1"):
            failures.append(f"ladder claim href not a bare-id anchor: {lad['claims'][0]['href']}")

        # --- a row with no Date, in a real repo, whose headline was rewritten
        failures += _selftest_git_rewrite(root / "rewritten")  # its own repo, inside the temp dir
    if failures:
        print("chronicle_lab selftest FAILED:\n- " + "\n- ".join(failures))
        return 1
    print("chronicle_lab selftest ok (35 planted assertions)")
    return 0


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    root = (args.root or Path.cwd()).resolve()
    marker = next((root / m for m in ("kit.json", "lab.json") if (root / m).is_file()), None)
    cfg = json.loads(marker.read_text()) if marker else {}
    out = extract(root, cfg)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
