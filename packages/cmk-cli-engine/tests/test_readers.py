#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.cli.engine.readers import assign as cli_assign
from cmk.cli.engine.readers import parsed as cli_parsed
from cmk.cli.engine.readers import record as cli_record
from cmk.cli.engine.readers import Recorded as CLIRecorded
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

from ._logger import null_logger

_FLAG = CLIFlag(long="flag", short="f", help="a flag")

_COUNTED_COUNT = CLICount(long="counted", short="c", help="counts")

_NUMBER_VALUE = CLIValue(long="number", help="a number", placeholder="N", parse=int)

_PLUGINS_FLAG = CLIFlag(long="plugins", help="the plugins", deprecated_names=frozenset({"checks"}))

_HOST_ARGUMENT = CLIArgument(placeholder="HOST", parse=str)

_ADDRESS_ARGUMENT = CLIOptionalArgument(placeholder="ADDRESS", parse=str)

_NUMBERS_ARGUMENTS = CLIArguments(placeholder="N...", parse=int)


def test_an_option_is_found_under_its_short_spelling() -> None:
    assert cli_parsed([("-f", "")], {}, null_logger()).flag(_FLAG)


def test_an_option_that_was_not_given_is_not_found() -> None:
    assert not cli_parsed([("--other", "")], {}, null_logger()).flag(_FLAG)


def test_every_spelling_of_an_option_counts() -> None:
    assert cli_parsed([("-c", ""), ("--counted", "")], {}, null_logger()).count(_COUNTED_COUNT) == 2


def test_an_option_is_given_its_arguments() -> None:
    assert cli_parsed([("--number", "5")], {}, null_logger()).value(_NUMBER_VALUE) == 5


def test_a_deprecated_option_reaches_the_option_it_replaces() -> None:
    assert cli_parsed([("--checks", "")], {}, null_logger()).flag(_PLUGINS_FLAG)


def test_a_deprecated_option_warns_about_the_one_it_replaces(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        cli_parsed([("--checks", "")], {}, logging.getLogger("cmk.test")).flag(_PLUGINS_FLAG)

    assert caplog.messages == ["'--checks' is deprecated in favour of option 'plugins'"]


def test_a_positional_argument_is_given_what_was_assigned_to_it() -> None:
    assert cli_parsed([], {"HOST": ["myhost"]}, null_logger()).argument(_HOST_ARGUMENT) == "myhost"


def test_a_positional_argument_is_read_by_its_placeholder() -> None:
    argument = CLIArgument(placeholder="HOST", parse=lambda text: text.upper())

    assert cli_parsed([], {"HOST": ["myhost"]}, null_logger()).argument(argument) == "MYHOST"


def _read_all(reader: CLIReader) -> None:
    reader.argument(_HOST_ARGUMENT)
    reader.value(_NUMBER_VALUE)
    reader.arguments(_NUMBERS_ARGUMENTS)
    reader.flag(_FLAG)


def test_the_recorder_keeps_the_options_and_the_positional_arguments_in_reading_order() -> None:
    assert cli_record(_read_all) == CLIRecorded(
        options=[_NUMBER_VALUE, _FLAG], positional=[_HOST_ARGUMENT, _NUMBERS_ARGUMENTS]
    )


def test_arguments_are_assigned_in_command_line_order() -> None:
    assert cli_assign([_HOST_ARGUMENT, _ADDRESS_ARGUMENT], ["myhost", "1.2.3.4"]) == {
        "HOST": ["myhost"],
        "ADDRESS": ["1.2.3.4"],
    }


def test_a_missing_optional_argument_is_assigned_nothing() -> None:
    assert cli_assign([_HOST_ARGUMENT, _ADDRESS_ARGUMENT], ["myhost"]) == {
        "HOST": ["myhost"],
        "ADDRESS": [],
    }


def test_a_missing_required_argument_is_reported() -> None:
    with pytest.raises(ValueError, match="HOST: Missing argument"):
        cli_assign([_HOST_ARGUMENT], [])


def test_arguments_are_assigned_all_that_are_left() -> None:
    assert cli_assign([_HOST_ARGUMENT, _NUMBERS_ARGUMENTS], ["myhost", "5", "3"]) == {
        "HOST": ["myhost"],
        "N...": ["5", "3"],
    }


def test_an_argument_left_unassigned_is_reported() -> None:
    with pytest.raises(ValueError, match="surplus: Unexpected argument"):
        cli_assign([_HOST_ARGUMENT], ["myhost", "surplus"])
