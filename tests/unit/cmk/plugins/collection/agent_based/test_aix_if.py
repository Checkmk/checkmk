#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.aix_if import parse_aix_if

from cmk.plugins.lib.interfaces import (
    Attributes,
    Counters,
    InterfaceWithCounters,
    Section,
)

STRING_TABLE = [
    ["[en4]"],
    ["Hardware", "Address:", "00:22:55:33:fb:5c"],
    ["Packets:", "26392620773", "Packets:", "36807731516"],
    ["Bytes:", "145065251448544", "Bytes:", "7041069124495"],
    ["General", "Statistics:"],
    ["-------------------"],
    ["No", "mbuf", "Errors:", "0"],
    ["Adapter", "Reset", "Count:", "0"],
    ["Adapter", "Data", "Rate:", "2000"],
    ["Driver", "Flags:", "Up", "Broadcast", "Running"],
    ["Simplex", "64BitSupport", "ChecksumOffload"],
    ["LargeSend", "DataRateSet", "ETHERCHANNEL"],
]

EXPECTED_SECTION = [
    InterfaceWithCounters(
        attributes=Attributes(
            index="1",
            descr="en4",
            alias="en4",
            type="6",
            speed=2000000000,
            oper_status="1",
            out_qlen=None,
            phys_address='\x00"U3û\\',
            oper_status_name="up",
            speed_as_text="",
            group=None,
            node=None,
            admin_status=None,
            extra_info=None,
        ),
        counters=Counters(
            in_octets=7041069124495,
            in_mcast=None,
            in_bcast=None,
            in_nucast=None,
            in_ucast=36807731516,
            in_disc=None,
            in_err=None,
            out_octets=145065251448544,
            out_mcast=None,
            out_bcast=None,
            out_nucast=None,
            out_ucast=26392620773,
            out_disc=None,
            out_err=None,
        ),
    )
]


@pytest.mark.parametrize(
    "string_table,section",
    [
        pytest.param(
            STRING_TABLE,
            EXPECTED_SECTION,
            id="previous aix_if section generated via entstat: we don't know if the interface is up or down",
        ),
        pytest.param(
            [
                ["[interfaces_in_down_state]"],
            ]
            + STRING_TABLE,
            EXPECTED_SECTION,
            id="new aix_if section with down interfaces: no down interfaces",
        ),
        pytest.param(
            [
                ["[interfaces_in_down_state]"],
                ["en4"],
            ]
            + STRING_TABLE,
            [
                InterfaceWithCounters(
                    attributes=Attributes(
                        index="1",
                        descr="en4",
                        alias="en4",
                        type="6",
                        speed=2000000000,
                        oper_status="2",
                        out_qlen=None,
                        phys_address='\x00"U3û\\',
                        oper_status_name="down",
                        speed_as_text="",
                        group=None,
                        node=None,
                        admin_status=None,
                        extra_info=None,
                    ),
                    counters=Counters(
                        in_octets=7041069124495,
                        in_mcast=None,
                        in_bcast=None,
                        in_nucast=None,
                        in_ucast=36807731516,
                        in_disc=None,
                        in_err=None,
                        out_octets=145065251448544,
                        out_mcast=None,
                        out_bcast=None,
                        out_nucast=None,
                        out_ucast=26392620773,
                        out_disc=None,
                        out_err=None,
                    ),
                )
            ],
            id="new aix_if section with down interfaces: en4 is down",
        ),
    ],
)
def test_parse_aix_if(string_table: list[list[str]], section: Section) -> None:
    assert parse_aix_if(string_table) == section
