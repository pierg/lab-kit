#!/usr/bin/env python3
"""The lab's page checks — registered in kit.json `checks`, named by the lab's genres.

content-kit's gate knows nothing about findings. A lab's genres name these checks, and the
engine runs them on every page of those genres exactly as it runs its own:

  bound_ids         the first <p class="sub"> seals the page to the rows it tells: at least one
                    <code>F-<n></code> (a pinned cross-lab row, <code>dsl:F-3</code>, counts).
                    Read from the markup a reader is served — a row id inside a comment does not seal.
  defn_no_findings  a concept's definition of record cites no finding: the defn must survive the
                    findings changing, so results are cited below it, never inside it.
  no_findings       the genre carries no results at all.

    python3 kit/tools/checks_lab.py --selftest    # planted fixtures, no lab and no engine needed
"""

from __future__ import annotations

import re
import sys
from types import SimpleNamespace

FINDING = re.compile(r"\bF-\d+(?:\.\d+)*\b")
# A row id as a page cites it: `F-12`, `F-22.1`, or another lab's pinned row, `dsl:F-3`.
BOUND_ID = re.compile(r"<code\b[^>]*>\s*(?:[a-z][a-z0-9_-]*:)?F-\d+(?:\.\d+)*\s*</code>", re.I)
SUB = re.compile(r'<p\b[^>]*class="[^"]*\bsub\b[^"]*"[^>]*>(.*?)</p>', re.I | re.S)
DEFN = re.compile(r'<blockquote\b[^>]*class="[^"]*\bdefn\b[^"]*"[^>]*>(.*?)</blockquote>', re.I | re.S)


def bound_ids(ctx) -> list[str]:
    sub = SUB.search(ctx.served)
    if BOUND_ID.search(sub.group(1) if sub else ""):
        return []
    return [f'{ctx.rel}: the opening line names no finding — a {ctx.genre.name} is sealed to the rows it '
            'tells, so its first <p class="sub"> carries at least one <code>F-<n></code>']


def defn_no_findings(ctx) -> list[str]:
    d = DEFN.search(ctx.text)
    ids = sorted(set(FINDING.findall(d.group(1)))) if d else []
    if not ids:
        return []
    return [f"{ctx.rel}: cites {', '.join(ids)} inside its defn — a definition must survive "
            "findings changing; cite below the defn, not in it"]


def no_findings(ctx) -> list[str]:
    ids = sorted(set(FINDING.findall(ctx.text)))
    return [f"{ctx.rel}: {ctx.genre.name} cites {', '.join(ids)} — this genre carries no results"] if ids else []


CHECKS = {"bound_ids": bound_ids, "defn_no_findings": defn_no_findings, "no_findings": no_findings}


# ----------------------------------------------------------------------------- selftest

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_BURIED = re.compile(r"<(script|style|noscript|template)\b[^>]*>.*?</\1>", re.S | re.I)


def _ctx(html: str, genre: str = "story"):
    served = _BURIED.sub(" ", _COMMENT.sub(" ", html))  # what ckit hands a check as ctx.served
    return SimpleNamespace(rel=f"content/x/{genre}.html", text=html, served=served,
                           genre=SimpleNamespace(name=genre), arg=True)


def _page(sub: str, body: str = "") -> str:
    return f'<main><h1>T</h1><p class="sub">{sub}</p>{body}</main>'


def selftest() -> int:
    failures: list[str] = []
    cases = [
        # (check, html, genre, should fire, what)
        (bound_ids, _page("<b>Status: LIVE</b> — sealed to <code>F-1</code>."), "story", False, "a sealed story"),
        (bound_ids, _page("<b>Status: LIVE</b> — sealed to <code>dsl:F-3</code>."), "story", False,
         "a story sealed to another lab's pinned row"),
        (bound_ids, _page("<b>Status: LIVE</b> — names no row."), "story", True, "an unbound story"),
        (bound_ids, _page("<b>Status: LIVE</b> — row commented out <!-- <code>F-1</code> -->."), "story", True,
         "a row id that only exists inside a comment"),
        (bound_ids, _page("<b>Status: LIVE</b> — F-1 bare, not as code."), "story", True,
         "a bare id rather than a <code> row"),
        (defn_no_findings, _page("LIVE", '<blockquote class="defn"><span class="defn-name">C</span> See F-3.</blockquote>'),
         "concept", True, "a defn that cites a finding"),
        (defn_no_findings, _page("LIVE", '<blockquote class="defn"><span class="defn-name">C</span> Timeless.</blockquote><p>See F-3.</p>'),
         "concept", False, "a finding cited below the defn"),
        (no_findings, _page("LIVE", "<p>Rests on F-2.</p>"), "note", True, "a result in a genre that carries none"),
        (no_findings, _page("LIVE", "<p>No results here.</p>"), "note", False, "a page with no result"),
    ]
    for check, html, genre, fire, what in cases:
        got = check(_ctx(html, genre))
        if bool(got) != fire:
            failures.append(f"{check.__name__}: {what} — expected {'a problem' if fire else 'silence'}, got {got}")
        elif fire and f"content/x/{genre}.html" not in got[0]:
            failures.append(f"{check.__name__}: the problem must name the page: {got[0]}")
    if set(CHECKS) != {"bound_ids", "defn_no_findings", "no_findings"}:
        failures.append(f"CHECKS must register the three checks the lab's genres name: {sorted(CHECKS)}")
    if failures:
        print("checks_lab selftest FAILED:\n- " + "\n- ".join(failures))
        return 1
    print(f"checks_lab selftest ok ({len(cases) + 1} planted cases)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else (print(__doc__) or 0))
