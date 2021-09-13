#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel
from cmk.base.plugins.agent_based.check_mk import host_label_function_labels, parse_checkmk_labels


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [
                ["Version:", "1.7.0i1"],
                ["AgentOS:", "linux"],
                ["Hostname:", "klappclub"],
                ["AgentDirectory:", "/etc/check_mk"],
                ["DataDirectory:", "/var/lib/check_mk_agent"],
                ["SpoolDirectory:", "/var/lib/check_mk_agent/spool"],
                ["PluginsDirectory:", "/usr/lib/check_mk_agent/plugins"],
                ["LocalDirectory:", "/usr/lib/check_mk_agent/local"],
            ],
            [HostLabel("cmk/os_family", "linux")],
        ),
    ],
)
def test_checkmk_labels(string_table, expected_parsed_data):
    result = list(host_label_function_labels(parse_checkmk_labels(string_table)))
    assert isinstance(result[0], HostLabel)
    assert expected_parsed_data == result
