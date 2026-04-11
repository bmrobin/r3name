from enum import StrEnum

from rich.console import Console
from rich.markup import escape

console = Console()


class Colors(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    CYAN = "cyan"


class Styles(StrEnum):
    BOLD = "bold"
    DIM = "dim"


def _style(style: str, text: str) -> str:
    return f"[{style}]{escape(text)}[/]"


def green(msg: str) -> str:
    return _style(Colors.GREEN, msg)


def yellow(msg: str) -> str:
    return _style(Colors.YELLOW, msg)


def cyan(msg: str) -> str:
    return _style(Colors.CYAN, msg)


def bold(msg: str) -> str:
    return _style(Styles.BOLD, msg)


def dim(msg: str) -> str:
    return _style(Styles.DIM, msg)
