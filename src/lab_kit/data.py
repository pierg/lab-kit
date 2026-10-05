"""Where lab-kit's shipped method, skills and agent roles live."""

from __future__ import annotations

from pathlib import Path

from .errors import LabError

SKILLS = ("set-up-lab", "plan-mission", "run-mission", "experiment", "review")
AGENTS = ("scout", "runner", "reviewer", "reporter")
METHOD = ("DISCIPLINE.md", "LADDER.md")


def data_root() -> Path:
    """The folder holding `method/`, `skills/` and `agents/`.

    An installed wheel carries them in `lab_kit/_data/`; a source checkout has
    them at the repository root, two levels above this package.
    """
    packaged = Path(__file__).resolve().parent / "_data"
    if (packaged / "method").is_dir():
        return packaged
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "method").is_dir():
        return checkout
    raise LabError(f"cannot find lab-kit's shipped method: looked in {packaged} and {checkout}")


def shipped(name: str) -> Path:
    if name not in ("method", "skills", "agents"):
        raise ValueError(name)
    return data_root() / name


def shipped_files() -> list[tuple[Path, str]]:
    """Every shipped file a lab carries, as (source, path in the lab from its root)."""
    out: list[tuple[Path, str]] = []
    for name in METHOD:
        out.append((shipped("method") / name, f".lab/method/{name}"))
    for skill in SKILLS:
        folder = shipped("skills") / skill
        for src in sorted(p for p in folder.rglob("*") if p.is_file()):
            out.append((src, f".agents/skills/{skill}/{src.relative_to(folder).as_posix()}"))
    for agent in AGENTS:
        out.append((shipped("agents") / f"{agent}.md", f".agents/agents/{agent}.md"))
    for src, _ in out:
        if not src.is_file():
            raise LabError(f"lab-kit's shipped file {src} is missing")
    return out
