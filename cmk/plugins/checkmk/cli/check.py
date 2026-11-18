#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --check" command."""

import dataclasses
from typing import Final

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import CheckPluginName
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader

from .options import (
    CHECK_PLUGINS_VALUE,
    fetch_request,
    FetchRequest,
    plugin_selection_request,
    PluginSelectionRequest,
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
    fetch: FetchRequest
    no_submit: bool
    perfdata: bool
    plugin_selection: PluginSelectionRequest[CheckPluginName]
    host: HostName | None
    address: HostAddress | None


def _checking_request(options: CLIReader) -> CheckingRequest:
    return CheckingRequest(
        fetch=fetch_request(options),
        no_submit=options.flag(_NO_SUBMIT_FLAG),
        perfdata=options.flag(_PERFDATA_FLAG),
        plugin_selection=plugin_selection_request(options, CHECK_PLUGINS_VALUE),
        host=options.argument(CLIArgument(placeholder="HOST", parse=HostName)),
        address=options.argument(CLIOptionalArgument(placeholder="IPADDRESS", parse=HostAddress)),
    )


cli_command_check = CLICommand(
    name="check",
    handler="cmk.plugins.checkmk.cli.handlers.check:cli_handler_check",
    long="check",
    request=_checking_request,
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
