#!/usr/bin/env python3
"""Chronicle extractor for a lab — PROBEs, findings, claims and missions as timeline events.

The content-kit engine builds `content/chronicle.json` from every dated heading in the declared
record (generic), and loads this file through lab.json to add the lab's own vocabulary:

    "record": ["HISTORY.md", "QUESTIONS.md", "ops/", "record/", "experiments/*/PROBE.md"],
    "chronicle": { "extractors": ["kit/tools/chronicle_lab.py"] }

What it emits, and from where:

  experiments[]  one per `experiments/<slug>/PROBE.md`: title (h1), question (the objective's
                 first paragraph, else the h1 after the dash), locked (`**Status: LOCKED <ts>**`,
                 else `**Date:**`, else the slug's date), status, kill rule (first line naming
                 a kill under a decision/kill heading), supersedes / superseded-by pointers from
                 the opening lines, and every finding whose Anchor points into the experiment.
  events[]       kind=experiment (the lock), kind=finding / kind=claim (dated by the commit
                 that introduced the row, via git; a finding falls back to its experiment's lock
                 date; an undatable row is listed on its experiment but not on the timeline),
                 kind=mission (dated by the file name `YYYYMMDD-…`).

Dated headings *inside* missions and logbooks are the generic extractor's job, not this file's.

    python3 kit/tools/chronicle_lab.py --selftest    # planted fixtures, no lab needed
    python3 kit/tools/chronicle_lab.py [--root DIR]  # print what would be emitted
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from ckit.chronicle import slugify, viewer_href
    from ckit.text import normalize
except ImportError:  # run standalone (--selftest, --root): find the engine the way the shell does
    _ckit = shutil.which("ckit")
    if not _ckit:
        raise SystemExit("chronicle_lab: the content-kit engine (ckit) is not on PATH — "
                         "bash content-kit/install-engine.sh")
    sys.path.insert(0, str(Path(os.path.realpath(_ckit)).parent.parent))
    from ckit.chronicle import slugify, viewer_href
    from ckit.text import normalize

H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
STATUS = re.compile(r"\*\*Status:\s*([A-Z][A-Z-]*)\b(?:\s+(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}Z)?))?")
DATE_FIELD = re.compile(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})")
SLUG_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})-")
ROW = re.compile(r"^##\s+((?:F|C)-\d+(?:\.\d+)*)\s*[·—–-]\s*(.+?)\s*$", re.M)
FIELD = re.compile(r"^\*\*(Status|Anchor):\*\*\s*(.+)$", re.M)
SUPERSEDES = re.compile(r"\b[Ss]upersedes\b[:\s—–-]*`?([^`\n;]+?)(?:[.;]\s|`|$)")
SUPERSEDED_BY = re.compile(r"\b[Ss]uperseded[ -]by\b[:\s—–-]*`?([^`\n;]+?)(?:[.;]\s|`|$)")
MD_INLINE = re.compile(r"[`*_]+")
KILL_HEAD = re.compile(r"kill|decision", re.I)
KILL_LINE = re.compile(r"\bkill\b", re.I)
LEAD = re.compile(r"^\s*(?:[-*]\s*|\d+\.\s*)?(?:\*\*)?")


def _plain(s: str, limit: int = 300) -> str:
    return normalize(MD_INLINE.sub("", s))[:limit]


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
            cwd=root, capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    first = out.stdout.strip().splitlines()
    return first[0].strip() if first else None


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
        status = (fields.get("Status") or "").split("·")[0].strip().strip("*").split()[0:1]
        rows.append({
            "id": m.group(1), "title": _plain(m.group(2), 200),
            "status": status[0].strip("*") if status else "",
            "anchor": fields.get("Anchor", ""),
            "href": viewer_href(rel, slugify(f"{m.group(1)} · {MD_INLINE.sub('', m.group(2))}")),
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


# ----------------------------------------------------------------------------- entry point

def extract(root: Path, cfg: dict) -> dict:
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
        date = _git_first_date(root, findings_rel, f["heading"]) or (by_slug[slug]["locked"] if slug else None)
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
    return {"events": events, "experiments": experiments}


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
"""

MISSION_FIXTURE = "# Mission 20260902-planted — LIVE (executing)\n\n**Objective:** prove the fixture.\n"


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
        (root / "ops" / "missions").mkdir(parents=True)
        (root / "ops" / "missions" / "20260902-planted.md").write_text(MISSION_FIXTURE, encoding="utf-8")
        (root / "ops" / "missions" / "TEMPLATE.md").write_text("# Mission <id>\n", encoding="utf-8")
        out = extract(root, {})
        ex = {x["slug"]: x for x in out["experiments"]}
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
            if [f["id"] for f in e9["findings"]] != ["F-7"] or e9["findings"][0]["status"] != "BANKED":
                failures.append(f"anchored finding not attached: {e9['findings']}")
            if not e9["findings"][0]["href"].startswith("/shell/record.html?p=record/findings.md#f-7-"):
                failures.append(f"finding href does not land on its heading: {e9['findings'][0]['href']}")
        d1 = ex.get("20260830-draft-only")
        if not d1 or d1["locked"] != "2026-08-30" or d1["status"] != "DRAFT":
            failures.append(f"draft PROBE: Date field / status not parsed: {d1}")
        kinds = sorted(e["kind"] for e in out["events"])
        # no git in the temp dir: F-7 falls back to its experiment's lock date, F-8 has no date → listed nowhere on the timeline
        if kinds != ["experiment", "experiment", "finding", "mission"]:
            failures.append(f"event kinds: {kinds}")
        f7 = next((e for e in out["events"] if e["kind"] == "finding"), None)
        if not f7 or f7["date"] != "2026-09-03T10:00Z" or f7.get("experiment") != "20260903-e9-planted":
            failures.append(f"finding event not dated by its experiment's lock: {f7}")
        mi = next((e for e in out["events"] if e["kind"] == "mission"), None)
        if not mi or mi["date"] != "2026-09-02" or "prove the fixture" not in mi["summary"]:
            failures.append(f"mission not parsed from its file name / objective: {mi}")
        if any("TEMPLATE" in e["title"] for e in out["events"]):
            failures.append("the mission TEMPLATE must not become an event")
    if failures:
        print("chronicle_lab selftest FAILED:\n- " + "\n- ".join(failures))
        return 1
    print("chronicle_lab selftest ok (12 planted assertions)")
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
    cfg = json.loads((root / "lab.json").read_text()) if (root / "lab.json").is_file() else {}
    out = extract(root, cfg)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
