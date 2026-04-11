import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def cli(repo_root: Path, tmp_path: Path):
    """Run r3name as a module against tmp_path by default."""

    def _run(*args: str, cwd: Path | None = None, path: Path | None = None):
        target_path = path if path is not None else tmp_path
        target_cwd = cwd if cwd is not None else repo_root
        return subprocess.run(
            [sys.executable, "-m", "r3name", str(target_path), *args],
            cwd=target_cwd,
            capture_output=True,
            text=True,
        )

    return _run


@pytest.fixture
def mkfiles(tmp_path: Path):
    """Create files in tmp_path by default (or in a provided directory)."""

    def _mk(*filenames: str, directory: Path | None = None) -> None:
        base = directory if directory is not None else tmp_path
        for name in filenames:
            (base / name).touch()

    return _mk


@pytest.fixture
def lsnames():
    """List directory names, excluding hidden entries by default."""

    def _ls(directory: Path, include_hidden: bool = False) -> set[str]:
        entries = {p.name for p in directory.iterdir()}
        if include_hidden:
            return entries
        return {n for n in entries if not n.startswith(".")}

    return _ls


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    return tmp_path / ".r3name-undo.json"
