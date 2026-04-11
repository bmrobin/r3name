#!/usr/bin/env python3
"""
r3name — rename files and directories from the command line.
"""

import argparse
import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from .output import bold, console, cyan, dim, green, yellow

UNDO_FILENAME = ".r3name-undo.json"
print = console.print


# ─── Transforms ───────────────────────────────────────────────────────────────


def apply_transforms(name: str, args: argparse.Namespace) -> str:
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


def apply_numbering(names: list[str], args: argparse.Namespace) -> list[str]:
    """
    Prepend sequential numbers to a list of filenames.
    """
    return [
        f"{args.num_prefix}{str(args.num_start + i).zfill(args.num_pad)}{args.num_sep}{name}"
        for i, name in enumerate(names)
    ]


def get_undo_manifest_path(path: Path) -> Path:
    """
    Return the undo manifest path for an operation root.
    """
    return path / UNDO_FILENAME


def write_undo_manifest(path: Path, records: list[tuple[Path, Path]]) -> None:
    """
    Persist successful renames so they can be reversed later.
    """
    manifest = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(path),
        "renames": [{"old": str(old), "new": str(new)} for old, new in records],
    }
    get_undo_manifest_path(path).write_text(json.dumps(manifest, indent=2) + "\n")


def load_undo_manifest(path: Path) -> dict:
    """
    Load and minimally validate the undo manifest.
    """
    mpath = get_undo_manifest_path(path)
    try:
        data = json.loads(mpath.read_text())
    except OSError as e:
        sys.exit(f"error: could not read undo manifest: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"error: invalid undo manifest JSON: {e}")

    if not isinstance(data, dict) or not isinstance(data.get("renames"), list):
        sys.exit("error: undo manifest has an invalid structure")
    return data


def display_name(path: Path, root: Path) -> str:
    """
    Render a path relative to root when possible for clearer output.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def run_undo(root: Path, args: argparse.Namespace) -> None:
    """
    Undo the last successful rename run for this root directory.
    """
    mpath = get_undo_manifest_path(root)
    if not mpath.exists():
        print(f"No undo manifest found at {mpath}.")
        return

    manifest = load_undo_manifest(root)
    raw_records = manifest.get("renames", [])
    if not raw_records:
        print("Undo manifest is empty — nothing to undo.")
        return

    # Reverse order to safely undo nested directory renames.
    records: list[tuple[Path, Path]] = []
    for rec in reversed(raw_records):
        if not isinstance(rec, dict) or "old" not in rec or "new" not in rec:
            print(yellow("Skipping malformed undo record."))
            continue
        src = Path(str(rec["new"]))
        dst = Path(str(rec["old"]))
        records.append((src, dst))

    if not records:
        print("Undo manifest has no valid records — nothing to undo.")
        return

    col = min(max(len(display_name(src, root)) for src, _ in records), 60)
    print(f"\n{bold(f'{len(records)} undo rename(s) planned')}\n")
    print(f"  {bold('Current'):<{col}}    {bold('Restore To')}")
    print(
        "  "
        + "─"
        * (col + 4 + min(max(len(display_name(dst, root)) for _, dst in records), 80))
    )

    missing_sources = 0
    conflicts = 0
    for src, dst in records:
        s_name = display_name(src, root)[:col].ljust(col)
        d_name = display_name(dst, root)[:80]
        if not src.exists():
            suffix = dim("  ← source missing, will skip")
            print(f"  {cyan(s_name)}  →  {yellow(d_name)}{suffix}")
            missing_sources += 1
            continue
        conflict = dst.exists() and not os.path.samefile(dst, src)
        if conflict:
            suffix = dim("  ← target exists, will skip")
            print(f"  {cyan(s_name)}  →  {yellow(d_name)}{suffix}")
            conflicts += 1
            continue
        print(f"  {cyan(s_name)}  →  {green(d_name)}")

    to_apply = len(records) - missing_sources - conflicts

    if args.dry_run:
        print("\n[bold yellow]Dry run[/] — no changes made.")
        return

    if to_apply == 0:
        print("\nNo undo operations can be applied safely.")
        return

    if not args.yes:
        try:
            ans = input(f"\nApply {to_apply} undo rename(s)? [y/N] ").strip().lower()
        except KeyboardInterrupt, EOFError:
            print("\nAborted.")
            return
        if ans != "y":
            print("Aborted.")
            return

    # Keep only records that were not successfully undone so another --undo can retry.
    remaining_raw: list[dict[str, str]] = []
    applied = errors = 0

    for rec in reversed(raw_records):
        if not isinstance(rec, dict) or "old" not in rec or "new" not in rec:
            continue

        src = Path(str(rec["new"]))
        dst = Path(str(rec["old"]))

        if not src.exists():
            print(yellow(f"  SKIP  {display_name(src, root)!r}  (source missing)"))
            remaining_raw.append({"old": str(dst), "new": str(src)})
            continue
        if dst.exists() and not os.path.samefile(dst, src):
            print(
                yellow(f"  SKIP  {display_name(src, root)!r}  (target already exists)")
            )
            remaining_raw.append({"old": str(dst), "new": str(src)})
            continue
        try:
            src.rename(dst)
            print(
                green(
                    f"  OK    {display_name(src, root)!r}  →  {display_name(dst, root)!r}"
                )
            )
            applied += 1
        except OSError as e:
            print(f"  ERR   {display_name(src, root)!r}: {e}")
            errors += 1
            remaining_raw.append({"old": str(dst), "new": str(src)})

    if remaining_raw:
        manifest["created_at"] = datetime.now(timezone.utc).isoformat()
        manifest["renames"] = remaining_raw
        mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    else:
        mpath.unlink(missing_ok=True)

    parts = [f"{applied} undo rename(s) applied"]
    if errors:
        parts.append(f"{errors} error(s)")
    if remaining_raw:
        parts.append(f"{len(remaining_raw)} remaining in undo manifest")
    print("\n" + ", ".join(parts) + ".")


# ─── Target collection ────────────────────────────────────────────────────────


def collect_targets(path: Path, args: argparse.Namespace) -> list[Path]:
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
        choices=["upper", "lower", "title"],
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
        default=1,
        metavar="N",
        help="starting number (default: 1)",
    )
    n.add_argument(
        "--num-pad",
        type=int,
        default=2,
        metavar="N",
        help="zero-pad width (default: 2, giving 01, 02, …)",
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

    args = parser.parse_args()

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
        print("No matching entries found.")
        return

    # Apply transforms
    new_names = [apply_transforms(t.name, args) for t in targets]

    # Apply numbering (list-level operation, runs after per-file transforms)
    if args.number:
        new_names = apply_numbering(new_names, args)

    # Build the diff plan — only entries whose name actually changes
    plan = [(t, t.parent / nn) for t, nn in zip(targets, new_names) if nn != t.name]

    if not plan:
        print("No changes — all names already match the desired form.")
        return

    # ── Preview table
    col = min(max(len(o.name) for o, _ in plan), 60)

    header_before = "Before"
    header_after = "After"
    print(f"\n{bold(f'{len(plan)} rename(s) planned')}\n")
    print(f"  {bold(header_before):<{col}}    {bold(header_after)}")
    print("  " + "─" * (col + 4 + min(max(len(n.name) for _, n in plan), 80)))

    for old, new in plan:
        o_pad = old.name[:col].ljust(col)
        n_text = new.name[:80]
        conflict = new.exists() and not os.path.samefile(new, old)
        suffix = dim("  ← target exists, will skip") if conflict else ""
        n_color = yellow(n_text) if conflict else green(n_text)
        print(f"  {cyan(o_pad)}  →  {n_color}{suffix}")

    # ── Counts
    n_conflicts = sum(1 for o, n in plan if n.exists() and not os.path.samefile(n, o))
    to_apply = len(plan) - n_conflicts

    if args.dry_run:
        print("\n[bold yellow]Dry run[/] — no changes made.")
        return

    if to_apply == 0:
        print(
            "\nAll planned renames would conflict with existing files — nothing to do."
        )
        return

    # ── Confirmation
    if not args.yes:
        try:
            ans = input(f"\nApply {to_apply} rename(s)? [y/N] ").strip().lower()
        except KeyboardInterrupt, EOFError:
            print("\nAborted.")
            return
        if ans != "y":
            print("Aborted.")
            return

    # ── Execute
    applied = errors = 0
    applied_records: list[tuple[Path, Path]] = []
    for old, new in plan:
        if new.exists() and not os.path.samefile(new, old):
            print(yellow(f"  SKIP  {old.name!r}  (target already exists)"))
            continue
        try:
            old.rename(new)
            print(green(f"  OK    {old.name!r}  →  {new.name!r}"))
            applied += 1
            applied_records.append((old, new))
        except OSError as e:
            print(f"  ERR   {old.name!r}: {e}")
            errors += 1

    if applied_records:
        try:
            write_undo_manifest(path, applied_records)
        except OSError as e:
            print(yellow(f"\nwarning: could not write undo manifest: {e}"))

    parts = [f"{applied} rename(s) applied"]
    if errors:
        parts.append(f"{errors} error(s)")
    print("\n" + ", ".join(parts) + ".")


if __name__ == "__main__":
    main()
