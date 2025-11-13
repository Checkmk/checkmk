#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

import pytest

from cmk.utils.regex import combine_patterns


@pytest.mark.parametrize(
    "patterns, expected",
    [
        ([], r"(?:)"),
        # Negation, no modifier
        ([r"cpu"], r"(?:cpu)"),
        ([(False, r"cpu")], r"(?:cpu)"),
        ([(True, r"cpu")], r"(?!cpu)"),
        ([r"cpu", r"disk"], r"(?:(?:cpu)|(?:disk))"),
        ([r"cpu", (False, r"disk")], r"(?:(?:cpu)|(?:disk))"),
        ([r"cpu", (True, r"disk")], r"(?:(?:cpu)|(?!disk))"),
        # Negation, modifier
        ([r"(?i)cpu"], r"(?i:(?:cpu))"),
        ([(True, r"(?i)cpu")], r"(?i:(?!cpu))"),
        # Multiple modifier
        ([r"(?i)cpu", r"memory"], r"(?:(?i:(?:cpu))|(?:memory))"),
        ([r"(?i)cpu", r"(?s)memory", r"disk"], r"(?:(?i:(?:cpu))|(?s:(?:memory))|(?:disk))"),
        ([(True, r"cpu"), r"(?s)memory", r"disk"], r"(?:(?!cpu)|(?s:(?:memory))|(?:disk))"),
        # Local and global modifier
        ([r"(?i)(?u-i:cpu)"], r"(?i:(?:(?u-i:cpu)))"),
        # Multiple patterns
        ([r"(?i)(?u-i:cpu)(.*)"], r"(?i:(?:(?u-i:cpu)(.*)))"),
        # Customer example that broke previous implementation
        ([r"(?i)(.\\\[NM])", r"(?i)(._NM$)"], r"(?:(?i:(?:(.\\\[NM])))|(?i:(?:(._NM$))))"),
    ],
)
def test_combine_patterns(patterns: list[tuple[bool, str]] | list[str], expected: str) -> None:
    pattern = combine_patterns(patterns)
    assert combine_patterns(patterns) == expected
    re.compile(pattern)


@pytest.mark.parametrize(
    "patterns, text, expected",
    [
        ([], "", True),
        ([], "cpu", True),
        ([r"cpu"], "cpu", True),
        ([r"cpu"], "disk", False),
        ([r"cpu", r"disk"], "cpu", True),
        ([r"cpu", r"disk"], "disk", True),
        ([r"cpu", (True, r"disk")], "cpu", True),
        ([r"cpu", (True, r"disk")], "disk", False),
        ([r"cpu"], "CPU", False),
        ([r"(?i)cpu"], "CPU", True),
        ([(True, r"(?i)cpu")], "CPU", False),
        ([r"(?i)(?u-i:cpu)(.*)"], "CPU", False),
        ([r"(?i)(.\\\[NM])", r"(?i)(._NM$)"], "x_nm", True),
    ],
)
def test_combined_pattern_matching(
    patterns: list[tuple[bool, str]], text: str, expected: bool
) -> None:
    combined_pattern = combine_patterns(patterns)
    assert bool(re.match(combined_pattern, text)) == expected
