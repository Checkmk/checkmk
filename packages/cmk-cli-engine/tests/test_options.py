#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

from cmk.cli.engine.options import long_getopt_specs as cli_long_getopt_specs
from cmk.cli.engine.options import read_global_options as cli_read_global_options
from cmk.cli.engine.options import short_getopt_specs as cli_short_getopt_specs
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Value as CLIValue

from ._logger import null_logger


def _read(options: Sequence[tuple[str, str]]) -> CLIGlobalOptions:
    return cli_read_global_options(CLIParsedOptions(options, null_logger()))


def test_a_general_flag_is_collected() -> None:
    assert _read([("--debug", "")]) == CLIGlobalOptions(debug=True)


def test_the_verbosity_counts_the_short_and_long_spelling_alike() -> None:
    assert _read([("-v", ""), ("--verbose", "")]) == CLIGlobalOptions(verbosity=2)


def test_the_log_file_is_a_path() -> None:
    assert _read([("--log-file", "var/log/cmk.log")]) == CLIGlobalOptions(
        log_file=Path("var/log/cmk.log")
    )


def test_an_option_that_is_not_a_general_one_is_left_alone() -> None:
    assert _read([("--flag", "")]) == CLIGlobalOptions()


def test_a_deprecated_spelling_is_a_long_getopt_spec_too() -> None:
    option = CLIFlag(long="plugins", help="the plugins", deprecated_names=frozenset({"checks"}))

    assert cli_long_getopt_specs(option) == ["plugins", "checks"]


def test_an_option_with_an_argument_requires_it_in_its_long_spec() -> None:
    option = CLIValue(long="number", help="a number", placeholder="N", parse=int)

    assert cli_long_getopt_specs(option) == ["number="]


def test_an_option_with_an_argument_requires_it_in_its_short_spec() -> None:
    option = CLIValue(long="number", short="n", help="a number", placeholder="N", parse=int)

    assert cli_short_getopt_specs(option) == ["n:"]
