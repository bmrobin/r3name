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
python r3name.py . --sub "old" "new" -n

# Apply literal replacement
python r3name.py . --sub "old" "new" -y

# Regex: spaces -> underscores
python r3name.py . --regex "\\s+" "_" -y

# Lowercase names recursively
python r3name.py . --case lower -r -y

# Number files (01 - name, 02 - name, ...)
python r3name.py . --number -y

# Only .txt files
python r3name.py . --ext txt --sub " " "_" -y

# Undo last successful run in this directory
python r3name.py . --undo -y
```

## Quick Start

## Requirements

- Python 3.14+

## Install (editable, recommended for local development)

```bash
uv sync
```

or

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
python r3name.py . --sub old new
```

You can also run with your venv interpreter directly:

```bash
.venv/bin/python r3name.py . --sub old new
```

## Basic Usage

```bash
python r3name.py PATH [OPTIONS]
```

- PATH is optional and defaults to current directory (.)

Examples:

```bash
python r3name.py . --regex "\\s+" "_"
python r3name.py . --sub "old" "new"
python r3name.py . --case lower
python r3name.py . --strip " _-"
python r3name.py . --number --num-sep "_"
python r3name.py ~/Music --ext flac --case title -r
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
  - Skip confirmation prompt
- --undo
  - Undo the last successful rename run recorded in .r3name-undo.json

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
python r3name.py . --sub old new -y

# Preview undo
python r3name.py . --undo -n

# Apply undo
python r3name.py . --undo -y
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
python r3name.py . --regex "\\s+" "_" -y
```

Remove a fixed token:

```bash
python r3name.py . --sub "[DRAFT] " "" -y
```

Normalize to lowercase (keep extensions):

```bash
python r3name.py . --case lower -y
```

Strip noisy separators from edges:

```bash
python r3name.py . --strip " _-" -y
```

Number files with custom format:

```bash
python r3name.py . --number --num-start 10 --num-pad 3 --num-prefix "IMG_" --num-sep "-" -y
```

Only rename txt files recursively:

```bash
python r3name.py . --ext txt --sub " " "_" -r -y
```

Rename directories only:

```bash
python r3name.py . --dirs-only --sub " " "_" -r -y
```

## Testing

Run tests (xdist enabled via pyproject addopts):

```bash
pytest
```

Single-process run:

```bash
pytest -n 0
```

## Troubleshooting

No matching entries found:

- Check your path and filters (--ext, --files-only, --dirs-only)
- Add --hidden if you want dotfiles included

No changes:

- Names may already match desired output
- Transform may not affect current names

Undo says no manifest:

- No successful rename run has been recorded in that directory root
- Run a non-dry rename first, then try --undo
