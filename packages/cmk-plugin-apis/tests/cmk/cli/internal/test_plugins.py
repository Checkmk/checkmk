#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import untyped_request as cli_untyped_request
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues


class _EveryOptionGivenOnce:
    """Stands in for the engine's reader: every option was given once, with the argument "1" """

    def flag(self, _option: CLIFlag) -> bool:
        return True

    def count(self, _option: CLICount) -> int:
        return 1

    def value[T](self, option: CLIValue[T]) -> T | None:
        return option.parse("1")

    def values[T](self, option: CLIValues[T]) -> Sequence[T]:
        return (option.parse("1"),)


def test_entry_point_prefixes() -> None:
    assert cli_entry_point_prefixes() == {CLICommand: "cli_command_"}


def test_untyped_request_reads_every_option_into_the_mapping() -> None:
    request = cli_untyped_request(
        [
            CLIOption(long="loud", help="Shout"),
            CLIOption(long="often", help="Shout more", repeat=True),
            CLIOption(
                long="times",
                help="Repeat",
                argument="N",
                parse=int,
            ),
            CLIOption(
                long="names",
                help="Names",
                argument="N",
                repeat=True,
            ),
        ]
    )

    assert request(_EveryOptionGivenOnce()) == {
        "loud": True,
        "often": 1,
        "times": 1,
        "names": ("1",),
    }


def _handler(_context: CLIContext, _request: object, _args: CLIArgs) -> CLIExitCode:
    return CLIExitCode.SUCCESS


def test_a_command_name_must_be_an_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        CLICommand(
            name="bake-agents",
            long="bake-agents",
            help="Bake",
            request=cli_untyped_request(),
            handler=_handler,
        )


def test_an_option_without_argument_parses_none() -> None:
    with pytest.raises(ValueError, match="does not take"):
        CLIOption(long="cache", help="Use the cache", parse=int)
