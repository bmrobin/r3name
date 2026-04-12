# r3name

A Python CLI utility for safely renaming files and directories.

It supports:

- Regex rename
- Literal substring replacement
- Character stripping
- Case conversion (extension preserved)
- Sequential numbering
- Filtering by file/dir/ext/hidden/recursive scope
- Dry-run previews
- Confirmation prompts
- Conflict skipping when the destination already exists
- Undo of the last successful run

## Command Cheatsheet

```bash
# Preview only (no changes)
r3name . --sub "old" "new" -n

# Apply literal replacement
r3name . --sub "old" "new"

# Regex: spaces -> underscores
r3name . --regex "\\s+" "_"

# Lowercase names recursively
r3name . --case lower -r

# Number files (01 - name, 02 - name, ...)
r3name . --number

# Only .txt files
r3name . --ext txt --sub " " "_"

# Undo last successful run in this directory
r3name . --undo
```

## Requirements

- Python 3.14+
- `uv` - https://docs.astral.sh/uv/

## Install
Install the requirements for local usage, testing, linting, etc.
```bash
uv sync
```

To build the package for distribution [not required for local usage]
```bash
uv build
```

## Run
Verify setup was successful
```bash
r3name --help
```

If you are running from the repo root without installing the console script yet, use module execution:

```bash
.venv/bin/python -m r3name . --sub old new
```

## Basic Usage

```bash
r3name PATH [OPTIONS]
```

- PATH is optional and defaults to current directory (.)

Examples:

```bash
r3name . --regex "\\s+" "_"
r3name . --sub "old" "new"
r3name . --case lower
r3name . --strip " _-"
r3name . --number --num-sep "_"
r3name ~/Music --ext flac --case title -r
```

## Option Reference

Transforms (applied in this order):

- --regex PATTERN REPL
  - Regex find/replace using Python re.sub on the full filename
- --sub OLD NEW
  - Literal substring replacement
- --strip CHARS
  - Strip leading/trailing characters from the full filename
- --case upper|lower|title
  - Case conversion on filename stem only; extension is preserved

Sequential numbering (applied after transforms):

- --number
  - Enable numbering prefix
- --num-start N
  - Starting number (default: 1)
- --num-pad N
  - Zero-pad width (default: 2)
- --num-prefix STR
  - Text inserted before number (default: empty)
- --num-sep STR
  - Separator between number and filename (default: " - ")

Filters:

- --files-only
  - Rename files only
- --dirs-only
  - Rename directories only
- --ext EXT
  - Only match files with this extension
- --hidden
  - Include hidden names starting with dot
- -r, --recursive
  - Recurse into subdirectories

Behavior:

- -n, --dry-run
  - Preview planned changes without applying
- -y, --yes
  - Skip confirmation prompt [default behavior is confirm before renaming]
- --undo
  - Undo the last successful rename run recorded in .r3name-undo.json
  - Cannot be combined with transforms, filters, or numbering options

Output formatting:

- r3name uses Rich for styled terminal output.
- If output is piped to another command/file, style rendering depends on whether stdout is treated as a terminal.

## Safety and Conflict Behavior

r3name includes safety checks before renaming:

- Rejects transforms that produce empty names
- Rejects transforms that produce path separators
- Skips entries where destination already exists and is a different path
- Displays a preview table before applying

If all planned operations would conflict, nothing is changed.

## Undo

Each successful rename run writes an undo manifest in the target root:

- .r3name-undo.json

Undo only reverts the last recorded run for that directory root.

Example flow:

```bash
# Apply rename
r3name . --sub old new

# Preview undo
r3name . --undo -n

# Apply undo
r3name . --undo
```

Undo behavior details:

- Operations are undone in reverse order for safer directory reversals
- Missing sources are skipped
- Conflicting restore targets are skipped
- If all undos are completed, the undo manifest is removed
- If some are skipped/failed, remaining items stay in the manifest for retry

## Common Recipes

Replace spaces with underscores:

```bash
r3name . --regex "\\s+" "_"
```

Remove a fixed token:

```bash
r3name . --sub "[DRAFT] " ""
```

Normalize to lowercase (keep extensions):

```bash
r3name . --case lower
```

Strip noisy separators from edges:

```bash
r3name . --strip " _-"
```

Number files with custom format:

```bash
r3name . --number --num-start 10 --num-pad 3 --num-prefix "IMG_" --num-sep "-"
```

Only rename txt files recursively:

```bash
r3name . --ext txt --sub " " "_" -r
```

Rename directories only:

```bash
r3name . --dirs-only --sub " " "_" -r
```

## Miscellaneous
Run all project checks with `make check`.  Individual aspects of this are described below

```bash
# Run tests
uv run pytest

# Format code
ruff format

# Lint code
ruff check --fix

# Type check Python
uv run pyright
```

