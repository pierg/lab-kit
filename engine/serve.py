#!/usr/bin/env python3
"""Serve a lab's reader pages as static files — stdlib only, zero deps, no build step.

    make serve                      # http://127.0.0.1:<port>/  (background, port from lab.json)
    make down
    python3 kit/engine/serve.py     # foreground
    python3 kit/engine/serve.py --port 8080 --host 0.0.0.0

Two roots are mounted:

  /shell/...   the kit's shared form (CSS/JS/KaTeX/skeletons) — vendored, identical in every lab
  /...         the lab root, so /content/... resolves to the lab's own pages

That split is why a lab can vendor the kit without copying the shell into its own
content tree, and why every page's absolute `/shell/lib.css` href works unchanged.
"""

from __future__ import annotations

import argparse
import html as html_mod
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CONTENT, LAB_ROOT, SHELL, config  # noqa: E402

CFG = config()
CONTENT_NAME = CFG["content"]


def _esc(text: str) -> str:
    return html_mod.escape(text, quote=False)


def _href(rel: Path) -> str:
    return "/" + str(rel).replace("\\", "/")


def _title_of(html: Path) -> str:
    try:
        for line in html.read_text(encoding="utf-8", errors="replace").splitlines():
            if "<title>" in line:
                return line.split("<title>", 1)[1].split("</title>", 1)[0].strip()
    except OSError:
        pass
    return html.stem


def _books() -> list[tuple[str, Path]]:
    books_dir = CONTENT / "books"
    if not books_dir.is_dir():
        return []
    out: list[tuple[str, Path]] = []
    for d in sorted(books_dir.iterdir()):
        idx = d / "index.html"
        if d.is_dir() and idx.is_file():
            out.append((_title_of(idx) or d.name, idx.relative_to(LAB_ROOT)))
    return out


def _pages(folder: str) -> list[tuple[str, Path]]:
    """Folder-per-item genres: <content>/<folder>/<slug>/index.html."""
    d = CONTENT / folder
    if not d.is_dir():
        return []
    return [
        (_title_of(p), p.relative_to(LAB_ROOT))
        for p in sorted(child / "index.html" for child in d.iterdir() if child.is_dir())
        if p.is_file()
    ]


def _flat(folder: str) -> list[tuple[str, Path]]:
    """Flat-file genres: <content>/<folder>/<slug>.html."""
    d = CONTENT / folder
    if not d.is_dir():
        return []
    return [(_title_of(p), p.relative_to(LAB_ROOT)) for p in sorted(d.glob("*.html"))]


def _list_group(title: str, items: list[tuple[str, Path]], empty: str) -> str:
    if not items:
        return f'<h2>{_esc(title)}</h2><p class="muted">{_esc(empty)}</p>'
    lis = "\n".join(
        f'<li><a href="{_esc(_href(rel))}">{_esc(name)}</a>'
        f'<div class="path">{_esc(_href(rel))}</div></li>'
        for name, rel in items
    )
    return f'<h2>{_esc(title)}</h2>\n<ul class="catalog">\n{lis}\n</ul>'


def _landing() -> bytes:
    name = _esc(str(CFG.get("name", "lab")))
    question = _esc(str(CFG.get("question", "")))
    lede = f'<p class="sub">{question}</p>' if question else ""
    c = CONTENT_NAME
    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<link rel="stylesheet" href="/shell/lib.css">
<script src="/shell/lib.js" defer></script>
<style>
  .catalog {{ list-style: none; padding: 0; }}
  .catalog li {{ margin: 0 0 10px; }}
  .catalog .path {{ color: var(--ink-3); font-size: 12px; }}
  .home-lede {{ background: var(--surface-1); border: 1px solid var(--ring);
                border-radius: 12px; padding: 14px 18px; margin: 18px 0; }}
  .home-lede a.search-cta {{ display: inline-block; margin-top: 6px;
                border: 1.5px solid var(--judge); color: var(--judge);
                border-radius: 999px; padding: 4px 14px; font-weight: 700;
                font-size: 13px; text-decoration: none; }}
  .home-lede a.search-cta:hover {{ background: color-mix(in srgb, var(--judge) 10%, transparent); }}
</style>
</head>
<body class="hb">
<main>
<h1>{name}</h1>
{lede}

<div class="home-lede">
Looking for something? <a class="search-cta" href="/{c}/search.html">Search everything &rarr;</a>
</div>

{_list_group("Papers", _pages("papers"), f"No papers yet — add {c}/papers/<slug>/index.html")}
{_list_group("Books", _books(), f"No books yet — add {c}/books/<slug>/index.html")}
{_list_group("Projects", _pages("projects"), f"No projects yet — add {c}/projects/<slug>/index.html")}
{_list_group("Hubs", _flat("hubs"), f"No hubs yet — add {c}/hubs/<slug>.html")}
{_list_group("Entries", _pages("entries"), f"No entries yet — add {c}/entries/<slug>/index.html")}
{_list_group("Notes", _flat("notes"), f"No notes yet — add {c}/notes/<slug>.html")}
{_list_group("Concepts", _pages("concepts"), f"No concepts yet — add {c}/concepts/<slug>/index.html")}
</main>
</body>
</html>
"""
    return body.encode("utf-8")


def _slug_file(slug: str) -> Path | None:
    """Resolve a bare slug to a page, so /foo redirects to whichever genre owns it."""
    if not slug or "/" in slug or slug in (".", ".."):
        return None
    candidates = (
        CONTENT / "entries" / slug / "index.html",
        CONTENT / "concepts" / slug / "index.html",
        CONTENT / "projects" / slug / "index.html",
        CONTENT / "papers" / slug / "index.html",
        CONTENT / "books" / slug / "index.html",
        CONTENT / "notes" / f"{slug}.html",
        CONTENT / "hubs" / f"{slug}.html",
    )
    for p in candidates:
        if p.is_file():
            return p
    return None


def _dir_listing(directory: Path) -> bytes | None:
    """HTML index for a folder with no index.html (e.g. /content/entries/)."""
    if not directory.is_dir():
        return None
    items: list[tuple[str, Path]] = []
    for child in sorted(directory.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir() and (child / "index.html").is_file():
            items.append((_title_of(child / "index.html"), child.relative_to(LAB_ROOT)))
        elif child.suffix == ".html":
            items.append((_title_of(child), child.relative_to(LAB_ROOT)))
    if not items:
        return None
    heading = directory.relative_to(LAB_ROOT).as_posix()
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{_esc(heading)}</title>"
        '<link rel="stylesheet" href="/shell/lib.css">'
        '<script src="/shell/lib.js" defer></script></head>'
        f'<body class="hb"><main>{_list_group(heading, items, "")}</main></body></html>'
    ).encode("utf-8")


def _resolve(rel_path: str) -> Path | None:
    """Map a URL path to a file, keeping both mounts inside their own root."""
    if rel_path == "shell" or rel_path.startswith("shell/"):
        base, tail = SHELL, rel_path[len("shell") :].lstrip("/")
    else:
        base, tail = LAB_ROOT, rel_path
    target = (base / tail).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


class Handler(BaseHTTPRequestHandler):
    server_version = "lab-kit-serve/1.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(body=False)

    def do_GET(self) -> None:  # noqa: N802
        self._serve(body=True)

    def _send(self, status: int, data: bytes, ctype: str, body: bool) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if body:
            self.wfile.write(data)

    def _serve(self, *, body: bool) -> None:
        path = unquote(urlparse(self.path).path)
        if path in ("", "/"):
            self._send(200, _landing(), "text/html; charset=utf-8", body)
            return

        rel_path = path.lstrip("/")
        target = _resolve(rel_path)
        if target is None:
            self.send_error(403, "Forbidden")
            return

        if target.is_dir():
            idx = target / "index.html"
            if idx.is_file():
                target = idx
            else:
                listing = _dir_listing(target)
                if listing is not None:
                    self._send(200, listing, "text/html; charset=utf-8", body)
                    return
                self.send_error(404, "Not found")
                return

        if not target.is_file():
            found = _slug_file(Path(rel_path).name)
            if found is not None:
                self.send_response(302)
                self.send_header("Location", _href(found.relative_to(LAB_ROOT)))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_error(404, "Not found")
            return

        data = target.read_bytes()
        ctype, _ = mimetypes.guess_type(str(target))
        if ctype is None:
            ctype = "application/octet-stream"
        if (
            ctype.startswith("text/")
            or ctype in ("application/javascript", "application/json", "image/svg+xml")
        ) and "charset" not in ctype:
            ctype = f"{ctype}; charset=utf-8"
        self._send(200, data, ctype, body)


def main() -> None:
    ap = argparse.ArgumentParser(description="Serve a lab's reader pages.")
    ap.add_argument("--host", default=CFG["host"])
    ap.add_argument("--port", type=int, default=CFG["port"])
    ap.add_argument(
        "--lab-root",
        default=None,
        help="the lab this process serves; makes the ps line self-describing so "
             "several labs can serve at once and ctl.sh can find its own",
    )
    args = ap.parse_args()
    if args.lab_root and Path(args.lab_root).resolve() != LAB_ROOT:
        raise SystemExit(
            f"--lab-root {args.lab_root} disagrees with the resolved lab root {LAB_ROOT}"
        )
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"{CFG.get('name', 'lab')} at http://{args.host}:{args.port}/  (root={LAB_ROOT})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
