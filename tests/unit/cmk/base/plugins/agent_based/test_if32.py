#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.if32 import parse_if
from cmk.base.plugins.agent_based.utils.interfaces import Interface


def test_parse_if() -> None:
    assert parse_if(
        [
            [
                "1",
                "1",
                "6",
                "100000000",
                "1",
                "539345078",
                "3530301",
                "494413",
                "0",
                "15",
                "231288017",
                "3477770",
                "38668315",
                "0",
                "0",
                "0",
                [0, 38, 241, 198, 3, 255],
            ]
        ]
    ) == [
        Interface(
            index="1",
            descr="1",
            alias="1",
            type="6",
            speed=100000000,
            oper_status="1",
            in_octets=539345078,
            in_ucast=3530301,
            in_mcast=494413,
            in_bcast=0,
            in_discards=0,
            in_errors=15,
            out_octets=231288017,
            out_ucast=3477770,
            out_mcast=0,
            out_bcast=38668315,
            out_discards=0,
            out_errors=0,
            out_qlen=0,
            phys_address=[0, 38, 241, 198, 3, 255],
            oper_status_name="up",
            speed_as_text="",
            group=None,
            node=None,
            admin_status=None,
            total_octets=770633095,
        )
    ]
