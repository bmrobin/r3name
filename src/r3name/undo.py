import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .output import Colors, Styles, log, style

if TYPE_CHECKING:
    import argparse


UNDO_FILENAME = ".r3name-undo.json"


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


def get_path_display_name(path: Path, root: Path) -> str:
    """
    Render a path relative to root when possible for clearer output.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def run_undo(root: Path, args: "argparse.Namespace") -> None:
    """
    Undo the last successful rename run for this root directory.
    """
    mpath = get_undo_manifest_path(root)
    if not mpath.exists():
        log(f"No undo manifest found at {mpath}.")
        return

    manifest = load_undo_manifest(root)
    raw_records = manifest.get("renames", [])
    if not raw_records:
        log("Undo manifest is empty — nothing to undo.")
        return

    # Reverse order to safely undo nested directory renames.
    records: list[tuple[Path, Path]] = []
    for rec in reversed(raw_records):
        if not isinstance(rec, dict) or "old" not in rec or "new" not in rec:
            log(style("Skipping malformed undo record.", Colors.YELLOW))
            continue
        src = Path(str(rec["new"]))
        dst = Path(str(rec["old"]))
        records.append((src, dst))

    if not records:
        log("Undo manifest has no valid records — nothing to undo.")
        return

    col = min(max(len(get_path_display_name(src, root)) for src, _ in records), 60)
    log(f"\n{style(f'{len(records)} undo rename(s) planned', Styles.BOLD)}\n")
    log(
        f"  {style('Current', Styles.BOLD):<{col}}    {style('Restore To', Styles.BOLD)}"
    )
    log(
        "  "
        + "─"
        * (
            col
            + 4
            + min(max(len(get_path_display_name(dst, root)) for _, dst in records), 80)
        )
    )

    missing_sources = 0
    conflicts = 0
    for src, dst in records:
        s_name = get_path_display_name(src, root)[:col].ljust(col)
        d_name = get_path_display_name(dst, root)[:80]
        if not src.exists():
            suffix = style("  ← source missing, will skip", Styles.DIM)
            log(
                f"  {style(s_name, Colors.CYAN)}  →  {style(d_name, Colors.YELLOW)}{suffix}"
            )
            missing_sources += 1
            continue
        conflict = dst.exists() and not os.path.samefile(dst, src)
        if conflict:
            suffix = style("  ← target exists, will skip", Styles.DIM)
            log(
                f"  {style(s_name, Colors.CYAN)}  →  {style(d_name, Colors.YELLOW)}{suffix}"
            )
            conflicts += 1
            continue
        log(f"  {style(s_name, Colors.CYAN)}  →  {style(d_name, Colors.GREEN)}")

    to_apply = len(records) - missing_sources - conflicts

    if args.dry_run:
        log(style("\nDry run — no changes made.", Colors.YELLOW, Styles.BOLD))
        return

    if to_apply == 0:
        log("\nNo undo operations can be applied safely.")
        return

    if not args.yes:
        try:
            ans = input(f"\nApply {to_apply} undo rename(s)? [y/N] ").strip().lower()
        except KeyboardInterrupt, EOFError:
            log("\nAborted.")
            return
        if ans != "y":
            log("Aborted.")
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
            log(
                style(
                    f"  SKIP  {get_path_display_name(src, root)!r}  (source missing)",
                    Colors.YELLOW,
                )
            )
            remaining_raw.append({"old": str(dst), "new": str(src)})
            continue
        if dst.exists() and not os.path.samefile(dst, src):
            log(
                style(
                    f"  SKIP  {get_path_display_name(src, root)!r}  (target already exists)",
                    Colors.YELLOW,
                )
            )
            remaining_raw.append({"old": str(dst), "new": str(src)})
            continue
        try:
            src.rename(dst)
            log(
                style(
                    f"  OK    {get_path_display_name(src, root)!r}  →  {get_path_display_name(dst, root)!r}",
                    Colors.GREEN,
                )
            )
            applied += 1
        except OSError as e:
            log(f"  ERR   {get_path_display_name(src, root)!r}: {e}")
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
    log("\n" + ", ".join(parts) + ".")
