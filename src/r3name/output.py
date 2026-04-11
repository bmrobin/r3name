from enum import StrEnum
from typing import Any

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


def style(text: str, *styles: Colors | Styles | str) -> str:
    """
    Return Rich markup for text using one or more styles.

    Example:
        style("hello", Colors.GREEN)
        style("warning", Styles.BOLD, Colors.YELLOW)
    """
    escaped = escape(text)
    if not styles:
        return escaped
    style_expr = " ".join(str(s) for s in styles)
    return f"[{style_expr}]{escaped}[/]"


def log(*objects: Any, **kwargs: Any) -> None:
    """
    Print to the Rich Console() instance.
    """
    console.print(*objects, **kwargs)
