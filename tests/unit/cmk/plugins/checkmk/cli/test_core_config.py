#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.ccc.hostaddress import HostAddress
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.core_config import (
    _core_config_request,
    CoreConfigRequest,
)
from cmk.plugins.checkmk.cli.options import FAKE_DNS_VALUE


def test_the_hosts_are_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        FAKE_DNS_VALUE: ["127.0.0.1"],
        CLIArguments(placeholder="HOST1 HOST2...", parse=HostAddress): ["host1", "host2"],
    }

    assert _core_config_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == CoreConfigRequest(
        fake_dns=HostAddress("127.0.0.1"), hosts=(HostAddress("host1"), HostAddress("host2"))
    )
