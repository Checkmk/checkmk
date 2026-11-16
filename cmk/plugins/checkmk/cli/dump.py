#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The dumping commands: --dump-agent and --dump."""

from dataclasses import dataclass

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Reader as CLIReader

from .options import (
    fake_dns_request,
    FAKE_DNS_VALUE,
    file_cache_request,
    FileCacheRequest,
    SNMP_BACKEND_VALUE,
)


@dataclass(frozen=True, kw_only=True)
class DumpAgentRequest:
    file_cache: FileCacheRequest
    snmp_backend: SNMPBackendEnum | None
    fake_dns: HostAddress | None


def _dump_agent_request(options: CLIReader) -> DumpAgentRequest:
    return DumpAgentRequest(
        file_cache=file_cache_request(options),
        snmp_backend=options.value(SNMP_BACKEND_VALUE),
        fake_dns=options.value(FAKE_DNS_VALUE),
    )


cli_command_dump_agent = CLICommand(
    name="dump_agent",
    handler="cmk.plugins.checkmk.cli.handlers.dump:cli_handler_dump_agent",
    long="dump-agent",
    short="d",
    request=_dump_agent_request,
    arguments=CLIArgument(placeholder="HOSTNAME|ADDRESS", parse=str),
    help="Show raw information from agent",
    description=[
        (
            "Shows the raw information received from the given host. For regular "
            "hosts it shows the agent output plus possible piggyback information. "
            "Does not work on clusters but only on real hosts. "
        )
    ],
)


cli_command_dump = CLICommand(
    name="dump",
    handler="cmk.plugins.checkmk.cli.handlers.dump:cli_handler_dump",
    long="dump",
    short="D",
    arguments=CLIArguments(placeholder="H1 H2...", parse=str),
    request=fake_dns_request,
    help="Dump info about all or some hosts",
    description=[
        (
            "Dumps out the complete configuration and information "
            "about one, several or all hosts. It shows all services, hostgroups, "
            "contacts and other information about that host."
        ),
    ],
)
