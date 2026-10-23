#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.ccc import debug
from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import GlobalOptions
from cmk.plugins.checkmk.cli.snmp import cli_command_snmptranslate, cli_command_snmpwalk


@pytest.fixture(name="without_debug")
def _without_debug() -> Iterator[None]:
    was_enabled = debug.enabled()
    debug.disable()
    try:
        yield
    finally:
        if was_enabled:
            debug.enable()


def test_a_missing_walk_name_exits_three() -> None:
    assert (
        cli_command_snmptranslate.handler_function(Path("/nonexistent"), GlobalOptions(), {}, [""])
        == 3
    )


def test_a_missing_walk_name_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="cmk.base"):
        cli_command_snmptranslate.handler_function(Path("/nonexistent"), GlobalOptions(), {}, [""])

    assert caplog.messages == ["Please provide the name of a SNMP walk file"]


def test_a_missing_walk_name_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="name of a SNMP walk file"):
        cli_command_snmptranslate.handler_function(
            Path("/nonexistent"), GlobalOptions(debug=True), {}, [""]
        )


def test_oids_and_extra_oids_together_exit_three() -> None:
    assert (
        cli_command_snmpwalk.handler_function(
            Path("/nonexistent"), GlobalOptions(), {"oid": ("1.3",), "extraoid": ("1.4",)}, []
        )
        == 3
    )


@pytest.mark.usefixtures("without_debug")
def test_a_command_given_debug_switches_debug_mode_on() -> None:
    with pytest.raises(MKGeneralException):
        cli_command_snmpwalk.handler_function(
            Path("/nonexistent"),
            GlobalOptions(debug=True),
            {"oid": ("1.3",), "extraoid": ("1.4",)},
            [],
        )

    assert debug.enabled()
