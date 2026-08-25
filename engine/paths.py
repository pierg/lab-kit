#!/usr/bin/env python3
"""Resolve where the lab is, from anywhere inside the kit.

The kit is vendored into a lab as `<lab>/kit/`, so `__file__`'s grandparent is the
*kit* root, not the lab root. Every engine script imports from here rather than
guessing, so a vendored kit and a flat checkout behave identically.

Resolution order for the lab root:

1. `$LAB_ROOT` if set — an explicit override always wins.
2. The nearest ancestor directory containing `lab.json` — the marker file a lab
   writes once at install time.
3. The kit root's parent if the kit root is named `kit` (the vendored layout).
4. The kit root itself (a flat checkout, e.g. the kit's own selftest fixtures).

`lab.json` is also where a lab declares its content directory and port, so those
are configured in one place rather than passed through every call site.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
SHELL = KIT_ROOT / "shell"

DEFAULTS = {"content": "content", "port": 5180, "host": "127.0.0.1", "name": "lab"}


def _find_root() -> Path:
    env = os.environ.get("LAB_ROOT")
    if env:
        return Path(env).resolve()
    for cand in [KIT_ROOT, *KIT_ROOT.parents]:
        if (cand / "lab.json").is_file():
            return cand
    if KIT_ROOT.name == "kit":
        return KIT_ROOT.parent
    return KIT_ROOT


LAB_ROOT = _find_root()


def config() -> dict:
    """The lab's `lab.json`, merged over the defaults. Missing file is fine."""
    cfg = dict(DEFAULTS)
    marker = LAB_ROOT / "lab.json"
    if marker.is_file():
        try:
            cfg.update(json.loads(marker.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{marker}: invalid JSON — {exc}") from exc
    return cfg


CONTENT = LAB_ROOT / config()["content"]


def rel(path: Path) -> str:
    """Path relative to the lab root when possible, else absolute — for messages."""
    try:
        return str(Path(path).resolve().relative_to(LAB_ROOT))
    except ValueError:
        return str(path)
