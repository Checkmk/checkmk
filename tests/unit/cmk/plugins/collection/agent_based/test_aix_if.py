#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import dataclasses

import pytest

from cmk.plugins.collection.agent_based.aix_if import parse_aix_if_pure
from cmk.plugins.lib.interfaces import Attributes, Counters, InterfaceWithCounters, Section

# Below is an output from the support ticket
#
# <<<aix_if>>>
# [interfaces_in_down_state]
# en1 en3 en5 en7
# [en8]
# Hardware Address: a2:1a:95:75:19:03
# Transmit Statistics:                          Receive Statistics:
# Packets: 73466                                Packets: 55078
# Bytes: 23141433                               Bytes: 8218386
# Transmit Errors: 0                            Receive Errors: 0
# General Statistics:
# -------------------
# No mbuf Errors: 0
# Adapter Reset Count: 0
# Adapter Data Rate: 20000
# Driver Flags: Up Broadcast Running
#         Simplex 64BitSupport ChecksumOffload
#         LargeSend DataRateSet PlatformTSO
#         VIOENT IPV6_LSO
#
# [en1]
# Hardware Address: a0:88:c2:e9:b3:21
# Transmit Statistics:                          Receive Statistics:
# Packets: 0                                    Packets: 0
# Bytes: 0                                      Bytes: 0
# Transmit Errors: 0                            Receive Errors: 0
# General Statistics:
# -------------------
# No mbuf Errors: 0
# Adapter Reset Count: 1
# Adapter Data Rate: 20000
# Driver Flags: Up Broadcast Simplex
#         Limbo 64BitSupport ChecksumOffload
#         LargeSend DataRateSet IPV6_LSO
#         IPV6_CSO LARGE_RECEIVE ROCE
#         HW_PTP_SUPP
#
# [en3]
# Hardware Address: a0:88:c2:e9:b3:81
# Transmit Statistics:                          Receive Statistics:
# Packets: 0                                    Packets: 0
# Bytes: 0                                      Bytes: 0
# Transmit Errors: 0                            Receive Errors: 0
# General Statistics:
# -------------------
# No mbuf Errors: 0
# Adapter Reset Count: 1
# Adapter Data Rate: 20000
# Driver Flags: Up Broadcast Simplex
#         Limbo 64BitSupport ChecksumOffload
#         LargeSend DataRateSet IPV6_LSO
#         IPV6_CSO LARGE_RECEIVE ROCE
#         HW_PTP_SUPP
#
# [en5]
# Hardware Address: a2:1a:95:75:19:03
# Transmit Statistics:                          Receive Statistics:
# Packets: 73475                                Packets: 55087
# Bytes: 23144195                               Bytes: 8219016
# Transmit Errors: 0                            Receive Errors: 0
# General Statistics:
# -------------------
# No mbuf Errors: 0
# Adapter Reset Count: 0
# Adapter Data Rate: 20000
# Driver Flags: Up Broadcast Running
#         Simplex 64BitSupport ChecksumOffload
#         LargeSend DataRateSet PlatformTSO
#         VIOENT IPV6_LSO
#
# [en7]
# Hardware Address: a0:88:c2:e9:b3:20
# Transmit Statistics:                          Receive Statistics:
# Packets: 30164825                             Packets: 29054584756
# Bytes: 20494315278                            Bytes: 43183684966611
# Transmit Errors: 0                            Receive Errors: 54788554
# General Statistics:
# -------------------
# No mbuf Errors: 0
# Adapter Reset Count: 0
# Adapter Data Rate: 0
# Driver Flags: Up Broadcast Running
#         Simplex 64BitSupport ChecksumOffload
#         LargeSend DataRateSet SEA

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
    ["[en5]"],
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
TIMESTAMP = 123.0

EXPECTED_SECTIONS = [
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
        timestamp=TIMESTAMP,
    ),
    InterfaceWithCounters(
        attributes=Attributes(
            index="2",
            descr="en5",
            alias="en5",
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
        timestamp=TIMESTAMP,
    ),
]


def disabled_section(interface: InterfaceWithCounters) -> InterfaceWithCounters:
    return dataclasses.replace(
        interface,
        attributes=dataclasses.replace(
            interface.attributes, oper_status="2", oper_status_name="down"
        ),
    )


@pytest.mark.parametrize(
    "string_table,section",
    [
        pytest.param(
            STRING_TABLE,
            EXPECTED_SECTIONS,
            id="previous aix_if section generated via entstat: we don't know if the interface is up or down",
        ),
        pytest.param(
            [
                ["[interfaces_in_down_state]"],
            ]
            + STRING_TABLE,
            EXPECTED_SECTIONS,
            id="new aix_if section with down interfaces: no down interfaces",
        ),
        pytest.param(
            [
                ["[interfaces_in_down_state]"],
                ["en4"],
            ]
            + STRING_TABLE,
            [disabled_section(EXPECTED_SECTIONS[0]), EXPECTED_SECTIONS[1]],
            id="new aix_if section with down interfaces: en4 is down",
        ),
        pytest.param(
            [
                ["[interfaces_in_down_state]"],
                ["en4", "en5"],
            ]
            + STRING_TABLE,
            [disabled_section(EXPECTED_SECTIONS[0]), disabled_section(EXPECTED_SECTIONS[1])],
            id="new aix_if section with down interfaces: en4 and en5 are down",
        ),
    ],
)
def test_parse_aix_if_pure(string_table: list[list[str]], section: Section) -> None:
    assert parse_aix_if_pure(string_table, timestamp=TIMESTAMP) == section
