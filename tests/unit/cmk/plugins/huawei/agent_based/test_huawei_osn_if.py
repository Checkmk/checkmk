#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.huawei.agent_based.huawei_osn_if import parse_huawei_osn_if_pure
from cmk.plugins.lib import interfaces


def test_parse_huawei_osn_if_pure() -> None:
    name = "board=2,subcard=255,port=3,path=1"
    assert parse_huawei_osn_if_pure(
        [
            [
                [
                    name,
                    "7082029074219",
                    "17036981",
                    "279",
                    "6838315476691",
                    "17036419",
                    "",
                    "3948539971896391",
                    "7735753792855325",
                    "310",
                    "1283",
                ],
            ]
        ],
        1.0,
    ) == {
        name: interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index=name,
                descr=name,
                alias=name,
                type="39",
                oper_status="1",
            ),
            interfaces.Counters(
                in_octets=3948539971896391,
                in_ucast=7082029074219,
                in_mcast=17036981,
                in_bcast=279,
                in_err=310,
                out_octets=7735753792855325,
                out_ucast=6838315476691,
                out_mcast=17036419,
                out_bcast=0,
                out_err=1283,
            ),
            timestamp=1.0,
        ),
    }
