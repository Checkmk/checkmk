#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.engine.arguments import parse as cli_parse
from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.options import general_options as cli_general_options
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.plugins.checkmk.cli.check import _checking_request, CheckingRequest, cli_command_check
from cmk.plugins.checkmk.cli.options import FileCacheRequest, PluginSelectionRequest


def test_fake_dns_reaches_the_implicit_check() -> None:
    parsed = cli_parse(
        CLICommands(
            plugins=[cli_make_command(cli_command_check)], general_options=cli_general_options()
        ),
        ["cmk", "--fake-dns", "1.2.3.4", "myhost"],
    )

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command.name, parsed.options, parsed.arguments) == (
        "check",
        [("--fake-dns", "1.2.3.4")],
        ["myhost"],
    )


def test_check_declares_its_options_in_help_order() -> None:
    recorded = CLIRecordedOptions()
    cli_command_check.request(recorded)

    assert [option.name for option in recorded.options] == [
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
