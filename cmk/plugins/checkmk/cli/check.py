#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --check" command."""

import dataclasses
from typing import Final

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import CheckPluginName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader

from .options import (
    CHECK_PLUGINS_VALUE,
    FAKE_DNS_VALUE,
    file_cache_request,
    FileCacheRequest,
    plugin_selection_request,
    PluginSelectionRequest,
    SNMP_BACKEND_VALUE,
    USEWALK_FLAG,
)

_NO_SUBMIT_FLAG: Final = CLIFlag(
    long="no-submit",
    short="n",
    help="Do not submit results to core, do not save counters",
)


_PERFDATA_FLAG: Final = CLIFlag(
    long="perfdata",
    short="p",
    help="Also show performance data (use with -v)",
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class CheckingRequest:
    file_cache: FileCacheRequest
    usewalk: bool
    snmp_backend: SNMPBackendEnum | None
    no_submit: bool
    perfdata: bool
    plugin_selection: PluginSelectionRequest[CheckPluginName]
    fake_dns: HostAddress | None


def _checking_request(options: CLIReader) -> CheckingRequest:
    return CheckingRequest(
        file_cache=file_cache_request(options),
        usewalk=options.flag(USEWALK_FLAG),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        no_submit=options.flag(_NO_SUBMIT_FLAG),
        perfdata=options.flag(_PERFDATA_FLAG),
        plugin_selection=plugin_selection_request(options, CHECK_PLUGINS_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
    )


cli_command_check = CLICommand(
    name="check",
    handler="cmk.plugins.checkmk.cli.handlers.check:cli_handler_check",
    long="check",
    request=_checking_request,
    arguments=CLIArguments("HOST [IPADDRESS]", optional=True),
    default=True,
    help="Check all services on the given HOST",
    description=[
        (
            "Execute all checks on the given HOST. Optionally you can specify "
            "a second argument, the IPADDRESS. If you don't set this, the "
            "configured IP address of the HOST is used."
        ),
        (
            "By default the check results are sent to the core. If you provide "
            "the option '-n', the results will not be sent to the core and the "
            "counters of the check will not be stored."
        ),
        (
            "You can use '-v' to see the results of the checks. Add '-p' to "
            "also see the performance data of the checks. "
            "Can be restricted to certain check types. Write '--checks df -I' if "
            "you just want to look for new filesystems. Use 'check_mk -L' for a "
            "list of all check types. Use 'tcp' for all TCP based checks and "
            "'snmp' for all SNMP based checks."
        ),
    ],
)
