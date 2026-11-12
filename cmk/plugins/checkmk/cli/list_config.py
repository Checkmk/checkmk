#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk" commands that list parts of the configuration.

--list-hosts, --list-tag and --list-checks.
"""

import dataclasses
from typing import Final

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader

_ALL_SITES_FLAG: Final = CLIFlag(
    long="all-sites",
    help="Include hosts of foreign sites",
)


_INCLUDE_OFFLINE_FLAG: Final = CLIFlag(
    long="include-offline",
    help="Include offline hosts",
)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ListHostsRequest:
    all_sites: bool
    include_offline: bool


def _list_hosts_request(options: CLIReader) -> ListHostsRequest:
    return ListHostsRequest(
        all_sites=options.flag(_ALL_SITES_FLAG),
        include_offline=options.flag(_INCLUDE_OFFLINE_FLAG),
    )


cli_command_list_hosts = CLICommand(
    name="list_hosts",
    handler="cmk.plugins.checkmk.cli.handlers.list_config:cli_handler_list_hosts",
    long="list-hosts",
    short="l",
    arguments=CLIArguments("G1 G2...", optional=True),
    request=_list_hosts_request,
    help="Print list of all hosts or members of host groups",
    description=[
        (
            "Called without argument lists all hosts. You may "
            "specify one or more host groups to restrict the output to hosts "
            "that are in at least one of those groups."
        ),
    ],
)


cli_command_list_tag = CLICommand(
    name="list_tag",
    handler="cmk.plugins.checkmk.cli.handlers.list_config:cli_handler_list_tag",
    long="list-tag",
    request=cli_no_options,
    arguments=CLIArguments("TAG1 TAG2...", optional=True),
    help="List hosts having certain tags",
    description=["Prints all hosts that have all of the specified tags at once."],
)


cli_command_list_checks = CLICommand(
    name="list_checks",
    handler="cmk.plugins.checkmk.cli.handlers.list_config:cli_handler_list_checks",
    long="list-checks",
    short="L",
    request=cli_no_options,
    help="List all available Check_MK checks",
)
