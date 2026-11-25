#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.dump import (
    _dump_agent_request,
    _dump_hosts_request,
    DumpAgentRequest,
    DumpHostsRequest,
)
from cmk.plugins.checkmk.cli.options import (
    _NO_TCP_FLAG,
    FAKE_DNS_VALUE,
    FileCacheRequest,
    SNMP_BACKEND_VALUE,
)


def test_the_dump_agent_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _NO_TCP_FLAG: [""],
        SNMP_BACKEND_VALUE: ["stored-walk"],
        CLIArgument(placeholder="HOSTNAME|ADDRESS", parse=HostAddress): ["myhost"],
    }

    assert _dump_agent_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == DumpAgentRequest(
        file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=True),
        snmp_backend=SNMPBackendEnum.STORED_WALK,
        fake_dns=None,
        host=HostAddress("myhost"),
    )


def test_the_hosts_to_dump_are_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        FAKE_DNS_VALUE: ["127.0.0.1"],
        CLIArguments(placeholder="H1 H2...", parse=HostAddress): ["host1", "host2"],
    }

    assert _dump_hosts_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == DumpHostsRequest(
        fake_dns=HostAddress("127.0.0.1"), hosts=(HostAddress("host1"), HostAddress("host2"))
    )
