#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.cli.engine.options import parse_general_options as cli_parse_general_options
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions


def test_a_general_flag_is_collected() -> None:
    assert cli_parse_general_options([("--debug", "")]) == CLIGlobalOptions(debug=True)


def test_the_verbosity_counts_the_short_and_long_spelling_alike() -> None:
    assert cli_parse_general_options([("-v", ""), ("--verbose", "")]) == CLIGlobalOptions(
        verbosity=2
    )


def test_an_option_that_is_not_a_general_one_is_left_alone() -> None:
    assert cli_parse_general_options([("--flag", "")]) == CLIGlobalOptions()
