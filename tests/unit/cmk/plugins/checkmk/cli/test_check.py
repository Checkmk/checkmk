#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.check import (
    _checking_request,
    _NO_SUBMIT_FLAG,
    _run_check,
    CheckingRequest,
)
from cmk.plugins.checkmk.cli.options import (
    CHECK_PLUGINS_VALUE,
    DETECT_PLUGINS_VALUE,
    DETECT_SECTIONS_VALUE,
    FAKE_DNS_VALUE,
    FileCacheRequest,
    NO_CACHE_FLAG,
    PluginSelectionRequest,
    SNMP_BACKEND_VALUE,
    USEWALK_FLAG,
)


def test_more_than_a_host_and_an_address_are_rejected() -> None:
    logger = logging.getLogger(__name__)
    context = CLIContext(
        omd_root=Path("/nonexistent"), global_options=CLIGlobalOptions(), logger=logger
    )
    given: Mapping[CLIDeclaration, Sequence[str]] = {}

    request = _checking_request(CLIReader(lambda declaration: given.get(declaration, ())))

    assert _run_check(context, request, ["host1", "host2", "host3"]) == CLIExitCode.UNKNOWN


def test_the_checking_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        NO_CACHE_FLAG: [""],
        USEWALK_FLAG: [""],
        _NO_SUBMIT_FLAG: [""],
        SNMP_BACKEND_VALUE: ["classic"],
        DETECT_SECTIONS_VALUE: ["df,mem"],
        CHECK_PLUGINS_VALUE: ["df"],
        DETECT_PLUGINS_VALUE: ["cpu_loads"],
        FAKE_DNS_VALUE: ["1.2.3.4"],
    }

    assert _checking_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == CheckingRequest(
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
