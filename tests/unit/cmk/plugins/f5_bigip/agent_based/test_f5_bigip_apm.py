#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.f5_bigip.agent_based.f5_bigip_apm import check_f5_bigip_apm, parse_f5_bigip_apm


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param([["42"]], 42, id="a connection count"),
        pytest.param([["0"]], 0, id="no connections"),
        pytest.param([[""]], None, id="the OID is not populated"),
        pytest.param([], None, id="empty section"),
    ],
)
def test_parse_f5_bigip_apm(string_table: StringTable, expected: int | None) -> None:
    assert parse_f5_bigip_apm(string_table) == expected


def test_check_f5_bigip_apm() -> None:
    assert list(check_f5_bigip_apm(42)) == [
        Result(state=State.OK, summary="Connections: 42"),
        Metric("connections_ssl_vpn", 42.0, boundaries=(0.0, None)),
    ]
