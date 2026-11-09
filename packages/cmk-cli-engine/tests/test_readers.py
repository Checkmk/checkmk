#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import traceback

import pytest

from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from ._logger import null_logger

_FLAG = CLIFlag(long="flag", short="f", help="a flag")

_COUNTED_COUNT = CLICount(long="counted", short="c", help="counts")

_NUMBER_VALUE = CLIValue(long="number", help="a number", placeholder="N", parse=int)

_NUMBERS_VALUES = CLIValues(long="numbers", help="numbers", placeholder="N", parse=int)

_PLUGINS_FLAG = CLIFlag(long="plugins", help="the plugins", deprecated_names=frozenset({"checks"}))


def test_a_flag_that_was_given_reads_true() -> None:
    assert CLIParsedOptions([("--flag", "")], null_logger()).flag(_FLAG)


def test_a_flag_that_was_not_given_reads_false() -> None:
    assert not CLIParsedOptions([("--other", "")], null_logger()).flag(_FLAG)


def test_a_flag_is_found_under_its_short_spelling() -> None:
    assert CLIParsedOptions([("-f", "")], null_logger()).flag(_FLAG)


def test_a_counted_option_counts_every_spelling() -> None:
    assert (
        CLIParsedOptions([("-c", ""), ("--counted", "")], null_logger()).count(_COUNTED_COUNT) == 2
    )


def test_a_counted_option_that_was_not_given_reads_zero() -> None:
    assert CLIParsedOptions([], null_logger()).count(_COUNTED_COUNT) == 0


def test_a_value_is_parsed() -> None:
    assert CLIParsedOptions([("--number", "5")], null_logger()).value(_NUMBER_VALUE) == 5


def test_the_last_of_repeated_values_wins() -> None:
    assert (
        CLIParsedOptions([("--number", "5"), ("--number", "7")], null_logger()).value(_NUMBER_VALUE)
        == 7
    )


def test_a_value_that_was_not_given_reads_none() -> None:
    assert CLIParsedOptions([], null_logger()).value(_NUMBER_VALUE) is None


def test_values_are_parsed_in_order() -> None:
    assert CLIParsedOptions([("--numbers", "5"), ("--numbers", "3")], null_logger()).values(
        _NUMBERS_VALUES
    ) == (5, 3)


def test_values_that_were_not_given_read_empty() -> None:
    assert CLIParsedOptions([], null_logger()).values(_NUMBERS_VALUES) == ()


def test_an_option_argument_the_conversion_rejects_is_reported() -> None:
    with pytest.raises(ValueError, match="--number: Invalid argument"):
        CLIParsedOptions([("--number", "not a number")], null_logger()).value(_NUMBER_VALUE)


def test_a_rejected_option_argument_hides_the_conversion_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        CLIParsedOptions([("--number", "not a number")], null_logger()).value(_NUMBER_VALUE)
    assert "During handling" not in "".join(traceback.format_exception(excinfo.value))


def test_a_deprecated_option_reaches_the_option_it_replaces() -> None:
    assert CLIParsedOptions([("--checks", "")], null_logger()).flag(_PLUGINS_FLAG)


def test_a_deprecated_option_warns_about_the_one_it_replaces(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        CLIParsedOptions([("--checks", "")], logging.getLogger("cmk.test")).flag(_PLUGINS_FLAG)

    assert caplog.messages == ["'--checks' is deprecated in favour of option 'plugins'"]


def test_the_recorder_reads_every_kind_as_absent() -> None:
    recorded = CLIRecordedOptions()

    assert (
        recorded.flag(_FLAG),
        recorded.count(_COUNTED_COUNT),
        recorded.value(_NUMBER_VALUE),
        recorded.values(_NUMBERS_VALUES),
    ) == (False, 0, None, ())


def test_the_recorder_keeps_the_options_in_reading_order() -> None:
    recorded = CLIRecordedOptions()
    recorded.values(_NUMBERS_VALUES)
    recorded.flag(_FLAG)

    assert [option.long for option in recorded.options] == ["numbers", "flag"]


def test_the_recorder_keeps_the_declarations_it_reads() -> None:
    recorded = CLIRecordedOptions()
    recorded.flag(_FLAG)
    recorded.count(_COUNTED_COUNT)
    recorded.value(_NUMBER_VALUE)
    recorded.values(_NUMBERS_VALUES)

    assert recorded.options == [_FLAG, _COUNTED_COUNT, _NUMBER_VALUE, _NUMBERS_VALUES]
