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
  H2  every anchor, and every `**Defense:**` path, resolves to a real path or to a
      declared pin in record/pins.json
  H3  every `F-<n>` cited anywhere resolves to a finding that exists
  H4  every `## C-<n>` in record/claims.md cites at least one finding
  H5  every record/ops/paper document declares a status in its opening lines
  H6  no markdown/HTML twin of the same authored document
  H7  every cross-lab `<pin>:F-<n>` citation names a declared pin, and resolves to a
      real row in that lab when its checkout is reachable

  S1  no dangling internal /<content>/... link                         (soft)
  S2  no result-shaped number in a section that cites no finding       (soft)
  S3  no finding headline over 24 words                                (soft)
  S4  no ids (F-n, C-n, §, <pin>:) in a finding headline               (soft)
  S5  a `**Date:**` field the chronicle can read (YYYY-MM-DD)          (soft)
  S6  ops/STATE.md under 500 words — it is a pointer                   (soft)
  S7  a finding row carries `**Defense:**`  ("findings_layered" labs)  (soft)

A finding row is an **interface**: a plain headline, then Status · Tier · Date · Number · Bound ·
Why it matters · Anchor · Re-derive · Defense, with the long-form defense — predictions as scored,
the reviewer's verdict, the anomalies — at `record/findings/F-<n>.md`. S3-S7 are the rules that
keep the row short, and they only ever warn: they are voice, they fire on every unmigrated ledger
at once, and a check that fails from day one gets disabled (MIGRATION.md). A lab that has finished
the migration sets `"findings_layered": true` in kit.json, which turns on S7.

`**Defense:**` is read only on its own line and only as a backticked path — unlike Tier, which the
chronicle also accepts inline for rows written before the layering. An unbackticked value is an
error, because it would otherwise satisfy S7 while being checked by nothing. The defense pages
themselves are linted as the record documents they are (H3, H5, H7).

Ids are `F-<n>`, optionally sub-numbered (`F-21.1`). A lab arriving from a
"numbers.md §n" convention sets `"citation_alias": "section"` in kit.json, and its
existing `§12` citations and `## 12 · Title` headings are read as `F-12` — so a
migration is a config flag rather than a sed across a few thousand references.

Hard checks fail under --strict; soft checks always warn and never fail. A lab
mid-migration runs the default until it is clean, then sets "ladder": "strict" in
kit.json (lab.json before content-kit 0.4; both are read). Failing loud from day one
would just mean the gate is disabled.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


# The lab's config: kit.json (content-kit 0.4+), else the deprecated lab.json it replaced.
MARKERS = ("kit.json", "lab.json")


def _config_file(root: Path) -> Path | None:
    for name in MARKERS:
        if (root / name).is_file():
            return root / name
    return None


def _find_config_name(root: Path) -> str | None:
    marker = _config_file(root)
    return marker.name if marker else None


def _load_config(root: Path) -> dict:
    marker = _config_file(root)
    return json.loads(marker.read_text(encoding="utf-8")) if marker else {}


def _find_root() -> Path:
    """The lab root: $CKIT_ROOT (or its old name $LAB_ROOT), else the nearest ancestor of the
    working directory — then of this file (the vendored layout is <lab>/kit/tools/) — that holds
    kit.json (or lab.json)."""
    env = os.environ.get("CKIT_ROOT") or os.environ.get("LAB_ROOT")
    if env:
        return Path(env).resolve()
    for start in (Path.cwd(), Path(__file__).resolve()):
        for cand in [start, *start.parents]:
            if _config_file(cand) is not None:
                return cand
    raise SystemExit("ladder_lint: no kit.json above the working directory — run inside a lab or pass --root")


NUM = r"\d+(?:\.\d+)*"
FINDING_ID = re.compile(rf"\bF-({NUM})\b")
# A lab migrating off a "numbers.md §n" convention sets citation_alias="section"
# in kit.json and keeps its existing citations; ids are still F-<n> canonically.
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
FIELD = re.compile(
    r"^\*\*(Status|Tier|Date|Number|Bound|Why it matters|Anchor|Re-derive|Defense)\:\*\*\s*(.+)$", re.M)
BACKTICKED = re.compile(r"`([^`]+)`")
# The headline is the heading with its id and separator stripped — what a citer actually reads.
HEAD_TITLE = re.compile(rf"^#{{2,6}}\s+(?:F-)?{NUM}\s*[·—–:.-]*\s*(.*)$")
HEADLINE_WORDS = 24
# Codes in a headline: a reader cannot expand them, and they date the row to a numbering scheme.
HEADLINE_CODE = re.compile(rf"[FC]-{NUM}|§")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATE_WORDS = 500
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
    # The ledger has been layered: every row is an interface with its defense at a Defense path.
    # Off by default — S7 would otherwise fire on every row of every ledger not migrated yet.
    layered: bool = False
    # Where this lab keeps its ledgers. The convention is record/findings.md and
    # record/claims.md, and that stays the default. A lab migrating onto the ladder
    # may already hold its ledger somewhere else with hundreds of live by-path
    # references into it (design-space-lab: docs/papers/proofs-rot/numbers.md); making
    # it move the file before the gate will run is how a migration gets abandoned.
    # Point the gate at the real file, move it later, on purpose.
    findings_rel: str = "record/findings.md"
    claims_rel: str = "record/claims.md"
    _pin_ids_cache: dict = field(default_factory=dict)
    _defense_linked: set[Path] = field(default_factory=set)  # resolved **Defense:** paths that exist

    @property
    def findings_path(self) -> Path:
        return self.root / self.findings_rel

    @property
    def claims_path(self) -> Path:
        return self.root / self.claims_rel

    def defense_pages(self) -> list[Path]:
        """Every defense page: the ones rows link to, plus any sitting in the conventional
        directory. The links are what matters — a lab may keep its long forms anywhere — but a
        page that exists and is not yet linked is still a record document that has to declare
        itself. `check_findings` fills `_defense_linked`, so it must run first (it already does).
        """
        found = set(self._defense_linked)
        conventional = self.root / "record" / "findings"
        if conventional.is_dir():
            found.update(p.resolve() for p in conventional.glob("*.md"))
        return sorted(found)

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


def _headline(body: str) -> str:
    """The row's headline — the heading line minus its id and separator."""
    m = HEAD_TITLE.match(body.partition("\n")[0])
    return m.group(1).strip() if m else ""


def _is_iso_date(value: str) -> bool:
    """YYYY-MM-DD *and* a real calendar day. `2026-13-45` is the right shape and no day at all.

    The shape is checked first because date.fromisoformat also accepts `20260916` and full
    timestamps, neither of which the chronicle reads.
    """
    if not ISO_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _path_field(lab: Lab, ident: str, rel: str, line: int, kind: str, value: str) -> list[Problem]:
    """H2 — every backticked path in an Anchor / Defense field resolves.

    The templates keep their example row inside a fenced block, spelled `## F-<n>`, so a
    scaffolded lab has no row here to fail on — the ledger is empty until the lab writes one.
    """
    probs: list[Problem] = []
    for target in BACKTICKED.findall(value):
        if not _anchor_ok(lab, target):
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} {kind} `{target}` does not resolve "
                    "(no such path, and no matching pin in record/pins.json)",
                )
            )
        elif kind == "defense" and ":" not in target:
            # remember where this lab actually keeps its long forms, so the record checks find
            # them wherever they are rather than only under record/findings/
            page = (lab.root / target.lstrip("/")).resolve()
            if page.is_file():
                lab._defense_linked.add(page)
    return probs


def check_findings(lab: Lab) -> list[Problem]:
    """H1 + H2 — findings are well-formed and their evidence is reachable.

    Plus the voice rules that keep a row an interface rather than a second essay: S3-S5 on every
    row, S7 only where the lab says its ledger is layered. All four warn and never fail.
    """
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

        probs += _path_field(lab, ident, rel, line, "anchor", fields.get("Anchor", ""))
        # The defense is a path like an anchor is a path: if it does not resolve, the row's
        # long form is unreachable and the interface points at nothing.
        probs += _path_field(lab, ident, rel, line, "defense", fields.get("Defense", ""))
        # ...and an unbackticked defense would be checked by nothing at all, while still
        # satisfying S7 — the one hard check this field adds, defeated by forgetting a backtick.
        if "Defense" in fields and not BACKTICKED.search(fields["Defense"]):
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} defense path is not a backticked path",
                )
            )

        if "Re-derive" in fields and not BACKTICKED.search(fields["Re-derive"]):
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} re-derivation is not a backticked command",
                )
            )

        title = _headline(body)
        words = len(title.split())
        if words > HEADLINE_WORDS:
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} headline is {words} words (limit {HEADLINE_WORDS}) — the row is "
                    "the interface; the argument belongs in its **Defense:** page",
                    hard=False,
                )
            )
        codes = sorted(set(HEADLINE_CODE.findall(title)) | {f"{p}:" for p in lab.pins if f"{p}:" in title})
        if codes:
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} headline carries {', '.join(codes)} — codes are links, not content",
                    hard=False,
                )
            )

        banked = fields.get("Date", "")
        if banked and not _is_iso_date(banked):
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} **Date:** {banked!r} is not a real YYYY-MM-DD day — the chronicle "
                    "cannot read it, and falls back to dating the row by git archaeology",
                    hard=False,
                )
            )

        if lab.layered and "Defense" not in fields:
            probs.append(
                Problem(
                    f"{rel}:{line}",
                    f"{ident} has no **Defense:** field — a layered row points at its long "
                    f"form (record/findings/{ident}.md)",
                    hard=False,
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
    # A defense page is an authored record document: it cites findings and it names pins, and
    # nothing else scans it (record/*.md is deliberately not recursive).
    out.extend(lab.defense_pages())
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
    targets.extend(lab.defense_pages())
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
    # Content pages only. If this ever scans record/, exempt the defense pages: a defense page is
    # its own finding's evidence, so its numbers are anchored by the row it defends.
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


def check_state_size(lab: Lab) -> list[Problem]:
    """S6 — STATE says what is running and why, and points at the record for the rest (soft).

    A STATE.md that grows past a screen has started to be a second logbook: an append-only record
    kept in a file whose whole contract is that it is overwritten.
    """
    path = lab.root / "ops" / "STATE.md"
    if not path.is_file():
        return []
    words = len(path.read_text(encoding="utf-8", errors="replace").split())
    if words <= STATE_WORDS:
        return []
    return [
        Problem(
            "ops/STATE.md",
            f"{words} words (limit {STATE_WORDS}) — STATE is a pointer, not a record; "
            "the detail belongs in a mission or a logbook",
            hard=False,
        )
    ]


def load_lab(root: Path) -> Lab:
    cfg = {"content": "content"}
    cfg.update(_load_config(root))
    lab = Lab(
        root=root.resolve(),
        content=(root / cfg["content"]).resolve(),
        alias=cfg.get("citation_alias") == "section",
        layered=cfg.get("findings_layered") is True,
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
        check_twins, check_links, check_uncited_numbers, check_state_size,
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

# The layered row: a short interface, with the long form at the Defense path.
LAYERED_FINDINGS = """# Findings — LIVE

## F-1 · The floor does not move under mining
**Status:** BANKED
**Tier:** reviewer-gated
**Date:** 2026-08-25
**Number:** 2 survivors of 5000 candidates, 0 of 6 converted
**Bound:** one substrate and one miner — it says nothing about a second engine.
**Why it matters:** mining is not the lever it looks like.
**Anchor:** `evidence/mining.tsv`
**Re-derive:** `awk -F'\\t' '$3=="survivor"' evidence/mining.tsv | wc -l`
**Defense:** `record/findings/F-1.md`
"""

# Everything the voice rules exist to catch, in one row: a headline that argues instead of
# stating, carries codes a reader cannot expand, and a date the chronicle cannot read.
NOISY_FINDINGS = """# Findings — LIVE

## F-1 · The floor does not move under mining, which is the same conclusion F-2 reached on the second substrate under a differently parameterised miner, at §4
**Status:** BANKED
**Date:** 2026-8-25
**Anchor:** `evidence/mining.tsv`
**Re-derive:** `wc -l evidence/mining.tsv`
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

        # The layered row: the Defense path is checked exactly as an anchor is.
        layered = _plant(tmp / "t1", LAYERED_FINDINGS, {
            "record/findings/F-1.md": "# F-1 — the defense — LIVE\n\nPredictions as scored.\n",
        })
        res = run(layered)
        expect("defense-ok", not [q for q in res if q.hard],
               f"a layered row with a resolving defense was flagged: {[q.render() for q in res if q.hard]}")
        expect("defense-quiet", not [q for q in res if "headline" in q.message or "Date" in q.message],
               f"a well-formed layered row warned: {[q.render() for q in res]}")

        dangling = _plant(tmp / "t2", LAYERED_FINDINGS.replace("F-1.md`", "F-404.md`"), {
            "record/findings/F-1.md": "# F-1 — the defense — LIVE\n\nPredictions as scored.\n",
        })
        msgs = " ".join(q.message for q in run(dangling) if q.hard)
        expect("H2-defense", "defense `record/findings/F-404.md` does not resolve" in msgs,
               f"a dangling defense path was not caught: {msgs}")

        # The voice rules: they fire, and they never turn into errors.
        noisy = _plant(tmp / "t3", NOISY_FINDINGS, {})
        res = run(noisy)
        warns = " ".join(q.message for q in res if not q.hard)
        expect("S3", "headline is 25 words (limit 24)" in warns, f"long headline not warned: {warns}")
        expect("S4", "codes are links, not content" in warns and "F-2" in warns and "§" in warns,
               f"ids in a headline not warned: {warns}")
        expect("S5", "is not a real YYYY-MM-DD day" in warns, f"malformed Date not warned: {warns}")
        expect("voice-soft", not [q for q in res if q.hard],
               f"a voice rule leaked into the hard findings: {[q.render() for q in res if q.hard]}")

        # A declared pin's prefix is a code too — `dsl:F-12` in a headline reads as machinery.
        pinhead = _plant(tmp / "t4", GOOD_FINDINGS.replace(
            "## F-1 · The floor", "## F-1 · dsl:F-12 says the floor"), {
            "record/pins.json": '{"dsl": {"repo": "x", "sha": "y"}}',
        })
        warns = " ".join(q.message for q in run(pinhead) if not q.hard)
        expect("S4-pin", "dsl:" in warns and "codes are links" in warns,
               f"a pin-qualified id in a headline was not warned: {warns}")

        # STATE is overwritten, not appended to: past a screen it has become a second logbook.
        bigstate = _plant(tmp / "t5", GOOD_FINDINGS, {
            "ops/STATE.md": "# STATE — LIVE\n\n" + "status " * 600,
        })
        res = run(bigstate)
        expect("S6", any("STATE is a pointer, not a record" in q.message and not q.hard for q in res),
               f"an oversized STATE.md was not warned: {[q.render() for q in res]}")
        smallstate = _plant(tmp / "t6", GOOD_FINDINGS, {
            "ops/STATE.md": "# STATE — LIVE\n\nRunning: nothing. Next: the first probe.\n",
        })
        expect("S6-quiet", not any("STATE is a pointer" in q.message for q in run(smallstate)),
               "a short STATE.md was warned")

        # An unbackticked defense path is checked by nothing and silences S7 — so it is an error.
        bare = _plant(tmp / "t9", LAYERED_FINDINGS.replace("`record/findings/F-1.md`", "record/findings/F-1.md"), {
            "record/findings/F-1.md": "# F-1 — the defense — LIVE\n\nPredictions as scored.\n",
        }, cfg={"findings_layered": True})
        res = run(bare)
        expect("H2-defense-bare", any("defense path is not a backticked path" in q.message and q.hard for q in res),
               f"an unbackticked defense was not caught: {[q.render() for q in res]}")
        expect("H2-defense-bare-not-S7", not any("has no **Defense:**" in q.message for q in res),
               "an unbackticked defense both silenced S7 and escaped the path check")

        # A defense page is a record document: it is read for citations, pins and its status
        # banner, and it is not second-guessed for uncited numbers.
        defended = _plant(tmp / "t10", LAYERED_FINDINGS, {
            "record/findings/F-1.md": "# F-1 — the defense — LIVE\n\nRests on F-1; compare dsl:F-3.\n",
        })
        msgs = " ".join(q.message for q in run(defended) if q.hard)
        expect("H3-defense", "cites F-404" not in msgs, "fixture drift")
        expect("H7-defense", "not declared in record/pins.json" in msgs,
               f"a defense page's undeclared pin was not seen: {msgs}")
        ghosted = _plant(tmp / "t11", LAYERED_FINDINGS, {
            "record/findings/F-1.md": "# F-1 — the defense — LIVE\n\nSuperseded by F-404.\n",
        })
        msgs = " ".join(q.message for q in run(ghosted) if q.hard)
        expect("H3-defense-dangling", "cites F-404" in msgs,
               f"a defense page citing a finding that does not exist was not caught: {msgs}")
        unbannered = _plant(tmp / "t12", LAYERED_FINDINGS, {
            "record/findings/F-1.md": "# F-1 — the defense\n\nNo status anywhere near the top.\n",
        })
        msgs = " ".join(q.message for q in run(unbannered) if q.hard)
        expect("H5-defense", "no status in the opening lines" in msgs,
               f"a defense page with no status banner was not caught: {msgs}")
        # ...and wherever the row says it lives, not only under record/findings/.
        elsewhere = _plant(tmp / "t13", LAYERED_FINDINGS.replace(
            "`record/findings/F-1.md`", "`record/defenses/F-1.md`"), {
            "record/defenses/F-1.md": "# F-1 — the defense\n\nSuperseded by F-404.\n",
        })
        msgs = " ".join(q.message for q in run(elsewhere) if q.hard)
        expect("defense-nondefault", "no status in the opening lines" in msgs and "cites F-404" in msgs,
               f"a defense page at a non-default path was not linted: {msgs}")

        # A date of the right shape that is no day at all.
        badday = _plant(tmp / "t14", LAYERED_FINDINGS.replace("2026-08-25", "2026-13-45"), {
            "record/findings/F-1.md": "# F-1 — the defense — LIVE\n\nPredictions as scored.\n",
        })
        res = run(badday)
        expect("S5-calendar", any("is not a real YYYY-MM-DD day" in q.message and not q.hard for q in res),
               f"an impossible date passed the shape check: {[q.render() for q in res]}")

        # The row template is an example, not a row: fenced, and spelled `## F-<n>`, so it parses
        # as nothing at all rather than as a finding whose placeholder paths do not resolve.
        example = _plant(tmp / "t15", (Path(__file__).parent.parent / "templates/record/findings.md")
                         .read_text(encoding="utf-8"), {})
        res = run(example)
        expect("template-clean", not [q for q in res if q.hard],
               f"the scaffolded row template reports errors: {[q.render() for q in res if q.hard]}")
        expect("template-empty", any("no `## F-<n>` sections found" in q.message for q in res),
               f"the template's example row was parsed as a real row: {[q.render() for q in res]}")

        # A missing Defense is only a warning once the lab says its ledger is layered.
        unmigrated = _plant(tmp / "t7", GOOD_FINDINGS, {})
        expect("S7-off", not any("**Defense:**" in q.message for q in run(unmigrated)),
               "a lab that has not migrated was warned about Defense")
        migrated = _plant(tmp / "t8", GOOD_FINDINGS, {}, cfg={"findings_layered": True})
        res = run(migrated)
        expect("S7", any("has no **Defense:** field" in q.message and not q.hard for q in res),
               f"a layered lab's undefended row was not warned: {[q.render() for q in res]}")

        # Default stays the convention: no config, no relocation.
        missing = _plant(tmp / "r2", GOOD_FINDINGS, {})
        (missing / "record" / "findings.md").unlink()
        msgs = " ".join(q.message for q in run(missing) if q.hard)
        expect("default-path", "no findings ledger" in msgs,
               "a lab with no ledger at the default path was not reported")

        # The config file: kit.json is read first, the deprecated lab.json second — a lab that
        # has renamed it keeps every setting (here, the relocated ledger).
        renamed = _plant(tmp / "kitjson", GOOD_FINDINGS, {}, {"findings": "ledger/findings.md"})
        (renamed / "ledger").mkdir()
        (renamed / "record" / "findings.md").rename(renamed / "ledger" / "findings.md")
        (renamed / "lab.json").rename(renamed / "kit.json")
        expect("kit.json", moved_ids(renamed) == {"F-1"} and _find_config_name(renamed) == "kit.json",
               "a lab whose config is kit.json lost its settings")
        (renamed / "lab.json").write_text(json.dumps({"findings": "nowhere.md"}), encoding="utf-8")
        expect("kit.json-first", moved_ids(renamed) == {"F-1"},
               "lab.json must not override kit.json when both exist")

    if failures:
        print("ladder_lint selftest FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ladder_lint selftest ok (53 planted cases)")
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

    cfg = _load_config(root)
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
        print('not failing the gate — set "ladder": "strict" in kit.json once this is clean')
    return 0


if __name__ == "__main__":
    sys.exit(main())
