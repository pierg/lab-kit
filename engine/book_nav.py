#!/usr/bin/env python3
"""Discover book / library navigation from the filesystem.

Convention for content/books/<slug>/:
  1. index.html first (book hub)
  2. NN-*.html sorted by chapter number
  3. other *.html alphabetically (doubts, drills, …)

Optional thin override: content/books/<slug>/book.json
  {
    "homeLabel": "Proofs forever",          # default: index <title> / slug
    "homeHref": "index.html",
    "order": ["doubts.html", "drills.html"], # reorder non-numbered pages only
    "chapters": ["index.html", "01-a.html"], # full order override (rare)
    "labels": { "07-pe.html": "07 PE" },
    "planned": [
      { "file": "11-x.html", "label": "11 X", "title": "Coming soon" }
    ]
  }

Writes (committed artifacts; regenerate via lint / check):
  content/books/<slug>/nav.json
  content/catalog.json
"""

from __future__ import annotations

import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent))

import argparse
import html as html_mod
import json
import re
import sys
from pathlib import Path

from paths import CONTENT, LAB_ROOT  # noqa: E402  (kit path resolver)

ROOT = LAB_ROOT
BOOKS = CONTENT / "books"
NUMBERED = re.compile(r"^(\d+)-.+\.html$", re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.I | re.S)
H3_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.I | re.S)
DEFN_RE = re.compile(
    r'<blockquote[^>]*class="[^"]*\bdefn\b[^"]*"[^>]*>(.*?)</blockquote>',
    re.I | re.S,
)
SUB_RE = re.compile(r'<p[^>]*class="[^"]*\bsub\b[^"]*"[^>]*>(.*?)</p>', re.I | re.S)
TAGS_META_RE = re.compile(
    r'<meta[^>]*name=["\']tags["\'][^>]*content=["\']([^"\']*)["\']', re.I
)
TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", html_mod.unescape(TAG_RE.sub("", text))).strip()


def _title_of(html: Path) -> str:
    try:
        text = html.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return html.stem
    m = TITLE_RE.search(text)
    if m:
        return _strip_tags(m.group(1))
    m = H1_RE.search(text)
    if m:
        return _strip_tags(m.group(1))
    return html.stem


def _label_from_file(name: str) -> str:
    if name == "index.html":
        return "Hub"
    stem = name[: -len(".html")] if name.endswith(".html") else name
    m = NUMBERED.match(name)
    if m:
        rest = stem.split("-", 1)[1] if "-" in stem else stem
        return f"{int(m.group(1)):02d} {rest.replace('-', ' ').title()}"
    return stem.replace("-", " ").title()


def _load_book_json(book_dir: Path) -> dict:
    path = book_dir / "book.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"{path.relative_to(ROOT)}: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit(f"{path.relative_to(ROOT)}: must be a JSON object")
    return data


def _discover_files(book_dir: Path) -> list[str]:
    return sorted(p.name for p in book_dir.glob("*.html"))


def _default_order(files: list[str], extras_order: list[str] | None) -> list[str]:
    index = [f for f in files if f == "index.html"]
    numbered: list[tuple[int, str]] = []
    other: list[str] = []
    for f in files:
        if f == "index.html":
            continue
        m = NUMBERED.match(f)
        if m:
            numbered.append((int(m.group(1)), f))
        else:
            other.append(f)
    numbered_files = [f for _, f in sorted(numbered, key=lambda t: (t[0], t[1]))]
    if extras_order:
        seen = set(extras_order)
        ordered_other = [f for f in extras_order if f in other]
        ordered_other += sorted(f for f in other if f not in seen)
    else:
        ordered_other = sorted(other)
    return index + numbered_files + ordered_other


def build_book_nav(book_dir: Path) -> dict:
    cfg = _load_book_json(book_dir)
    files = _discover_files(book_dir)
    if not files:
        raise SystemExit(f"{book_dir.relative_to(ROOT)}: no HTML pages")

    labels = cfg.get("labels") or {}
    if not isinstance(labels, dict):
        raise SystemExit(f"{book_dir / 'book.json'}: labels must be an object")

    if cfg.get("chapters"):
        chapters_spec = cfg["chapters"]
        if not isinstance(chapters_spec, list) or not all(
            isinstance(x, str) for x in chapters_spec
        ):
            raise SystemExit(f"{book_dir / 'book.json'}: chapters must be a string list")
        order = list(chapters_spec)
        for f in order:
            if f not in files:
                raise SystemExit(
                    f"{book_dir.relative_to(ROOT)}: chapters lists missing file {f}"
                )
        for f in files:
            if f not in order:
                raise SystemExit(
                    f"{book_dir.relative_to(ROOT)}: {f} exists but not in book.json chapters"
                )
    else:
        extras = cfg.get("order")
        if extras is not None and (
            not isinstance(extras, list) or not all(isinstance(x, str) for x in extras)
        ):
            raise SystemExit(f"{book_dir / 'book.json'}: order must be a string list")
        order = _default_order(files, extras)

    chapters: list[dict] = []
    for f in order:
        title = _title_of(book_dir / f)
        label = labels.get(f) or _label_from_file(f)
        chapters.append(
            {"file": f, "label": label, "title": title, "status": "landed"}
        )

    for item in cfg.get("planned") or []:
        if not isinstance(item, dict) or "file" not in item:
            raise SystemExit(
                f"{book_dir / 'book.json'}: planned entries need at least file"
            )
        f = item["file"]
        chapters.append(
            {
                "file": f,
                "label": item.get("label") or labels.get(f) or _label_from_file(f),
                "title": item.get("title") or item.get("label") or _label_from_file(f),
                "status": "planned",
            }
        )

    home_label = cfg.get("homeLabel")
    if not home_label:
        idx = book_dir / "index.html"
        home_label = _title_of(idx) if idx.is_file() else book_dir.name
    home_href = cfg.get("homeHref") or "index.html"

    return {
        "homeLabel": home_label,
        "homeHref": home_href,
        "chapters": chapters,
    }


def build_catalog() -> dict:
    books: list[dict] = []
    if BOOKS.is_dir():
        for d in sorted(BOOKS.iterdir()):
            if not d.is_dir() or not (d / "index.html").is_file():
                continue
            books.append(
                {
                    "slug": d.name,
                    "title": _title_of(d / "index.html"),
                    "href": f"/content/books/{d.name}/",
                }
            )

    def pages(folder: str) -> list[dict]:
        """Folder-per-item genres: content/<folder>/<slug>/index.html."""
        d = CONTENT / folder
        if not d.is_dir():
            return []
        out: list[dict] = []
        for p in sorted(child / "index.html" for child in d.iterdir() if child.is_dir()):
            out.append(
                {
                    "slug": p.parent.name,
                    "title": _title_of(p),
                    "href": f"/content/{folder}/{p.parent.name}/",
                }
            )
        return out

    def flat(folder: str) -> list[dict]:
        """Flat-file genres: content/<folder>/<slug>.html."""
        d = CONTENT / folder
        if not d.is_dir():
            return []
        out: list[dict] = []
        for p in sorted(d.glob("*.html")):
            out.append(
                {
                    "slug": p.stem,
                    "title": _title_of(p),
                    "href": f"/content/{folder}/{p.stem}.html",
                }
            )
        return out

    return {
        "books": books,
        "entries": pages("entries"),
        "concepts": pages("concepts"),
        "projects": pages("projects"),
        "hubs": flat("hubs"),
        "notes": flat("notes"),
    }


def write_json(path: Path, data: object) -> bool:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _snippet(html: str, pattern: re.Pattern, limit: int = 200) -> str:
    m = pattern.search(html)
    if not m:
        return ""
    return _strip_tags(m.group(1))[:limit]


def _all(html: str, pattern: re.Pattern, limit: int = 8) -> list[str]:
    out: list[str] = []
    for m in pattern.finditer(html):
        text = _strip_tags(m.group(1))
        if text:
            out.append(text[:120])
        if len(out) >= limit:
            break
    return out


KIND_BY_FOLDER = {
    "books": "book",
    "entries": "entry",
    "concepts": "concept",
    "hubs": "hub",
    "notes": "note",
    "projects": "project",
}


def _kind_of(rel: Path) -> str:
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "content":
        return KIND_BY_FOLDER.get(parts[1], "page")
    return "page"


def _record(html_path: Path) -> dict:
    rel = html_path.relative_to(ROOT)
    text = html_path.read_text(encoding="utf-8", errors="replace")
    title = _snippet(text, TITLE_RE, 200) or _snippet(text, H1_RE, 200) or html_path.stem
    sub = _snippet(text, SUB_RE, 240)
    defn = _snippet(text, DEFN_RE, 400)
    tags_match = TAGS_META_RE.search(text)
    tags = [t.strip() for t in tags_match.group(1).split(",")] if tags_match else []
    href = "/" + str(rel).replace("\\", "/")
    if href.endswith("/index.html"):
        href = href[: -len("index.html")]
    return {
        "title": title,
        "sub": sub,
        "defn": defn,
        "headings": _all(text, H2_RE) + _all(text, H3_RE, 4),
        "tags": tags,
        "kind": _kind_of(rel),
        "href": href,
    }


def build_search_index() -> list[dict]:
    out: list[dict] = []
    if not CONTENT.is_dir():
        return out
    for p in sorted(CONTENT.rglob("*.html")):
        rel = p.relative_to(ROOT)
        if "archive" in rel.parts:
            continue
        # skip generated / infrastructure pages
        if p.name == "search.html":
            continue
        out.append(_record(p))
    return out


HREF_RE = re.compile(r'href="(/content/[^"#?]*)(?:[#?][^"]*)?"', re.I)


def _normalize_href(href: str) -> str:
    """Canonicalize an internal href for backlink matching.

    /content/foo/index.html  →  /content/foo/
    /content/foo/            →  /content/foo/  (unchanged)
    /content/foo/bar.html    →  /content/foo/bar.html
    """
    if href.endswith("/index.html"):
        return href[: -len("index.html")]
    return href


def _self_href(html_path: Path) -> str:
    rel = html_path.relative_to(ROOT)
    href = "/" + str(rel).replace("\\", "/")
    return _normalize_href(href)


def build_backlinks() -> dict[str, list[dict]]:
    """Reverse-index: for each target /content/... href, the pages that link to it."""
    if not CONTENT.is_dir():
        return {}
    pages: list[tuple[Path, str, str, str]] = []
    for p in sorted(CONTENT.rglob("*.html")):
        rel = p.relative_to(ROOT)
        if "archive" in rel.parts or p.name == "search.html":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        title = _snippet(text, TITLE_RE, 200) or _snippet(text, H1_RE, 200) or p.stem
        kind = _kind_of(rel)
        self_href = _self_href(p)
        pages.append((p, self_href, title, kind))

    # Second pass: scan links, build reverse index
    reverse: dict[str, list[dict]] = {}
    seen_pairs: set[tuple[str, str]] = set()
    for p, self_href, title, kind in pages:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in HREF_RE.finditer(text):
            target = _normalize_href(m.group(1))
            if target == self_href:
                continue  # don't self-link
            key = (self_href, target)
            if key in seen_pairs:
                continue  # dedup multiple links per page → target
            seen_pairs.add(key)
            reverse.setdefault(target, []).append(
                {"title": title, "href": self_href, "kind": kind}
            )
    # sort each target's inbound list by kind then title
    for target in reverse:
        reverse[target].sort(key=lambda x: (x["kind"], x["title"].lower()))
    return dict(sorted(reverse.items()))


def regenerate() -> list[str]:
    written: list[str] = []
    if BOOKS.is_dir():
        for d in sorted(BOOKS.iterdir()):
            if not d.is_dir() or not (d / "index.html").is_file():
                continue
            nav = build_book_nav(d)
            path = d / "nav.json"
            if write_json(path, nav):
                written.append(str(path.relative_to(ROOT)))
    catalog_path = CONTENT / "catalog.json"
    if write_json(catalog_path, build_catalog()):
        written.append(str(catalog_path.relative_to(ROOT)))
    search_path = CONTENT / "search-index.json"
    if write_json(search_path, build_search_index()):
        written.append(str(search_path.relative_to(ROOT)))
    backlinks_path = CONTENT / "backlinks.json"
    if write_json(backlinks_path, build_backlinks()):
        written.append(str(backlinks_path.relative_to(ROOT)))
    return written


def _expected_nav_files() -> dict[Path, object]:
    expected: dict[Path, object] = {}
    if BOOKS.is_dir():
        for d in sorted(BOOKS.iterdir()):
            if d.is_dir() and (d / "index.html").is_file():
                expected[d / "nav.json"] = build_book_nav(d)
    expected[CONTENT / "catalog.json"] = build_catalog()
    expected[CONTENT / "search-index.json"] = build_search_index()
    expected[CONTENT / "backlinks.json"] = build_backlinks()
    return expected


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate library nav JSON.")
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if committed nav JSON differs from discovery",
    )
    args = ap.parse_args()

    if args.check:
        dirty: list[str] = []
        for path, data in _expected_nav_files().items():
            text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            cur = path.read_text(encoding="utf-8") if path.is_file() else None
            if cur != text:
                dirty.append(str(path.relative_to(ROOT)))
        if dirty:
            print("nav out of date — run: python3 engine/book_nav.py")
            print("\n".join(dirty))
            return 1
        print("nav up to date")
        return 0

    written = regenerate()
    if written:
        print("wrote " + ", ".join(written))
    else:
        print("nav unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
