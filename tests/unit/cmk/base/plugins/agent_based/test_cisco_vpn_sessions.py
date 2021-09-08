#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing as t

import pytest

from cmk.base.plugins.agent_based import cisco_vpn_sessions
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

DATA_0 = [["0", "0", "0", "13", "152", "13", "58", "10533", "87", "0", "0", "0", "2500"]]
RESULT_0 = {
    "AnyConnect SVC": {
        "active_sessions": 58,
        "cumulative_sessions": 10533,
        "maximum_sessions": 2500,
        "peak_sessions": 87,
    },
    "IPsec L2L": {
        "active_sessions": 13,
        "cumulative_sessions": 152,
        "maximum_sessions": 2500,
        "peak_sessions": 13,
    },
    "IPsec RA": {
        "active_sessions": 0,
        "cumulative_sessions": 0,
        "maximum_sessions": 2500,
        "peak_sessions": 0,
    },
    "Summary": {"active_sessions": 71, "cumulative_sessions": 10685, "maximum_sessions": 2500},
    "WebVPN": {
        "active_sessions": 0,
        "cumulative_sessions": 0,
        "maximum_sessions": 2500,
        "peak_sessions": 0,
    },
}


@pytest.mark.parametrize(
    "string_table,output",
    [
        (DATA_0, RESULT_0),
    ],
)
def test_cisco_vpn_sessions_parse(
    string_table: StringTable, output: t.Dict[str, t.Dict[str, int]]
) -> None:
    result = cisco_vpn_sessions.parse_cisco_vpn_sessions(string_table)
    assert result == output
