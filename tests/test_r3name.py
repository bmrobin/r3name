import json

# ---------------------------------------------------------------------------
# --sub  (literal substring replacement)
# ---------------------------------------------------------------------------


def test_basic_replacement(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_alpha.txt", "old_beta.txt")
    result = cli("--sub", "old", "new", "-y")
    assert result.returncode == 0
    assert lsnames(tmp_path) == {"new_alpha.txt", "new_beta.txt"}


def test_no_match_is_noop(mkfiles, cli, lsnames, tmp_path):
    mkfiles("alpha.txt")
    result = cli("--sub", "xyz", "abc", "-y")
    assert result.returncode == 0
    assert "No changes" in result.stdout
    assert lsnames(tmp_path) == {"alpha.txt"}


def test_dry_run_does_not_rename(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_file.txt")
    result = cli("--sub", "old", "new", "-n")
    assert result.returncode == 0
    assert "Dry run" in result.stdout
    assert lsnames(tmp_path) == {"old_file.txt"}


def test_dry_run_does_not_emit_literal_rich_markup(mkfiles, cli):
    mkfiles("old_file.txt")
    result = cli("--sub", "old", "new", "-n")
    assert result.returncode == 0
    assert "[cyan]" not in result.stdout
    assert "[/]" not in result.stdout


# ---------------------------------------------------------------------------
# --regex  (Python re.sub)
# ---------------------------------------------------------------------------


def test_spaces_to_underscores(mkfiles, cli, lsnames, tmp_path):
    mkfiles("hello world.txt", "foo bar baz.txt")
    result = cli("--regex", r"\s+", "_", "-y")
    assert result.returncode == 0
    assert lsnames(tmp_path) == {"hello_world.txt", "foo_bar_baz.txt"}


def test_capture_group_reorder(mkfiles, cli, lsnames, tmp_path):
    mkfiles("2024-01-15.txt")
    result = cli("--regex", r"(\d{4})-(\d{2})-(\d{2})", r"\3_\2_\1", "-y")
    assert result.returncode == 0
    assert "15_01_2024.txt" in lsnames(tmp_path)


def test_invalid_regex_exits_with_error(mkfiles, cli):
    mkfiles("file.txt")
    result = cli("--regex", "[invalid", "x", "-y")
    assert result.returncode != 0


def test_regex_dry_run_does_not_rename(mkfiles, cli, lsnames, tmp_path):
    mkfiles("hello world.txt")
    result = cli("--regex", r"\s+", "_", "-n")
    assert result.returncode == 0
    assert "Dry run" in result.stdout
    assert "hello world.txt" in lsnames(tmp_path)


# ---------------------------------------------------------------------------
# --strip  (leading/trailing character stripping)
# ---------------------------------------------------------------------------


def test_strip_leading_trailing_dashes(mkfiles, cli, lsnames, tmp_path):
    mkfiles("--hello--.txt", "--world--.txt")
    result = cli("--strip", "-", "-y")
    assert result.returncode == 0
    assert lsnames(tmp_path) == {"hello--.txt", "world--.txt"}


def test_strip_spaces(cli, lsnames, tmp_path):
    # Filesystems may or may not allow leading/trailing spaces.
    # Create via Path.touch which bypasses shell glob issues.
    (tmp_path / "  spaced  .txt").touch()
    result = cli("--strip", " ", "-y")
    assert result.returncode == 0
    assert "spaced  .txt" in lsnames(tmp_path)


def test_strip_multiple_chars(mkfiles, cli, lsnames, tmp_path):
    # "_-trimme-_.txt".strip("_-") -> leading "_-" stripped; trailing ".txt"
    # ends in 't' which is not in the strip set, so only leading chars are removed.
    mkfiles("_-trimme-_.txt")
    result = cli("--strip", "_-", "-y")
    assert result.returncode == 0
    assert "trimme-_.txt" in lsnames(tmp_path)


# ---------------------------------------------------------------------------
# --case  (upper / lower / title, extension preserved)
# ---------------------------------------------------------------------------


def test_lower(mkfiles, cli):
    mkfiles("Hello_World.TXT")
    result = cli("--case", "lower", "-y")
    assert result.returncode == 0
    assert "hello_world" in result.stdout
    assert "rename(s)" in result.stdout


def test_upper(mkfiles, cli):
    mkfiles("hello_world.txt")
    result = cli("--case", "upper", "-y")
    assert result.returncode == 0
    assert "HELLO_WORLD" in result.stdout
    assert "rename(s)" in result.stdout


def test_title(mkfiles, cli):
    mkfiles("hello world.txt")
    result = cli("--case", "title", "-y")
    assert result.returncode == 0
    assert "Hello World" in result.stdout
    assert "rename(s)" in result.stdout


def test_extension_preserved(mkfiles, cli, lsnames, tmp_path):
    mkfiles("report.TXT")
    result = cli("--case", "lower", "-y")
    assert result.returncode == 0
    assert "report.TXT" in lsnames(tmp_path)


# ---------------------------------------------------------------------------
# --number  (sequential numbering)
# ---------------------------------------------------------------------------


def test_default_numbering(mkfiles, cli, lsnames, tmp_path):
    mkfiles("alpha.txt", "beta.txt")
    result = cli("--number", "-y")
    assert result.returncode == 0
    result_names = lsnames(tmp_path)
    assert any(n.startswith("01") for n in result_names)
    assert any(n.startswith("02") for n in result_names)


def test_custom_start_and_pad(mkfiles, cli, lsnames, tmp_path):
    mkfiles("alpha.txt")
    result = cli("--number", "--num-start", "5", "--num-pad", "3", "-y")
    assert result.returncode == 0
    assert any(n.startswith("005") for n in lsnames(tmp_path))


def test_custom_prefix_and_sep(mkfiles, cli, lsnames, tmp_path):
    mkfiles("track.txt")
    result = cli("--number", "--num-prefix", "ch", "--num-sep", "_", "-y")
    assert result.returncode == 0
    assert any(n.startswith("ch01_") for n in lsnames(tmp_path))


# ---------------------------------------------------------------------------
# --files-only / --dirs-only
# ---------------------------------------------------------------------------


def test_files_only_skips_directories(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_file.txt")
    (tmp_path / "old_dir").mkdir()
    result = cli("--sub", "old", "new", "--files-only", "-y")
    assert result.returncode == 0
    assert "new_file.txt" in lsnames(tmp_path)
    assert "old_dir" in lsnames(tmp_path)


def test_dirs_only_skips_files(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_file.txt")
    (tmp_path / "old_dir").mkdir()
    result = cli("--sub", "old", "new", "--dirs-only", "-y")
    assert result.returncode == 0
    assert "new_dir" in lsnames(tmp_path)
    assert "old_file.txt" in lsnames(tmp_path)


def test_files_and_dirs_only_are_mutually_exclusive(cli):
    result = cli("--sub", "a", "b", "--files-only", "--dirs-only")
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# --ext  (extension filter)
# ---------------------------------------------------------------------------


def test_only_matching_extension_renamed(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_doc.txt", "old_img.png")
    result = cli("--sub", "old", "new", "--ext", "txt", "-y")
    assert result.returncode == 0
    assert "new_doc.txt" in lsnames(tmp_path)
    assert "old_img.png" in lsnames(tmp_path)


def test_ext_with_leading_dot(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_doc.txt", "old_img.png")
    result = cli("--sub", "old", "new", "--ext", ".txt", "-y")
    assert result.returncode == 0
    assert "new_doc.txt" in lsnames(tmp_path)


# ---------------------------------------------------------------------------
# --hidden
# ---------------------------------------------------------------------------


def test_hidden_files_excluded_by_default(mkfiles, cli, lsnames, tmp_path):
    mkfiles(".old_secret.txt", "old_visible.txt")
    result = cli("--sub", "old", "new", "-y")
    assert result.returncode == 0
    assert (tmp_path / ".old_secret.txt").exists()
    assert "new_visible.txt" in lsnames(tmp_path)


def test_hidden_flag_includes_hidden(mkfiles, cli, lsnames, tmp_path):
    mkfiles(".old_secret.txt")
    result = cli("--sub", "old", "new", "--hidden", "-y")
    assert result.returncode == 0
    assert ".new_secret.txt" in lsnames(tmp_path, include_hidden=True)


# ---------------------------------------------------------------------------
# -r / --recursive
# ---------------------------------------------------------------------------


def test_recursive_renames_in_subdirectories(mkfiles, cli, lsnames, tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    mkfiles("old_nested.txt", directory=subdir)
    mkfiles("old_top.txt")
    result = cli("--sub", "old", "new", "-r", "-y")
    assert result.returncode == 0
    assert "new_top.txt" in lsnames(tmp_path)
    assert "new_nested.txt" in lsnames(subdir)


def test_non_recursive_leaves_subdirectory_files_untouched(
    mkfiles, cli, lsnames, tmp_path
):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    mkfiles("old_nested.txt", directory=subdir)
    mkfiles("old_top.txt")
    result = cli("--sub", "old", "new", "-y")
    assert result.returncode == 0
    assert "old_nested.txt" in lsnames(subdir)


# ---------------------------------------------------------------------------
# Conflict handling (target already exists)
# ---------------------------------------------------------------------------


def test_existing_target_is_skipped(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old.txt", "new.txt")
    result = cli("--sub", "old", "new", "-y")
    assert result.returncode == 0
    assert "old.txt" in lsnames(tmp_path)
    assert "new.txt" in lsnames(tmp_path)


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------


def test_no_transform_exits_with_error(mkfiles, cli):
    mkfiles("file.txt")
    result = cli()
    assert result.returncode != 0


def test_transform_producing_path_separator_exits(mkfiles, cli):
    mkfiles("file.txt")
    result = cli("--sub", "file", "dir/file", "-y")
    assert result.returncode != 0


def test_transform_producing_empty_name_exits(mkfiles, cli):
    mkfiles("abc.txt")
    result = cli("--regex", r".*", "", "-y")
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# --undo
# ---------------------------------------------------------------------------


def test_undo_reverses_rename(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old.txt")
    cli("--sub", "old", "new", "-y")
    assert "new.txt" in lsnames(tmp_path)

    result = cli("--undo", "-y")
    assert result.returncode == 0
    assert "old.txt" in lsnames(tmp_path)
    assert "new.txt" not in lsnames(tmp_path)


def test_undo_manifest_written_after_rename(mkfiles, cli, manifest_path):
    mkfiles("old.txt")
    cli("--sub", "old", "new", "-y")
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["version"] == 1
    assert len(data["renames"]) == 1


def test_undo_manifest_deleted_after_full_undo(mkfiles, cli, manifest_path):
    mkfiles("old.txt")
    cli("--sub", "old", "new", "-y")
    cli("--undo", "-y")
    assert not manifest_path.exists()


def test_undo_dry_run_does_not_rename(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old.txt")
    cli("--sub", "old", "new", "-y")
    result = cli("--undo", "-n")
    assert result.returncode == 0
    assert "Dry run" in result.stdout
    assert "new.txt" in lsnames(tmp_path)


def test_undo_no_manifest_reports_gracefully(cli):
    result = cli("--undo", "-y")
    assert result.returncode == 0
    assert "No undo manifest" in result.stdout


def test_undo_skips_missing_source(mkfiles, cli, tmp_path):
    mkfiles("old.txt")
    cli("--sub", "old", "new", "-y")
    (tmp_path / "new.txt").unlink()
    result = cli("--undo", "-y")
    assert result.returncode == 0
    assert "will skip" in result.stdout


def test_undo_skips_conflicting_target(mkfiles, cli, tmp_path):
    mkfiles("old.txt")
    cli("--sub", "old", "new", "-y")
    (tmp_path / "old.txt").touch()
    result = cli("--undo", "-y")
    assert result.returncode == 0
    assert "will skip" in result.stdout


def test_undo_cannot_be_combined_with_transforms(cli):
    result = cli("--undo", "--sub", "a", "b")
    assert result.returncode != 0


def test_undo_reverses_multiple_files(mkfiles, cli, lsnames, tmp_path):
    mkfiles("old_one.txt", "old_two.txt", "old_three.txt")
    cli("--sub", "old", "new", "-y")
    result = cli("--undo", "-y")
    assert result.returncode == 0
    assert lsnames(tmp_path) == {"old_one.txt", "old_two.txt", "old_three.txt"}
