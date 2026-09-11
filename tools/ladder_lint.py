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
  H7  every cross-lab `<pin>:F-<n>` citation names a declared pin, and resolves to a
      real row in that lab when its checkout is reachable

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
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _find_root() -> Path:
    """The lab root: $LAB_ROOT, else the nearest ancestor of the working directory — then of
    this file (the vendored layout is <lab>/kit/tools/) — that holds lab.json."""
    env = os.environ.get("LAB_ROOT")
    if env:
        return Path(env).resolve()
    for start in (Path.cwd(), Path(__file__).resolve()):
        for cand in [start, *start.parents]:
            if (cand / "lab.json").is_file():
                return cand
    raise SystemExit("ladder_lint: no lab.json above the working directory — run inside a lab or pass --root")


NUM = r"\d+(?:\.\d+)*"
FINDING_ID = re.compile(rf"\bF-({NUM})\b")
# A lab migrating off a "numbers.md §n" convention sets citation_alias="section"
# in lab.json and keeps its existing citations; ids are still F-<n> canonically.
# Both the markdown "§12" and the LaTeX "\S12" spellings, plus "§§10-21" ranges.
SECTION_ID = re.compile(rf"(?:§|\\S)({NUM})\b")
SECTION_RANGE = re.compile(rf"(?:§§|\\S\\S)(\d+)\s*[-–—]\s*(\d+)")
# `phl:F-1` — a finding owned by another lab, resolved through record/pins.json.
PINNED_ID = re.compile(rf"\b([a-z][a-z0-9_-]*):(F-{NUM})\b")
CLAIM_HEAD = re.compile(r"^##\s+(C-\d+(?:\.\d+)*)\b(.*)$", re.M)
FINDING_HEAD = re.compile(rf"^#{{2,3}}\s+(F-{NUM})\b(.*)$", re.M)
# numbers.md style: "## 12 · Title" / "### 21.1 · Title"
SECTION_HEAD = re.compile(rf"^#{{2,3}}\s+({NUM})\s*[·.]\s*(.*)$", re.M)
# Any numbered heading, however it is punctuated — used to spot self-reference.
ANY_NUMBERED_HEAD = re.compile(rf"^#{{1,6}}\s+({NUM})\b", re.M)
FIELD = re.compile(r"^\*\*(Status|Anchor|Re-derive)\:\*\*\s*(.+)$", re.M)
BACKTICKED = re.compile(r"`([^`]+)`")
# MOVED: the row is owned by another lab now. Distinct from SUPERSEDED (which means a
# better result replaced it) and from RETRACTED (which means it was wrong). A by-question
# split relocates rows that are perfectly correct, and calling that "superseded" would be
# a lie about the evidence.
STATUS_WORDS = {"BANKED", "PROVISIONAL", "RETRACTED", "SUPERSEDED", "MOVED"}
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
    # Where this lab keeps its ledgers. The convention is record/findings.md and
    # record/claims.md, and that stays the default. A lab migrating onto the ladder
    # may already hold its ledger somewhere else with hundreds of live by-path
    # references into it (design-space-lab: docs/papers/proofs-rot/numbers.md); making
    # it move the file before the gate will run is how a migration gets abandoned.
    # Point the gate at the real file, move it later, on purpose.
    findings_rel: str = "record/findings.md"
    claims_rel: str = "record/claims.md"
    _pin_ids_cache: dict = field(default_factory=dict)

    @property
    def findings_path(self) -> Path:
        return self.root / self.findings_rel

    @property
    def claims_path(self) -> Path:
        return self.root / self.claims_rel

    def cites(self, text: str) -> list[tuple[str, int, bool]]:
        """Every finding id referenced in `text`, as (id, offset, canonical).

        `canonical` is True for an explicit `F-<n>`. Alias hits are marked False
        because §-numbering is inherently ambiguous prose: the same "§4.5" may mean
        a finding, this document's own section, or a section of a third document
        ("folio overview §4.5" — a real line from the corpus this was measured on).
        Two ambiguities are handled and the rest are reported softly:

        - a reference to one of *this file's own* numbered headings is skipped, which
          is how a human reads it;
        - a range "§§10-21" expands to every id it covers.

        An unresolved alias hit is therefore a warning, while an unresolved `F-<n>`
        is an error. Full enforcement is what a lab buys by moving to canonical ids.
        """
        # Pinned ids are consumed first so the bare "F-1" inside "phl:F-1" is not
        # also read as a local citation.
        pinned = {i for m in PINNED_ID.finditer(text) for i in range(m.start(), m.end())}
        out = [
            (f"F-{m.group(1)}", m.start(), True)
            for m in FINDING_ID.finditer(text)
            if m.start() not in pinned
        ]
        if not self.alias:
            return out

        own = {m.group(1) for m in ANY_NUMBERED_HEAD.finditer(text)}
        covered: set[int] = set()
        for m in SECTION_RANGE.finditer(text):
            lo, hi = int(m.group(1)), int(m.group(2))
            covered.update(range(m.start(), m.end()))
            if lo <= hi and hi - lo < 100:
                out += [(f"F-{n}", m.start(), False) for n in range(lo, hi + 1)
                        if str(n) not in own]
        out += [
            (f"F-{m.group(1)}", m.start(), False)
            for m in SECTION_ID.finditer(text)
            if m.group(1) not in own and m.start() not in covered
        ]
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
    path = lab.findings_path
    rel = lab.findings_rel
    if not path.is_file():
        return [Problem(rel, "missing — the lab has no findings ledger")]

    text = path.read_text(encoding="utf-8", errors="replace")
    sections = lab.heads(text)
    if not sections:
        probs.append(Problem(rel, "no `## F-<n>` sections found", hard=False))

    for ident, body, line in sections:
        if ident in lab.findings:
            probs.append(Problem(f"{rel}:{line}", f"duplicate finding id {ident}"))
        lab.findings[ident] = line

        fields = {m.group(1): m.group(2).strip() for m in FIELD.finditer(body)}
        missing = [f for f in ("Status", "Anchor", "Re-derive") if f not in fields]
        if missing:
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} has no " + ", ".join(f"**{f}:**" for f in missing) + " field"
                    + ("s" if len(missing) > 1 else ""),
                )
            )

        status = fields.get("Status", "")
        if status and not any(w in status.upper() for w in STATUS_WORDS):
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} status {status!r} is none of {sorted(STATUS_WORDS)}",
                )
            )

        for anchor in BACKTICKED.findall(fields.get("Anchor", "")):
            if not _anchor_ok(lab, anchor):
                probs.append(
                    Problem(
                        f"{rel}:{line}",
                        f"{ident} anchor `{anchor}` does not resolve "
                        "(no such path, and no matching pin in record/pins.json)",
                    )
                )
        if "Re-derive" in fields and not BACKTICKED.search(fields["Re-derive"]):
            probs.append(
                Problem(
                    f"{rel}:{line}",
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
        # A relocated ledger's neighbours are authored documents too — they are the
        # ones most likely to cite it, so a lab does not lose coverage by not having
        # moved its record/ yet.
        (lab.findings_path.parent, ("*.md", "*.tex")),
    ):
        if base.is_dir():
            for pat in patterns:
                out.extend(sorted(base.glob(pat)))
    skip = {p.resolve() for p in (lab.findings_path, lab.claims_path) if p.is_file()}
    return [p for p in out if p.resolve() not in skip]


def _pinned_lab_ids(lab: Lab, pin: str) -> set[str] | None:
    """Finding ids declared by a pinned lab, if its checkout is reachable from here.

    Returns None when the pin declares no `local` path, or that path is not on this
    machine — a pinned lab is external by definition and may simply not be checked out.
    """
    if pin in lab._pin_ids_cache:
        return lab._pin_ids_cache[pin]
    spec = lab.pins.get(pin)
    result: set[str] | None = None
    local = (spec or {}).get("local") if isinstance(spec, dict) else None
    if local:
        root = (lab.root / local).resolve()
        if root.is_dir():
            try:
                other = load_lab(root)
                check_findings(other)
                result = set(other.findings)
            except Exception:
                result = None
    lab._pin_ids_cache[pin] = result
    return result


def check_pins(lab: Lab, path: Path, text: str) -> list[Problem]:
    """H7 — a cross-lab citation names a declared pin, and resolves in that lab.

    The second half matters more than it looks. A `<pin>:F-<n>` that names a declared pin
    but no real row is invisible to every other check: it is not a local id, so H3 skips
    it, and the pin exists, so the first half passes. That is exactly how seven citations
    to non-existent rows survived a by-question split — a `§n` rewrite had turned prose
    line references (`§207-249`) into finding citations, and nothing looked.
    """
    probs: list[Problem] = []
    for m in PINNED_ID.finditer(text):
        pin, ident = m.group(1), m.group(2)
        line = text.count("\n", 0, m.start()) + 1
        if pin not in lab.pins:
            probs.append(
                Problem(
                    f"{_rel(lab, path)}:{line}",
                    f"cites {m.group(0)}, but pin '{pin}' is not declared in record/pins.json "
                    "— a cross-lab citation must name the repo and commit it resolves against",
                )
            )
            continue
        known = _pinned_lab_ids(lab, pin)
        if known is not None and ident not in known:
            probs.append(
                Problem(
                    f"{_rel(lab, path)}:{line}",
                    f"cites {m.group(0)}, but '{pin}' declares no {ident} "
                    f"({lab.pins[pin].get('local')}) — the citation resolves to nothing",
                )
            )
    return probs


def check_citations(lab: Lab) -> list[Problem]:
    """H3 — a cited finding id exists (locally, or in a declared pinned lab)."""
    probs: list[Problem] = []
    for path in _cited_files(lab):
        text = path.read_text(encoding="utf-8", errors="replace")
        probs.extend(check_pins(lab, path, text))
        seen: set[tuple[str, int]] = set()
        for ident, offset, canonical in lab.cites(text):
            if ident in lab.findings:
                continue
            line = text.count("\n", 0, offset) + 1
            if (ident, line) in seen:
                continue
            seen.add((ident, line))
            note = "" if canonical else " (§-alias — may be a reference to another document)"
            probs.append(
                Problem(
                    f"{_rel(lab, path)}:{line}",
                    f"cites {ident}, which is not in findings.md{note}",
                    hard=canonical,
                )
            )
    return probs


def check_claims(lab: Lab) -> list[Problem]:
    """H4 — a claim is licensed by findings, not by assertion."""
    path = lab.claims_path
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    probs: list[Problem] = []
    for ident, body, line in _sections(text, CLAIM_HEAD):
        if not lab.cites(body):
            probs.append(
                Problem(f"{lab.claims_rel}:{line}", f"{ident} cites no finding — nothing licenses it")
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
        findings_rel=cfg.get("findings", "record/findings.md"),
        claims_rel=cfg.get("claims", "record/claims.md"),
    )
    pins = root / "record" / "pins.json"
    if pins.is_file():
        lab.pins = {
            k: v for k, v in json.loads(pins.read_text(encoding="utf-8")).items()
            if not k.startswith("_")
        }
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


def moved_ids(root: Path) -> set[str]:
    """Finding ids the gate actually read for a lab, whatever path its ledger is on."""
    lab = load_lab(root)
    check_findings(lab)
    return set(lab.findings)


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

        # A document's reference to its own numbered section is not a citation.
        selfref = _plant(tmp / "m", legacy_findings, {
            "record/claims.md": (
                "# Claims — LIVE\n\n## 3 · Structure\n\n### 3.1 One paper\n\n"
                "Rests on §12. Write it in the §3.1 shape.\n"
            ),
        }, cfg={"citation_alias": "section"})
        allmsgs = " ".join(q.message for q in run(selfref))
        expect("self-ref", "F-3.1" not in allmsgs, f"self-reference read as a citation: {allmsgs}")
        expect("self-ref-keeps-real", "F-12" not in allmsgs, "a real §-citation was broken")

        # LaTeX \S spelling and §§ ranges resolve; an alias miss is soft, not hard.
        latex = _plant(tmp / "n", legacy_findings, {
            "content/papers/r/main.tex": "% Report -- LIVE\nHarness rows (\\S12) and \\S21.1.\n",
            "content/notes/rng.md": "# Note — LIVE\n\nBanked across §§12-12 inclusive.\n",
            "content/notes/miss.md": "# Note — LIVE\n\nSee folio overview §77 for context.\n",
        }, cfg={"citation_alias": "section"})
        res = run(latex)
        expect("latex", not [q for q in res if q.hard and "F-12" in q.message],
               "LaTeX \\S12 not resolved against findings")
        expect("alias-soft", any("F-77" in q.message and not q.hard for q in res),
               "unresolved alias citation should warn, not error")
        expect("alias-not-hard", not [q for q in res if q.hard and "F-77" in q.message],
               "unresolved alias citation must not be a hard error")

        # A cross-lab citation resolves through a declared pin, and only then.
        pinned_ok = _plant(tmp / "p", GOOD_FINDINGS, {
            "content/notes/x.md": "# Note — LIVE\n\nThe frontier is phl:F-1; ours is F-1.\n",
            "record/pins.json": '{"_comment": "docs", "phl": {"repo": "r", "sha": "abc"}}',
        })
        hard = [q.render() for q in run(pinned_ok) if q.hard]
        expect("pin-ok", not hard, f"declared pin wrongly flagged: {hard}")

        pinned_bad = _plant(tmp / "q", GOOD_FINDINGS, {
            "content/notes/x.md": "# Note — LIVE\n\nRests on dsl:F-99.\n",
        })
        msgs = " ".join(q.message for q in run(pinned_bad) if q.hard)
        expect("pin-undeclared", "not declared in record/pins.json" in msgs,
               "undeclared pin not caught")
        expect("pin-no-leak", "cites F-99" not in msgs,
               "the F-99 inside dsl:F-99 was also read as a local citation")

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

        # A lab whose ledger has not moved to record/findings.md yet: point the gate
        # at the real file via lab.json rather than making the move a precondition.
        moved = _plant(tmp / "r1", "unused\n", {
            "docs/papers/numbers.md": GOOD_FINDINGS,
            "docs/papers/neighbour.md": "# Neighbour — LIVE\n\nRests on F-1.\n",
        }, cfg={"findings": "docs/papers/numbers.md"})
        (moved / "record" / "findings.md").unlink()
        probs = run(moved)
        hard = [q.render() for q in probs if q.hard]
        expect("relocated-ledger", not hard, f"relocated ledger not accepted: {hard}")
        expect("relocated-ledger-read", "F-1" in moved_ids(moved),
               "findings were not read from the configured path")
        # The relocated ledger must not be linted as if it were an authored document
        # citing itself, and its neighbours must still be scanned for citations.
        expect("relocated-not-selfcited",
               not any("numbers.md" in q.where and "cites" in q.message for q in probs),
               "the ledger was treated as a document citing itself")

        # A cross-lab citation that names a declared pin but no real row. This is the case
        # that slipped through in production: the pin exists, so the old H7 passed.
        sib = _plant(tmp / "s1", GOOD_FINDINGS, {})
        ghost = _plant(tmp / "s2", GOOD_FINDINGS, {
            "record/pins.json": json.dumps({"sib": {"repo": "x", "sha": "y", "local": "../../s1/lab"}}),
            "content/notes/x.md": "# Note — LIVE\n\nRests on sib:F-1 and on sib:F-404.\n",
        })
        msgs = " ".join(q.message for q in run(ghost) if q.hard)
        expect("pin-row-missing", "declares no F-404" in msgs,
               f"a pinned citation to a non-existent row was not caught: {msgs}")
        expect("pin-row-present", "declares no F-1" not in msgs,
               "a valid pinned citation was wrongly flagged")

        # A pin whose checkout is not on this machine cannot be validated, and must not fail.
        away = _plant(tmp / "s3", GOOD_FINDINGS, {
            "record/pins.json": json.dumps({"sib": {"repo": "x", "sha": "y", "local": "../nope"}}),
            "content/notes/x.md": "# Note — LIVE\n\nRests on sib:F-404.\n",
        })
        hard = [q.render() for q in run(away) if q.hard]
        expect("pin-unreachable", not hard,
               f"an unreachable pin was treated as a failure: {hard}")

        # A row relocated to another lab by a by-question split.
        movedrow = _plant(tmp / "r3", GOOD_FINDINGS + """
## F-9 · A row that now lives in another lab
**Status:** MOVED 2026-08-25 — owned by `phl:F-9`
**Anchor:** `phl:F-9`
**Re-derive:** `$HARNESS/record/findings.md → F-9`

Pointer only: this row holds no numbers.
""", {"record/pins.json": json.dumps({"phl": {"repo": "x", "sha": "y"}})})
        hard = [q.render() for q in run(movedrow) if q.hard]
        expect("moved-status", not hard, f"MOVED pointer row rejected: {hard}")

        # Default stays the convention: no config, no relocation.
        missing = _plant(tmp / "r2", GOOD_FINDINGS, {})
        (missing / "record" / "findings.md").unlink()
        msgs = " ".join(q.message for q in run(missing) if q.hard)
        expect("default-path", "no findings ledger" in msgs,
               "a lab with no ledger at the default path was not reported")

    if failures:
        print("ladder_lint selftest FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ladder_lint selftest ok (27 planted cases)")
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
        root = _find_root()

    cfg = {}
    if (root / "lab.json").is_file():
        cfg = json.loads((root / "lab.json").read_text(encoding="utf-8"))
    strict = args.strict or cfg.get("ladder") == "strict"

    if cfg.get("ladder") == "off":
        print("ladder lint: off (library mode — this repo is not a lab)")
        return 0

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
