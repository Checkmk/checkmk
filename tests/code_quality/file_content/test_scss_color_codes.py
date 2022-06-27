#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Iterable, List, Optional, Tuple

from ..conftest import ChangedFiles
from .test_scss_variables import scss_files


def _get_regex_matches_in_scss_files(
    regex_pattern: re.Pattern,
    changed_files: ChangedFiles,
    exclude_files: Optional[Iterable[str]] = None,
) -> Iterable[Tuple[str, Iterable[Tuple[str, str]]]]:
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

        if not changed_files.is_changed(scss_file):
            continue

        with open(scss_file) as f:
            file_matches: List[Tuple[str, str]] = []
            for i, l in enumerate(f):
                if match := regex_pattern.search(l):
                    file_matches.append((f"Line: {str(i)}", match.group()))

            if file_matches:
                yield (str(scss_file), file_matches)


def test_rgb_color_codes(changed_files: ChangedFiles) -> None:
    """No rgb color codes allowed outside of _variables*.scss files"""
    rgb_pattern = re.compile(r"rgb\([^\)]*\)")
    exclude_files = ["_variables.scss", "_variables_common.scss"]
    matches = list(_get_regex_matches_in_scss_files(rgb_pattern, changed_files, exclude_files))
    assert matches == [], "RGB color codes found outside of variable SCSS files"


def test_hex_color_codes(changed_files: ChangedFiles) -> None:
    """No hex color codes allowed at all"""
    hex_pattern = re.compile(r":.*#[a-fA-F1-9]{3,6}")
    matches = list(_get_regex_matches_in_scss_files(hex_pattern, changed_files))
    assert matches == [], "Hex color codes found"
