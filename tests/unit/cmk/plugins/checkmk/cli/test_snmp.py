#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import GlobalOptions
from cmk.plugins.checkmk.cli.snmp import cli_command_snmptranslate, cli_command_snmpwalk


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
