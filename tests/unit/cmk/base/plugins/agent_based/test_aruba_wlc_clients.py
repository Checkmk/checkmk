#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.aruba_wlc_clients import parse_aruba_wlc_clients
from cmk.base.plugins.agent_based.utils.wlc_clients import ClientsTotal, VsResult, WlcClientsSection
from cmk.base.plugins.agent_based.wlc_clients import check_wlc_clients

# raw data looks like this:
# TODO: we should use this as test input
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.0 0 --> WLSX-WLAN-MIB::wlanESSIDNumStations.""
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.4.86.111.73.80 0 --> WLSX-WLAN-MIB::wlanESSIDNumStations."VoIP"
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.5.87.105.76.65.78 37 --> WLSX-WLAN-MIB::wlanESSIDNumStations."WiLAN"
# .1.3.6.1.4.1.14823.2.2.1.5.2.1.8.1.2.7.77.45.87.105.76.65.78 44 --> WLSX-WLAN-MIB::wlanESSIDNumStations."M-WiLAN"

INFO: List[StringTable] = [
    [
        ["0", "0"],
        ["4.86.111.73.80", "0"],
        ["5.87.105.76.65.78", "37"],
        ["7.77.45.87.105.76.65.78", "44"],
    ]
]

ITEM_RESULT = [
    [
        "Summary",
        [
            Result(state=State.OK, summary="Connections: 81"),
            Metric("connections", 81.0),
        ],
    ],
    [
        "VoIP",
        [
            Result(state=State.OK, summary="Connections: 0"),
            Metric("connections", 0.0),
        ],
    ],
    [
        "WiLAN",
        [
            Result(state=State.OK, summary="Connections: 37"),
            Metric("connections", 37.0),
        ],
    ],
]


def _run_parse_and_check(
    item: str,
    info: List[StringTable],
    params: Optional[VsResult] = None,
):
    if params is None:
        params = {}
    result = list(check_wlc_clients(item, params, parse_aruba_wlc_clients(info)))
    return result


@pytest.mark.parametrize("item, result", ITEM_RESULT)
def test_aruba_wlc_clients(item, result):
    assert _run_parse_and_check(item, INFO) == result


def test_parse_aruba_wlc_clients():
    result = parse_aruba_wlc_clients(INFO)

    assert result == WlcClientsSection(
        total_clients=81,
        clients_per_ssid={
            "VoIP": ClientsTotal(total=0),
            "WiLAN": ClientsTotal(total=37),
            "M-WiLAN": ClientsTotal(total=44),
        },
    )
