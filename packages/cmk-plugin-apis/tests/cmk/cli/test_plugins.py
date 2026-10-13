#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cli.internal import (
    Args,
    CLICommand,
    CLIOption,
    entry_point_prefixes,
    GlobalOptions,
    Options,
)


def test_entry_point_prefixes() -> None:
    assert entry_point_prefixes() == {CLICommand: "cli_command_"}


def _print_version(
    _app: object, _global_optoins: GlobalOptions, _options: Options, _args: Args
) -> int:
    return 0


def test_command_is_named_after_its_long_option() -> None:
    command = CLICommand(
        long_option="version",
        handler_function=_print_version,
        short_help="Print the version",
    )
    assert command.name == "version"


def test_option_argument_requires_description() -> None:
    with pytest.raises(ValueError, match="argument description"):
        CLIOption(long_option="cache", short_help="Use cache", argument=True)


def test_option_repeat_allows_argument() -> None:
    option = CLIOption(
        long_option="oid",
        short_help="Walk on this OID",
        argument=True,
        argument_descr="A",
        repeat=True,
    )
    assert option.repeat
