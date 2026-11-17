#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.list_config import (
    _ALL_SITES_FLAG,
    _INCLUDE_OFFLINE_FLAG,
    _list_hosts_request,
    _tags_request,
    ListHostsRequest,
)
from cmk.ruleset_matcher.tags import TagID


def test_the_list_hosts_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _ALL_SITES_FLAG: [""],
        _INCLUDE_OFFLINE_FLAG: [""],
        CLIArguments(placeholder="G1 G2...", parse=str): ["linux"],
    }

    assert _list_hosts_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == ListHostsRequest(all_sites=True, include_offline=True, host_groups=("linux",))


def test_the_tags_to_list_are_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        CLIArguments(placeholder="TAG1 TAG2...", parse=TagID): ["lan", "prod"]
    }

    assert _tags_request(CLIReader(lambda declaration: given.get(declaration, ()))) == (
        TagID("lan"),
        TagID("prod"),
    )
