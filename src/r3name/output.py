from rich.console import Console
from rich.markup import escape

console = Console()


def _style(style: str, text: str) -> str:
    return f"[{style}]{escape(text)}[/]"


def green(t: str) -> str:
    return _style("green", t)


def yellow(t: str) -> str:
    return _style("yellow", t)


def cyan(t: str) -> str:
    return _style("cyan", t)


def bold(t: str) -> str:
    return _style("bold", t)


def dim(t: str) -> str:
    return _style("dim", t)
