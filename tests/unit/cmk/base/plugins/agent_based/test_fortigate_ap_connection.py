#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.fortigate_ap_connection import (
    AccessPoint,
    check_fortigate_ap_connection,
    ConnectionState,
)


def test_check_fortigate_ap_connection() -> None:
    assert list(
        check_fortigate_ap_connection(
            "a",
            {
                "conn_state_to_mon_state": {
                    "other": 3,
                    "offLine": 1,
                    "onLine": 0,
                    "downloadingImage": 0,
                    "connectedImage": 0,
                    "standby": 0,
                },
            },
            {
                "a": AccessPoint(
                    connection_state=ConnectionState(
                        status="offLine",
                        description="The WTP is not connected.",
                    ),
                    station_count=0,
                ),
                "b": AccessPoint(
                    connection_state=ConnectionState(
                        status="onLine",
                        description="The WTP is connected.",
                    ),
                    station_count=5,
                ),
            },
        )
    ) == [
        Result(
            state=State.WARN,
            summary="State: offLine",
            details="The WTP is not connected.",
        ),
        Result(
            state=State.OK,
            summary="Connected clients: 0",
        ),
        Metric(
            "connections",
            0.0,
            boundaries=(0.0, None),
        ),
    ]
