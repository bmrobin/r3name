import argparse
import itertools
from dataclasses import FrozenInstanceError

import pytest

from r3name.config import (
    FilteringOptions,
    NumberingOptions,
    ParsedOptions,
    ProgramOptions,
    TransformOptions,
)


def make_namespace(**overrides):
    defaults = {
        "path": ".",
        "regex": None,
        "sub": None,
        "strip": None,
        "case": None,
        "number": False,
        "num_start": 1,
        "num_pad": 2,
        "num_prefix": "",
        "num_sep": " - ",
        "files_only": False,
        "dirs_only": False,
        "ext": None,
        "hidden": False,
        "recursive": False,
        "dry_run": False,
        "yes": False,
        "undo": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.mark.parametrize(
    "option, expected",
    [
        (TransformOptions.REGEX, "regex"),
        (TransformOptions.SUBSTITUTION, "sub"),
        (TransformOptions.CASE, "case"),
        (TransformOptions.STRIP, "strip"),
        (NumberingOptions.NUMBER, "number"),
        (NumberingOptions.NUMBER_START, "num_start"),
        (NumberingOptions.NUMBER_SEPARATOR, "num_sep"),
        (NumberingOptions.NUMBER_PREFIX, "num_prefix"),
        (NumberingOptions.NUMBER_PADDING, "num_pad"),
        (FilteringOptions.EXTENSION, "ext"),
        (FilteringOptions.FILES_ONLY, "files_only"),
        (FilteringOptions.DIRECTORIES_ONLY, "dirs_only"),
        (FilteringOptions.INCLUDE_HIDDEN_FILES, "hidden"),
        (FilteringOptions.RECURSIVE, "recursive"),
        (ProgramOptions.DRY_RUN, "dry_run"),
        (ProgramOptions.RUN, "yes"),
        (ProgramOptions.UNDO, "undo"),
    ],
)
def test_dest_mapping_from_enums(option, expected):
    assert ParsedOptions._dest(option) == expected


def test_transform_case_choices():
    assert TransformOptions.case_choices() == ["upper", "lower", "title"]


def test_numbering_defaults():
    assert NumberingOptions.default_number_start() == 1
    assert NumberingOptions.default_number_pad() == 2


@pytest.mark.parametrize(
    "field, value",
    [
        ("path", "~/Music"),
        ("regex", (r"\\s+", "_")),
        ("sub", ("old", "new")),
        ("strip", " _-"),
        ("case", "title"),
        ("number", True),
        ("num_start", 11),
        ("num_pad", 4),
        ("num_prefix", "trk-"),
        ("num_sep", "_"),
        ("files_only", True),
        ("dirs_only", True),
        ("ext", "flac"),
        ("hidden", True),
        ("recursive", True),
        ("dry_run", True),
        ("yes", True),
        ("undo", True),
    ],
)
def test_from_namespace_maps_each_field(field, value):
    ns = make_namespace(**{field: value})
    parsed = ParsedOptions.from_namespace(ns)
    assert getattr(parsed, field) == value


def test_from_namespace_preserves_regex_and_sub_tuple_order():
    ns = make_namespace(regex=(r"(a+)", r"X\\1"), sub=("alpha", "beta"))
    parsed = ParsedOptions.from_namespace(ns)

    assert parsed.regex == (r"(a+)", r"X\\1")
    assert parsed.sub == ("alpha", "beta")


def test_from_namespace_is_frozen_immutable():
    parsed = ParsedOptions.from_namespace(make_namespace())
    with pytest.raises(FrozenInstanceError):
        setattr(parsed, "path", "new")


def test_from_namespace_raises_on_missing_required_namespace_attribute():
    ns = make_namespace()
    delattr(ns, "num_start")
    with pytest.raises(AttributeError):
        ParsedOptions.from_namespace(ns)


@pytest.mark.parametrize("case", TransformOptions.case_choices())
def test_from_namespace_accepts_all_case_choices(case):
    parsed = ParsedOptions.from_namespace(make_namespace(case=case))
    assert parsed.case == case


@pytest.mark.parametrize(
    "num_start,num_pad,num_prefix,num_sep",
    [
        (1, 2, "", " - "),
        (0, 1, "", ""),
        (5, 3, "ch", "_"),
        (99, 5, "disc-", " :: "),
    ],
)
def test_from_namespace_numbering_permutations(num_start, num_pad, num_prefix, num_sep):
    parsed = ParsedOptions.from_namespace(
        make_namespace(
            number=True,
            num_start=num_start,
            num_pad=num_pad,
            num_prefix=num_prefix,
            num_sep=num_sep,
        )
    )
    assert parsed.number is True
    assert parsed.num_start == num_start
    assert parsed.num_pad == num_pad
    assert parsed.num_prefix == num_prefix
    assert parsed.num_sep == num_sep


_BOOLEAN_OPTIONS = [
    ParsedOptions._dest(NumberingOptions.NUMBER),
    ParsedOptions._dest(FilteringOptions.FILES_ONLY),
    ParsedOptions._dest(FilteringOptions.DIRECTORIES_ONLY),
    ParsedOptions._dest(FilteringOptions.INCLUDE_HIDDEN_FILES),
    ParsedOptions._dest(FilteringOptions.RECURSIVE),
    ParsedOptions._dest(ProgramOptions.DRY_RUN),
    ParsedOptions._dest(ProgramOptions.RUN),
    ParsedOptions._dest(ProgramOptions.UNDO),
]


@pytest.mark.parametrize(
    "flags", itertools.product([False, True], repeat=len(_BOOLEAN_OPTIONS))
)
def test_from_namespace_all_boolean_flag_permutations(flags):
    kwargs = dict(zip(_BOOLEAN_OPTIONS, flags, strict=True))
    parsed = ParsedOptions.from_namespace(make_namespace(**kwargs))
    for name, expected in kwargs.items():
        assert getattr(parsed, name) is expected


@pytest.mark.parametrize("ext", [None, "txt", ".txt", "FLAC", "tar.gz"])
def test_from_namespace_extension_permutations(ext):
    parsed = ParsedOptions.from_namespace(make_namespace(ext=ext))
    assert parsed.ext == ext


def test_from_namespace_complex_configuration_combo():
    parsed = ParsedOptions.from_namespace(
        make_namespace(
            path="/tmp/media",
            regex=(r"\\s+", "_"),
            sub=("draft", "final"),
            strip=" _-",
            case="lower",
            number=True,
            num_start=42,
            num_pad=3,
            num_prefix="trk",
            num_sep="__",
            files_only=True,
            dirs_only=False,
            ext="flac",
            hidden=True,
            recursive=True,
            dry_run=True,
            yes=True,
            undo=False,
        )
    )

    assert parsed.path == "/tmp/media"
    assert parsed.regex == (r"\\s+", "_")
    assert parsed.sub == ("draft", "final")
    assert parsed.strip == " _-"
    assert parsed.case == "lower"
    assert parsed.number is True
    assert parsed.num_start == 42
    assert parsed.num_pad == 3
    assert parsed.num_prefix == "trk"
    assert parsed.num_sep == "__"
    assert parsed.files_only is True
    assert parsed.dirs_only is False
    assert parsed.ext == "flac"
    assert parsed.hidden is True
    assert parsed.recursive is True
    assert parsed.dry_run is True
    assert parsed.yes is True
    assert parsed.undo is False
