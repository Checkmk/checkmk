#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Command as CLICommand
from cmk.plugins.checkmk.cli.discovery import (
    _check_discovery_request,
    _CheckDiscoveryRequest,
    _discover_request,
    _DiscoverRequest,
    cli_command_check_discovery,
    cli_command_discover,
)
from cmk.plugins.checkmk.cli.options import FileCacheRequest, PluginSelectionRequest


def _declared[R](command: CLICommand[R]) -> list[str]:
    recorded = CLIRecordedOptions()
    command.request(recorded)
    return [option.name for option in recorded.options]


def test_check_discovery_declares_its_options_in_help_order() -> None:
    assert _declared(cli_command_check_discovery) == [
        "cache",
        "no-cache",
        "no-tcp",
        "usewalk",
        "snmp-backend",
        "fake-dns",
    ]


def test_discover_declares_its_options_in_help_order() -> None:
    assert _declared(cli_command_discover) == [
        "cache",
        "no-cache",
        "no-tcp",
        "usewalk",
        "snmp-backend",
        "discover",
        "detect-sections",
        "plugins",
        "detect-plugins",
        "only-host-labels",
        "fake-dns",
    ]


def test_the_check_discovery_request_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions(
        [("--cache", ""), ("--snmp-backend", "inline"), ("--fake-dns", "1.2.3.4")],
        logging.getLogger(__name__),
    )

    assert _check_discovery_request(options) == _CheckDiscoveryRequest(
        file_cache=FileCacheRequest(cache=True, no_cache=False, no_tcp=False),
        usewalk=False,
        snmp_backend=SNMPBackendEnum.INLINE,
        fake_dns=HostAddress("1.2.3.4"),
    )


def test_the_discover_request_counts_the_commands_own_option() -> None:
    options = CLIParsedOptions(
        [
            ("--discover", ""),
            ("--discover", ""),
            ("--no-tcp", ""),
            ("--plugins", "df,mem"),
            ("--only-host-labels", ""),
        ],
        logging.getLogger(__name__),
    )

    assert _discover_request(options) == _DiscoverRequest(
        file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=True),
        usewalk=False,
        snmp_backend=None,
        discover=2,
        plugin_selection=PluginSelectionRequest(
            detect_sections=None,
            plugins=frozenset({CheckPluginName("df"), CheckPluginName("mem")}),
            detect_plugins=None,
        ),
        only_host_labels=True,
        fake_dns=None,
    )
