#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The core configuration commands: --nagios-config, --update, --restart and --reload."""

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand

from .options import fake_dns_request

cli_command_nagios_config = CLICommand(
    name="nagios_config",
    handler="cmk.plugins.checkmk.cli.handlers.core_config:cli_handler_nagios_config",
    long="nagios-config",
    short="N",
    arguments=CLIArguments(placeholder="HOST1 HOST2...", parse=str),
    request=fake_dns_request,
    help="Output Nagios configuration",
    description=[
        (
            "Outputs the Nagios configuration. You may optionally add a list "
            "of hosts. In that case the configuration is generated only for "
            "that hosts (useful for debugging)."
        ),
    ],
)


cli_command_update = CLICommand(
    name="update",
    handler="cmk.plugins.checkmk.cli.handlers.core_config:cli_handler_update",
    long="update",
    short="U",
    request=fake_dns_request,
    help="Create core config",
    description=[
        (
            "Updates the core configuration based on the current Checkmk "
            "configuration. When using the Nagios core, the precompiled host "
            "checks are created and the nagios configuration is updated. "
            "When using the CheckMK Micro Core, the core configuration is created "
            "and the configuration for the Core helper processes is being created."
        ),
    ],
)


cli_command_restart = CLICommand(
    name="restart",
    handler="cmk.plugins.checkmk.cli.handlers.core_config:cli_handler_restart",
    long="restart",
    short="R",
    arguments=CLIArguments(placeholder="[HostA, HostB]", parse=str),
    request=fake_dns_request,
    help="Create core config + core restart",
    description=[
        (
            "You may add host names as additional arguments. This enables the incremental "
            "activate mechanism, only compiling these host names and using cached data for all "
            "other hosts. Only supported with Checkmk Micro Core."
        )
    ],
)


cli_command_reload = CLICommand(
    name="reload",
    handler="cmk.plugins.checkmk.cli.handlers.core_config:cli_handler_reload",
    long="reload",
    short="O",
    arguments=CLIArguments(placeholder="[HostA, HostB]", parse=str),
    request=fake_dns_request,
    help="Create core config + core reload",
    description=[
        (
            "You may add host names as additional arguments. This enables the incremental "
            "activate mechanism, only compiling these host names and using cached data for all "
            "other hosts. Only supported with Checkmk Micro Core."
        )
    ],
)
