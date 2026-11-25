#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.discovery import (
    _check_discovery_request,
    _DISCOVER_COUNT,
    _discover_request,
    _ONLY_HOST_LABELS_FLAG,
    CheckDiscoveryRequest,
    DiscoverRequest,
)
from cmk.plugins.checkmk.cli.options import (
    _CACHE_FLAG,
    _NO_TCP_FLAG,
    CHECK_PLUGINS_VALUE,
    FAKE_DNS_VALUE,
    FetchRequest,
    FileCacheRequest,
    PluginSelectionRequest,
    SNMP_BACKEND_VALUE,
)


def test_the_check_discovery_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _CACHE_FLAG: [""],
        SNMP_BACKEND_VALUE: ["inline"],
        FAKE_DNS_VALUE: ["1.2.3.4"],
        CLIArgument(placeholder="HOSTNAME", parse=HostAddress): ["myhost"],
    }

    assert _check_discovery_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == CheckDiscoveryRequest(
        fetch=FetchRequest(
            file_cache=FileCacheRequest(cache=True, no_cache=False, no_tcp=False),
            usewalk=False,
            snmp_backend=SNMPBackendEnum.INLINE,
            fake_dns=HostAddress("1.2.3.4"),
        ),
        host=HostAddress("myhost"),
    )


def test_the_discover_request_counts_the_commands_own_option() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _NO_TCP_FLAG: [""],
        _ONLY_HOST_LABELS_FLAG: [""],
        _DISCOVER_COUNT: ["", ""],
        CHECK_PLUGINS_VALUE: ["df,mem"],
        CLIArguments(placeholder="HOST1 HOST2...", parse=str): ["myhost", "@mytag"],
    }

    assert _discover_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == DiscoverRequest(
        fetch=FetchRequest(
            file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=True),
            usewalk=False,
            snmp_backend=None,
            fake_dns=None,
        ),
        discover=2,
        plugin_selection=PluginSelectionRequest(
            detect_sections=None,
            plugins=frozenset({CheckPluginName("df"), CheckPluginName("mem")}),
            detect_plugins=None,
        ),
        only_host_labels=True,
        hosts=("myhost", "@mytag"),
    )
