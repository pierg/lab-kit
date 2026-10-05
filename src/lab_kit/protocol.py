"""A protocol as lab-kit reads it: its file, status, hash with the status set aside, pins and ids."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from folio.documents import Document
from folio.frontmatter import front_block, sections, split
from folio.errors import FolioError

from .errors import LabError
from .lab import Lab

_STATUS_LINE = re.compile(r"^status:[^\n]*\n?", re.M)
_ITEM_ID = re.compile(r"^\s*[-*]\s+([PD]\d+)\b", re.M)
_YAML_FENCE = re.compile(r"^(```|~~~)\s*ya?ml\s*\n(.*?)^\1\s*$", re.S | re.M)

CONFIG_HEADING = "Pinned configuration"
PREDICTIONS_HEADING = "Predictions"
RULES_HEADING = "Decision rules"


@dataclass
class Protocol:
    slug: str
    doc: Document
    path: str  # from the lab root
    abspath: Path

    @property
    def status(self) -> str:
        return self.doc.status

    def text(self) -> str:
        return self.abspath.read_text(encoding="utf-8")


def find(lab: Lab, slug: str) -> Protocol | None:
    docs = lab.library().find(slug, "protocol")
    if not docs:
        return None
    doc = docs[0]
    main = doc.main
    if main is None:
        return None
    return Protocol(doc.id, doc, lab.doc_path(main.path), main.abspath)


def require(lab: Lab, slug: str) -> Protocol:
    proto = find(lab, slug)
    if proto is None:
        raise LabError(f"no protocol `{slug}` in the library; draft it with folio's write skill first")
    return proto


def hash_text(text: str) -> str:
    """The sha256 of a protocol's text with its front matter's `status` line set aside."""
    span = front_block(text)
    if span is not None:
        start, end = span
        text = text[:start] + _STATUS_LINE.sub("", text[start:end]) + text[end:]
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section(text: str, heading: str, where: str) -> str:
    try:
        _, body = split(text, where)
    except FolioError as exc:
        raise LabError(str(exc)) from exc
    for name, content in sections(body):
        if name.strip() == heading:
            return content
    raise LabError(f"{where}: has no `## {heading}` section")


def pinned_config(text: str, where: str) -> Any:
    """The parsed `yaml` block under `## Pinned configuration`."""
    blocks = _YAML_FENCE.findall(_section(text, CONFIG_HEADING, where))
    if len(blocks) != 1:
        raise LabError(f"{where}: `## {CONFIG_HEADING}` must hold exactly one fenced yaml block")
    try:
        return yaml.safe_load(blocks[0][1])
    except yaml.YAMLError as exc:
        raise LabError(f"{where}: the pinned configuration is not valid YAML: {exc}") from exc


def scored_ids(text: str, where: str) -> list[str]:
    """The prediction ids (`P1`...) and decision-rule ids (`D1`...) the protocol names, in order."""
    found: list[str] = []
    for heading, prefix in ((PREDICTIONS_HEADING, "P"), (RULES_HEADING, "D")):
        ids = [i for i in _ITEM_ID.findall(_section(text, heading, where)) if i.startswith(prefix)]
        if not ids:
            raise LabError(f"{where}: `## {heading}` names no {prefix}-id")
        found.extend(ids)
    return found
