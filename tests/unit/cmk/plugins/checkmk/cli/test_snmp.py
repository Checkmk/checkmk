#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import CommandContext, ExitCode, GlobalOptions
from cmk.plugins.checkmk.cli.snmp import cli_command_snmptranslate, cli_command_snmpwalk


def _context(*, debug_mode: bool = False) -> CommandContext:
    return CommandContext(
        omd_root=Path("/nonexistent"),
        global_options=GlobalOptions(debug=debug_mode),
        logger=logging.getLogger(__name__),
    )


def test_a_missing_walk_name_exits_three() -> None:
    assert cli_command_snmptranslate.handler_function(_context(), {}, [""]) == ExitCode.UNKNOWN


def test_a_missing_walk_name_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        cli_command_snmptranslate.handler_function(_context(), {}, [""])

    assert caplog.messages == ["Please provide the name of a SNMP walk file"]


def test_a_missing_walk_name_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="name of a SNMP walk file"):
        cli_command_snmptranslate.handler_function(_context(debug_mode=True), {}, [""])


def test_oids_and_extra_oids_together_exit_three() -> None:
    assert (
        cli_command_snmpwalk.handler_function(
            _context(), {"oid": ("1.3",), "extraoid": ("1.4",)}, []
        )
        == ExitCode.UNKNOWN
    )


def test_oids_and_extra_oids_together_are_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="--oid and --extraoid"):
        cli_command_snmpwalk.handler_function(
            _context(debug_mode=True), {"oid": ("1.3",), "extraoid": ("1.4",)}, []
        )
