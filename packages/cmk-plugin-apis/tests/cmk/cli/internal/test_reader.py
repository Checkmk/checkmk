#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from collections.abc import Sequence

import pytest

from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

_FLAG = CLIFlag(long="flag", help="a flag")

_COUNTED_COUNT = CLICount(long="counted", help="counts")

_NUMBER_VALUE = CLIValue(long="number", help="a number", placeholder="N", parse=int)

_NUMBERS_VALUES = CLIValues(long="numbers", help="numbers", placeholder="N", parse=int)

_HOST_ARGUMENT = CLIArgument(placeholder="HOST", parse=str)

_NUMBERS_ARGUMENTS = CLIArguments(placeholder="N...", parse=int)


def _reader(declaration: CLIDeclaration, given: Sequence[str]) -> CLIReader:
    return CLIReader(lambda read: given if read == declaration else ())


def test_a_flag_that_was_given_reads_true() -> None:
    assert _reader(_FLAG, [""]).flag(_FLAG)


def test_a_flag_that_was_not_given_reads_false() -> None:
    assert not _reader(_FLAG, []).flag(_FLAG)


def test_a_counted_option_counts_how_often_it_was_given() -> None:
    assert _reader(_COUNTED_COUNT, ["", ""]).count(_COUNTED_COUNT) == 2


def test_the_last_of_repeated_values_is_parsed() -> None:
    assert _reader(_NUMBER_VALUE, ["5", "7"]).value(_NUMBER_VALUE) == 7


def test_a_value_that_was_not_given_reads_none() -> None:
    assert _reader(_NUMBER_VALUE, []).value(_NUMBER_VALUE) is None


def test_values_are_parsed_in_order() -> None:
    assert _reader(_NUMBERS_VALUES, ["5", "3"]).values(_NUMBERS_VALUES) == (5, 3)


def test_an_argument_is_parsed() -> None:
    assert _reader(_HOST_ARGUMENT, ["myhost"]).argument(_HOST_ARGUMENT) == "myhost"


def test_an_argument_that_was_not_given_reads_none() -> None:
    assert _reader(_HOST_ARGUMENT, []).argument(_HOST_ARGUMENT) is None


def test_arguments_are_parsed_in_order() -> None:
    assert _reader(_NUMBERS_ARGUMENTS, ["5", "3"]).arguments(_NUMBERS_ARGUMENTS) == (5, 3)


def test_an_option_argument_the_conversion_rejects_is_reported() -> None:
    with pytest.raises(
        ValueError, match="--number: Invalid argument 'not a number': invalid literal"
    ):
        _reader(_NUMBER_VALUE, ["not a number"]).value(_NUMBER_VALUE)


def test_a_positional_argument_the_conversion_rejects_is_reported() -> None:
    with pytest.raises(ValueError, match=r"N\.\.\.: Invalid argument 'x': invalid literal"):
        _reader(_NUMBERS_ARGUMENTS, ["x"]).arguments(_NUMBERS_ARGUMENTS)


def test_a_rejected_argument_hides_the_conversion_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        _reader(_NUMBER_VALUE, ["not a number"]).value(_NUMBER_VALUE)
    assert "During handling" not in "".join(traceback.format_exception(excinfo.value))
