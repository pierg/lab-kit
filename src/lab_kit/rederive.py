"""Run a result's re-derive command from the lab root and compare what it prints with its number."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from folio.documents import Document

from .errors import LabError
from .lab import Lab
from .records import script_env


@dataclass
class Outcome:
    ok: bool
    expected: str
    printed: str
    detail: str  # why it failed, or "" when it passed


def number_of(doc: Document) -> str:
    return str(doc.meta.get("number", "")).strip()


def run(lab: Lab, doc: Document) -> Outcome:
    command = doc.meta.get("rederive")
    expected = number_of(doc)
    if not isinstance(command, str) or not command.strip():
        return Outcome(False, expected, "", "has no `rederive` command")
    try:
        done = subprocess.run(command, shell=True, cwd=lab.root, capture_output=True, text=True,
                              timeout=lab.settings.rederive_timeout, check=False, env=script_env())
    except subprocess.TimeoutExpired:
        return Outcome(False, expected, "", f"`{command}` ran past the {lab.settings.rederive_timeout}s timeout")
    printed = done.stdout.strip()
    if done.returncode != 0:
        tail = done.stderr.strip().splitlines()[-1:] or [""]
        return Outcome(False, expected, printed, f"`{command}` exited {done.returncode}: {tail[0]}".rstrip(": "))
    if printed != expected:
        return Outcome(False, expected, printed, f"`{command}` printed `{printed}`, not the number `{expected}`")
    return Outcome(True, expected, printed, "")


def result_doc(lab: Lab, ident: str) -> Document:
    docs = lab.library().find(ident, "result")
    if not docs:
        raise LabError(f"no result `{ident}` in the library")
    return docs[0]


def live_results(lab: Lab) -> list[Document]:
    return [d for d in lab.library().documents if d.is_a("result") and d.status == "live"]
