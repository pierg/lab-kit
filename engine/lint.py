#!/usr/bin/env python3
"""Lint a lab's reader pages against the shared shell contract.

    python3 kit/engine/lint.py
    python3 kit/engine/lint.py content/entries/foo

Checks (content HTML only):
  1. no raw hex colors — use the shell's .hb tokens
  2. classes that look like shell vocabulary are actually in the allowlist
  3. every page loads /shell/lib.css
  4. no reference to the retired book.js / book.css
  5. nav.json / catalog.json match filesystem discovery (regenerated in place)

This is the *form* lint. The *ladder* lint — every number traces to a finding — is
`kit/tools/ladder_lint.py`, and the two are deliberately separate: form is about
whether a page renders like the rest of the library, the ladder is about whether it
is allowed to say what it says.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CONTENT, LAB_ROOT  # noqa: E402

HEX = re.compile(r"(?<![\w-])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
CLASS_ATTR = re.compile(r'\bclass="([^"]*)"')
SHELL_LINK = re.compile(r'href="/shell/lib\.css"')
BOOK_JS = re.compile(r'src=["\']book\.js["\']')
BOOK_CSS = re.compile(r"book\.css")

# Classes that claim to be shell vocabulary — must be known.
SHELLISH = re.compile(r"^(?:ev-|v-|st-|sw-|hb-|hb$|own$)")

ALLOWED = {
    # root / chrome
    "hb", "sub", "muted", "mono", "q", "anchors", "idx", "cols", "card",
    "check", "fcard", "ans", "back", "own", "law", "defn", "defn-name",
    "defn-link", "defn-pop", "defn-pop-name", "formula",
    "active", "here", "sep", "dhead", "did",
    # chips
    "ev", "ev-m", "ev-b", "ev-d", "ev-o",
    "v", "v-kept", "v-disc", "v-rej", "v-unt", "v-gen",
    "st", "st-done", "st-plan", "st-open",
    "sw-reach", "sw-cert", "sw-target", "sw-slack", "sw-leak",
    "sw-gen", "sw-judge", "sw-world",
    # lanes / motifs
    "lane", "lane-reach", "lane-cert", "lane-judge", "lane-gen",
    "lane-world", "lane-kept", "lane-baseline",
    "twin", "twin-tag", "twin-row", "twin-k",
    "split", "split-tag", "note", "note-warn",
    # widget primitives
    "tbtn", "on", "cyc", "prow", "cur", "skip", "nrow", "drawer", "hyp",
    "cell", "cellrow", "vline", "reach", "inS", "cap", "bad", "cti", "dead",
    "tag", "lbl", "gate", "gline", "g", "pass", "fail", "flat", "stop",
    "lchip", "new", "cbar", "ho", "mtable",
    "wcap", "wcap-sm", "wcap-md", "wcap-lg",
    "k", "d", "r", "c", "sel", "run", "viol",
    # injected by lib.js rather than authored in HTML
    "hb-nav", "hb-home", "hb-foot",
    "hb-has-shell", "hb-no-side", "hb-stage", "hb-side", "hb-side-open",
    "hb-side-toggle", "hb-side-backdrop", "hb-side-section", "hb-side-lib",
    "hb-side-search",
    "hb-side-label", "hb-side-list", "hb-toc", "hb-toc-label",
    "hb-kind", "hb-kind-book", "hb-kind-entry", "hb-kind-concept",
    "hb-kind-hub", "hb-kind-note", "hb-kind-project", "hb-kind-page",
    "hb-kind-paper",
}


def _iter_html(paths: list[Path]) -> list[Path]:
    if not paths:
        return sorted(CONTENT.rglob("*.html")) if CONTENT.is_dir() else []
    out: list[Path] = []
    for p in paths:
        p = p.resolve() if p.is_absolute() else (LAB_ROOT / p).resolve()
        if p.is_dir():
            out.extend(sorted(p.rglob("*.html")))
        else:
            out.append(p)
    return out


def lint_file(path: Path) -> list[str]:
    rel = path.relative_to(LAB_ROOT)
    text = path.read_text(encoding="utf-8", errors="replace")
    problems: list[str] = []

    for m in HEX.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        problems.append(f"{rel}:{line}: hex color {m.group(0)} — use shell tokens")

    if BOOK_CSS.search(text):
        problems.append(f"{rel}: references book.css (retired)")
    if BOOK_JS.search(text):
        problems.append(f"{rel}: references book.js (retired — use book.json + nav.json)")
    if not SHELL_LINK.search(text):
        problems.append(f'{rel}: missing href="/shell/lib.css"')

    for m in CLASS_ATTR.finditer(text):
        for cls in m.group(1).split():
            if SHELLISH.match(cls) and cls not in ALLOWED:
                problems.append(f"{rel}: unknown shell class '{cls}'")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint lab content against the shell contract.")
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--no-nav", action="store_true",
                    help="skip regenerating / checking nav.json + catalog.json")
    args = ap.parse_args()

    if not CONTENT.is_dir():
        print(f"no content directory at {CONTENT} — nothing to lint")
        return 0

    files = [
        p for p in _iter_html(args.paths)
        if p.resolve().is_relative_to(CONTENT.resolve()) and "archive" not in p.parts
    ]

    all_probs: list[str] = []
    for f in files:
        all_probs.extend(lint_file(f))

    books = CONTENT / "books"
    if books.is_dir():
        for d in sorted(books.iterdir()):
            if d.is_dir() and (d / "book.js").is_file():
                all_probs.append(
                    f"{d.relative_to(LAB_ROOT)}/book.js: retired — use book.json "
                    "(optional) and run kit/engine/book_nav.py"
                )

    if not args.no_nav:
        import book_nav  # noqa: WPS433  (same directory, added to sys.path above)

        written = book_nav.regenerate()
        if written:
            print("nav refreshed: " + ", ".join(written))

    if all_probs:
        print("\n".join(all_probs))
        print(f"\n{len(all_probs)} problem(s) in {len(files)} file(s)")
        return 1
    print(f"form lint clean — {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
