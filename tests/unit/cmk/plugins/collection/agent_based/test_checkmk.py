#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import HostLabel
from cmk.plugins.collection.agent_based.check_mk import (
    host_label_function_labels,
    parse_checkmk_labels,
)

# TODO(sk):  tests should use native agent data as input, not manually parsed string table
# TODO(sk):  the lone test should be separated into three tests, one for each case


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        pytest.param(
            [
                ["Version:", "1.7.0i1"],
                ["AgentOS:", "linux"],
                ["Hostname:", "klappclub"],
                ["AgentDirectory:", "/etc/check_mk"],
                # .... doesnt matter
                ["LocalDirectory:", "/usr/lib/check_mk_agent/local"],
                ["OSType:", "linux"],
                ["OSPlatform:", "ubuntu"],
                ["OSName:", "Ubuntu"],
                ["OSVersion:", "20.04"],
            ],
            [
                HostLabel("cmk/os_family", "linux"),
                HostLabel("cmk/os_type", "linux"),
                HostLabel("cmk/os_platform", "ubuntu"),
                HostLabel("cmk/os_name", "Ubuntu"),
                HostLabel("cmk/os_version", "20.04"),
            ],
            id="linux current agent",
        ),
        pytest.param(
            [
                ["Version:", "1.7.0i1"],
                ["AgentOS:", "linux"],
                ["Hostname:", "klappclub"],
                ["AgentDirectory:", "/etc/check_mk"],
                # .... doesnt matter
            ],
            [
                HostLabel("cmk/os_family", "linux"),
                HostLabel("cmk/os_platform", "linux"),
            ],
            id="old agent",
        ),
        pytest.param(
            [
                ["Version:", "1.7.0i1"],
                ["AgentOS:", "windows"],
                ["Hostname:", "klappclub"],
                ["AgentDirectory:", "doesntmatter"],
            ],
            [
                HostLabel("cmk/os_family", "windows"),
                HostLabel("cmk/os_platform", "windows"),
            ],
            id="windows agent",
        ),
    ],
)
def test_checkmk_labels_old_agent(
    string_table: StringTable, expected_parsed_data: Sequence[HostLabel]
) -> None:
    result = list(host_label_function_labels(parse_checkmk_labels(string_table)))
    assert expected_parsed_data == result
