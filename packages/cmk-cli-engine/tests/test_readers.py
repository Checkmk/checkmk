#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.cli.engine.options import Option as CLIOption
from cmk.cli.engine.readers import option_count as cli_option_count
from cmk.cli.engine.readers import option_names as cli_option_names
from cmk.cli.engine.readers import option_string as cli_option_string
from cmk.cli.engine.readers import option_strings as cli_option_strings
from cmk.cli.engine.readers import parse_sub_options as cli_parse_sub_options

from ._logger import null_logger


def test_an_argument_to_a_flag_option_is_rejected() -> None:
    option = CLIOption(long_option="flag", short_help="a flag")

    with pytest.raises(ValueError):
        cli_parse_sub_options([option], [("--flag", "a value")], null_logger())


def test_an_option_argument_the_conversion_rejects_is_reported() -> None:
    option = CLIOption(
        long_option="number",
        short_help="a number",
        argument=True,
        argument_descr="N",
        argument_conv=int,
    )

    with pytest.raises(ValueError):
        cli_parse_sub_options([option], [("--number", "not a number")], null_logger())


def test_a_deprecated_option_warns_about_the_one_it_replaces(
    caplog: pytest.LogCaptureFixture,
) -> None:
    option = CLIOption(
        long_option="plugins", short_help="the plugins", deprecated_long_options={"checks"}
    )

    with caplog.at_level(logging.WARNING):
        cli_parse_sub_options([option], [("--checks", "")], logging.getLogger("cmk.test"))

    assert caplog.messages == ["'--checks' is deprecated in favour of option 'plugins'"]


def test_a_missing_string_option_has_no_value() -> None:
    assert cli_option_string({}, "snmp-backend") is None


def test_a_string_option_that_is_not_a_string_is_rejected() -> None:
    with pytest.raises(TypeError):
        cli_option_string({"snmp-backend": 23}, "snmp-backend")


def test_a_counted_option_that_was_never_given_is_rejected() -> None:
    with pytest.raises(TypeError):
        cli_option_count({}, "discover")


def test_a_name_of_the_wrong_type_is_rejected() -> None:
    with pytest.raises(TypeError):
        cli_option_names({"plugins": {23}}, "plugins", str)


def test_a_missing_collected_option_has_no_values() -> None:
    assert cli_option_strings({}, "oid") == ()


def test_collected_values_that_are_not_strings_are_rejected() -> None:
    with pytest.raises(TypeError):
        cli_option_strings({"oid": (23,)}, "oid")
