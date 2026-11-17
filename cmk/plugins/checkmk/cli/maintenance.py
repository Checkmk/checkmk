#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The site maintenance commands: --flush, --update-dns-cache and --cleanup-piggyback."""

from collections.abc import Sequence

from cmk.ccc.hostaddress import HostAddress
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader

from .options import fake_dns_request

cli_command_update_dns_cache = CLICommand(
    name="update_dns_cache",
    handler="cmk.plugins.checkmk.cli.handlers.maintenance:cli_handler_update_dns_cache",
    long="update-dns-cache",
    request=fake_dns_request,
    help="Update IP address lookup cache",
)


cli_command_cleanup_piggyback = CLICommand(
    name="cleanup_piggyback",
    handler="cmk.plugins.checkmk.cli.handlers.maintenance:cli_handler_cleanup_piggyback",
    long="cleanup-piggyback",
    request=cli_no_options,
    help="Cleanup outdated piggyback files",
)


def _hosts_request(options: CLIReader) -> Sequence[HostAddress]:
    return options.arguments(CLIArguments(placeholder="HOST1 HOST2...", parse=HostAddress))


cli_command_flush = CLICommand(
    name="flush",
    handler="cmk.plugins.checkmk.cli.handlers.maintenance:cli_handler_flush",
    long="flush",
    request=_hosts_request,
    help="Flush all data of some or all hosts",
    description=[
        (
            "Deletes all runtime data belonging to a host. This includes "
            "the inventorized checks, the state of performance counters, "
            "cached agent output, and logfiles. Precompiled host checks "
            "are not deleted."
        ),
    ],
)
