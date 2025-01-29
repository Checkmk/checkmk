#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.agent_based.emc_vplex_if import parse_emc_vplex_if
from cmk.plugins.lib import interfaces


def test_parse_emc_vplex_if() -> None:
    assert parse_emc_vplex_if(
        [
            [["director-1-1-A", "128.221.252.35"], ["director-1-1-B", "128.221.252.36"]],
            [
                ["A0-FC00", "159850409786880", "118814791148032", "128.221.252.35.1"],
                ["B0-FC00", "325205070345216", "198559903067648", "128.221.252.36.1"],
            ],
            [
                ["A1-FC00", "186252890510666", "187929275117112", "128.221.252.35.1"],
                ["B1-FC00", "245631087709370", "155375928891392", "128.221.252.36.1"],
            ],
        ]
    ) == [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="1",
                descr="A0-FC00",
                alias="director-1-1-A A0-FC00",
                type="",
                speed=0,
                oper_status="1",
                phys_address="",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Counters(
                in_octets=159850409786880,
                out_octets=118814791148032,
            ),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="2",
                descr="B0-FC00",
                alias="director-1-1-B B0-FC00",
                type="",
                speed=0,
                oper_status="1",
                phys_address="",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Counters(
                in_octets=325205070345216,
                out_octets=198559903067648,
            ),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="3",
                descr="A1-FC00",
                alias="director-1-1-A A1-FC00",
                type="",
                speed=0,
                oper_status="1",
                phys_address="",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Counters(
                in_octets=186252890510666,
                out_octets=187929275117112,
            ),
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="4",
                descr="B1-FC00",
                alias="director-1-1-B B1-FC00",
                type="",
                speed=0,
                oper_status="1",
                phys_address="",
                oper_status_name="up",
                speed_as_text="",
                group=None,
                node=None,
                admin_status=None,
            ),
            interfaces.Counters(
                in_octets=245631087709370,
                out_octets=155375928891392,
            ),
        ),
    ]
