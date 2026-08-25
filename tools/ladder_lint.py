#!/usr/bin/env python3
"""Ladder lint — every number a lab publishes must trace back to a finding.

    python3 kit/tools/ladder_lint.py            # report everything, exit 0
    python3 kit/tools/ladder_lint.py --strict   # hard findings fail the gate
    python3 kit/tools/ladder_lint.py --selftest # planted fixtures, no lab needed

The ladder a lab records on:

    evidence -> probe -> logbook -> finding -> claim -+-> page
                                                      +-> paper
                                                      +-> post

It converges at `claim` and fans out into terminal artifacts. Prose is written once
per artifact and is *not* synced between them; numbers are never written twice at
all -- each artifact cites a finding id, and this tool checks the joints:

  H1  every `## F-<n>` in record/findings.md carries Status + Anchor + Re-derive
  H2  every anchor resolves to a real path, or to a declared pin in record/pins.json
  H3  every `F-<n>` cited anywhere resolves to a finding that exists
  H4  every `## C-<n>` in record/claims.md cites at least one finding
  H5  every record/ops/paper document declares a status in its opening lines
  H6  no markdown/HTML twin of the same authored document

  S1  no dangling internal /<content>/... link                        (soft)
  S2  no result-shaped number in a section that cites no finding       (soft)

Ids are `F-<n>`, optionally sub-numbered (`F-21.1`). A lab arriving from a
"numbers.md §n" convention sets `"citation_alias": "section"` in lab.json, and its
existing `§12` citations and `## 12 · Title` headings are read as `F-12` — so a
migration is a config flag rather than a sed across a few thousand references.

Hard checks fail under --strict; soft checks always warn and never fail. A lab
mid-migration runs the default until it is clean, then sets "ladder": "strict" in
lab.json. Failing loud from day one would just mean the gate is disabled.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

NUM = r"\d+(?:\.\d+)*"
FINDING_ID = re.compile(rf"\bF-({NUM})\b")
# A lab migrating off a "numbers.md §n" convention sets citation_alias="section"
# in lab.json and keeps its existing citations; ids are still F-<n> canonically.
SECTION_ID = re.compile(rf"§({NUM})\b")
CLAIM_HEAD = re.compile(r"^##\s+(C-\d+(?:\.\d+)*)\b(.*)$", re.M)
FINDING_HEAD = re.compile(rf"^#{{2,3}}\s+(F-{NUM})\b(.*)$", re.M)
# numbers.md style: "## 12 · Title" / "### 21.1 · Title"
SECTION_HEAD = re.compile(rf"^#{{2,3}}\s+({NUM})\s*[·.]\s*(.*)$", re.M)
FIELD = re.compile(r"^\*\*(Status|Anchor|Re-derive)\:\*\*\s*(.+)$", re.M)
BACKTICKED = re.compile(r"`([^`]+)`")
STATUS_WORDS = {"BANKED", "PROVISIONAL", "RETRACTED", "SUPERSEDED"}
DOC_STATUS = {"LIVE", "HISTORICAL", "PARKED", "RETIRED", "FROZEN", "DRAFT"}
HREF = re.compile(r'href="(/[^"#?]*)(?:[#?][^"]*)?"')

# Numbers that look like a measured result rather than prose furniture:
# ratios (7/7), percentages (92.7%), and 3+ digit counts (565, 3600).
RESULT_NUM = re.compile(r"(?<![\w./-])(?:\d+/\d+|\d+(?:\.\d+)?%|\d{3,})(?![\w%/-])")
# Section headings inside a prose document.
SECTION = re.compile(r"^#{1,6}\s+.*$", re.M)


@dataclass
class Problem:
    where: str
    message: str
    hard: bool = True

    def render(self) -> str:
        return f"{'ERROR' if self.hard else 'warn '}  {self.where}: {self.message}"


@dataclass
class Lab:
    root: Path
    content: Path
    findings: dict[str, int] = field(default_factory=dict)  # id -> line number
    pins: dict[str, str] = field(default_factory=dict)
    alias: bool = False  # accept "§n" as a citation of F-n

    def cites(self, text: str) -> list[tuple[str, int]]:
        """Every finding id referenced in `text`, as (canonical id, offset)."""
        out = [(f"F-{m.group(1)}", m.start()) for m in FINDING_ID.finditer(text)]
        if self.alias:
            out += [(f"F-{m.group(1)}", m.start()) for m in SECTION_ID.finditer(text)]
        return out

    def heads(self, text: str) -> list[tuple[str, str, int]]:
        """Finding sections, accepting the §-numbered heading style when aliased."""
        found = _sections(text, FINDING_HEAD)
        if self.alias:
            found += [
                (f"F-{ident}", body, line)
                for ident, body, line in _sections(text, SECTION_HEAD)
            ]
        return sorted(found, key=lambda t: t[2])


def _rel(lab: Lab, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(lab.root))
    except ValueError:
        return str(p)


def _sections(text: str, head: re.Pattern[str]) -> list[tuple[str, str, int]]:
    """Split a markdown file into (id, body, line_no) at the given heading pattern."""
    marks = [(m.group(1), m.start(), text.count("\n", 0, m.start()) + 1)
             for m in head.finditer(text)]
    out: list[tuple[str, str, int]] = []
    for i, (ident, start, line) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        out.append((ident, text[start:end], line))
    return out


def _anchor_ok(lab: Lab, target: str) -> bool:
    """An anchor is either a path in this lab, or `<pin>:<path>` for an external vault."""
    if ":" in target:
        pin = target.split(":", 1)[0]
        if pin in lab.pins:
            return True
    candidate = (lab.root / target.lstrip("/")).resolve()
    if candidate.exists():
        return True
    # Anchors may point at a directory of evidence rather than a single file.
    return candidate.parent.is_dir() and any(candidate.parent.glob(candidate.name))


def check_findings(lab: Lab) -> list[Problem]:
    """H1 + H2 — findings are well-formed and their evidence is reachable."""
    probs: list[Problem] = []
    path = lab.root / "record" / "findings.md"
    if not path.is_file():
        return [Problem("record/findings.md", "missing — the lab has no findings ledger")]

    text = path.read_text(encoding="utf-8", errors="replace")
    sections = lab.heads(text)
    if not sections:
        probs.append(Problem("record/findings.md", "no `## F-<n>` sections found", hard=False))

    for ident, body, line in sections:
        if ident in lab.findings:
            probs.append(Problem(f"record/findings.md:{line}", f"duplicate finding id {ident}"))
        lab.findings[ident] = line

        fields = {m.group(1): m.group(2).strip() for m in FIELD.finditer(body)}
        missing = [f for f in ("Status", "Anchor", "Re-derive") if f not in fields]
        if missing:
            probs.append(
                Problem(
                    f"record/findings.md:{line}",
                    f"{ident} has no " + ", ".join(f"**{f}:**" for f in missing) + " field"
                    + ("s" if len(missing) > 1 else ""),
                )
            )

        status = fields.get("Status", "")
        if status and not any(w in status.upper() for w in STATUS_WORDS):
            probs.append(
                Problem(
                    f"record/findings.md:{line}",
                    f"{ident} status {status!r} is none of {sorted(STATUS_WORDS)}",
                )
            )

        for anchor in BACKTICKED.findall(fields.get("Anchor", "")):
            if not _anchor_ok(lab, anchor):
                probs.append(
                    Problem(
                        f"record/findings.md:{line}",
                        f"{ident} anchor `{anchor}` does not resolve "
                        "(no such path, and no matching pin in record/pins.json)",
                    )
                )
        if "Re-derive" in fields and not BACKTICKED.search(fields["Re-derive"]):
            probs.append(
                Problem(
                    f"record/findings.md:{line}",
                    f"{ident} re-derivation is not a backticked command",
                )
            )
    return probs


def _cited_files(lab: Lab) -> list[Path]:
    out: list[Path] = []
    for base, patterns in (
        (lab.content, ("**/*.html", "**/*.md", "**/*.tex")),
        (lab.root / "record", ("*.md",)),
        (lab.root / "ops", ("**/*.md",)),
    ):
        if base.is_dir():
            for pat in patterns:
                out.extend(sorted(base.glob(pat)))
    findings = lab.root / "record" / "findings.md"
    return [p for p in out if p.resolve() != findings.resolve()]


def check_citations(lab: Lab) -> list[Problem]:
    """H3 — a cited finding id exists."""
    probs: list[Problem] = []
    for path in _cited_files(lab):
        text = path.read_text(encoding="utf-8", errors="replace")
        for ident, offset in lab.cites(text):
            if ident not in lab.findings:
                line = text.count("\n", 0, offset) + 1
                probs.append(
                    Problem(f"{_rel(lab, path)}:{line}", f"cites {ident}, which is not in findings.md")
                )
    return probs


def check_claims(lab: Lab) -> list[Problem]:
    """H4 — a claim is licensed by findings, not by assertion."""
    path = lab.root / "record" / "claims.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    probs: list[Problem] = []
    for ident, body, line in _sections(text, CLAIM_HEAD):
        if not lab.cites(body):
            probs.append(
                Problem(f"record/claims.md:{line}", f"{ident} cites no finding — nothing licenses it")
            )
    return probs


def check_status_banners(lab: Lab) -> list[Problem]:
    """H5 — a reader can tell in three lines whether a document is still true."""
    probs: list[Problem] = []
    targets: list[Path] = []
    for base, pat in ((lab.root / "record", "*.md"), (lab.root / "ops", "*.md")):
        if base.is_dir():
            targets.extend(sorted(base.glob(pat)))
    if lab.content.is_dir():
        targets.extend(sorted(lab.content.glob("papers/*/main.md")))

    for path in targets:
        head = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()[:8] if ln.strip()][:5]
        if not any(w in ln.upper() for ln in head for w in DOC_STATUS):
            probs.append(
                Problem(
                    _rel(lab, path),
                    f"no status in the opening lines — declare one of {sorted(DOC_STATUS)}",
                )
            )
    return probs


def check_twins(lab: Lab) -> list[Problem]:
    """H6 — one authored document, one format.

    `main.md` beside `index.html` is legitimate only for an imported external paper,
    where main.md holds *someone else's* text and index.html holds our reading of it.
    That case declares itself with source.json. Anything else is the same prose kept
    in two formats, which is what drifts.
    """
    probs: list[Problem] = []
    if not lab.content.is_dir():
        return probs
    for md in sorted(lab.content.glob("**/main.md")):
        folder = md.parent
        if (folder / "index.html").is_file() and not (folder / "source.json").is_file():
            probs.append(
                Problem(
                    _rel(lab, md),
                    "main.md and index.html hold the same authored document — keep one "
                    "format, or add source.json if main.md is an imported source text",
                )
            )
    return probs


def check_links(lab: Lab) -> list[Problem]:
    """S1 — internal links resolve (soft: a link may point at work in progress)."""
    probs: list[Problem] = []
    if not lab.content.is_dir():
        return probs
    prefix = f"/{lab.content.name}/"
    for path in sorted(lab.content.rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in HREF.finditer(text):
            href = m.group(1)
            if not href.startswith(prefix):
                continue
            target = (lab.root / href.lstrip("/")).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                line = text.count("\n", 0, m.start()) + 1
                probs.append(Problem(f"{_rel(lab, path)}:{line}", f"dangling link {href}", hard=False))
    return probs


def check_uncited_numbers(lab: Lab) -> list[Problem]:
    """S2 — a section full of results that cites nothing (soft: heuristic by nature)."""
    probs: list[Problem] = []
    if not lab.content.is_dir():
        return probs
    for path in sorted(lab.content.rglob("*.md")):
        if path.name == "main.md" and (path.parent / "source.json").is_file():
            continue  # imported source text, not our claims
        text = path.read_text(encoding="utf-8", errors="replace")
        marks = [(m.start(), text.count("\n", 0, m.start()) + 1) for m in SECTION.finditer(text)]
        spans = [
            (text[s: marks[i + 1][0] if i + 1 < len(marks) else len(text)], ln)
            for i, (s, ln) in enumerate(marks)
        ] or [(text, 1)]
        for body, line in spans:
            nums = RESULT_NUM.findall(body)
            if len(nums) >= 2 and not lab.cites(body):
                probs.append(
                    Problem(
                        f"{_rel(lab, path)}:{line}",
                        f"section has result-shaped numbers ({', '.join(nums[:3])}…) "
                        "but cites no finding",
                        hard=False,
                    )
                )
    return probs


def load_lab(root: Path) -> Lab:
    cfg = {"content": "content"}
    marker = root / "lab.json"
    if marker.is_file():
        cfg.update(json.loads(marker.read_text(encoding="utf-8")))
    lab = Lab(
        root=root.resolve(),
        content=(root / cfg["content"]).resolve(),
        alias=cfg.get("citation_alias") == "section",
    )
    pins = root / "record" / "pins.json"
    if pins.is_file():
        lab.pins = json.loads(pins.read_text(encoding="utf-8"))
    return lab


def run(root: Path) -> list[Problem]:
    lab = load_lab(root)
    probs = check_findings(lab)  # populates lab.findings, so it must run first
    for check in (
        check_citations, check_claims, check_status_banners,
        check_twins, check_links, check_uncited_numbers,
    ):
        probs.extend(check(lab))
    return probs


# ---------------------------------------------------------------- selftest

GOOD_FINDINGS = """# Findings — LIVE

## F-1 · The floor does not move under mining
**Status:** BANKED · **Tier:** reviewer-gated
**Anchor:** `evidence/mining.tsv`
**Re-derive:** `awk -F'\\t' '$3=="survivor"' evidence/mining.tsv | wc -l`

Mining 5000 candidates leaves 2 survivors and converts 0/6.
"""

BAD_FINDINGS = """# Findings — LIVE

## F-1 · Missing its fields
Some prose and no fields at all.

## F-2 · Anchor points nowhere
**Status:** BANKED
**Anchor:** `evidence/does-not-exist.tsv`
**Re-derive:** `cat evidence/does-not-exist.tsv`
"""


def _plant(tmp: Path, findings: str, extra: dict[str, str], cfg: dict | None = None) -> Path:
    root = tmp / "lab"
    (root / "record").mkdir(parents=True)
    (root / "evidence").mkdir(parents=True)
    (root / "content").mkdir(parents=True)
    conf = {"content": "content"}
    conf.update(cfg or {})
    (root / "lab.json").write_text(json.dumps(conf), encoding="utf-8")
    (root / "record" / "findings.md").write_text(findings, encoding="utf-8")
    (root / "evidence" / "mining.tsv").write_text("a\tb\tsurvivor\n", encoding="utf-8")
    for rel, body in extra.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


def selftest() -> int:
    failures: list[str] = []

    def expect(name: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{name}: {detail}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        clean = _plant(tmp / "a", GOOD_FINDINGS, {
            "record/claims.md": "# Claims — LIVE\n\n## C-1 · Mining is not a lever\nRests on F-1.\n",
            "content/notes/x.md": "# Note — LIVE\n\nMining left 2 survivors of 5000 (F-1).\n",
        })
        probs = run(clean)
        expect("clean", not [p for p in probs if p.hard],
               f"expected no hard problems, got {[p.render() for p in probs if p.hard]}")

        broken = _plant(tmp / "b", BAD_FINDINGS, {})
        msgs = " ".join(p.message for p in run(broken) if p.hard)
        expect("H1", "**Status:**" in msgs or "**Anchor:**" in msgs, "missing-field not caught")
        expect("H2", "does not resolve" in msgs, "dangling anchor not caught")

        cited = _plant(tmp / "c", GOOD_FINDINGS, {
            "content/notes/y.md": "# Note — LIVE\n\nSee F-9 for the detail.\n",
        })
        msgs = " ".join(p.message for p in run(cited) if p.hard)
        expect("H3", "F-9" in msgs, "unknown finding id not caught")

        unlicensed = _plant(tmp / "d", GOOD_FINDINGS, {
            "record/claims.md": "# Claims — LIVE\n\n## C-1 · Asserted from nowhere\nTrust me.\n",
        })
        msgs = " ".join(p.message for p in run(unlicensed) if p.hard)
        expect("H4", "cites no finding" in msgs, "unlicensed claim not caught")

        nobanner = _plant(tmp / "e", GOOD_FINDINGS, {
            "record/lab.md": "# Lab notes\n\nNo status anywhere near the top.\n",
        })
        msgs = " ".join(p.message for p in run(nobanner) if p.hard)
        expect("H5", "no status" in msgs, "missing status banner not caught")

        twin = _plant(tmp / "f", GOOD_FINDINGS, {
            "content/papers/r/main.md": "# Report — LIVE\n\nBody (F-1).\n",
            "content/papers/r/index.html": "<html><title>Report</title></html>",
        })
        msgs = " ".join(p.message for p in run(twin) if p.hard)
        expect("H6", "same authored document" in msgs, "md/html twin not caught")

        imported = _plant(tmp / "g", GOOD_FINDINGS, {
            "content/entries/p/main.md": "# Their paper — LIVE\n\n7/7 and 92.7% reported.\n",
            "content/entries/p/index.html": "<html><title>Reading</title></html>",
            "content/entries/p/source.json": '{"abs": "https://example.org"}',
        })
        hard = [p.render() for p in run(imported) if p.hard]
        expect("H6-exempt", not hard, f"source.json entry wrongly flagged: {hard}")

        soft = _plant(tmp / "h", GOOD_FINDINGS, {
            "content/notes/z.md": "# Note — LIVE\n\n## Results\n\nWe saw 7/7 and 92.7% here.\n",
        })
        res = run(soft)
        expect("S2", any("cites no finding" in p.message and not p.hard for p in res),
               "uncited result numbers not warned")
        expect("S2-soft", not [p for p in res if p.hard], "soft check leaked into hard")

        # A lab arriving from a "numbers.md §n" convention keeps its citations.
        legacy_findings = """# Findings — LIVE

## 12 · Reuse is invisible to the score
**Status:** BANKED
**Anchor:** `evidence/mining.tsv`
**Re-derive:** `wc -l evidence/mining.tsv`

The 6/7 certificate converts 5 of 5.

### 21.1 · Portability holds on a second substrate
**Status:** BANKED
**Anchor:** `evidence/mining.tsv`
**Re-derive:** `wc -l evidence/mining.tsv`

Five of ten obligations false as stated.
"""
        legacy = _plant(tmp / "i", legacy_findings, {
            "content/notes/l.md": "# Note — LIVE\n\nSee §12 and §21.1 for the detail.\n",
        }, cfg={"citation_alias": "section"})
        hard = [q.render() for q in run(legacy) if q.hard]
        expect("alias", not hard, f"§-style findings/citations wrongly flagged: {hard}")

        # Without the flag, the same §-citations are simply not citations at all,
        # so the section reads as uncited results rather than as unknown ids.
        strict_ids = _plant(tmp / "j", legacy_findings, {
            "content/notes/l.md": "# Note — LIVE\n\nSee §12 and §21.1 for the detail.\n",
        })
        msgs = " ".join(q.message for q in run(strict_ids) if q.hard)
        expect("alias-off", "F-12" not in msgs, "alias leaked when not configured")

        # Sub-numbered canonical ids resolve.
        subid = _plant(tmp / "k", GOOD_FINDINGS + """
## F-2.3 · A sub-numbered finding
**Status:** BANKED
**Anchor:** `evidence/mining.tsv`
**Re-derive:** `wc -l evidence/mining.tsv`

Detail.
""", {"content/notes/s.md": "# Note — LIVE\n\nRests on F-2.3.\n"})
        hard = [q.render() for q in run(subid) if q.hard]
        expect("sub-id", not hard, f"sub-numbered id not resolved: {hard}")

    if failures:
        print("ladder_lint selftest FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ladder_lint selftest ok (11 planted cases)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Check that every published number traces to a finding.")
    ap.add_argument("--root", type=Path, default=None, help="lab root (default: resolved from the kit)")
    ap.add_argument("--strict", action="store_true", help="hard problems fail (exit 1)")
    ap.add_argument("--selftest", action="store_true", help="run planted fixtures and exit")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.root is not None:
        root = args.root.resolve()
    else:
        from paths import LAB_ROOT  # resolved the same way as the rest of the kit

        root = LAB_ROOT

    cfg = {}
    if (root / "lab.json").is_file():
        cfg = json.loads((root / "lab.json").read_text(encoding="utf-8"))
    strict = args.strict or cfg.get("ladder") == "strict"

    probs = run(root)
    hard = [p for p in probs if p.hard]
    soft = [p for p in probs if not p.hard]

    def order(x: Problem) -> tuple:
        # ledger first, then hard-before-soft, then by location with line as a number
        head, _, tail = x.where.rpartition(":")
        return (not x.hard, 0 if x.where.startswith("record/findings.md") else 1,
                head or x.where, int(tail) if tail.isdigit() else 0)

    for p in sorted(probs, key=order):
        print(p.render())

    mode = "strict" if strict else "warn"
    print(f"\nladder lint ({mode}): {len(hard)} error(s), {len(soft)} warning(s)")
    if hard and strict:
        return 1
    if hard:
        print('not failing the gate — set "ladder": "strict" in lab.json once this is clean')
    return 0


if __name__ == "__main__":
    sys.exit(main())
