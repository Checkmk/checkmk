#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Command as CLICommand
from cmk.plugins.checkmk.cli.list_config import (
    _list_hosts_request,
    _ListHostsRequest,
    cli_command_list_checks,
    cli_command_list_hosts,
    cli_command_list_tag,
)


@pytest.mark.parametrize(
    ["command", "expected"],
    [
        pytest.param(cli_command_list_hosts, ["all-sites", "include-offline"], id="list-hosts"),
        pytest.param(cli_command_list_tag, [], id="list-tag"),
        pytest.param(cli_command_list_checks, [], id="list-checks"),
    ],
)
def test_a_list_command_declares_its_options[R](
    command: CLICommand[R], expected: list[str]
) -> None:
    recorded = CLIRecordedOptions()
    command.request(recorded)

    assert [option.name for option in recorded.options] == expected


def test_the_list_hosts_request_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions([("--include-offline", "")], logging.getLogger(__name__))

    assert _list_hosts_request(options) == _ListHostsRequest(all_sites=False, include_offline=True)
