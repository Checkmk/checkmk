#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

from cmk.cli.engine.options import GlobalOptions as CLIEngineGlobalOptions
from cmk.cli.engine.options import read_global_options as cli_read_global_options
from cmk.cli.engine.readers import parsed as cli_parsed


def _read(options: Sequence[tuple[str, str]]) -> CLIEngineGlobalOptions:
    return cli_read_global_options(cli_parsed(options, {}))


def test_a_general_flag_is_collected() -> None:
    assert _read([("--debug", "")]) == CLIEngineGlobalOptions(debug=True)


def test_the_verbosity_counts_the_short_and_long_spelling_alike() -> None:
    assert _read([("-v", ""), ("--verbose", "")]) == CLIEngineGlobalOptions(verbosity=2)


def test_the_log_file_is_a_path() -> None:
    assert _read([("--log-file", "var/log/cmk.log")]) == CLIEngineGlobalOptions(
        log_file=Path("var/log/cmk.log")
    )


def test_an_option_that_is_not_a_general_one_is_left_alone() -> None:
    assert _read([("--flag", "")]) == CLIEngineGlobalOptions()
