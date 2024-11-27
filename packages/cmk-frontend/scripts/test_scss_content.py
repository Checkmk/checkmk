#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import sys
import traceback
from collections.abc import Callable, Iterable
from pathlib import Path
from textwrap import indent

PROJECT_ROOT = Path(__file__).parent
GIT_ROOT = PROJECT_ROOT / "../../../"


def is_enterprise_repo() -> bool:
    return (GIT_ROOT / "omd" / "packages" / "enterprise").exists()


def scss_files() -> Iterable[Path]:
    return (PROJECT_ROOT / "src/themes").glob("**/*.scss")


def _scss_variables(_scss_files: Iterable[Path]) -> tuple[set[str], set[str]]:
    variable_definition = re.compile(r"\s*(\$[-_a-zA-Z0-9]+)\s*:")
    variable_usage = re.compile(r"(\$[-_a-zA-Z0-9]+)")

    definitions, usages = set(), set()
    for file_ in _scss_files:
        with open(file_) as f:
            for l in f:
                if definition := variable_definition.match(l):
                    definitions.add(definition.group(1))

                # Need to search for usages like this - after splitting away potential definitions
                # (before a colon) - because re does not support overlapping matches, and there may
                # be more than one variable usage per line.
                after_colon: str = l.split(":", 1)[-1]
                if usage := variable_usage.findall(after_colon):
                    usages.update(usage)
    return definitions, usages


def _get_regex_matches_in_scss_files(
    regex_pattern: re.Pattern,
    exclude_files: Iterable[str] | None = None,
) -> Iterable[tuple[str, Iterable[tuple[str, str]]]]:
    """Return a generator holding all matches of regex_pattern in scss_files (without exclude_files)
    Returned tuples hold the scss file's path and a list of line and match per match
    E.g.: (
            "git/check_mk/web/htdocs/themes/facelift/_main.scss",
            [
                ("Line 123", "rgb(0, 0, 0)"),
                ("Line 234", "rgb(255, 255, 255)"),
            ]
          )
    """
    for scss_file in scss_files():
        if exclude_files and scss_file.name in exclude_files:
            continue

        with open(scss_file) as f:
            file_matches: list[tuple[str, str]] = []
            for i, l in enumerate(f):
                if match := regex_pattern.search(l):
                    file_matches.append((f"Line: {str(i)}", match.group()))

            if file_matches:
                yield (str(scss_file), file_matches)


def test_unused_scss_variables() -> None:
    definitions, usages = _scss_variables(scss_files())
    unused = [var for var in definitions if var not in usages]
    expected = []

    if not is_enterprise_repo():
        expected.append("$ntop-protocol-painter-padding-top")

    assert sorted(unused) == sorted(expected), f"Found unused SCSS variables {unused}"


def test_rgb_color_codes() -> None:
    """No rgb color codes allowed outside of _variables*.scss files"""
    rgb_pattern = re.compile(r"rgb\([^\)]*\)")
    exclude_files = ["_variables.scss", "_variables_common.scss"]
    matches = list(_get_regex_matches_in_scss_files(rgb_pattern, exclude_files))
    assert not matches, f"RGB color codes found outside of variable SCSS files: {matches}"


def test_hex_color_codes() -> None:
    """No hex color codes allowed at all"""
    hex_pattern = re.compile(r":.*#[a-fA-F0-9]{3,6}")
    matches = list(_get_regex_matches_in_scss_files(hex_pattern))
    assert not matches, f"Hex color codes found {matches}"


def test(function: Callable) -> None:
    sys.stdout.write(function.__name__ + "\n")
    try:
        function()
    except Exception:
        sys.stdout.write(indent(traceback.format_exc().rstrip("\n"), "  ") + "\n")
        sys.stdout.write("  FAIL\n")
    else:
        sys.stdout.write("  OK\n")


if __name__ == "__main__":
    test(test_unused_scss_variables)
    test(test_rgb_color_codes)
    test(test_hex_color_codes)
