import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def script_path() -> Path:
    return Path(__file__).parent.parent / "r3name.py"


@pytest.fixture
def cli(script_path: Path, tmp_path: Path):
    """Run r3name.py in tmp_path by default unless a custom target path is provided."""

    def _run(*args: str, cwd: Path | None = None, path: Path | None = None):
        target_path = path if path is not None else tmp_path
        target_cwd = cwd if cwd is not None else tmp_path
        return subprocess.run(
            [sys.executable, str(script_path), str(target_path), *args],
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
