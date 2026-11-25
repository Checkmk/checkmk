#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.check import (
    _checking_request,
    _NO_SUBMIT_FLAG,
    _PERFDATA_FLAG,
    CheckingRequest,
)
from cmk.plugins.checkmk.cli.options import (
    _DETECT_PLUGINS_VALUE,
    _DETECT_SECTIONS_VALUE,
    _NO_CACHE_FLAG,
    _USEWALK_FLAG,
    CHECK_PLUGINS_VALUE,
    FAKE_DNS_VALUE,
    FetchRequest,
    FileCacheRequest,
    PluginSelectionRequest,
    SNMP_BACKEND_VALUE,
)


def test_the_checking_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _NO_CACHE_FLAG: [""],
        _USEWALK_FLAG: [""],
        _NO_SUBMIT_FLAG: [""],
        _PERFDATA_FLAG: [""],
        SNMP_BACKEND_VALUE: ["classic"],
        _DETECT_SECTIONS_VALUE: ["df,mem"],
        CHECK_PLUGINS_VALUE: ["df"],
        _DETECT_PLUGINS_VALUE: ["cpu_loads"],
        FAKE_DNS_VALUE: ["1.2.3.4"],
        CLIArgument(placeholder="HOST", parse=HostName): ["myhost"],
        CLIOptionalArgument(placeholder="IPADDRESS", parse=HostAddress): ["10.0.0.1"],
    }

    assert _checking_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == CheckingRequest(
        fetch=FetchRequest(
            file_cache=FileCacheRequest(cache=False, no_cache=True, no_tcp=False),
            usewalk=True,
            snmp_backend=SNMPBackendEnum.CLASSIC,
            fake_dns=HostAddress("1.2.3.4"),
        ),
        no_submit=True,
        perfdata=True,
        plugin_selection=PluginSelectionRequest(
            detect_sections=frozenset({SectionName("df"), SectionName("mem")}),
            plugins=frozenset({CheckPluginName("df")}),
            detect_plugins=frozenset({"cpu_loads"}),
        ),
        host=HostName("myhost"),
        address=HostAddress("10.0.0.1"),
    )
