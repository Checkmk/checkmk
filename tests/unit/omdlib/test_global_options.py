#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.global_options import GlobalOptions, parse_global_opts


@pytest.mark.parametrize(
    "args, expected_options, expected_args",
    [
        (
            ["config", "v240p8", "show"],
            GlobalOptions(),
            ["config", "v240p8", "show"],
        ),
        (
            ["versions"],
            GlobalOptions(),
            ["versions"],
        ),
        (
            ["version"],
            GlobalOptions(),
            ["version"],
        ),
        (
            ["sites"],
            GlobalOptions(),
            ["sites"],
        ),
        (
            [],
            GlobalOptions(),
            [],
        ),
        (
            ["-V", "2.4.0p8.cce", "create", "s"],
            GlobalOptions(
                version="2.4.0p8.cce",
            ),
            ["create", "s"],
        ),
        (
            ["-f", "-V", "2.4.0p8.cce", "create", "s"],
            GlobalOptions(
                version="2.4.0p8.cce",
                force=True,
            ),
            ["create", "s"],
        ),
        (
            ["--force", "-V", "2.4.0p8.cce", "create", "s"],
            GlobalOptions(
                version="2.4.0p8.cce",
                force=True,
            ),
            ["create", "s"],
        ),
        (
            ["--verbose", "create", "s"],
            GlobalOptions(verbose=True),
            ["create", "s"],
        ),
        (
            ["-fv", "-V", "2.4.0p8.cce", "create", "s"],
            GlobalOptions(
                version="2.4.0p8.cce",
                force=True,
                verbose=True,
            ),
            ["create", "s"],
        ),
        (
            ["-V", "-v", "create", "s"],
            GlobalOptions(
                version="-v",
            ),
            ["create", "s"],
        ),
        (
            ["-V", "create", "s"],
            GlobalOptions(
                version="create",
            ),
            ["s"],
        ),
    ],
)
def test_parse_global_options_valid(
    args: list[str], expected_options: GlobalOptions, expected_args: list[str]
) -> None:
    assert parse_global_opts(args) == (expected_options, expected_args)


@pytest.mark.parametrize(
    "args, expected_message",
    [
        (
            ["-V"],
            "Option V needs an argument",
        ),
        (
            ["--if", "-v", "-V", "2.4.0p8.cce", "create", "s"],
            "Invalid global option --if",
        ),
    ],
)
def test_parse_global_options_invalid(args: list[str], expected_message: str) -> None:
    with pytest.raises(SystemExit, match=expected_message):
        parse_global_opts(args)
