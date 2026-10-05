from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest
from folio import cli as folio_cli

from lab_kit import cli

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "monte-carlo-lab"
TODAY = "2026-10-04"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


def commit(root: Path, message: str = "change") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def init_repo(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "lab@example.org")
    git(root, "config", "user.name", "Lab")


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOLIO_TODAY", TODAY)


@pytest.fixture
def make_lab(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., Path]:
    """A copy of the example lab in its own git repository, committed; `before` changes it first."""

    def make(before: Callable[[Path], None] | None = None) -> Path:
        root = tmp_path / "monte-carlo-lab"
        shutil.copytree(EXAMPLE, root, symlinks=True)
        if before is not None:
            before(root)
        init_repo(root)
        commit(root, "the example lab")
        monkeypatch.chdir(root)
        return root

    return make


@pytest.fixture
def lab_kit(capsys: pytest.CaptureFixture[str]) -> Callable[..., tuple[int, str]]:
    """Run `lab-kit` in the current folder; return its exit code and everything it printed."""

    def run(*args: str) -> tuple[int, str]:
        capsys.readouterr()
        code = cli.main(list(args))
        captured = capsys.readouterr()
        return code, captured.out + captured.err

    return run


@pytest.fixture
def folio(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> Callable[..., tuple[int, str]]:
    """Run `folio` in a given folder; return its exit code and everything it printed."""

    def run(where: Path, *args: str) -> tuple[int, str]:
        capsys.readouterr()
        with monkeypatch.context() as m:
            m.chdir(where)
            code = folio_cli.main(list(args))
        captured = capsys.readouterr()
        return code, captured.out + captured.err

    return run
