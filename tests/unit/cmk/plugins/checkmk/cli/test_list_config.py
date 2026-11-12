#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.list_config import (
    _INCLUDE_OFFLINE_FLAG,
    _list_hosts_request,
    ListHostsRequest,
)


def test_the_list_hosts_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {_INCLUDE_OFFLINE_FLAG: [""]}

    assert _list_hosts_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == ListHostsRequest(all_sites=False, include_offline=True)
