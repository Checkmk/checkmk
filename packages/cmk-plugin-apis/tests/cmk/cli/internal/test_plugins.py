#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Option as CLIOption


def test_entry_point_prefixes() -> None:
    assert cli_entry_point_prefixes() == {CLICommand: "cli_command_"}


def _handler(_context: CLIContext, _request: object, _args: CLIArgs) -> CLIExitCode:
    return CLIExitCode.SUCCESS


def test_a_command_name_must_be_an_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        CLICommand(name="bake-agents", long="bake-agents", help="Bake", handler_function=_handler)


def test_an_option_without_argument_parses_none() -> None:
    with pytest.raises(ValueError, match="does not take"):
        CLIOption(long="cache", help="Use the cache", parse=int)
