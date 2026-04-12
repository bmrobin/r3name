from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


# ─── Configuration ────────────────────────────────────────────────────────
class TransformOptions(StrEnum):
    REGEX = "regex"
    SUBSTITUTION = "sub"
    CASE = "case"
    STRIP = "strip"

    @staticmethod
    def case_choices() -> list[str]:
        return ["upper", "lower", "title"]


class NumberingOptions(StrEnum):
    NUMBER = "number"
    NUMBER_START = "num-start"
    NUMBER_SEPARATOR = "num-sep"
    NUMBER_PREFIX = "num-prefix"
    NUMBER_PADDING = "num-pad"

    @staticmethod
    def default_number_start() -> int:
        return 1

    @staticmethod
    def default_number_pad() -> int:
        return 2


class FilteringOptions(StrEnum):
    EXTENSION = "ext"
    FILES_ONLY = "files-only"
    DIRECTORIES_ONLY = "dirs-only"
    INCLUDE_HIDDEN_FILES = "hidden"
    RECURSIVE = "recursive"


class ProgramOptions(StrEnum):
    DRY_RUN = "dry-run"
    RUN = "yes"
    UNDO = "undo"


@dataclass(frozen=True)
class ParsedOptions:
    path: str
    regex: tuple[str, str] | None
    sub: tuple[str, str] | None
    strip: str | None
    case: str | None
    number: bool
    num_start: int
    num_pad: int
    num_prefix: str
    num_sep: str
    files_only: bool
    dirs_only: bool
    ext: str | None
    hidden: bool
    recursive: bool
    dry_run: bool
    yes: bool
    undo: bool

    @staticmethod
    def _dest(opt: StrEnum) -> str:
        return opt.value.replace("-", "_")

    @classmethod
    def from_namespace(cls, ns: "argparse.Namespace") -> "ParsedOptions":
        return cls(
            path=ns.path,
            regex=getattr(ns, cls._dest(TransformOptions.REGEX)),
            sub=getattr(ns, cls._dest(TransformOptions.SUBSTITUTION)),
            strip=getattr(ns, cls._dest(TransformOptions.STRIP)),
            case=getattr(ns, cls._dest(TransformOptions.CASE)),
            number=getattr(ns, cls._dest(NumberingOptions.NUMBER)),
            num_start=getattr(ns, cls._dest(NumberingOptions.NUMBER_START)),
            num_pad=getattr(ns, cls._dest(NumberingOptions.NUMBER_PADDING)),
            num_prefix=getattr(ns, cls._dest(NumberingOptions.NUMBER_PREFIX)),
            num_sep=getattr(ns, cls._dest(NumberingOptions.NUMBER_SEPARATOR)),
            files_only=getattr(ns, cls._dest(FilteringOptions.FILES_ONLY)),
            dirs_only=getattr(ns, cls._dest(FilteringOptions.DIRECTORIES_ONLY)),
            ext=getattr(ns, cls._dest(FilteringOptions.EXTENSION)),
            hidden=getattr(ns, cls._dest(FilteringOptions.INCLUDE_HIDDEN_FILES)),
            recursive=getattr(ns, cls._dest(FilteringOptions.RECURSIVE)),
            dry_run=getattr(ns, cls._dest(ProgramOptions.DRY_RUN)),
            yes=getattr(ns, cls._dest(ProgramOptions.RUN)),
            undo=getattr(ns, cls._dest(ProgramOptions.UNDO)),
        )
