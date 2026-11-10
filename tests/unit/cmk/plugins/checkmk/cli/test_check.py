#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.check import (
    _checking_request,
    _run_check,
    CheckingRequest,
    cli_command_check,
)
from cmk.plugins.checkmk.cli.options import FileCacheRequest, PluginSelectionRequest


def test_more_than_a_host_and_an_address_are_rejected() -> None:
    logger = logging.getLogger(__name__)
    context = CLIContext(
        omd_root=Path("/nonexistent"), global_options=CLIGlobalOptions(), logger=logger
    )
    request = _checking_request(CLIParsedOptions([], logger))

    assert _run_check(context, request, ["host1", "host2", "host3"]) == CLIExitCode.UNKNOWN


def test_check_declares_its_options_in_help_order() -> None:
    recorded = CLIRecordedOptions()
    cli_command_check.request(recorded)

    assert [option.long for option in recorded.options] == [
        "cache",
        "no-cache",
        "no-tcp",
        "usewalk",
        "snmp-backend",
        "no-submit",
        "perfdata",
        "detect-sections",
        "plugins",
        "detect-plugins",
        "fake-dns",
    ]


def test_the_checking_request_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions(
        [
            ("--no-cache", ""),
            ("--usewalk", ""),
            ("--snmp-backend", "classic"),
            ("--no-submit", ""),
            ("--detect-sections", "df,mem"),
            ("--plugins", "df"),
            ("--checks", "cpu_loads"),
            ("--fake-dns", "1.2.3.4"),
        ],
        logging.getLogger(__name__),
    )

    assert _checking_request(options) == CheckingRequest(
        file_cache=FileCacheRequest(cache=False, no_cache=True, no_tcp=False),
        usewalk=True,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        no_submit=True,
        perfdata=False,
        plugin_selection=PluginSelectionRequest(
            detect_sections=frozenset({SectionName("df"), SectionName("mem")}),
            plugins=frozenset({CheckPluginName("df")}),
            detect_plugins=frozenset({"cpu_loads"}),
        ),
        fake_dns=HostAddress("1.2.3.4"),
    )
