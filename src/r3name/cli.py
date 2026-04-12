#!/usr/bin/env python3
"""
r3name — rename files and directories from the command line.
"""

import argparse
import os
import re
import sys
import textwrap
from pathlib import Path

from .config import NumberingOptions, ParsedOptions, TransformOptions
from .output import Colors, Styles, log, style
from .undo import UNDO_FILENAME, run_undo, write_undo_manifest

# ─── Transforms ───────────────────────────────────────────────────────────────


def apply_transforms(name: str, args: ParsedOptions) -> str:
    """
    Apply all requested per-file transforms to a filename.
    """
    result = name

    if args.regex:
        try:
            result = re.sub(args.regex[0], args.regex[1], result)
        except re.error as e:
            sys.exit(f"error: invalid regex — {e}")

    if args.sub:
        result = result.replace(args.sub[0], args.sub[1])

    if args.strip:
        result = result.strip(args.strip)

    if args.case:
        stem, ext = os.path.splitext(result)
        fn = {"upper": str.upper, "lower": str.lower, "title": str.title}[args.case]
        result = fn(stem) + ext

    # Safety: reject empty names or names that would escape the directory
    result = result.strip()
    if not result:
        sys.exit(f"error: transform produced an empty filename for: {name!r}")
    if os.sep in result or (os.altsep and os.altsep in result):
        sys.exit(
            f"error: transform produced a name containing a path separator: {result!r}"
        )

    return result


def apply_numbering(names: list[str], args: ParsedOptions) -> list[str]:
    """
    Prepend sequential numbers to a list of filenames.
    """
    return [
        f"{args.num_prefix}{str(args.num_start + i).zfill(args.num_pad)}{args.num_sep}{name}"
        for i, name in enumerate(names)
    ]


# ─── Target collection ────────────────────────────────────────────────────────


def collect_targets(path: Path, args: ParsedOptions) -> list[Path]:
    entries = sorted(path.rglob("*") if args.recursive else path.iterdir())
    out: list[Path] = []
    for entry in entries:
        if not args.hidden and entry.name.startswith("."):
            continue
        if args.files_only and not entry.is_file():
            continue
        if args.dirs_only and not entry.is_dir():
            continue
        if args.ext and entry.is_file():
            if entry.suffix.lstrip(".").lower() != args.ext.lstrip(".").lower():
                continue
        out.append(entry)
    return out


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="r3name",
        description="Rename files and directories from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              r3name . --regex "\\s+" "_"                  replace spaces with underscores
              r3name . --sub "old" "new"                  literal substring replacement
              r3name . --case lower                       lowercase all filenames
              r3name . --strip " _-"                      strip leading/trailing separators
              r3name . --number --num-sep "_"             prepend 01_, 02_, …
              r3name . --regex "(.*)" "\\1" --dry-run      preview without applying
              r3name ~/Music --ext flac --case title -r   title-case all .flac files recursively
              r3name . --undo                             undo the last successful rename run in .
        """),
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="directory to operate in (default: current directory)",
    )

    # ── Transforms
    g = parser.add_argument_group("transforms  (applied in the order listed below)")
    g.add_argument(
        "--regex",
        nargs=2,
        metavar=("PATTERN", "REPL"),
        help="regex find & replace applied to the full filename (Python re.sub)",
    )
    g.add_argument(
        "--sub",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="literal substring replacement",
    )
    g.add_argument(
        "--strip",
        metavar="CHARS",
        help="strip these leading/trailing characters from the filename",
    )
    g.add_argument(
        "--case",
        choices=TransformOptions.case_choices(),
        help="convert filename case (extension is preserved)",
    )

    # ── Numbering
    n = parser.add_argument_group(
        "sequential numbering  (applied after other transforms)"
    )
    n.add_argument("--number", action="store_true", help="prepend sequential numbers")
    n.add_argument(
        "--num-start",
        type=int,
        default=NumberingOptions.default_number_start(),
        metavar="N",
        help=f"starting number (default: {NumberingOptions.default_number_start()})",
    )
    n.add_argument(
        "--num-pad",
        type=int,
        default=NumberingOptions.default_number_pad(),
        metavar="N",
        help=f"zero-pad width (default: {NumberingOptions.default_number_pad()}, giving 01, 02, …)",
    )
    n.add_argument(
        "--num-prefix",
        default="",
        metavar="STR",
        help="text inserted before the number",
    )
    n.add_argument(
        "--num-sep",
        default=" - ",
        metavar="STR",
        help='separator between number and name (default: " - ")',
    )

    # ── Filters
    f = parser.add_argument_group("filters")
    f.add_argument(
        "--files-only", action="store_true", help="rename files only, skip directories"
    )
    f.add_argument(
        "--dirs-only", action="store_true", help="rename directories only, skip files"
    )
    f.add_argument(
        "--ext", metavar="EXT", help="only match files with this extension (e.g. mp3)"
    )
    f.add_argument(
        "--hidden",
        action="store_true",
        help="include hidden entries (names starting with .)",
    )
    f.add_argument(
        "-r", "--recursive", action="store_true", help="recurse into subdirectories"
    )

    # ── Behaviour
    b = parser.add_argument_group("behaviour")
    b.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="show planned renames without applying them",
    )
    b.add_argument(
        "-y", "--yes", action="store_true", help="skip the confirmation prompt"
    )
    b.add_argument(
        "--undo",
        action="store_true",
        help=f"undo the last successful run recorded in {UNDO_FILENAME}",
    )

    parsed_args = parser.parse_args()
    args = ParsedOptions.from_namespace(parsed_args)

    if args.files_only and args.dirs_only:
        parser.error("--files-only and --dirs-only are mutually exclusive")

    path = Path(args.path).resolve()
    if not path.is_dir():
        parser.error(f"not a directory: {path}")

    if args.undo:
        if any(
            [
                args.regex,
                args.sub,
                args.case,
                args.strip,
                args.number,
                args.files_only,
                args.dirs_only,
                args.ext,
                args.hidden,
                args.recursive,
                args.num_start != 1,
                args.num_pad != 2,
                args.num_prefix != "",
                args.num_sep != " - ",
            ]
        ):
            parser.error(
                "--undo cannot be combined with transform/filter/numbering options"
            )
        run_undo(path, args)
        return

    # Validate: need at least one transform
    if not any([args.regex, args.sub, args.case, args.strip, args.number]):
        parser.error(
            "specify at least one transform: --regex, --sub, --case, --strip, or --number"
        )

    # Collect entries
    targets = collect_targets(path, args)
    if not targets:
        log("No matching entries found.")
        return

    # Apply transforms
    new_names = [apply_transforms(t.name, args) for t in targets]

    # Apply numbering (list-level operation, runs after per-file transforms)
    if args.number:
        new_names = apply_numbering(new_names, args)

    # Build the diff plan — only entries whose name actually changes
    plan = [
        (t, t.parent / nn)
        for t, nn in zip(targets, new_names, strict=True)
        if nn != t.name
    ]

    if not plan:
        log("No changes — all names already match the desired form.")
        return

    # ── Preview table
    col = min(max(len(o.name) for o, _ in plan), 60)

    header_before = "Before"
    header_after = "After"
    log(f"\n{style(f'{len(plan)} rename(s) planned', Styles.BOLD)}\n")
    log(
        f"  {style(header_before, Styles.BOLD):<{col}}    {style(header_after, Styles.BOLD)}"
    )
    log("  " + "─" * (col + 4 + min(max(len(n.name) for _, n in plan), 80)))

    for old, new in plan:
        o_pad = old.name[:col].ljust(col)
        n_text = new.name[:80]
        conflict = new.exists() and not os.path.samefile(new, old)
        suffix = style("  ← target exists, will skip", Styles.DIM) if conflict else ""
        n_color = (
            style(n_text, Colors.YELLOW) if conflict else style(n_text, Colors.GREEN)
        )
        log(f"  {style(o_pad, Colors.CYAN)}  →  {n_color}{suffix}")

    # ── Counts
    n_conflicts = sum(1 for o, n in plan if n.exists() and not os.path.samefile(n, o))
    to_apply = len(plan) - n_conflicts

    if args.dry_run:
        log(style("\nDry run — no changes made.", Colors.YELLOW, Styles.BOLD))
        return

    if to_apply == 0:
        log("\nAll planned renames would conflict with existing files — nothing to do.")
        return

    # ── Confirmation
    if not args.yes:
        try:
            ans = input(f"\nApply {to_apply} rename(s)? [y/N] ").strip().lower()
        except KeyboardInterrupt, EOFError:
            log("\nAborted.")
            return
        if ans != "y":
            log("Aborted.")
            return

    # ── Execute
    applied = errors = 0
    applied_records: list[tuple[Path, Path]] = []
    for old, new in plan:
        if new.exists() and not os.path.samefile(new, old):
            log(style(f"  SKIP  {old.name!r}  (target already exists)", Colors.YELLOW))
            continue
        try:
            old.rename(new)
            log(style(f"  OK    {old.name!r}  →  {new.name!r}", Colors.GREEN))
            applied += 1
            applied_records.append((old, new))
        except OSError as e:
            log(f"  ERR   {old.name!r}: {e}")
            errors += 1

    if applied_records:
        try:
            write_undo_manifest(path, applied_records)
        except OSError as e:
            log(style(f"\nwarning: could not write undo manifest: {e}", Colors.YELLOW))

    parts = [f"{applied} rename(s) applied"]
    if errors:
        parts.append(f"{errors} error(s)")
    log("\n" + ", ".join(parts) + ".")


if __name__ == "__main__":
    main()
