#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.cli.engine.readers import parsed as cli_parsed
from cmk.cli.engine.readers import record as cli_record
from cmk.cli.engine.readers import Recorded as CLIRecorded
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

from ._logger import null_logger

_FLAG = CLIFlag(long="flag", short="f", help="a flag")

_COUNTED_COUNT = CLICount(long="counted", short="c", help="counts")

_NUMBER_VALUE = CLIValue(long="number", help="a number", placeholder="N", parse=int)

_PLUGINS_FLAG = CLIFlag(long="plugins", help="the plugins", deprecated_names=frozenset({"checks"}))


def test_an_option_is_found_under_its_short_spelling() -> None:
    assert cli_parsed([("-f", "")], null_logger()).flag(_FLAG)


def test_an_option_that_was_not_given_is_not_found() -> None:
    assert not cli_parsed([("--other", "")], null_logger()).flag(_FLAG)


def test_every_spelling_of_an_option_counts() -> None:
    assert cli_parsed([("-c", ""), ("--counted", "")], null_logger()).count(_COUNTED_COUNT) == 2


def test_an_option_is_given_its_arguments() -> None:
    assert cli_parsed([("--number", "5")], null_logger()).value(_NUMBER_VALUE) == 5


def test_a_deprecated_option_reaches_the_option_it_replaces() -> None:
    assert cli_parsed([("--checks", "")], null_logger()).flag(_PLUGINS_FLAG)


def test_a_deprecated_option_warns_about_the_one_it_replaces(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        cli_parsed([("--checks", "")], logging.getLogger("cmk.test")).flag(_PLUGINS_FLAG)

    assert caplog.messages == ["'--checks' is deprecated in favour of option 'plugins'"]


def test_the_recorder_keeps_the_options_in_reading_order() -> None:
    def request(reader: CLIReader) -> None:
        reader.value(_NUMBER_VALUE)
        reader.flag(_FLAG)

    assert cli_record(request) == CLIRecorded(options=[_NUMBER_VALUE, _FLAG])
