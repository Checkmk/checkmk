#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.cli.engine.options import long_getopt_specs as cli_long_getopt_specs
from cmk.cli.engine.options import parse_general_options as cli_parse_general_options
from cmk.cli.engine.options import short_getopt_specs as cli_short_getopt_specs
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Value as CLIValue


def test_a_general_flag_is_collected() -> None:
    assert cli_parse_general_options([("--debug", "")]) == CLIGlobalOptions(debug=True)


def test_the_verbosity_counts_the_short_and_long_spelling_alike() -> None:
    assert cli_parse_general_options([("-v", ""), ("--verbose", "")]) == CLIGlobalOptions(
        verbosity=2
    )


def test_an_option_that_is_not_a_general_one_is_left_alone() -> None:
    assert cli_parse_general_options([("--flag", "")]) == CLIGlobalOptions()


def test_a_deprecated_spelling_is_a_long_getopt_spec_too() -> None:
    option = CLIFlag(long="plugins", help="the plugins", deprecated_names=frozenset({"checks"}))

    assert cli_long_getopt_specs(option) == ["plugins", "checks"]


def test_an_option_with_an_argument_requires_it_in_its_long_spec() -> None:
    option = CLIValue(long="number", help="a number", placeholder="N", parse=int)

    assert cli_long_getopt_specs(option) == ["number="]


def test_an_option_with_an_argument_requires_it_in_its_short_spec() -> None:
    option = CLIValue(long="number", short="n", help="a number", placeholder="N", parse=int)

    assert cli_short_getopt_specs(option) == ["n:"]
